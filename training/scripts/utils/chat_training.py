from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from datasets import Dataset, load_dataset


def maybe_parse_messages(raw_messages: Any) -> list[dict[str, str]]:
    if isinstance(raw_messages, list):
        return [
            {"role": str(item.get("role", "user")), "content": str(item.get("content", ""))}
            for item in raw_messages
            if isinstance(item, dict)
        ]
    if isinstance(raw_messages, str):
        return maybe_parse_messages(json.loads(raw_messages))
    raise ValueError("messages must be a list or JSON string")


def render_chat_text(tokenizer, messages: list[dict[str, str]], add_generation_prompt: bool = False) -> str:
    rendered = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=add_generation_prompt,
    )
    return rendered.removeprefix("<bos>")


def resolve_dtype(torch_module):
    if torch_module.cuda.is_available():
        if hasattr(torch_module.cuda, "is_bf16_supported") and torch_module.cuda.is_bf16_supported():
            return torch_module.bfloat16
        return torch_module.float16
    return torch_module.float32


def resolve_target_modules(model, requested: str | None = None) -> list[str]:
    del model
    if requested:
        return [item.strip() for item in requested.split(",") if item.strip()]
    return [
        "q_proj",
        "k_proj",
        "v_proj",
        "o_proj",
        "gate_proj",
        "up_proj",
        "down_proj",
    ]


def build_text_dataset(dataset_path: str, tokenizer, max_records: int = 0):
    ds = load_dataset("json", data_files=dataset_path, split="train")
    if max_records > 0:
        ds = ds.select(range(min(max_records, len(ds))))

    def _format(example: dict[str, Any]) -> dict[str, str]:
        messages = maybe_parse_messages(example["messages"])
        return {"text": render_chat_text(tokenizer, messages)}

    return ds.map(
        _format,
        remove_columns=ds.column_names,
        desc=f"Formatting {Path(dataset_path).name}",
    )


def build_assistant_only_dataset(dataset_path: str, tokenizer, max_records: int = 0, max_seq_length: int = 2048) -> Dataset:
    source = load_dataset("json", data_files=dataset_path, split="train")
    if max_records > 0:
        source = source.select(range(min(max_records, len(source))))

    tokenized_examples: list[dict[str, list[int]]] = []

    for row in source:
        messages = maybe_parse_messages(row["messages"])
        history: list[dict[str, str]] = []

        for message in messages:
            role = message.get("role", "user")
            if role == "assistant" and history:
                prompt_text = render_chat_text(tokenizer, history, add_generation_prompt=True)
                full_text = render_chat_text(tokenizer, history + [message], add_generation_prompt=False)

                prompt_ids = tokenizer(prompt_text, add_special_tokens=False)["input_ids"]
                full_ids = tokenizer(full_text, add_special_tokens=False)["input_ids"]

                prefix_len = 0
                for prompt_token, full_token in zip(prompt_ids, full_ids):
                    if prompt_token != full_token:
                        break
                    prefix_len += 1

                labels = [-100] * prefix_len + full_ids[prefix_len:]
                if len(full_ids) > max_seq_length:
                    full_ids = full_ids[-max_seq_length:]
                    labels = labels[-max_seq_length:]

                if any(label != -100 for label in labels):
                    tokenized_examples.append(
                        {
                            "input_ids": full_ids,
                            "attention_mask": [1] * len(full_ids),
                            "labels": labels,
                        }
                    )

            history.append(message)

    if not tokenized_examples:
        raise ValueError(f"No assistant training examples could be built from {dataset_path}")

    return Dataset.from_list(tokenized_examples)
