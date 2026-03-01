# EM-NS Kaggle Training Notebook

Copy each cell below into a **new Kaggle notebook** in order.

**Setup**: GPU P100, Internet ON, dataset `emns-combined-bilingual` added.

---

## Cell 1: Install dependencies

```python
!pip install -q datasets transformers peft trl bitsandbytes accelerate tqdm sentencepiece protobuf

```

---

## Cell 2: Write the training script

```python
%%writefile /kaggle/working/train.py
"""EM-NS LoRA training - compatible with latest trl/transformers on Kaggle."""
import argparse, json
from pathlib import Path

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-model", default="Qwen/Qwen2.5-3B-Instruct")
    parser.add_argument("--train-file", required=True)
    parser.add_argument("--eval-file", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--num-epochs", type=float, default=2.0)
    parser.add_argument("--batch-size", type=int, default=2)
    parser.add_argument("--grad-accum", type=int, default=8)
    parser.add_argument("--max-seq-length", type=int, default=1024)
    parser.add_argument("--lora-r", type=int, default=16)
    parser.add_argument("--lora-alpha", type=int, default=32)
    parser.add_argument("--lora-dropout", type=float, default=0.05)
    parser.add_argument("--learning-rate", type=float, default=2e-4)
    parser.add_argument("--logging-steps", type=int, default=10)
    parser.add_argument("--save-steps", type=int, default=500)
    parser.add_argument("--eval-steps", type=int, default=500)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    import torch
    from datasets import load_dataset
    from peft import LoraConfig
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    from trl import SFTTrainer, SFTConfig
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Dtype
    if not torch.cuda.is_available():
        dtype = torch.float32
    elif torch.cuda.is_bf16_supported():
        dtype = torch.bfloat16
    else:
        dtype = torch.float16

    # Quantization
    use_4bit = torch.cuda.is_available()
    quant_config = None
    if use_4bit:
        quant_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_use_double_quant=True,
            bnb_4bit_compute_dtype=dtype,
        )

    # Tokenizer
    tokenizer = AutoTokenizer.from_pretrained(args.base_model, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    # Model
    model = AutoModelForCausalLM.from_pretrained(
        args.base_model,
        trust_remote_code=True,
        torch_dtype=dtype,
        quantization_config=quant_config,
        device_map="auto" if torch.cuda.is_available() else None,
    )
    model.config.use_cache = False

    # Dataset
    def load_and_format(path):
        ds = load_dataset("json", data_files=path, split="train")
        def fmt(example):
            messages = example["messages"]
            if isinstance(messages, str):
                messages = json.loads(messages)
            text = tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=False
            )
            return {"text": text}
        return ds.map(fmt, remove_columns=ds.column_names, desc=f"Formatting {Path(path).name}")

    train_ds = load_and_format(args.train_file)
    eval_ds = load_and_format(args.eval_file) if Path(args.eval_file).exists() else None

    print(f"Train: {len(train_ds)} samples, Eval: {len(eval_ds) if eval_ds else 0} samples")

    # LoRA target modules
    target_modules = []
    candidates = ["q_proj", "k_proj", "v_proj", "o_proj", "up_proj", "down_proj", "gate_proj"]
    for name, _ in model.named_modules():
        for c in candidates:
            if name.endswith(c) and c not in target_modules:
                target_modules.append(c)

    lora_config = LoraConfig(
        r=args.lora_r,
        lora_alpha=args.lora_alpha,
        lora_dropout=args.lora_dropout,
        task_type="CAUSAL_LM",
        target_modules=sorted(target_modules),
    )

    # Training config
    training_args = SFTConfig(
        output_dir=str(output_dir),
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=max(1, args.batch_size),
        gradient_accumulation_steps=args.grad_accum,
        learning_rate=args.learning_rate,
        num_train_epochs=args.num_epochs,
        weight_decay=0.01,
        warmup_ratio=0.03,
        lr_scheduler_type="cosine",
        logging_steps=args.logging_steps,
        save_steps=args.save_steps,
        eval_steps=args.eval_steps,
        eval_strategy="steps" if eval_ds else "no",
        save_strategy="steps",
        bf16=(dtype == torch.bfloat16),
        fp16=(dtype == torch.float16),
        gradient_checkpointing=True,
        max_grad_norm=1.0,
        report_to="none",
        seed=args.seed,
        remove_unused_columns=False,
        optim="paged_adamw_8bit" if use_4bit else "adamw_torch",
        max_seq_length=args.max_seq_length,
        dataset_text_field="text",
        packing=True,
    )

    # Trainer
    trainer = SFTTrainer(
        model=model,
        processing_class=tokenizer,
        train_dataset=train_ds,
        eval_dataset=eval_ds,
        peft_config=lora_config,
        args=training_args,
    )

    trainer.train()
    trainer.save_model(str(output_dir))
    tokenizer.save_pretrained(str(output_dir))
    print(f"Saved adapter to {output_dir}")

if __name__ == "__main__":
    main()
```

