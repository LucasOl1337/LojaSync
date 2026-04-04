from __future__ import annotations

import time
import uuid
from threading import RLock
from typing import Any, Callable, Generic, Mapping, TypeVar

StatusT = TypeVar("StatusT")
ResultT = TypeVar("ResultT")


class InMemoryJobStore(Generic[StatusT, ResultT]):
    def __init__(
        self,
        *,
        stage_messages: Mapping[str, str],
        status_factory: Callable[..., StatusT],
    ) -> None:
        self._stage_messages = dict(stage_messages)
        self._status_factory = status_factory
        self._jobs: dict[str, StatusT] = {}
        self._results: dict[str, ResultT] = {}
        self._lock = RLock()

    def create(self) -> StatusT:
        now = time.time()
        job = self._status_factory(
            job_id=uuid.uuid4().hex,
            stage="pending",
            message=self._stage_messages["pending"],
            started_at=now,
            updated_at=now,
        )
        with self._lock:
            self._jobs[getattr(job, "job_id")] = job
        return job

    def update(
        self,
        job_id: str,
        stage: str,
        *,
        message: str | None = None,
        error: str | None = None,
        result: ResultT | None = None,
        metrics: dict[str, Any] | None = None,
    ) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return
            setattr(job, "stage", stage)
            setattr(job, "message", message or self._stage_messages.get(stage, stage))
            setattr(job, "updated_at", time.time())
            if error is not None:
                setattr(job, "error", error)
            if metrics is not None and hasattr(job, "metrics"):
                merged = dict(getattr(job, "metrics", {}) or {})
                merged.update(metrics)
                setattr(job, "metrics", merged)
            if result is not None or stage == "completed":
                setattr(job, "completed_at", getattr(job, "updated_at"))
            if result is not None:
                self._results[job_id] = result

    def get_job(self, job_id: str) -> StatusT | None:
        with self._lock:
            return self._jobs.get(job_id)

    def get_result(self, job_id: str) -> ResultT | None:
        with self._lock:
            return self._results.get(job_id)

    def remove(self, job_id: str) -> bool:
        with self._lock:
            exists = job_id in self._jobs or job_id in self._results
            self._jobs.pop(job_id, None)
            self._results.pop(job_id, None)
        return exists
