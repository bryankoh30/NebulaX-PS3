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
from ml.shm.serialize import write_predictions
from ml.shm.modeling import official_score, evaluate_candidate


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


@pytest.mark.parametrize("mape,expected", [(0, 1), (0.10, 0.90), (1, 0), (1.5, 0)])
def test_official_score_is_one_minus_fractional_mape_floored_at_zero(mape, expected):
    assert official_score(mape) == pytest.approx(expected)


@pytest.mark.parametrize("mape", [-0.1, float("nan"), float("inf")])
def test_official_score_rejects_invalid_mape(mape):
    with pytest.raises(ValueError):
        official_score(mape)


def test_evaluation_reports_cv_and_averaged_oof_scores(monkeypatch):
    import ml.shm.modeling as modeling
    monkeypatch.setattr(modeling, "N_SPLITS", 2)
    monkeypatch.setattr(modeling, "N_REPEATS", 2)
    table = pd.DataFrame({"file_id": [f"synthetic{i}.csv" for i in range(6)],
                          "target": [1., 2., 3., 4., 5., 6.], "stats__mean": [1., 2., 3., 4., 5., 6.]})
    result, _ = evaluate_candidate(table, ("statistics",), "dummy_median", "regression")
    assert result.CV_official_score == pytest.approx(max(0, 1 - result.CV_MAPE_mean))
    assert result.OOF_official_score == pytest.approx(max(0, 1 - result.OOF_MAPE))


def test_shared_shm_serializer_preserves_precision_and_exact_columns(tmp_path):
    destination = tmp_path / "synthetic.csv"
    write_predictions([{"file_id": "stress,01.csv", "prediction": 0.004820001}], destination)
    import csv
    with destination.open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert rows == [{"file_id": "stress,01.csv", "prediction": "0.004820001"}]


@pytest.mark.parametrize("rows", [
    [], [{"file_id": "a.csv", "prediction": -1}], [{"file_id": "a.csv", "prediction": float("nan")}],
    [{"file_id": "a.csv", "prediction": float("inf")}], [{"file_id": "a.csv", "prediction": True}],
    [{"file_id": "a.csv", "prediction": "0.1"}], [{"file_id": "../a.csv", "prediction": 1}],
    [{"file_id": "a.csv", "prediction": 1, "review_status": "confirmed"}],
    [{"file_id": "a.csv", "prediction": 1}, {"file_id": "a.csv", "prediction": 2}],
])
def test_shm_serializer_rejects_invalid_batch_before_writing(tmp_path, rows):
    destination = tmp_path / "synthetic.csv"
    destination.write_text("existing")
    with pytest.raises(ValueError):
        write_predictions(rows, destination)
    assert destination.read_text() == "existing"


def test_cli_uses_shared_serializer(tmp_path, monkeypatch):
    import ml.shm.predict as cli
    assert cli.write_predictions is write_predictions
    monkeypatch.setattr(cli, "discover_csv_files", lambda _: [tmp_path / "synthetic.csv"])
    monkeypatch.setattr(cli, "predict_shm", lambda *_: [{"file_id": "synthetic.csv", "prediction": 0.125}])
    output = tmp_path / "synthetic-output.csv"
    monkeypatch.setattr("sys.argv", ["predict", "--input", "unused.csv", "--output", str(output)])
    cli.main()
    assert output.read_text() == "file_id,prediction\nsynthetic.csv,0.125\n"
