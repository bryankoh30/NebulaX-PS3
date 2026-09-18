"""Evaluation scaffold for SHM."""

import argparse
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate SHM (implementation pending).")
    parser.add_argument("--dataset-root", type=Path, help="Dataset root; implementation should otherwise use ml.config.get_dataset_root()")
    parser.add_argument("--artifacts", type=Path, help="Artifact directory")
    parser.parse_args()
    parser.error("SHM evaluate is not implemented. Agent C: follow S1-S4 in plan.md.")


if __name__ == "__main__":
    main()
