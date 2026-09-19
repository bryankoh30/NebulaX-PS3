# Train Condition Monitoring frontend

React, TypeScript, Vite, Recharts and Lucide React. All implementation is contained in this directory. No model inference runs in the browser.

From the repository root:

```powershell
npm --prefix frontend ci
npm --prefix frontend run dev -- --host 127.0.0.1
```

Open `http://127.0.0.1:5173`. Real API mode is the default. The Vite development server proxies `/api` to `http://127.0.0.1:8000`. For deployment, serve `/api` on the same origin or set `VITE_API_BASE_URL` at build time. The backend must allow the frontend origin if these are separate origins. No backend is included in this workspace at the time of implementation.

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

## API boundary and open contract items

There is no `contracts/api.md`. The adapter implements the planned L1 endpoints from `plan.md` without adding model output fields. `src/api/types.ts` contains the frontend types and `src/api/client.ts` owns the transport; components do not depend on adapter selection.

| Endpoint | Current assumption from the plan |
| --- | --- |
| `POST /api/runs` | Multipart `subsystem` plus repeated `files`; response `{run_id,status}` |
| `GET /api/runs/{id}` | `{run_id,subsystem,status,results,chart_series,error}`; error is null or `{code,message}` |
| `GET /api/runs` | Bare array of newest-first summaries with `run_id,subsystem,status` |
| `GET /api/runs/{id}/export` | Backend-owned CSV response; browser saves it as `<subsystem>_predictions.csv` |
| `PATCH /api/results/{result_id}/review` | JSON `{status,note}`; response includes `review_status,review_note` |
| `POST /api/exports` | JSON `{run_ids:[...]}`; ZIP file response |

Review and ZIP endpoints are planned, not present. Set `VITE_ENABLE_REVIEWS=true` and `VITE_ENABLE_ZIP_EXPORT=true` only when the backend supports them. ZIP selection requires exactly one completed run for each of the four subsystems. Official exports always come from the backend in real mode; React never builds submission CSV/ZIP content.

Backend owner must confirm the run-list envelope, review-response metadata, and upload-time/file-count field names. No undocumented metadata is expected: history uses upload timestamps and filenames saved locally in the current browser tab, explicitly showing unavailable values for other runs. Overview retrieves the latest completed run per subsystem based on the API's newest-first ordering. The ACV plan allows workbook batches. No anomaly score field is defined, so no numeric score is displayed. Review event history is not displayed because its event payload is undefined.

Charts accept only the planned `chart_series` fields. File-level evidence is matched by source filename. Door timestamp series are restricted to the selected cycle; sample-index series are explicitly labelled as full recordings because no cycle-to-sample mapping is defined. Units and car IDs come from the API. An accessible data table accompanies each chart.

Polling waits one second between requests, stops at completed/failed, aborts requests and clears timers on navigation/unmount. A transport failure stops polling and offers retry. Run URLs retain the run ID across reloads. Backend jobs are not cancelled when leaving a page.

## Verification

```powershell
npm --prefix frontend run build
cd frontend
npx playwright install chromium
npm test
```

Browser tests cover desktop and mobile Chromium using HTTP interception against the **real client**: multipart uploads; all four result types; queued/running/completed/failed states; polling intervals and cancellation; extension/single/batch validation; review immutability; CSV and ZIP transport; latest-run overview; history and refresh; API errors; evidence charts. Screenshots are written under ignored `test-results/`.

Still required when FastAPI is available: run real training/validation recordings through all four endpoints; inspect returned chart semantics; validate downloaded CSVs against subsystem exporters and inspect ZIP contents; confirm review persistence and worker failures. Do not treat synthetic browser fixtures as real inference acceptance.

See [PHASE_REPORT.md](PHASE_REPORT.md) for phase status and handoff.
