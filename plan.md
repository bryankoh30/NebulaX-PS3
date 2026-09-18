# PS3 Subsystem-First Plan for Three AI Agents

## Goal and Scope

Build a **React + TypeScript + FastAPI** prototype within **24-48 hours**, covering **all four PS3 subsystems**: Door, ACV, Rail Corrugation, and SHM.

| Subsystem | Required task | Official metric | Model owner |
| --- | --- | --- | --- |
| Door | Find door-cycle boundaries and classify Normal / Abnormal resistance | IoU-weighted F1 | A |
| ACV | Rank every car in each workbook by likelihood of a refrigerant leak | Linear rank-decay score | C |
| Rail Corrugation | Classify each recording as Normal / Side I / Side II | Macro F1 across all three classes | B |
| SHM | Predict one fatigue-damage value per recording | `max(0, 1 - MAPE)` | C |

The product lets engineers upload recordings, inspect predictions and supporting charts, review findings, and download official prediction files for all four subsystems. Recorded Door playback is an optional demonstration of the monitoring concept.

**Current work is subsystem development only.** A works on Door, B works on Rail Corrugation, and C works on the two smaller datasets, SHM and ACV. Each subsystem is a standalone Python package with its own loader, training/evaluation pipeline, inference function, and CSV exporter. No subsystem depends on an API, database, frontend, or another model.

**Backend and frontend come later**, after all four subsystem packages pass the model handoff gate. The app remains a compulsory final hackathon deliverable; postponing it does not remove it from the final prototype.

All four contribute equally to the combined Overall Score. Treat 24 hours as a baseline delivery and use any additional time up to 48 hours for measured improvements and integration. Preserve real inference and export coverage for all four; drop optional playback and visual polish first if time is tight.

Automatic retraining, real onboard connectivity, remaining-life prediction, and verified physical deterioration forecasting are outside this prototype's scope.

## How Each Teammate Uses This Plan

Each teammate gives their AI agent this entire document and identifies its role:

```text
Read plan.md. You are Agent A (Door).
Implement only the Door subsystem phases D1-D4 and the shared handoff requirements.
Do not implement the deferred backend or frontend stages.
Inspect the current repository and shared contracts before making changes.
Complete phases in order and report each phase's exit criteria and handoff.
Do not change shared interfaces without coordinating with their owner.
```

For **Agent B**, substitute Rail Corrugation and phases R1-R4. For **Agent C**, substitute SHM and ACV, phases S1-S4 and V1-V4. C should get a working SHM baseline through S2 first, then an ACV baseline through V2, before finishing validation and handoffs for both. These are two separate packages, not one combined model.

Work in separate local clones and branches. Agents in separate clones cannot see one another's unpushed files or messages: teammates must share handoffs through Git pull requests or their team communication channel. Each agent should report a dependency that needs another owner, then continue any independent work available in its phase.

Merge baseline subsystem packages around hours 8-12 and check that they run in the same Python environment. This is a model integration checkpoint, not an app implementation task. Continue subsystem work independently until the handoff gate passes.

## Shared Context and Rules

- **Current stack:** Python 3.11, pandas, NumPy, SciPy, scikit-learn, and openpyxl for ACV workbooks. Defer FastAPI, SQLite, React, TypeScript, Vite, Recharts, and Lucide setup until the later app stage.
- **Repository:** Use a separate team implementation repository. Copy this plan into that repository's root when it is created. The current repository remains the reference and dataset source.
- **Data location:** Set `DATASET_ROOT` to the existing repository's `PS3/02_Datasets` directory. Read each assigned subsystem's info kit under `PS3/03_References` and the main PS3 specification before implementing its workflow.
- **Git exclusions:** Never commit raw datasets, uploads, local databases, secrets, or build output. Record reproducible artifact-generation instructions and keep large model binaries out of ordinary Git.
- **Ownership:** A owns `ml/door/`; B owns `ml/rail/`; C owns `ml/acv/` and `ml/shm/`. Each owner keeps loaders, features, evaluation, tests, CSV export, reports, and artifact manifests inside their subsystem folder. B maintains root dependencies, package scaffolding, shared documentation, and `contracts/model.md` as a small coordination task, not a backend role.
- **Branches:** Use `feat/door`, `feat/rail`, `feat/acv`, and `feat/shm`. C merges a working SHM baseline before branching from updated `main` for ACV, then returns to the relevant branch for refinements. Do not mix ACV and SHM edits in one PR. B coordinates merges; each owner resolves conflicts in their files.
- **Agent boundaries:** Complete phases in order. Work independently only against agreed contracts. Do not silently change an interface, modify another owner's implementation, or use fake predictions as a fallback for missing models.
- **Phase reports:** At every phase completion, report changed files, checks run, remaining limitations, and the exact command or artifact the next agent can use. A phase is complete only when its exit criteria are satisfied.

