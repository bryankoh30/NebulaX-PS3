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

## Behaviour

- Uploads are validated by subsystem and basenames are preserved.
- One background worker runs inference jobs serially and never retrains.
- Run, result, chart, failure, and review history state persists in SQLite.
- Active runs interrupted by a server restart are marked failed.
- Model exceptions, including missing artifacts, are persisted visibly.
- Official CSV exports omit review/application metadata.
- ZIP exports contain at most one completed run per subsystem directly at the
  archive root.

The current local checkout has Door, ACV, and regenerated SHM artifacts. Rail
runs still need the model owner's final `model.joblib` under
`ml/rail/artifacts/`; its final-fit command currently rejects the committed
evaluation provenance as stale, so the backend does not bypass that safeguard.

## Tests

```text
python -m pytest backend/tests -q
python -m pytest -q
```

The API contract consumed by the frontend is in [`contracts/api.md`](../contracts/api.md).
