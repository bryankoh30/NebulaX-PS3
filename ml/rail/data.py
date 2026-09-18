"""Strict header-based Rail loading, independent of training labels."""
import csv
import hashlib
from pathlib import Path

import numpy as np
import pandas as pd

CLASSES = ["Normal", "Side I", "Side II"]
SAMPLE_RATE = 10_000
CHANNELS = [
    {"header": f"{kind} of bearing in position {position} of car {car}",
     "car": car, "position": position, "kind": kind.lower(),
     "side": "Side I" if position % 2 else "Side II"}
    for car in range(1, 9) for position in range(1, 9)
    for kind in ("Vibration", "Shock")
]
HEADERS = ["Rotating speed"] + [c["header"] for c in CHANNELS]


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def load_recording(path):
    path = Path(path)
    with path.open(encoding="utf-8-sig", newline="") as stream:
        headers = next(csv.reader(stream), [])
    if len(headers) != len(HEADERS) or set(headers) != set(HEADERS):
        raise ValueError(f"{path.name}: expected speed pulse and 128 unique named channels")
    try:
        frame = pd.read_csv(path, dtype=np.float64).loc[:, HEADERS]
    except (ValueError, pd.errors.ParserError) as exc:
        raise ValueError(f"{path.name}: invalid numeric CSV: {exc}") from exc
    values = frame.to_numpy()
    if values.shape != (SAMPLE_RATE, 129) or not np.isfinite(values).all():
        raise ValueError(f"{path.name}: expected 10000 finite rows and 129 columns; got {values.shape}")
    if not np.isin(values[:, 0], [0, 1]).all():
        raise ValueError(f"{path.name}: speed pulse must contain only 0 and 1")
    return values


def input_files(input_path):
    path = Path(input_path)
    if path.is_dir():
        paths = sorted((p for p in path.iterdir() if p.is_file() and p.suffix.lower() == ".csv"), key=lambda p: p.name)
    else:
        paths = [path]
    return validate_paths(paths)


def validate_paths(paths):
    if isinstance(paths, (str, Path)):
        raise TypeError("input_paths must be a sequence of file paths")
    paths = [Path(p) for p in paths]
    if not paths:
        raise ValueError("No CSV recordings supplied")
    if len({p.name for p in paths}) != len(paths):
        raise ValueError("Duplicate output file_id")
    for path in paths:
        if not path.is_file():
            raise FileNotFoundError(path)
        if path.suffix.lower() != ".csv":
            raise ValueError(f"Unsupported recording: {path}")
    return paths


def training_labels(dataset_root=None):
    from ml.config import get_dataset_root

    root = (Path(dataset_root) if dataset_root else get_dataset_root()) / "Rail_Corrugation"
    if not (root / "Train_Labels.csv").is_file():
        raise FileNotFoundError(root / "Train_Labels.csv")
    for name in ["Train", "Test"]:
        if not (root / name).is_dir():
            raise FileNotFoundError(root / name)
    labels = pd.read_csv(root / "Train_Labels.csv", dtype=str)
    if list(labels.columns) != ["filename", "label"]:
        raise ValueError("Expected filename,label in Train_Labels.csv")
    if labels.filename.duplicated().any() or labels.label.value_counts().to_dict() != {"Normal": 234, "Side I": 14, "Side II": 24}:
        raise ValueError("Expected 272 unique labels: 234 Normal, 14 Side I, 24 Side II")
    if labels.isna().any().any() or any(Path(name).name != name for name in labels.filename):
        raise ValueError("Label filenames must be nonempty basenames")
    labels = labels.sort_values("filename").reset_index(drop=True)
    files = input_files(root / "Train")
    if {p.name for p in files} != set(labels.filename):
        raise ValueError("Training files and label filenames differ")
    return root, labels
