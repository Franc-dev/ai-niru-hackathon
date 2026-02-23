# EM-NS Training Alignment (Roadmap -> Implementation)

This maps the technical roadmap training requirements to repo implementation.

## Scope Guardrails

- Voice models are not trained. Voice remains external (roadmap-aligned).
- Training focus is chat intelligence only.

## Stage Mapping

1. Stage 1: Baseline Model Selection
- Implemented by `training/scripts/train_lora_chat.py` with configurable base model.
- Default: `Qwen/Qwen2.5-1.5B-Instruct`.

2. Stage 2: Domain Adaptation (Bilingual + Kenyan context)
- Implemented by `training/scripts/build_mentalchat_bilingual.py`.
- Data source: `ShenLab/MentalChat16K`.
- Generates English + translated Swahili records in a shared schema.
- Ready to merge clinician-reviewed Kenyan Swahili/code-switch data in same format.

3. Stage 3: Safety-Centered Instruction Tuning
- Training dataset includes risk tier metadata (`crisis`, `distress`, `seeking_information`).
- Red-team evaluation hook included: `training/scripts/run_red_team_eval.py`.

4. Stage 4: RAG Integration
- Existing backend RAG pipeline remains in:
  - `backend/services/rag.py`
  - `backend/services/vector_db.py`
- Trained chat model connects through:
  - `LOCAL_MODEL_URL`
  - `LOCAL_EMBEDDING_URL`

5. Stage 5: Evaluation and Red-Team Testing
- Baseline red-team suite:
  - `training/evals/red_team_prompts.jsonl`
  - `training/scripts/run_red_team_eval.py`
- Output report:
  - `training/reports/red_team_report.json`

## Operational Governance Hooks

- Data provenance stored per record (`source_dataset`, `translation` metadata).
- Manifest output with counts and split details:
  - `data/training/mentalchat_bilingual_manifest.json`
- Model artifact versioning path:
  - `training/artifacts/<version-name>/`
