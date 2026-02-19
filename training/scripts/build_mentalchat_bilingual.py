"""
Build bilingual EM-NS chat training data from ShenLab/MentalChat16K.

Outputs JSONL records with this schema:
{
  "id": "123_en",
  "language": "en|sw",
  "risk_tier": "crisis|distress|seeking_information",
  "source_dataset": "ShenLab/MentalChat16K",
  "messages": [
    {"role": "system", "content": "..."},
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "..."}
  ],
  "metadata": {...}
}
"""

from __future__ import annotations

import atexit
import argparse
import concurrent.futures
import json
import os
import random
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from datasets import load_dataset
from tqdm import tqdm


# Aligned with backend/services/agent_prompts.py for training-inference consistency
DEFAULT_SYSTEM_PROMPT = (
    "You are a mental health and emotional support assistant. "
    "Provide safe, supportive, non-judgmental guidance. "
    "Stay within emotional well-being and mental health topics."
)

CRISIS_PATTERNS = (
    r"\bsuicide\b",
    r"\bkill myself\b",
    r"\bself[- ]?harm\b",
    r"\bend my life\b",
    r"\bi want to die\b",
    r"\babuse\b",
)

DISTRESS_PATTERNS = (
    r"\banxious\b",
    r"\bpanic\b",
    r"\boverwhelm",
    r"\bdepress",
    r"\bstress",
    r"\bburnout\b",
    r"\bhopeless\b",
    r"\blost\b",
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
    # Keep natural boundary when possible.
    last_break = max(clipped.rfind(". "), clipped.rfind("? "), clipped.rfind("! "), clipped.rfind("\n"))
    if last_break > int(max_chars * 0.6):
        clipped = clipped[: last_break + 1]
    return clipped.strip()


def infer_risk_tier(user_text: str) -> str:
    text = user_text.lower()
    if any(re.search(p, text) for p in CRISIS_PATTERNS):
        return "crisis"
    if any(re.search(p, text) for p in DISTRESS_PATTERNS):
        return "distress"
    return "seeking_information"


def batched(items: list[str], size: int) -> Iterable[list[str]]:
    for i in range(0, len(items), size):
        yield items[i : i + size]


@dataclass
class MarianTranslator:
    model_name: str = "Helsinki-NLP/opus-mt-en-sw"
    device: str = "auto"
    max_input_length: int = 512
    num_beams: int = 1

    def __post_init__(self) -> None:
        import torch
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

        self._torch = torch
        if self.device == "auto":
            self.device = "cuda" if torch.cuda.is_available() else "cpu"

        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self.model = AutoModelForSeq2SeqLM.from_pretrained(self.model_name)
        self.model.to(self.device)
        self.model.eval()

    def translate_batch(
        self,
        texts: list[str],
        batch_size: int = 8,
        max_new_tokens: int = 256,
    ) -> list[str]:
        if not texts:
            return []

        out: list[str] = []
        for chunk in batched(texts, batch_size):
            encoded = self.tokenizer(
                chunk,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=self.max_input_length,
            )
            encoded = {k: v.to(self.device) for k, v in encoded.items()}
            with self._torch.inference_mode():
                generated = self.model.generate(
                    **encoded,
                    max_new_tokens=max_new_tokens,
                    num_beams=self.num_beams,
                )
            decoded = self.tokenizer.batch_decode(generated, skip_special_tokens=True)
            out.extend(clean_text(x) for x in decoded)
        return out


@dataclass
class GoogleTranslator:
    source: str = "en"
    target: str = "sw"
    max_chars: int = 4500
    max_workers: int = 4
    retries: int = 4
    retry_backoff_seconds: float = 1.5

    def __post_init__(self) -> None:
        from deep_translator import GoogleTranslator as _GoogleTranslator

        self._google_cls = _GoogleTranslator
        self._cache: dict[str, str] = {}

    def _split_text(self, text: str) -> list[str]:
        text = text.strip()
        if not text:
            return [""]
        if len(text) <= self.max_chars:
            return [text]

        paragraphs = [p for p in text.split("\n\n") if p.strip()]
        if len(paragraphs) == 1:
            paragraphs = [p for p in re.split(r"(?<=[.!?])\s+", text) if p.strip()]

        chunks: list[str] = []
        current = ""
        for piece in paragraphs:
            piece = piece.strip()
            if not piece:
                continue
            candidate = f"{current}\n\n{piece}".strip() if current else piece
            if len(candidate) <= self.max_chars:
                current = candidate
            else:
                if current:
                    chunks.append(current)
                    current = ""
                if len(piece) <= self.max_chars:
                    current = piece
                else:
                    # Hard split for very long single segments.
                    for i in range(0, len(piece), self.max_chars):
                        chunks.append(piece[i : i + self.max_chars])
        if current:
            chunks.append(current)
        return chunks or [text[: self.max_chars]]

    def _translate_text(self, text: str) -> str:
        if text in self._cache:
            return self._cache[text]
        parts = self._split_text(text)
        translated_parts = []
        translator = self._google_cls(source=self.source, target=self.target)
        for idx, part in enumerate(parts):
            if not part:
                translated_parts.append("")
                continue
            success = False
            last_error: Exception | None = None
            for attempt in range(self.retries):
                try:
                    translated_parts.append(translator.translate(part))
                    success = True
                    break
                except Exception as exc:  # noqa: BLE001
                    last_error = exc
                    sleep_for = self.retry_backoff_seconds * (attempt + 1)
                    time.sleep(sleep_for)
            if not success:
                raise RuntimeError(f"Google translation failed for part {idx + 1}/{len(parts)}") from last_error

        merged = "\n\n".join(p for p in translated_parts if p is not None)
        self._cache[text] = merged
        return merged

    def translate_batch(
        self,
        texts: list[str],
        batch_size: int = 8,
        max_new_tokens: int = 0,
    ) -> list[str]:
        if not texts:
            return []

        out: list[str] = [""] * len(texts)
        to_run: list[tuple[int, str]] = []
        for i, text in enumerate(texts):
            if not text.strip():
                out[i] = ""
                continue
            if text in self._cache:
                out[i] = clean_text(self._cache[text])
                continue
            to_run.append((i, text))

        if to_run:
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as ex:
                futures = {
                    ex.submit(self._translate_text, text): i
                    for i, text in to_run
                }
                for fut in concurrent.futures.as_completed(futures):
                    i = futures[fut]
                    out[i] = clean_text(fut.result())
        return out


def load_existing_ids(output_jsonl: Path) -> set[str]:
    if not output_jsonl.exists():
        return set()
    ids: set[str] = set()
    with output_jsonl.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                record_id = obj.get("id")
                if record_id:
                    ids.add(record_id)
            except json.JSONDecodeError:
                continue
    return ids


def append_jsonl(path: Path, records: list[dict]) -> None:
    if not records:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


def make_record(
    record_id: str,
    language: str,
    risk_tier: str,
    system_text: str,
    user_text: str,
    assistant_text: str,
    translation: str,
) -> dict:
    return {
        "id": record_id,
        "language": language,
        "risk_tier": risk_tier,
        "source_dataset": "ShenLab/MentalChat16K",
        "messages": [
            {"role": "system", "content": system_text},
            {"role": "user", "content": user_text},
            {"role": "assistant", "content": assistant_text},
        ],
        "metadata": {
            "translation": translation,
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
    }


def split_dataset(
    source_jsonl: Path,
    output_dir: Path,
    seed: int,
    train_ratio: float,
    val_ratio: float,
    test_ratio: float,
) -> dict:
    if round(train_ratio + val_ratio + test_ratio, 6) != 1.0:
        raise ValueError("Split ratios must sum to 1.0")

    records: list[dict] = []
    with source_jsonl.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            records.append(json.loads(line))

    groups: dict[str, list[dict]] = {"en": [], "sw": []}
    for rec in records:
        groups.setdefault(rec.get("language", "en"), []).append(rec)

    rng = random.Random(seed)
    train_records: list[dict] = []
    val_records: list[dict] = []
    test_records: list[dict] = []

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
        train_records.extend(lang_records[:train_end])
        val_records.extend(lang_records[train_end:val_end])
        test_records.extend(lang_records[val_end:])

    rng.shuffle(train_records)
    rng.shuffle(val_records)
    rng.shuffle(test_records)

    train_path = output_dir / "mentalchat_bilingual_train.jsonl"
    val_path = output_dir / "mentalchat_bilingual_val.jsonl"
    test_path = output_dir / "mentalchat_bilingual_test.jsonl"
    for path in (train_path, val_path, test_path):
        if path.exists():
            path.unlink()

    append_jsonl(train_path, train_records)
    append_jsonl(val_path, val_records)
    append_jsonl(test_path, test_records)

    return {
        "train_path": str(train_path),
        "val_path": str(val_path),
        "test_path": str(test_path),
        "train_count": len(train_records),
        "val_count": len(val_records),
        "test_count": len(test_records),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-name", default="ShenLab/MentalChat16K")
    parser.add_argument("--split", default="train")
    parser.add_argument("--output-dir", default="data/training")
    parser.add_argument(
        "--output-file",
        default="mentalchat_bilingual_all.jsonl",
        help="Combined EN+SW output file under --output-dir.",
    )
    parser.add_argument("--limit", type=int, default=0, help="0 means full dataset.")
    parser.add_argument("--include-english", action="store_true", default=True)
    parser.add_argument("--no-english", dest="include_english", action="store_false")
    parser.add_argument("--include-swahili", action="store_true", default=True)
    parser.add_argument("--no-swahili", dest="include_swahili", action="store_false")
    parser.add_argument(
        "--translate-backend",
        choices=("marian", "google", "none"),
        default="google",
    )
    parser.add_argument("--translation-model", default="Helsinki-NLP/opus-mt-en-sw")
    parser.add_argument("--row-batch-size", type=int, default=32)
    parser.add_argument("--translation-batch-size", type=int, default=8)
    parser.add_argument("--translation-max-new-tokens", type=int, default=256)
    parser.add_argument("--translation-num-beams", type=int, default=1)
    parser.add_argument("--max-user-chars", type=int, default=3000)
    parser.add_argument("--max-assistant-chars", type=int, default=3000)
    parser.add_argument("--google-max-workers", type=int, default=4)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--train-ratio", type=float, default=0.9)
    parser.add_argument("--val-ratio", type=float, default=0.05)
    parser.add_argument("--test-ratio", type=float, default=0.05)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument(
        "--status-file",
        default="",
        help="Optional JSON file to update with live progress.",
    )
    parser.add_argument(
        "--lock-dir",
        default="training/reports/build.lock",
        help="Lock directory to prevent concurrent runs.",
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_jsonl = output_dir / args.output_file
    if args.overwrite and output_jsonl.exists():
        output_jsonl.unlink()

    existing_ids = load_existing_ids(output_jsonl)

    lock_dir = Path(args.lock_dir)
    lock_dir.parent.mkdir(parents=True, exist_ok=True)
    pid_file = lock_dir / "pid.txt"
    try:
        lock_dir.mkdir(parents=False, exist_ok=False)
    except FileExistsError as exc:
        existing_pid = ""
        if pid_file.exists():
            existing_pid = pid_file.read_text(encoding="utf-8").strip()
        raise RuntimeError(
            f"Another builder appears to be running (lock: {lock_dir}, pid: {existing_pid})."
        ) from exc

    pid_file.write_text(str(os.getpid()), encoding="utf-8")

    def _cleanup_lock() -> None:
        try:
            if pid_file.exists():
                pid_file.unlink()
            lock_dir.rmdir()
        except OSError:
            pass

    atexit.register(_cleanup_lock)

    translator = None
    translation_label = "source"
    if args.include_swahili:
        if args.translate_backend == "none":
            raise ValueError("Swahili requires --translate-backend marian or google")
        if args.translate_backend == "marian":
            translator = MarianTranslator(
                model_name=args.translation_model,
                num_beams=args.translation_num_beams,
            )
            translation_label = args.translation_model
        else:
            translator = GoogleTranslator(max_workers=args.google_max_workers)
            translation_label = "google-translate"

    dataset = load_dataset(args.dataset_name, split=args.split)
    if args.limit and args.limit > 0:
        dataset = dataset.select(range(min(args.limit, len(dataset))))

    written = 0
    skipped = 0
    english_count = 0
    swahili_count = 0

    def update_status(extra: dict | None = None) -> None:
        if not args.status_file:
            return
        payload = {
            "dataset_name": args.dataset_name,
            "output_file": str(output_jsonl),
            "written_records": written,
            "skipped_records": skipped,
            "english_records": english_count,
            "swahili_records": swahili_count,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        if extra:
            payload.update(extra)
        status_path = Path(args.status_file)
        status_path.parent.mkdir(parents=True, exist_ok=True)
        with status_path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

    update_status({"phase": "starting", "total_rows": len(dataset)})

    for start in tqdm(range(0, len(dataset), args.row_batch_size), desc="Processing rows"):
        end = min(start + args.row_batch_size, len(dataset))
        rows = [dataset[i] for i in range(start, end)]

        to_translate: list[tuple[str, str, str, str, str]] = []
        batch_records: list[dict] = []

        for row_index, row in enumerate(rows, start=start):
            instruction = clean_text(row.get("instruction", "")) or DEFAULT_SYSTEM_PROMPT
            user_text = clip_text(clean_text(row.get("input", "")), args.max_user_chars)
            assistant_text = clip_text(clean_text(row.get("output", "")), args.max_assistant_chars)
            if not user_text or not assistant_text:
                skipped += 1
                continue

            risk_tier = infer_risk_tier(user_text)
            record_key = str(row_index)

            if args.include_english:
                en_id = f"{record_key}_en"
                if en_id not in existing_ids:
                    batch_records.append(
                        make_record(
                            record_id=en_id,
                            language="en",
                            risk_tier=risk_tier,
                            system_text=instruction,
                            user_text=user_text,
                            assistant_text=assistant_text,
                            translation="source",
                        )
                    )
                    existing_ids.add(en_id)
                    english_count += 1
                else:
                    skipped += 1

            if args.include_swahili:
                sw_id = f"{record_key}_sw"
                if sw_id not in existing_ids:
                    to_translate.append((sw_id, risk_tier, instruction, user_text, assistant_text))
                else:
                    skipped += 1

        if to_translate and translator is not None:
            text_block: list[str] = []
            for _, _, system_text, user_text, assistant_text in to_translate:
                text_block.extend([system_text, user_text, assistant_text])

            translated = translator.translate_batch(
                text_block,
                batch_size=args.translation_batch_size,
                max_new_tokens=args.translation_max_new_tokens,
            )
            if len(translated) != len(text_block):
                raise RuntimeError("Translation output size mismatch.")

            for i, (sw_id, risk_tier, _, _, _) in enumerate(to_translate):
                offset = i * 3
                system_sw = translated[offset]
                user_sw = translated[offset + 1]
                assistant_sw = translated[offset + 2]
                batch_records.append(
                    make_record(
                        record_id=sw_id,
                        language="sw",
                        risk_tier=risk_tier,
                        system_text=system_sw,
                        user_text=user_sw,
                        assistant_text=assistant_sw,
                        translation=translation_label,
                    )
                )
                existing_ids.add(sw_id)
                swahili_count += 1

        append_jsonl(output_jsonl, batch_records)
        written += len(batch_records)
        update_status(
            {
                "phase": "processing",
                "start_row": start,
                "end_row": end,
                "total_rows": len(dataset),
            }
        )

    split_info = split_dataset(
        source_jsonl=output_jsonl,
        output_dir=output_dir,
        seed=args.seed,
        train_ratio=args.train_ratio,
        val_ratio=args.val_ratio,
        test_ratio=args.test_ratio,
    )

    manifest = {
        "dataset_name": args.dataset_name,
        "split": args.split,
        "output_file": str(output_jsonl),
        "written_records": written,
        "skipped_records": skipped,
        "english_records": english_count,
        "swahili_records": swahili_count,
        "translation_backend": args.translate_backend if args.include_swahili else "none",
        "translation_model": translation_label if args.include_swahili else "",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "splits": split_info,
    }
    manifest_path = output_dir / "mentalchat_bilingual_manifest.json"
    with manifest_path.open("w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    update_status({"phase": "completed", "manifest_path": str(manifest_path)})
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
