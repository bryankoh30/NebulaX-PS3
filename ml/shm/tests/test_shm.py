from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import pytest
from sklearn.dummy import DummyRegressor

from ml.shm.data import discover_csv_files, load_signal
from ml.shm.feature_extraction import extract_signal_features, feature_columns_for_groups
from ml.shm.inference import predict_shm


def write_signal(path: Path, values: np.ndarray) -> None:
    pd.DataFrame(values).to_csv(path, header=False, index=False)


def test_load_signal_rejects_non_numeric_values(tmp_path: Path) -> None:
    path = tmp_path / "bad.csv"
    path.write_text("1\nnot-a-number\n3\n", encoding="utf-8")
    with pytest.raises(ValueError, match="non-numeric"):
        load_signal(path)


def test_discovery_is_sorted_and_rejects_empty_directory(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="No CSV"):
        discover_csv_files(tmp_path)
    write_signal(tmp_path / "b.csv", np.arange(4, dtype=float))
    write_signal(tmp_path / "a.csv", np.arange(4, dtype=float))
    assert [path.name for path in discover_csv_files(tmp_path)] == ["a.csv", "b.csv"]


def test_phase_one_feature_count_and_finiteness() -> None:
    signal = np.sin(np.linspace(0, 20, 1000)) + np.linspace(-1, 1, 1000)
    features = extract_signal_features(signal, ("statistics", "distribution"))
    assert len(features) == 37
    assert np.isfinite(list(features.values())).all()
    table = pd.DataFrame([{"file_id": "x.csv", "target": 0.1, **features}])
    assert len(feature_columns_for_groups(table, ("statistics",))) == 15
    assert len(feature_columns_for_groups(table, ("statistics", "distribution"))) == 37


def test_saved_artifact_inference_preserves_name_and_is_nonnegative(tmp_path: Path) -> None:
    signal_path = tmp_path / "sample.csv"
    signal = np.sin(np.linspace(0, 10, 100))
    write_signal(signal_path, signal)
    features = extract_signal_features(signal, ("statistics",))
    feature_names = list(features)
    X = np.asarray([[features[name] for name in feature_names]] * 2)
    model = DummyRegressor(strategy="constant", constant=0.25).fit(X, [0.2, 0.3])
    artifact_dir = tmp_path / "artifacts"
    artifact_dir.mkdir()
    joblib.dump(
        {
            "model": model,
            "feature_groups": ("statistics",),
            "feature_names": feature_names,
        },
        artifact_dir / "model.joblib",
    )

    assert predict_shm([signal_path], artifact_dir) == [
        {"file_id": "sample.csv", "prediction": 0.25}
    ]
