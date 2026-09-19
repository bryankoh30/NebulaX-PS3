"""Bounded presentation-series extraction from subsystem recordings."""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

import numpy as np

from ml.acv.data import load_workbook
from ml.acv.ranker import INDOOR_PARAMETERS
from ml.door.loader import format_timestamp, load_stream
from ml.rail.data import CHANNELS, load_recording
from ml.shm.data import load_signal


def _indices(length: int, limit: int) -> np.ndarray:
    if length <= limit:
        return np.arange(length, dtype=int)
    return np.unique(np.linspace(0, length - 1, limit, dtype=int))


def _points(values: np.ndarray, limit: int, x_values: Sequence[object] | None = None) -> list[dict[str, object]]:
    selected = _indices(len(values), limit)
    return [
        {
            "x": int(index) if x_values is None else x_values[int(index)],
            "y": float(values[int(index)]),
        }
        for index in selected
        if np.isfinite(values[int(index)])
    ]


def build_chart_series(
    subsystem: str, paths: Sequence[Path], point_limit: int
) -> list[dict[str, object]]:
    builders = {
        "door": _door_series,
        "acv": _acv_series,
        "rail": _rail_series,
        "shm": _shm_series,
    }
    return builders[subsystem](paths, point_limit)


def _door_series(paths: Sequence[Path], limit: int) -> list[dict[str, object]]:
    frame = load_stream(paths[0])
    timestamps = [format_timestamp(value) for value in frame["ts"]]
    definitions = (
        ("Motor current(mA)", "motor-current", "Motor current", "mA"),
        ("Door leaf position", "door-position", "Door leaf position", ""),
    )
    return [
        {
            "file_id": paths[0].name,
            "series_id": series_id,
            "label": label,
            "unit": unit,
            "x_kind": "timestamp",
            "points": _points(frame[column].to_numpy(dtype=float), limit, timestamps),
        }
        for column, series_id, label, unit in definitions
        if column in frame
    ]


def _acv_series(paths: Sequence[Path], limit: int) -> list[dict[str, object]]:
    output: list[dict[str, object]] = []
    for path in paths:
        workbook = load_workbook(path)
        for car_id in workbook.car_ids:
            parameter = next(
                (name for name in INDOOR_PARAMETERS if name in workbook.car_columns[car_id]),
                None,
            )
            if parameter is None:
                continue
            values = workbook.numeric(car_id, parameter).to_numpy(dtype=float)
            output.append(
                {
                    "file_id": path.name,
                    "series_id": f"car-{car_id}-temperature",
                    "label": f"Car {car_id} cabin temperature",
                    "unit": "",
                    "x_kind": "sample_index",
                    "car_id": car_id,
                    "points": _points(values, limit),
                }
            )
    return output


def _rail_series(paths: Sequence[Path], limit: int) -> list[dict[str, object]]:
    output: list[dict[str, object]] = []
    for path in paths:
        values = load_recording(path)
        for side in ("Side I", "Side II"):
            columns = [
                index + 1
                for index, channel in enumerate(CHANNELS)
                if channel["kind"] == "vibration" and channel["side"] == side
            ]
            aggregate = np.sqrt(np.mean(np.square(values[:, columns]), axis=1))
            output.append(
                {
                    "file_id": path.name,
                    "series_id": f"{path.stem}-{side.lower().replace(' ', '-')}-vibration",
                    "label": f"{side} aggregated vibration",
                    "unit": "m/s²",
                    "x_kind": "sample_index",
                    "side": side,
                    "points": _points(aggregate, limit),
                }
            )
    return output


def _shm_series(paths: Sequence[Path], limit: int) -> list[dict[str, object]]:
    return [
        {
            "file_id": path.name,
            "series_id": f"{path.stem}-stress",
            "label": "Stress",
            "unit": "",
            "x_kind": "sample_index",
            "points": _points(load_signal(path), limit),
        }
        for path in paths
    ]