## Required Files from PS3

### Reference Files to Commit in the Team Repository

Copy these ten specification/reference/example files and the three Rail reference images from the organiser's repository, preserving their paths. Keep `plan.md` at the team repository root.

```text
PS3/
|-- 01_Problem_Statement_3_Specifications.md
|-- 03_References/
|   |-- ACV/
|   |   `-- ACV_Subsystem_Info_Kit.md
|   |-- Door/
|   |   |-- Door_Subsystem_Info_Kit.md
|   |   `-- Door Data Headers.md
|   |-- Rail_Corrugation/
|   |   |-- Rail_Corrugation_Info_Kit.md
|   |   `-- images/
|   |       |-- image1.jpeg
|   |       |-- image2.png
|   |       `-- image3.jpeg
|   `-- SHM/
|       `-- SHM_Info_Kit.md
`-- 04_Example_Submission/
    |-- acv_predictions.csv
    |-- door_predictions.csv
    |-- rail_predictions.csv
    `-- shm_predictions.csv
```

These files give all three agents the requirements, sensor definitions, scoring rules, and export formats. The example prediction CSVs contain illustrative placeholders, not real predictions; never use them as model outputs or submit them.

Keep the Rail images alongside the info kit so its relative image links continue to work.

### Datasets to Keep Locally Outside the Team Repository

Each teammate can keep a local clone of the organiser's repository containing:

```text
PS3/02_Datasets/
|-- ACV/
|   |-- Train_Labels.csv
|   |-- Train/                  # All 6 acv_case_*.xlsx workbooks
|   `-- Test/
|       `-- acv_test_case.xlsx
|-- Door/
|   |-- Train.csv
|   |-- Train_Segments_Answer.csv
|   `-- Test.csv
|-- Rail_Corrugation/
|   |-- Train_Labels.csv
|   |-- Train/                  # All 272 recordings
|   `-- Test/                   # All 68 recordings
`-- SHM/
    |-- Train_Labels.csv
    |-- Train/                  # All 64 recordings
    `-- Test/                   # All 16 recordings
```

Do not copy these datasets into the team repository or include them in the final submission. Each agent uses their assigned subsystem's training recordings and labels for model development. All agents use training recordings for integration checks. Reserve the held-out test files for final inference, not training, model selection, or tuning. Preserve ACV labels such as `01` as strings.

### Local Environment Setup

Each teammate sets their own local path in an untracked `.env` file:

```dotenv
DATASET_ROOT=C:/path/to/NebulaX-Hackathon-ProblemStatement/PS3/02_Datasets
```

B commits an `.env.example` with a placeholder and ensures `.env` is ignored by Git. Document how training commands load this setting; do not hard-code a teammate's machine-specific path. Code resolves `Door`, `ACV`, `Rail_Corrugation`, and `SHM` dataset paths relative to `DATASET_ROOT`. Use `rail` as the package identifier and map it explicitly to the `Rail_Corrugation` dataset directory.

## Phase 0: Agree Contracts and Start Independently [Hours 0-2]

**B leads; A and C review before their Phase 1 implementation.**

B creates only the Python skeleton, copies the references and images listed above, and adds root Python dependencies, `.gitignore`, `.env.example`, startup instructions, and `contracts/model.md`. Each teammate verifies their local `DATASET_ROOT`. A and C supply their required ML dependencies to B. B creates `ml/__init__.py` and the four subsystem package directories; each owner then works only within their assigned folders. Do not create `backend/`, `frontend/`, HTTP routes, a database, or dashboard fixtures in this stage.

