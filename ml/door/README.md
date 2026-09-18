# Door

Owner: **Agent A**. Implement **D1-D4** from [plan.md](../../plan.md), following [the shared contract](../../contracts/model.md).

**Status: scaffold only.** No model, ranking configuration, evaluation results, or working CSV exporter exists yet. Commands expose help and clearly fail until implemented.

## Data and Metric

- Local data: `DATASET_ROOT/Door`.
- Input: one continuous CSV recording.
- Official metric: IoU-weighted F1.
- Output: `door_predictions.csv` in the organiser's schema.

## Commands

Run from the repository root using your virtual environment's Python:

```text
python -m ml.door.train --help
python -m ml.door.evaluate --help
python -m ml.door.predict --help
```

Replace this section with verified train/evaluate/predict examples as you complete the phases. Training may use `ml.config.get_dataset_root()`; inference receives explicit paths and must not depend on labels.

## Handoff

Keep loaders, features, preprocessing, CSV serialization, and tests inside this package. Store generated models/configuration locally in ignored `artifacts/`; commit an artifact manifest and regeneration instructions outside that directory. Record split definitions, baseline comparisons, exact dependency versions, measured scores, and limitations. Do not implement backend/frontend work here.
