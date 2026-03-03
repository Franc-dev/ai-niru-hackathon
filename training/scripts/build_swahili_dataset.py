"""
Build Swahili-only mental health dataset from HuggingFace.

Dataset: franmwan/swahili-Mental-Health
Output: JSONL files for training

Usage:
    python build_swahili_dataset.py --output-dir data/training
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


# Crisis detection patterns in Swahili
CRISIS_PATTERNS_SW = (
    r"\bkujiua\b",
    r"\bjidhuru\b",
    r"\bkujidhuru\b",
    r"\bkufa\b",
    r"\bkumaliza maisha\b",
    r"\bunyanyasaji\b",
    r"\bdhuluma\b",
    r"\bkujikata\b",
    r"\bnataka kufa\b",
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
    r"\bstress\b",
    r"\bdepression\b",
    r"\banxiety\b",
)


# Default Swahili system prompt (aligned with AGENTS.md)
DEFAULT_SYSTEM_PROMPT_SW = """Wewe ni msaidizi wa afya ya akili (si daktari).
Jibu kwa Kiswahili sanifu pekee - USITUMIE Kiingereza hata neno moja.
Toa majibu mafupi, wazi, yenye huruma.
Toa hatua 3-6 zinazoweza kufanywa sasa.
Usitoe utambuzi wa kitabibu wala dawa.
Ikiwa swali si la afya ya akili, elekeza mazungumzo kurudi kwenye hisia au ustawi wa kihemko.
Ikiwa kuna dalili za hatari ya kujidhuru au kujiua, himiza msaada wa haraka."""


def clean_text(text: str) -> str:
    """Clean and normalize text."""
    if not text:
        return ""
    text = text.replace("\r\n", "\n").strip()
    text = re.sub(r"\n*\s*Response:\s*$", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+\n", "\n", text)
    return text.strip()


def clip_text(text: str, max_chars: int) -> str:
    """Clip text to max characters at sentence boundary."""
    if max_chars <= 0 or len(text) <= max_chars:
        return text
    
    clipped = text[:max_chars]
    last_break = max(
        clipped.rfind(". "),
        clipped.rfind("? "),
        clipped.rfind("! "),
        clipped.rfind("\n"),
    )
    if last_break > int(max_chars * 0.6):
        clipped = clipped[:last_break + 1]
    return clipped.strip()


def infer_risk_tier(user_text: str) -> str:
    """Infer risk tier from user text."""
    text = user_text.lower()
    
    if any(re.search(p, text) for p in CRISIS_PATTERNS_SW):
        return "crisis"
    if any(re.search(p, text) for p in DISTRESS_PATTERNS_SW):
        return "distress"
    return "seeking_information"


def make_record(
    record_id: str,
    risk_tier: str,
    source_dataset: str,
    system_text: str,
    user_text: str,
    assistant_text: str,
) -> dict:
    """Create a standardized training record."""
    return {
        "id": record_id,
        "language": "sw",
        "risk_tier": risk_tier,
        "source_dataset": source_dataset,
        "messages": [
            {"role": "system", "content": system_text},
            {"role": "user", "content": user_text},
            {"role": "assistant", "content": assistant_text},
        ],
        "metadata": {
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
    }


def write_jsonl(path: Path, records: list[dict]) -> None:
    """Write records to JSONL file."""
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
    """Split dataset into train/val/test."""
    rng = random.Random(seed)
    rng.shuffle(records)
    
    n = len(records)
    train_end = int(n * train_ratio)
    val_end = train_end + int(n * val_ratio)
    
    return records[:train_end], records[train_end:val_end], records[val_end:]


def main() -> None:
    parser = argparse.ArgumentParser(description="Build Swahili mental health dataset")
    parser.add_argument("--dataset", default="franmwan/swahili-Mental-Health")
    parser.add_argument("--split", default="train")
    parser.add_argument("--output-dir", default="data/training")
    parser.add_argument("--max-rows", type=int, default=0, help="0 = all rows")
    parser.add_argument("--max-user-chars", type=int, default=2000)
    parser.add_argument("--max-assistant-chars", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--train-ratio", type=float, default=0.90)
    parser.add_argument("--val-ratio", type=float, default=0.05)
    parser.add_argument("--test-ratio", type=float, default=0.05)
    args = parser.parse_args()
    
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load dataset
    print(f"Loading dataset: {args.dataset}...")
    ds = load_dataset(args.dataset, split=args.split)
    
    if args.max_rows > 0:
        ds = ds.select(range(min(args.max_rows, len(ds))))
    
    print(f"Processing {len(ds)} rows...")
    
    all_records: list[dict] = []
    skipped = 0
    
    for idx in tqdm(range(len(ds)), desc="Processing"):
        row = ds[idx]
        
        # Get fields from dataset
        instruction = clean_text(row.get("instruction", "")) or DEFAULT_SYSTEM_PROMPT_SW
        user_text = clip_text(clean_text(row.get("input", "")), args.max_user_chars)
        assistant_text = clip_text(clean_text(row.get("output", "")), args.max_assistant_chars)
        
        # Skip empty records
        if not user_text or not assistant_text:
            skipped += 1
            continue
        
        # Infer risk tier
        risk_tier = infer_risk_tier(user_text)
        
        # Create record
        record = make_record(
            record_id=f"sw_{idx}",
            risk_tier=risk_tier,
            source_dataset=args.dataset,
            system_text=instruction,
            user_text=user_text,
            assistant_text=assistant_text,
        )
        all_records.append(record)
    
    print(f"\nProcessed: {len(all_records)} records")
    print(f"Skipped: {skipped} empty records")
    
    # Count risk tiers
    tier_counts = {}
    for r in all_records:
        tier = r["risk_tier"]
        tier_counts[tier] = tier_counts.get(tier, 0) + 1
    print(f"Risk tier distribution: {tier_counts}")
    
    # Write all records
    all_path = output_dir / "swahili_mental_health_all.jsonl"
    write_jsonl(all_path, all_records)
    print(f"\nWrote {len(all_records)} records to {all_path}")
    
    # Split and write
    train_records, val_records, test_records = split_dataset(
        all_records,
        seed=args.seed,
        train_ratio=args.train_ratio,
        val_ratio=args.val_ratio,
        test_ratio=args.test_ratio,
    )
    
    train_path = output_dir / "swahili_mental_health_train.jsonl"
    val_path = output_dir / "swahili_mental_health_val.jsonl"
    test_path = output_dir / "swahili_mental_health_test.jsonl"
    
    write_jsonl(train_path, train_records)
    write_jsonl(val_path, val_records)
    write_jsonl(test_path, test_records)
    
    print(f"\nSplit files:")
    print(f"  Train: {len(train_records)} records -> {train_path}")
    print(f"  Val:   {len(val_records)} records -> {val_path}")
    print(f"  Test:  {len(test_records)} records -> {test_path}")
    
    # Write manifest
    manifest = {
        "source_dataset": args.dataset,
        "total_records": len(all_records),
        "skipped": skipped,
        "risk_tier_distribution": tier_counts,
        "splits": {
            "train": {"path": str(train_path), "count": len(train_records)},
            "val": {"path": str(val_path), "count": len(val_records)},
            "test": {"path": str(test_path), "count": len(test_records)},
        },
        "seed": args.seed,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    
    manifest_path = output_dir / "swahili_manifest.json"
    with manifest_path.open("w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    
    print(f"\nManifest: {manifest_path}")


if __name__ == "__main__":
    main()