### Model Contract

Each owner exposes their function from their own `ml/<subsystem>/inference.py`. No shared inference dispatcher is required until the later app stage:

```python
predict_door(input_path, artifact_dir=None)
predict_acv(input_paths, artifact_dir=None)
predict_rail(input_paths, artifact_dir=None)
predict_shm(input_paths, artifact_dir=None)
```

- Return lists of JSON-serializable dictionaries using ordinary Python scalars and, for ACV, a list of string car IDs; do not return NumPy scalar objects.
- Door records contain `start_time`, `end_time`, and `prediction`.
- ACV records contain `file_id` and `ranked_cars`; use a list of car-ID strings in Python and JSON, then join with `|` only for CSV export.
- Rail and SHM records contain `file_id` and `prediction`.
- Inference loads saved models, never trains, and raises explicit exceptions on invalid inputs or unavailable artifacts.
- Door timestamps use consistently formatted ISO timestamps without inventing a timezone. Labels are exactly `Normal` or `Abnormal resistance`.
- ACV, Rail, and SHM preserve source filenames including extensions. ACV ranks every car discovered in that workbook's headers exactly once, preserving identifiers such as `03`; do not hard-code cars `01` through `08`.
- Rail labels are exactly `Normal`, `Side I`, or `Side II`. SHM returns finite, nonnegative damage estimates.
- Use `str` or `pathlib.Path` for paths. A missing `artifact_dir` resolves to that subsystem's local `artifacts/` directory, independent of the current working directory; ignore generated artifacts in Git. Each package imports without loading models, reading data, or starting training.
- Owners publish a reproducible artifact-generation command, artifact manifest, and inference example. Keep preprocessing with the saved model or ranker configuration; report missing required artifacts explicitly. A deterministic ACV ranker may use a saved configuration instead of learned model weights.
- Do not add application IDs, review metadata, HTTP responses, or chart payloads to model outputs. Keep loaders reusable so charts can be added later without duplicating parsing.

### Standalone CLI Contract

Each owner provides a `predict.py` module runnable from the team repository root:

```text
python -m ml.door.predict --input <recording.csv> --output <door_predictions.csv> --artifacts <artifact_directory>
python -m ml.rail.predict --input <recording.csv_or_directory> --output <rail_predictions.csv> --artifacts <artifact_directory>
python -m ml.acv.predict --input <case.xlsx_or_directory> --output <acv_predictions.csv> --artifacts <artifact_directory>
python -m ml.shm.predict --input <recording.csv_or_directory> --output <shm_predictions.csv> --artifacts <artifact_directory>
```

`--artifacts` is optional and uses the same default as the Python function. For directory inputs, process supported files in sorted filename order, reject empty inputs and duplicate output IDs, and preserve original basenames. Fail clearly on an invalid recording instead of silently omitting it from a successful CSV. Keep CSV serialization inside the subsystem package so the later backend can reuse it.

These CLIs are the team's development interface, not a replacement for the organiser's required app workflow. Training and evaluation commands must be documented per subsystem. They may use `DATASET_ROOT`; prediction must run on its explicit input without training labels or access to other subsystems.

### Export Contract

| Subsystem | Output filename | Exact CSV columns and values |
| --- | --- | --- |
| Door | `door_predictions.csv` | `start_time,end_time,prediction`; one row per detected cycle |
| ACV | `acv_predictions.csv` | `file_id,ranked_cars`; every car ID joined by `\|`, with leading zeros preserved; no `prediction` column |
| Rail | `rail_predictions.csv` | `file_id,prediction`; one row per file with `Normal`, `Side I`, or `Side II` |
| SHM | `shm_predictions.csv` | `file_id,prediction`; one numeric damage estimate per file |

Exclude review metadata, charts, confidence, and application IDs from the submitted CSVs. A full final export contains all four CSVs directly at the root of `predictions.zip`.

### Exit Criteria

