from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from app.application.automation.service import AutomationService


class AutomationServiceNativeGateTests(unittest.TestCase):
    def _make_service(self, data_dir: Path) -> AutomationService:
        return AutomationService(product_service=Mock(), data_dir=data_dir)

    def test_native_byteempresa_is_disabled_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir, patch.dict(os.environ, {}, clear=False):
            service = self._make_service(Path(tmpdir))
            with patch.object(AutomationService, "_native_byte_empresa_supported", return_value=True):
                self.assertFalse(service._should_use_native_byte_empresa())

    def test_native_byteempresa_can_be_enabled_by_env(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir, patch.dict(
            os.environ,
            {"LOJASYNC_ENABLE_NATIVE_BYTEEMPRESA": "1"},
            clear=False,
        ):
            service = self._make_service(Path(tmpdir))
            with patch.object(AutomationService, "_native_byte_empresa_supported", return_value=True):
                self.assertTrue(service._should_use_native_byte_empresa())

    def test_native_byteempresa_can_be_enabled_by_profile(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir, patch.dict(os.environ, {}, clear=False):
            service = self._make_service(Path(tmpdir))
            service._save_desktop_profile({"native_byte_empresa": {"enabled": True}})
            with patch.object(AutomationService, "_native_byte_empresa_supported", return_value=True):
                self.assertTrue(service._should_use_native_byte_empresa())
