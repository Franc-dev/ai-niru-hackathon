# EM-NS: Complete Training & Deployment Guide

> **Your setup**: Windows, 8GB RAM, CPU only.
> **Training**: Kaggle free GPU (P100, 30 hrs/week).
> **Serving**: Local CPU (slow but works) or free cloud.

---

## Overview

```
Step 1: [LOCAL]   Build the combined EN+SW dataset (CPU, ~5 min)
Step 2: [KAGGLE]  Upload dataset to Kaggle
Step 3: [KAGGLE]  Train LoRA adapter on free P100 GPU (~2-3 hrs)
Step 4: [KAGGLE]  Download trained adapter
Step 5: [LOCAL]   Serve model on localhost:8001
Step 6: [LOCAL]   Start backend (localhost:8000) + frontend (localhost:3000)
```

---

## Step 1: Build the Combined Bilingual Dataset (Local)

This only downloads and formats data — runs fine on CPU with 8GB RAM.

### 1.1 Install dataset dependencies

```bash
pip install datasets tqdm
```

### 1.2 Run the builder

```bash
python training/scripts/build_combined_dataset.py
```

This pulls two HuggingFace datasets:

| Source | Language | Rows |
|--------|----------|------|
| `ShenLab/MentalChat16K` | English | ~16K |
| `franmwan/swahili-Mental-Health` | Swahili (native) | ~9K |

### 1.3 Verify output

You should now have these files:

```
data/training/
├── combined_all.jsonl       # ~25K records
├── combined_train.jsonl     # 90% (~22.5K)
├── combined_val.jsonl       # 5% (~1.2K)
├── combined_test.jsonl      # 5% (~1.2K)
└── combined_manifest.json   # stats
```

Check the manifest:
```bash
python -c "import json; print(json.dumps(json.load(open('data/training/combined_manifest.json')), indent=2))"
```

---

## Step 2: Upload Dataset to Kaggle

### 2.1 Create a Kaggle account

