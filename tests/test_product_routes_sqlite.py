from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.application.automation.service import AutomationService
from app.application.products.service import ProductService
from app.bootstrap.wiring.container import AppContainer
from app.infrastructure.persistence.sqlite import (
    SQLiteBrandRepository,
    SQLiteMarginSettingsStore,
    SQLiteMetricsStore,
    SQLiteProductRepository,
)
from app.interfaces.api.http.app import create_app
from app.shared.config.settings import AppSettings


class ProductRoutesSQLiteTests(unittest.TestCase):
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
        )
        settings = AppSettings()
        products = SQLiteProductRepository(paths.database_file, paths.products_active_file, paths.products_history_file)
        brands = SQLiteBrandRepository(paths.database_file, paths.brands_file, settings.default_brands)
        margin = SQLiteMarginSettingsStore(paths.database_file, paths.margin_file, settings.default_margin)
        metrics = SQLiteMetricsStore(paths.database_file, paths.metrics_file)
        product_service = ProductService(products, brands, margin, metrics)
        automation_service = AutomationService(product_service, data_dir)
        return AppContainer(
            settings=settings,
            paths=paths,
            product_service=product_service,
            automation_service=automation_service,
        )

    def test_reorder_route_changes_only_order(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            container = self._build_container(root)
            with patch("app.interfaces.api.http.app.build_container", return_value=container):
                client = TestClient(create_app())

                first = client.post(
                    "/products",
                    json={
                        "nome": "Primeiro",
                        "codigo": "A1",
                        "quantidade": 1,
                        "preco": "10,00",
                        "categoria": "Infantil",
                        "marca": "Marca 1",
                    },
                ).json()["item"]
                second = client.post(
                    "/products",
                    json={
                        "nome": "Segundo",
                        "codigo": "B2",
                        "quantidade": 2,
                        "preco": "20,00",
                        "categoria": "Masculino",
                        "marca": "Marca 2",
                    },
                ).json()["item"]

                response = client.post("/actions/reorder", json={"keys": [second["ordering_key"], first["ordering_key"]]})
                self.assertEqual(response.status_code, 200)

                listed = client.get("/products").json()["items"]
                self.assertEqual([item["ordering_key"] for item in listed], [second["ordering_key"], first["ordering_key"]])
                self.assertEqual(listed[0]["nome"], "Segundo")
                self.assertEqual(listed[1]["nome"], "Primeiro")
                self.assertEqual(listed[0]["preco"], "20,00")
                self.assertEqual(listed[1]["preco"], "10,00")

    def test_restore_snapshot_preserves_ordering_keys(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            container = self._build_container(root)
            with patch("app.interfaces.api.http.app.build_container", return_value=container):
                client = TestClient(create_app())

                created = client.post(
                    "/products",
                    json={
                        "nome": "Produto Base",
                        "codigo": "COD-1",
                        "quantidade": 1,
                        "preco": "10,00",
                        "categoria": "",
                        "marca": "",
                    },
                ).json()["item"]

                restore_payload = {
                    "items": [
                        {
                            "ordering_key": created["ordering_key"],
                            "nome": created["nome"],
                            "codigo": "COD-ALTERADO",
                            "codigo_original": created["codigo_original"],
                            "quantidade": created["quantidade"],
                            "preco": created["preco"],
                            "categoria": created["categoria"],
                            "marca": created["marca"],
                            "preco_final": created["preco_final"],
                            "descricao_completa": created["descricao_completa"],
                            "grades": created.get("grades"),
                            "cores": created.get("cores"),
                            "timestamp": created["timestamp"],
                        }
                    ]
                }
                response = client.post("/actions/restore-snapshot", json=restore_payload)
                self.assertEqual(response.status_code, 200)

                listed = client.get("/products").json()["items"]
                self.assertEqual(len(listed), 1)
                self.assertEqual(listed[0]["ordering_key"], created["ordering_key"])
                self.assertEqual(listed[0]["codigo"], "COD-ALTERADO")

    def test_export_json_uses_database_contents(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            container = self._build_container(root)
            with patch("app.interfaces.api.http.app.build_container", return_value=container):
                client = TestClient(create_app())

                created = client.post(
                    "/products",
                    json={
                        "nome": "Exportavel",
                        "codigo": "EXP-1",
                        "quantidade": 3,
                        "preco": "15,00",
                        "categoria": "Infantil",
                        "marca": "Marca E",
                    },
                ).json()["item"]

                response = client.get("/actions/export-json")
                self.assertEqual(response.status_code, 200)
                self.assertIn('filename="products_active.jsonl"', response.headers.get("content-disposition", ""))
                lines = [line for line in response.text.splitlines() if line.strip()]
                self.assertEqual(len(lines), 1)
                exported = json.loads(lines[0])
                self.assertEqual(exported["ordering_key"], created["ordering_key"])
                self.assertEqual(exported["codigo"], "EXP-1")


if __name__ == "__main__":
    unittest.main()
