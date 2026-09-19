"""Workbook loading and schema discovery for the ACV subsystem."""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
import re
from typing import Iterable

import pandas as pd


CAR_COLUMN = re.compile(r"^Car\s+(\d+)\s+-\s+(.+?)\s*$")


@dataclass(frozen=True)
class ACVWorkbook:
    path: Path
    frame: pd.DataFrame
    car_columns: OrderedDict[str, dict[str, str]]
    identifier_columns: tuple[str, ...]

    @property
    def car_ids(self) -> list[str]:
        return list(self.car_columns)

    def numeric(self, car_id: str, parameter: str) -> pd.Series | None:
        column = self.car_columns[car_id].get(parameter)
        if column is None:
            return None
        values = pd.to_numeric(self.frame[column], errors="coerce")
        values.name = car_id
        return values


def load_workbook(path: str | Path) -> ACVWorkbook:
    workbook_path = Path(path)
    if workbook_path.suffix.lower() != ".xlsx":
        raise ValueError(f"ACV input must be an .xlsx workbook: {workbook_path}")
    if not workbook_path.is_file():
        raise FileNotFoundError(f"ACV workbook does not exist: {workbook_path}")

    frame = pd.read_excel(workbook_path, sheet_name=0, engine="openpyxl")
    if frame.empty:
        raise ValueError(f"ACV workbook contains no telemetry rows: {workbook_path}")

    car_columns: OrderedDict[str, dict[str, str]] = OrderedDict()
    identifier_columns: list[str] = []
    for original in frame.columns:
        column = str(original).strip()
        match = CAR_COLUMN.match(column)
        if match is None:
            identifier_columns.append(str(original))
            continue
        car_id, parameter = match.groups()
        parameters = car_columns.setdefault(car_id, {})
        if parameter in parameters:
            raise ValueError(
                f"Duplicate ACV parameter for car {car_id}: {parameter!r} in {workbook_path}"
            )
        parameters[parameter] = str(original)

    if len(car_columns) < 2:
        raise ValueError(
            f"Expected telemetry for at least two cars in {workbook_path}; "
            f"found {len(car_columns)}"
        )

    return ACVWorkbook(
        path=workbook_path,
        frame=frame,
        car_columns=car_columns,
        identifier_columns=tuple(identifier_columns),
    )


def discover_inputs(path: str | Path) -> list[Path]:
    input_path = Path(path)
    if input_path.is_file():
        candidates = [input_path]
    elif input_path.is_dir():
        candidates = sorted(input_path.glob("*.xlsx"), key=lambda item: item.name.casefold())
    else:
        raise FileNotFoundError(f"ACV input path does not exist: {input_path}")

    if not candidates:
        raise ValueError(f"No .xlsx workbooks found in: {input_path}")
    unsupported = [item for item in candidates if item.suffix.lower() != ".xlsx"]
    if unsupported:
        raise ValueError(f"Unsupported ACV input: {unsupported[0]}")

    names = [item.name for item in candidates]
    if len(names) != len(set(names)):
        raise ValueError("ACV inputs contain duplicate output file IDs")
    return candidates


def resolve_acv_root(dataset_root: str | Path) -> Path:
    root = Path(dataset_root).expanduser().resolve()
    acv_root = root if root.name.casefold() == "acv" else root / "ACV"
    if not acv_root.is_dir():
        raise FileNotFoundError(f"ACV dataset directory does not exist: {acv_root}")
    return acv_root


def summarize_schema(workbooks: Iterable[ACVWorkbook]) -> list[dict[str, object]]:
    summaries: list[dict[str, object]] = []
    for workbook in workbooks:
        parameter_counts = {
            car_id: len(parameters) for car_id, parameters in workbook.car_columns.items()
        }
        summaries.append(
            {
                "file_id": workbook.path.name,
                "rows": int(len(workbook.frame)),
                "car_ids": workbook.car_ids,
                "parameters_per_car": parameter_counts,
            }
        )
    return summaries
