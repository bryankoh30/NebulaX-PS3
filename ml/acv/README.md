# ACV Refrigerant-Leak Localisation

Owner: **Agent C**. This package implements phases V1-V4 from [`plan.md`](../../plan.md) and follows the shared [`model.md`](../../contracts/model.md) contract. It is independent of SHM and contains no backend or frontend code.

## Approach

Each workbook is one train case with telemetry from all cars. The loader discovers car IDs and parameters from headers shaped as `Car <NN> - <parameter>`; it does not assume a fixed column count or hard-code IDs `01`-`08`.

The frozen ranker uses peer-relative, robust whole-case signals:

- median and 90th-percentile cabin-temperature excess relative to the row-wise peer median;
- fraction of readings above the peer median;
- 90th-percentile cabin-temperature excess over the available cooling target;
- for the rich schema, imbalance between Refrigeration Systems 1 and 2 high-side pressure and compressor duty.

Each component is converted to a within-case percentile and combined with the frozen weights in `artifacts/ranker_config.json`. Cars with entirely unavailable telemetry remain in the output after scored cars, in header order. Ties are deterministic by header order.

This is a transparent localisation ranker, not a calibrated failure probability. It assumes the organiser's one-fault-per-case setup and cannot establish a general no-fault detector or estimate leak quantity.

## Data and Validation

- Local data: `DATASET_ROOT/ACV`.
- Training data: six labelled whole workbooks; validation never splits rows or cars within a workbook.
- Official metric: linear rank-decay, averaged across cases.
- Output: `acv_predictions.csv` with exact columns `file_id,ranked_cars`.

The fixed label-free rule ranked the disclosed faulty car first in all six training cases, producing a mean rank-decay score of **1.0000**. See [`evaluation_report.json`](evaluation_report.json). Because there are only six documented faults and no independent labels beyond the organiser's held-out case, this score is an in-sample rule check rather than a reliable estimate of deployment performance.

## Commands

Run from the repository root:

```text
# Inspect all training schemas and freeze the ranker configuration
python -m ml.acv.train

# Evaluate whole labelled workbooks with the official metric
python -m ml.acv.evaluate

# Predict one workbook or every XLSX workbook in a directory
python -m ml.acv.predict --input <case.xlsx_or_directory> --output acv_predictions.csv

# Focused package tests
python -m pytest ml/acv/tests/test_acv.py -q
```

`--dataset-root` can override `DATASET_ROOT` for training/evaluation. `--artifacts` can override the default `ml/acv/artifacts/` directory. Prediction uses only explicit input paths and frozen artifacts; it does not read labels or the dataset root.

## Handoff

- `data.py`: varied-schema XLSX loading, header discovery, input batching, and schema summaries.
- `ranker.py`: frozen configuration, robust feature calculation, ranking, and official metric.
- `inference.py`: public `predict_acv(input_paths, artifact_dir=None)` interface.
- `serialize.py` and `predict.py`: exact CSV export and standalone CLI.
- `artifact_manifest.json`: artifact descriptions, regeneration commands, validation summary, and limitations.

Generated `ranker_config.json` and `metadata.json` live in the git-ignored `artifacts/` directory. Regenerate them with `python -m ml.acv.train`. The package imports without reading data or loading artifacts.
