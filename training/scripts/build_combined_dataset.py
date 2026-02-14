"""
Build combined bilingual EM-NS training dataset from two HuggingFace sources.

English: ShenLab/MentalChat16K (~16K rows)
Swahili: franmwan/swahili-Mental-Health (~9K rows, native Swahili)

Outputs JSONL records with this schema:
{
  "id": "en_123" | "sw_456",
  "language": "en" | "sw",
  "risk_tier": "crisis" | "distress" | "seeking_information",
  "source_dataset": "ShenLab/MentalChat16K" | "franmwan/swahili-Mental-Health",
  "messages": [
    {"role": "system", "content": "..."},
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "..."}
  ],
  "metadata": {...}
}
"""

from __future__ import annotations

import argparse
import json
import random
import re
from datetime import datetime, timezone
from pathlib import Path

from datasets import load_dataset
from tqdm import tqdm

# ---------------------------------------------------------------------------
# Reuse text-processing helpers from the original bilingual builder
# ---------------------------------------------------------------------------

CRISIS_PATTERNS_EN = (
    r"\bsuicide\b",
    r"\bkill myself\b",
    r"\bself[- ]?harm\b",
    r"\bend my life\b",
    r"\bi want to die\b",
    r"\babuse\b",
)

DISTRESS_PATTERNS_EN = (
    r"\banxious\b",
    r"\bpanic\b",
    r"\boverwhelm",
    r"\bdepress",
    r"\bstress",
    r"\bburnout\b",
    r"\bhopeless\b",
    r"\blost\b",
)

CRISIS_PATTERNS_SW = (
    r"\bkujiua\b",
    r"\bjidhuru\b",
    r"\bkujidhuru\b",
    r"\bkufa\b",
    r"\bkumaliza maisha\b",
    r"\bunyanyasaji\b",
    r"\bdhuluma\b",
)

DISTRESS_PATTERNS_SW = (
    r"\bwasiwasi\b",
    r"\bmsongo\b",
    r"\bhuzuni\b",
    r"\bsonona\b",
    r"\bhofu\b",
    r"\bkukata tamaa\b",
    r"\bshida\b",
    r"\bdhiki\b",
    r"\bmawazo\b",
)

DEFAULT_SYSTEM_PROMPT_EN = (
    "You are a helpful mental health counselling assistant. "
    "Provide safe, supportive, non-judgmental guidance."
)

DEFAULT_SYSTEM_PROMPT_SW = (
    "Wewe ni msaidizi wa ushauri wa afya ya akili. "
    "Toa mwongozo salama, wa kusaidia, na usio na hukumu."
)


