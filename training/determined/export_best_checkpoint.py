"""
Export the best Determined checkpoint as a HuggingFace LoRA adapter.

Usage:
    python training/determined/export_best_checkpoint.py --experiment-id 1
    python training/determined/export_best_checkpoint.py --experiment-id 1 --output-dir training/artifacts/det-best-lora
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export best Determined checkpoint as HF LoRA adapter"
    )
    parser.add_argument(
        "--experiment-id", type=int, required=True, help="Determined experiment ID"
    )
    parser.add_argument(
        "--master-url",
        default="http://localhost:8080",
        help="Determined master URL",
    )
    parser.add_argument(
        "--output-dir",
        default="training/artifacts/det-best-lora",
        help="Directory to export adapter files to",
    )
    parser.add_argument(
        "--metric",
        default="eval_loss",
        help="Metric to select best checkpoint by",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    from determined.experimental import Determined

    client = Determined(master=args.master_url)

    print(f"Fetching experiment {args.experiment_id} from {args.master_url}...")
    experiment = client.get_experiment(args.experiment_id)

    # Get the best checkpoint ordered by the target metric
    best_checkpoint = experiment.top_checkpoint(
        sort_by=args.metric, smaller_is_better=True
    )
    if best_checkpoint is None:
        print("ERROR: No checkpoints found for this experiment.")
        raise SystemExit(1)

    trial_id = best_checkpoint.trial_id
    print(f"Best trial: {trial_id}")
    print(f"Checkpoint UUID: {best_checkpoint.uuid}")

    # Download checkpoint to a temp dir, then copy adapter files
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    download_path = Path(f"/tmp/det-checkpoint-{best_checkpoint.uuid}")
    if download_path.exists():
        shutil.rmtree(download_path)

    print(f"Downloading checkpoint to {download_path}...")
    best_checkpoint.download(str(download_path))

    # Look for adapter files (PEFT format) in the downloaded checkpoint
    adapter_config = None
    for candidate in [download_path, download_path / "checkpoint"]:
        if (candidate / "adapter_config.json").exists():
            adapter_config = candidate
            break

    if adapter_config is None:
        # Fall back: search recursively
        found = list(download_path.rglob("adapter_config.json"))
        if found:
            adapter_config = found[0].parent
        else:
            print("ERROR: Could not find adapter_config.json in checkpoint.")
            print(f"Checkpoint contents: {list(download_path.rglob('*'))}")
            raise SystemExit(1)

    # Copy adapter files to output directory
    print(f"Found adapter at: {adapter_config}")
    for f in adapter_config.iterdir():
        if f.is_file():
            dest = output_dir / f.name
            shutil.copy2(f, dest)
            print(f"  Copied: {f.name}")

    # Validate required files exist
    required = ["adapter_config.json"]
    safetensors = output_dir / "adapter_model.safetensors"
    bin_file = output_dir / "adapter_model.bin"
    if not safetensors.exists() and not bin_file.exists():
        print("WARNING: Neither adapter_model.safetensors nor adapter_model.bin found.")

    for req in required:
        if not (output_dir / req).exists():
            print(f"ERROR: Required file {req} not found in exported checkpoint.")
            raise SystemExit(1)

    print(f"\nSuccessfully exported best checkpoint to: {output_dir}")
    print(f"  Trial ID: {trial_id}")
    print(f"  Files: {[f.name for f in output_dir.iterdir() if f.is_file()]}")


if __name__ == "__main__":
    main()
