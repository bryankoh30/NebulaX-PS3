"""SHM inference contract. Model implementation is pending."""

from pathlib import Path
from typing import Sequence


DEFAULT_ARTIFACT_DIR = Path(__file__).resolve().parent / "artifacts"


def predict_shm(
    input_paths: Sequence[str | Path],
    artifact_dir: str | Path | None = None,
) -> list[dict[str, object]]:
    """Return contract records using saved artifacts; never train during inference."""
    raise NotImplementedError(
        "SHM inference is not implemented. Agent C: follow S1-S4 in plan.md."
    )
