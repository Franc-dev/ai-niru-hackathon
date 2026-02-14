# EM-NS: Full Training & Deployment Pipeline

End-to-end guide for building, training, and deploying the EM-NS bilingual mental health counselling model.

> **Your setup**: 8GB RAM, CPU only, Windows. This guide uses **free cloud GPUs** for training.

---

## 1. Prerequisites

### Local Machine (dataset building only)
- Python 3.10+
- 8 GB RAM (sufficient for dataset building)
- No GPU needed for Steps 1-2

### Install Dependencies (local)

```bash
pip install datasets tqdm
```

### Free Cloud GPU Options (for training)

| Platform | Free GPU | VRAM | Time Limit | Best For |
|----------|----------|------|------------|----------|
| **Google Colab** | T4 | 15 GB | ~12 hrs/day | Quick experiments |
| **Kaggle Notebooks** | P100 / T4x2 | 16 GB | 30 hrs/week | Longer training |
| **Lightning AI** | T4 | 16 GB | 22 GPU hrs/month | Determined AI |
| **GitHub Codespaces** | None (CPU) | 8 GB | 60 hrs/month | Dataset building |

**Recommended path**: Build dataset locally → Upload to Google Drive/Kaggle → Train on Colab/Kaggle.

### Project Structure

```
ai-niru-hackathon/
├── training/
│   ├── scripts/
│   │   ├── build_combined_dataset.py   # Stage 0: combined EN+SW dataset
│   │   ├── build_mentalchat_bilingual.py  # Legacy: translated bilingual
│   │   ├── train_lora_chat.py          # Local LoRA training
│   │   └── run_training_pipeline.py    # Orchestrates all stages
│   └── determined/
│       ├── train_det.py                # Determined AI entrypoint
│       ├── experiment_const.yaml       # Single-run config
│       └── experiment_adaptive.yaml    # ASHA HP search config
├── data/training/                      # Generated datasets (gitignored)
├── backend/                            # FastAPI app
└── frontend/                           # Next.js frontend
```

---

## 2. Build the Combined Bilingual Dataset (Local - CPU)

This runs on your machine. It only downloads and formats data — no GPU needed.

```bash
python training/scripts/build_combined_dataset.py
```

| Source | Language | Rows | Type |
|--------|----------|------|------|
| `ShenLab/MentalChat16K` | English | ~16K | Counselling Q&A |
| `franmwan/swahili-Mental-Health` | Swahili | ~9K | Native Swahili Q&A |

### Options

```bash
python training/scripts/build_combined_dataset.py --max-en-rows 5000 --max-sw-rows 5000
```

### Output Files

```
data/training/
├── combined_all.jsonl       # All records (EN + SW)
├── combined_train.jsonl     # 90% stratified split
├── combined_val.jsonl       # 5% stratified split
├── combined_test.jsonl      # 5% stratified split
└── combined_manifest.json   # Build metadata & stats
```

---

## 3. Train on Google Colab (Free T4 GPU)

### Step 3.1: Upload dataset to Google Drive

