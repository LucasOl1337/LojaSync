from __future__ import annotations

import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient

from app.application.automation.service import AutomationService
from app.application.auth.service import AuthService
from app.application.products.service import ProductService
from app.bootstrap.wiring.auth_container import AuthRuntimeContainer
from app.bootstrap.wiring.container import AppContainer
from app.domain.products.entities import Product
from app.infrastructure.persistence.files.auth_store import JsonAuthStore
from app.infrastructure.persistence.sqlite import (
    SQLiteBrandRepository,
    SQLiteMarginSettingsStore,
    SQLiteMetricsStore,
    SQLiteProductRepository,
)
from app.interfaces.api.http.app import create_app
from app.interfaces.api.http.jobs.runtime import run_grade_extraction_job, run_import_job
from app.interfaces.api.http.jobs.store import (
    create_grade_job,
    create_import_job,
    remove_grade_job,
    remove_import_job,
)
from app.interfaces.auth_api.http.app import create_auth_app
from app.shared.config.settings import AppSettings
from tests.auth_test_support import AuthServiceConnectorStub


def _record_with_event(records: list[object], event: str) -> object:
    for record in records:
        if getattr(record, "event", None) == event:
            return record
    raise AssertionError(f"log event not found: {event}")


class LoggingCoverageTests(unittest.TestCase):
    def _build_main_container(self, root: Path, *, auth_enabled: bool = True) -> AppContainer:
        data_dir = root / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        ts_dir = root / "frontend-ts" / "dist"
        legacy_dir = root / "app" / "interfaces" / "webapp" / "static"
        ts_dir.mkdir(parents=True, exist_ok=True)
        legacy_dir.mkdir(parents=True, exist_ok=True)
        (ts_dir / "index.html").write_text("<!doctype html><title>TS</title>", encoding="utf-8")
        (legacy_dir / "index.html").write_text("<!doctype html><title>Legacy</title>", encoding="utf-8")

        settings = AppSettings()
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
        )
        auth_store = JsonAuthStore(paths.auth_file, settings.auth_session_ttl_minutes)
        auth_service = AuthService(auth_store, settings.auth_password_min_length, settings.auth_cookie_name)
        auth_connector = AuthServiceConnectorStub(auth_service, enabled=auth_enabled)
        products = SQLiteProductRepository(paths.database_file, paths.products_active_file, paths.products_history_file)
        brands = SQLiteBrandRepository(paths.database_file, paths.brands_file, settings.default_brands)
        margin = SQLiteMarginSettingsStore(paths.database_file, paths.margin_file, settings.default_margin)
        metrics = SQLiteMetricsStore(paths.database_file, paths.metrics_file)
        product_service = ProductService(products, brands, margin, metrics)
        automation_service = AutomationService(product_service, data_dir)
        return AppContainer(
            settings=settings,
            paths=paths,
            auth_connector=auth_connector,
            product_service=product_service,
            automation_service=automation_service,
        )

    def _build_auth_container(self, root: Path) -> AuthRuntimeContainer:
        data_dir = root / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        settings = AppSettings()
        paths = SimpleNamespace(data_dir=data_dir, auth_file=data_dir / "auth.json")
        auth_store = JsonAuthStore(paths.auth_file, settings.auth_session_ttl_minutes)
        auth_service = AuthService(auth_store, settings.auth_password_min_length, settings.auth_cookie_name)
        return AuthRuntimeContainer(settings=settings, paths=paths, auth_service=auth_service)

    def test_api_request_completion_log_includes_request_context(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            container = self._build_main_container(root, auth_enabled=False)
            with patch("app.interfaces.api.http.app.build_container", return_value=container):
                client = TestClient(create_app())

                with self.assertLogs("app.interfaces.api.http.app", level="INFO") as logs:
                    response = client.get("/health", headers={"x-request-id": "req-health-1"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["x-request-id"], "req-health-1")
        record = _record_with_event(logs.records, "http_request_completed")
        self.assertEqual(getattr(record, "request_id"), "req-health-1")
        self.assertEqual(getattr(record, "method"), "GET")
        self.assertEqual(getattr(record, "path"), "/health")
        self.assertEqual(getattr(record, "status_code"), 200)
        self.assertIsInstance(getattr(record, "duration_ms"), int)

    def test_protected_api_block_logs_reason_without_request_body(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            container = self._build_main_container(root)
            with patch("app.interfaces.api.http.app.build_container", return_value=container):
                client = TestClient(create_app())

                with self.assertLogs("app.interfaces.api.http.app", level="WARNING") as logs:
                    response = client.get("/products", headers={"x-request-id": "req-blocked-1"})

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.headers["x-request-id"], "req-blocked-1")
        blocked = _record_with_event(logs.records, "auth_request_blocked")
        self.assertEqual(getattr(blocked, "request_id"), "req-blocked-1")
        self.assertEqual(getattr(blocked, "path"), "/products")
        self.assertEqual(getattr(blocked, "status_code"), 403)
        self.assertEqual(getattr(blocked, "auth_reason"), "setup_required")
        self.assertNotIn("password", blocked.getMessage().lower())
        self.assertNotIn("token", blocked.getMessage().lower())

        completed = _record_with_event(logs.records, "http_request_completed")
        self.assertEqual(getattr(completed, "status_code"), 403)
        self.assertEqual(getattr(completed, "auth_reason"), "setup_required")

    def test_auth_runtime_logs_success_and_failed_login_without_secret_values(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            container = self._build_auth_container(root)
            with patch("app.interfaces.auth_api.http.app.build_auth_container", return_value=container):
                client = TestClient(create_auth_app())

                with self.assertLogs("app.interfaces.auth_api.http.routes", level="INFO") as logs:
                    bootstrap = client.post("/internal/auth/bootstrap", json={"password": "senha-forte-123"})

                self.assertEqual(bootstrap.status_code, 200)
                bootstrap_record = _record_with_event(logs.records, "auth_bootstrap_succeeded")
                self.assertEqual(getattr(bootstrap_record, "user"), "admin")
                self.assertNotIn("senha-forte-123", bootstrap_record.getMessage())

                with self.assertLogs("app.interfaces.auth_api.http.routes", level="WARNING") as failed_logs:
                    failed = client.post("/internal/auth/login", json={"password": "senha-errada-123"})

        self.assertEqual(failed.status_code, 401)
        failed_record = _record_with_event(failed_logs.records, "auth_login_failed")
        self.assertEqual(getattr(failed_record, "status_code"), 401)
        self.assertNotIn("senha-errada-123", failed_record.getMessage())

    def test_frontend_auth_route_logs_bootstrap_without_password(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            container = self._build_main_container(root)
            with patch("app.interfaces.api.http.app.build_container", return_value=container):
                client = TestClient(create_app())

                with self.assertLogs("app.interfaces.api.http.route_auth", level="INFO") as logs:
                    response = client.post(
                        "/auth/bootstrap",
                        json={"password": "senha-forte-123"},
                        headers={"x-request-id": "req-auth-bootstrap-1"},
                    )

        self.assertEqual(response.status_code, 200)
        record = _record_with_event(logs.records, "auth_bootstrap_succeeded")
        self.assertEqual(getattr(record, "request_id"), "req-auth-bootstrap-1")
        self.assertEqual(getattr(record, "user"), "admin")
        self.assertNotIn("senha-forte-123", record.getMessage())

    def test_product_create_logs_mutation_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            container = self._build_main_container(root, auth_enabled=False)
            with patch("app.interfaces.api.http.app.build_container", return_value=container):
                client = TestClient(create_app())

                with self.assertLogs("app.application.products.service", level="INFO") as logs:
                    response = client.post(
                        "/products",
                        json={
                            "nome": "Produto Logavel",
                            "codigo": "LOG-1",
                            "quantidade": 3,
                            "preco": "15,00",
                            "categoria": "Infantil",
                            "marca": "Marca L",
                        },
                    )

        self.assertEqual(response.status_code, 201)
        record = _record_with_event(logs.records, "product_created")
        self.assertEqual(getattr(record, "ordering_key"), response.json()["item"]["ordering_key"])
        self.assertEqual(getattr(record, "source_type"), "manual")
        self.assertEqual(getattr(record, "quantity"), 3)

    def test_automation_background_operation_logs_start_and_completion(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            service = AutomationService(product_service=Mock(), data_dir=Path(tmpdir))
            worker_started = threading.Event()
            worker_can_finish = threading.Event()

            def worker() -> dict[str, str]:
                worker_started.set()
                self.assertTrue(worker_can_finish.wait(2))
                return {"status": "success", "message": "ok", "job_kind": "catalog"}

            with self.assertLogs("app.application.automation.service", level="INFO") as logs:
                result = service._start_background_operation(
                    kind="catalog",
                    thread_name="test-automation-worker",
                    started_message="Teste iniciado",
                    started_phase="catalog",
                    worker=worker,
                )
                thread = service._thread
                self.assertIsNotNone(thread)
                self.assertTrue(worker_started.wait(2))
                worker_can_finish.set()
                thread.join(2)
                self.assertFalse(thread.is_alive())

        self.assertEqual(result["status"], "started")
        started = _record_with_event(logs.records, "automation_operation_started")
        self.assertEqual(getattr(started, "job_kind"), "catalog")
        completed = _record_with_event(logs.records, "automation_operation_completed")
        self.assertEqual(getattr(completed, "job_kind"), "catalog")
        self.assertEqual(getattr(completed, "status"), "success")

    def test_import_background_job_logs_completion_summary(self) -> None:
        class FakeImportService:
            def create_many(self, products: list[Product]) -> list[Product]:
                return products

        job = create_import_job()
        self.addCleanup(remove_import_job, job.job_id)

        local_payload = {
            "total_rows": 1,
            "total_itens": 1,
            "remessa_quantity": 2,
            "quantity_matches_remessa": True,
            "document_total_products": "40,00",
            "document_total_note": None,
            "extracted_total_products": "40,00",
            "products_value_matches_document": True,
            "items": [
                {
                    "nome": "CAMISETA",
                    "codigo": "C20",
                    "quantidade": 2,
                    "preco": "20,00",
                }
            ],
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch(
                "app.interfaces.api.http.jobs.runtime.parse_local_romaneio_experiment",
                return_value=local_payload,
            ):
                with self.assertLogs("app.interfaces.api.http.jobs.runtime", level="INFO") as logs:
                    run_import_job(
                        job_id=job.job_id,
                        contents=b"fake-pdf",
                        filename="romaneio.pdf",
                        content_type="application/pdf",
                        service=FakeImportService(),
                        data_dir=Path(tmpdir),
                    )

        record = _record_with_event(logs.records, "import_job_completed")
        self.assertEqual(getattr(record, "job_id"), job.job_id)
        self.assertEqual(getattr(record, "selected_source"), "local")
        self.assertEqual(getattr(record, "imported_items"), 1)
        self.assertEqual(getattr(record, "llm_chat_calls"), 0)

    def test_grade_extraction_job_logs_completion_summary(self) -> None:
        class FakeResponse:
            def raise_for_status(self) -> None:
                return None

            def json(self) -> dict[str, object]:
                return {"documents": [{"name": "nota.txt", "content": "grades"}], "images": []}

        class FakeClient:
            def __init__(self, *_args: object, **_kwargs: object) -> None:
                pass

            def __enter__(self) -> "FakeClient":
                return self

            def __exit__(self, *_args: object) -> None:
                return None

            def post(self, *_args: object, **_kwargs: object) -> FakeResponse:
                return FakeResponse()

        class FakeGradeService:
            def update_grades_by_identifier(self, **_kwargs: object) -> object:
                return object()

        job = create_grade_job()
        self.addCleanup(remove_grade_job, job.job_id)

        with (
            patch("app.interfaces.api.http.jobs.runtime.httpx.Client", FakeClient),
            patch(
                "app.interfaces.api.http.jobs.runtime.post_llm_chat",
                return_value=('{"items":[{"codigo":"C20","grades":{"P":2}}]}', None),
            ),
        ):
            with self.assertLogs("app.interfaces.api.http.jobs.runtime", level="INFO") as logs:
                run_grade_extraction_job(
                    job_id=job.job_id,
                    contents=b"fake-pdf",
                    filename="nota.pdf",
                    content_type="application/pdf",
                    service=FakeGradeService(),
                )

        record = _record_with_event(logs.records, "grade_extraction_job_completed")
        self.assertEqual(getattr(record, "job_id"), job.job_id)
        self.assertEqual(getattr(record, "parsed_items"), 1)
        self.assertEqual(getattr(record, "updated_products"), 1)
