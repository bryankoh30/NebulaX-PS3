"""Public inference interface for ACV car localisation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Sequence

from .data import load_workbook
from .ranker import RankerConfig, rank_workbook


DEFAULT_ARTIFACT_DIR = Path(__file__).resolve().parent / "artifacts"


def load_config(artifact_dir: str | Path | None = None) -> RankerConfig:
    directory = Path(artifact_dir) if artifact_dir is not None else DEFAULT_ARTIFACT_DIR
    config_path = directory / "ranker_config.json"
    if not config_path.is_file():
        raise FileNotFoundError(
            f"ACV ranker configuration is missing: {config_path}. "
            "Regenerate it with `python -m ml.acv.train`."
        )
    with config_path.open("r", encoding="utf-8") as handle:
        values = json.load(handle)
    return RankerConfig.from_mapping(values)


def predict_acv(
    input_paths: Sequence[str | Path],
    artifact_dir: str | Path | None = None,
) -> list[dict[str, object]]:
    """Rank every car in each workbook using a frozen configuration."""
    paths = [Path(path) for path in input_paths]
    if not paths:
        raise ValueError("ACV inference requires at least one workbook")
    file_ids = [path.name for path in paths]
    if len(file_ids) != len(set(file_ids)):
        raise ValueError("ACV inference received duplicate output file IDs")

    config = load_config(artifact_dir)
    records: list[dict[str, object]] = []
    for path in paths:
        result = rank_workbook(load_workbook(path), config)
        records.append({"file_id": path.name, "ranked_cars": result.ranked_cars})
    return records
