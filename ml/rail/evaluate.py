"""Evaluation scaffold for Rail Corrugation."""

import argparse
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate Rail Corrugation (implementation pending).")
    parser.add_argument("--dataset-root", type=Path, help="Dataset root; implementation should otherwise use ml.config.get_dataset_root()")
    parser.add_argument("--artifacts", type=Path, help="Artifact directory")
    parser.parse_args()
    parser.error("Rail Corrugation evaluate is not implemented. Agent B: follow R1-R4 in plan.md.")


if __name__ == "__main__":
    main()
