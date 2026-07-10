from __future__ import annotations

import json
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
from app.domain.products.entities import GradeItem, Product
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

    def _authenticate(self, client: TestClient) -> None:
        response = client.post("/auth/bootstrap", json={"password": "senha-forte-123"})
        self.assertEqual(response.status_code, 200)

    def _login(self, client: TestClient) -> None:
        response = client.post("/auth/login", json={"password": "senha-forte-123"})
        self.assertEqual(response.status_code, 200)

    def test_product_routes_reject_invalid_create_prices(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            container = self._build_container(root)
            with patch("app.interfaces.api.http.app.build_container", return_value=container):
                client = TestClient(create_app())
                self._authenticate(client)

                base_payload = {
                    "nome": "Produto Invalido",
                    "codigo": "INV-1",
                    "quantidade": 1,
                    "categoria": "",
                    "marca": "",
                }
                for price in ["12,34abc", "-1,00"]:
                    with self.subTest(price=price):
                        response = client.post("/products", json={**base_payload, "preco": price})
                        self.assertEqual(response.status_code, 422)

                self.assertEqual(client.get("/products").json()["items"], [])

    def test_product_routes_reject_invalid_patch_prices(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            container = self._build_container(root)
            with patch("app.interfaces.api.http.app.build_container", return_value=container):
                client = TestClient(create_app())
                self._authenticate(client)

                created = client.post(
                    "/products",
                    json={
                        "nome": "Produto Base",
                        "codigo": "BASE-1",
                        "quantidade": 1,
                        "preco": "10,00",
                        "categoria": "",
                        "marca": "",
                    },
                ).json()["item"]

                for payload in [{"preco": "12,34abc"}, {"preco": "-1,00"}, {"preco_final": "-5,00"}]:
                    with self.subTest(payload=payload):
                        response = client.patch(f"/products/{created['ordering_key']}", json=payload)
                        self.assertEqual(response.status_code, 422)

                listed = client.get("/products").json()["items"]
                self.assertEqual(len(listed), 1)
                self.assertEqual(listed[0]["preco"], "10,00")

    def test_reorder_route_changes_only_order(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            container = self._build_container(root)
            with patch("app.interfaces.api.http.app.build_container", return_value=container):
                client = TestClient(create_app())
                self._authenticate(client)

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

    def test_bulk_actions_only_change_products_in_explicit_scope(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            container = self._build_container(root)
            with patch("app.interfaces.api.http.app.build_container", return_value=container):
                client = TestClient(create_app())
                self._authenticate(client)

                first = client.post(
                    "/products",
                    json={
                        "nome": "Camisa 123!",
                        "codigo": "00123",
                        "quantidade": 1,
                        "preco": "10,00",
                        "categoria": "Original A",
                        "marca": "Marca A",
                    },
                ).json()["item"]
                second = client.post(
                    "/products",
                    json={
                        "nome": "Calca 456!",
                        "codigo": "00999",
                        "quantidade": 1,
                        "preco": "20,00",
                        "categoria": "Original B",
                        "marca": "Marca B",
                    },
                ).json()["item"]
                first_key = first["ordering_key"]

                empty_scope = client.post(
                    "/actions/apply-category",
                    json={"valor": "Nao aplicar", "keys": []},
                )
                self.assertEqual(empty_scope.status_code, 200)
                self.assertEqual(empty_scope.json()["total"], 0)

                category = client.post(
                    "/actions/apply-category",
                    json={"valor": "Visivel", "keys": [first_key]},
                )
                brand = client.post(
                    "/actions/apply-brand",
                    json={"valor": "Marca visivel", "keys": [first_key]},
                )
                margin = client.post(
                    "/actions/apply-margin",
                    json={"percentual": 50, "keys": [first_key]},
                )
                codes = client.post(
                    "/actions/format-codes",
                    json={"remover_primeiros_numeros": 2, "keys": [first_key]},
                )
                descriptions = client.post(
                    "/actions/improve-descriptions",
                    json={"remover_numeros": True, "remover_especiais": True, "keys": [first_key]},
                )

                self.assertEqual(category.json()["total"], 1)
                self.assertEqual(brand.json()["total"], 1)
                self.assertEqual(margin.json()["total_atualizados"], 1)
                self.assertEqual(codes.json()["total"], 1)
                self.assertEqual(descriptions.json()["total"], 1)

                listed = {item["ordering_key"]: item for item in client.get("/products").json()["items"]}
                self.assertEqual(listed[first_key]["categoria"], "Visivel")
                self.assertEqual(listed[first_key]["marca"], "Marca visivel")
                self.assertEqual(listed[first_key]["codigo"], "123")
                self.assertEqual(listed[first_key]["nome"], "Camisa")
                self.assertNotEqual(listed[first_key]["preco_final"], first["preco_final"])

                second_after = listed[second["ordering_key"]]
                self.assertEqual(second_after["categoria"], "Original B")
                self.assertEqual(second_after["marca"], "Marca B")
                self.assertEqual(second_after["codigo"], "00999")
                self.assertEqual(second_after["nome"], "Calca 456!")
                self.assertEqual(second_after["preco_final"], second["preco_final"])

                restored = client.post(
                    "/actions/restore-original-codes",
                    json={"keys": [first_key]},
                )
                self.assertEqual(restored.json(), {"total": 1, "restaurados": 1})
                restored_items = {item["ordering_key"]: item for item in client.get("/products").json()["items"]}
                self.assertEqual(restored_items[first_key]["codigo"], "00123")
                self.assertEqual(restored_items[second["ordering_key"]]["codigo"], "00999")

    def test_join_duplicates_only_merges_products_in_explicit_scope(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            container = self._build_container(root)
            with patch("app.interfaces.api.http.app.build_container", return_value=container):
                client = TestClient(create_app())
                self._authenticate(client)

                created = []
                for quantity in (1, 2, 4):
                    created.append(
                        client.post(
                            "/products",
                            json={
                                "nome": "Camisa Basica",
                                "codigo": "CAM-1",
                                "quantidade": quantity,
                                "preco": "10,00",
                                "categoria": "Camisetas",
                                "marca": "Marca A",
                            },
                        ).json()["item"]
                    )

                empty_scope = client.post("/actions/join-duplicates", json={"keys": []})
                self.assertEqual(empty_scope.json(), {"originais": 0, "resultantes": 0, "removidos": 0})
                self.assertEqual(len(client.get("/products").json()["items"]), 3)

                response = client.post(
                    "/actions/join-duplicates",
                    json={"keys": [created[0]["ordering_key"], created[1]["ordering_key"]]},
                )
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json(), {"originais": 2, "resultantes": 1, "removidos": 1})

                listed = {item["ordering_key"]: item for item in client.get("/products").json()["items"]}
                self.assertEqual(len(listed), 2)
                self.assertEqual(listed[created[0]["ordering_key"]]["quantidade"], 3)
                self.assertEqual(listed[created[2]["ordering_key"]]["quantidade"], 4)

    def test_join_duplicates_preserves_distinct_product_details(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            container = self._build_container(root)
            with patch("app.interfaces.api.http.app.build_container", return_value=container):
                client = TestClient(create_app())
                self._authenticate(client)

                base = {
                    "nome": "Camisa Basica",
                    "codigo": "CAM-1",
                    "quantidade": 2,
                    "preco": "10,00",
                    "preco_final": "19,90",
                    "categoria": "Camisetas",
                    "marca": "Marca A",
                    "descricao_completa": "Malha premium",
                    "grades": [
                        {"tamanho": "P", "quantidade": 1},
                        {"tamanho": "M", "quantidade": 1},
                    ],
                    "cores": [
                        {"cor": "Azul", "quantidade": 1},
                        {"cor": "Verde", "quantidade": 1},
                    ],
                }
                payloads = [
                    base,
                    {
                        **base,
                        "grades": list(reversed(base["grades"])),
                        "cores": list(reversed(base["cores"])),
                    },
                    {**base, "descricao_completa": "Malha leve"},
                    {**base, "grades": [{"tamanho": "G", "quantidade": 2}]},
                    {**base, "cores": [{"cor": "Preto", "quantidade": 2}]},
                    {**base, "preco_final": "21,90"},
                ]
                created = [client.post("/products", json=payload).json()["item"] for payload in payloads]

                response = client.post(
                    "/actions/join-duplicates",
                    json={"keys": [item["ordering_key"] for item in created]},
                )

                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json(), {"originais": 6, "resultantes": 5, "removidos": 1})
                listed = client.get("/products").json()["items"]
                self.assertEqual(len(listed), 5)

                merged = next(item for item in listed if item["ordering_key"] == created[0]["ordering_key"])
                self.assertEqual(merged["quantidade"], 4)
                self.assertEqual(
                    {item["tamanho"]: item["quantidade"] for item in merged["grades"]},
                    {"P": 2, "M": 2},
                )
                self.assertEqual(
                    {item["cor"]: item["quantidade"] for item in merged["cores"]},
                    {"Azul": 2, "Verde": 2},
                )
                self.assertEqual({item["descricao_completa"] for item in listed}, {"Malha premium", "Malha leve"})
                self.assertEqual({item["preco_final"] for item in listed}, {"19,90", "21,90"})
                self.assertEqual(
                    {item["grades"][0]["tamanho"] for item in listed},
                    {"P", "G"},
                )
                self.assertEqual(
                    {item["cores"][0]["cor"] for item in listed},
                    {"Azul", "Preto"},
                )

    def test_restore_snapshot_preserves_ordering_keys(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            container = self._build_container(root)
            with patch("app.interfaces.api.http.app.build_container", return_value=container):
                client = TestClient(create_app())
                self._authenticate(client)

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

    def test_undo_history_persists_across_app_restart(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            first_container = self._build_container(root)
            with patch("app.interfaces.api.http.app.build_container", return_value=first_container):
                client = TestClient(create_app())
                self._authenticate(client)

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

                snapshot_response = client.post("/actions/history/snapshot")
                self.assertEqual(snapshot_response.status_code, 200)
                self.assertEqual(snapshot_response.json()["undo_count"], 1)

                patch_response = client.patch(f"/products/{created['ordering_key']}", json={"codigo": "COD-2"})
                self.assertEqual(patch_response.status_code, 200)

            restarted_container = self._build_container(root)
            with patch("app.interfaces.api.http.app.build_container", return_value=restarted_container):
                client = TestClient(create_app())
                self._login(client)

                history_response = client.get("/actions/history")
                self.assertEqual(history_response.status_code, 200)
                self.assertEqual(history_response.json()["undo_count"], 1)

                undo_response = client.post("/actions/history/undo")
                self.assertEqual(undo_response.status_code, 200)
                self.assertTrue(undo_response.json()["restored"])
                self.assertEqual(undo_response.json()["redo_count"], 1)

                listed = client.get("/products").json()["items"]
                self.assertEqual(len(listed), 1)
                self.assertEqual(listed[0]["codigo"], "COD-1")

    def test_undo_redo_restore_default_margin_across_app_restart(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            first_container = self._build_container(root)
            with patch("app.interfaces.api.http.app.build_container", return_value=first_container):
                client = TestClient(create_app())
                self._authenticate(client)

                created = client.post(
                    "/products",
                    json={
                        "nome": "Produto com margem reversivel",
                        "codigo": "MARGEM-1",
                        "quantidade": 1,
                        "preco": "10,00",
                        "categoria": "",
                        "marca": "",
                    },
                ).json()["item"]
                original_price = created["preco_final"]
                original_percent = client.get("/settings/margin").json()["percentual"]

                snapshot_response = client.post("/actions/history/snapshot")
                self.assertEqual(snapshot_response.status_code, 200)
                self.assertEqual(snapshot_response.json()["undo_count"], 1)

                margin_response = client.post("/settings/margin", json={"percentual": 65})
                self.assertEqual(margin_response.status_code, 200)
                apply_response = client.post(
                    "/actions/apply-margin",
                    json={"percentual": 65, "keys": [created["ordering_key"]]},
                )
                self.assertEqual(apply_response.status_code, 200)
                applied_price = client.get("/products").json()["items"][0]["preco_final"]
                self.assertNotEqual(applied_price, original_price)
                self.assertAlmostEqual(client.get("/settings/margin").json()["percentual"], 65)

            persisted_history = json.loads((root / "data" / "undo_redo_history.json").read_text(encoding="utf-8"))
            self.assertEqual(persisted_history["version"], 2)
            self.assertEqual(persisted_history["undo"][-1]["default_margin"], 1.0)

            restarted_container = self._build_container(root)
            with patch("app.interfaces.api.http.app.build_container", return_value=restarted_container):
                client = TestClient(create_app())
                self._login(client)

                undo_response = client.post("/actions/history/undo")
                self.assertEqual(undo_response.status_code, 200)
                self.assertTrue(undo_response.json()["restored"])
                self.assertEqual(client.get("/products").json()["items"][0]["preco_final"], original_price)
                self.assertAlmostEqual(client.get("/settings/margin").json()["percentual"], original_percent)

                redo_response = client.post("/actions/history/redo")
                self.assertEqual(redo_response.status_code, 200)
                self.assertTrue(redo_response.json()["restored"])
                self.assertEqual(client.get("/products").json()["items"][0]["preco_final"], applied_price)
                self.assertAlmostEqual(client.get("/settings/margin").json()["percentual"], 65)

    def test_undo_history_version_one_keeps_current_margin_when_margin_is_unknown(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            first_container = self._build_container(root)
            with patch("app.interfaces.api.http.app.build_container", return_value=first_container):
                client = TestClient(create_app())
                self._authenticate(client)

                created = client.post(
                    "/products",
                    json={
                        "nome": "Produto de historico legado",
                        "codigo": "LEGADO-1",
                        "quantidade": 1,
                        "preco": "10,00",
                        "categoria": "",
                        "marca": "",
                    },
                ).json()["item"]
                legacy_snapshot = first_container.product_service.list_products()[0].to_dict()
                patch_response = client.patch(
                    f"/products/{created['ordering_key']}",
                    json={"codigo": "LEGADO-ALTERADO"},
                )
                self.assertEqual(patch_response.status_code, 200)
                margin_response = client.post("/settings/margin", json={"percentual": 40})
                self.assertEqual(margin_response.status_code, 200)

            legacy_history = {
                "version": 1,
                "limit": MAX_UNDO_HISTORY,
                "undo": [[legacy_snapshot]],
                "redo": [],
            }
            history_file = root / "data" / "undo_redo_history.json"
            history_file.write_text(json.dumps(legacy_history, ensure_ascii=False), encoding="utf-8")

            restarted_container = self._build_container(root)
            with patch("app.interfaces.api.http.app.build_container", return_value=restarted_container):
                client = TestClient(create_app())
                self._login(client)

                undo_response = client.post("/actions/history/undo")
                self.assertEqual(undo_response.status_code, 200)
                self.assertTrue(undo_response.json()["restored"])
                self.assertEqual(client.get("/products").json()["items"][0]["codigo"], "LEGADO-1")
                self.assertAlmostEqual(client.get("/settings/margin").json()["percentual"], 40)

    def test_improve_descriptions_rejects_remove_letters_only_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            container = self._build_container(root)
            with patch("app.interfaces.api.http.app.build_container", return_value=container):
                client = TestClient(create_app())
                self._authenticate(client)

                client.post(
                    "/products",
                    json={
                        "nome": "CALCA ENT POCKETS SLIM OGPT",
                        "codigo": "COD-1",
                        "quantidade": 1,
                        "preco": "10,00",
                        "categoria": "",
                        "marca": "",
                    },
                )

                response = client.post("/actions/improve-descriptions", json={"remover_letras": True})
                self.assertEqual(response.status_code, 400)

                listed = client.get("/products").json()["items"]
                self.assertEqual(listed[0]["nome"], "CALCA ENT POCKETS SLIM OGPT")

    def test_join_grades_processes_all_pending_import_batches_without_touching_manual_items(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            container = self._build_container(root)
            with patch("app.interfaces.api.http.app.build_container", return_value=container):
                client = TestClient(create_app())
                self._authenticate(client)

                service = container.product_service
                service.create_many(
                    [
                        Product(
                            nome="Produto A 36",
                            codigo="BATCH-A",
                            quantidade=1,
                            preco="10,00",
                            categoria="",
                            marca="",
                            grades=[GradeItem(tamanho="36", quantidade=1)],
                            source_type="romaneio",
                            import_batch_id="batch-a",
                            import_source_name="romaneio_a.pdf",
                            pending_grade_import=True,
                        ),
                        Product(
                            nome="Produto A 38",
                            codigo="BATCH-A",
                            quantidade=1,
                            preco="10,00",
                            categoria="",
                            marca="",
                            grades=[GradeItem(tamanho="38", quantidade=1)],
                            source_type="romaneio",
                            import_batch_id="batch-a",
                            import_source_name="romaneio_a.pdf",
                            pending_grade_import=True,
                        ),
                        Product(
                            nome="Produto B P",
                            codigo="BATCH-B",
                            quantidade=1,
                            preco="20,00",
                            categoria="",
                            marca="",
                            grades=[GradeItem(tamanho="P", quantidade=1)],
                            source_type="romaneio",
                            import_batch_id="batch-b",
                            import_source_name="romaneio_b.pdf",
                            pending_grade_import=True,
                        ),
                        Product(
                            nome="Produto B M",
                            codigo="BATCH-B",
                            quantidade=1,
                            preco="20,00",
                            categoria="",
                            marca="",
                            grades=[GradeItem(tamanho="M", quantidade=1)],
                            source_type="romaneio",
                            import_batch_id="batch-b",
                            import_source_name="romaneio_b.pdf",
                            pending_grade_import=True,
                        ),
                        Product(
                            nome="Manual Avulso",
                            codigo="MANUAL-1",
                            quantidade=1,
                            preco="30,00",
                            categoria="",
                            marca="",
                            source_type="manual",
                            pending_grade_import=False,
                        ),
                    ]
                )

                response = client.post("/actions/join-grades", json={"keys": []})
                self.assertEqual(response.status_code, 200)
                payload = response.json()
                self.assertEqual(payload["lotes_processados"], 2)
                self.assertEqual(payload["atualizados_grades"], 2)

                listed = client.get("/products").json()["items"]
                self.assertEqual(len(listed), 3)

                manual = next(item for item in listed if item["codigo"] == "MANUAL-1")
                self.assertEqual(manual["source_type"], "manual")
                self.assertFalse(manual["pending_grade_import"])

                imported = [item for item in listed if item["codigo"] in {"BATCH-A", "BATCH-B"}]
                self.assertEqual(len(imported), 2)
                self.assertTrue(all(not item["pending_grade_import"] for item in imported))
                self.assertEqual({item["import_batch_id"] for item in imported}, {"batch-a", "batch-b"})
                grade_lookup = {
                    item["codigo"]: [(grade["tamanho"], grade["quantidade"]) for grade in (item.get("grades") or [])]
                    for item in imported
                }
                quantity_lookup = {item["codigo"]: item["quantidade"] for item in imported}
                self.assertEqual(grade_lookup["BATCH-A"], [("36", 1), ("38", 1)])
                self.assertEqual(grade_lookup["BATCH-B"], [("P", 1), ("M", 1)])
                self.assertEqual(quantity_lookup["BATCH-A"], 2)
                self.assertEqual(quantity_lookup["BATCH-B"], 2)

    def test_create_set_rejects_partial_variant_overflow_without_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            container = self._build_container(root)
            with patch("app.interfaces.api.http.app.build_container", return_value=container):
                client = TestClient(create_app())
                self._authenticate(client)

                first = client.post(
                    "/products",
                    json={
                        "nome": "CAMISETA",
                        "codigo": "A-OVERFLOW",
                        "quantidade": 5,
                        "preco": "10,00",
                        "categoria": "",
                        "marca": "",
                        "grades": [
                            {"tamanho": "P", "quantidade": 2},
                            {"tamanho": "M", "quantidade": 3},
                        ],
                        "cores": [{"cor": "Azul", "quantidade": 5}],
                    },
                ).json()["item"]
                second = client.post(
                    "/products",
                    json={
                        "nome": "SHORT",
                        "codigo": "B-OVERFLOW",
                        "quantidade": 2,
                        "preco": "20,00",
                        "categoria": "",
                        "marca": "",
                    },
                ).json()["item"]
                before = client.get("/products").json()["items"]

                response = client.post(
                    "/actions/create-set",
                    json={"key_a": first["ordering_key"], "key_b": second["ordering_key"]},
                )

                self.assertEqual(response.status_code, 409)
                detail = response.json()["detail"]
                self.assertIn('"CAMISETA" ficaria com 3 unidades', detail)
                self.assertIn("grades somam 5", detail)
                self.assertIn("cores somam 5", detail)
                self.assertIn("Ajuste grades/cores", detail)
                self.assertEqual(client.get("/products").json()["items"], before)

    def test_create_set_allows_total_consumption_with_complete_compositions(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            container = self._build_container(root)
            with patch("app.interfaces.api.http.app.build_container", return_value=container):
                client = TestClient(create_app())
                self._authenticate(client)

                created = []
                for payload in (
                    {
                        "nome": "CAMISETA",
                        "codigo": "A-TOTAL",
                        "quantidade": 2,
                        "preco": "10,00",
                        "categoria": "",
                        "marca": "",
                        "grades": [
                            {"tamanho": "P", "quantidade": 1},
                            {"tamanho": "M", "quantidade": 1},
                        ],
                        "cores": [{"cor": "Azul", "quantidade": 2}],
                    },
                    {
                        "nome": "SHORT",
                        "codigo": "B-TOTAL",
                        "quantidade": 2,
                        "preco": "20,00",
                        "categoria": "",
                        "marca": "",
                        "grades": [
                            {"tamanho": "36", "quantidade": 1},
                            {"tamanho": "38", "quantidade": 1},
                        ],
                        "cores": [{"cor": "Preto", "quantidade": 2}],
                    },
                ):
                    created.append(client.post("/products", json=payload).json()["item"])

                response = client.post(
                    "/actions/create-set",
                    json={"key_a": created[0]["ordering_key"], "key_b": created[1]["ordering_key"]},
                )

                self.assertEqual(response.status_code, 200)
                self.assertEqual(
                    response.json(),
                    {"created": 1, "removed": 2, "remaining_a": 0, "remaining_b": 0},
                )
                listed = client.get("/products").json()["items"]
                self.assertEqual(len(listed), 1)
                self.assertEqual(listed[0]["quantidade"], 2)
                self.assertIsNone(listed[0]["grades"])
                self.assertIsNone(listed[0]["cores"])

    def test_create_set_allows_partial_consumption_when_compositions_fit_balance(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            container = self._build_container(root)
            with patch("app.interfaces.api.http.app.build_container", return_value=container):
                client = TestClient(create_app())
                self._authenticate(client)

                first = client.post(
                    "/products",
                    json={
                        "nome": "CAMISETA",
                        "codigo": "A-FIT",
                        "quantidade": 5,
                        "preco": "10,00",
                        "categoria": "",
                        "marca": "",
                        "grades": [
                            {"tamanho": "P", "quantidade": 1},
                            {"tamanho": "M", "quantidade": 1},
                        ],
                        "cores": [{"cor": "Azul", "quantidade": 3}],
                    },
                ).json()["item"]
                second = client.post(
                    "/products",
                    json={
                        "nome": "SHORT",
                        "codigo": "B-FIT",
                        "quantidade": 2,
                        "preco": "20,00",
                        "categoria": "",
                        "marca": "",
                    },
                ).json()["item"]

                response = client.post(
                    "/actions/create-set",
                    json={"key_a": first["ordering_key"], "key_b": second["ordering_key"]},
                )

                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()["remaining_a"], 3)
                listed = client.get("/products").json()["items"]
                remaining = next(item for item in listed if item["codigo"] == "A-FIT")
                self.assertEqual(remaining["quantidade"], 3)
                self.assertEqual(
                    [(item["tamanho"], item["quantidade"]) for item in remaining["grades"]],
                    [("P", 1), ("M", 1)],
                )
                self.assertEqual(remaining["cores"], [{"cor": "Azul", "quantidade": 3}])
                set_item = next(item for item in listed if item["codigo"] == "A-FIT / B-FIT")
                self.assertEqual(set_item["quantidade"], 2)

    def test_export_json_uses_database_contents(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            container = self._build_container(root)
            with patch("app.interfaces.api.http.app.build_container", return_value=container):
                client = TestClient(create_app())
                self._authenticate(client)

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
