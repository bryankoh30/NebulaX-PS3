"""Shared dataset location; model inference must use explicit input paths."""

import os
from pathlib import Path


def get_dataset_root() -> Path:
    """Load the repository-local .env without overriding an existing environment."""
    from dotenv import load_dotenv

    repository_root = Path(__file__).resolve().parents[1]
    load_dotenv(repository_root / ".env", override=False)
    value = os.environ.get("DATASET_ROOT", "").strip()
    if not value:
        raise ValueError("Set DATASET_ROOT in your environment or repository-local .env.")
    dataset_root = Path(value).expanduser()
    if not dataset_root.is_absolute():
        dataset_root = repository_root / dataset_root
    dataset_root = dataset_root.resolve()
    if not dataset_root.is_dir():
        raise FileNotFoundError(f"Dataset directory does not exist: {dataset_root}")
    return dataset_root
