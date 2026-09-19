from __future__ import annotations

import io
from pathlib import Path
import time
import zipfile
from dataclasses import replace

import pytest

from fastapi.testclient import TestClient

from backend.config import Settings
from backend.database import Store
from backend.main import create_app


def _settings(tmp_path: Path) -> Settings:
    data = tmp_path / "runtime"
    return Settings(
        data_dir=data,
        database_path=data / "test.sqlite3",
        upload_dir=data / "uploads",
        max_upload_bytes=1024 * 1024,
        chart_point_limit=20,
        cors_origins=("http://localhost:5173",),
    )


def _wait_for_terminal(client: TestClient, run_id: str) -> dict[str, object]:
    for _ in range(100):
        run = client.get(f"/api/runs/{run_id}").json()
        if run["status"] in {"completed", "failed"}:
            return run
        time.sleep(0.01)
    raise AssertionError("run did not finish")


def test_upload_run_review_and_official_export(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        "backend.worker.run_inference",
        lambda subsystem, paths: [
            {
                "start_time": "2026-1-1-0-0-0-0",
                "end_time": "2026-1-1-0-0-1-0",
                "prediction": "Normal",
            }
        ],
    )
    monkeypatch.setattr("backend.worker.build_chart_series", lambda *args: [])
    with TestClient(create_app(_settings(tmp_path))) as client:
        response = client.post(
            "/api/runs",
            data={"subsystem": "door"},
            files={"files": ("recording.csv", b"header\nvalue\n", "text/csv")},
        )
        assert response.status_code == 202
        run = _wait_for_terminal(client, response.json()["run_id"])
        assert run["status"] == "completed"
        assert run["files"] == ["recording.csv"]
        summary = client.get("/api/runs").json()[0]
        assert summary["created_at"] == run["created_at"]
        assert summary["updated_at"] == run["updated_at"]
        assert summary["file_count"] == 1
        assert summary["result_count"] == 1
        assert summary["error"] is None
        result = run["results"][0]
        assert result["review_status"] == "unreviewed"

        reviewed = client.patch(
            f"/api/results/{result['result_id']}/review",
            json={"status": "confirmed", "note": "Verified"},
        )
        assert reviewed.status_code == 200
        assert reviewed.json()["review_note"] == "Verified"
        assert reviewed.json()["prediction"] == result["prediction"]
        history = client.get(f"/api/results/{result['result_id']}/reviews").json()
        assert [(item["status"], item["note"]) for item in history] == [
            ("confirmed", "Verified")
        ]
        assert history[0]["id"] and history[0]["created_at"]
        rejected = client.patch(f"/api/results/{result['result_id']}/review",
                                json={"status": "dismissed", "note": "x" * 2001})
        assert rejected.status_code == 422
        assert client.get(f"/api/runs/{run['run_id']}").json()["results"][0]["review_status"] == "confirmed"

        exported = client.get(f"/api/runs/{run['run_id']}/export")
        assert exported.status_code == 200
        assert exported.text.splitlines() == [
            "start_time,end_time,prediction",
            "2026-1-1-0-0-0-0,2026-1-1-0-0-1-0,Normal",
        ]
        assert "review" not in exported.text


def test_worker_persists_inference_failure(tmp_path: Path, monkeypatch) -> None:
    def fail(*_):
        raise FileNotFoundError("model artifact is unavailable")

    monkeypatch.setattr("backend.worker.run_inference", fail)
    with TestClient(create_app(_settings(tmp_path))) as client:
        response = client.post(
            "/api/runs",
            data={"subsystem": "shm"},
            files={"files": ("signal.csv", b"1\n2\n3\n", "text/csv")},
        )
        run = _wait_for_terminal(client, response.json()["run_id"])
        assert run["status"] == "failed"
        assert run["error"] == {
            "code": "inference_failed",
            "message": "model artifact is unavailable",
        }
        assert client.get(f"/api/runs/{run['run_id']}/export").status_code == 409


def test_upload_validation_rejects_wrong_extension_and_duplicate_names(tmp_path: Path) -> None:
    with TestClient(create_app(_settings(tmp_path))) as client:
        wrong = client.post(
            "/api/runs",
            data={"subsystem": "acv"},
            files={"files": ("case.csv", b"x", "text/csv")},
        )
        assert wrong.status_code == 400
        assert wrong.json()["detail"]["code"] == "invalid_extension"

        duplicate = client.post(
            "/api/runs",
            data={"subsystem": "rail"},
            files=[
                ("files", ("same.csv", b"x", "text/csv")),
                ("files", ("SAME.csv", b"y", "text/csv")),
            ],
        )
        assert duplicate.status_code == 400
        assert duplicate.json()["detail"]["code"] == "duplicate_filename"


