from __future__ import annotations

from dataclasses import dataclass, field
import unittest

from app.shared.jobs.in_memory import InMemoryJobStore


@dataclass
class DummyStatus:
    job_id: str
    stage: str
    message: str
    started_at: float
    updated_at: float
    completed_at: float | None = None
    error: str | None = None
    metrics: dict[str, int] = field(default_factory=dict)


@dataclass
class DummyResult:
    status: str
    total: int = 0


class JobStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.store = InMemoryJobStore[DummyStatus, DummyResult](
            stage_messages={
                "pending": "Aguardando inicio",
                "processing": "Processando",
                "completed": "Concluido",
            },
            status_factory=DummyStatus,
        )

    def test_import_job_store_tracks_metrics_and_result(self) -> None:
        job = self.store.create()

        self.store.update(job.job_id, "processing", metrics={"step": 1})
        self.store.update(
            job.job_id,
            "completed",
            result=DummyResult(status="ok", total=2),
            metrics={"duration_ms": 45},
        )

        stored = self.store.get_job(job.job_id)
        result = self.store.get_result(job.job_id)

        self.assertIsNotNone(stored)
        self.assertEqual(stored.stage, "completed")
        self.assertIsNotNone(stored.completed_at)
        self.assertEqual(stored.metrics["step"], 1)
        self.assertEqual(stored.metrics["duration_ms"], 45)
        self.assertIsNotNone(result)
        self.assertEqual(result.total, 2)
        self.assertTrue(self.store.remove(job.job_id))

    def test_grade_job_store_tracks_completion_and_cleanup(self) -> None:
        job = self.store.create()

        self.store.update(
            job.job_id,
            "completed",
            result=DummyResult(status="ok", total=1),
        )

        stored = self.store.get_job(job.job_id)
        result = self.store.get_result(job.job_id)

        self.assertIsNotNone(stored)
        self.assertEqual(stored.stage, "completed")
        self.assertIsNotNone(stored.completed_at)
        self.assertIsNotNone(result)
        self.assertEqual(result.total, 1)
        self.assertTrue(self.store.remove(job.job_id))


if __name__ == "__main__":
    unittest.main()
