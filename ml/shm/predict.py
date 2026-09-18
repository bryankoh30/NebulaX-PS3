"""Command-line scaffold for SHM prediction."""

import argparse
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Predict SHM results (implementation pending).")
    parser.add_argument("--input", type=Path, required=True, help="one headerless CSV recording or a directory of CSV recordings")
    parser.add_argument("--output", type=Path, required=True, help="Destination shm_predictions.csv")
    parser.add_argument("--artifacts", type=Path, help="Saved artifact directory; defaults to this package's artifacts/")
    parser.parse_args()
    parser.error(
        "SHM prediction/export is not implemented. "
        "Agent C: follow S1-S4 in plan.md. No output was written."
    )


if __name__ == "__main__":
    main()
