"""Saved-artifact inference for SHM fatigue-damage regression."""

from pathlib import Path
from typing import Sequence

import joblib
import numpy as np

from ml.shm.data import load_signal
from ml.shm.feature_extraction import extract_signal_features


DEFAULT_ARTIFACT_DIR = Path(__file__).resolve().parent / "artifacts"


def predict_shm(
    input_paths: Sequence[str | Path],
    artifact_dir: str | Path | None = None,
) -> list[dict[str, object]]:
    """Return finite nonnegative predictions using a saved training bundle."""
    paths = [Path(path).expanduser().resolve() for path in input_paths]
    if not paths:
        raise ValueError("At least one SHM input path is required.")
    names = [path.name for path in paths]
    if len(names) != len(set(names)):
        raise ValueError("SHM input paths contain duplicate output file IDs.")

    artifact_path = Path(artifact_dir or DEFAULT_ARTIFACT_DIR).expanduser().resolve()
    model_path = artifact_path / "model.joblib"
    if not model_path.is_file():
        raise FileNotFoundError(
            f"SHM model artifact is unavailable: {model_path}. Run python -m ml.shm.train first."
        )
    bundle = joblib.load(model_path)
    required = {"model", "feature_groups", "feature_names"}
    if not isinstance(bundle, dict) or not required.issubset(bundle):
        raise ValueError(f"Invalid SHM artifact bundle: {model_path}")

    rows: list[list[float]] = []
    for path in paths:
        features = extract_signal_features(load_signal(path), bundle["feature_groups"])
        try:
            rows.append([features[name] for name in bundle["feature_names"]])
        except KeyError as exc:
            raise ValueError(f"Artifact requires an unavailable SHM feature: {exc}") from exc
    predictions = np.asarray(bundle["model"].predict(np.asarray(rows, dtype=float)), dtype=float)
    if not np.isfinite(predictions).all():
        raise ValueError("SHM model produced a non-finite prediction.")
    predictions = np.maximum(predictions, 0.0)
    return [
        {"file_id": path.name, "prediction": float(prediction)}
        for path, prediction in zip(paths, predictions, strict=True)
    ]