Go to [kaggle.com](https://www.kaggle.com) and sign up (free).

### 2.2 Upload as a Kaggle Dataset

1. Go to **kaggle.com/datasets** → **New Dataset**
2. Name it: `emns-combined-bilingual`
3. Upload these 3 files from your `data/training/` folder:
   - `combined_train.jsonl`
   - `combined_val.jsonl`
   - `combined_test.jsonl`
4. Click **Create**

### 2.3 Note your dataset path

Your dataset will be at: `kaggle.com/datasets/<your-username>/emns-combined-bilingual`

In notebooks it's available at: `/kaggle/input/emns-combined-bilingual/`

---

## Step 3: Train on Kaggle (Free P100 GPU)

### 3.1 Create a new Kaggle Notebook

1. Go to **kaggle.com/code** → **New Notebook**
2. On the right sidebar:
   - **Settings** → **Accelerator** → Select **GPU P100**
   - **Settings** → **Internet** → Toggle **ON**
3. On the right sidebar → **Add Data** → search your dataset `emns-combined-bilingual` → **Add**

### 3.2 Paste these cells into the notebook

---

**Cell 1: Install dependencies**

```python
!pip install -q datasets transformers peft trl bitsandbytes accelerate tqdm sentencepiece protobuf
```

---

**Cell 2: Clone the project repo**

```python
!git clone https://github.com/Franc-dev/ai-niru-hackathon.git /kaggle/working/emns
import os
os.chdir("/kaggle/working/emns")
print("Working directory:", os.getcwd())
```

---

**Cell 3: Verify dataset files exist**

```python
import os

TRAIN_FILE = "/kaggle/input/emns-combined-bilingual/combined_train.jsonl"
VAL_FILE = "/kaggle/input/emns-combined-bilingual/combined_val.jsonl"

for f in [TRAIN_FILE, VAL_FILE]:
    if os.path.exists(f):
        # Count lines
        with open(f) as fh:
            count = sum(1 for _ in fh)
        print(f"OK: {f} ({count} records)")
    else:
        print(f"MISSING: {f}")
```

---

**Cell 4: Train the LoRA adapter**

```python
import subprocess, sys

result = subprocess.run([
    sys.executable, "training/scripts/train_lora_chat.py",
    "--base-model", "Qwen/Qwen2.5-3B-Instruct",
    "--train-file", TRAIN_FILE,
    "--eval-file", VAL_FILE,
    "--output-dir", "/kaggle/working/emns-lora-v1",
    "--num-epochs", "2",
    "--batch-size", "2",
    "--grad-accum", "8",
    "--max-seq-length", "1024",
    "--lora-r", "16",
    "--lora-alpha", "32",
    "--lora-dropout", "0.05",
    "--logging-steps", "10",
    "--save-steps", "500",
    "--eval-steps", "500",
])

print("Exit code:", result.returncode)
```

This takes **~2-3 hours** on a P100. You'll see training loss printed every 10 steps.

---

**Cell 5: Verify the adapter was saved**

```python
import os

adapter_dir = "/kaggle/working/emns-lora-v1"
print("Adapter files:")
for f in os.listdir(adapter_dir):
    size_mb = os.path.getsize(os.path.join(adapter_dir, f)) / (1024 * 1024)
    print(f"  {f} ({size_mb:.1f} MB)")
```

You should see:
```
adapter_config.json
adapter_model.safetensors
tokenizer.json
tokenizer_config.json
special_tokens_map.json
tokenizer.model (if applicable)
```

---

**Cell 6: Quick test — generate a response**

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

**Cell 7: Zip and prepare for download**

```python
import shutil, os

adapter_dir = "/kaggle/working/emns-lora-v1"
shutil.make_archive("/kaggle/working/emns-lora-v1-adapter", "zip", adapter_dir)
print("Created: /kaggle/working/emns-lora-v1-adapter.zip")
print(f"Size: {os.path.getsize('/kaggle/working/emns-lora-v1-adapter.zip') / (1024*1024):.1f} MB")
```

---

## Step 4: Download the Trained Adapter

### Option A: From Kaggle Output tab
1. After the notebook finishes, click **Save Version** (top right) → **Save & Run All**
2. Once done, go to the notebook's **Output** tab
3. Download `emns-lora-v1-adapter.zip`

### Option B: Using Kaggle API (from your local machine)

```bash
pip install kaggle
kaggle kernels output <your-username>/<notebook-name> -p ./
```

### 4.1 Extract the adapter locally

```bash
mkdir -p training/artifacts/emns-chat-lora-v1
```

Unzip `emns-lora-v1-adapter.zip` into `training/artifacts/emns-chat-lora-v1/`.

Your folder should look like:
```
training/artifacts/emns-chat-lora-v1/
├── adapter_config.json
├── adapter_model.safetensors
├── tokenizer.json
├── tokenizer_config.json
└── special_tokens_map.json
```

---

## Step 5: Serve the Model Locally

The serving script loads your trained LoRA adapter and runs a FastAPI server on port 8001 — exactly what the backend expects.

### 5.1 Install serving dependencies

```bash
pip install torch transformers peft fastapi uvicorn
```

> **Note**: On your 8GB CPU machine, the 3B model will use ~6GB RAM and respond in ~30-60 seconds per message. This is fine for development/demo.

### 5.2 Start the model server

```bash
python training/scripts/serve_model.py \
  --base-model Qwen/Qwen2.5-3B-Instruct \
  --adapter-path training/artifacts/emns-chat-lora-v1 \
  --port 8001
```

First run downloads the base model (~6GB). After that it starts instantly.

You should see:
```
Loading base model: Qwen/Qwen2.5-3B-Instruct on cpu ...
Loading LoRA adapter: training/artifacts/emns-chat-lora-v1 ...
Adapter loaded.
Model ready.
INFO:     Uvicorn running on http://0.0.0.0:8001
```

### 5.3 Test the model server

Open a new terminal and test:

```bash
curl -X POST http://localhost:8001/v1/chat -H "Content-Type: application/json" -d "{\"messages\": [{\"role\": \"system\", \"content\": \"You are a helpful mental health counselling assistant.\"}, {\"role\": \"user\", \"content\": \"I feel anxious\"}]}"
```

Or with Python:

```python
import requests

r = requests.post("http://localhost:8001/v1/chat", json={
    "messages": [
        {"role": "system", "content": "You are a helpful mental health counselling assistant."},
        {"role": "user", "content": "I feel anxious"},
    ]
})
print(r.json())
# {"content": "I hear you. Anxiety can feel overwhelming..."}
```

### 5.4 Check health

```bash
curl http://localhost:8001/health
# {"status": "ok", "device": "cpu"}
```

---

## Step 6: Connect to Backend & Frontend

### 6.1 Backend configuration

Your backend already expects the model at `http://localhost:8001/v1/chat` (set in `backend/core/config.py`). No changes needed.

If you want to customize, create `backend/.env`:
```env
LOCAL_MODEL_URL=http://localhost:8001/v1/chat
LOCAL_EMBEDDING_URL=http://localhost:8001/v1/embeddings
MONGODB_URL=mongodb://localhost:27017
```

### 6.2 Start the backend (new terminal)

```bash
cd backend
pip install -r requirements.txt
python run.py
```

Backend runs on `http://localhost:8000`.

### 6.3 Start the frontend (new terminal)

```bash
cd frontend
npm install
npm run dev
```

Frontend runs on `http://localhost:3000`.

### 6.4 Architecture

```
Browser (localhost:3000)
   │
   ▼
Frontend (Next.js)
   │  POST /api/v1/chat
   ▼
Backend (FastAPI, localhost:8000)
   │  POST /v1/chat {"messages": [...]}
   ▼
Model Server (serve_model.py, localhost:8001)
   │  Qwen2.5-3B + LoRA adapter
   ▼
Response → Backend → Frontend → User
```

### 6.5 Full startup (3 terminals)

**Terminal 1 — Model Server:**
```bash
python training/scripts/serve_model.py --adapter-path training/artifacts/emns-chat-lora-v1
```

**Terminal 2 — Backend:**
```bash
cd backend && python run.py
```

**Terminal 3 — Frontend:**
```bash
cd frontend && npm run dev
```

Open `http://localhost:3000` and start chatting.

---

## Troubleshooting

### Dataset build: "Dataset not found"
```bash
pip install --upgrade datasets huggingface_hub
```

### Kaggle: "No GPU available"
- Make sure you selected **GPU P100** in notebook settings
- Kaggle limits to 30 hrs/week — check your quota at kaggle.com/me/account

### Kaggle: Notebook disconnects mid-training
- Click **Save Version** before starting to save progress
- Reduce dataset: rebuild with `--max-en-rows 8000 --max-sw-rows 5000`
- This reduces training time to ~1.5 hrs

### Kaggle: "CUDA out of memory"
- Change `--batch-size` to `1` and `--grad-accum` to `16` in Cell 4
- Use `--max-seq-length 512` instead of 1024

### Local: Model server uses too much RAM
- The 3B model needs ~6GB RAM. Close other apps.
- If still tight, use a smaller model: `--base-model Qwen/Qwen2.5-1.5B-Instruct`
  (Retrain on Kaggle with this smaller model too)

### Local: Responses are very slow on CPU
- Expected: 30-60 seconds per response on CPU. This is normal.
- Add `--max-new-tokens 128` to limit response length (faster)
- For production, deploy on a cloud GPU (see below)

### Backend: "Connection refused" to model server
- Make sure `serve_model.py` is running on port 8001
- Check: `curl http://localhost:8001/health`

### Import error: "No module named training"
- Make sure `training/__init__.py` and `training/scripts/__init__.py` exist
- Run from project root directory

---

## Optional: Faster Serving with Free Cloud GPU

If CPU is too slow, you can serve the model on a free cloud GPU:

### Option A: Google Colab as a server (free T4)

**Colab notebook:**
```python
# Cell 1: Install
!pip install -q torch transformers peft fastapi uvicorn pyngrok

# Cell 2: Clone & setup
!git clone https://github.com/Franc-dev/ai-niru-hackathon.git /content/emns
# Upload your adapter zip and unzip it:
# !unzip /content/emns-lora-v1-adapter.zip -d /content/emns-lora-v1

# Cell 3: Expose with ngrok
from pyngrok import ngrok
import threading, os, sys

os.chdir("/content/emns")
sys.path.insert(0, "/content/emns")

# Start tunnel
public_url = ngrok.connect(8001)
print(f"Public URL: {public_url}")
print(f"Set LOCAL_MODEL_URL={public_url}/v1/chat in your backend/.env")

# Cell 4: Run server
!python training/scripts/serve_model.py \
  --base-model Qwen/Qwen2.5-3B-Instruct \
  --adapter-path /content/emns-lora-v1 \
  --port 8001
```

Then on your local machine, set in `backend/.env`:
```env
LOCAL_MODEL_URL=https://<ngrok-url>/v1/chat
```

### Option B: HuggingFace Spaces (free, persistent)

1. Go to [huggingface.co/spaces](https://huggingface.co/spaces) → Create Space
2. Select **Gradio** or **Docker** SDK
3. Upload your adapter files
4. Add inference code
5. Your model gets a permanent URL

---

## File Reference

| File | Purpose |
|------|---------|
| `training/scripts/build_combined_dataset.py` | Build EN+SW dataset from HuggingFace |
| `training/scripts/train_lora_chat.py` | LoRA training script (runs on Kaggle) |
| `training/scripts/serve_model.py` | Serve trained model as HTTP API |
| `training/determined/train_det.py` | Determined AI training entrypoint |
| `training/determined/experiment_const.yaml` | Single-run experiment config |
| `training/determined/experiment_adaptive.yaml` | HP search config (20 trials) |
| `backend/services/agent.py` | ReAct agent that calls model server |
| `backend/core/config.py` | Backend config (LOCAL_MODEL_URL) |