B commits the agreed function/CLI/output contracts. A and C confirm their packages can follow them. Every teammate can locate their assigned training files and install the common Python environment. No API or frontend work is a prerequisite for subsystem implementation.

## Door Subsystem: Agent A

**Own:** `ml/door/` on `feat/door`. No Rail, ACV, SHM, backend, or frontend work is part of this assignment.

**Deliver:** A continuous-stream cycle detector and abnormal-resistance classifier, validated together, with standalone inference and CSV export.

### D1 - Inspect Data and Lock Validation

**Prerequisite:** Phase 0 model contract agreed.

1. Read the Door info kit and parameter definitions, then inspect `Train.csv` and `Train_Segments_Answer.csv`.
2. Verify timestamp parsing, signal columns, the 110 labelled cycles, and the 80 Normal / 30 Abnormal resistance distribution.
3. Inspect timestamp gaps, position changes, and motion flags around training cycle boundaries. Do not assume a single flag defines a complete cycle.
4. Reserve approximately the final 30% of complete cycles as one contiguous validation block, without splitting cycles or reusing overlapping samples across the boundary.
5. Record the split, preprocessing assumptions, and reproducible inspection command in the subsystem README.

**Exit:** A documented loader and fixed split can reproduce the training and validation inputs.

### D2 - Build Segmentation and Classification Baselines

**Prerequisite:** D1 complete.

1. Implement boundary detection using timestamp gaps and motion/position evidence. Develop segmentation rules on the training block only.
2. Extract cycle duration plus current, voltage, back-EMF, and position statistics. Train a class-balanced random forest classifier on labelled training cycles.
3. Implement `predict_door` to segment raw input and classify detected cycles without ground-truth boundaries or labels.
4. Implement the standalone prediction command and exact Door CSV serializer. Save baseline artifacts locally with the feature order.
5. Open a baseline PR containing implementation, checks, and run instructions. Do not commit raw recordings or generated artifacts.

**Exit:** One command takes a continuous recording and returns detected start/end times and allowed labels using real inference.

### D3 - Evaluate the Complete Pipeline

**Prerequisite:** D2 baseline ready.

1. Run the detector and classifier on the raw validation block, not pre-segmented ground-truth examples.
2. Implement official greedy same-label IoU matching and IoU-weighted F1. Count wrong labels, missed cycles, extra cycles, and inaccurate boundaries through that metric.
3. Inspect boundary failures and class errors. Keep any preprocessing fitting inside the training split.
4. Document baseline performance, subsequent validation-driven changes, and limits of the small dataset. Do not tune against `Test.csv`.
5. Add focused checks for non-zero-padded source timestamps, cycle ordering, valid start/end intervals, no-cycle input, and allowed labels.

**Exit:** A repeatable report measures the actual segmentation-plus-classification pipeline.

### D4 - Freeze and Hand Off Door

**Prerequisite:** D3 evaluation complete.

1. Refit the selected classifier on all labelled training data and freeze the chosen detector configuration.
2. Package preprocessing, model weights, feature order, dependency versions, and artifact-loading instructions.
3. Verify a fresh process can import the package and predict without training labels or any app services.
4. Confirm the Python return records and exported CSV agree; never hard-code a test cycle count from training labels.
5. Complete the shared handoff checklist and stop at the model gate. Do not begin backend implementation as part of this assignment.

**Exit:** Another teammate can reproduce Door training/evaluation and run its final predictor independently.

## Rail Corrugation Subsystem: Agent B

**Own:** `ml/rail/` on `feat/rail`. B also maintains the small shared Python setup and coordinates model merges; there is no current backend assignment.

**Deliver:** One Normal / Side I / Side II label per recording, with an evaluated three-class model and exact CSV export.

### R1 - Inspect Channel Layout and Lock Validation

**Prerequisite:** Phase 0 model contract agreed.

