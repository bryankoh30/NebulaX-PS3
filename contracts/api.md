# Application API Contract

The backend serves JSON under `/api` and calls the four frozen model inference
functions directly. Predictions are immutable. Review state and review events
are application metadata and never alter model output or official exports.

## Runs

### `POST /api/runs`

Multipart fields:

- `subsystem`: `door`, `acv`, `rail`, or `shm`
- `files`: one or more repeated uploads

Door accepts exactly one CSV. ACV accepts XLSX files. Rail and SHM accept CSV
files. Basenames must be unique within a run. A successful request returns HTTP
202 with:

```json
{"run_id":"uuid","status":"queued"}
```

### `GET /api/runs/{run_id}`

Returns `run_id`, `subsystem`, `status`, timestamps, input filenames,
`results`, `chart_series`, and nullable `error`. Status is `queued`, `running`,
`completed`, or `failed`.

Each completed result contains `result_id`, `review_status`, `review_note`, plus
the corresponding model record. Door records have `start_time`, `end_time`, and
`prediction`; ACV has `file_id` and `ranked_cars`; Rail and SHM have `file_id`
and `prediction`.

Chart series contain `file_id`, `series_id`, `label`, `unit`, `x_kind`, and
`points` shaped as `{x, y}`. ACV series may include `car_id`; Rail series may
include `side`. Charts are presentation data and are downsampled independently
of inference.

### `GET /api/runs`

Returns newest-first run summaries with result and file counts.

## Reviews

### `PATCH /api/results/{result_id}/review`

Body:

```json
{"status":"confirmed","note":"Inspected by maintenance engineer"}
```

Status is `unreviewed`, `confirmed`, `dismissed`, or `resolved`. The endpoint
updates current review metadata and appends an immutable timestamped event.

### `GET /api/results/{result_id}/reviews`

Returns review events oldest first.

## Exports

### `GET /api/runs/{run_id}/export`

Returns the completed run's official subsystem CSV with no application or
review fields.

### `POST /api/exports`

Body: `{"run_ids":["uuid", "..."]}`. Runs must be completed and may contain
at most one run for each subsystem. Returns a ZIP whose root contains the
official subsystem filenames. Selecting all four produces the final
`predictions.zip` layout.

## Errors

HTTP errors use `{"detail":{"code":"...","message":"..."}}`. Background
inference errors are persisted on the run as `error` with the same shape. A
restart marks previously queued or running work as failed rather than leaving
it indefinitely active.
