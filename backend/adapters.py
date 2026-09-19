"""Adapters around frozen subsystem inference and official serializers."""

from __future__ import annotations

from pathlib import Path
import tempfile
from typing import Sequence

from ml.acv.inference import predict_acv, DEFAULT_ARTIFACT_DIR as ACV_ARTIFACT_DIR
from ml.acv.serialize import write_predictions as write_acv
from ml.door.inference import predict_door, DEFAULT_ARTIFACT_DIR as DOOR_ARTIFACT_DIR, MODEL_FILENAME as DOOR_MODEL_FILENAME
from ml.door.predict import write_predictions as write_door
from ml.rail.inference import predict_rail, DEFAULT_ARTIFACT_DIR as RAIL_ARTIFACT_DIR
from ml.rail.serialize import write_predictions as write_rail
from ml.shm.inference import predict_shm, DEFAULT_ARTIFACT_DIR as SHM_ARTIFACT_DIR
from ml.shm.serialize import write_predictions as write_shm


OUTPUT_FILENAMES = {
    "door": "door_predictions.csv",
    "acv": "acv_predictions.csv",
    "rail": "rail_predictions.csv",
    "shm": "shm_predictions.csv",
}


class ArtifactUnavailableError(FileNotFoundError):
    """A configured subsystem cannot run until its frozen artifact is installed."""


def require_artifact(subsystem: str) -> None:
    artifacts = {
        "door": DOOR_ARTIFACT_DIR / DOOR_MODEL_FILENAME,
        "acv": ACV_ARTIFACT_DIR / "ranker_config.json",
        "rail": RAIL_ARTIFACT_DIR / "model.joblib",
        "shm": SHM_ARTIFACT_DIR / "model.joblib",
    }
    if subsystem not in artifacts:
        raise ValueError(f"Unsupported subsystem: {subsystem}")
    if not artifacts[subsystem].is_file():
        raise ArtifactUnavailableError(
            f"{subsystem.upper()} analysis is unavailable because its model artifact is not installed. "
            "Ask the service administrator to install the frozen artifact described in backend/README.md, then submit a new run."
        )


def run_inference(subsystem: str, paths: Sequence[Path]) -> list[dict[str, object]]:
    require_artifact(subsystem)
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
            write_shm(records, path)
        else:
            raise ValueError(f"Unsupported subsystem: {subsystem}")
        return path.read_bytes()
