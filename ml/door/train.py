"""Training pipeline for Door abnormal-resistance classifier.

Segmentation is deterministic (gap-based) and needs no training.  This script
trains the *classifier* that labels each detected cycle Normal vs. Abnormal
resistance, and saves the model plus feature order to ``artifacts/``.

Usage (from repository root):

    python -m ml.door.train                 # train on the 70% training block
    python -m ml.door.train --full          # refit on ALL labelled data (D4 freeze)
    python -m ml.door.train --artifacts DIR # custom artifact output directory
"""

from __future__ import annotations

import argparse
import json
import platform
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier

from ml.config import get_dataset_root
from ml.door.features import FEATURE_NAMES, build_feature_matrix
from ml.door.loader import (
    load_labels,
    load_stream,
    make_split,
    segment_stream,
)

DEFAULT_ARTIFACT_DIR = Path(__file__).resolve().parent / "artifacts"
MODEL_FILENAME = "door_classifier.joblib"
MANIFEST_FILENAME = "manifest.json"

# Labels used by the classifier
LABEL_NORMAL = "Normal"
LABEL_ABNORMAL = "Abnormal resistance"

RANDOM_STATE = 42


def _match_segments_to_labels(
    segments: list[pd.DataFrame],
    labels: pd.DataFrame,
) -> tuple[np.ndarray, list[str]]:
    """Align detected segments with ground-truth labels by time overlap.

    For each labelled cycle we find the detected segment whose time range best
    overlaps it, then take that segment's features and the cycle's status.
    Because segmentation is deterministic and matches the labels exactly on the
    training stream, this is a robust 1:1 alignment.

    Returns (feature_matrix, status_list).
    """
    seg_ranges = [
        (s["ts"].iloc[0], s["ts"].iloc[-1], idx) for idx, s in enumerate(segments)
    ]

    matched_features: list[np.ndarray] = []
    matched_status: list[str] = []

    from ml.door.features import extract_features

    for _, row in labels.iterrows():
        ls, le = row["start_ts"], row["end_ts"]
        best_idx = None
        best_overlap = 0.0
        for ss, se, idx in seg_ranges:
            inter = (min(le, se) - max(ls, ss)).total_seconds()
            if inter > best_overlap:
                best_overlap = inter
                best_idx = idx
        if best_idx is not None and best_overlap > 0:
            matched_features.append(extract_features(segments[best_idx]))
            matched_status.append(row["status"])

    X = np.vstack(matched_features) if matched_features else np.empty((0, len(FEATURE_NAMES)))
    return X, matched_status


def build_classifier() -> RandomForestClassifier:
    """Class-balanced random forest — handles the 80/30 class imbalance."""
    return RandomForestClassifier(
        n_estimators=400,
        max_depth=None,
        min_samples_leaf=1,
        class_weight="balanced",
        random_state=RANDOM_STATE,
        n_jobs=-1,
    )


def train(full: bool, artifact_dir: Path) -> dict:
    """Train the classifier and persist model + manifest.

    Parameters
    ----------
    full:
        When True, fit on all 110 labelled cycles (D4 freeze).  Otherwise fit
        only on the 70% training block, leaving the last 30% for validation.
    artifact_dir:
        Where to write ``door_classifier.joblib`` and ``manifest.json``.
    """
    dataset_root = get_dataset_root()
    door_dir = dataset_root / "Door"
    train_csv = door_dir / "Train.csv"
    answer_csv = door_dir / "Train_Segments_Answer.csv"

    stream = load_stream(train_csv)
    labels = load_labels(answer_csv)
    segments = segment_stream(stream)

    if full:
        fit_labels = labels
        split_desc = "all labelled cycles (freeze)"
    else:
        fit_labels, _val_labels = make_split(labels)
        split_desc = "70% chronological training block"

    X, y = _match_segments_to_labels(segments, fit_labels)
    if len(X) == 0:
        raise RuntimeError("No segments matched labels; check segmentation.")

    clf = build_classifier()
    clf.fit(X, y)

    artifact_dir.mkdir(parents=True, exist_ok=True)
    model_path = artifact_dir / MODEL_FILENAME
    joblib.dump(
        {
            "classifier": clf,
            "feature_names": FEATURE_NAMES,
            "classes": list(clf.classes_),
        },
        model_path,
    )

    import sklearn

    manifest = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "model_file": MODEL_FILENAME,
        "n_training_cycles": int(len(X)),
        "class_distribution": {c: int((np.array(y) == c).sum()) for c in set(y)},
        "split": split_desc,
        "feature_names": FEATURE_NAMES,
        "n_features": len(FEATURE_NAMES),
        "gap_threshold_ms": 500,
        "random_state": RANDOM_STATE,
        "dependencies": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "scikit-learn": sklearn.__version__,
            "joblib": joblib.__version__,
        },
    }
    (artifact_dir / MANIFEST_FILENAME).write_text(json.dumps(manifest, indent=2))

    print(f"Trained on {len(X)} cycles ({split_desc}).")
    print(f"Class distribution: {manifest['class_distribution']}")
    print(f"Saved model -> {model_path}")
    print(f"Saved manifest -> {artifact_dir / MANIFEST_FILENAME}")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Train the Door abnormal-resistance classifier.")
    parser.add_argument(
        "--full",
        action="store_true",
        help="Refit on ALL labelled cycles (D4 freeze). Default fits the 70%% training block.",
    )
    parser.add_argument(
        "--artifacts",
        type=Path,
        default=DEFAULT_ARTIFACT_DIR,
        help="Artifact output directory (default: this package's artifacts/).",
    )
    args = parser.parse_args()
    train(full=args.full, artifact_dir=args.artifacts)


if __name__ == "__main__":
    main()