1. Go to [drive.google.com](https://drive.google.com)
2. Create folder: `emns-training`
3. Upload these files from `data/training/`:
   - `combined_train.jsonl`
   - `combined_val.jsonl`
   - `combined_test.jsonl`

### Step 3.2: Open Colab notebook

Go to [colab.research.google.com](https://colab.research.google.com) → New Notebook.

**Change runtime**: Runtime → Change runtime type → **T4 GPU**

### Step 3.3: Paste this into Colab cells

**Cell 1: Install dependencies**
```python
!pip install -q datasets transformers peft trl bitsandbytes accelerate tqdm torch
```

**Cell 2: Mount Drive & load data**
```python
from google.colab import drive
drive.mount('/content/drive')

TRAIN_FILE = "/content/drive/MyDrive/emns-training/combined_train.jsonl"
EVAL_FILE = "/content/drive/MyDrive/emns-training/combined_val.jsonl"
OUTPUT_DIR = "/content/drive/MyDrive/emns-training/emns-lora-v1"
```

**Cell 3: Clone repo and train**
```python
!git clone https://github.com/Franc-dev/ai-niru-hackathon.git /content/emns
%cd /content/emns

!python training/scripts/train_lora_chat.py \
  --base-model Qwen/Qwen2.5-3B-Instruct \
  --train-file {TRAIN_FILE} \
  --eval-file {EVAL_FILE} \
  --output-dir {OUTPUT_DIR} \
  --num-epochs 2 \
  --batch-size 2 \
  --grad-accum 8 \
  --max-seq-length 1024
```

Training takes ~2-4 hours on a T4. The adapter saves to your Google Drive so it persists.

---

## 4. Train on Kaggle (Free P100 GPU - 30 hrs/week)

Kaggle gives more GPU time than Colab.

### Step 4.1: Create a Kaggle Notebook

1. Go to [kaggle.com/code](https://kaggle.com/code) → New Notebook
2. Settings → Accelerator → **GPU P100**
3. Settings → Internet → **On**

### Step 4.2: Upload dataset as Kaggle Dataset

1. Go to [kaggle.com/datasets](https://kaggle.com/datasets) → New Dataset
2. Name: `emns-combined-bilingual`
3. Upload `combined_train.jsonl`, `combined_val.jsonl`, `combined_test.jsonl`

### Step 4.3: Add to notebook and train

**Cell 1:**
```python
!pip install -q datasets transformers peft trl bitsandbytes accelerate tqdm

!git clone https://github.com/Franc-dev/ai-niru-hackathon.git /kaggle/working/emns
%cd /kaggle/working/emns
```

**Cell 2:**
```python
# Adjust username to your Kaggle handle
TRAIN_FILE = "/kaggle/input/emns-combined-bilingual/combined_train.jsonl"
EVAL_FILE = "/kaggle/input/emns-combined-bilingual/combined_val.jsonl"
OUTPUT_DIR = "/kaggle/working/emns-lora-v1"

!python training/scripts/train_lora_chat.py \
  --base-model Qwen/Qwen2.5-3B-Instruct \
  --train-file $TRAIN_FILE \
  --eval-file $EVAL_FILE \
  --output-dir $OUTPUT_DIR \
  --num-epochs 2 \
  --batch-size 2 \
  --grad-accum 8 \
  --max-seq-length 1024
```

**Cell 3: Download adapter when done**
```python
import shutil
shutil.make_archive("/kaggle/working/emns-lora-v1", 'zip', OUTPUT_DIR)
# Download from Kaggle's Output tab
```

---

## 5. Determined AI on Lightning AI (Free Tier)

If you want the full Determined AI experience with HP search:

### Step 5.1: Sign up at [lightning.ai](https://lightning.ai) (free)

### Step 5.2: Create a Studio with GPU

1. New Studio → Select **T4 GPU**
2. Open terminal in the Studio

### Step 5.3: Set up and run

```bash
# Clone and enter project
git clone https://github.com/Franc-dev/ai-niru-hackathon.git
cd ai-niru-hackathon

# Install deps
pip install datasets transformers peft trl bitsandbytes accelerate tqdm determined

# Build dataset
python training/scripts/build_combined_dataset.py

# Start Determined local cluster
det deploy local cluster-up

# Run sanity check (single trial)
det -m http://localhost:8080 experiment create \
    training/determined/experiment_const.yaml .

# Once that passes, run HP search
det -m http://localhost:8080 experiment create \
    training/determined/experiment_adaptive.yaml .
```

### Monitor experiments

```bash
det -m http://localhost:8080 experiment list
det -m http://localhost:8080 trial logs <trial_id>
```

### HP Search Space

| Parameter | Type | Range |
|-----------|------|-------|
| `lora_r` | categorical | 8, 16, 32, 64 |
| `lora_alpha` | categorical | 16, 32, 64 |
| `lora_dropout` | double | 0.0 - 0.1 |
| `learning_rate` | log | 1e-5 - 1e-3 |
| `batch_size` | categorical | 1, 2, 4 |
| `grad_accum` | categorical | 4, 8, 16 |
| `language_filter` | categorical | en, sw, all |

---

## 6. Export the Trained Adapter

After training completes (on any platform), download the adapter folder. It contains:

```
emns-lora-v1/
├── adapter_config.json
├── adapter_model.safetensors
├── tokenizer.json
├── tokenizer_config.json
└── special_tokens_map.json
```

### Optional: Merge into base model

```python
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer

base = AutoModelForCausalLM.from_pretrained("Qwen/Qwen2.5-3B-Instruct")
model = PeftModel.from_pretrained(base, "training/artifacts/emns-lora-v1")
merged = model.merge_and_unload()
merged.save_pretrained("training/artifacts/emns-merged")
AutoTokenizer.from_pretrained("Qwen/Qwen2.5-3B-Instruct").save_pretrained(
    "training/artifacts/emns-merged"
)
```

---

## 7. Serve the Model

### Option A: HuggingFace Spaces (free, easiest)

1. Go to [huggingface.co/spaces](https://huggingface.co/spaces) → Create Space
2. Upload your adapter + a Gradio app
3. Free CPU inference (slow but works)

### Option B: vLLM on cloud (if you have a GPU server)

```bash
pip install vllm
python -m vllm.entrypoints.openai.api_server \
    --model training/artifacts/emns-merged \
    --port 8000
```

### Option C: Local inference with LoRA (CPU - slow but works)

```python
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer

tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen2.5-3B-Instruct")
model = AutoModelForCausalLM.from_pretrained(
    "Qwen/Qwen2.5-3B-Instruct", device_map="cpu"
)
model = PeftModel.from_pretrained(model, "training/artifacts/emns-lora-v1")

messages = [
    {"role": "system", "content": "You are a helpful mental health counselling assistant."},
    {"role": "user", "content": "I've been feeling very anxious lately."},
]
inputs = tokenizer.apply_chat_template(messages, return_tensors="pt")
outputs = model.generate(inputs, max_new_tokens=256)
print(tokenizer.decode(outputs[0], skip_special_tokens=True))
```

---

## 8. Evaluation

### Run on test split (on Colab/Kaggle)

```bash
python training/scripts/train_lora_chat.py \
  --eval-only \
  --eval-file data/training/combined_test.jsonl \
  --base-model Qwen/Qwen2.5-3B-Instruct \
  --adapter-path training/artifacts/emns-lora-v1
```

### Key Metrics
- **eval_loss**: Cross-entropy loss on held-out data
- **perplexity**: `exp(eval_loss)` — lower is better
- Compare EN-only vs SW-only vs bilingual to assess cross-lingual transfer

### Manual Evaluation Checklist
- [ ] Crisis responses include safety resources and hotline numbers
- [ ] Swahili responses are fluent and culturally appropriate
- [ ] Model does not diagnose or prescribe medication
- [ ] Empathetic tone is maintained across languages

---

## 9. Connect to the Application

### Configure the backend

Set environment variables in `backend/.env`:

```env
# If using vLLM or OpenAI-compatible endpoint:
OPENAI_API_BASE=http://localhost:8000/v1
OPENAI_API_KEY=not-needed

# If using HuggingFace local model:
MODEL_PATH=training/artifacts/emns-lora-v1
BASE_MODEL=Qwen/Qwen2.5-3B-Instruct
```

### Start the backend

```bash
cd backend
python run.py
```

### Start the frontend

```bash
cd frontend
npm install
npm run dev
```

The app will be available at `http://localhost:3000`.

---

## 10. Troubleshooting

### Dataset build fails with "Dataset not found"
```bash
pip install --upgrade datasets huggingface_hub
```

### Colab disconnects during training
- Use Colab Pro ($10/month) for longer sessions
- Or use Kaggle (30 hrs/week, less disconnection)
- Save checkpoints to Google Drive so you can resume

### Out of memory on T4 (15GB VRAM)
- Reduce `--batch-size` to 1
- Increase `--grad-accum` to 16
- Use `--max-seq-length 512`
- QLoRA is enabled by default (4-bit quantization)

### Import errors in `train_det.py`
- Ensure `training/__init__.py` and `training/scripts/__init__.py` exist
- Run from project root: `python -m py_compile training/determined/train_det.py`

### Determined experiment fails
- Check master is running: `det -m http://localhost:8080 version`
- Verify data paths exist: `ls data/training/combined_train.jsonl`
- Check logs: `det -m http://localhost:8080 trial logs <trial_id>`

### Lock file prevents dataset build
```bash
rm -rf training/reports/build.lock
```

### Windows-specific issues
- Use `python` instead of `python3`
- bitsandbytes on Windows: `pip install bitsandbytes-windows`
- Dataset building works fine on Windows/CPU

---

## Quick Reference: Recommended Path

```
1. [LOCAL]  python training/scripts/build_combined_dataset.py
2. [LOCAL]  Upload combined_*.jsonl to Google Drive
3. [COLAB]  Train with T4 GPU (free) → saves adapter to Drive
4. [LOCAL]  Download adapter → connect to backend
```
