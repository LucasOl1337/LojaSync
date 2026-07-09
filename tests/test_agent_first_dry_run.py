from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.application.automation.service import AutomationService
from app.application.auth.service import AuthService
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


class AgentFirstDryRunTests(unittest.TestCase):
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

    def _auth(self, client: TestClient) -> None:
        self.assertEqual(client.post("/auth/bootstrap", json={"password": "senha-forte-123"}).status_code, 200)

    def _seed(self, client: TestClient, *, duplicate: bool = False) -> None:
        for idx in range(1, 3):
            response = client.post(
                "/products",
                json={
                    "nome": "Item Dup" if duplicate else f"Item {idx}",
                    "codigo": "AAA1" if duplicate else f"AAA{idx}",
                    "quantidade": idx,
                    "preco": "10,00",
                    "categoria": "",
                    "marca": "",
                },
            )
            self.assertEqual(response.status_code, 201)

    def test_join_duplicates_dry_run_does_not_persist(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            container = self._build_container(Path(tmpdir))
            with patch("app.interfaces.api.http.app.build_container", return_value=container):
                client = TestClient(create_app())
                self._auth(client)
                self._seed(client, duplicate=True)
                self.assertEqual(len(client.get("/products").json()["items"]), 2)

                preview = client.post("/actions/join-duplicates?dry_run=true")
                self.assertEqual(preview.status_code, 200)
                body = preview.json()
                self.assertTrue(body["dry_run"])
                self.assertEqual(body["removidos"], 1)
                self.assertEqual(len(client.get("/products").json()["items"]), 2)
                self.assertFalse(client.get("/actions/history").json()["can_undo"])

                applied = client.post("/actions/join-duplicates")
                self.assertEqual(applied.status_code, 200)
                self.assertFalse(applied.json()["dry_run"])
                self.assertEqual(len(client.get("/products").json()["items"]), 1)
                self.assertTrue(client.get("/actions/history").json()["can_undo"])

    def test_clear_dry_run_and_apply_margin_dry_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            container = self._build_container(Path(tmpdir))
            with patch("app.interfaces.api.http.app.build_container", return_value=container):
                client = TestClient(create_app())
                self._auth(client)
                self._seed(client)

                clear_preview = client.delete("/products?dry_run=true")
                self.assertEqual(clear_preview.status_code, 200)
                self.assertTrue(clear_preview.json()["dry_run"])
                self.assertEqual(clear_preview.json()["removed"], 2)
                self.assertEqual(len(client.get("/products").json()["items"]), 2)

                margin_preview = client.post("/actions/apply-margin", json={"percentual": 50, "dry_run": True})
                self.assertEqual(margin_preview.status_code, 200)
                self.assertTrue(margin_preview.json()["dry_run"])
                self.assertGreaterEqual(margin_preview.json()["total_atualizados"], 1)
                item = client.get("/products").json()["items"][0]
                self.assertIsNotNone(item.get("preco_final"))


if __name__ == "__main__":
    unittest.main()
