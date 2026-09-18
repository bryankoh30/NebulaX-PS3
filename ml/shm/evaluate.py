"""Re-run Phase 1 SHM validation without fitting a deployment artifact."""

import argparse
import json
from pathlib import Path

import pandas as pd

from ml.config import get_dataset_root
from ml.shm.feature_extraction import DEFAULT_GROUPS, extract_training_table, feature_quality_report
from ml.shm.modeling import run_baseline_experiments


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate Phase 1 SHM candidates.")
    parser.add_argument("--dataset-root", type=Path, help="Common dataset root; defaults to DATASET_ROOT.")
    parser.add_argument("--features", type=Path, help="Optional previously extracted feature table.")
    args = parser.parse_args()
    table = pd.read_csv(args.features) if args.features else extract_training_table(
        args.dataset_root or get_dataset_root(), DEFAULT_GROUPS
    )
    print(json.dumps(feature_quality_report(table), indent=2))
    results, _ = run_baseline_experiments(table)
    print(results.to_string(index=False))


if __name__ == "__main__":
    main()
