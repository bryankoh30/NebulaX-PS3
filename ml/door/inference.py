"""Door inference: segment a continuous stream and classify each cycle.

Public contract (see contracts/model.md):

    predict_door(input_path, artifact_dir=None) -> list[dict]

Each returned record has ``start_time``, ``end_time`` (timezone-free ISO
timestamps with milliseconds) and ``prediction`` (exactly ``Normal`` or
``Abnormal resistance``).  Inference loads the saved model, never trains, and
raises explicit errors on missing artifacts or invalid input.
"""

from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np

from ml.door.features import extract_features
from ml.door.loader import format_timestamp, load_stream, segment_stream

DEFAULT_ARTIFACT_DIR = Path(__file__).resolve().parent / "artifacts"
MODEL_FILENAME = "door_classifier.joblib"


def _resolve_artifact_dir(artifact_dir: str | Path | None) -> Path:
    if artifact_dir is None:
        return DEFAULT_ARTIFACT_DIR
    return Path(artifact_dir)


def _load_model(artifact_dir: Path) -> dict:
    model_path = artifact_dir / MODEL_FILENAME
    if not model_path.is_file():
        raise FileNotFoundError(
            f"Door model artifact not found: {model_path}. "
            "Run `python -m ml.door.train --full` to generate it."
        )
    bundle = joblib.load(model_path)
    if "classifier" not in bundle or "feature_names" not in bundle:
        raise ValueError(f"Corrupt Door model artifact: {model_path}")
    return bundle


def predict_door(
    input_path: str | Path,
    artifact_dir: str | Path | None = None,
) -> list[dict[str, object]]:
    """Detect door cycles in a continuous recording and classify each one.

    Parameters
    ----------
    input_path:
        Path to one continuous Door CSV recording (e.g. ``Test.csv``).
    artifact_dir:
        Directory containing ``door_classifier.joblib``.  Defaults to this
        package's ``artifacts/`` directory.

    Returns
    -------
    list[dict]
        One dict per detected cycle with keys ``start_time``, ``end_time``,
        ``prediction``.  Ordered chronologically by cycle start.

    Raises
    ------
    FileNotFoundError
        If the input file or model artifact is missing.
    ValueError
        If the input has no rows.
    """
    input_path = Path(input_path)
    if not input_path.is_file():
        raise FileNotFoundError(f"Door input recording not found: {input_path}")

    artifact_dir = _resolve_artifact_dir(artifact_dir)
    bundle = _load_model(artifact_dir)
    clf = bundle["classifier"]

    stream = load_stream(input_path)
    if stream.empty:
        raise ValueError(f"Door input recording is empty: {input_path}")

    segments = segment_stream(stream)
    if not segments:
        return []

    records: list[dict[str, object]] = []
    feature_rows = [extract_features(seg) for seg in segments]
    X = np.vstack(feature_rows)
    predictions = clf.predict(X)

    for seg, pred in zip(segments, predictions):
        start_ts = seg["ts"].iloc[0]
        end_ts = seg["ts"].iloc[-1]
        records.append(
            {
                "start_time": format_timestamp(start_ts),
                "end_time": format_timestamp(end_ts),
                "prediction": str(pred),
            }
        )
    return records