def test_restart_marks_interrupted_runs_failed(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    store = Store(settings.database_path)
    store.initialize()
    source = tmp_path / "input.csv"
    source.write_text("1\n", encoding="utf-8")
    run_id = store.create_run("shm", [(source.name, source)])
    store.set_running(run_id)
    store.initialize()
    run = store.get_run(run_id)
    assert run["status"] == "failed"
    assert run["error"]["code"] == "server_restarted"


def test_zip_has_one_official_file_per_subsystem_at_root(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    with TestClient(create_app(settings)) as client:
        store: Store = client.app.state.store
        records = {
            "door": [{"start_time": "a", "end_time": "b", "prediction": "Normal"}],
            "acv": [{"file_id": "a.xlsx", "ranked_cars": ["01", "02"]}],
            "rail": [{"file_id": "r.csv", "prediction": "Side I"}],
            "shm": [{"file_id": "s.csv", "prediction": 0.25}],
        }
        run_ids = []
        for subsystem, payload in records.items():
            source = tmp_path / f"{subsystem}.input"
            source.write_text("x", encoding="utf-8")
            run_id = store.create_run(subsystem, [(source.name, source)])
            store.set_running(run_id)
            store.complete_run(run_id, payload, [])
            run_ids.append(run_id)

        response = client.post("/api/exports", json={"run_ids": run_ids})
        assert response.status_code == 200
        with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
            assert sorted(archive.namelist()) == [
                "acv_predictions.csv",
                "door_predictions.csv",
                "rail_predictions.csv",
                "shm_predictions.csv",
            ]
            assert all("/" not in name for name in archive.namelist())

        duplicate = client.post("/api/exports", json={"run_ids": [run_ids[0], run_ids[0]]})
        assert duplicate.status_code == 400


def test_upload_capacity_default_override_and_validation(monkeypatch):
    monkeypatch.delenv("BACKEND_MAX_UPLOAD_BYTES", raising=False)
    assert Settings.from_env().max_upload_bytes == 2 * 1024**3
    # A synthetic 68-recording batch at 18 MiB per recording fits the default.
    assert Settings.from_env().max_upload_bytes > 68 * 18 * 1024**2
    monkeypatch.setenv("BACKEND_MAX_UPLOAD_BYTES", "100")
    assert Settings.from_env().max_upload_bytes == 100
    for invalid in ("0", "-1", "not-a-number"):
        monkeypatch.setenv("BACKEND_MAX_UPLOAD_BYTES", invalid)
        with pytest.raises(ValueError):
            Settings.from_env()
    monkeypatch.setenv("BACKEND_MAX_UPLOAD_BYTES", "100")
    monkeypatch.setenv("BACKEND_CHART_POINT_LIMIT", "1")
    with pytest.raises(ValueError, match="at least 2"):
        Settings.from_env()


def test_upload_limit_counts_all_files_and_cleans_rejected_run(tmp_path, monkeypatch):
    settings = replace(_settings(tmp_path), max_upload_bytes=8)
    monkeypatch.setattr("backend.worker.run_inference", lambda *_: [])
    monkeypatch.setattr("backend.worker.build_chart_series", lambda *_: [])
    with TestClient(create_app(settings)) as client:
        response = client.post("/api/runs", data={"subsystem": "rail"}, files=[
            ("files", ("first.csv", b"12345", "text/csv")),
            ("files", ("second.csv", b"6789", "text/csv")),
        ])
        assert response.status_code == 413
        assert response.json()["detail"]["code"] == "upload_too_large"
        assert client.get("/api/runs").json() == []
        assert list(settings.upload_dir.iterdir()) == []
        accepted = client.post("/api/runs", data={"subsystem": "rail"}, files=[
            ("files", ("first.csv", b"1234", "text/csv")),
            ("files", ("second.csv", b"5678", "text/csv")),
        ])
        assert accepted.status_code == 202
        assert _wait_for_terminal(client, accepted.json()["run_id"])["status"] == "completed"


def test_empty_file_is_rejected_without_a_run(tmp_path):
    settings = _settings(tmp_path)
    with TestClient(create_app(settings)) as client:
        response = client.post("/api/runs", data={"subsystem": "shm"},
                               files={"files": ("empty.csv", b"", "text/csv")})
        assert response.status_code == 400
        assert response.json()["detail"]["code"] == "empty_file"
        assert client.get("/api/runs").json() == []
        assert list(settings.upload_dir.iterdir()) == []


@pytest.mark.parametrize("subsystem,constant,extension", [
    ("door", "DOOR_ARTIFACT_DIR", ".csv"), ("acv", "ACV_ARTIFACT_DIR", ".xlsx"),
    ("rail", "RAIL_ARTIFACT_DIR", ".csv"), ("shm", "SHM_ARTIFACT_DIR", ".csv"),
])
def test_missing_artifact_is_actionable_and_worker_keeps_running(tmp_path, monkeypatch, subsystem, constant, extension):
    monkeypatch.setattr(f"backend.adapters.{constant}", tmp_path / "absent-artifacts")
    monkeypatch.setattr(f"backend.adapters.predict_{subsystem}", lambda *_: pytest.fail("Missing model must not invoke inference"))
    settings = _settings(tmp_path)
    with TestClient(create_app(settings)) as client:
        for _ in range(2):
            response = client.post("/api/runs", data={"subsystem": subsystem},
                                   files={"files": ("synthetic" + extension, b"fixture", "application/octet-stream")})
            assert response.status_code == 202
            run = _wait_for_terminal(client, response.json()["run_id"])
            assert run["status"] == "failed"
            assert run["error"]["code"] == "model_unavailable"
            assert "service administrator" in run["error"]["message"]
            assert run["results"] == []
            assert client.get(f"/api/runs/{run['run_id']}/export").status_code == 409
        assert client.get("/api/health").json()["status"] == "ok"
    # Failure survives application restart, rather than being replaced by fake output.
    with TestClient(create_app(settings)) as client:
        assert client.get(f"/api/runs/{run['run_id']}").json()["error"]["code"] == "model_unavailable"


def test_backend_reuses_shm_serializer():
    from backend.adapters import official_csv, write_shm
    from ml.shm.serialize import write_predictions
    assert write_shm is write_predictions
    assert official_csv("shm", [{"file_id": "synthetic.csv", "prediction": 0.125}]) == b"file_id,prediction\nsynthetic.csv,0.125\n"
    with pytest.raises(ValueError):
        official_csv("shm", [{"file_id": "synthetic.csv", "prediction": float("nan")}])
