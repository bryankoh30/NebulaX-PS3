# Shared Model Contract

This is the shared subsystem contract from plan.md. Owners coordinate changes with B before other packages depend on them. The separate [API contract](api.md) defines backend/frontend metadata; model functions remain independent of the application.

## Ownership

| Owner | Folder | Public function |
| --- | --- | --- |
| A | `ml/door/` | `predict_door(input_path, artifact_dir=None)` |
| B | `ml/rail/` | `predict_rail(input_paths, artifact_dir=None)` |
| C | `ml/acv/` | `predict_acv(input_paths, artifact_dir=None)` |
| C | `ml/shm/` | `predict_shm(input_paths, artifact_dir=None)` |

Functions live in their package's `inference.py`. Paths accept strings or pathlib.Path. Batch functions receive a sequence of file paths; the CLI expands a directory into sorted paths before calling them. No package imports another subsystem's implementation.

## Records

Return a list of ordinary JSON-serializable dictionaries. Convert NumPy values to Python scalars. These are shapes, not example predictions to submit:

- Door: `start_time`, `end_time`, `prediction`. Use ISO timestamps without inventing a timezone and exactly `Normal` or `Abnormal resistance`.
- Rail: `file_id`, `prediction`. Use the original basename including extension and exactly `Normal`, `Side I`, or `Side II`.
- ACV: `file_id`, `ranked_cars`. The ranking is a list of string IDs from that workbook's headers, preserving leading zeros. Include every car exactly once; there is no `prediction` field.
- SHM: `file_id`, `prediction`. Use a finite nonnegative numeric damage estimate.

Inference never trains, reads labels, or requires the dataset root. Missing artifacts or invalid input raise explicit errors; there are no mock fallbacks. Importing modules performs no model loading or training. Default artifacts live beside each inference module in `artifacts/`, independent of the working directory.

## CLI and CSV

Each package provides `python -m ml.<subsystem>.predict --input PATH --output PATH [--artifacts PATH]`. Door input is one CSV. Other subsystems accept a file or directory; ACV uses XLSX and Rail/SHM use CSV. Process directory files in sorted basename order, reject empty inputs and duplicate IDs, and do not silently omit invalid recordings.

| Subsystem | Output | Exact columns |
| --- | --- | --- |
| Door | `door_predictions.csv` | `start_time,end_time,prediction` |
| ACV | `acv_predictions.csv` | `file_id,ranked_cars` |
| Rail | `rail_predictions.csv` | `file_id,prediction` |
| SHM | `shm_predictions.csv` | `file_id,prediction` |

ACV joins the list of string IDs with a literal pipe character only at CSV serialization. Do not include a dataframe index, confidence, application IDs, or reviewer metadata. CSV writing belongs inside each subsystem package for reuse by the later backend.

All four CLIs implement inference and export using installed frozen artifacts. A successful invocation must mean a real prediction file was written; missing artifacts fail explicitly. The backend reuses each subsystem's CSV serializer, including `ml.shm.serialize.write_predictions`.

## Training and Handoff

Training/evaluation may call `ml.config.get_dataset_root()`; it loads the repository-local .env and honours existing environment variables. Dataset folders are Door, Rail_Corrugation, ACV, and SHM. Never tune on organiser test inputs.

Owners supply reproducible commands, fixed validation splits, official metrics, focused tests, versioned artifact manifests, and fresh-process inference checks. Models/configurations are transferred separately or regenerated from committed code. Stop at the model handoff gate until app development becomes the active task.
