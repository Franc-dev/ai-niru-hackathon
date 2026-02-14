"""
Run full EM-NS training pipeline end-to-end.

Stages:
0) Build combined bilingual dataset (EN + native SW)
1) Build bilingual data from MentalChat16K (legacy fallback)
2) Merge localized Kenyan template data
3) Train Qwen LoRA adapter
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def write_status(path: Path, stage: str, state: str, extra: dict | None = None) -> None:
    payload = {
        "stage": stage,
        "state": state,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    if extra:
        payload.update(extra)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def run_cmd(cmd: list[str], stage: str, status_path: Path) -> None:
    write_status(status_path, stage=stage, state="running", extra={"command": cmd})
    process = subprocess.run(cmd)
    if process.returncode != 0:
        write_status(
            status_path,
            stage=stage,
            state="failed",
            extra={"returncode": process.returncode, "command": cmd},
        )
        raise SystemExit(process.returncode)
    write_status(status_path, stage=stage, state="completed", extra={"command": cmd})


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--python-bin", default=sys.executable)
    parser.add_argument(
        "--skip-combined-build",
        action="store_true",
        help="Skip Stage 0 (combined bilingual dataset build).",
    )
    parser.add_argument("--max-en-rows", type=int, default=0, help="Limit EN rows (0=all)")
    parser.add_argument("--max-sw-rows", type=int, default=0, help="Limit SW rows (0=all)")
    parser.add_argument("--build-backend", choices=("marian", "google"), default="marian")
    parser.add_argument("--build-output-dir", default="data/training")
    parser.add_argument("--build-status-file", default="training/reports/build_status.json")
    parser.add_argument("--build-row-batch-size", type=int, default=16)
    parser.add_argument("--build-translation-batch-size", type=int, default=8)
    parser.add_argument("--build-translation-max-new-tokens", type=int, default=192)
    parser.add_argument("--build-google-max-workers", type=int, default=4)
    parser.add_argument("--build-max-user-chars", type=int, default=3000)
    parser.add_argument("--build-max-assistant-chars", type=int, default=3000)
    parser.add_argument("--build-translation-num-beams", type=int, default=1)
    parser.add_argument("--pipeline-status-file", default="training/reports/pipeline_status.json")
    parser.add_argument("--base-model", default="Qwen/Qwen2.5-3B-Instruct")
    parser.add_argument("--train-file", default="data/training/combined_train.jsonl")
    parser.add_argument("--eval-file", default="data/training/combined_val.jsonl")
    parser.add_argument("--output-dir", default="training/artifacts/emns-chat-lora-v1")
    parser.add_argument("--num-epochs", type=float, default=2.0)
    parser.add_argument("--batch-size", type=int, default=2)
    parser.add_argument("--grad-accum", type=int, default=8)
    parser.add_argument("--max-seq-length", type=int, default=1024)
    parser.add_argument("--target-modules", default="auto")
    parser.add_argument("--no-4bit", action="store_true")
    args = parser.parse_args()

    status_path = Path(args.pipeline_status_file)
    write_status(status_path, stage="pipeline", state="starting")

    # ------------------------------------------------------------------
    # Stage 0: Build combined bilingual dataset (EN + native SW)
    # ------------------------------------------------------------------
    if not args.skip_combined_build:
        combined_cmd = [
            args.python_bin,
            "training/scripts/build_combined_dataset.py",
            "--output-dir",
            args.build_output_dir,
            "--max-en-rows",
            str(args.max_en_rows),
            "--max-sw-rows",
            str(args.max_sw_rows),
        ]
        run_cmd(combined_cmd, stage="build_combined", status_path=status_path)

    build_cmd = [
        args.python_bin,
        "training/scripts/build_mentalchat_bilingual.py",
        "--output-dir",
        args.build_output_dir,
        "--translate-backend",
        args.build_backend,
        "--status-file",
        args.build_status_file,
        "--row-batch-size",
        str(args.build_row_batch_size),
        "--translation-batch-size",
        str(args.build_translation_batch_size),
        "--translation-max-new-tokens",
        str(args.build_translation_max_new_tokens),
        "--google-max-workers",
        str(args.build_google_max_workers),
        "--max-user-chars",
        str(args.build_max_user_chars),
        "--max-assistant-chars",
        str(args.build_max_assistant_chars),
        "--translation-num-beams",
        str(args.build_translation_num_beams),
    ]
    run_cmd(build_cmd, stage="build_bilingual", status_path=status_path)

    merge_cmd = [
        args.python_bin,
        "training/scripts/merge_localized_data.py",
        "--base-jsonl",
        "data/training/mentalchat_bilingual_all.jsonl",
        "--localized-jsonl",
        "training/templates/kenyan_localized_template.jsonl",
        "--output-dir",
        "data/training",
    ]
    run_cmd(merge_cmd, stage="merge_localized", status_path=status_path)

    train_cmd = [
        args.python_bin,
        "training/scripts/train_lora_chat.py",
        "--base-model",
        args.base_model,
        "--train-file",
        args.train_file,
        "--eval-file",
        args.eval_file,
        "--output-dir",
        args.output_dir,
        "--num-epochs",
        str(args.num_epochs),
        "--batch-size",
        str(args.batch_size),
        "--grad-accum",
        str(args.grad_accum),
        "--max-seq-length",
        str(args.max_seq_length),
        "--target-modules",
        args.target_modules,
    ]
    if args.no_4bit:
        train_cmd.append("--no-4bit")
    run_cmd(train_cmd, stage="train_lora", status_path=status_path)

    write_status(status_path, stage="pipeline", state="completed")
    print(f"Pipeline completed. Status file: {status_path}")


if __name__ == "__main__":
    main()
