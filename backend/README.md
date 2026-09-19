# Backend

FastAPI backend for the four frozen model packages. It implements the deferred
L1-L2 app stage without changing model outputs or training during requests.

## Run

From the repository root:

```text
python -m pip install -r requirements.txt
python -m backend
```

The API is available at `http://127.0.0.1:8000`; OpenAPI documentation is at
`http://127.0.0.1:8000/docs`. The frontend development origins
`http://localhost:5173` and `http://127.0.0.1:5173` are allowed by default.

Runtime state is written under the ignored `backend/runtime/` directory. Set
`BACKEND_DATA_DIR` to place the SQLite database and uploaded files elsewhere.
Other optional settings are `BACKEND_MAX_UPLOAD_BYTES`,
`BACKEND_CHART_POINT_LIMIT`, and comma-separated `BACKEND_CORS_ORIGINS`.

`BACKEND_MAX_UPLOAD_BYTES` defaults to **2147483648 bytes (2 GiB)** for the
combined files in one run, providing headroom for a large Rail batch. Set a
positive integer to override it; any reverse proxy must allow the same body
size. The application copies spooled uploads in 1 MiB chunks and cleans up a
rejected batch. Multipart parsing can also use temporary disk space before the
endpoint is called, so allow space for both temporary and stored uploads.
`BACKEND_CHART_POINT_LIMIT` defaults to 500 and must be at least 2. Start this
prototype with one server process so its serial worker owns its run queue.

## Behaviour

- Uploads are validated by subsystem and basenames are preserved.
- One background worker runs inference jobs serially and never retrains.
- Run, result, chart, failure, and review history state persists in SQLite.
- Active runs interrupted by a server restart are marked failed.
- Model exceptions, including missing artifacts, are persisted visibly.
- Official CSV exports omit review/application metadata.
- ZIP exports contain at most one completed run per subsystem directly at the
  archive root.

## Model artifacts

Artifacts are machine-local and intentionally untracked. A fresh clone does
not include them. Install trusted artifacts supplied by the respective model
owner at these paths; keep their accompanying manifests/metadata with them:

| Subsystem | Required runtime file | Owner's regeneration command |
| --- | --- | --- |
| Door | `ml/door/artifacts/door_classifier.joblib` | `python -m ml.door.train --full` |
| ACV | `ml/acv/artifacts/ranker_config.json` | `python -m ml.acv.train` |
| Rail | `ml/rail/artifacts/model.joblib` | `python -m ml.rail.train` |
| SHM | `ml/shm/artifacts/model.joblib` | `python -m ml.shm.train` |

Regeneration is an explicit administrator operation using configured training
data, never an automatic action during an upload. Rail's evaluation must match
the feature version, split and model source before a final fit. Its source
hashes normalize CRLF to LF; code and binary integrity checks remain enabled.
See each subsystem README for its artifact contract and evaluation commands.

The server starts even if artifacts are absent. A requested subsystem with a
missing file fails visibly with `error.code = "model_unavailable"`, an
administrator-facing recovery instruction, no fabricated results, and no
available export. The failure persists in history and the worker continues
processing other jobs. Invalid/corrupt artifacts and other inference errors
remain `inference_failed`. Restarting or installing an artifact does not
silently retry prior failed runs.

## Tests

```text
python -m pytest backend/tests -q
python -m pytest -q
```

The API contract consumed by the frontend is in [`contracts/api.md`](../contracts/api.md).
