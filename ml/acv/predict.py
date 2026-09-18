"""Command-line scaffold for ACV prediction."""

import argparse
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Predict ACV results (implementation pending).")
    parser.add_argument("--input", type=Path, required=True, help="one XLSX workbook or a directory of XLSX workbooks")
    parser.add_argument("--output", type=Path, required=True, help="Destination acv_predictions.csv")
    parser.add_argument("--artifacts", type=Path, help="Saved artifact directory; defaults to this package's artifacts/")
    parser.parse_args()
    parser.error(
        "ACV prediction/export is not implemented. "
        "Agent C: follow V1-V4 in plan.md. No output was written."
    )


if __name__ == "__main__":
    main()
