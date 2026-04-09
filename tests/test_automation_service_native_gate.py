from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from app.application.automation.service import AutomationService
from app.domain.products.entities import GradeItem, Product


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

    def test_complete_ready_blocks_when_there_are_incomplete_grades(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir, patch.dict(os.environ, {}, clear=False):
            product_service = Mock()
            product_service.list_products.return_value = [
                Product(
                    nome="CALCA TESTE",
                    codigo="123",
                    quantidade=5,
                    preco="19,90",
                    categoria="Feminino",
                    marca="Marca",
                    grades=[GradeItem(tamanho="P", quantidade=2), GradeItem(tamanho="M", quantidade=1)],
                )
            ]
            service = AutomationService(product_service=product_service, data_dir=Path(tmpdir))
            with patch.object(service, "_should_use_native_byte_empresa", return_value=False), patch.object(
                service,
                "_ensure_bulk_ready",
                return_value=None,
            ):
                with self.assertRaisesRegex(RuntimeError, "grades pendentes"):
                    service._ensure_complete_ready()

    def test_status_exposes_current_product_details_while_running(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir, patch.dict(os.environ, {}, clear=False):
            service = self._make_service(Path(tmpdir))
            product = Product(
                nome="VESTIDO MIDI",
                codigo="ABC123",
                quantidade=2,
                preco="79,90",
                categoria="Feminino",
                marca="Marca",
            )
            service._running = True
            service._active_job_kind = "catalog"
            service._active_job_phase = "catalog"
            service._active_job_message = "Cadastrando produto 2/5"
            service._set_active_product(
                product,
                payload={"descricao_completa": "VESTIDO MIDI Marca ABC123"},
                index=2,
                total=5,
            )

            status = service.status()

            self.assertEqual(status["produto_atual"], "VESTIDO MIDI")
            self.assertEqual(status["codigo_atual"], "ABC123")
            self.assertEqual(status["descricao_digitada"], "VESTIDO MIDI Marca ABC123")
            self.assertEqual(status["item_atual"], 2)
            self.assertEqual(status["total_itens"], 5)
