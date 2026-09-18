"""Command-line scaffold for Door prediction."""

import argparse
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Predict Door results (implementation pending).")
    parser.add_argument("--input", type=Path, required=True, help="one continuous CSV recording")
    parser.add_argument("--output", type=Path, required=True, help="Destination door_predictions.csv")
    parser.add_argument("--artifacts", type=Path, help="Saved artifact directory; defaults to this package's artifacts/")
    parser.parse_args()
    parser.error(
        "Door prediction/export is not implemented. "
        "Agent A: follow D1-D4 in plan.md. No output was written."
    )


if __name__ == "__main__":
    main()
