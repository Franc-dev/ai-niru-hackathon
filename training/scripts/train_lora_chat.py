"""Qwen LoRA fine-tuning for English MentalChat16K."""
from __future__ import annotations

import argparse
import platform
from pathlib import Path

from training.scripts.utils.chat_training import (
    build_assistant_only_dataset,
    resolve_dtype,
    resolve_target_modules,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fine-tune Qwen 2.5 on MentalChat16K")
    parser.add_argument("--base-model", default="Qwen/Qwen2.5-1.5B-Instruct")
    parser.add_argument("--train-file", default="data/training/mentalchat16k_en_train.jsonl")
    parser.add_argument("--eval-file", default="data/training/mentalchat16k_en_val.jsonl")
    parser.add_argument("--output-dir", default="training/artifacts/emns-qwen25-en-v1")
    parser.add_argument("--max-seq-length", type=int, default=2048)
    parser.add_argument("--batch-size", type=int, default=2)
    parser.add_argument("--grad-accum", type=int, default=4)
    parser.add_argument("--num-epochs", type=int, default=1)
    parser.add_argument("--learning-rate", type=float, default=2e-4)
    parser.add_argument("--logging-steps", type=int, default=10)
    parser.add_argument("--save-steps", type=int, default=100)
    parser.add_argument("--max-records", type=int, default=0)
    parser.add_argument("--seed", type=int, default=3407)
    parser.add_argument("--no-4bit", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    import torch
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
    from transformers import (
        AutoModelForCausalLM,
        AutoTokenizer,
        BitsAndBytesConfig,
        Trainer,
        TrainingArguments,
    )

    dtype = resolve_dtype(torch)
    use_4bit = torch.cuda.is_available() and not args.no_4bit and platform.system() != "Windows"

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

    if use_4bit:
        model = prepare_model_for_kbit_training(model)

    model = get_peft_model(
        model,
        LoraConfig(
            r=128,
            lora_alpha=128,
            lora_dropout=0.0,
            bias="none",
            task_type="CAUSAL_LM",
            target_modules=resolve_target_modules(model),
        ),
    )

    train_ds = build_assistant_only_dataset(
        args.train_file,
        tokenizer,
        max_records=args.max_records,
        max_seq_length=args.max_seq_length,
    )
    eval_ds = (
        build_assistant_only_dataset(
            args.eval_file,
            tokenizer,
            max_records=args.max_records,
            max_seq_length=args.max_seq_length,
        )
        if Path(args.eval_file).exists()
        else None
    )

    def collate_supervised_batch(features: list[dict[str, list[int]]]) -> dict[str, torch.Tensor]:
        pad_multiple = 8 if torch.cuda.is_available() else 1
        max_length = max(len(feature["input_ids"]) for feature in features)
        if max_length % pad_multiple:
            max_length = ((max_length // pad_multiple) + 1) * pad_multiple

        input_ids: list[list[int]] = []
        attention_masks: list[list[int]] = []
        labels: list[list[int]] = []

        for feature in features:
            pad_length = max_length - len(feature["input_ids"])
            input_ids.append(feature["input_ids"] + [tokenizer.pad_token_id] * pad_length)
            attention_masks.append(feature["attention_mask"] + [0] * pad_length)
            labels.append(feature["labels"] + [-100] * pad_length)

        return {
            "input_ids": torch.tensor(input_ids, dtype=torch.long),
            "attention_mask": torch.tensor(attention_masks, dtype=torch.long),
            "labels": torch.tensor(labels, dtype=torch.long),
        }

    training_args = TrainingArguments(
        output_dir=args.output_dir,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=max(1, args.batch_size),
        gradient_accumulation_steps=args.grad_accum,
        warmup_steps=5,
        num_train_epochs=args.num_epochs,
        learning_rate=args.learning_rate,
        logging_steps=args.logging_steps,
        save_steps=args.save_steps,
        save_strategy="steps",
        evaluation_strategy="steps" if eval_ds is not None else "no",
        eval_steps=args.save_steps,
        optim="paged_adamw_8bit" if use_4bit else "adamw_torch",
        weight_decay=0.01,
        lr_scheduler_type="linear",
        seed=args.seed,
        report_to="none",
        bf16=dtype == torch.bfloat16,
        fp16=dtype == torch.float16,
        gradient_checkpointing=True,
        remove_unused_columns=False,
    )

    trainer = Trainer(
        model=model,
        train_dataset=train_ds,
        eval_dataset=eval_ds,
        args=training_args,
        data_collator=collate_supervised_batch,
    )

    trainer_stats = trainer.train()
    print(trainer_stats)
    trainer.save_model(args.output_dir)
    tokenizer.save_pretrained(args.output_dir)


if __name__ == "__main__":
    main()
