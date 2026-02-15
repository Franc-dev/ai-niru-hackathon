"""
LoRA/QLoRA training for EM-NS bilingual chat model.

Expected dataset format:
{"messages":[{"role":"system","content":"..."},{"role":"user","content":"..."},{"role":"assistant","content":"..."}], ...}
"""

from __future__ import annotations

import argparse
import json
import platform
from pathlib import Path

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-model", default="Qwen/Qwen2.5-3B-Instruct")
    parser.add_argument("--train-file", default="data/training/mentalchat_bilingual_train.jsonl")
    parser.add_argument("--eval-file", default="data/training/mentalchat_bilingual_val.jsonl")
    parser.add_argument("--output-dir", default="training/artifacts/emns-chat-lora-v1")
    parser.add_argument("--max-seq-length", type=int, default=1024)
    parser.add_argument("--num-epochs", type=float, default=2.0)
    parser.add_argument("--learning-rate", type=float, default=2e-4)
    parser.add_argument("--weight-decay", type=float, default=0.01)
    parser.add_argument("--warmup-ratio", type=float, default=0.03)
    parser.add_argument("--batch-size", type=int, default=2)
    parser.add_argument("--grad-accum", type=int, default=8)
    parser.add_argument("--logging-steps", type=int, default=20)
    parser.add_argument("--save-steps", type=int, default=200)
    parser.add_argument("--eval-steps", type=int, default=200)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--lora-r", type=int, default=16)
    parser.add_argument("--lora-alpha", type=int, default=32)
    parser.add_argument("--lora-dropout", type=float, default=0.05)
    parser.add_argument(
        "--target-modules",
        default="q_proj,k_proj,v_proj,o_proj,up_proj,down_proj,gate_proj",
        help="Comma-separated target modules or 'auto'.",
    )
    parser.add_argument("--max-train-samples", type=int, default=0)
    parser.add_argument("--max-eval-samples", type=int, default=0)
    parser.add_argument("--no-4bit", dest="use_4bit", action="store_false")
    parser.add_argument("--use-4bit", dest="use_4bit", action="store_true", default=True)
    parser.add_argument("--gradient-checkpointing", action="store_true", default=True)
    return parser.parse_args()


def resolve_dtype(torch_module):
    if not torch_module.cuda.is_available():
        return torch_module.float32
    if torch_module.cuda.is_bf16_supported():
        return torch_module.bfloat16
    return torch_module.float16


def maybe_parse_messages(messages: object) -> list[dict]:
    if isinstance(messages, str):
        return json.loads(messages)
    if isinstance(messages, list):
        return messages
    raise ValueError("Invalid messages field in dataset.")


def render_chat_text(tokenizer, messages: list[dict]) -> str:
    if tokenizer.chat_template:
        return tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=False,
        )
    lines = [f"{m.get('role', 'user').upper()}: {m.get('content', '')}" for m in messages]
    return "\n".join(lines)


def resolve_target_modules(model, configured: str) -> list[str]:
    if configured.strip().lower() != "auto":
        return [x.strip() for x in configured.split(",") if x.strip()]

    candidates = (
        "q_proj",
        "k_proj",
        "v_proj",
        "o_proj",
        "up_proj",
        "down_proj",
        "gate_proj",
        "c_attn",
        "c_proj",
        "fc_in",
        "fc_out",
    )
    found: set[str] = set()
    for name, _ in model.named_modules():
        for candidate in candidates:
            if name.endswith(candidate):
                found.add(candidate)
    if not found:
        raise ValueError("Could not auto-detect LoRA target modules. Pass --target-modules explicitly.")
    return sorted(found)


def build_text_dataset(dataset_path: str, tokenizer, max_records: int = 0):
    from datasets import load_dataset

    ds = load_dataset("json", data_files=dataset_path, split="train")
    if max_records > 0:
        ds = ds.select(range(min(max_records, len(ds))))

    def _format(example: dict) -> dict:
        messages = maybe_parse_messages(example["messages"])
        text = render_chat_text(tokenizer, messages)
        return {"text": text}

    ds = ds.map(_format, remove_columns=ds.column_names, desc=f"Formatting {Path(dataset_path).name}")
    return ds


def main() -> None:
    args = parse_args()

    import torch
    from peft import LoraConfig
    from transformers import (
        AutoModelForCausalLM,
        AutoTokenizer,
        BitsAndBytesConfig,
        TrainingArguments,
    )
    from trl import SFTTrainer

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    dtype = resolve_dtype(torch)
    use_4bit = args.use_4bit and torch.cuda.is_available() and platform.system() != "Windows"
    quantization_config = None
    if use_4bit:
        quantization_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_use_double_quant=True,
            bnb_4bit_compute_dtype=dtype,
        )

    tokenizer = AutoTokenizer.from_pretrained(args.base_model, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        args.base_model,
        trust_remote_code=True,
        torch_dtype=dtype,
        quantization_config=quantization_config,
        device_map="auto" if torch.cuda.is_available() else None,
    )
    model.config.use_cache = False

    train_ds = build_text_dataset(
        args.train_file,
        tokenizer=tokenizer,
        max_records=args.max_train_samples,
    )
    eval_ds = (
        build_text_dataset(
            args.eval_file,
            tokenizer=tokenizer,
            max_records=args.max_eval_samples,
        )
        if Path(args.eval_file).exists()
        else None
    )

    target_modules = resolve_target_modules(model, args.target_modules)

    lora_config = LoraConfig(
        r=args.lora_r,
        lora_alpha=args.lora_alpha,
        lora_dropout=args.lora_dropout,
        task_type="CAUSAL_LM",
        target_modules=target_modules,
    )

    training_args = TrainingArguments(
        output_dir=str(output_dir),
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=max(1, args.batch_size),
        gradient_accumulation_steps=args.grad_accum,
        learning_rate=args.learning_rate,
        num_train_epochs=args.num_epochs,
        weight_decay=args.weight_decay,
        warmup_ratio=args.warmup_ratio,
        lr_scheduler_type="cosine",
        logging_steps=args.logging_steps,
        save_steps=args.save_steps,
        eval_steps=args.eval_steps,
        eval_strategy="steps" if eval_ds is not None else "no",
        save_strategy="steps",
        bf16=(dtype == torch.bfloat16),
        fp16=(dtype == torch.float16),
        gradient_checkpointing=args.gradient_checkpointing,
        max_grad_norm=1.0,
        report_to="none",
        seed=args.seed,
        remove_unused_columns=False,
        optim="paged_adamw_8bit" if use_4bit else "adamw_torch",
    )

    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=train_ds,
        eval_dataset=eval_ds,
        peft_config=lora_config,
        dataset_text_field="text",
        max_seq_length=args.max_seq_length,
        packing=True,
        args=training_args,
    )

    trainer.train()
    trainer.save_model(str(output_dir))
    tokenizer.save_pretrained(str(output_dir))
    print(f"Saved adapter/model artifacts to {output_dir}")


if __name__ == "__main__":
    main()
