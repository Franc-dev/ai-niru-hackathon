"""
Determined AI training entrypoint for EM-NS LoRA fine-tuning.

Uses Determined's DetCallback (HuggingFace Trainer integration) to report
metrics, manage checkpoints, and coordinate with the ASHA searcher.

Reuses helper functions from training/scripts/train_lora_chat.py.
"""

from __future__ import annotations

import math
import platform
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Make project helpers importable
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from training.scripts.train_lora_chat import (
    build_text_dataset,
    maybe_parse_messages,
    render_chat_text,
    resolve_dtype,
    resolve_target_modules,
)


def build_filtered_dataset(
    dataset_path: str,
    tokenizer,
    language_filter: str = "en",
    max_records: int = 0,
):
    """Load dataset and optionally filter by language before formatting.

    Args:
        dataset_path: Path to JSONL file.
        tokenizer: HuggingFace tokenizer for chat template rendering.
        language_filter: "en", "sw", or "all" (no filter).
        max_records: Limit number of records (0 = no limit).
    """
    from datasets import load_dataset

    ds = load_dataset("json", data_files=dataset_path, split="train")

    # Filter by language if requested
    if language_filter and language_filter != "all":
        ds = ds.filter(lambda x: x.get("language", "en") == language_filter)

    if max_records > 0:
        ds = ds.select(range(min(max_records, len(ds))))

    def _format(example: dict) -> dict:
        messages = maybe_parse_messages(example["messages"])
        text = render_chat_text(tokenizer, messages)
        return {"text": text}

    ds = ds.map(
        _format,
        remove_columns=ds.column_names,
        desc=f"Formatting {Path(dataset_path).name} (lang={language_filter})",
    )
    return ds


def main() -> None:
    import determined as det
    import torch
    from determined.transformers import DetCallback
    from peft import LoraConfig
    from transformers import (
        AutoModelForCausalLM,
        AutoTokenizer,
        BitsAndBytesConfig,
        TrainingArguments,
    )
    from trl import SFTTrainer

    # ------------------------------------------------------------------
    # Determined context & hyperparameters
    # ------------------------------------------------------------------
    info = det.get_cluster_info()
    assert info is not None, "This script must run inside a Determined experiment"
    hparams = info.trial.hparams

    base_model = hparams.get("base_model", "Qwen/Qwen2.5-1.5B-Instruct")
    lora_r = int(hparams.get("lora_r", 16))
    lora_alpha = int(hparams.get("lora_alpha", 32))
    lora_dropout = float(hparams.get("lora_dropout", 0.05))
    learning_rate = float(hparams.get("learning_rate", 2e-4))
    batch_size = int(hparams.get("batch_size", 2))
    grad_accum = int(hparams.get("grad_accum", 8))
    warmup_ratio = float(hparams.get("warmup_ratio", 0.03))
    weight_decay = float(hparams.get("weight_decay", 0.01))
    num_epochs = float(hparams.get("num_epochs", 2))
    max_seq_length = int(hparams.get("max_seq_length", 1024))
    language_filter = hparams.get("language_filter", "en")
    seed = int(hparams.get("seed", 42))

    # Data paths from experiment config
    data_conf = info.trial.experiment_config.get("data", {})
    train_file = data_conf.get(
        "train_file", "data/training/combined_train.jsonl"
    )
    eval_file = data_conf.get(
        "eval_file", "data/training/combined_val.jsonl"
    )

    output_dir = "/tmp/determined-train-output"
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Model & tokenizer
    # ------------------------------------------------------------------
    dtype = resolve_dtype(torch)
    use_4bit = torch.cuda.is_available() and platform.system() != "Windows"

    quantization_config = None
    if use_4bit:
        quantization_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_use_double_quant=True,
            bnb_4bit_compute_dtype=dtype,
        )

    tokenizer = AutoTokenizer.from_pretrained(base_model, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        base_model,
        trust_remote_code=True,
        torch_dtype=dtype,
        quantization_config=quantization_config,
        device_map="auto" if torch.cuda.is_available() else None,
    )
    model.config.use_cache = False

    # ------------------------------------------------------------------
    # Datasets
    # ------------------------------------------------------------------
    train_ds = build_filtered_dataset(
        train_file,
        tokenizer=tokenizer,
        language_filter=language_filter,
    )
    eval_ds = None
    if Path(eval_file).exists():
        eval_ds = build_filtered_dataset(
            eval_file,
            tokenizer=tokenizer,
            language_filter=language_filter,
        )

    print(f"Train samples: {len(train_ds)}, Eval samples: {len(eval_ds) if eval_ds else 0}")
    print(f"Language filter: {language_filter}")
    print(f"Hyperparams: lr={learning_rate}, lora_r={lora_r}, lora_alpha={lora_alpha}, "
          f"batch={batch_size}, grad_accum={grad_accum}")

    # ------------------------------------------------------------------
    # LoRA config
    # ------------------------------------------------------------------
    target_modules = resolve_target_modules(
        model, "q_proj,k_proj,v_proj,o_proj,up_proj,down_proj,gate_proj"
    )

    lora_config = LoraConfig(
        r=lora_r,
        lora_alpha=lora_alpha,
        lora_dropout=lora_dropout,
        task_type="CAUSAL_LM",
        target_modules=target_modules,
    )

    # ------------------------------------------------------------------
    # Training arguments
    # ------------------------------------------------------------------
    training_args = TrainingArguments(
        output_dir=output_dir,
        per_device_train_batch_size=batch_size,
        per_device_eval_batch_size=max(1, batch_size),
        gradient_accumulation_steps=grad_accum,
        learning_rate=learning_rate,
        num_train_epochs=num_epochs,
        weight_decay=weight_decay,
        warmup_ratio=warmup_ratio,
        lr_scheduler_type="cosine",
        logging_steps=20,
        save_steps=20,
        eval_steps=20,
        eval_strategy="steps" if eval_ds is not None else "no",
        save_strategy="steps",
        bf16=(dtype == torch.bfloat16),
        fp16=(dtype == torch.float16),
        gradient_checkpointing=True,
        max_grad_norm=1.0,
        report_to="none",
        seed=seed,
        remove_unused_columns=False,
        optim="paged_adamw_8bit" if use_4bit else "adamw_torch",
    )

    # ------------------------------------------------------------------
    # Determined callback & trainer
    # ------------------------------------------------------------------
    core_context = det.core.init()
    det_callback = DetCallback(core_context, training_args)

    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=train_ds,
        eval_dataset=eval_ds,
        peft_config=lora_config,
        dataset_text_field="text",
        max_seq_length=max_seq_length,
        packing=True,
        args=training_args,
        callbacks=[det_callback],
    )

    # ------------------------------------------------------------------
    # Train
    # ------------------------------------------------------------------
    train_result = trainer.train()

    # Compute and log perplexity
    eval_loss = train_result.metrics.get("train_loss", 0)
    if eval_ds is not None:
        eval_metrics = trainer.evaluate()
        eval_loss = eval_metrics.get("eval_loss", eval_loss)
    perplexity = math.exp(eval_loss) if eval_loss < 20 else float("inf")
    print(f"Final eval_loss={eval_loss:.4f}, perplexity={perplexity:.2f}")

    # Save adapter
    trainer.save_model(output_dir)
    tokenizer.save_pretrained(output_dir)
    print(f"Saved adapter to {output_dir}")


if __name__ == "__main__":
    main()
