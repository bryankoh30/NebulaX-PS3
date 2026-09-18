"""Official Door scoring metric: IoU-weighted F1.

Implements exactly the matching + scoring rules from the Door Info Kit Section 4:

- A predicted segment can only match a true segment with the SAME label.
- Among same-label pairs, a match requires IoU > 0.
- Matching is one-to-one, assigned greedily by highest IoU first.
- Each match's credit is its IoU value itself.
- soft_recall    = sum(IoU over matches) / n_true
- soft_precision = sum(IoU over matches) / n_pred
- score = harmonic mean of soft_recall and soft_precision (0 if both 0).

IoU is computed on the time interval [start, end] in seconds.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Segment:
    start: float  # seconds (any consistent numeric epoch)
    end: float
    label: str


def iou(a: Segment, b: Segment) -> float:
    """Intersection-over-union of two time intervals (0 if no overlap)."""
    intersection = max(0.0, min(a.end, b.end) - max(a.start, b.start))
    union = (a.end - a.start) + (b.end - b.start) - intersection
    if union <= 0:
        return 0.0
    return intersection / union


def score_segments(
    true_segs: list[Segment],
    pred_segs: list[Segment],
) -> dict[str, float]:
    """Compute IoU-weighted F1 and its components.

    Returns a dict with ``score``, ``soft_recall``, ``soft_precision``,
    ``sum_iou``, ``n_true``, ``n_pred``, ``n_matches``.
    """
    n_true = len(true_segs)
    n_pred = len(pred_segs)

    # Build all valid candidate pairs (same label, IoU > 0)
    candidates: list[tuple[float, int, int]] = []
    for ti, t in enumerate(true_segs):
        for pi, p in enumerate(pred_segs):
            if t.label != p.label:
                continue
            v = iou(t, p)
            if v > 0:
                candidates.append((v, ti, pi))

    # Greedy one-to-one matching, highest IoU first
    candidates.sort(key=lambda x: x[0], reverse=True)
    used_true: set[int] = set()
    used_pred: set[int] = set()
    sum_iou = 0.0
    n_matches = 0
    for v, ti, pi in candidates:
        if ti in used_true or pi in used_pred:
            continue
        used_true.add(ti)
        used_pred.add(pi)
        sum_iou += v
        n_matches += 1

    soft_recall = sum_iou / n_true if n_true > 0 else 0.0
    soft_precision = sum_iou / n_pred if n_pred > 0 else 0.0
    if soft_recall + soft_precision > 0:
        score = 2 * soft_recall * soft_precision / (soft_recall + soft_precision)
    else:
        score = 0.0

    return {
        "score": score,
        "soft_recall": soft_recall,
        "soft_precision": soft_precision,
        "sum_iou": sum_iou,
        "n_true": float(n_true),
        "n_pred": float(n_pred),
        "n_matches": float(n_matches),
    }
