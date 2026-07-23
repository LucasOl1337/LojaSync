from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.application.auth.service import AuthService
from app.application.automation.service import AutomationService
from app.application.products.service import MAX_UNDO_HISTORY, ProductService
from app.bootstrap.wiring.container import AppContainer
from app.infrastructure.persistence.files.auth_store import JsonAuthStore
from app.infrastructure.persistence.files.undo_history import JsonUndoRedoHistoryStore
from app.infrastructure.persistence.sqlite import (
    SQLiteBrandRepository,
    SQLiteMarginSettingsStore,
    SQLiteMetricsStore,
    SQLiteProductRepository,
)
from app.interfaces.api.http.app import create_app
from app.shared.config.settings import AppSettings
from tests.auth_test_support import AuthServiceConnectorStub


class ImportReapplyTests(unittest.TestCase):
    def _build_container(self, root: Path) -> AppContainer:
        data_dir = root / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        ts_dir = root / "frontend-ts" / "dist"
        legacy_dir = root / "app" / "interfaces" / "webapp" / "static"
        ts_dir.mkdir(parents=True, exist_ok=True)
        legacy_dir.mkdir(parents=True, exist_ok=True)
        (ts_dir / "index.html").write_text("<!doctype html><title>TS</title>", encoding="utf-8")
        (legacy_dir / "index.html").write_text("<!doctype html><title>Legacy</title>", encoding="utf-8")

        paths = SimpleNamespace(
            root_dir=root,
            app_dir=root / "app",
            data_dir=data_dir,
            web_static_dir=legacy_dir,
            web_ts_dist_dir=ts_dir,
            database_file=data_dir / "lojasync.db",
            products_active_file=data_dir / "products_active.jsonl",
            products_history_file=data_dir / "products_history.jsonl",
            brands_file=data_dir / "brands.json",
            metrics_file=data_dir / "metrics.json",
            margin_file=data_dir / "margem.json",
            auth_file=data_dir / "auth.json",
            undo_history_file=data_dir / "undo_redo_history.json",
        )
        settings = AppSettings()
        auth_store = JsonAuthStore(paths.auth_file, settings.auth_session_ttl_minutes)
        auth_service = AuthService(auth_store, settings.auth_password_min_length, settings.auth_cookie_name)
        auth_connector = AuthServiceConnectorStub(auth_service)
        products = SQLiteProductRepository(paths.database_file, paths.products_active_file, paths.products_history_file)
        brands = SQLiteBrandRepository(paths.database_file, paths.brands_file, settings.default_brands)
        margin = SQLiteMarginSettingsStore(paths.database_file, paths.margin_file, settings.default_margin)
        metrics = SQLiteMetricsStore(paths.database_file, paths.metrics_file)
        undo_history = JsonUndoRedoHistoryStore(paths.undo_history_file, MAX_UNDO_HISTORY)
        product_service = ProductService(products, brands, margin, metrics, undo_history)
        automation_service = AutomationService(product_service, data_dir)
        return AppContainer(
            settings=settings,
            paths=paths,
            auth_connector=auth_connector,
            product_service=product_service,
            automation_service=automation_service,
        )

    def test_reapply_uses_processed_content_without_llm(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            container = self._build_container(Path(tmpdir))
            with patch("app.interfaces.api.http.app.build_container", return_value=container):
                client = TestClient(create_app())
                self.assertEqual(client.post("/auth/bootstrap", json={"password": "senha-forte-123"}).status_code, 200)

                content = "codigo|nome|quantidade|preco\nC200|CAMISETA|2|20,00\nC300|CALCA|1|30,00"
                response = client.post(
                    "/actions/import-romaneio/reapply",
                    json={
                        "content": content,
                        "source_name": "romaneio_reapply.txt",
                        "import_mode": "llm",
                    },
                )
                self.assertEqual(response.status_code, 200, response.text)
                payload = response.json()
                self.assertEqual(payload["total_itens"], 2)
                self.assertTrue(payload["metrics"]["llm_skipped"])
                self.assertTrue(payload["metrics"]["reapplied"])
                self.assertEqual(len(payload["imported_keys"]), 2)

                products = client.get("/products").json()["items"]
                self.assertEqual(len(products), 2)
                codes = sorted(item["codigo"] for item in products)
                self.assertEqual(codes, ["C200", "C300"])

    def test_reapply_rejects_empty_processed_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            container = self._build_container(Path(tmpdir))
            with patch("app.interfaces.api.http.app.build_container", return_value=container):
                client = TestClient(create_app())
                self.assertEqual(client.post("/auth/bootstrap", json={"password": "senha-forte-123"}).status_code, 200)
                response = client.post("/actions/import-romaneio/reapply", json={"content": "", "local_file": None})
                self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()
