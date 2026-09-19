"""Extract Phase 1 features, validate candidates, and train the SHM artifact."""

import argparse
import json
from pathlib import Path

from ml.config import get_dataset_root
from ml.shm.feature_extraction import (
    DEFAULT_GROUPS,
    extract_training_table,
    feature_quality_report,
)
from ml.shm.inference import DEFAULT_ARTIFACT_DIR
from ml.shm.modeling import (
    append_experiment_results,
    fit_and_save_best,
    run_baseline_experiments,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Train the Phase 1 SHM baseline.")
    parser.add_argument("--dataset-root", type=Path, help="Common dataset root; defaults to DATASET_ROOT.")
    parser.add_argument("--artifacts", type=Path, default=DEFAULT_ARTIFACT_DIR)
    parser.add_argument("--features-output", type=Path, default=Path("outputs/features/shm_features.csv"))
    parser.add_argument(
        "--experiments-output",
        type=Path,
        default=Path("outputs/experiments/shm_experiments.csv"),
    )
    parser.add_argument("--oof-output", type=Path, default=Path("outputs/oof/shm_oof.csv"))
    args = parser.parse_args()

    dataset_root = args.dataset_root or get_dataset_root()
    table = extract_training_table(dataset_root, DEFAULT_GROUPS)
    args.features_output.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(args.features_output, index=False)
    quality = feature_quality_report(table)
    print("Feature quality report:")
    print(json.dumps(quality, indent=2))

    results, oof_tables = run_baseline_experiments(table)
    append_experiment_results(results, args.experiments_output)
    best = results.sort_values(["CV_MAPE_mean", "CV_MAPE_std"]).iloc[0]
    args.oof_output.parent.mkdir(parents=True, exist_ok=True)
    oof_tables[str(best["experiment_id"])].to_csv(args.oof_output, index=False)
    metadata = fit_and_save_best(table, results, args.artifacts)
    print("Phase 1 experiment results:")
    print(results.to_string(index=False))
    print("Selected artifact:")
    print(json.dumps(metadata, indent=2, default=str))


if __name__ == "__main__":
    main()
