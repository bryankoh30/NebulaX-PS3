"""Chart contract regression checks using synthetic input only."""
import numpy as np
import pandas as pd

from backend.charts import build_chart_series
from ml.rail.data import CHANNELS


def test_door_chart_timestamps_are_iso_and_keep_milliseconds(tmp_path):
    path = tmp_path / "synthetic.csv"
    pd.DataFrame({"Datetime": ["2023-7-5-0-0-9-20", "2023-7-5-0-0-10-120", "2023-7-5-0-0-12-0"],
                  "Motor current(mA)": [1, 2, 3], "Door leaf position": [0, 1, 2]}).to_csv(path, index=False)
    charts = build_chart_series("door", [path], 10)
    assert len(charts) == 2
    assert [point["x"] for point in charts[0]["points"]] == [
        "2023-07-05T00:00:09.020", "2023-07-05T00:00:10.120", "2023-07-05T00:00:12.000"]
    assert charts[0]["unit"] == "mA"
    assert charts[1]["unit"] == ""  # Reference does not specify a position unit.


def test_rail_chart_uses_documented_units_and_correct_side_channels(monkeypatch, tmp_path):
    values = np.zeros((4, 129))
    for index, channel in enumerate(CHANNELS, 1):
        values[:, index] = (3 if channel["side"] == "Side I" else 4) if channel["kind"] == "vibration" else 100
    monkeypatch.setattr("backend.charts.load_recording", lambda _: values)
    charts = build_chart_series("rail", [tmp_path / "synthetic.csv"], 2)
    assert [chart["unit"] for chart in charts] == ["m/s²", "m/s²"]
    assert [chart["points"][0]["y"] for chart in charts] == [3, 4]
    assert all(len(chart["points"]) == 2 for chart in charts)
