"""Door inference contract. Model implementation is pending."""

from pathlib import Path


DEFAULT_ARTIFACT_DIR = Path(__file__).resolve().parent / "artifacts"


def predict_door(
    input_path: str | Path,
    artifact_dir: str | Path | None = None,
) -> list[dict[str, object]]:
    """Return contract records using saved artifacts; never train during inference."""
    raise NotImplementedError(
        "Door inference is not implemented. Agent A: follow D1-D4 in plan.md."
    )
