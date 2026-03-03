"""
Serve the EM-NS Swahili Mental Health LoRA model as an HTTP API.

This is specifically for the Swahili Mistral-7B model.

Endpoints:
  POST /v1/chat       -> {"content": "..."}
  GET  /health        -> {"status": "ok"}

Usage:
  python training/scripts/serve_swahili_model.py
  python training/scripts/serve_swahili_model.py --adapter-path training/artifacts/emns-swahili-mistral-v1 --port 8002
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# Set memory optimization before importing torch
os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"

import torch
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Swahili System Prompt (from AGENTS.md)
# ---------------------------------------------------------------------------

SWAHILI_SYSTEM_PROMPT = """Wewe ni msaidizi wa afya ya akili (si daktari).
Jibu kwa Kiswahili sanifu pekee - USITUMIE Kiingereza hata neno moja.
Toa majibu mafupi, wazi, yenye huruma.
Toa hatua 3-6 zinazoweza kufanywa sasa.
Usitoe utambuzi wa kitabibu wala dawa.
Ikiwa swali si la afya ya akili, elekeza mazungumzo kurudi kwenye hisia au ustawi wa kihemko.
Ikiwa kuna dalili za hatari ya kujidhuru au kujiua, himiza msaada wa haraka."""


# ---------------------------------------------------------------------------
# Request/response schemas
# ---------------------------------------------------------------------------

class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    max_new_tokens: int = 180
    temperature: float = 0.0
    top_p: float = 0.9
    repetition_penalty: float = 1.1


class ChatResponse(BaseModel):
    content: str


# ---------------------------------------------------------------------------
# Global model state
# ---------------------------------------------------------------------------

_model = None
_tokenizer = None
_device = None
_config = {}


def load_model(base_model: str, adapter_path: str | None, use_4bit: bool = True) -> None:
    """Load the model with optional LoRA adapter."""
    global _model, _tokenizer, _device, _config
    
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    from peft import PeftModel
    
    _device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Device: {_device}")
    
    if torch.cuda.is_available():
        print(f"GPU: {torch.cuda.get_device_name(0)}")
        print(f"VRAM: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")
    
    # Check for training config in adapter path
    if adapter_path:
        config_path = Path(adapter_path) / "training_config.json"
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                _config = json.load(f)
            base_model = _config.get("base_model", base_model)
            print(f"Loaded training config, using base model: {base_model}")
    
    # Load tokenizer
    print(f"Loading tokenizer: {base_model}")
    _tokenizer = AutoTokenizer.from_pretrained(base_model, trust_remote_code=True)
    if _tokenizer.pad_token is None:
        _tokenizer.pad_token = _tokenizer.eos_token
    
    # Determine dtype
    dtype = torch.float32
    if torch.cuda.is_available():
        dtype = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
    
    # Configure quantization
    quantization_config = None
    if use_4bit and torch.cuda.is_available():
        try:
            quantization_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_use_double_quant=True,
                bnb_4bit_compute_dtype=dtype,
            )
            print("Using 4-bit quantization")
        except Exception as e:
            print(f"4-bit quantization not available: {e}")
    
    # Load base model
    print(f"Loading model: {base_model}")
    model_kwargs = {
        "trust_remote_code": True,
        "torch_dtype": dtype,
        "device_map": "auto" if torch.cuda.is_available() else None,
        "low_cpu_mem_usage": True,
    }
    if quantization_config:
        model_kwargs["quantization_config"] = quantization_config
    
    _model = AutoModelForCausalLM.from_pretrained(base_model, **model_kwargs)
    
    # Load LoRA adapter if available
    if adapter_path and Path(adapter_path).exists():
        adapter_config = Path(adapter_path) / "adapter_config.json"
        if adapter_config.exists():
            print(f"Loading LoRA adapter: {adapter_path}")
            _model = PeftModel.from_pretrained(_model, adapter_path)
            print("Adapter loaded successfully!")
        else:
            print(f"No adapter_config.json found in {adapter_path}, using base model")
    else:
        print("No adapter path provided or path doesn't exist, using base model only")
    
    _model.eval()
    print("Model ready for inference!")


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(
    title="EM-NS Swahili Mental Health Model",
    description="Swahili mental health support assistant powered by Mistral-7B + LoRA",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "ok",
        "device": str(_device),
        "model_loaded": _model is not None,
        "config": _config,
    }


@app.post("/v1/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Generate a response to a chat message."""
    if _model is None or _tokenizer is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    # Build messages - inject system prompt if not present
    messages = []
    has_system = any(m.role == "system" for m in request.messages)
    
    if not has_system:
        messages.append({"role": "system", "content": SWAHILI_SYSTEM_PROMPT})
    
    for m in request.messages:
        messages.append({"role": m.role, "content": m.content})
    
    # Apply chat template
    try:
        if hasattr(_tokenizer, 'apply_chat_template') and _tokenizer.chat_template:
            input_text = _tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True
            )
        else:
            # Mistral format fallback
            system_msg = messages[0]["content"] if messages[0]["role"] == "system" else ""
            user_msgs = [m["content"] for m in messages if m["role"] == "user"]
            user_text = user_msgs[-1] if user_msgs else ""
            input_text = f"[INST] {system_msg}\n\n{user_text} [/INST]"
    except Exception as e:
        print(f"Error applying chat template: {e}")
        # Ultimate fallback
        parts = [f"{m['role'].upper()}: {m['content']}" for m in messages]
        parts.append("ASSISTANT:")
        input_text = "\n".join(parts)
    
    # Tokenize
    inputs = _tokenizer(input_text, return_tensors="pt")
    input_ids = inputs["input_ids"].to(_model.device)
    attention_mask = inputs.get("attention_mask")
    if attention_mask is not None:
        attention_mask = attention_mask.to(_model.device)
    
    # Generation parameters
    do_sample = request.temperature > 0
    gen_kwargs = {
        "max_new_tokens": request.max_new_tokens,
        "pad_token_id": _tokenizer.pad_token_id,
        "eos_token_id": _tokenizer.eos_token_id,
        "repetition_penalty": request.repetition_penalty,
        "do_sample": do_sample,
    }
    if do_sample:
        gen_kwargs["temperature"] = request.temperature
        gen_kwargs["top_p"] = request.top_p
    
    # Generate
    with torch.inference_mode():
        outputs = _model.generate(
            input_ids,
            attention_mask=attention_mask,
            **gen_kwargs,
        )
    
    # Decode only the new tokens
    new_tokens = outputs[0][input_ids.shape[1]:]
    response_text = _tokenizer.decode(new_tokens, skip_special_tokens=True).strip()
    
    return ChatResponse(content=response_text)


@app.post("/v1/swahili/chat", response_model=ChatResponse)
async def swahili_chat(request: ChatRequest):
    """Alias for /v1/chat - explicitly for Swahili."""
    return await chat(request)


# ---------------------------------------------------------------------------
# CLI entry
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Serve EM-NS Swahili model")
    parser.add_argument(
        "--base-model",
        default="microsoft/Phi-3-mini-4k-instruct",
        help="Base model (Phi-3-mini is fast and good for Swahili)",
    )
    parser.add_argument(
        "--adapter-path",
        default="training/artifacts/emns-swahili-phi3-v1",
        help="Path to LoRA adapter directory",
    )
    parser.add_argument("--port", type=int, default=8002)
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--no-4bit", dest="use_4bit", action="store_false", default=True)
    args = parser.parse_args()
    
    print("=" * 60)
    print("EM-NS Swahili Mental Health Model Server")
    print("=" * 60)
    
    load_model(args.base_model, args.adapter_path, args.use_4bit)
    
    print(f"\nStarting server on http://{args.host}:{args.port}")
    print("Endpoints:")
    print(f"  POST http://localhost:{args.port}/v1/chat")
    print(f"  GET  http://localhost:{args.port}/health")
    print("=" * 60)
    
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