1. Read the Rail info kit and axle-position diagram. Verify 272 labelled recordings: 234 Normal, 14 Side I, and 24 Side II.
2. Inspect the actual CSV format before loading; keep the first speed-pulse column separate from the 128 vibration/shock channels.
3. Map channels to eight cars and eight axle positions per car. Positions 1, 3, 5, and 7 belong to Side I; positions 2, 4, 6, and 8 belong to Side II.
4. Create five stratified file-level folds with seed 42. Keep all windows from one recording in the same fold; use recording groups if inspection reveals related acquisitions and document that decision before evaluation.
5. Check for duplicate recordings and establish a local feature cache excluded from Git.

**Exit:** Channel mapping, class counts, and file-level validation folds are documented and reproducible.

### R2 - Build the Rail Baseline

**Prerequisite:** R1 complete.

1. Extract per-channel RMS, peak-to-peak, kurtosis, and spectral band-power features using NumPy/SciPy and the documented 10,000 Hz sampling rate.
2. Aggregate features by side while preserving side contrasts. Include a speed-pulse transition-rate feature without treating raw 0/1 pulses as physical speed.
3. Train a class-balanced random forest classifier and an always-Normal comparison baseline.
4. Process files sequentially and cache feature vectors, rather than holding the entire raw dataset in memory.
5. Implement `predict_rail`, standalone prediction, and exact CSV export. Open a baseline PR with real inference examples.

**Exit:** A file or directory can be processed into one allowed label per recording without other subsystem packages.

### R3 - Evaluate Minority-Class and Side Errors

**Prerequisite:** R2 baseline ready.

1. Evaluate macro F1 over all three labels, including classes receiving no predictions; also report per-class precision/recall and the confusion matrix.
2. Fit preprocessing on training folds only and select models by macro F1, not overall accuracy.
3. Compare against the always-Normal baseline and inspect Side I / Side II confusion and minority-class misses.
4. Test channel-to-side mapping, filename preservation, malformed recordings, and stable batch output ordering.
5. Record runtime and memory observations for a representative training batch; do not use test recordings for feature or model selection.

**Exit:** The report explains measured fault-class performance and validates batch feasibility.

### R4 - Freeze and Hand Off Rail

**Prerequisite:** R3 evaluation complete.

1. Refit the chosen model on all labelled training recordings.
2. Package the model, preprocessing, channel mapping, feature order, dependency metadata, and regeneration instructions.
3. Verify a fresh process can predict a multi-file batch using the supplied artifacts, without labels or app services.
4. Complete the shared handoff checklist and coordinate the four-package import/dependency check.
5. Stop at the model gate; do not create backend or frontend scaffolding during this assignment.

**Exit:** Rail inference and export are independently reproducible and compatible with the shared Python environment.

## SHM Subsystem: Agent C

**Own:** `ml/shm/` on `feat/shm`. Keep this separate from the ACV package and its PRs.

**Deliver:** One finite, nonnegative fatigue-damage estimate per recording.

### S1 - Inspect Stress Data and Lock Validation

**Prerequisite:** Phase 0 model contract agreed.

1. Read the SHM info kit and verify the 64 labelled, headerless numeric recordings and `filename,damage` label schema.
2. Check numeric parsing, missing values, recording lengths, and the distribution of target damage.
3. Create five shuffled file-level folds with seed 42. File numbers are random identifiers, not chronological order.
4. Document the loader, split, and the fact that all supplied recordings represent healthy operating conditions.

**Exit:** A reproducible loader and evaluation split exist without assuming damage classes or asset chronology.

### S2 - Build the SHM Baseline

**Prerequisite:** S1 complete.

1. Extract stress distribution, RMS, peak-to-peak, and successive-difference statistics.
2. Compare a random forest regressor with a training-fold median prediction baseline.
3. Implement `predict_shm`, standalone prediction, and exact CSV export with original filenames.
4. Save a baseline artifact and publish a focused SHM PR and handoff instructions.
5. After this working baseline, move to ACV V1-V2 before spending time on optional SHM experiments.

**Exit:** SHM runs independently from a file or directory and produces real numeric estimates.

### S3 - Evaluate Damage Estimates

**Prerequisite:** S2 ready; C may complete this after establishing the ACV baseline.

