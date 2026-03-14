"""
Build an English SFT dataset directly from MentalChat16K, following the
Qwen LoRA fine-tuning workflow.

Outputs chat-formatted JSONL files under data/training/:
- mentalchat16k_en_all.jsonl
- mentalchat16k_en_train.jsonl
- mentalchat16k_en_val.jsonl
- mentalchat16k_en_test.jsonl
- mentalchat16k_en_manifest.json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from datasets import Dataset, load_dataset


PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = PROJECT_ROOT / "data" / "training"
DEFAULT_SYSTEM_PROMPT = "You are a helpful and empathetic mental health support assistant."


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build English SFT dataset from MentalChat16K")
    parser.add_argument("--dataset-name", default="ShenLab/MentalChat16K")
    parser.add_argument("--dataset-split", default="train[:10000]")
    parser.add_argument("--output-dir", default=str(OUTPUT_DIR))
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def convert_to_messages(example: dict) -> dict:
    instruction = str(example.get("instruction") or "").strip()
    user_input = str(example.get("input") or "").strip()
    assistant_output = str(example.get("output") or "").strip()

    if user_input:
        user_content = f"{instruction}\n\n{user_input}" if instruction else user_input
    else:
        user_content = instruction

    return {
        "messages": [
            {"role": "system", "content": DEFAULT_SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
            {"role": "assistant", "content": assistant_output},
        ],
        "language": "en",
        "source_dataset": "ShenLab/MentalChat16K",
    }


def write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    dataset: Dataset = load_dataset(args.dataset_name, split=args.dataset_split)
    dataset = dataset.map(convert_to_messages, remove_columns=dataset.column_names)
    dataset = dataset.shuffle(seed=args.seed)

    total = len(dataset)
    train_end = int(total * 0.9)
    val_end = int(total * 0.95)

    train_rows = [dataset[index] for index in range(train_end)]
    val_rows = [dataset[index] for index in range(train_end, val_end)]
    test_rows = [dataset[index] for index in range(val_end, total)]
    all_rows = [dataset[index] for index in range(total)]

    write_jsonl(output_dir / "mentalchat16k_en_all.jsonl", all_rows)
    write_jsonl(output_dir / "mentalchat16k_en_train.jsonl", train_rows)
    write_jsonl(output_dir / "mentalchat16k_en_val.jsonl", val_rows)
    write_jsonl(output_dir / "mentalchat16k_en_test.jsonl", test_rows)

    manifest = {
        "dataset_name": args.dataset_name,
        "dataset_split": args.dataset_split,
        "total_examples": total,
        "train_examples": len(train_rows),
        "val_examples": len(val_rows),
        "test_examples": len(test_rows),
        "system_prompt": DEFAULT_SYSTEM_PROMPT,
        "seed": args.seed,
    }
    with (output_dir / "mentalchat16k_en_manifest.json").open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2)

    print(f"Built {total} English MentalChat16K examples into {output_dir}")


if __name__ == "__main__":
    main()
