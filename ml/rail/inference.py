"""Rail Corrugation inference contract. Model implementation is pending."""

from pathlib import Path
from typing import Sequence


DEFAULT_ARTIFACT_DIR = Path(__file__).resolve().parent / "artifacts"


def predict_rail(
    input_paths: Sequence[str | Path],
    artifact_dir: str | Path | None = None,
) -> list[dict[str, object]]:
    """Return contract records using saved artifacts; never train during inference."""
    raise NotImplementedError(
        "Rail Corrugation inference is not implemented. Agent B: follow R1-R4 in plan.md."
    )
