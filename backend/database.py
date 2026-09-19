"""Small SQLite persistence layer for runs, results, and reviews."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
from typing import Iterator, Sequence
from uuid import uuid4


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Store:
    def __init__(self, path: str | Path):
        self.path = Path(path)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def initialize(self) -> None:
        with self.connect() as connection:
            connection.executescript(
                """
                PRAGMA journal_mode = WAL;
                CREATE TABLE IF NOT EXISTS runs (
                    id TEXT PRIMARY KEY,
                    subsystem TEXT NOT NULL CHECK (subsystem IN ('door','acv','rail','shm')),
                    status TEXT NOT NULL CHECK (status IN ('queued','running','completed','failed')),
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    chart_json TEXT NOT NULL DEFAULT '[]',
                    error_code TEXT,
                    error_message TEXT
                );
                CREATE TABLE IF NOT EXISTS run_files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
                    ordinal INTEGER NOT NULL,
                    file_name TEXT NOT NULL,
                    stored_path TEXT NOT NULL,
                    UNIQUE(run_id, file_name),
                    UNIQUE(run_id, ordinal)
                );
                CREATE TABLE IF NOT EXISTS results (
                    id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
                    ordinal INTEGER NOT NULL,
                    payload_json TEXT NOT NULL,
                    review_status TEXT NOT NULL DEFAULT 'unreviewed',
                    review_note TEXT NOT NULL DEFAULT '',
                    UNIQUE(run_id, ordinal)
                );
                CREATE TABLE IF NOT EXISTS reviews (
                    id TEXT PRIMARY KEY,
                    result_id TEXT NOT NULL REFERENCES results(id) ON DELETE CASCADE,
                    status TEXT NOT NULL,
                    note TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_runs_created ON runs(created_at DESC);
                CREATE INDEX IF NOT EXISTS idx_reviews_result ON reviews(result_id, created_at);
                """
            )
            restarted_at = _now()
            connection.execute(
                """
                UPDATE runs
                SET status = 'failed', updated_at = ?, error_code = 'server_restarted',
                    error_message = 'The server restarted before this run completed.'
                WHERE status IN ('queued', 'running')
                """,
                (restarted_at,),
            )

    def create_run(
        self, subsystem: str, files: Sequence[tuple[str, Path]], run_id: str | None = None
    ) -> str:
        identifier = run_id or str(uuid4())
        timestamp = _now()
        with self.connect() as connection:
            connection.execute(
                "INSERT INTO runs(id, subsystem, status, created_at, updated_at) VALUES (?, ?, 'queued', ?, ?)",
                (identifier, subsystem, timestamp, timestamp),
            )
            connection.executemany(
                "INSERT INTO run_files(run_id, ordinal, file_name, stored_path) VALUES (?, ?, ?, ?)",
                [
                    (identifier, ordinal, file_name, str(path))
                    for ordinal, (file_name, path) in enumerate(files)
                ],
            )
        return identifier

    def set_running(self, run_id: str) -> None:
        with self.connect() as connection:
            cursor = connection.execute(
                "UPDATE runs SET status = 'running', updated_at = ?, error_code = NULL, error_message = NULL WHERE id = ? AND status = 'queued'",
                (_now(), run_id),
            )
            if cursor.rowcount != 1:
                raise ValueError(f"Run is not queued: {run_id}")

    def complete_run(
        self,
        run_id: str,
        records: Sequence[dict[str, object]],
        chart_series: Sequence[dict[str, object]],
    ) -> None:
        with self.connect() as connection:
            status = connection.execute(
                "SELECT status FROM runs WHERE id = ?", (run_id,)
            ).fetchone()
            if status is None or status["status"] != "running":
                raise ValueError(f"Run is not running: {run_id}")
            connection.executemany(
                "INSERT INTO results(id, run_id, ordinal, payload_json) VALUES (?, ?, ?, ?)",
                [
                    (str(uuid4()), run_id, ordinal, json.dumps(record, allow_nan=False))
                    for ordinal, record in enumerate(records)
                ],
            )
            connection.execute(
                "UPDATE runs SET status = 'completed', updated_at = ?, chart_json = ? WHERE id = ?",
                (_now(), json.dumps(list(chart_series), allow_nan=False), run_id),
            )

    def fail_run(self, run_id: str, code: str, message: str) -> None:
        with self.connect() as connection:
            connection.execute(
                "UPDATE runs SET status = 'failed', updated_at = ?, error_code = ?, error_message = ? WHERE id = ?",
                (_now(), code, message[:4000], run_id),
            )

    def get_files(self, run_id: str) -> list[dict[str, object]]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT file_name, stored_path, ordinal FROM run_files WHERE run_id = ? ORDER BY ordinal",
                (run_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def get_run(self, run_id: str) -> dict[str, object] | None:
        with self.connect() as connection:
            run = connection.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
            if run is None:
                return None
            files = connection.execute(
                "SELECT file_name FROM run_files WHERE run_id = ? ORDER BY ordinal", (run_id,)
            ).fetchall()
            results = connection.execute(
                "SELECT * FROM results WHERE run_id = ? ORDER BY ordinal", (run_id,)
            ).fetchall()
        output = {
            "run_id": run["id"],
            "subsystem": run["subsystem"],
            "status": run["status"],
            "created_at": run["created_at"],
            "updated_at": run["updated_at"],
            "files": [row["file_name"] for row in files],
            "results": [self._result_dict(row) for row in results],
            "chart_series": json.loads(run["chart_json"]),
            "error": None,
        }
        if run["error_code"]:
            output["error"] = {
                "code": run["error_code"],
                "message": run["error_message"],
            }
        return output

    def list_runs(self) -> list[dict[str, object]]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT r.*, COUNT(DISTINCT f.id) AS file_count,
                       COUNT(DISTINCT x.id) AS result_count
                FROM runs r
                LEFT JOIN run_files f ON f.run_id = r.id
                LEFT JOIN results x ON x.run_id = r.id
                GROUP BY r.id
                ORDER BY r.created_at DESC
                """
            ).fetchall()
        return [
            {
                "run_id": row["id"],
                "subsystem": row["subsystem"],
                "status": row["status"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
                "file_count": row["file_count"],
                "result_count": row["result_count"],
                "error": (
                    {"code": row["error_code"], "message": row["error_message"]}
                    if row["error_code"]
                    else None
                ),
            }
            for row in rows
        ]

    def update_review(self, result_id: str, status: str, note: str) -> dict[str, object] | None:
        event_id = str(uuid4())
        timestamp = _now()
        with self.connect() as connection:
            cursor = connection.execute(
                "UPDATE results SET review_status = ?, review_note = ? WHERE id = ?",
                (status, note, result_id),
            )
            if cursor.rowcount != 1:
                return None
            connection.execute(
                "INSERT INTO reviews(id, result_id, status, note, created_at) VALUES (?, ?, ?, ?, ?)",
                (event_id, result_id, status, note, timestamp),
            )
            row = connection.execute("SELECT * FROM results WHERE id = ?", (result_id,)).fetchone()
        return self._result_dict(row)

    def get_reviews(self, result_id: str) -> list[dict[str, object]] | None:
        with self.connect() as connection:
            exists = connection.execute("SELECT 1 FROM results WHERE id = ?", (result_id,)).fetchone()
            if exists is None:
                return None
            rows = connection.execute(
                "SELECT id, status, note, created_at FROM reviews WHERE result_id = ? ORDER BY created_at, id",
                (result_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    @staticmethod
    def _result_dict(row: sqlite3.Row) -> dict[str, object]:
        payload = json.loads(row["payload_json"])
        return {
            "result_id": row["id"],
            **payload,
            "review_status": row["review_status"],
            "review_note": row["review_note"],
        }
