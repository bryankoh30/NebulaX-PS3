"""Modular, file-level features for SHM stress recordings."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.signal import find_peaks
from scipy.stats import kurtosis, skew

from ml.shm.data import iter_training_signals, load_signal, resolve_shm_root


DEFAULT_GROUPS = ("statistics", "distribution")
SUPPORTED_GROUPS = ("statistics", "distribution", "peaks", "dynamic")
RAW_PERCENTILES = (1, 5, 10, 25, 75, 90, 95, 99, 99.5)


def _safe_moment(value: float) -> float:
    return float(value) if np.isfinite(value) else 0.0


def statistics_features(signal: np.ndarray) -> dict[str, float]:
    """Fifteen compact location, scale, and nonduplicate absolute-stress statistics."""
    absolute = np.abs(signal)
    q25, q75 = np.percentile(signal, [25, 75])
    return {
        "stats__mean": float(np.mean(signal)),
        "stats__median": float(np.median(signal)),
        "stats__std": float(np.std(signal)),
        "stats__variance": float(np.var(signal)),
        "stats__min": float(np.min(signal)),
        "stats__max": float(np.max(signal)),
        "stats__range": float(np.ptp(signal)),
        "stats__rms": float(np.sqrt(np.mean(np.square(signal)))),
        "stats__mean_abs": float(np.mean(absolute)),
        "stats__iqr": float(q75 - q25),
        "stats__skewness": _safe_moment(skew(signal, bias=False)),
        "stats__kurtosis": _safe_moment(kurtosis(signal, fisher=True, bias=False)),
        "stats__abs_median": float(np.median(absolute)),
        "stats__abs_std": float(np.std(absolute)),
        "stats__max_abs": float(np.max(absolute)),
    }


def distribution_features(signal: np.ndarray) -> dict[str, float]:
    """Twenty-two nonduplicate raw/absolute tail and exceedance features."""
    absolute = np.abs(signal)
    result: dict[str, float] = {}
    raw_values = np.percentile(signal, RAW_PERCENTILES)
    absolute_values = np.percentile(absolute, RAW_PERCENTILES)
    for percentile, value in zip(RAW_PERCENTILES, raw_values, strict=True):
        result[f"dist__p{str(percentile).replace('.', '_')}"] = float(value)
    for percentile, value in zip(RAW_PERCENTILES, absolute_values, strict=True):
        result[f"dist__abs_p{str(percentile).replace('.', '_')}"] = float(value)

    mean = float(np.mean(signal))
    std = float(np.std(signal))
    centered = np.abs(signal - mean)
    for multiplier in (1, 2, 3):
        result[f"dist__fraction_beyond_{multiplier}std"] = float(
            np.mean(centered > multiplier * std)
        )
    result["dist__tail_ratio_abs_p99_to_median"] = float(
        result["dist__abs_p99"] / max(float(np.median(absolute)), np.finfo(float).eps)
    )
    return result


def dynamic_features(signal: np.ndarray) -> dict[str, float]:
    """Small, sampling-rate-independent change features for later ablation."""
    differences = np.diff(signal)
    centered = signal - np.mean(signal)
    return {
        "dynamic__mean_abs_diff": float(np.mean(np.abs(differences))),
        "dynamic__std_diff": float(np.std(differences)),
        "dynamic__rms_diff": float(np.sqrt(np.mean(np.square(differences)))),
        "dynamic__max_abs_diff": float(np.max(np.abs(differences))),
        "dynamic__zero_crossing_rate": float(np.mean(signal[:-1] * signal[1:] < 0)),
        "dynamic__mean_crossing_rate": float(np.mean(centered[:-1] * centered[1:] < 0)),
    }


def peak_features(
    signal: np.ndarray,
    *,
    prominence_std: float = 0.5,
    distance: int = 5,
) -> dict[str, float]:
    """Configurable peak/trough summaries reserved for later ablation."""
    prominence = max(float(np.std(signal)) * prominence_std, np.finfo(float).eps)
    peaks, peak_props = find_peaks(signal, prominence=prominence, distance=distance)
    troughs, _ = find_peaks(-signal, prominence=prominence, distance=distance)
    amplitudes = signal[peaks]
    prominences = peak_props.get("prominences", np.asarray([], dtype=float))
    spacing = np.diff(peaks)

    def summary(values: np.ndarray, operation: str) -> float:
        if values.size == 0:
            return 0.0
        return float(getattr(np, operation)(values))

    return {
        "peaks__count": float(peaks.size),
        "peaks__trough_count": float(troughs.size),
        "peaks__density": float(peaks.size / signal.size),
        "peaks__mean_amplitude": summary(amplitudes, "mean"),
        "peaks__median_amplitude": summary(amplitudes, "median"),
        "peaks__max_amplitude": summary(amplitudes, "max"),
        "peaks__std_amplitude": summary(amplitudes, "std"),
        "peaks__mean_prominence": summary(prominences, "mean"),
        "peaks__max_prominence": summary(prominences, "max"),
        "peaks__mean_spacing": summary(spacing, "mean"),
        "peaks__median_spacing": summary(spacing, "median"),
    }


def extract_signal_features(
    signal: np.ndarray,
    groups: Sequence[str] = DEFAULT_GROUPS,
) -> dict[str, float]:
    """Extract independently switchable feature families from one signal."""
    unknown = set(groups) - set(SUPPORTED_GROUPS)
    if unknown:
        raise ValueError(f"Unsupported SHM feature groups: {sorted(unknown)}")
    extractors = {
        "statistics": statistics_features,
        "distribution": distribution_features,
        "peaks": peak_features,
        "dynamic": dynamic_features,
    }
    features: dict[str, float] = {}
    for group in groups:
        features.update(extractors[group](signal))
    values = np.asarray(list(features.values()), dtype=float)
    if not np.isfinite(values).all():
        raise ValueError("Feature extraction produced a NaN or infinite value.")
    return features


def extract_feature_table(
    paths: Iterable[str | Path],
    groups: Sequence[str] = DEFAULT_GROUPS,
) -> pd.DataFrame:
    """Convert recordings into a one-file-per-row feature table."""
    rows: list[dict[str, object]] = []
    for path in paths:
        source = Path(path)
        rows.append({"file_id": source.name, **extract_signal_features(load_signal(source), groups)})
    table = pd.DataFrame(rows)
    if table.empty:
        raise ValueError("Cannot extract features from an empty input collection.")
    if table["file_id"].duplicated().any():
        raise ValueError("Feature table contains duplicate file IDs.")
    return table


def extract_training_table(
    dataset_root: str | Path,
    groups: Sequence[str] = DEFAULT_GROUPS,
) -> pd.DataFrame:
    """Build a labelled feature table while holding only one signal in memory."""
    root = resolve_shm_root(dataset_root)
    rows: list[dict[str, object]] = []
    for filename, signal, damage in iter_training_signals(root):
        rows.append(
            {
                "file_id": filename,
                "target": damage,
                **extract_signal_features(signal, groups),
            }
        )
    return pd.DataFrame(rows)


def feature_columns_for_groups(table: pd.DataFrame, groups: Sequence[str]) -> list[str]:
    prefix_by_group = {
        "statistics": "stats__",
        "distribution": "dist__",
        "peaks": "peaks__",
        "dynamic": "dynamic__",
    }
    unknown = set(groups) - set(prefix_by_group)
    if unknown:
        raise ValueError(f"Unsupported SHM feature groups: {sorted(unknown)}")
    prefixes = tuple(prefix_by_group[group] for group in groups)
    return [column for column in table.columns if column.startswith(prefixes)]


def feature_quality_report(table: pd.DataFrame) -> dict[str, object]:
    """Identify non-finite, constant, duplicate, and highly correlated features."""
    feature_frame = table.drop(columns=["file_id", "target"], errors="ignore")
    values = feature_frame.to_numpy(dtype=float)
    constant = [column for column in feature_frame if feature_frame[column].nunique() <= 1]
    duplicate: list[list[str]] = []
    visited: set[str] = set()
    for column in feature_frame:
        if column in visited:
            continue
        matches = [
            other
            for other in feature_frame
            if other != column and feature_frame[column].equals(feature_frame[other])
        ]
        if matches:
            group = [column, *matches]
            duplicate.append(group)
            visited.update(group)
    correlations = feature_frame.corr().abs()
    high_pairs: list[dict[str, object]] = []
    columns = list(feature_frame.columns)
    for left_index, left in enumerate(columns):
        for right in columns[left_index + 1 :]:
            value = correlations.loc[left, right]
            if np.isfinite(value) and value >= 0.995:
                high_pairs.append({"left": left, "right": right, "abs_correlation": float(value)})
    return {
        "feature_count": int(feature_frame.shape[1]),
        "nonfinite_values": int((~np.isfinite(values)).sum()),
        "constant_features": constant,
        "duplicate_features": duplicate,
        "high_correlation_pairs_ge_0_995": high_pairs,
    }
