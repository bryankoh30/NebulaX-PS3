# Frontend phase handoff

Historical implementation report below describes the initial frontend-only
checkpoint. The merged backend/API integration now supersedes its absent-backend
and undefined-metadata limitations: history uses persisted API metadata, reviews
and ZIP controls default to enabled, review events are displayed, and Door
filtering handles ISO and legacy timestamps. See `README.md` and
`../contracts/api.md` for the current implementation.

Implemented only `frontend/`. Root README, plan, contracts, model code, organiser references and datasets are unchanged. Shared `SubsystemPage` and `Results` components provide the four subsystem views without duplicating the upload/polling lifecycle.

## F1 — Complete

- Created `package.json`, lockfile, `tsconfig.json`, `vite.config.ts`, `index.html`, `.env.example`, `.gitignore`, `src/main.tsx`, `src/App.tsx`, `src/api/types.ts`, `src/api/client.ts`, `src/components/AppShell.tsx`, `src/components/States.tsx`, and `src/styles.css`.
- Pages: responsive shell, six navigation destinations, hash routes, loading/error/empty states.
- Commands: `npm install`; `npm run build` (from `frontend/`). Final production build passed. Installation audited 113 packages with zero vulnerabilities reported.
- API status: real mode by default; uses planned L1 shapes because `contracts/api.md` does not exist.
- Limitation: contract agreement and real backend are outstanding.
- Next command from repository root: `npm --prefix frontend run dev`.

## F2 — Complete

- Created `src/api/mockClient.ts`, `src/hooks/useRun.ts`, `src/components/UploadZone.tsx`, `src/components/Results.tsx`, `src/components/ChartCard.tsx`, `src/pages/SubsystemPage.tsx`, and `src/utils/domain.ts`; extended styling.
- Pages: Rail batch upload, Normal/Side I/Side II filters, detail dialog, plain-language explanations, affected side, supplied charts, CSV download. Polling and file validation are shared.
- Commands: `npx playwright install chromium`; `npm test -- --workers=2` from `frontend/`.
- Screenshots: desktop/mobile `rail-results.png` under `test-results/flows-Rail-upload-polling--2d442--official-export-and-layout-<project>/`.
- API status: separate development fixtures; real transport tested with intercepted responses. No actual inference was performed.
- Limitations: official CSV content remains the backend's responsibility. Fixture CSVs must never be submitted.
- Next command: `npm --prefix frontend test -- --grep "Rail upload" --workers=2`.

## F3 — Complete

- Extended `SubsystemPage.tsx`, `Results.tsx`, `ChartCard.tsx`, `mockClient.ts`, and `domain.ts` for SHM, ACV, and Door.
- Pages: numeric fatigue damage, complete string-preserving car rankings, multiple door cycles with boundaries and contextual inspection examples. No unsupported confidence, probability, severity or remaining-life values.
- Commands: `npm test -- --workers=2`; `npm run build` from `frontend/`.
- Screenshots: desktop/mobile `door-results.png`, `acv-details.png`, and `shm-details.png` in corresponding test output folders.
- API status: all four views share one API abstraction. Charts render only supplied series.
- Limitations: no ACV score field is defined, so only rankings appear; absent chart data is explicitly stated.
- Next command: `npm --prefix frontend test -- --workers=2`.

## F4 — Complete against planned endpoints

- Created `src/pages/OverviewPage.tsx`, `src/pages/HistoryPage.tsx`, `src/hooks/useHistory.ts`; added review form and session upload metadata helpers.
- Pages: latest completed run per subsystem, recent findings, newest-first history, reopen/reload run URLs. Review actions preserve the model prediction. Optional final ZIP selection enforces one completed run per subsystem.
- Commands: `npm test -- --workers=2` from `frontend/`.
- Screenshots: desktop/mobile `overview.png` and `history.png` under `test-results/flows-Overview-history-refresh-reopening-and-ZIP-request-<project>/`.
- API status: review and ZIP controls are disabled in real mode unless explicitly enabled in environment configuration.
- Limitations: history metadata keys and review-event payloads are not defined. File counts/timestamps use locally recorded upload metadata and show unavailable values otherwise. Review-event history is not implemented.
- Next command: `npm --prefix frontend run dev`.

## F5 — Frontend transport complete; real integration pending

- Real multipart create, run polling, history, review PATCH, CSV and ZIP transport implemented in `src/api/client.ts`; documented in `frontend/README.md`.
- Commands: `npm test -- --workers=2` verifies the real client with HTTP interception, including repeated-file upload, error handling, one-second polling, terminal-state/navigation stops, reviews, and downloads.
- No FastAPI implementation or API contract file exists in this checkout. Actual uploads → model inference → official CSV/ZIP content cannot be accepted yet. No backend files were created or changed.
- Development mocks are off by default and excluded from production builds. A scan of `dist/assets` found no mock storage key or fixture failure implementation.
- Required next action: backend owner confirms run-list/review response shapes and implements the planned endpoints. Start their documented FastAPI command, then run `npm --prefix frontend run dev` with `VITE_USE_MOCK_API=false`.

## F6 — Frontend verification complete; live acceptance pending F5

- Created `playwright.config.ts`, `tests/flows.spec.ts`, `README.md`, and this report. Refined mobile table scrolling, labels, native modal keyboard behavior, chart data tables, and lazy loading of charts.
- Final commands: `npm run build` and `npm test -- --workers=2` from `frontend/`.
- Results: production build passed; **22 browser tests passed**, covering desktop (1280×720) and mobile (390×664) Chromium. Overview, Rail results and ACV detail screenshots were visually inspected; screenshots for all six pages were captured. No page-level horizontal overflow in the Rail layout checks.
- Initial Rail fixture timing checks failed because the fixture advanced on a cancelled development request. Changed fixture progression to elapsed time; the complete suite then passed.
- Build output: initial JavaScript 258.74 kB (79.99 kB gzip), separately loaded chart bundle 361.65 kB (106.55 kB gzip). Build output and screenshots are ignored by Git.
- Limitations: browser tests use synthetic transport fixtures, not real model outputs; WebKit/Firefox were not tested. Google Fonts are optional with system-font fallbacks. Actual CSV/ZIP schemas and review persistence still need backend acceptance.
- Next command from repository root: `npm --prefix frontend run dev -- --host 127.0.0.1`.

## Real acceptance checklist for the backend handoff

1. Confirm the remaining API envelope/metadata questions documented in `README.md`.
2. Run a Door continuous CSV, an ACV workbook, Rail CSV batch and SHM CSV batch from training/validation inputs through the app with mocks disabled.
3. Verify results, filenames, leading-zero car IDs, cycle bounds and any supplied charts against backend responses.
4. Download each subsystem CSV and inspect its exact schema; enable ZIP export and inspect all four root-level files.
5. Enable reviews, save a decision/note, reload and confirm persistence with unchanged predictions.
6. Exercise invalid schemas, missing artifacts and worker failures on the actual backend.

These remaining checks require the backend and its model artifacts; they are not claimed as completed frontend acceptance.
