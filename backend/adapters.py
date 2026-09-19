"""Adapters around frozen subsystem inference and official serializers."""

from __future__ import annotations

import csv
from pathlib import Path
import tempfile
from typing import Sequence

from ml.acv.inference import predict_acv
from ml.acv.serialize import write_predictions as write_acv
from ml.door.inference import predict_door
from ml.door.predict import write_predictions as write_door
from ml.rail.inference import predict_rail
from ml.rail.serialize import write_predictions as write_rail
from ml.shm.inference import predict_shm


OUTPUT_FILENAMES = {
    "door": "door_predictions.csv",
    "acv": "acv_predictions.csv",
    "rail": "rail_predictions.csv",
    "shm": "shm_predictions.csv",
}


def run_inference(subsystem: str, paths: Sequence[Path]) -> list[dict[str, object]]:
    if subsystem == "door":
        if len(paths) != 1:
            raise ValueError("Door inference requires exactly one recording")
        return predict_door(paths[0])
    if subsystem == "acv":
        return predict_acv(paths)
    if subsystem == "rail":
        return predict_rail(paths)
    if subsystem == "shm":
        return predict_shm(paths)
    raise ValueError(f"Unsupported subsystem: {subsystem}")


def official_csv(subsystem: str, records: Sequence[dict[str, object]]) -> bytes:
    """Serialize immutable model records with the subsystem's official schema."""
    with tempfile.TemporaryDirectory(prefix="nebulax-export-") as directory:
        path = Path(directory) / OUTPUT_FILENAMES[subsystem]
        if subsystem == "door":
            write_door(list(records), path)
        elif subsystem == "acv":
            write_acv(records, path)
        elif subsystem == "rail":
            write_rail(records, path)
        elif subsystem == "shm":
            with path.open("w", encoding="utf-8", newline="") as stream:
                writer = csv.DictWriter(
                    stream, fieldnames=["file_id", "prediction"], lineterminator="\n"
                )
                writer.writeheader()
                writer.writerows(records)
        else:
            raise ValueError(f"Unsupported subsystem: {subsystem}")
        return path.read_bytes()
