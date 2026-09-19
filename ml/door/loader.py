"""Door data loader and timestamp utilities."""

from __future__ import annotations

from pathlib import Path
import re

import numpy as np
import pandas as pd


# ── Timestamp helpers ──────────────────────────────────────────────────────────

def parse_timestamp(s: str) -> pd.Timestamp:
    """Parse native 'YYYY-M-D-H-M-S-ms' or timezone-free ISO Door timestamps.

    The format is NOT zero-padded (e.g. '2023-7-5-0-0-3-700').
    Milliseconds are stored as an integer (0-999); pandas Timestamp takes
    microseconds so we multiply by 1000.
    """
    value = str(s)
    if re.fullmatch(r"\d{4}(?:-\d{1,2}){5}-\d{1,3}", value):
        yr, mo, dy, h, m, sec, ms = [int(x) for x in value.split("-")]
        return pd.Timestamp(yr, mo, dy, h, m, sec, ms * 1_000)
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?", value):
        return pd.Timestamp(value)
    raise ValueError(f"Invalid Door timestamp (expected source format or timezone-free ISO): {value}")


def format_timestamp(ts: pd.Timestamp) -> str:
    """Return consistent ISO milliseconds without inventing a timezone."""
    if ts.tzinfo is not None:
        raise ValueError("Door recordings must use timezone-free timestamps.")
    return ts.isoformat(timespec="milliseconds")


def ts_to_ms(ts: pd.Timestamp) -> int:
    """Convert Timestamp to integer milliseconds since epoch (for arithmetic)."""
    return int(ts.value) // 1_000_000


# ── Main loader ────────────────────────────────────────────────────────────────

# Boundary gap threshold in milliseconds.  Within-cycle sampling is 20 ms;
# between-cycle idle periods are all >10 000 ms.  500 ms cleanly separates them.
GAP_THRESHOLD_MS: int = 500


def load_stream(path: str | Path) -> pd.DataFrame:
    """Load a Door CSV recording and attach a parsed Timestamp column.

    Returns the original DataFrame plus an extra ``ts`` column.
    No labels are required or read.
    """
    df = pd.read_csv(path)
    df["ts"] = df["Datetime"].map(parse_timestamp)
    df = df.sort_values("ts").reset_index(drop=True)
    return df


def segment_stream(df: pd.DataFrame, gap_threshold_ms: int = GAP_THRESHOLD_MS) -> list[pd.DataFrame]:
    """Split a continuous Door recording into individual door-cycle segments.

    A new segment begins whenever the gap between consecutive rows exceeds
    ``gap_threshold_ms`` milliseconds (between-cycle idle period).  Within each
    cycle the sampling interval is 20 ms, so the threshold of 500 ms leaves a
    large safety margin.

    Parameters
    ----------
    df:
        Output of :func:`load_stream` — must have a ``ts`` column.
    gap_threshold_ms:
        Gap in milliseconds above which a new segment starts.  Default 500 ms.

    Returns
    -------
    list[pd.DataFrame]
        One DataFrame per detected cycle, each a contiguous slice of ``df``.
    """
    if df.empty:
        return []

    gap_ms = df["ts"].diff().dt.total_seconds() * 1_000
    boundary_mask = gap_ms > gap_threshold_ms

    # Build list of (start_row_index, end_row_index) pairs
    starts = [0] + list(boundary_mask[boundary_mask].index)
    ends = list(boundary_mask[boundary_mask].index) + [len(df)]

    segments = []
    for s, e in zip(starts, ends):
        chunk = df.iloc[s:e].copy()
        if len(chunk) > 0:
            segments.append(chunk)
    return segments


def load_labels(path: str | Path) -> pd.DataFrame:
    """Load ``Train_Segments_Answer.csv`` and add parsed timestamp columns.

    Returns the original DataFrame plus ``start_ts`` and ``end_ts`` columns.
    This is only used during training/evaluation, never during inference.
    """
    ans = pd.read_csv(path)
    ans["start_ts"] = ans["start_time"].map(parse_timestamp)
    ans["end_ts"] = ans["end_time"].map(parse_timestamp)
    return ans


# ── Train/validation split ────────────────────────────────────────────────────

# The final 30 % of complete cycles (chronological) form the validation block.
# This is a contiguous time block — the last 33 of 110 labelled segments.
TRAIN_FRAC: float = 0.70


def make_split(labels: pd.DataFrame, train_frac: float = TRAIN_FRAC) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (train_labels, val_labels) as a chronological 70/30 split.

    The split is on *complete labelled cycles*, ordered by start time, so no
    cycle is partially included in both blocks and there is no overlap.
    """
    labels = labels.sort_values("start_ts").reset_index(drop=True)
    n = len(labels)
    split_idx = int(n * train_frac)
    return labels.iloc[:split_idx].copy(), labels.iloc[split_idx:].copy()
