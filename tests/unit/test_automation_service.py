from __future__ import annotations

import tempfile
import time
import unittest
from pathlib import Path

from app.application.automation import service as automation_service_module
from app.application.automation.service import AutomationService


class _DummyProducts:
    def list_products(self) -> list[object]:
        return []


class _FakePag:
    PAUSE = 0.0


class _FakeGradeBot:
    def __init__(self) -> None:
        self.pag = _FakePag()
        self.SPEED = 1.0
        self._cancelled = False
        self.calls: list[dict[str, object]] = []

    def parse_grades_json(self, value: str) -> dict[str, int]:
        return {"P": 1} if value else {}

    def reset_stop_flag(self) -> None:
        self._cancelled = False

    def request_stop(self) -> None:
        self._cancelled = True

    def is_cancel_requested(self) -> bool:
        return self._cancelled

    def run(self, grades_map: dict[str, int], model_index: int | None = None, activation_step: bool = True) -> None:
        self.calls.append(
            {
                "grades": dict(grades_map),
                "model_index": model_index,
                "activation_step": activation_step,
            }
        )
        time.sleep(0.05)


class AutomationServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self._previous_pyautogui = automation_service_module.pyautogui
        automation_service_module.pyautogui = object()

        self._tmpdir = tempfile.TemporaryDirectory()
        self._data_dir = Path(self._tmpdir.name)
        self.service = AutomationService(_DummyProducts(), self._data_dir)
        self.fake_gradebot = _FakeGradeBot()
        self.service._gradebot_module = self.fake_gradebot
        self.service._ensure_gradebot_ready = lambda: None  # type: ignore[method-assign]
        self.service._sync_legacy_automation_files = lambda: None  # type: ignore[method-assign]

    def tearDown(self) -> None:
        automation_service_module.pyautogui = self._previous_pyautogui
        self._tmpdir.cleanup()

    def test_run_gradebot_batch_starts_in_background(self) -> None:
        response = self.service.run_gradebot_batch(
            tasks=[{"grades": {"P": 2}}, {"grades": {"M": 3}}],
            pause=None,
            speed=None,
        )

        self.assertEqual(response["status"], "started")
        self.assertEqual(self.service.status()["estado"], "running")

        deadline = time.time() + 2.0
        while time.time() < deadline and self.service.status()["estado"] == "running":
            time.sleep(0.02)

        status = self.service.status()
        self.assertEqual(status["estado"], "idle")
        self.assertEqual(status["status"], "success")
        self.assertEqual(status["job_kind"], "grades")
        self.assertEqual(status["sucesso"], "2")
        self.assertEqual(len(self.fake_gradebot.calls), 2)
        self.assertTrue(self.fake_gradebot.calls[0]["activation_step"])
        self.assertFalse(self.fake_gradebot.calls[1]["activation_step"])


if __name__ == "__main__":
    unittest.main()
