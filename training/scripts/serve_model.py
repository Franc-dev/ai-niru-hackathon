"""
Serve the EM-NS LoRA fine-tuned model as an HTTP API.

Exposes two endpoints that the backend expects:
  POST /v1/chat       -> {"content": "..."}
  POST /v1/embeddings -> {"embeddings": [[...]]}

Works on CPU (slow) or GPU (fast). Loads the LoRA adapter on top of the
base model and generates responses.

Usage:
  python training/scripts/serve_model.py
  python training/scripts/serve_model.py --adapter-path ./emns-lora-v1 --port 8001
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import torch
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Request/response schemas (matches what backend/services/agent.py expects)
# ---------------------------------------------------------------------------

class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    max_new_tokens: int = 128
    temperature: float = 0.7
    top_p: float = 0.9


class ChatResponse(BaseModel):
    content: str


class EmbeddingRequest(BaseModel):
    input: str | list[str]


class EmbeddingResponse(BaseModel):
    embeddings: list[list[float]]


# ---------------------------------------------------------------------------
# Global model state
# ---------------------------------------------------------------------------

_model = None
_tokenizer = None
_device = None


def load_model(base_model: str, adapter_path: str | None) -> None:
    global _model, _tokenizer, _device
    from transformers import AutoModelForCausalLM, AutoTokenizer

    _device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Loading base model: {base_model} on {_device} ...")

    _tokenizer = AutoTokenizer.from_pretrained(base_model, trust_remote_code=True)
    if _tokenizer.pad_token is None:
        _tokenizer.pad_token = _tokenizer.eos_token

    dtype = torch.float32  # CPU-safe default
    if torch.cuda.is_available():
        dtype = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16

    _model = AutoModelForCausalLM.from_pretrained(
        base_model,
        trust_remote_code=True,
        torch_dtype=dtype,
        device_map="auto" if torch.cuda.is_available() else None,
    )

    if adapter_path and Path(adapter_path).exists():
        from peft import PeftModel

        print(f"Loading LoRA adapter: {adapter_path} ...")
        _model = PeftModel.from_pretrained(_model, adapter_path)
        print("Adapter loaded.")
    else:
        print("No adapter loaded — running base model only.")

    if _device == "cpu":
        _model = _model.to("cpu")

    _model.eval()
    print("Model ready.")


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(title="EM-NS Model Server", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok", "device": str(_device)}


@app.post("/v1/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    if _model is None or _tokenizer is None:
        raise HTTPException(status_code=503, detail="Model not loaded")

    messages = [{"role": m.role, "content": m.content} for m in request.messages]

    try:
        input_text = _tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
    except Exception:
        # Fallback if chat template is not available
        parts = []
        for m in messages:
            parts.append(f"{m['role'].upper()}: {m['content']}")
        parts.append("ASSISTANT:")
        input_text = "\n".join(parts)

    inputs = _tokenizer(input_text, return_tensors="pt")
    input_ids = inputs["input_ids"].to(_model.device)
    attention_mask = inputs.get("attention_mask")
    if attention_mask is not None:
        attention_mask = attention_mask.to(_model.device)

    with torch.inference_mode():
        outputs = _model.generate(
            input_ids,
            attention_mask=attention_mask,
            max_new_tokens=request.max_new_tokens,
            temperature=request.temperature,
            top_p=request.top_p,
            do_sample=request.temperature > 0,
            pad_token_id=_tokenizer.pad_token_id,
        )

    # Only decode the newly generated tokens
    new_tokens = outputs[0][input_ids.shape[1]:]
    response_text = _tokenizer.decode(new_tokens, skip_special_tokens=True).strip()

    return ChatResponse(content=response_text)


@app.post("/v1/embeddings", response_model=EmbeddingResponse)
async def embeddings(request: EmbeddingRequest):
    if _model is None or _tokenizer is None:
        raise HTTPException(status_code=503, detail="Model not loaded")

    texts = request.input if isinstance(request.input, list) else [request.input]
    all_embeddings: list[list[float]] = []

    for text in texts:
        inputs = _tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
        input_ids = inputs["input_ids"].to(_model.device)
        attention_mask = inputs.get("attention_mask")
        if attention_mask is not None:
            attention_mask = attention_mask.to(_model.device)

        with torch.inference_mode():
            outputs = _model(input_ids=input_ids, attention_mask=attention_mask, output_hidden_states=True)

        # Use mean of last hidden state as embedding
        last_hidden = outputs.hidden_states[-1]
        if attention_mask is not None:
            mask = attention_mask.unsqueeze(-1).float()
            embedding = (last_hidden * mask).sum(dim=1) / mask.sum(dim=1)
        else:
            embedding = last_hidden.mean(dim=1)

        all_embeddings.append(embedding[0].cpu().tolist())

    return EmbeddingResponse(embeddings=all_embeddings)


# ---------------------------------------------------------------------------
# CLI entry
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Serve EM-NS model")
    parser.add_argument("--base-model", default="Qwen/Qwen2.5-1.5B-Instruct")
    parser.add_argument(
        "--adapter-path",
        default="training/artifacts/emns-chat-lora-v1",
        help="Path to LoRA adapter directory. Leave empty for base model only.",
    )
    parser.add_argument("--port", type=int, default=8001)
    parser.add_argument("--host", default="0.0.0.0")
    args = parser.parse_args()

    load_model(args.base_model, args.adapter_path)
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
