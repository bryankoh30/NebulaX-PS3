# Train Condition Monitoring frontend

React, TypeScript, Vite, Recharts and Lucide React. All implementation is contained in this directory. No model inference runs in the browser.

From the repository root:

```powershell
npm --prefix frontend ci
npm --prefix frontend run dev -- --host 127.0.0.1
```

Open `http://127.0.0.1:5173`. Real API mode is the default. Start the merged FastAPI service with `python -m backend` from the repository root. The Vite development server proxies `/api` to `http://127.0.0.1:8000`. For deployment, serve `/api` on the same origin or set `VITE_API_BASE_URL` at build time. The backend must allow the frontend origin if these are separate origins.

## Development fixtures

Only enable fixtures for UI development:

```powershell
$env:VITE_USE_MOCK_API='true'
npm --prefix frontend run dev
```

Fixtures are visibly labelled, live only in `src/api/mockClient.ts`, and persist in browser session storage. They do not read or analyse uploaded data. Files prefixed `fail-` exercise a failed run; other nonempty files exercise queued → running → completed. Fixture charts are deliberately absent. Browser tests separately inject chart responses. Fixture CSVs are for testing download behavior only, never submission. ZIP fixture export is disabled.

For real testing and demos, stop the server, disable fixtures, and restart:

```powershell
$env:VITE_USE_MOCK_API='false'
npm --prefix frontend run dev
```

Production builds force the real adapter regardless of the mock environment flag. Browser transport tests also force real mode and intercept HTTP requests; these tests do not establish actual backend/model acceptance.

## API boundary

The adapter follows [`contracts/api.md`](../contracts/api.md). `src/api/types.ts` contains the frontend types and `src/api/client.ts` owns the transport; components do not depend on adapter selection.

| Endpoint | Implemented contract |
| --- | --- |
| `POST /api/runs` | Multipart `subsystem` plus repeated `files`; response `{run_id,status}` |
| `GET /api/runs/{id}` | `{run_id,subsystem,status,created_at,updated_at,files,results,chart_series,error}` |
| `GET /api/runs` | Bare array of newest-first summaries with IDs, subsystem, status, timestamps, `file_count`, `result_count`, nullable `error` |
| `GET /api/runs/{id}/export` | Backend-owned CSV response; browser saves it as `<subsystem>_predictions.csv` |
| `PATCH /api/results/{result_id}/review` | JSON `{status,note}`; response includes `review_status,review_note` |
| `GET /api/results/{result_id}/reviews` | Bare array of `{id,status,note,created_at}`, oldest first |
| `POST /api/exports` | JSON `{run_ids:[...]}`; ZIP file response |

Review and ZIP endpoints are implemented and enabled by default. Set `VITE_ENABLE_REVIEWS=false` or `VITE_ENABLE_ZIP_EXPORT=false` only for an older backend without those endpoints. ZIP selection requires exactly one completed run for each of the four subsystems. Exports always come from the backend in real mode; React never builds submission CSV/ZIP content.

History uses backend timestamps and counts, including in a new browser session. Overview retrieves the latest completed run per subsystem based on the API's newest-first ordering. Review details include persistent event history and a 2000-character note limit. Only review metadata is applied from a review response; model prediction fields remain unchanged. No ACV anomaly score field is defined, so only car rankings are displayed.

Charts accept only the planned `chart_series` fields. File-level evidence is matched by source filename. Door timestamp series are restricted to the selected cycle; sample-index series are explicitly labelled as full recordings because no cycle-to-sample mapping is defined. Units and car IDs come from the API. An accessible data table accompanies each chart.

Door filtering accepts both ISO and legacy non-zero-padded recording timestamps, normalizes their numeric parts, and compares them without assigning a browser timezone. Invalid values are excluded. An absent unit displays "Unit not supplied".

Polling waits one second between requests, stops at completed/failed, aborts requests and clears timers on navigation/unmount. A transport failure stops polling and offers retry. Run URLs retain the run ID across reloads. Backend jobs are not cancelled when leaving a page.

## Verification

```powershell
npm --prefix frontend run build
cd frontend
npx playwright install chromium
npm test
```

Browser tests cover desktop and mobile Chromium using HTTP interception against the **real client**: multipart uploads; all four result types; queued/running/completed/failed states; polling intervals and cancellation; extension/single/batch validation; review immutability; CSV and ZIP transport; latest-run overview; history and refresh; API errors; evidence charts. Screenshots are written under ignored `test-results/`.

Tests start their own Vite server on port 5174 (override with `PLAYWRIGHT_PORT`), leaving a development app on port 5173 untouched. Regressions include legacy Door timestamps, persisted run metadata, review history, case-insensitive duplicates, structured validation errors and missing-model failures.

Missing model artifacts produce a visible failed run with an administrator recovery instruction. See the backend README for machine-local artifact installation. Development fixtures never act as a fallback for a backend failure.

See [PHASE_REPORT.md](PHASE_REPORT.md) for phase status and handoff.
