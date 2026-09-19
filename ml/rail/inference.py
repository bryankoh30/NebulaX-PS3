"""Rail Corrugation inference: explicit files and trusted local artifacts only."""

from pathlib import Path
from typing import Sequence

import joblib
import numpy as np

from .data import CLASSES, load_recording, validate_paths
from .features import FEATURE_VERSION, extract_features


DEFAULT_ARTIFACT_DIR = Path(__file__).resolve().parent / "artifacts"


def predict_rail(
    input_paths: Sequence[str | Path],
    artifact_dir: str | Path | None = None,
) -> list[dict[str, object]]:
    """Return contract records using saved artifacts; never train during inference."""
    paths = validate_paths(input_paths)
    artifact_path = (Path(artifact_dir) if artifact_dir is not None else DEFAULT_ARTIFACT_DIR) / "model.joblib"
    if not artifact_path.is_file():
        raise FileNotFoundError(f"Missing Rail artifact: {artifact_path}; run python -m ml.rail.train")
    bundle = joblib.load(artifact_path)
    if not isinstance(bundle, dict) or bundle.get("feature_version") != FEATURE_VERSION or bundle.get("classes") != CLASSES:
        raise ValueError("Incompatible Rail artifact schema")
    if "model" not in bundle or "feature_names" not in bundle:
        raise ValueError("Incomplete Rail artifact")
    records = []
    for path in paths:
        vector, names = extract_features(load_recording(path))
        if names != bundle["feature_names"]:
            raise ValueError("Artifact feature order differs from this implementation")
        prediction = str(bundle["model"].predict(np.array([vector]))[0])
        if prediction not in CLASSES:
            raise ValueError(f"Model returned invalid Rail label: {prediction}")
        records.append({"file_id": path.name, "prediction": prediction})
    return records