def clean_text(text: str) -> str:
    if not text:
        return ""
    text = text.replace("\r\n", "\n").strip()
    text = re.sub(r"\n*\s*Response:\s*$", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+\n", "\n", text)
    return text.strip()


def clip_text(text: str, max_chars: int) -> str:
    if max_chars <= 0:
        return text
    if len(text) <= max_chars:
        return text
    clipped = text[:max_chars]
    last_break = max(
        clipped.rfind(". "), clipped.rfind("? "),
        clipped.rfind("! "), clipped.rfind("\n"),
    )
    if last_break > int(max_chars * 0.6):
        clipped = clipped[: last_break + 1]
    return clipped.strip()


def infer_risk_tier(user_text: str, language: str = "en") -> str:
    text = user_text.lower()
    if language == "sw":
        if any(re.search(p, text) for p in CRISIS_PATTERNS_SW):
            return "crisis"
        if any(re.search(p, text) for p in DISTRESS_PATTERNS_SW):
            return "distress"
    # Also check English patterns (code-switching is common)
    if any(re.search(p, text) for p in CRISIS_PATTERNS_EN):
        return "crisis"
    if any(re.search(p, text) for p in DISTRESS_PATTERNS_EN):
        return "distress"
    return "seeking_information"


# ---------------------------------------------------------------------------
# Record builder
# ---------------------------------------------------------------------------

def make_record(
    record_id: str,
    language: str,
    risk_tier: str,
    source_dataset: str,
    system_text: str,
    user_text: str,
    assistant_text: str,
) -> dict:
    return {
        "id": record_id,
        "language": language,
        "risk_tier": risk_tier,
        "source_dataset": source_dataset,
        "messages": [
            {"role": "system", "content": system_text},
            {"role": "user", "content": user_text},
            {"role": "assistant", "content": assistant_text},
        ],
        "metadata": {
            "translation": "native",
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
    }


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------

def write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


def split_dataset(
    records: list[dict],
    seed: int,
    train_ratio: float = 0.90,
    val_ratio: float = 0.05,
    test_ratio: float = 0.05,
) -> tuple[list[dict], list[dict], list[dict]]:
    """Stratified split preserving language balance."""
    if round(train_ratio + val_ratio + test_ratio, 6) != 1.0:
        raise ValueError("Split ratios must sum to 1.0")

    groups: dict[str, list[dict]] = {}
    for rec in records:
        lang = rec.get("language", "en")
        groups.setdefault(lang, []).append(rec)

    rng = random.Random(seed)
    train_all: list[dict] = []
    val_all: list[dict] = []
    test_all: list[dict] = []

    for lang_records in groups.values():
        rng.shuffle(lang_records)
        n = len(lang_records)
        train_end = int(n * train_ratio)
        val_count = int(n * val_ratio)
        test_count = n - train_end - val_count
        if n >= 3 and val_ratio > 0 and val_count == 0:
            val_count = 1
        if n >= 3 and test_ratio > 0 and test_count == 0:
            test_count = 1
        train_end = max(0, n - val_count - test_count)
        val_end = train_end + val_count
        train_all.extend(lang_records[:train_end])
        val_all.extend(lang_records[train_end:val_end])
        test_all.extend(lang_records[val_end:])

    rng.shuffle(train_all)
    rng.shuffle(val_all)
    rng.shuffle(test_all)
    return train_all, val_all, test_all


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build combined EN+SW mental-health training dataset"
    )
    parser.add_argument("--en-dataset", default="ShenLab/MentalChat16K")
    parser.add_argument("--en-split", default="train")
    parser.add_argument("--sw-dataset", default="franmwan/swahili-Mental-Health")
    parser.add_argument("--sw-split", default="train")
    parser.add_argument("--output-dir", default="data/training")
    parser.add_argument("--max-en-rows", type=int, default=0, help="0 = all rows")
    parser.add_argument("--max-sw-rows", type=int, default=0, help="0 = all rows")
    parser.add_argument("--max-user-chars", type=int, default=3000)
    parser.add_argument("--max-assistant-chars", type=int, default=3000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--train-ratio", type=float, default=0.90)
    parser.add_argument("--val-ratio", type=float, default=0.05)
    parser.add_argument("--test-ratio", type=float, default=0.05)
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    all_records: list[dict] = []

    # ------------------------------------------------------------------
    # Load English dataset: ShenLab/MentalChat16K
    # ------------------------------------------------------------------
    print(f"Loading English dataset: {args.en_dataset} ...")
    en_ds = load_dataset(args.en_dataset, split=args.en_split)
    if args.max_en_rows > 0:
        en_ds = en_ds.select(range(min(args.max_en_rows, len(en_ds))))

    en_skipped = 0
    for idx in tqdm(range(len(en_ds)), desc="Processing EN"):
        row = en_ds[idx]
        instruction = clean_text(row.get("instruction", "")) or DEFAULT_SYSTEM_PROMPT_EN
        user_text = clip_text(clean_text(row.get("input", "")), args.max_user_chars)
        assistant_text = clip_text(clean_text(row.get("output", "")), args.max_assistant_chars)
        if not user_text or not assistant_text:
            en_skipped += 1
            continue
        risk_tier = infer_risk_tier(user_text, language="en")
        all_records.append(
            make_record(
                record_id=f"en_{idx}",
                language="en",
                risk_tier=risk_tier,
                source_dataset=args.en_dataset,
                system_text=instruction,
                user_text=user_text,
                assistant_text=assistant_text,
            )
        )

    en_count = sum(1 for r in all_records if r["language"] == "en")
    print(f"  EN records: {en_count} (skipped {en_skipped})")

    # ------------------------------------------------------------------
    # Load Swahili dataset: franmwan/swahili-Mental-Health
    # ------------------------------------------------------------------
    print(f"Loading Swahili dataset: {args.sw_dataset} ...")
    sw_ds = load_dataset(args.sw_dataset, split=args.sw_split)
    if args.max_sw_rows > 0:
        sw_ds = sw_ds.select(range(min(args.max_sw_rows, len(sw_ds))))

    sw_skipped = 0
    for idx in tqdm(range(len(sw_ds)), desc="Processing SW"):
        row = sw_ds[idx]
        # Use the instruction field from the dataset as the system prompt,
        # fall back to our default Swahili prompt
        instruction = clean_text(row.get("instruction", "")) or DEFAULT_SYSTEM_PROMPT_SW
        user_text = clip_text(clean_text(row.get("input", "")), args.max_user_chars)
        assistant_text = clip_text(clean_text(row.get("output", "")), args.max_assistant_chars)
        if not user_text or not assistant_text:
            sw_skipped += 1
            continue
        risk_tier = infer_risk_tier(user_text, language="sw")
        all_records.append(
            make_record(
                record_id=f"sw_{idx}",
                language="sw",
                risk_tier=risk_tier,
                source_dataset=args.sw_dataset,
                system_text=instruction,
                user_text=user_text,
                assistant_text=assistant_text,
            )
        )

    sw_count = sum(1 for r in all_records if r["language"] == "sw")
    print(f"  SW records: {sw_count} (skipped {sw_skipped})")

    # ------------------------------------------------------------------
    # Write combined "all" file
    # ------------------------------------------------------------------
    all_path = output_dir / "combined_all.jsonl"
    write_jsonl(all_path, all_records)
    print(f"Wrote {len(all_records)} total records to {all_path}")

    # ------------------------------------------------------------------
    # Stratified split
    # ------------------------------------------------------------------
    train_records, val_records, test_records = split_dataset(
        all_records,
        seed=args.seed,
        train_ratio=args.train_ratio,
        val_ratio=args.val_ratio,
        test_ratio=args.test_ratio,
    )

    train_path = output_dir / "combined_train.jsonl"
    val_path = output_dir / "combined_val.jsonl"
    test_path = output_dir / "combined_test.jsonl"

    write_jsonl(train_path, train_records)
    write_jsonl(val_path, val_records)
    write_jsonl(test_path, test_records)

    # ------------------------------------------------------------------
    # Manifest
    # ------------------------------------------------------------------
    manifest = {
        "english_dataset": args.en_dataset,
        "swahili_dataset": args.sw_dataset,
        "total_records": len(all_records),
        "english_records": en_count,
        "swahili_records": sw_count,
        "english_skipped": en_skipped,
        "swahili_skipped": sw_skipped,
        "splits": {
            "train": {"path": str(train_path), "count": len(train_records)},
            "val": {"path": str(val_path), "count": len(val_records)},
            "test": {"path": str(test_path), "count": len(test_records)},
        },
        "seed": args.seed,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    manifest_path = output_dir / "combined_manifest.json"
    with manifest_path.open("w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    print(f"\nManifest: {manifest_path}")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
