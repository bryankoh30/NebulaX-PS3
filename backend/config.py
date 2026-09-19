"""Runtime configuration for the backend."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    database_path: Path
    upload_dir: Path
    max_upload_bytes: int
    chart_point_limit: int
    cors_origins: tuple[str, ...]

    @classmethod
    def from_env(cls) -> "Settings":
        data_dir = Path(
            os.getenv("BACKEND_DATA_DIR", REPOSITORY_ROOT / "backend" / "runtime")
        ).expanduser().resolve()
        origins = tuple(
            item.strip()
            for item in os.getenv(
                "BACKEND_CORS_ORIGINS",
                "http://localhost:5173,http://127.0.0.1:5173",
            ).split(",")
            if item.strip()
        )
        return cls(
            data_dir=data_dir,
            database_path=data_dir / "nebulax.sqlite3",
            upload_dir=data_dir / "uploads",
            max_upload_bytes=int(os.getenv("BACKEND_MAX_UPLOAD_BYTES", str(250 * 1024 * 1024))),
            chart_point_limit=int(os.getenv("BACKEND_CHART_POINT_LIMIT", "500")),
            cors_origins=origins,
        )
