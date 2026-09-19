"""Case-level ACV validation using the official rank-decay metric."""

import argparse
import json
from pathlib import Path

import pandas as pd

from ml.config import get_dataset_root

from .data import load_workbook, resolve_acv_root
from .inference import load_config
from .ranker import rank_decay_score, rank_workbook


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate ACV localisation by whole workbook.")
    parser.add_argument("--dataset-root", type=Path, help="Dataset root; defaults to DATASET_ROOT")
    parser.add_argument("--artifacts", type=Path, help="Artifact directory")
    parser.add_argument("--output", type=Path, help="Optional JSON report path")
    args = parser.parse_args()

    dataset_root = args.dataset_root if args.dataset_root is not None else get_dataset_root()
    acv_root = resolve_acv_root(dataset_root)
    labels = pd.read_csv(acv_root / "Train_Labels.csv", dtype=str)
    expected_columns = {"filename", "faulty_car"}
    if not expected_columns.issubset(labels.columns):
        raise ValueError(f"ACV labels must contain columns: {sorted(expected_columns)}")
    config = load_config(args.artifacts)

    cases: list[dict[str, object]] = []
    for row in labels.itertuples(index=False):
        path = acv_root / "Train" / row.filename
        result = rank_workbook(load_workbook(path), config)
        true_car = str(row.faulty_car)
        score = rank_decay_score(result.ranked_cars, true_car)
        rank = result.ranked_cars.index(true_car) + 1 if true_car in result.ranked_cars else None
        case = {
            "file_id": path.name,
            "true_car": true_car,
            "rank": rank,
            "car_count": len(result.ranked_cars),
            "score": score,
            "ranked_cars": result.ranked_cars,
            "parameters_used": result.parameters_used,
        }
        cases.append(case)
        print(
            f"{path.name}: true={true_car} rank={rank}/{len(result.ranked_cars)} "
            f"score={score:.3f} ranking={'|'.join(result.ranked_cars)}"
        )

    mean_score = float(sum(float(case["score"]) for case in cases) / len(cases))
    report = {
        "protocol": "leave-one-workbook-out equivalent for a fixed, label-free ranker",
        "metric": "mean_linear_rank_decay",
        "mean_score": mean_score,
        "cases": cases,
        "limitations": [
            "Only six documented one-fault cases are available.",
            "The fixed ranker is not a calibrated probability model.",
            "The dataset cannot validate no-fault detection or leak quantity.",
        ],
    }
    print(f"Mean ACV rank-decay score: {mean_score:.4f}")
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("w", encoding="utf-8") as handle:
            json.dump(report, handle, indent=2)
            handle.write("\n")
        print(f"Wrote evaluation report to {args.output}")


if __name__ == "__main__":
    main()
