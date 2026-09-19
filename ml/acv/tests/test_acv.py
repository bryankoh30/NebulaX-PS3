from __future__ import annotations

import csv
import json
from pathlib import Path

import pandas as pd
import pytest

from ml.acv.data import discover_inputs, load_workbook
from ml.acv.inference import predict_acv
from ml.acv.ranker import RankerConfig, rank_decay_score, rank_workbook
from ml.acv.serialize import write_predictions


def _write_workbook(
    path: Path,
    indoor: dict[str, list[float | None]],
    targets: dict[str, list[float | None]] | None = None,
    extra: dict[tuple[str, str], list[float | None]] | None = None,
) -> Path:
    row_count = len(next(iter(indoor.values())))
    columns: dict[str, object] = {
        "Car model": ["M"] * row_count,
        "Train number": ["T"] * row_count,
        "Time": pd.date_range("2026-01-01", periods=row_count, freq="30s"),
    }
    for car_id, values in indoor.items():
        columns[f"Car {car_id} - Indoor Average Temperature"] = values
        if targets is not None:
            columns[f"Car {car_id} - ACV Control Temperature (Cooling)"] = targets[car_id]
    for (car_id, parameter), values in (extra or {}).items():
        columns[f"Car {car_id} - {parameter}"] = values
    pd.DataFrame(columns).to_excel(path, index=False)
    return path


def _write_config(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    (path / "ranker_config.json").write_text(
        json.dumps(RankerConfig().to_dict()), encoding="utf-8"
    )
    return path


def test_loader_preserves_header_car_order_and_leading_zeroes(tmp_path: Path) -> None:
    workbook_path = _write_workbook(
        tmp_path / "case.xlsx",
        {"08": [24, 24], "01": [25, 25], "03": [23, 23]},
    )
    workbook = load_workbook(workbook_path)
    assert workbook.car_ids == ["08", "01", "03"]
    assert workbook.numeric("01", "Indoor Average Temperature").tolist() == [25, 25]


def test_thermal_peer_score_ranks_persistently_hot_car_first(tmp_path: Path) -> None:
    workbook = load_workbook(
        _write_workbook(
            tmp_path / "thermal.xlsx",
            {
                "01": [24, 24, 24, 24, 24],
                "02": [28, 28, 28, 28, 28],
                "03": [23, 24, 24, 23, 24],
            },
            targets={car: [22] * 5 for car in ("01", "02", "03")},
        )
    )
    result = rank_workbook(workbook, RankerConfig())
    assert result.ranked_cars[0] == "02"
    assert sorted(result.ranked_cars) == ["01", "02", "03"]


def test_rich_schema_pressure_imbalance_can_localise_fault(tmp_path: Path) -> None:
    cars = {car: [25, 25, 25, 25] for car in ("01", "02", "03")}
    extra: dict[tuple[str, str], list[float]] = {}
    for car in cars:
        extra[(car, "Refrigeration System 1 High Pressure Value")] = [2000] * 4
        extra[(car, "Refrigeration System 2 High Pressure Value")] = (
            [1200] * 4 if car == "01" else [1980] * 4
        )
        extra[(car, "Compressor 1 Running")] = [1, 1, 1, 1]
        extra[(car, "Compressor 2 Running")] = [0, 0, 0, 0] if car == "01" else [1, 1, 1, 1]
    workbook = load_workbook(_write_workbook(tmp_path / "rich.xlsx", cars, extra=extra))
    result = rank_workbook(workbook, RankerConfig())
    assert result.ranked_cars[0] == "01"


def test_unavailable_cars_are_retained_after_scored_cars(tmp_path: Path) -> None:
    workbook = load_workbook(
        _write_workbook(
            tmp_path / "missing.xlsx",
            {"01": [25, 26, 26], "02": [24, 24, 24], "03": [None, None, None]},
        )
    )
    result = rank_workbook(workbook, RankerConfig())
    assert result.ranked_cars[-1] == "03"
    assert set(result.ranked_cars) == {"01", "02", "03"}


def test_no_usable_cross_car_telemetry_fails_explicitly(tmp_path: Path) -> None:
    workbook = load_workbook(
        _write_workbook(
            tmp_path / "empty.xlsx",
            {"01": [None, None], "02": [None, None]},
        )
    )
    with pytest.raises(ValueError, match="No usable cross-car"):
        rank_workbook(workbook, RankerConfig())


def test_inference_preserves_filename_and_returns_string_ids(tmp_path: Path) -> None:
    workbook_path = _write_workbook(
        tmp_path / "case.xlsx", {"01": [24, 24], "02": [27, 27]}
    )
    records = predict_acv([workbook_path], _write_config(tmp_path / "artifacts"))
    assert records == [{"file_id": "case.xlsx", "ranked_cars": ["02", "01"]}]


def test_inference_rejects_duplicate_output_ids(tmp_path: Path) -> None:
    first_dir = tmp_path / "first"
    second_dir = tmp_path / "second"
    first_dir.mkdir()
    second_dir.mkdir()
    first = _write_workbook(first_dir / "same.xlsx", {"01": [24], "02": [25]})
    second = _write_workbook(second_dir / "same.xlsx", {"01": [24], "02": [25]})
    with pytest.raises(ValueError, match="duplicate output"):
        predict_acv([first, second], _write_config(tmp_path / "artifacts"))


def test_csv_serializer_uses_exact_schema_and_pipe_delimiter(tmp_path: Path) -> None:
    output = tmp_path / "acv_predictions.csv"
    write_predictions(
        [{"file_id": "case.xlsx", "ranked_cars": ["03", "01", "08"]}], output
    )
    with output.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames == ["file_id", "ranked_cars"]
        assert list(reader) == [{"file_id": "case.xlsx", "ranked_cars": "03|01|08"}]


def test_discovery_sorts_workbooks_and_rejects_empty_directory(tmp_path: Path) -> None:
    _write_workbook(tmp_path / "b.xlsx", {"01": [24], "02": [25]})
    _write_workbook(tmp_path / "a.xlsx", {"01": [24], "02": [25]})
    assert [item.name for item in discover_inputs(tmp_path)] == ["a.xlsx", "b.xlsx"]
    empty = tmp_path / "empty"
    empty.mkdir()
    with pytest.raises(ValueError, match="No .xlsx"):
        discover_inputs(empty)


def test_rank_decay_metric() -> None:
    ranking = ["03", "01", "05", "02"]
    assert rank_decay_score(ranking, "03") == 1.0
    assert rank_decay_score(ranking, "01") == 0.75
    assert rank_decay_score(ranking, "99") == 0.0
