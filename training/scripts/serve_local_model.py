"""Serve MentalChat-16K or any HuggingFace model behind the local-model contract."""
from __future__ import annotations

import argparse
import platform
from pathlib import Path
from functools import lru_cache
from typing import Literal

import torch
import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel, Field
from sentence_transformers import SentenceTransformer
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

# Default: use local MentalChat-16K if present, else HuggingFace ID
_DEFAULT_MODEL = "MentalChat-16K"
if not (Path(__file__).resolve().parent.parent.parent / _DEFAULT_MODEL / "config.json").exists():
    _DEFAULT_MODEL = "khazarai/MentalChat-16K"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Serve MentalChat-16K or another model locally")
    parser.add_argument("--model-id", default=_DEFAULT_MODEL)
    parser.add_argument("--adapter-path", default="")
    parser.add_argument("--embedding-model", default="sentence-transformers/all-MiniLM-L6-v2")
    parser.add_argument("--port", type=int, default=8002)
    parser.add_argument("--no-4bit", action="store_true")
    return parser.parse_args()


class Message(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    messages: list[Message]
    max_new_tokens: int = Field(default=220, ge=1, le=768)
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    top_p: float = Field(default=0.9, ge=0.0, le=1.0)
    repetition_penalty: float = Field(default=1.08, ge=1.0, le=2.0)


class ChatResponse(BaseModel):
    content: str
    model: str


class EmbeddingRequest(BaseModel):
    input: list[str] | str | None = None
    texts: list[str] | None = None


class EmbeddingResponse(BaseModel):
    data: list[dict]
    model: str


def _resolve_dtype() -> torch.dtype:
    if torch.cuda.is_available():
        if hasattr(torch.cuda, "is_bf16_supported") and torch.cuda.is_bf16_supported():
            return torch.bfloat16
        return torch.float16
    return torch.float32


def _load_model(model_id: str, adapter_path: str, no_4bit: bool):
    dtype = _resolve_dtype()
    use_4bit = torch.cuda.is_available() and not no_4bit and platform.system() != "Windows"

    quantization_config = None
    if use_4bit:
        quantization_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_use_double_quant=True,
            bnb_4bit_compute_dtype=dtype,
        )

    tokenizer = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        model_id,
        trust_remote_code=True,
        torch_dtype=dtype,
        quantization_config=quantization_config,
        device_map="auto" if torch.cuda.is_available() else None,
    )

    if adapter_path:
        from peft import PeftModel

        model = PeftModel.from_pretrained(model, adapter_path)

    model.eval()
    return tokenizer, model


@lru_cache(maxsize=1)
def _embedding_model(model_name: str):
    return SentenceTransformer(model_name)


def create_app(args: argparse.Namespace) -> FastAPI:
    tokenizer, model = _load_model(args.model_id, args.adapter_path, args.no_4bit)
    app = FastAPI(title="MentalChat-16K Model Server")

    @app.get("/health")
    async def health():
        return {
            "status": "healthy",
            "model_id": args.model_id,
            "adapter_loaded": bool(args.adapter_path),
            "embedding_model": args.embedding_model,
        }

    @app.post("/v1/chat", response_model=ChatResponse)
    async def chat(request: ChatRequest):
        prompt = tokenizer.apply_chat_template(
            [message.model_dump() for message in request.messages if message.content.strip()],
            tokenize=False,
            add_generation_prompt=True,
        )
        inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
        do_sample = request.temperature > 0

        generate_kwargs = {
            "max_new_tokens": request.max_new_tokens,
            "do_sample": do_sample,
            "repetition_penalty": request.repetition_penalty,
            "pad_token_id": tokenizer.pad_token_id,
            "eos_token_id": tokenizer.eos_token_id,
        }
        if do_sample:
            generate_kwargs["temperature"] = max(request.temperature, 1e-5)
            generate_kwargs["top_p"] = request.top_p

        with torch.no_grad():
            outputs = model.generate(**inputs, **generate_kwargs)

        generated = outputs[0][inputs["input_ids"].shape[-1] :]
        content = tokenizer.decode(generated, skip_special_tokens=True).strip()
        return ChatResponse(content=content, model=args.model_id)

    @app.post("/v1/embeddings", response_model=EmbeddingResponse)
    async def embeddings(request: EmbeddingRequest):
        texts = request.texts or request.input or []
        if isinstance(texts, str):
            texts = [texts]
        clean_texts = [str(text).strip() for text in texts if str(text).strip()]
        vectors = _embedding_model(args.embedding_model).encode(clean_texts).tolist()
        return EmbeddingResponse(
            data=[{"index": index, "embedding": vector} for index, vector in enumerate(vectors)],
            model=args.embedding_model,
        )

    return app


def main() -> None:
    args = parse_args()
    uvicorn.run(create_app(args), host="0.0.0.0", port=args.port)


if __name__ == "__main__":
    main()
