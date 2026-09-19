"""Transparent, schema-aware ACV refrigerant-leak ranking."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from typing import Mapping

import numpy as np
import pandas as pd

from .data import ACVWorkbook


INDOOR_PARAMETERS = (
    "Indoor Average Temperature",
    "Passenger Cabin Temperature Detected Value",
    "Observation Area Temperature Detected Value",
)
COOLING_TARGET_PARAMETERS = (
    "ACV Control Temperature (Cooling)",
    "Target Temperature Value",
)
HIGH_PRESSURE_1 = "Refrigeration System 1 High Pressure Value"
HIGH_PRESSURE_2 = "Refrigeration System 2 High Pressure Value"
COMPRESSOR_1 = "Compressor 1 Running"
COMPRESSOR_2 = "Compressor 2 Running"


@dataclass(frozen=True)
class RankerConfig:
    schema_version: int = 1
    minimum_valid_fraction: float = 0.02
    thermal_median_weight: float = 0.30
    thermal_q90_weight: float = 0.25
    above_peer_weight: float = 0.25
    cooling_gap_q90_weight: float = 0.20
    high_pressure_imbalance_weight: float = 0.80
    compressor_duty_imbalance_weight: float = 0.20

    @classmethod
    def from_mapping(cls, values: Mapping[str, object]) -> "RankerConfig":
        known = {field: values[field] for field in asdict(cls()) if field in values}
        return cls(**known)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class RankingResult:
    ranked_cars: list[str]
    scores: dict[str, float | None]
    components: dict[str, dict[str, float | None]]
    parameters_used: dict[str, str | None]


def _shared_parameter(workbook: ACVWorkbook, candidates: tuple[str, ...]) -> str | None:
    for candidate in candidates:
        available = sum(
            candidate in parameters for parameters in workbook.car_columns.values()
        )
        if available >= 2:
            return candidate
    return None


def _valid_numeric(series: pd.Series | None) -> pd.Series | None:
    if series is None:
        return None
    numeric = pd.to_numeric(series, errors="coerce").replace([np.inf, -np.inf], np.nan)
    return numeric if numeric.notna().any() else None


def _percentile_components(values: Mapping[str, float | None]) -> dict[str, float | None]:
    present = [(car_id, value) for car_id, value in values.items() if value is not None and math.isfinite(value)]
    output = {car_id: None for car_id in values}
    if not present:
        return output
    if len(present) == 1:
        output[present[0][0]] = 1.0
        return output

    numeric = pd.Series({car_id: value for car_id, value in present}, dtype=float)
    ranks = numeric.rank(method="average", ascending=True)
    scaled = (ranks - 1.0) / (len(numeric) - 1.0)
    for car_id, value in scaled.items():
        output[str(car_id)] = float(value)
    return output


def _thermal_metrics(
    workbook: ACVWorkbook,
    indoor_parameter: str | None,
    target_parameter: str | None,
    minimum_valid_fraction: float,
) -> dict[str, dict[str, float | None]]:
    metrics = {
        name: {car_id: None for car_id in workbook.car_ids}
        for name in ("thermal_median", "thermal_q90", "above_peer", "cooling_gap_q90")
    }
    if indoor_parameter is None:
        return metrics

    indoor_series: dict[str, pd.Series] = {}
    for car_id in workbook.car_ids:
        series = _valid_numeric(workbook.numeric(car_id, indoor_parameter))
        if series is not None and float(series.notna().mean()) >= minimum_valid_fraction:
            indoor_series[car_id] = series
    if len(indoor_series) < 2:
        return metrics

    indoor = pd.DataFrame(indoor_series)
    peer_median = indoor.median(axis=1, skipna=True)
    for car_id, series in indoor_series.items():
        deviation = (series - peer_median).dropna()
        if deviation.empty:
            continue
        metrics["thermal_median"][car_id] = float(deviation.median())
        metrics["thermal_q90"][car_id] = float(deviation.quantile(0.90))
        metrics["above_peer"][car_id] = float((deviation > 0).mean())

        if target_parameter is not None:
            target = _valid_numeric(workbook.numeric(car_id, target_parameter))
            if target is not None:
                gap = (series - target).dropna()
                if not gap.empty:
                    metrics["cooling_gap_q90"][car_id] = float(gap.quantile(0.90))
    return metrics


def _circuit_metrics(
    workbook: ACVWorkbook,
    minimum_valid_fraction: float,
) -> dict[str, dict[str, float | None]]:
    metrics = {
        "high_pressure_imbalance": {car_id: None for car_id in workbook.car_ids},
        "compressor_duty_imbalance": {car_id: None for car_id in workbook.car_ids},
    }
    for car_id in workbook.car_ids:
        high_1 = _valid_numeric(workbook.numeric(car_id, HIGH_PRESSURE_1))
        high_2 = _valid_numeric(workbook.numeric(car_id, HIGH_PRESSURE_2))
        if high_1 is not None and high_2 is not None:
            paired = pd.concat([high_1, high_2], axis=1).dropna()
            if len(paired) >= max(2, int(len(workbook.frame) * minimum_valid_fraction)):
                numerator = (paired.iloc[:, 0] - paired.iloc[:, 1]).abs()
                denominator = paired.abs().mean(axis=1).replace(0, np.nan)
                relative = (numerator / denominator).replace([np.inf, -np.inf], np.nan).dropna()
                if not relative.empty:
                    metrics["high_pressure_imbalance"][car_id] = float(relative.median())

        compressor_1 = _valid_numeric(workbook.numeric(car_id, COMPRESSOR_1))
        compressor_2 = _valid_numeric(workbook.numeric(car_id, COMPRESSOR_2))
        if compressor_1 is not None and compressor_2 is not None:
            metrics["compressor_duty_imbalance"][car_id] = float(
                abs(compressor_1.mean() - compressor_2.mean())
            )
    return metrics


def rank_workbook(
    workbook: ACVWorkbook,
    config: RankerConfig,
) -> RankingResult:
    indoor_parameter = _shared_parameter(workbook, INDOOR_PARAMETERS)
    target_parameter = _shared_parameter(workbook, COOLING_TARGET_PARAMETERS)
    raw_components = _thermal_metrics(
        workbook,
        indoor_parameter,
        target_parameter,
        config.minimum_valid_fraction,
    )
    raw_components.update(_circuit_metrics(workbook, config.minimum_valid_fraction))

    normalized = {
        component: _percentile_components(values)
        for component, values in raw_components.items()
    }
    weights = {
        "thermal_median": config.thermal_median_weight,
        "thermal_q90": config.thermal_q90_weight,
        "above_peer": config.above_peer_weight,
        "cooling_gap_q90": config.cooling_gap_q90_weight,
        "high_pressure_imbalance": config.high_pressure_imbalance_weight,
        "compressor_duty_imbalance": config.compressor_duty_imbalance_weight,
    }

    scores: dict[str, float | None] = {}
    for car_id in workbook.car_ids:
        available = [
            (normalized[name][car_id], weight)
            for name, weight in weights.items()
            if normalized[name][car_id] is not None and weight > 0
        ]
        if not available:
            scores[car_id] = None
            continue
        weighted_sum = sum(float(value) * weight for value, weight in available)
        scores[car_id] = weighted_sum / sum(weight for _, weight in available)

    if not any(value is not None for value in scores.values()):
        raise ValueError(
            f"No usable cross-car ACV telemetry found in workbook: {workbook.path}"
        )

    header_order = {car_id: index for index, car_id in enumerate(workbook.car_ids)}
    ranked_cars = sorted(
        workbook.car_ids,
        key=lambda car_id: (
            scores[car_id] is not None,
            scores[car_id] if scores[car_id] is not None else float("-inf"),
            -header_order[car_id],
        ),
        reverse=True,
    )
    return RankingResult(
        ranked_cars=ranked_cars,
        scores=scores,
        components=normalized,
        parameters_used={"indoor": indoor_parameter, "cooling_target": target_parameter},
    )


def rank_decay_score(ranked_cars: list[str], true_car: str) -> float:
    if true_car not in ranked_cars or not ranked_cars:
        return 0.0
    rank = ranked_cars.index(true_car) + 1
    return float((len(ranked_cars) - (rank - 1)) / len(ranked_cars))
