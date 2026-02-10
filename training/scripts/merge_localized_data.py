"""
Merge localized Kenyan data into the bilingual training corpus.
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path


def read_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def validate_row(row: dict) -> None:
    for key in ("id", "language", "messages"):
        if key not in row:
            raise ValueError(f"Missing key '{key}' in row: {row}")
    if row["language"] not in ("en", "sw"):
        raise ValueError(f"Unsupported language '{row['language']}' in row id={row.get('id')}")
    if not isinstance(row["messages"], list) or len(row["messages"]) < 2:
        raise ValueError(f"Invalid messages in row id={row.get('id')}")


def split_by_language(rows: list[dict], seed: int, train_ratio: float, val_ratio: float, test_ratio: float) -> tuple[list[dict], list[dict], list[dict]]:
    if round(train_ratio + val_ratio + test_ratio, 6) != 1.0:
        raise ValueError("Split ratios must sum to 1.0")

    groups: dict[str, list[dict]] = {"en": [], "sw": []}
    for row in rows:
        groups.setdefault(row.get("language", "en"), []).append(row)

    rng = random.Random(seed)
    train_rows: list[dict] = []
    val_rows: list[dict] = []
    test_rows: list[dict] = []
    for group in groups.values():
        rng.shuffle(group)
        n = len(group)
        train_end = int(n * train_ratio)
        val_count = int(n * val_ratio)
        test_count = n - train_end - val_count
        if n >= 3 and val_ratio > 0 and val_count == 0:
            val_count = 1
        if n >= 3 and test_ratio > 0 and test_count == 0:
            test_count = 1
        train_end = max(0, n - val_count - test_count)
        val_end = train_end + val_count
        train_rows.extend(group[:train_end])
        val_rows.extend(group[train_end:val_end])
        test_rows.extend(group[val_end:])

    rng.shuffle(train_rows)
    rng.shuffle(val_rows)
    rng.shuffle(test_rows)
    return train_rows, val_rows, test_rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-jsonl", default="data/training/mentalchat_bilingual_all.jsonl")
    parser.add_argument("--localized-jsonl", default="training/templates/kenyan_localized_template.jsonl")
    parser.add_argument("--output-dir", default="data/training")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--train-ratio", type=float, default=0.9)
    parser.add_argument("--val-ratio", type=float, default=0.05)
    parser.add_argument("--test-ratio", type=float, default=0.05)
    args = parser.parse_args()

    base_rows = read_jsonl(Path(args.base_jsonl))
    localized_rows = read_jsonl(Path(args.localized_jsonl))
    for row in localized_rows:
        validate_row(row)

    existing_ids = {row["id"] for row in base_rows if "id" in row}
    merged_rows = list(base_rows)
    added = 0
    for row in localized_rows:
        if row["id"] in existing_ids:
            continue
        merged_rows.append(row)
        existing_ids.add(row["id"])
        added += 1

    output_dir = Path(args.output_dir)
    merged_path = output_dir / "mentalchat_bilingual_merged.jsonl"
    write_jsonl(merged_path, merged_rows)

    train_rows, val_rows, test_rows = split_by_language(
        merged_rows,
        seed=args.seed,
        train_ratio=args.train_ratio,
        val_ratio=args.val_ratio,
        test_ratio=args.test_ratio,
    )
    write_jsonl(output_dir / "mentalchat_bilingual_train.jsonl", train_rows)
    write_jsonl(output_dir / "mentalchat_bilingual_val.jsonl", val_rows)
    write_jsonl(output_dir / "mentalchat_bilingual_test.jsonl", test_rows)

    summary = {
        "base_count": len(base_rows),
        "localized_count": len(localized_rows),
        "added_localized": added,
        "merged_count": len(merged_rows),
        "train_count": len(train_rows),
        "val_count": len(val_rows),
        "test_count": len(test_rows),
        "merged_path": str(merged_path),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
