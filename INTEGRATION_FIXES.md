# Code and integration fixes

Base: latest fetched `main`, `a8b98c7` (Merge FastAPI backend). Changes are local,
not committed or pushed. Existing subsystem ownership and the API adapter/model
package separation are preserved. No held-out inference, model regeneration,
final predictions, submission archive, video, or packaging was performed.
CSV/ZIP regression checks use synthetic test fixtures in temporary storage or
memory. No datasets, local environment files, caches or model binaries are
included in the source changes.

## Exact fixes

1. **Upload capacity/configuration:** default combined request capacity is 2 GiB;
   explicit environment overrides remain supported. Nonpositive limits and
   unusable chart limits fail at startup. Oversized and empty uploads clean up
   partial files and never create a run. The existing chunked copy is preserved.
2. **Door timestamps:** native and timezone-free ISO input is parsed numerically;
   new cycle bounds and chart points use ISO milliseconds. Frontend chart
   filtering accepts both persisted legacy and ISO values, handles boundary
   crossings and milliseconds, and never assigns a browser timezone.
3. **API alignment:** frontend types match actual run/detail/summary/review
   payloads. History/Overview use server metadata rather than session storage.
   Reviews and ZIP controls default to enabled, with opt-out environment flags.
   Review history is fetched, displayed and refreshed after saving. Notes obey
   the backend's 2000-character limit. Review responses only update metadata,
   even when the full response contains prediction fields. FastAPI 422 errors
   display readable field messages. Mocks use the same metadata/event shapes.
4. **Rail provenance:** source hashes normalize CRLF to LF only. Other bytes,
   including whitespace, remain significant. Actual source changes, feature
   changes and frozen split changes still block the final fit. Binary/data/split
   hashes remain byte-exact. New reports identify the normalization algorithm;
   recorded model scores and model binaries are unchanged.
5. **Missing artifacts:** the backend returns persistent `model_unavailable`
   failed runs with recovery instructions before attempting model inference.
   Other jobs continue; failed runs cannot be exported. Documentation lists each
   owner's required runtime artifact and explicit regeneration command without
   asserting machine-specific artifact availability or training automatically.
6. **SHM handoff:** a validated package-owned CSV serializer is reused by both
   CLI and backend. Full-batch validation occurs before writing, preserves
   numeric precision, and rejects invalid values/IDs/extra fields. Evaluation
   now reports `CV_official_score` and `OOF_official_score` as
   `max(0, 1 - fractional MAPE)`, keeping their distinct MAPE summaries explicit.
   The manifest's added scores are arithmetic conversions of its historical
   MAPE values, not new evaluation results. README describes the implemented
   repeated-fold/Extra Trees approach and limitations; its stale dataset path
   was corrected to configured external training data.
7. **Consistency:** frontend rejects duplicate filenames ignoring case; chart
   units use documented Rail acceleration/current units or explicitly unknown
   units. Browser tests run separately on port 5174 (`PLAYWRIGHT_PORT` override),
   leaving a developer server on 5173 untouched. Vite caches are ignored. Shared
   docs now reflect the merged backend instead of scaffold-only status.

## Files changed

Paths below are relative to the repository root.

| Area | Files |
| --- | --- |
| Shared docs | `README.md`, `contracts/api.md`, `contracts/model.md`, `INTEGRATION_FIXES.md` |
| Backend | `backend/config.py`, `backend/main.py`, `backend/adapters.py`, `backend/worker.py`, `backend/charts.py`, `backend/README.md` |
| Backend tests | `backend/tests/test_backend.py`, new `backend/tests/test_charts.py` |
| Door | `ml/door/loader.py`, `ml/door/inference.py`, `ml/door/README.md`, `ml/door/tests/test_door.py` |
| Rail | `ml/rail/provenance.py`, `ml/rail/evaluate.py`, `ml/rail/train.py`, `ml/rail/README.md`, new `ml/rail/test_provenance.py` |
| SHM | new `ml/shm/serialize.py`, `ml/shm/predict.py`, `ml/shm/modeling.py`, `ml/shm/artifact_manifest.json`, `ml/shm/README.md`, `ml/shm/tests/test_shm.py` |
| Frontend transport | `frontend/src/api/types.ts`, `frontend/src/api/client.ts`, `frontend/src/api/mockClient.ts` |
| Frontend UI | `frontend/src/components/ChartCard.tsx`, `frontend/src/components/Results.tsx`, `frontend/src/components/UploadZone.tsx`, new `frontend/src/components/ReviewHistory.tsx` |
| Frontend pages/lifecycle | `frontend/src/pages/HistoryPage.tsx`, `frontend/src/pages/OverviewPage.tsx`, `frontend/src/pages/SubsystemPage.tsx`, `frontend/src/hooks/useRun.ts`, `frontend/src/utils/domain.ts`, new `frontend/src/utils/timestamps.ts` |
| Frontend configuration/docs/tests | `frontend/.env.example`, `frontend/.gitignore`, `frontend/README.md`, `frontend/PHASE_REPORT.md`, `frontend/playwright.config.ts`, `frontend/tests/flows.spec.ts` |

## Regression tests added or strengthened

- Config defaults/overrides/invalid values; combined-file limit, exact boundary,
  empty files and cleanup of rejected uploads.
- Door source/ISO parsing, invalid dates/timezones, milliseconds, ISO backend
  chart points, chronological frontend comparisons and cross-cycle filtering.
- Persistent API timestamps/counts in a fresh browser session, review event
  payloads, history refresh, note limits, and prediction immutability.
- LF/CRLF equality, byte-exact binary hashing, real code/whitespace changes,
  and stale source/split/feature-version rejection before dataset access.
- Missing artifacts for all four subsystems, continued worker operation,
  persistence across restart, blocked exports and readable UI errors.
- SHM score formula/floor/invalid values, distinction between CV and averaged
  OOF reporting, serializer validation/precision, and CLI/backend reuse.
- Correct Rail side aggregation/units, case-insensitive upload duplicates,
  structured HTTP validation errors and default-enabled endpoint controls.

## Commands and results

From repository root:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
npm --prefix frontend run build
```

From `frontend/`:

```powershell
npm test -- --workers=2
```

- Full Python suite: **85 passed**, 2 third-party deprecation warnings.
- Frontend production build: **passed**.
- Full Playwright suite: **34 passed**, desktop and mobile Chromium.
- `git diff --check`: **passed**.
- The first browser launch found port 5173 occupied. After isolating the test
  server on 5174, the entire suite passed; no existing server was stopped.

## Remaining code issues

No known unresolved defects in the requested fixes. The installed
Starlette/TestClient dependencies emit two deprecation warnings (httpx and
AnyIO compatibility aliases); they do not fail the suite. The existing backend
architecture remains a single-process serial-worker prototype, as documented.
