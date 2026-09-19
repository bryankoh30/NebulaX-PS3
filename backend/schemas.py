"""HTTP request models and shared API constants."""

from typing import Literal

from pydantic import BaseModel, Field


Subsystem = Literal["door", "acv", "rail", "shm"]
ReviewStatus = Literal["unreviewed", "confirmed", "dismissed", "resolved"]
RunStatus = Literal["queued", "running", "completed", "failed"]


class ReviewUpdate(BaseModel):
    status: ReviewStatus
    note: str = Field(default="", max_length=2000)


class ExportRequest(BaseModel):
    run_ids: list[str] = Field(min_length=1, max_length=4)
