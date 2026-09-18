"""Inspect the real SHM dataset before feature extraction or modelling."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.stats import skew

from ml.config import get_dataset_root
from ml.shm.data import iter_training_signals, load_labels, resolve_shm_root


def inspect_dataset(dataset_root: str | Path) -> dict[str, object]:
    """Return a concise, JSON-serializable data-quality report."""
    root = resolve_shm_root(dataset_root)
    labels = load_labels(root)
    test_paths = sorted((root / "Test").glob("*.csv"))

    lengths: list[int] = []
    minima: list[float] = []
    maxima: list[float] = []
    means: list[float] = []
    stds: list[float] = []
    digests: dict[str, list[str]] = {}
    missing = 0
    nonfinite = 0
    constants: list[str] = []

    targets: list[float] = []
    for filename, signal, damage in iter_training_signals(root):
        targets.append(damage)
        lengths.append(int(signal.size))
        minima.append(float(np.min(signal)))
        maxima.append(float(np.max(signal)))
        means.append(float(np.mean(signal)))
        std = float(np.std(signal))
        stds.append(std)
        missing += int(np.isnan(signal).sum())
        nonfinite += int((~np.isfinite(signal)).sum())
        if std == 0.0:
            constants.append(filename)
        digest = hashlib.sha256(np.ascontiguousarray(signal).tobytes()).hexdigest()
        digests.setdefault(digest, []).append(filename)

    duplicates = [names for names in digests.values() if len(names) > 1]
    target_array = np.asarray(targets, dtype=float)
    return {
        "train_files": len(labels),
        "test_files": len(test_paths),
        "columns_per_recording": 1,
        "stress_columns": ["column_0"],
        "timestamp_present": False,
        "sampling_interval": None,
        "sampling_frequency": None,
        "observations_per_file": {
            "min": min(lengths),
            "max": max(lengths),
            "unique": sorted(set(lengths)),
        },
        "missing_values": missing,
        "nan_or_inf_values": nonfinite,
        "constant_signals": constants,
        "duplicate_signal_groups": duplicates,
        "signal_range_across_files": {
            "global_min": min(minima),
            "global_max": max(maxima),
            "file_mean_min": min(means),
            "file_mean_max": max(means),
            "file_std_min": min(stds),
            "file_std_max": max(stds),
        },
        "target": {
            "count": int(target_array.size),
            "min": float(np.min(target_array)),
            "median": float(np.median(target_array)),
            "mean": float(np.mean(target_array)),
            "max": float(np.max(target_array)),
            "std": float(np.std(target_array, ddof=1)),
            "skewness": float(skew(target_array, bias=False)),
            "max_to_min_ratio": float(np.max(target_array) / np.min(target_array)),
            "orders_of_magnitude": float(np.log10(np.max(target_array) / np.min(target_array))),
            "zero_or_near_zero_count_le_1e-12": int(np.sum(target_array <= 1e-12)),
        },
        "notes": [
            "The sole headerless numeric column is treated as stress.",
            "No timestamp is supplied, so sampling interval/frequency cannot be established.",
            "File IDs are identifiers only and must not be model features.",
            "All supplied recordings represent healthy operating conditions.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect SHM recordings and labels.")
    parser.add_argument(
        "--dataset-root",
        type=Path,
        help="Common PS3 dataset root or SHM directory; defaults to DATASET_ROOT.",
    )
    parser.add_argument("--output", type=Path, help="Optional JSON report path.")
    args = parser.parse_args()
    report = inspect_dataset(args.dataset_root or get_dataset_root())
    rendered = json.dumps(report, indent=2)
    print(rendered)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