1. Evaluate MAPE and report the official `max(0, 1 - MAPE)` score; select the candidate with lower mean validation MAPE.
2. Fit preprocessing inside each training fold and inspect large relative errors, especially for small damage values.
3. Report baseline comparisons and limitations. Do not interpret the estimate as failure probability or remaining useful life.
4. Test headerless loading, filename preservation, invalid numeric input, and finite nonnegative outputs.

**Exit:** SHM has a reproducible evaluation report and tested prediction behaviour.

### S4 - Freeze and Hand Off SHM

**Prerequisite:** S3 complete.

1. Refit the chosen approach on all labelled SHM training data.
2. Package model/preprocessing, feature order, dependency metadata, and artifact-generation instructions.
3. Verify fresh-process inference without labels, ACV imports, or app services.
4. Complete the shared handoff checklist in a SHM-only PR.

**Exit:** SHM is independently ready for the later app adapter.

## ACV Subsystem: Agent C

**Own:** `ml/acv/` on `feat/acv`. Reuse the agreed Python dependencies, but do not import or depend on SHM code.

**Deliver:** A complete ranking of the cars in each workbook from most to least likely to have a refrigerant leak.

### V1 - Inspect Workbooks and Lock Case-Level Validation

**Prerequisite:** Phase 0 complete; C should finish the initial SHM baseline through S2 first.

1. Read the ACV info kit, all six training workbook schemas, and `Train_Labels.csv`.
2. Read labels and car identifiers as strings, preserving leading zeros such as `01`.
3. Discover each workbook's own `Car <NN> - <parameter>` headers. One workbook has a much richer schema; do not assume fixed column positions or universally available fields.
4. Record valid interpretations of operating-mode and information-valid signals. Do not guess numeric mode meanings that the references do not establish.
5. Define leave-one-workbook-out validation across the six cases; never split rows or cars from the same workbook between training and validation.

**Exit:** The loader handles all training schemas and the case-level evaluation protocol is fixed.

### V2 - Build a Transparent Ranking Baseline

**Prerequisite:** V1 complete.

1. Implement a baseline based on persistent cabin-temperature excess relative to peer cars and available cooling targets, using supported operating/validity signals where meaningful.
2. Use robust per-case summaries to reduce sensitivity to isolated readings and ordinary control cycling. Document which features are available in each schema and how missing channels affect the score.
3. Rank every detected car exactly once and break ties by header order. Fail clearly if usable comparison data is absent; never fabricate a successful ranking.
4. Implement `predict_acv`, returning a list of string IDs for each file. Join IDs with `|` only in the CSV serializer.
5. Save the ranker configuration and any learned preprocessing parameters, implement the standalone command, and open an ACV-only baseline PR.

**Exit:** Real workbook input produces a complete, duplicate-free ranked list with original identifiers preserved.

### V3 - Evaluate Localisation

**Prerequisite:** V2 ready.

1. Keep the initial baseline scoring rule fixed for case-level evaluation. If tuning weights or comparing variants, select using only the five training cases within each held-out fold.
2. Report the official score `(n - (r - 1)) / n`, with one-based true-car rank `r` among `n` cars, averaged across cases.
3. Include the true car's rank per held-out case and explain uncertainty from only six documented faults.
4. Test varied workbook schemas, leading-zero IDs, complete rankings, deterministic ties, and explicit failure on unusable telemetry.
5. Do not tune using `acv_test_case.xlsx`, and do not claim the ranker establishes a general no-fault detector.

**Exit:** ACV has a repeatable case-level evaluation and robust export semantics.

### V4 - Freeze and Hand Off ACV

**Prerequisite:** V3 complete.

1. Freeze the selected ranking configuration; fit any learned parameters on all labelled training cases after evaluation.
2. Publish schema mappings, dependency metadata, artifact/configuration loading instructions, and reproducible generation commands.
3. Verify standalone inference without labels, SHM imports, or app services.
4. Complete the shared handoff checklist in an ACV-only PR. C then ensures both SHM and ACV handoffs are complete.

**Exit:** ACV is independently ready for the later app adapter, with all car IDs and ranking order preserved.

## Shared Model Handoff Gate

**Every subsystem must pass this gate before app implementation starts.** An individual agent completing its assigned subsystem should report the handoff and continue only relevant model fixes; it should not automatically start deferred app work.

