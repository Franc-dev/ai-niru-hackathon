# EMNS Qwen Training Workflow

This training path uses a plain Hugging Face LoRA stack:
- MentalChat16K as the base English corpus
- Qwen 2.5 Instruct chat template
- `transformers` + `peft` LoRA fine-tuning
- local FastAPI serving with `/v1/chat` and `/v1/embeddings`

## 1) Environment

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r training/requirements.txt
```

## 2) Build English MentalChat16K Dataset

```bash
python training/scripts/build_english_sft_dataset.py
```

Outputs:
- `data/training/mentalchat16k_en_all.jsonl`
- `data/training/mentalchat16k_en_train.jsonl`
- `data/training/mentalchat16k_en_val.jsonl`
- `data/training/mentalchat16k_en_test.jsonl`
- `data/training/mentalchat16k_en_manifest.json`

## 3) Fine-Tune Qwen 2.5 1.5B

```bash
python training/scripts/train_lora_chat.py ^
  --base-model Qwen/Qwen2.5-1.5B-Instruct ^
  --train-file data/training/mentalchat16k_en_train.jsonl ^
  --eval-file data/training/mentalchat16k_en_val.jsonl ^
  --output-dir training/artifacts/emns-qwen25-en-v1
```

Training details:
- Qwen 2.5 instruct base model
- LoRA on language/attention/MLP modules
- assistant-response-only supervision
- portable `transformers` + `peft` serving artifacts

## 4) Serve the Fine-Tuned Model on Port 8002

```bash
python training/scripts/serve_local_model.py ^
  --model-id Qwen/Qwen2.5-1.5B-Instruct ^
  --adapter-path training/artifacts/emns-qwen25-en-v1 ^
  --port 8002
```

## 5) Red-Team Safety Check

```bash
python training/scripts/run_red_team_eval.py --server-url http://localhost:8002
```

Output:
- `training/reports/red_team_report.json`

## 6) Connect to the Existing Backend

Set these values in `backend/.env`:

```env
LOCAL_MODEL_URL=http://localhost:8002/v1/chat
LOCAL_EMBEDDING_URL=http://localhost:8002/v1/embeddings
```

## 7) End-to-End Run

```bash
# terminal 1
python training/scripts/serve_local_model.py --model-id Qwen/Qwen2.5-1.5B-Instruct --adapter-path training/artifacts/emns-qwen25-en-v1 --port 8002

# terminal 2
cd backend
uvicorn main:app --reload

# terminal 3
cd frontend
npm run dev
```

## Notes

- V1 is English-only fine-tuning.
- Counselor, resource, crisis, safety, and memory routing remain deterministic in the backend.
- Swahili generation or translation is a later phase.
