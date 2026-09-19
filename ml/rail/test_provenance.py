"""Newline portability must not permit changed model code or split bytes."""
import json
from pathlib import Path

import pytest

from ml.rail.data import digest
from ml.rail.provenance import model_source_hashes, source_digest


def test_source_newlines_are_portable_but_binary_hashes_stay_exact(tmp_path):
    lf, crlf = tmp_path / "lf.py", tmp_path / "crlf.py"
    lf.write_bytes(b"x = 1\ny = 2\n")
    crlf.write_bytes(b"x = 1\r\ny = 2\r\n")
    assert source_digest(lf) == source_digest(crlf)
    assert digest(lf) != digest(crlf)
    crlf.write_bytes(b"x = 2\r\ny = 2\r\n")
    assert source_digest(lf) != source_digest(crlf)
    crlf.write_bytes(b"x = 1 \r\ny = 2\r\n")
    assert source_digest(lf) != source_digest(crlf)  # No whitespace/code stripping.


def test_committed_model_source_hashes_match_without_regenerating_evaluation():
    package = Path(__file__).resolve().parent
    report = json.loads((package / "evaluation.json").read_text())
    assert report["model_source_sha256"] == model_source_hashes()


@pytest.mark.parametrize("change", ["code", "split", "feature_version"])
def test_final_fit_still_rejects_stale_provenance_before_reading_data(tmp_path, monkeypatch, change):
    import ml.rail.train as training
    split = tmp_path / "validation_split.json"
    split.write_bytes(b'{"recordings": []}\n')
    report = {"feature_version": training.FEATURE_VERSION, "split_sha256": digest(split),
              "model_source_sha256": model_source_hashes(), "selected_model": "random_forest"}
    if change == "code":
        report["model_source_sha256"]["models.py"] = "0" * 64
    elif change == "split":
        split.write_bytes(b'{"recordings": ["changed"]}\n')
    else:
        report["feature_version"] = "stale"
    (tmp_path / "evaluation.json").write_text(json.dumps(report))
    monkeypatch.setattr(training, "PACKAGE", tmp_path)
    monkeypatch.setattr(training, "training_features", lambda *_: pytest.fail("Must not read datasets on stale provenance"))
    with pytest.raises(ValueError, match="stale|changed"):
        training.train()
