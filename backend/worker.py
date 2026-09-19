"""Single-consumer background inference worker."""

from __future__ import annotations

from pathlib import Path
from queue import Queue
from threading import Thread

from .adapters import run_inference
from .charts import build_chart_series
from .database import Store


class InferenceWorker:
    def __init__(self, store: Store, chart_point_limit: int):
        self.store = store
        self.chart_point_limit = chart_point_limit
        self._queue: Queue[str | None] = Queue()
        self._thread: Thread | None = None

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._thread = Thread(target=self._consume, name="inference-worker", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if self._thread is None:
            return
        self._queue.put(None)
        self._thread.join(timeout=10)
        self._thread = None

    def submit(self, run_id: str) -> None:
        self._queue.put(run_id)

    def process(self, run_id: str) -> None:
        try:
            self.store.set_running(run_id)
            run = self.store.get_run(run_id)
            if run is None:
                raise ValueError(f"Unknown run: {run_id}")
            paths = [Path(item["stored_path"]) for item in self.store.get_files(run_id)]
            records = run_inference(str(run["subsystem"]), paths)
            charts = build_chart_series(
                str(run["subsystem"]), paths, self.chart_point_limit
            )
            self.store.complete_run(run_id, records, charts)
        except Exception as exc:
            self.store.fail_run(run_id, "inference_failed", str(exc) or type(exc).__name__)

    def _consume(self) -> None:
        while True:
            run_id = self._queue.get()
            try:
                if run_id is None:
                    return
                self.process(run_id)
            finally:
                self._queue.task_done()
