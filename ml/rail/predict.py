"""Command-line scaffold for Rail Corrugation prediction."""

import argparse
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Predict Rail Corrugation results (implementation pending).")
    parser.add_argument("--input", type=Path, required=True, help="one CSV recording or a directory of CSV recordings")
    parser.add_argument("--output", type=Path, required=True, help="Destination rail_predictions.csv")
    parser.add_argument("--artifacts", type=Path, help="Saved artifact directory; defaults to this package's artifacts/")
    parser.parse_args()
    parser.error(
        "Rail Corrugation prediction/export is not implemented. "
        "Agent B: follow R1-R4 in plan.md. No output was written."
    )


if __name__ == "__main__":
    main()
