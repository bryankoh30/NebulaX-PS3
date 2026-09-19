"""Evaluate the complete Door pipeline on the held-out validation block.

Runs the *full* pipeline (segmentation + classification) on the raw validation
time-window — NOT on pre-segmented ground-truth cycles — and scores it with the
official IoU-weighted F1 metric (see ml/door/metric.py).

The validation block is the final 30% of labelled cycles (chronological).  To
evaluate segmentation on raw data we slice the continuous Train.csv stream from
the first validation cycle's start onward, so the detector must rediscover the
cycle boundaries itself.

Usage (from repository root):

    python -m ml.door.evaluate
    python -m ml.door.evaluate --artifacts DIR
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np

from ml.config import get_dataset_root
from ml.door.features import extract_features
from ml.door.loader import (
    load_labels,
    load_stream,
    make_split,
    segment_stream,
    ts_to_ms,
)
from ml.door.metric import Segment, score_segments

DEFAULT_ARTIFACT_DIR = Path(__file__).resolve().parent / "artifacts"


def _load_classifier(artifact_dir: Path):
    import joblib

    model_path = artifact_dir / "door_classifier.joblib"
    if not model_path.is_file():
        raise FileNotFoundError(
            f"Model not found: {model_path}. Train the 70% block first with "
            "`python -m ml.door.train`."
        )
    return joblib.load(model_path)["classifier"]


def evaluate(artifact_dir: Path) -> dict:
    dataset_root = get_dataset_root()
    door_dir = dataset_root / "Door"

    stream = load_stream(door_dir / "Train.csv")
    labels = load_labels(door_dir / "Train_Segments_Answer.csv")
    _train_labels, val_labels = make_split(labels)

    # Raw validation window: from the first validation cycle's start to the end
    # of the stream.  The detector must find boundaries with no label help.
    val_start_ts = val_labels["start_ts"].iloc[0]
    val_stream = stream[stream["ts"] >= val_start_ts].reset_index(drop=True)

    clf = _load_classifier(artifact_dir)

    # Segment + classify the raw validation window
    segments = segment_stream(val_stream)
    if segments:
        X = np.vstack([extract_features(s) for s in segments])
        preds = clf.predict(X)
    else:
        preds = []

    pred_segs = [
        Segment(
            start=ts_to_ms(seg["ts"].iloc[0]) / 1000.0,
            end=ts_to_ms(seg["ts"].iloc[-1]) / 1000.0,
            label=str(pred),
        )
        for seg, pred in zip(segments, preds)
    ]

    true_segs = [
        Segment(
            start=ts_to_ms(row["start_ts"]) / 1000.0,
            end=ts_to_ms(row["end_ts"]) / 1000.0,
            label=row["status"],
        )
        for _, row in val_labels.iterrows()
    ]

    result = score_segments(true_segs, pred_segs)

    # Extra diagnostics: label-level accuracy on matched cycles
    print("=" * 60)
    print("Door pipeline evaluation (raw validation block)")
    print("=" * 60)
    print(f"True cycles (val):      {int(result['n_true'])}")
    print(f"Predicted cycles:       {int(result['n_pred'])}")
    print(f"Matches (same label):   {int(result['n_matches'])}")
    print(f"Sum IoU over matches:   {result['sum_iou']:.4f}")
    print(f"Soft recall:            {result['soft_recall']:.4f}")
    print(f"Soft precision:         {result['soft_precision']:.4f}")
    print(f"IoU-weighted F1 score:  {result['score']:.4f}")
    print("=" * 60)

    # Classification-only diagnostic: match segments to true cycles by overlap
    # (ignoring label) and report the confusion, to separate segmentation vs.
    # classification error sources.
    _report_classification_breakdown(segments, preds, val_labels)

    return result


def _report_classification_breakdown(segments, preds, val_labels) -> None:
    """Diagnostic: how many detected cycles overlap a true cycle, and whether
    the classifier's label was correct.  Helps separate boundary error from
    label error."""
    if not segments:
        print("No segments detected — cannot break down classification.")
        return

    val_rows = list(val_labels.iterrows())
    correct = 0
    wrong = 0
    unmatched = 0
    for seg, pred in zip(segments, preds):
        ss = seg["ts"].iloc[0]
        se = seg["ts"].iloc[-1]
        best_overlap = 0.0
        best_status = None
        for _, row in val_rows:
            inter = (min(se, row["end_ts"]) - max(ss, row["start_ts"])).total_seconds()
            if inter > best_overlap:
                best_overlap = inter
                best_status = row["status"]
        if best_status is None:
            unmatched += 1
        elif str(pred) == best_status:
            correct += 1
        else:
            wrong += 1
    total = correct + wrong + unmatched
    print("\nClassification breakdown (detected cycles vs. best-overlap truth):")
    print(f"  Correct label:   {correct}/{total}")
    print(f"  Wrong label:     {wrong}/{total}")
    print(f"  No overlap:      {unmatched}/{total}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate the Door pipeline on the validation block.")
    parser.add_argument(
        "--artifacts",
        type=Path,
        default=DEFAULT_ARTIFACT_DIR,
        help="Artifact directory containing the trained classifier.",
    )
    args = parser.parse_args()
    evaluate(artifact_dir=args.artifacts)


if __name__ == "__main__":
    main()
