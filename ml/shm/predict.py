"""Command-line SHM prediction and exact CSV export."""

import argparse
from pathlib import Path

from ml.shm.data import discover_csv_files
from ml.shm.inference import predict_shm
from ml.shm.serialize import write_predictions


def main() -> None:
    parser = argparse.ArgumentParser(description="Predict SHM cumulative fatigue damage.")
    parser.add_argument("--input", type=Path, required=True, help="one headerless CSV recording or a directory of CSV recordings")
    parser.add_argument("--output", type=Path, required=True, help="Destination shm_predictions.csv")
    parser.add_argument("--artifacts", type=Path, help="Saved artifact directory; defaults to this package's artifacts/")
    args = parser.parse_args()
    paths = discover_csv_files(args.input)
    records = predict_shm(paths, args.artifacts)
    write_predictions(records, args.output)
    print(f"Wrote {len(records)} SHM predictions to {args.output}")


if __name__ == "__main__":
    main()