Each subsystem owner supplies:

- A README containing exact install, train/configure, evaluate, and predict commands that work from the repository root.
- Loader, feature/preprocessing code, inference function, and CSV serialization contained within its own package.
- Saved model artifacts or ranker configuration through the team's agreed file-sharing method, plus a versioned manifest and regeneration instructions in Git.
- Validation split definitions, baseline comparisons, the official metric, known limitations, and focused checks for its input/output contract.
- A real inference smoke check using training/validation recordings; do not commit raw recordings or label example-submission placeholders as actual model output.
- A prediction path that never trains, reads labels, imports another subsystem's implementation, or requires an HTTP server, database, or browser.

B coordinates the model merge; each owner fixes their own package. Install one common Python environment, import all four packages without side effects, and run each inference function and CLI from a fresh process. Confirm dependency compatibility, original filenames, allowed output values, and CSV agreement. This is the merge checkpoint even though backend and frontend have not been built.

## Deferred App Stage: After Model Handoff

This section preserves the final prototype requirements. **Do not implement it during the subsystem assignments above.** It becomes the next team task once all four packages pass the model gate.

Future ownership: A handles backend adapters; B handles frontend; C handles integration checks, final outputs, and demo packaging. Model defects still go to their subsystem owners. Keep these app branches separate from the subsystem branches.

### L1 - Freeze the App Contract

A creates `contracts/api.md`, using the real model outputs as fixtures. B reviews the fixtures before building screens; C checks all four output formats. App contracts add presentation and review metadata without changing the model functions or official CSV serializers.

| Endpoint | Request | Response or behaviour |
| --- | --- | --- |
| `POST /api/runs` | Multipart `subsystem` (`door`, `acv`, `rail`, or `shm`) and repeated `files` | HTTP 202 with `run_id` and `status`; Door accepts one CSV, ACV accepts XLSX batches, Rail/SHM accept CSV batches |
| `GET /api/runs/{id}` | Run ID | `run_id`, `subsystem`, `status`, `results`, `chart_series`, and nullable `error` |
| `GET /api/runs` | None | Newest-first run summaries |
| `PATCH /api/results/{result_id}/review` | `status` and `note` | Updated review metadata; status is `unreviewed`, `confirmed`, `dismissed`, or `resolved` |
| `GET /api/results/{result_id}/reviews` | Result ID | Timestamped review events |
| `GET /api/runs/{id}/export` | Run ID | Official CSV for a completed run |
| `POST /api/exports` | `{"run_ids":[...]}` | ZIP with one completed run per selected subsystem; reject duplicates and select all four for final submission |

Run status is `queued`, `running`, `completed`, or `failed`. Errors contain a code and readable message. Each result gains `result_id`, `review_status`, and `review_note`; ACV still has `ranked_cars` instead of `prediction`.

Chart series use `file_id`, `series_id`, `label`, `unit`, `x_kind` (`timestamp` or `sample_index`), and `points` shaped as `{x, y}`; optional `car_id` or `side` identifies ACV/Rail channels. Use Door current/position, ACV car temperatures, explicitly labelled side-aggregated Rail vibration, and SHM stress. Reuse subsystem loaders, downsample only presentation data, and do not invent timestamps or units.

**Exit:** A and B agree the API and fixtures; no model implementation changes are needed merely to present its results.

### L2 - Build Backend and Frontend in Parallel

**Prerequisite:** L1 complete and all models handed off.

1. A builds FastAPI with SQLite run/result/review persistence and a serial background inference worker. Call the subsystem functions directly; never retrain during requests.
2. Preserve original basenames, reject duplicate filenames/invalid schemas, process large batches sequentially, and persist failures rather than silently omitting files. Mark interrupted runs failed on restart.
3. Reuse subsystem CSV serializers and add ZIP export. Keep reviewer actions separate from immutable predictions.
4. B builds React/TypeScript views for all four subsystems: uploads, progress/errors, results, supporting charts, run history, review notes, and downloads. Use the fixtures only while endpoints are being connected; disable mocks for acceptance.
5. Poll active runs every second and stop on completion, failure, or navigation away. Show ACV as a ranked list, Door/Rail as classifications, and SHM as a numeric estimate.
6. Use within-subsystem review priority, not a fabricated cross-subsystem severity scale. Add recorded Door playback only after mandatory workflows pass.
7. C integrates real uploads and exports as endpoints become ready and reports model defects to their owners.

