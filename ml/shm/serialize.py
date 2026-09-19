"""Single validated CSV serializer shared by the CLI and backend."""
import csv
import math
from numbers import Real
from pathlib import Path

CSV_COLUMNS = ["file_id", "prediction"]


def write_predictions(records, output_path):
    rows = list(records)
    if not rows:
        raise ValueError("No SHM predictions to export.")
    seen = set()
    for row in rows:
        if set(row) != set(CSV_COLUMNS):
            raise ValueError("SHM records must contain exactly file_id,prediction.")
        file_id, prediction = row["file_id"], row["prediction"]
        if (not isinstance(file_id, str) or not file_id or "/" in file_id or "\\" in file_id
                or file_id in {".", ".."} or file_id in seen):
            raise ValueError("Invalid or duplicate SHM file_id.")
        if isinstance(prediction, bool) or not isinstance(prediction, Real) or not math.isfinite(prediction) or prediction < 0:
            raise ValueError("SHM prediction must be a finite, nonnegative number.")
        seen.add(file_id)
    # Validate the entire batch before touching the destination.
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=CSV_COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
