"""Standalone Door prediction CLI and CSV serializer.

Usage (from repository root):

    python -m ml.door.predict --input Test.csv --output door_predictions.csv
    python -m ml.door.predict --input Test.csv --output out.csv --artifacts DIR

Writes a CSV with exactly the columns ``start_time,end_time,prediction`` — one
row per detected cycle.  A successful invocation always means a real prediction
file was written; on any error nothing is written and a clear message is shown.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from ml.door.inference import predict_door

CSV_COLUMNS = ["start_time", "end_time", "prediction"]


def write_predictions(records: list[dict[str, object]], output_path: str | Path) -> None:
    """Serialize Door prediction records to CSV in the exact required schema.

    No dataframe index, no extra columns beyond ``start_time,end_time,prediction``.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for rec in records:
            writer.writerow({col: rec[col] for col in CSV_COLUMNS})


def main() -> None:
    parser = argparse.ArgumentParser(description="Predict Door cycles from a continuous recording.")
    parser.add_argument("--input", type=Path, required=True, help="One continuous CSV recording.")
    parser.add_argument("--output", type=Path, required=True, help="Destination door_predictions.csv.")
    parser.add_argument(
        "--artifacts",
        type=Path,
        default=None,
        help="Saved artifact directory; defaults to this package's artifacts/.",
    )
    args = parser.parse_args()

    records = predict_door(args.input, artifact_dir=args.artifacts)
    write_predictions(records, args.output)
    n_abnormal = sum(1 for r in records if r["prediction"] == "Abnormal resistance")
    print(
        f"Wrote {len(records)} predicted cycles "
        f"({n_abnormal} Abnormal resistance, {len(records) - n_abnormal} Normal) "
        f"-> {args.output}"
    )


if __name__ == "__main__":
    main()