**Exit:** Each subsystem completes upload -> real inference -> visible results -> correct CSV through the app.

### L3 - Verify and Package the Final Prototype

**Prerequisite:** L2 complete.

1. Test invalid files, varied ACV schemas, leading-zero car IDs, Rail batches, missing artifacts, worker failures, review persistence, and all CSV/ZIP formats.
2. Verify desktop/mobile views, refresh behaviour, and a clean startup on another teammate's machine.
3. Freeze model and app versions. Run all four held-out datasets through the actual app and download `predictions.zip`. Do not tune models from test inputs; final submission predictions must come through the app, not just earlier CLI experiments.
4. Record one video of at most three minutes showing upload/results for Door, ACV, Rail, and SHM, plus prediction downloads. Include review history if time permits.
5. Package the registered team-name folder containing `app/`, required model artifacts, `predictions.zip`, the demo video, and optional methodology under `Optional_Items/`. Exclude raw datasets, uploaded copies, local databases, and secrets.

**Exit:** The team has a reproducible runnable app and complete final submission.

## Timing and Checkpoints

| Stage | 24-hour target | 48-hour target | Required outcome |
| --- | --- | --- | --- |
| Shared Python setup | Hours 0-2 | Hours 0-2 | Paths, dependencies, package ownership, and function/CLI contracts agreed |
| Independent subsystem work | Hours 2-12 | Hours 2-22 | A develops Door; B develops Rail; C establishes SHM then ACV baselines and evaluates both |
| Baseline model merge | Around hours 8-12 | Around hours 8-12 | Available baseline packages run together in one Python environment; no app needed |
| Model handoff gate | Hours 12-14 | Hours 22-24 | All four standalone packages, evaluated artifacts, and CSV exporters pass the shared gate |
| Deferred app implementation | Hours 14-20 | Hours 24-40 | L1-L2: agree API, then implement backend/frontend against real models |
| Final verification and packaging | Hours 20-24 | Hours 40-48 | L3: clean startup, app-generated predictions, demo, and final archive |

These are timeboxes, not accuracy guarantees. With three people and four subsystems, C owns two smaller datasets; timebox optional experiments so both receive validation and handoffs. If one subsystem is blocked, share the concrete blocker early and continue independent work. Preserve time for the compulsory app rather than spending the entire hackathon on models.

## Final Acceptance and Honest Claims

- All four packages pass the standalone model gate before the app stage.
- The final app processes one continuous Door test file, one ACV workbook, 68 Rail files, and 16 SHM files.
- `predictions.zip` contains exactly `door_predictions.csv`, `acv_predictions.csv`, `rail_predictions.csv`, and `shm_predictions.csv` directly at its root.
- ACV includes every car exactly once with original string IDs; Rail and SHM cover every input filename; Door exports detected cycles, not raw samples or a hard-coded count.
- Validation reports Door IoU-weighted F1, ACV mean rank-decay score, Rail macro F1, and SHM `max(0, 1 - MAPE)`. Test inputs are not used for training or model selection.
- Displayed and exported predictions agree, and engineer review actions do not overwrite predictions.
- Feedback is stored for future reviewed retraining; the prototype does not automatically improve after every review.
- Engineer-confirmed resolution is separate from physical recovery, and unrelated recordings are not presented as a real asset maintenance history.
- Door identifies abnormal resistance rather than its physical cause; Rail identifies corrugation side rather than a bogie defect or track location.
- ACV ranks likely leaking cars under the provided one-fault-per-case setup; it does not estimate leak quantity or validate a general no-fault detector.
- SHM estimates fatigue damage; it does not diagnose structural faults, predict failure probability, or provide remaining useful life.
- Optional recorded playback is explicitly simulated, not an actual onboard live connection.
