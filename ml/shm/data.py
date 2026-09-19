"""Validated data loading for the SHM fatigue-damage subsystem."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd


DATASET_DIRECTORY = "SHM"
LABEL_COLUMNS = ("filename", "damage")


def resolve_shm_root(dataset_root: str | Path) -> Path:
    """Resolve either the common dataset root or the SHM directory itself."""
    root = Path(dataset_root).expanduser().resolve()
    shm_root = root if root.name.casefold() == DATASET_DIRECTORY.casefold() else root / DATASET_DIRECTORY
    if not shm_root.is_dir():
        raise FileNotFoundError(f"SHM dataset directory does not exist: {shm_root}")
    return shm_root


def load_signal(path: str | Path) -> np.ndarray:
    """Load one headerless, single-column, finite numeric stress recording."""
    source = Path(path)
    if source.suffix.casefold() != ".csv":
        raise ValueError(f"SHM recordings must be CSV files: {source}")
    if not source.is_file():
        raise FileNotFoundError(f"SHM recording does not exist: {source}")

    try:
        frame = pd.read_csv(source, header=None)
    except (OSError, pd.errors.ParserError, UnicodeDecodeError) as exc:
        raise ValueError(f"Could not parse SHM recording {source}: {exc}") from exc
    if frame.shape[1] != 1:
        raise ValueError(
            f"Expected one headerless stress column in {source}, found {frame.shape[1]} columns."
        )
    try:
        signal = pd.to_numeric(frame.iloc[:, 0], errors="raise").to_numpy(dtype=np.float64)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"SHM recording contains non-numeric values: {source}") from exc
    if signal.size < 3:
        raise ValueError(f"SHM recording must contain at least 3 observations: {source}")
    if not np.isfinite(signal).all():
        raise ValueError(f"SHM recording contains NaN or infinite values: {source}")
    return signal


def load_labels(shm_root: str | Path) -> pd.DataFrame:
    """Load and validate the filename-to-damage training label table."""
    root = resolve_shm_root(shm_root)
    path = root / "Train_Labels.csv"
    if not path.is_file():
        raise FileNotFoundError(f"SHM label file does not exist: {path}")
    labels = pd.read_csv(path)
    if tuple(labels.columns) != LABEL_COLUMNS:
        raise ValueError(f"Expected label columns {LABEL_COLUMNS}, found {tuple(labels.columns)}")
    if labels.empty:
        raise ValueError("SHM label file is empty.")
    if labels["filename"].isna().any() or labels["filename"].duplicated().any():
        raise ValueError("SHM labels contain missing or duplicate filenames.")
    try:
        labels["damage"] = pd.to_numeric(labels["damage"], errors="raise").astype(float)
    except (TypeError, ValueError) as exc:
        raise ValueError("SHM damage labels must be numeric.") from exc
    damage = labels["damage"].to_numpy()
    if not np.isfinite(damage).all() or np.any(damage <= 0):
        raise ValueError("SHM damage labels must be finite and strictly positive for MAPE.")

    expected = set(labels["filename"])
    actual = {path.name for path in (root / "Train").glob("*.csv")}
    if expected != actual:
        missing = sorted(expected - actual)
        unlabelled = sorted(actual - expected)
        raise ValueError(f"Label/file mismatch; missing={missing}, unlabelled={unlabelled}")
    return labels


def discover_csv_files(path: str | Path) -> list[Path]:
    """Expand a single CSV or directory into a deterministic input list."""
    source = Path(path).expanduser().resolve()
    if source.is_file():
        files = [source]
    elif source.is_dir():
        files = sorted(source.glob("*.csv"), key=lambda item: item.name.casefold())
    else:
        raise FileNotFoundError(f"SHM input does not exist: {source}")
    if not files:
        raise ValueError(f"No CSV recordings found in {source}")
    names = [item.name for item in files]
    if len(names) != len(set(names)):
        raise ValueError("SHM input contains duplicate output file IDs.")
    return files


def iter_training_signals(shm_root: str | Path) -> Iterable[tuple[str, np.ndarray, float]]:
    """Yield labelled training recordings in label-table order."""
    root = resolve_shm_root(shm_root)
    labels = load_labels(root)
    for row in labels.itertuples(index=False):
        yield row.filename, load_signal(root / "Train" / row.filename), float(row.damage)
