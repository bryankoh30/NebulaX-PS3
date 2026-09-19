"""Focused checks for the Door subsystem contract.

Covers: non-zero-padded timestamp round-trip, gap-based segmentation, cycle
ordering and valid start/end intervals, no-cycle input, the IoU metric, and the
CSV serializer schema.  These use tiny synthetic streams and do NOT require the
dataset or a trained model.

Run from the repository root:

    python -m pytest ml/door/tests/test_door.py -q
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from ml.door.loader import (
    format_timestamp,
    parse_timestamp,
    segment_stream,
)
from ml.door.metric import Segment, iou, score_segments
from ml.door.predict import CSV_COLUMNS, write_predictions


# ── Timestamp handling ──────────────────────────────────────────────────────

def test_parse_non_zero_padded_timestamp():
    ts = parse_timestamp("2023-7-5-0-11-17-664")
    assert (ts.year, ts.month, ts.day) == (2023, 7, 5)
    assert (ts.hour, ts.minute, ts.second) == (0, 11, 17)
    assert ts.microsecond == 664_000


def test_timestamp_output_is_iso_without_timezone():
    original = "2023-7-5-0-0-3-700"
    assert format_timestamp(parse_timestamp(original)) == "2023-07-05T00:00:03.700"


def test_timestamp_roundtrip_edge_values():
    for original in ["2023-7-5-1-10-17-112", "2023-12-31-23-59-59-999", "2023-1-1-0-0-0-0"]:
        parsed = parse_timestamp(original)
        assert parse_timestamp(format_timestamp(parsed)) == parsed


@pytest.mark.parametrize("value", ["2023-07-05T00:00:09.020", "2023-7-5-0-0-9-20"])
def test_both_timestamp_formats_preserve_milliseconds(value):
    assert format_timestamp(parse_timestamp(value)) == "2023-07-05T00:00:09.020"


@pytest.mark.parametrize("value", ["2023-2-30-0-0-0-0", "bad", "2023-07-05T00:00:00Z"])
def test_timestamp_parser_rejects_invalid_or_ambiguous_values(value):
    with pytest.raises(ValueError):
        parse_timestamp(value)


# ── Segmentation ────────────────────────────────────────────────────────────

def _make_stream(row_specs):
    """row_specs: list of timestamp strings; build a minimal Door-like df."""
    df = pd.DataFrame({"Datetime": row_specs})
    df["ts"] = df["Datetime"].map(parse_timestamp)
    return df


def test_segment_splits_on_large_gap():
    # Two cycles: first at 20ms spacing, then a 30s gap, then another
    rows = [
        "2023-7-5-0-0-0-0", "2023-7-5-0-0-0-20", "2023-7-5-0-0-0-40",
        # big gap (30s)
        "2023-7-5-0-0-30-40", "2023-7-5-0-0-30-60",
    ]
    df = _make_stream(rows)
    segs = segment_stream(df)
    assert len(segs) == 2
    assert len(segs[0]) == 3
    assert len(segs[1]) == 2


def test_segment_no_split_within_cycle():
    rows = ["2023-7-5-0-0-0-0", "2023-7-5-0-0-0-20", "2023-7-5-0-0-0-40"]
    df = _make_stream(rows)
    segs = segment_stream(df)
    assert len(segs) == 1


def test_segment_empty_stream_returns_empty():
    df = pd.DataFrame({"Datetime": [], "ts": []})
    assert segment_stream(df) == []


def test_segments_are_time_ordered_with_valid_intervals():
    rows = [
        "2023-7-5-0-0-0-0", "2023-7-5-0-0-0-20",
        "2023-7-5-0-1-0-0", "2023-7-5-0-1-0-20",
        "2023-7-5-0-2-0-0", "2023-7-5-0-2-0-20",
    ]
    df = _make_stream(rows)
    segs = segment_stream(df)
    assert len(segs) == 3
    prev_end = None
    for s in segs:
        start, end = s["ts"].iloc[0], s["ts"].iloc[-1]
        assert start <= end  # valid interval
        if prev_end is not None:
            assert start > prev_end  # chronological, non-overlapping
        prev_end = end


# ── Metric ──────────────────────────────────────────────────────────────────

def test_iou_perfect_and_none():
    a = Segment(0.0, 10.0, "Normal")
    assert iou(a, Segment(0.0, 10.0, "Normal")) == pytest.approx(1.0)
    assert iou(a, Segment(20.0, 30.0, "Normal")) == 0.0


def test_score_perfect_submission():
    true = [Segment(0, 10, "Normal"), Segment(20, 30, "Abnormal resistance")]
    pred = [Segment(0, 10, "Normal"), Segment(20, 30, "Abnormal resistance")]
    r = score_segments(true, pred)
    assert r["score"] == pytest.approx(1.0)


def test_score_wrong_label_scores_zero():
    true = [Segment(0, 10, "Normal")]
    pred = [Segment(0, 10, "Abnormal resistance")]  # perfect timing, wrong label
    r = score_segments(true, pred)
    assert r["score"] == 0.0
    assert r["n_matches"] == 0


def test_score_extra_prediction_lowers_precision():
    true = [Segment(0, 10, "Normal")]
    pred = [Segment(0, 10, "Normal"), Segment(100, 110, "Normal")]  # one spurious
    r = score_segments(true, pred)
    assert r["soft_recall"] == pytest.approx(1.0)
    assert r["soft_precision"] == pytest.approx(0.5)
    assert r["score"] == pytest.approx(2 / 3)


def test_score_greedy_one_to_one():
    # Two preds overlapping one true; only the best matches
    true = [Segment(0, 10, "Normal")]
    pred = [Segment(0, 9, "Normal"), Segment(1, 10, "Normal")]
    r = score_segments(true, pred)
    assert r["n_matches"] == 1


# ── CSV serializer ────────────────────────────────────────────────────────────

def test_write_predictions_schema(tmp_path: Path):
    records = [
        {"start_time": "2023-7-5-0-0-0-0", "end_time": "2023-7-5-0-0-3-700", "prediction": "Normal"},
        {"start_time": "2023-7-5-0-1-0-0", "end_time": "2023-7-5-0-1-3-0", "prediction": "Abnormal resistance"},
    ]
    out = tmp_path / "door_predictions.csv"
    write_predictions(records, out)
    df = pd.read_csv(out)
    assert list(df.columns) == CSV_COLUMNS
    assert len(df) == 2
    assert set(df["prediction"]) <= {"Normal", "Abnormal resistance"}


def test_write_predictions_empty(tmp_path: Path):
    out = tmp_path / "empty.csv"
    write_predictions([], out)
    df = pd.read_csv(out)
    assert list(df.columns) == CSV_COLUMNS
    assert len(df) == 0
