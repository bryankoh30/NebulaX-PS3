"""Focused Rail schema, feature and handoff contract checks."""
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from .data import CHANNELS, HEADERS, input_files, load_recording, validate_paths


def recording(path):
    values = np.zeros((10000, 129))
    values[:, 0] = np.arange(10000) % 2
    values[:, 1:] = np.arange(1, 129)
    pd.DataFrame(values, columns=HEADERS).to_csv(path, index=False)
    return values


def test_side_mapping():
    assert len(CHANNELS) == 128
    for car in range(1, 9):
        for side, positions in [("Side I", {1, 3, 5, 7}), ("Side II", {2, 4, 6, 8})]:
            channels = [c for c in CHANNELS if c["car"] == car and c["side"] == side]
            assert len(channels) == 8
            assert {c["position"] for c in channels} == positions
            assert {c["kind"] for c in channels} == {"vibration", "shock"}


def test_headers_reordered(tmp_path):
    path = tmp_path / "record.csv"
    values = recording(path)
    frame = pd.read_csv(path)
    frame.loc[:, HEADERS[::-1]].to_csv(path, index=False)
    np.testing.assert_array_equal(load_recording(path), values)


@pytest.mark.parametrize("fault", ["missing", "duplicate", "nan", "pulse", "short"])
def test_malformed(tmp_path, fault):
    path = tmp_path / "bad.csv"
    values = recording(path)
    frame = pd.DataFrame(values, columns=HEADERS)
    if fault == "missing":
        frame = frame.iloc[:, :-1]
    elif fault == "duplicate":
        frame.columns = HEADERS[:-1] + [HEADERS[1]]
    elif fault == "nan":
        frame.iloc[0, 1] = np.nan
    elif fault == "pulse":
        frame.iloc[0, 0] = 2
    else:
        frame = frame.iloc[:-1]
    frame.to_csv(path, index=False)
    with pytest.raises(ValueError):
        load_recording(path)


def test_input_discovery(tmp_path):
    with pytest.raises(ValueError, match="No CSV"):
        input_files(tmp_path)
    for name in ["z.csv", "A.csv", "ignore.txt"]:
        (tmp_path / name).touch()
    assert [p.name for p in input_files(tmp_path)] == ["A.csv", "z.csv"]
    with pytest.raises(ValueError, match="Duplicate"):
        validate_paths([tmp_path / "z.csv", tmp_path / "z.csv"])
    with pytest.raises(FileNotFoundError):
        validate_paths([tmp_path / "absent.csv"])


def test_statistics_and_side_contrast():
    from .features import extract_features

    values = np.zeros((10000, 129))
    values[:, 0] = np.arange(10000) % 2
    wave = np.tile([-1., 1.], 5000)
    for index, channel in enumerate(CHANNELS):
        values[:, index + 1] = wave * (2 if channel["side"] == "Side I" else 1)
    vector, names = extract_features(values)
    features = dict(zip(names, vector))
    assert features["car1_pos1_vibration_rms"] == 2
    assert features["car1_pos1_vibration_std"] == 2
    assert features["car1_pos1_vibration_peak_to_peak"] == 4
    assert features["car1_pos1_vibration_kurtosis"] == 1
    assert features["contrast_vibration_rms_mean"] == 1
    assert features["pulse_transitions_per_second"] == 10000
    constant, _ = extract_features(np.zeros((10000, 129)))
    assert np.isfinite(constant).all()


def test_export_exact_and_reject_invalid(tmp_path):
    from .serialize import write_predictions

    output = tmp_path / "predictions.csv"
    rows = [{"file_id": "Original.CSV", "prediction": "Side I"}]
    write_predictions(rows, output)
    assert output.read_bytes() == b"file_id,prediction\nOriginal.CSV,Side I\n"
    for invalid in [[], rows * 2, [{"file_id": "x.csv", "prediction": "side I"}],
                    [{"file_id": "x.csv", "prediction": "Normal", "confidence": 1}]]:
        with pytest.raises(ValueError):
            write_predictions(invalid, output)
        assert output.read_bytes() == b"file_id,prediction\nOriginal.CSV,Side I\n"


def test_missing_and_incompatible_artifacts(tmp_path):
    import joblib
    from .inference import predict_rail

    path = tmp_path / "record.csv"
    recording(path)
    with pytest.raises(FileNotFoundError, match="Missing Rail artifact"):
        predict_rail([path], tmp_path)
    joblib.dump({}, tmp_path / "model.joblib")
    with pytest.raises(ValueError, match="Incompatible"):
        predict_rail([path], tmp_path)


def test_frozen_folds():
    import json
    from sklearn.model_selection import StratifiedGroupKFold
    from .features import PACKAGE

    split = PACKAGE / "validation_split.json"
    if not split.exists():
        pytest.skip("Run R1 inspection before verifying the real frozen split")
    records = json.loads(split.read_text())["recordings"]
    assert len(records) == len({r["file_id"] for r in records}) == 272
    labels = [r["label"] for r in records]
    groups = np.array([r["numeric_sha256"] for r in records])
    for fold, (train, validation) in enumerate(StratifiedGroupKFold(5, shuffle=True, random_state=42).split(np.zeros(272), labels, groups)):
        assert set(train).isdisjoint(validation)
        assert set(groups[train]).isdisjoint(groups[validation])
        assert all(records[i]["fold"] == fold for i in validation)
        assert set(labels[i] for i in validation) == {"Normal", "Side I", "Side II"}


def test_cli_invalid_file_does_not_publish_partial_csv(tmp_path):
    import joblib
    import subprocess
    import sys
    from sklearn.dummy import DummyClassifier
    from .data import CLASSES
    from .features import FEATURE_VERSION, extract_features

    inputs = tmp_path / "inputs"
    inputs.mkdir()
    values = recording(inputs / "a-valid.csv")
    (inputs / "z-invalid.csv").write_text("wrong,headers\n1,2\n")
    vector, names = extract_features(values)
    model = DummyClassifier(strategy="constant", constant="Normal").fit([vector], ["Normal"])
    joblib.dump({"model": model, "feature_version": FEATURE_VERSION, "feature_names": names,
                 "classes": CLASSES}, tmp_path / "model.joblib")
    output = tmp_path / "predictions.csv"
    result = subprocess.run([sys.executable, "-m", "ml.rail.predict", "--input", str(inputs),
                             "--output", str(output), "--artifacts", str(tmp_path)], capture_output=True, text=True)
    assert result.returncode != 0
    assert "z-invalid.csv" in result.stderr
    assert not output.exists()
