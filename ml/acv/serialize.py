"""Official ACV prediction CSV serialization."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable, Mapping


def write_predictions(
    records: Iterable[Mapping[str, object]],
    output_path: str | Path,
) -> Path:
    path = Path(output_path)
    rows: list[dict[str, str]] = []
    seen: set[str] = set()
    for record in records:
        file_id = str(record.get("file_id", ""))
        ranked = record.get("ranked_cars")
        if not file_id:
            raise ValueError("ACV prediction record is missing file_id")
        if file_id in seen:
            raise ValueError(f"Duplicate ACV prediction file_id: {file_id}")
        if not isinstance(ranked, list) or not ranked:
            raise ValueError(f"ACV ranking for {file_id} must be a non-empty list")
        car_ids = [str(car_id) for car_id in ranked]
        if len(car_ids) != len(set(car_ids)):
            raise ValueError(f"ACV ranking for {file_id} contains duplicate cars")
        seen.add(file_id)
        rows.append({"file_id": file_id, "ranked_cars": "|".join(car_ids)})

    if not rows:
        raise ValueError("No ACV prediction records to write")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["file_id", "ranked_cars"])
        writer.writeheader()
        writer.writerows(rows)
    return path