---

## Cell 3: Verify dataset files

```python
import os

TRAIN = "/kaggle/input/emns-combined-bilingual/combined_train.jsonl"
VAL = "/kaggle/input/emns-combined-bilingual/combined_val.jsonl"

for f in [TRAIN, VAL]:
    if os.path.exists(f):
        with open(f) as fh:
            print(f"OK: {f} ({sum(1 for _ in fh)} records)")
    else:
        print(f"MISSING: {f}")
```

---

## Cell 4: Train (takes ~2-3 hours, do not interrupt)
```python
!python /kaggle/working/train.py \
  --base-model Qwen/Qwen2.5-3B-Instruct \
  --train-file /kaggle/input/emns-combined-bilingual/combined_train.jsonl \
  --eval-file /kaggle/input/emns-combined-bilingual/combined_val.jsonl \
  --output-dir /kaggle/working/emns-lora-v1 \
  --num-epochs 2 \
  --batch-size 2 \
  --grad-accum 8 \
  --max-seq-length 1024 \
  --logging-steps 10 \
  --save-steps 500 \
  --eval-steps 500
```

---

## Cell 5: Verify adapter files

```python
import os

adapter_dir = "/kaggle/working/emns-lora-v1"
if os.path.isdir(adapter_dir):
    print("Adapter files:")
    for f in sorted(os.listdir(adapter_dir)):
        size = os.path.getsize(os.path.join(adapter_dir, f)) / (1024 * 1024)
        print(f"  {f} ({size:.1f} MB)")
else:
    print("ERROR: Training did not produce output")
```

---

## Cell 6: Test the model (English + Swahili)
```python
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel

base_model_name = "Qwen/Qwen2.5-3B-Instruct"
adapter_path = "/kaggle/working/emns-lora-v1"

tokenizer = AutoTokenizer.from_pretrained(base_model_name, trust_remote_code=True)
model = AutoModelForCausalLM.from_pretrained(
    base_model_name, trust_remote_code=True, torch_dtype=torch.float16, device_map="auto"
)
model = PeftModel.from_pretrained(model, adapter_path)
model.eval()

# Test English
messages_en = [
    {"role": "system", "content": "You are a helpful mental health counselling assistant. Provide safe, supportive, non-judgmental guidance."},
    {"role": "user", "content": "I've been feeling very anxious and can't sleep at night."},
]
input_text = tokenizer.apply_chat_template(messages_en, tokenize=False, add_generation_prompt=True)
inputs = tokenizer(input_text, return_tensors="pt").to(model.device)
with torch.inference_mode():
    outputs = model.generate(**inputs, max_new_tokens=256, temperature=0.7, do_sample=True)
response = tokenizer.decode(outputs[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
print("=== English Response ===")
print(response)

# Test Swahili
messages_sw = [
    {"role": "system", "content": "Wewe ni msaidizi wa ushauri wa afya ya akili. Toa mwongozo salama, wa kusaidia, na usio na hukumu."},
    {"role": "user", "content": "Nina wasiwasi sana na siwezi kulala usiku."},
]
input_text = tokenizer.apply_chat_template(messages_sw, tokenize=False, add_generation_prompt=True)
inputs = tokenizer(input_text, return_tensors="pt").to(model.device)
with torch.inference_mode():
    outputs = model.generate(**inputs, max_new_tokens=256, temperature=0.7, do_sample=True)
response = tokenizer.decode(outputs[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
print("\n=== Swahili Response ===")
print(response)
```

---

## Cell 7: Zip adapter for download

```python
import shutil, os

adapter_dir = "/kaggle/working/emns-lora-v1"
shutil.make_archive("/kaggle/working/emns-lora-v1-adapter", "zip", adapter_dir)
print(f"Created: emns-lora-v1-adapter.zip ({os.path.getsize('/kaggle/working/emns-lora-v1-adapter.zip') / (1024*1024):.1f} MB)")
print("Download from the Output tab after saving the notebook.")
```

---

## After training: Download and serve locally

1. Click **Save Version** (top right) -> **Save & Run All**
2. Go to notebook **Output** tab -> download `emns-lora-v1-adapter.zip`
3. Unzip into `training/artifacts/emns-chat-lora-v1/` on your local machine
4. Start the model server:

```bash
pip install torch transformers peft fastapi uvicorn
python training/scripts/serve_model.py --adapter-path training/artifacts/emns-chat-lora-v1
```

5. Start backend (new terminal):

```bash
cd backend && python run.py
```

6. Start frontend (new terminal):

```bash
cd frontend && npm run dev
```

7. Open http://localhost:3000 and chat.
