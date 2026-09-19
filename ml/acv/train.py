"""Freeze the transparent ACV ranking configuration."""

import argparse
from datetime import datetime, timezone
import importlib.metadata
import json
from pathlib import Path

from ml.config import get_dataset_root

from .data import load_workbook, resolve_acv_root, summarize_schema
from .ranker import RankerConfig


def main() -> None:
    parser = argparse.ArgumentParser(description="Freeze the ACV ranker configuration.")
    parser.add_argument("--dataset-root", type=Path, help="Dataset root; defaults to DATASET_ROOT")
    parser.add_argument("--artifacts", type=Path, help="Artifact directory")
    args = parser.parse_args()

    dataset_root = args.dataset_root if args.dataset_root is not None else get_dataset_root()
    acv_root = resolve_acv_root(dataset_root)
    training_paths = sorted((acv_root / "Train").glob("*.xlsx"), key=lambda item: item.name)
    if not training_paths:
        raise ValueError(f"No ACV training workbooks found in {acv_root / 'Train'}")
    workbooks = [load_workbook(path) for path in training_paths]

    output_dir = args.artifacts or Path(__file__).resolve().parent / "artifacts"
    output_dir.mkdir(parents=True, exist_ok=True)
    config = RankerConfig()
    config_path = output_dir / "ranker_config.json"
    metadata_path = output_dir / "metadata.json"
    with config_path.open("w", encoding="utf-8") as handle:
        json.dump(config.to_dict(), handle, indent=2, sort_keys=True)
        handle.write("\n")
    metadata = {
        "artifact_version": 1,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "approach": "fixed_schema_aware_peer_ranking",
        "training_cases": len(workbooks),
        "schemas": summarize_schema(workbooks),
        "dependencies": {
            package: importlib.metadata.version(package)
            for package in ("numpy", "pandas", "openpyxl")
        },
    }
    with metadata_path.open("w", encoding="utf-8") as handle:
        json.dump(metadata, handle, indent=2, sort_keys=True)
        handle.write("\n")
    print(f"Wrote ACV configuration to {config_path}")
    print(f"Wrote ACV metadata to {metadata_path}")


if __name__ == "__main__":
    main()
