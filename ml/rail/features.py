"""Stateless statistics with channel identity and side contrasts preserved."""
import hashlib
import json
from pathlib import Path

import numpy as np

from .data import CHANNELS, SAMPLE_RATE, digest, load_recording, training_labels

PACKAGE = Path(__file__).resolve().parent
CACHE = PACKAGE / "cache"

FEATURE_VERSION = "rail-statistics-v1"
STATISTICS = ["rms", "std", "peak_to_peak", "kurtosis"]


def extract_features(values):
    signals = values[:, 1:]
    centered = signals - signals.mean(axis=0)
    variance = np.mean(centered ** 2, axis=0)
    fourth = np.mean(centered ** 4, axis=0)
    # Pearson kurtosis; constant signals receive zero by explicit convention.
    kurtosis = np.divide(fourth, variance ** 2, out=np.zeros_like(fourth), where=variance > 0)
    statistics = np.array([np.sqrt(np.mean(signals ** 2, axis=0)), np.sqrt(variance),
                           np.ptp(signals, axis=0), kurtosis])
    result = {}
    for statistic, channel_values in zip(STATISTICS, statistics):
        for channel, value in zip(CHANNELS, channel_values):
            result[f"car{channel['car']}_pos{channel['position']}_{channel['kind']}_{statistic}"] = float(value)
        for kind in ["vibration", "shock"]:
            sides = []
            for side in ["Side I", "Side II"]:
                mask = [c["side"] == side and c["kind"] == kind for c in CHANNELS]
                subset = channel_values[mask]
                summary = {"mean": np.mean(subset), "median": np.median(subset), "max": np.max(subset)}
                sides.append(summary)
                for name, value in summary.items():
                    result[f"{side}_{kind}_{statistic}_{name}"] = float(value)
            for name in sides[0]:
                left, right = sides[0][name], sides[1][name]
                result[f"contrast_{kind}_{statistic}_{name}"] = float(left - right)
                result[f"relative_contrast_{kind}_{statistic}_{name}"] = float((left - right) / (abs(left) + abs(right) + 1e-12))
    result["pulse_transitions_per_second"] = float(np.count_nonzero(np.diff(values[:, 0])) * SAMPLE_RATE / (len(values) - 1))
    vector = np.array(list(result.values()), dtype=np.float64)
    if not np.isfinite(vector).all():
        raise ValueError("Nonfinite statistical features")
    return vector, list(result)


def training_features(dataset_root=None):
    root, labels = training_labels(dataset_root)
    split_path = PACKAGE / "validation_split.json"
    if not split_path.is_file():
        raise FileNotFoundError("Run python -m ml.rail.inspect before training")
    split = json.loads(split_path.read_text(encoding="utf-8"))
    records = split["recordings"]
    if [(r["file_id"], r["label"]) for r in records] != list(labels.itertuples(index=False, name=None)):
        raise ValueError("Labels differ from frozen R1 split; rerun inspection")
    CACHE.mkdir(parents=True, exist_ok=True)
    implementation = digest(PACKAGE / "features.py") + digest(PACKAGE / "data.py")
    vectors, names = [], None
    for index, record in enumerate(records):
        path = root / "Train" / record["file_id"]
        checksum = digest(path)
        if checksum != record["sha256"]:
            raise ValueError(f"{path.name} changed since R1 inspection")
        key = hashlib.sha256((FEATURE_VERSION + implementation + checksum).encode()).hexdigest()
        cache_path = CACHE / f"{key}.npz"
        if cache_path.exists():
            with np.load(cache_path, allow_pickle=False) as cached:
                vector, current_names = cached["values"], cached["names"].tolist()
        else:
            vector, current_names = extract_features(load_recording(path))
            np.savez_compressed(cache_path, values=vector, names=np.array(current_names))
        if names is not None and current_names != names:
            raise ValueError("Feature cache schema mismatch; remove the local cache and regenerate")
        if vector.shape != (len(current_names),) or not np.isfinite(vector).all():
            raise ValueError(f"Invalid feature cache: {cache_path}")
        names = current_names
        vectors.append(vector)
        if (index + 1) % 25 == 0:
            print(f"Features {index + 1}/272", flush=True)
    return np.array(vectors), labels.label.to_numpy(), np.array([r["fold"] for r in records]), names, split
