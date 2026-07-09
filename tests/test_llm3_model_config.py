from __future__ import annotations

import importlib
import os
import unittest
from unittest.mock import patch

import Legacy.engine.LLM3.backend as llm_backend


class Llm3ModelConfigTests(unittest.TestCase):
    def _reload_backend(self, env: dict[str, str] | None = None):
        env = env or {}
        keys = [
            "LLM_MODEL_NAME",
            "LLM_TEXT_MODEL_NAME",
            "LLM_VISION_MODEL_NAME",
            "LLM_TEXT_FALLBACK_MODEL_NAMES",
            "LLM_VISION_FALLBACK_MODEL_NAMES",
            "LLM_TEMPERATURE",
            "LLM_SEED",
        ]
        with patch.dict(os.environ, {}, clear=False):
            for key in keys:
                os.environ.pop(key, None)
            os.environ.update(env)
            return importlib.reload(llm_backend)

    def test_default_model_does_not_require_qwen_cloud_subscription(self) -> None:
        reloaded = self._reload_backend()

        self.assertNotEqual(reloaded.MODEL_NAME, "qwen3.5:cloud")
        self.assertEqual(reloaded.TEXT_MODEL_NAME, "minimax-m3")
        self.assertEqual(reloaded.VISION_MODEL_NAME, "minimax-m3")

    def test_legacy_configured_model_falls_back_to_minimax_only(self) -> None:
        reloaded = self._reload_backend({"LLM_MODEL_NAME": "qwen3.5:cloud"})

        self.assertEqual(reloaded._candidate_model_names(has_images=False), ["qwen3.5:cloud", "minimax-m3"])
        self.assertEqual(reloaded._candidate_model_names(has_images=True), ["qwen3.5:cloud", "minimax-m3"])

    def test_subscription_errors_are_model_fallback_errors(self) -> None:
        reloaded = self._reload_backend()

        self.assertTrue(
            reloaded._is_model_fallback_error(
                403,
                '{"error":"this model requires a subscription, upgrade for access"}',
            )
        )
        self.assertFalse(reloaded._is_model_fallback_error(500, "temporary upstream failure"))

    def test_llm_requests_are_deterministic_by_default(self) -> None:
        reloaded = self._reload_backend()

        self.assertEqual(reloaded._llm_request_options(), {"temperature": 0.0, "seed": 42})

    def test_llm_request_options_can_be_overridden(self) -> None:
        reloaded = self._reload_backend({"LLM_TEMPERATURE": "0.2", "LLM_SEED": "99"})

        self.assertEqual(reloaded._llm_request_options(), {"temperature": 0.2, "seed": 99})


if __name__ == "__main__":
    unittest.main()
