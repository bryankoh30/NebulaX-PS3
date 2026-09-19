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
files. Nonempty basenames must be unique ignoring case within a run; empty
files are rejected. The default combined upload limit is 2 GiB, configurable
with `BACKEND_MAX_UPLOAD_BYTES`. A successful request returns HTTP
202 with:

```json
{"run_id":"uuid","status":"queued"}
```

### `GET /api/runs/{run_id}`

Returns `run_id`, `subsystem`, `status`, `created_at`, `updated_at`, `files`,
`results`, `chart_series`, and nullable `error`. Status is `queued`, `running`,
`completed`, or `failed`.

Each completed result contains `result_id`, `review_status`, `review_note`, plus
the corresponding model record. Door records have `start_time`, `end_time`, and
`prediction`; ACV has `file_id` and `ranked_cars`; Rail and SHM have `file_id`
and `prediction`.

`files` is an ordered list of original basenames. Run timestamps are ISO UTC
strings with an offset. Door result timestamps are timezone-free ISO strings
with milliseconds, for example `2023-07-05T00:00:09.020`; no timezone is inferred
for recording data. Older persisted runs may still contain the native
`YYYY-M-D-H-M-S-ms` strings, which the frontend also supports numerically.

Chart series contain `file_id`, `series_id`, `label`, `unit`, `x_kind`, and
`points` shaped as `{x, y}`. ACV series may include `car_id`; Rail series may
include `side`. Charts are presentation data and are downsampled independently
of inference. Unknown units are the empty string. Rail vibration uses `m/s²`
and Door motor current uses `mA` per the references.

### `GET /api/runs`

Returns a bare array, newest first. Every summary contains `run_id`,
`subsystem`, `status`, `created_at`, `updated_at`, integer `file_count`, integer
`result_count`, and nullable `error` (`{code,message}`). Filenames are available
on the detail endpoint. Frontend history uses these persisted values rather
than browser-session upload metadata.

## Reviews

### `PATCH /api/results/{result_id}/review`

Body:

```json
{"status":"confirmed","note":"Inspected by maintenance engineer"}
```

Status is `unreviewed`, `confirmed`, `dismissed`, or `resolved`. The endpoint
updates current review metadata and appends an immutable timestamped event.
Notes are limited to 2000 characters and trimmed. The response is the full
result object with its original prediction fields and updated `review_status`
and `review_note`. Clients must update only review metadata from this response.

### `GET /api/results/{result_id}/reviews`

Returns a bare array of `{id,status,note,created_at}` events, oldest first.
Event timestamps are ISO UTC strings. Reviews and ZIP controls are enabled
by default in the frontend; environment flags may disable them for an older
backend deployment.

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

Missing subsystem artifacts produce a persisted `model_unavailable` run error;
other inference failures use `inference_failed`. HTTP validation failures
(422) use FastAPI's `detail` array with `loc`, `msg`, and `type`; the frontend
renders readable field messages. Uploads exceeding the configured combined
limit return 413 `upload_too_large` without creating a run.
