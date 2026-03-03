"""
Swahili Mental Health LoRA Training with Mistral-7B-Instruct

Optimized for Windows with RTX 4050 (6GB VRAM) using 4-bit quantization.
Dataset: franmwan/swahili-Mental-Health from HuggingFace

Usage:
    python train_swahili_mistral.py --output-dir training/artifacts/emns-swahili-mistral-v1
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Set environment variables before importing torch
os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train Swahili Mental Health Model with Mistral-7B")
    
    # Model settings
    parser.add_argument(
        "--base-model", 
        default="TinyLlama/TinyLlama-1.1B-Chat-v1.0",
        help="Base model from HuggingFace (TinyLlama is fast and stable)"
    )
    
    # Dataset settings
    parser.add_argument("--dataset", default="franmwan/swahili-Mental-Health", help="HuggingFace dataset name")
    parser.add_argument("--dataset-split", default="train", help="Dataset split to use")
    parser.add_argument("--output-dir", default="training/artifacts/emns-swahili-mistral-v1")
    
    # Training hyperparameters - optimized for 6GB VRAM
    parser.add_argument("--max-seq-length", type=int, default=512, help="Max sequence length (lower = less VRAM)")
    parser.add_argument("--num-epochs", type=float, default=3.0, help="Number of training epochs")
    parser.add_argument("--learning-rate", type=float, default=2e-4, help="Learning rate")
    parser.add_argument("--weight-decay", type=float, default=0.01)
    parser.add_argument("--warmup-ratio", type=float, default=0.03)
    parser.add_argument("--batch-size", type=int, default=1, help="Batch size (1 for 6GB VRAM)")
    parser.add_argument("--grad-accum", type=int, default=16, help="Gradient accumulation steps")
    parser.add_argument("--logging-steps", type=int, default=10)
    parser.add_argument("--save-steps", type=int, default=100)
    parser.add_argument("--eval-steps", type=int, default=100)
    parser.add_argument("--seed", type=int, default=42)
    
    # LoRA settings
    parser.add_argument("--lora-r", type=int, default=16, help="LoRA rank")
    parser.add_argument("--lora-alpha", type=int, default=32, help="LoRA alpha")
    parser.add_argument("--lora-dropout", type=float, default=0.05)
    parser.add_argument(
        "--target-modules",
        default="q_proj,k_proj,v_proj,o_proj,gate_proj,up_proj,down_proj",
        help="Target modules for LoRA"
    )
    
    # Quantization settings
    parser.add_argument("--use-4bit", action="store_true", default=True, help="Use 4-bit quantization")
    parser.add_argument("--no-4bit", dest="use_4bit", action="store_false")
    parser.add_argument("--gradient-checkpointing", action="store_true", default=True)
    
    # Dataset limits (for testing)
    parser.add_argument("--max-train-samples", type=int, default=0, help="Limit training samples (0 = all)")
    parser.add_argument("--max-eval-samples", type=int, default=0, help="Limit eval samples (0 = all)")
    parser.add_argument("--train-ratio", type=float, default=0.9, help="Train/validation split ratio")
    
    return parser.parse_args()


# Swahili system prompt for mental health assistant
SWAHILI_SYSTEM_PROMPT = """Wewe ni msaidizi wa afya ya akili (si daktari).
Jibu kwa Kiswahili sanifu pekee - USITUMIE Kiingereza hata neno moja.
Toa majibu mafupi, wazi, yenye huruma.
Toa hatua 3-6 zinazoweza kufanywa sasa.
Usitoe utambuzi wa kitabibu wala dawa.
Ikiwa swali si la afya ya akili, elekeza mazungumzo kurudi kwenye hisia au ustawi wa kihemko.
Ikiwa kuna dalili za hatari ya kujidhuru au kujiua, himiza msaada wa haraka."""


def clean_text(text: str) -> str:
    """Clean and normalize text."""
    if not text:
        return ""
    text = text.replace("\r\n", "\n").strip()
    text = " ".join(text.split())  # Normalize whitespace
    return text.strip()


def format_conversation(example: dict, tokenizer) -> dict:
    """Format a single example into chat format for Mistral."""
    instruction = clean_text(example.get("instruction", "")) or SWAHILI_SYSTEM_PROMPT
    user_input = clean_text(example.get("input", ""))
    assistant_output = clean_text(example.get("output", ""))
    
    if not user_input or not assistant_output:
        return {"text": ""}
    
    # Build messages in Mistral chat format
    messages = [
        {"role": "system", "content": instruction},
        {"role": "user", "content": user_input},
        {"role": "assistant", "content": assistant_output}
    ]
    
    # Apply chat template
    if hasattr(tokenizer, 'apply_chat_template') and tokenizer.chat_template:
        try:
            text = tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=False
            )
        except Exception:
            # Fallback format
            text = f"[INST] {instruction}\n\n{user_input} [/INST] {assistant_output}"
    else:
        # Mistral instruction format fallback
        text = f"[INST] {instruction}\n\n{user_input} [/INST] {assistant_output}"
    
    return {"text": text}


def resolve_dtype(torch_module):
    """Determine optimal dtype for the hardware."""
    if not torch_module.cuda.is_available():
        return torch_module.float32
    if torch_module.cuda.is_bf16_supported():
        return torch_module.bfloat16
    return torch_module.float16


def main() -> None:
    args = parse_args()
    
    print("=" * 60)
    print("EMNS Swahili Mental Health Model Training")
    print("=" * 60)
    print(f"Base Model: {args.base_model}")
    print(f"Dataset: {args.dataset}")
    print(f"Output: {args.output_dir}")
    print("=" * 60)
    
    # Import heavy libraries after argument parsing
    import torch
    from datasets import load_dataset
    from peft import LoraConfig, TaskType, prepare_model_for_kbit_training
    from transformers import (
        AutoModelForCausalLM,
        AutoTokenizer,
        BitsAndBytesConfig,
        TrainingArguments,
    )
    from trl import SFTTrainer, SFTConfig
    
    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Determine compute dtype
    dtype = resolve_dtype(torch)
    print(f"\nCompute dtype: {dtype}")
    print(f"CUDA available: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"GPU: {torch.cuda.get_device_name(0)}")
        print(f"VRAM: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")
    
    # Configure 4-bit quantization for Windows (no bitsandbytes, use native)
    quantization_config = None
    if args.use_4bit and torch.cuda.is_available():
        try:
            quantization_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_use_double_quant=True,
                bnb_4bit_compute_dtype=dtype,
            )
            print("Using 4-bit quantization")
        except Exception as e:
            print(f"Warning: 4-bit quantization not available ({e})")
            print("Falling back to float16/bfloat16")
            quantization_config = None
    
    # Load tokenizer
    print(f"\nLoading tokenizer from {args.base_model}...")
    tokenizer = AutoTokenizer.from_pretrained(
        args.base_model,
        trust_remote_code=True,
        use_fast=True,
    )
    
    # Set padding token
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
        tokenizer.pad_token_id = tokenizer.eos_token_id
    
    # Load model
    print(f"\nLoading model from {args.base_model}...")
    print("This may take a few minutes for the first download...")
    
    model_kwargs = {
        "trust_remote_code": True,
        "torch_dtype": dtype,
        "device_map": "auto" if torch.cuda.is_available() else None,
        "low_cpu_mem_usage": True,
        "attn_implementation": "eager",  # Avoid flash attention issues
    }
    
    if quantization_config:
        model_kwargs["quantization_config"] = quantization_config
    
    # For Phi-3, use a specific revision that works
    if "Phi-3" in args.base_model or "phi-3" in args.base_model.lower():
        model_kwargs["revision"] = "main"
    
    model = AutoModelForCausalLM.from_pretrained(
        args.base_model,
        **model_kwargs
    )
    model.config.use_cache = False
    
    # Prepare model for k-bit training if using quantization
    if quantization_config:
        model = prepare_model_for_kbit_training(model)
    
    # Enable gradient checkpointing
    if args.gradient_checkpointing:
        model.gradient_checkpointing_enable()
    
    # Load and prepare dataset
    print(f"\nLoading dataset: {args.dataset}...")
    dataset = load_dataset(args.dataset, split=args.dataset_split)
    print(f"Loaded {len(dataset)} examples")
    
    # Split into train/validation
    dataset = dataset.train_test_split(
        test_size=1 - args.train_ratio,
        seed=args.seed
    )
    train_dataset = dataset["train"]
    eval_dataset = dataset["test"]
    
    # Limit samples if requested
    if args.max_train_samples > 0:
        train_dataset = train_dataset.select(range(min(args.max_train_samples, len(train_dataset))))
    if args.max_eval_samples > 0:
        eval_dataset = eval_dataset.select(range(min(args.max_eval_samples, len(eval_dataset))))
    
    print(f"Training samples: {len(train_dataset)}")
    print(f"Validation samples: {len(eval_dataset)}")
    
    # Format datasets
    print("\nFormatting datasets...")
    train_dataset = train_dataset.map(
        lambda x: format_conversation(x, tokenizer),
        remove_columns=train_dataset.column_names,
        desc="Formatting train"
    )
    eval_dataset = eval_dataset.map(
        lambda x: format_conversation(x, tokenizer),
        remove_columns=eval_dataset.column_names,
        desc="Formatting eval"
    )
    
    # Filter empty examples
    train_dataset = train_dataset.filter(lambda x: len(x["text"]) > 0)
    eval_dataset = eval_dataset.filter(lambda x: len(x["text"]) > 0)
    
    print(f"After filtering - Train: {len(train_dataset)}, Eval: {len(eval_dataset)}")
    
    # Show sample
    if len(train_dataset) > 0:
        print("\n--- Sample training example ---")
        print(train_dataset[0]["text"][:500] + "...")
        print("--- End sample ---\n")
    
    # Configure LoRA
    target_modules = [m.strip() for m in args.target_modules.split(",")]
    
    lora_config = LoraConfig(
        r=args.lora_r,
        lora_alpha=args.lora_alpha,
        lora_dropout=args.lora_dropout,
        task_type=TaskType.CAUSAL_LM,
        target_modules=target_modules,
        bias="none",
    )
    print(f"\nLoRA config: r={args.lora_r}, alpha={args.lora_alpha}, targets={target_modules}")
    
    # Training arguments - use TrainingArguments for compatibility
    from transformers import TrainingArguments
    
    training_args = TrainingArguments(
        output_dir=str(output_dir),
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size,
        gradient_accumulation_steps=args.grad_accum,
        learning_rate=args.learning_rate,
        num_train_epochs=args.num_epochs,
        weight_decay=args.weight_decay,
        warmup_ratio=args.warmup_ratio,
        lr_scheduler_type="cosine",
        logging_steps=args.logging_steps,
        save_steps=args.save_steps,
        eval_steps=args.eval_steps,
        eval_strategy="steps",
        save_strategy="steps",
        save_total_limit=3,
        bf16=(dtype == torch.bfloat16),
        fp16=(dtype == torch.float16),
        gradient_checkpointing=args.gradient_checkpointing,
        gradient_checkpointing_kwargs={"use_reentrant": False} if args.gradient_checkpointing else None,
        max_grad_norm=1.0,
        report_to="none",
        seed=args.seed,
        optim="adamw_torch",
        dataloader_pin_memory=False,
        remove_unused_columns=False,
    )
    
    # Create trainer - handle different trl versions
    print("\nInitializing trainer...")
    
    trainer_kwargs = {
        "model": model,
        "train_dataset": train_dataset,
        "eval_dataset": eval_dataset,
        "peft_config": lora_config,
        "args": training_args,
    }
    
    # Try different argument names for different trl versions
    try:
        # Newer trl versions use processing_class
        trainer = SFTTrainer(
            **trainer_kwargs,
            processing_class=tokenizer,
        )
    except TypeError:
        # Older trl versions use tokenizer
        trainer = SFTTrainer(
            **trainer_kwargs,
            tokenizer=tokenizer,
            max_seq_length=args.max_seq_length,
            dataset_text_field="text",
            packing=False,
        )
    
    # Print trainable parameters
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total_params = sum(p.numel() for p in model.parameters())
    print(f"\nTrainable parameters: {trainable_params:,} ({100 * trainable_params / total_params:.2f}%)")
    print(f"Total parameters: {total_params:,}")
    
    # Start training
    print("\n" + "=" * 60)
    print("Starting training...")
    print("=" * 60 + "\n")
    
    try:
        trainer.train()
        
        # Save the model
        print(f"\nSaving model to {output_dir}...")
        trainer.save_model(str(output_dir))
        tokenizer.save_pretrained(str(output_dir))
        
        # Save training config
        config = {
            "base_model": args.base_model,
            "dataset": args.dataset,
            "num_epochs": args.num_epochs,
            "learning_rate": args.learning_rate,
            "batch_size": args.batch_size,
            "grad_accum": args.grad_accum,
            "max_seq_length": args.max_seq_length,
            "lora_r": args.lora_r,
            "lora_alpha": args.lora_alpha,
            "target_modules": target_modules,
            "train_samples": len(train_dataset),
            "eval_samples": len(eval_dataset),
            "trained_at": datetime.now(timezone.utc).isoformat(),
            "system_prompt": SWAHILI_SYSTEM_PROMPT,
        }
        
        config_path = output_dir / "training_config.json"
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        
        print(f"\nTraining complete!")
        print(f"Model saved to: {output_dir}")
        print(f"Config saved to: {config_path}")
        
    except Exception as e:
        print(f"\nTraining failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
