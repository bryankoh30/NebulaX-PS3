"""Standalone ACV inference and official CSV export."""

import argparse
from pathlib import Path

from .data import discover_inputs
from .inference import predict_acv
from .serialize import write_predictions


def main() -> None:
    parser = argparse.ArgumentParser(description="Rank likely leaking ACV cars.")
    parser.add_argument("--input", type=Path, required=True, help="one XLSX workbook or a directory of XLSX workbooks")
    parser.add_argument("--output", type=Path, required=True, help="Destination acv_predictions.csv")
    parser.add_argument("--artifacts", type=Path, help="Saved artifact directory; defaults to this package's artifacts/")
    args = parser.parse_args()
    inputs = discover_inputs(args.input)
    records = predict_acv(inputs, artifact_dir=args.artifacts)
    output = write_predictions(records, args.output)
    print(f"Wrote {len(records)} ACV prediction row(s) to {output}")


if __name__ == "__main__":
    main()
