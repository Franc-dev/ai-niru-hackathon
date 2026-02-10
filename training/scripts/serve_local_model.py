"""
Local model gateway for backend compatibility.

Provides:
- POST /v1/chat
- POST /v1/embeddings
- GET /health
"""

from __future__ import annotations

import argparse
import asyncio
from dataclasses import dataclass
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[Message]
    max_new_tokens: int = Field(default=256, ge=1, le=2048)
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    top_p: float = Field(default=0.95, ge=0.1, le=1.0)


class EmbeddingRequest(BaseModel):
    input: str | list[str]


@dataclass
class State:
    model_id: str
    adapter_path: str
    embedding_model_id: str
    torch_module: Any = None
    chat_model: Any = None
    tokenizer: Any = None
    embedder: Any = None
    device: str = "cpu"


def create_app(state: State) -> FastAPI:
    app = FastAPI(title="EM-NS Local Model Gateway")
    lock = asyncio.Lock()

    @app.get("/health")
    async def health() -> dict:
        return {
            "status": "ok",
            "chat_model": state.model_id,
            "adapter_path": state.adapter_path,
            "embedding_model": state.embedding_model_id,
            "device": state.device,
        }

    @app.post("/v1/chat")
    async def chat(request: ChatRequest) -> dict:
        if state.chat_model is None or state.tokenizer is None:
            raise HTTPException(status_code=503, detail="Chat model not loaded.")

        try:
            async with lock:
                prompt = build_prompt(state.tokenizer, request.messages)
                inputs = state.tokenizer(prompt, return_tensors="pt")
                inputs = {k: v.to(state.device) for k, v in inputs.items()}
                input_len = inputs["input_ids"].shape[1]

                with state.torch_module.inference_mode():
                    generated = state.chat_model.generate(
                        **inputs,
                        max_new_tokens=request.max_new_tokens,
                        do_sample=request.temperature > 0,
                        temperature=max(request.temperature, 1e-5),
                        top_p=request.top_p,
                        eos_token_id=state.tokenizer.eos_token_id,
                        pad_token_id=state.tokenizer.eos_token_id,
                    )

                output_tokens = generated[0][input_len:]
                content = state.tokenizer.decode(output_tokens, skip_special_tokens=True).strip()
            return {"content": content}
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc))

    @app.post("/v1/embeddings")
    async def embeddings(request: EmbeddingRequest) -> dict:
        if state.embedder is None:
            raise HTTPException(status_code=503, detail="Embedding model not loaded.")

        texts = request.input if isinstance(request.input, list) else [request.input]
        if not texts:
            return {"embeddings": []}

        vectors = state.embedder.encode(
            texts,
            normalize_embeddings=True,
            convert_to_numpy=True,
            batch_size=16,
        )
        return {"embeddings": vectors.tolist()}

    return app


def build_prompt(tokenizer, messages: list[Message]) -> str:
    msg_dicts = [{"role": m.role, "content": m.content} for m in messages]
    if tokenizer.chat_template:
        return tokenizer.apply_chat_template(
            msg_dicts,
            tokenize=False,
            add_generation_prompt=True,
        )
    prompt_lines = []
    for m in msg_dicts:
        prompt_lines.append(f"{m['role'].upper()}: {m['content']}")
    prompt_lines.append("ASSISTANT:")
    return "\n".join(prompt_lines)


def load_state(args: argparse.Namespace) -> State:
    import torch
    from sentence_transformers import SentenceTransformer
    from transformers import AutoModelForCausalLM, AutoTokenizer

    try:
        from peft import PeftModel
    except Exception:  # pragma: no cover
        PeftModel = None

    device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.bfloat16 if torch.cuda.is_available() and torch.cuda.is_bf16_supported() else torch.float16
    if not torch.cuda.is_available():
        dtype = torch.float32

    tokenizer = AutoTokenizer.from_pretrained(args.model_id, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    chat_model = AutoModelForCausalLM.from_pretrained(
        args.model_id,
        trust_remote_code=True,
        torch_dtype=dtype,
        device_map="auto" if torch.cuda.is_available() else None,
    )
    if args.adapter_path:
        if PeftModel is None:
            raise RuntimeError("peft is required when --adapter-path is set.")
        chat_model = PeftModel.from_pretrained(chat_model, args.adapter_path)
    chat_model.eval()
    if device == "cpu":
        chat_model.to(device)

    embedder = SentenceTransformer(args.embedding_model_id, device=device)

    return State(
        model_id=args.model_id,
        adapter_path=args.adapter_path,
        embedding_model_id=args.embedding_model_id,
        torch_module=torch,
        chat_model=chat_model,
        tokenizer=tokenizer,
        embedder=embedder,
        device=device,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-id", default="Qwen/Qwen2.5-3B-Instruct")
    parser.add_argument("--adapter-path", default="")
    parser.add_argument("--embedding-model-id", default="intfloat/multilingual-e5-base")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8001)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    state = load_state(args)
    app = create_app(state)
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
