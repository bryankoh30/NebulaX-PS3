"""FastAPI application for model runs, reviews, charts, and exports."""

from __future__ import annotations

from contextlib import asynccontextmanager
import io
from pathlib import Path
import shutil
from typing import Annotated
from uuid import uuid4
import zipfile

from fastapi import FastAPI, File, Form, HTTPException, Response, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware

from .adapters import OUTPUT_FILENAMES, official_csv
from .config import Settings
from .database import Store
from .schemas import ExportRequest, ReviewUpdate, Subsystem
from .worker import InferenceWorker


ALLOWED_SUFFIXES = {
    "door": {".csv"},
    "acv": {".xlsx"},
    "rail": {".csv"},
    "shm": {".csv"},
}


def _error(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"code": code, "message": message})


def _model_records(run: dict[str, object]) -> list[dict[str, object]]:
    metadata = {"result_id", "review_status", "review_note"}
    return [
        {key: value for key, value in result.items() if key not in metadata}
        for result in run["results"]
    ]


def create_app(settings: Settings | None = None) -> FastAPI:
    config = settings or Settings.from_env()
    store = Store(config.database_path)
    worker = InferenceWorker(store, config.chart_point_limit)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        config.upload_dir.mkdir(parents=True, exist_ok=True)
        store.initialize()
        worker.start()
        try:
            yield
        finally:
            worker.stop()

    application = FastAPI(title="NebulaX Predictive Maintenance API", lifespan=lifespan)
    application.state.settings = config
    application.state.store = store
    application.state.worker = worker
    application.add_middleware(
        CORSMiddleware,
        allow_origins=list(config.cors_origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @application.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @application.post("/api/runs", status_code=status.HTTP_202_ACCEPTED)
    async def create_run(
        subsystem: Annotated[Subsystem, Form()],
        files: Annotated[list[UploadFile], File()],
    ) -> dict[str, str]:
        if not files:
            raise _error(400, "files_required", "At least one file is required.")
        if subsystem == "door" and len(files) != 1:
            raise _error(400, "invalid_file_count", "Door accepts exactly one CSV file.")

        names = [item.filename or "" for item in files]
        if any(not name or Path(name).name != name for name in names):
            raise _error(400, "invalid_filename", "Uploads must use plain, nonempty basenames.")
        normalized = [name.casefold() for name in names]
        if len(normalized) != len(set(normalized)):
            raise _error(400, "duplicate_filename", "Filenames must be unique within a run.")
        invalid = [name for name in names if Path(name).suffix.casefold() not in ALLOWED_SUFFIXES[subsystem]]
        if invalid:
            expected = ", ".join(sorted(ALLOWED_SUFFIXES[subsystem]))
            raise _error(400, "invalid_extension", f"{subsystem} accepts {expected} files.")

        run_id = str(uuid4())
        run_directory = config.upload_dir / run_id
        run_directory.mkdir(parents=True)
        saved: list[tuple[str, Path]] = []
        total_size = 0
        try:
            for upload, name in zip(files, names, strict=True):
                destination = run_directory / name
                file_size = 0
                with destination.open("xb") as stream:
                    while chunk := await upload.read(1024 * 1024):
                        total_size += len(chunk)
                        file_size += len(chunk)
                        if total_size > config.max_upload_bytes:
                            raise _error(
                                413,
                                "upload_too_large",
                                f"Combined upload exceeds {config.max_upload_bytes} bytes.",
                            )
                        stream.write(chunk)
                if file_size == 0:
                    raise _error(400, "empty_file", f"Recording is empty: {name}")
                saved.append((name, destination))
        except Exception:
            shutil.rmtree(run_directory, ignore_errors=True)
            raise
        finally:
            for upload in files:
                await upload.close()

        try:
            store.create_run(subsystem, saved, run_id=run_id)
        except Exception:
            shutil.rmtree(run_directory, ignore_errors=True)
            raise
        worker.submit(run_id)
        return {"run_id": run_id, "status": "queued"}

    @application.get("/api/runs/{run_id}")
    def get_run(run_id: str) -> dict[str, object]:
        run = store.get_run(run_id)
        if run is None:
            raise _error(404, "run_not_found", "Run does not exist.")
        return run

    @application.get("/api/runs")
    def list_runs() -> list[dict[str, object]]:
        return store.list_runs()

    @application.patch("/api/results/{result_id}/review")
    def review_result(result_id: str, update: ReviewUpdate) -> dict[str, object]:
        result = store.update_review(result_id, update.status, update.note.strip())
        if result is None:
            raise _error(404, "result_not_found", "Result does not exist.")
        return result

    @application.get("/api/results/{result_id}/reviews")
    def review_history(result_id: str) -> list[dict[str, object]]:
        reviews = store.get_reviews(result_id)
        if reviews is None:
            raise _error(404, "result_not_found", "Result does not exist.")
        return reviews

    @application.get("/api/runs/{run_id}/export")
    def export_run(run_id: str) -> Response:
        run = store.get_run(run_id)
        if run is None:
            raise _error(404, "run_not_found", "Run does not exist.")
        if run["status"] != "completed":
            raise _error(409, "run_not_completed", "Only completed runs can be exported.")
        subsystem = str(run["subsystem"])
        content = official_csv(subsystem, _model_records(run))
        filename = OUTPUT_FILENAMES[subsystem]
        return Response(
            content=content,
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    @application.post("/api/exports")
    def export_zip(request: ExportRequest) -> Response:
        if len(request.run_ids) != len(set(request.run_ids)):
            raise _error(400, "duplicate_run", "Each run ID may appear only once.")
        runs: list[dict[str, object]] = []
        for run_id in request.run_ids:
            run = store.get_run(run_id)
            if run is None:
                raise _error(404, "run_not_found", f"Run does not exist: {run_id}")
            if run["status"] != "completed":
                raise _error(409, "run_not_completed", f"Run is not completed: {run_id}")
            runs.append(run)
        subsystems = [str(run["subsystem"]) for run in runs]
        if len(subsystems) != len(set(subsystems)):
            raise _error(400, "duplicate_subsystem", "Select at most one run per subsystem.")

        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for run in runs:
                subsystem = str(run["subsystem"])
                archive.writestr(
                    OUTPUT_FILENAMES[subsystem],
                    official_csv(subsystem, _model_records(run)),
                )
        return Response(
            content=buffer.getvalue(),
            media_type="application/zip",
            headers={"Content-Disposition": 'attachment; filename="predictions.zip"'},
        )

    return application


app = create_app()
