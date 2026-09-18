"""Standalone Rail prediction and exact official CSV export."""

import argparse
from pathlib import Path

from .data import input_files
from .inference import predict_rail
from .serialize import write_predictions


def main() -> None:
    parser = argparse.ArgumentParser(description="Predict Rail Corrugation from saved artifacts.")
    parser.add_argument("--input", type=Path, required=True, help="one CSV recording or a directory of CSV recordings")
    parser.add_argument("--output", type=Path, required=True, help="Destination rail_predictions.csv")
    parser.add_argument("--artifacts", type=Path, help="Saved artifact directory; defaults to this package's artifacts/")
    args = parser.parse_args()
    try:
        paths = input_files(args.input)
        if args.output.resolve() in {p.resolve() for p in paths}:
            raise ValueError("Output cannot overwrite an input recording")
        records = predict_rail(paths, args.artifacts)
        write_predictions(records, args.output)
    except (ValueError, TypeError, OSError) as exc:
        parser.error(str(exc))
    print(f"Wrote {len(records)} predictions to {args.output}")


if __name__ == "__main__":
    main()
