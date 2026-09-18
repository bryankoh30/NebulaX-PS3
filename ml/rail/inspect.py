"""R1: validate every training recording and freeze file-level folds."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from sklearn.model_selection import StratifiedGroupKFold

from .data import CHANNELS, digest, load_recording, training_labels

PACKAGE = Path(__file__).resolve().parent
CACHE = PACKAGE / "cache"


def inspect(dataset_root=None):
    root, labels = training_labels(dataset_root)
    CACHE.mkdir(parents=True, exist_ok=True)
    seen, records = {}, []
    for index, row in labels.iterrows():
        path = root / "Train" / row.filename
        values = load_recording(path)
        numeric_hash = hashlib.sha256(values.astype("<f8").tobytes()).hexdigest()
        seen.setdefault(numeric_hash, []).append(row.filename)
        records.append({"file_id": row.filename, "label": row.label, "sha256": digest(path), "numeric_sha256": numeric_hash})
        if (index + 1) % 25 == 0:
            print(f"Validated {index + 1}/272", flush=True)
    fold_ids = np.empty(len(labels), dtype=int)
    groups = np.array([r["numeric_sha256"] for r in records])
    for group in set(groups):
        if labels.loc[groups == group, "label"].nunique() != 1:
            raise ValueError(f"Conflicting labels for duplicate group: {seen[group]}")
    for fold, (_, validation) in enumerate(StratifiedGroupKFold(5, shuffle=True, random_state=42).split(labels.filename, labels.label, groups)):
        if set(labels.iloc[validation].label) != set(labels.label):
            raise ValueError("A validation fold lacks a class; review the grouping protocol")
        fold_ids[validation] = fold
    for record, fold in zip(records, fold_ids):
        record["fold"] = int(fold)
    duplicates = [names for names in seen.values() if len(names) > 1]
    report = {"seed": 42, "split": "StratifiedGroupKFold, numeric content groups, sorted filename, 5 folds", "duplicates": duplicates,
              "unique_numeric_recordings": len(seen),
              "fold_label_counts": {str(fold): labels.loc[fold_ids == fold, "label"].value_counts().to_dict() for fold in range(5)},
              "shape": [10000, 129], "speed_header": "Rotating speed", "channels": CHANNELS,
              "label_counts": labels.label.value_counts().to_dict(), "recordings": records}
    (PACKAGE / "validation_split.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"label_counts": report["label_counts"], "duplicates": duplicates, "fold_counts": np.bincount(fold_ids).tolist()}))
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-root", type=Path)
    inspect(parser.parse_args().dataset_root)
