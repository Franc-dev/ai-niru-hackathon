# EMNS Training Workflow

This workflow is aligned to the EM-NS roadmap:
- Chat-only model training (no voice model training).
- Bilingual English + Swahili data.
- Safety-centered evaluation before release.
- Local serving endpoint compatible with backend (`/v1/chat`, `/v1/embeddings`).

## 1) Environment

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r training/requirements.txt
```

## 2) Build Bilingual Dataset (MentalChat16K -> English+Kiswahili)

Full dataset:

```bash
python training/scripts/build_mentalchat_bilingual.py
```

Quick start (first 200 rows):

```bash
python training/scripts/build_mentalchat_bilingual.py --limit 200
```

Offline/reproducible translation (Marian):

```bash
python training/scripts/build_mentalchat_bilingual.py --translate-backend marian
```

Outputs:
- `data/training/mentalchat_bilingual_all.jsonl`
- `data/training/mentalchat_bilingual_train.jsonl`
- `data/training/mentalchat_bilingual_val.jsonl`
- `data/training/mentalchat_bilingual_test.jsonl`
- `data/training/mentalchat_bilingual_manifest.json`

## 2b) Merge Kenyan Localized Data

Template file:
- `training/templates/kenyan_localized_template.jsonl`

Merge command:

```bash
python training/scripts/merge_localized_data.py
```

## 3) Train LoRA Chat Model

```bash
python training/scripts/train_lora_chat.py ^
  --base-model Qwen/Qwen2.5-3B-Instruct ^
  --train-file data/training/mentalchat_bilingual_train.jsonl ^
  --eval-file data/training/mentalchat_bilingual_val.jsonl ^
  --output-dir training/artifacts/emns-chat-lora-v1
```

Notes:
- On Windows, run with `--no-4bit` if bitsandbytes is unavailable.
- For low VRAM, reduce `--batch-size` and increase `--grad-accum`.

## 4) Serve Model Locally

Base model only:

```bash
python training/scripts/serve_local_model.py --model-id Qwen/Qwen2.5-3B-Instruct --port 8001
```

Base + LoRA adapter:

```bash
python training/scripts/serve_local_model.py ^
  --model-id Qwen/Qwen2.5-3B-Instruct ^
  --adapter-path training/artifacts/emns-chat-lora-v1 ^
  --port 8001
```

## 5) Red-Team Safety Check

```bash
python training/scripts/run_red_team_eval.py --server-url http://localhost:8001
```

Output:
- `training/reports/red_team_report.json`

## 6) Connect to Existing Backend

The backend already expects these URLs in `backend/.env`:

```env
LOCAL_MODEL_URL=http://localhost:8001/v1/chat
LOCAL_EMBEDDING_URL=http://localhost:8001/v1/embeddings
```

No code changes are required in `backend/services/agent.py` or `backend/services/embeddings.py`.

End-to-end run sequence:

```bash
# terminal 1
python training/scripts/serve_local_model.py --model-id Qwen/Qwen2.5-3B-Instruct --adapter-path training/artifacts/emns-chat-lora-v1 --port 8001

# terminal 2
cd backend
uvicorn main:app --reload

# terminal 3
cd frontend
npm run dev
```

## 7) Recommended Next Dataset Step (Kenyan Localization)

Add a second dataset file with clinician-reviewed Kenyan Swahili/code-switch samples, then merge into the same JSONL format before training.
