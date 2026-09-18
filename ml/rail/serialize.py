"""Reusable exact official Rail CSV export."""
import csv
from pathlib import Path

from .data import CLASSES


def write_predictions(records, output_path):
    records = list(records)
    if not records:
        raise ValueError("No predictions to export")
    seen = set()
    for row in records:
        if set(row) != {"file_id", "prediction"}:
            raise ValueError("Rail records must contain exactly file_id,prediction")
        file_id = row["file_id"]
        if not isinstance(file_id, str) or not file_id or Path(file_id).name != file_id or file_id in seen:
            raise ValueError("Invalid or duplicate file_id")
        if row["prediction"] not in CLASSES:
            raise ValueError("Invalid Rail prediction label")
        seen.add(file_id)
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["file_id", "prediction"], lineterminator="\n")
        writer.writeheader()
        writer.writerows(records)
