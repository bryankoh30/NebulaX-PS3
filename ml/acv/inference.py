"""ACV inference contract. Model implementation is pending."""

from pathlib import Path
from typing import Sequence


DEFAULT_ARTIFACT_DIR = Path(__file__).resolve().parent / "artifacts"


def predict_acv(
    input_paths: Sequence[str | Path],
    artifact_dir: str | Path | None = None,
) -> list[dict[str, object]]:
    """Return contract records using saved artifacts; never train during inference."""
    raise NotImplementedError(
        "ACV inference is not implemented. Agent C: follow V1-V4 in plan.md."
    )
