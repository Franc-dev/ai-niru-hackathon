"""
Train Mistral 7B with LoRA for Swahili Mental Health.
Uses 4-bit quantization for 6GB VRAM.
"""

import json
from pathlib import Path

import torch
from datasets import Dataset
from peft import LoraConfig
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig, TrainingArguments
from trl import SFTTrainer

DATA_PATH = "data/training/swahili_mental_health_expanded.jsonl"
MODEL_NAME = "mistralai/Mistral-7B-Instruct-v0.3"
OUTPUT_DIR = "training/artifacts/emns-swahili-mistral-v1"
MAX_LENGTH = 512


def load_data(path: str):
    """Load conversation data from JSONL."""
    data = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                data.append(json.loads(line))
    print(f"Loaded {len(data)} examples")
    return data


def format_for_sft(example):
    """Format conversation for SFT training."""
    messages = example["messages"]
    
    # Build text with Mistral format
    text_parts = []
    for msg in messages:
        role = msg["role"]
        content = msg["content"]
        
        if role == "system":
            text_parts.append(f"<s>[INST] {content}")
        elif role == "user":
            if text_parts:
                text_parts.append(f"\n\nUser: {content}")
            else:
                text_parts.append(f"<s>[INST] User: {content}")
        elif role == "assistant":
            text_parts.append(f" [/INST] {content}</s>")
    
    return {"text": "".join(text_parts)}


def main():
    print("=" * 60)
    print("Training Mistral 7B for Swahili Mental Health")
    print("=" * 60)
    
    # Load data
    raw_data = load_data(DATA_PATH)
    formatted = [format_for_sft(d) for d in raw_data]
    dataset = Dataset.from_list(formatted)
    
    print(f"Sample: {dataset[0]['text'][:200]}...")
    
    # Load model with 4-bit quantization
    print("\nLoading Mistral 7B with 4-bit quantization...")
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True,
    )
    
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME,
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=True,
    )
    
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, trust_remote_code=True)
    tokenizer.pad_token = tokenizer.eos_token
    
    # LoRA config
    lora_config = LoraConfig(
        r=16,
        lora_alpha=32,
        lora_dropout=0.1,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
        bias="none",
        task_type="CAUSAL_LM",
    )
    
    # Training args (optimized for 6GB VRAM)
    training_args = TrainingArguments(
        output_dir=OUTPUT_DIR,
        num_train_epochs=3,
        per_device_train_batch_size=1,
        gradient_accumulation_steps=8,
        learning_rate=2e-4,
        fp16=True,
        logging_steps=5,
        save_strategy="epoch",
        save_total_limit=2,
        warmup_steps=10,
        report_to="none",
        max_grad_norm=0.3,
    )
    
    # Trainer
    trainer = SFTTrainer(
        model=model,
        args=training_args,
        train_dataset=dataset,
        peft_config=lora_config,
        dataset_text_field="text",
        max_seq_length=MAX_LENGTH,
        tokenizer=tokenizer,
    )
    
    print("\nStarting training...")
    trainer.train()
    
    # Save
    print(f"\nSaving to {OUTPUT_DIR}")
    trainer.save_model(OUTPUT_DIR)
    tokenizer.save_pretrained(OUTPUT_DIR)
    print("✅ Training complete!")


if __name__ == "__main__":
    main()
