from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.application.auth.service import AuthService
from app.bootstrap.wiring.container import AppContainer
from app.infrastructure.persistence.files.auth_store import JsonAuthStore
from app.interfaces.api.http.app import create_app
from app.shared.config.settings import AppSettings
from tests.auth_test_support import AuthServiceConnectorStub


class AuthRoutesTests(unittest.TestCase):
    def _build_container(self, root: Path, *, auth_enabled: bool = True) -> AppContainer:
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
            auth_file=data_dir / "auth.json",
        )
        auth_store = JsonAuthStore(paths.auth_file, settings.auth_session_ttl_minutes)
        auth_service = AuthService(auth_store, settings.auth_password_min_length, settings.auth_cookie_name)
        auth_connector = AuthServiceConnectorStub(auth_service, enabled=auth_enabled)
        product_service = SimpleNamespace(list_products=lambda: [])
        return AppContainer(
            settings=settings,
            paths=paths,
            auth_connector=auth_connector,
            product_service=product_service,
            automation_service=None,
        )

    def test_auth_disabled_keeps_business_runtime_open(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            container = self._build_container(root, auth_enabled=False)
            with patch("app.interfaces.api.http.app.build_container", return_value=container):
                client = TestClient(create_app())

                session = client.get("/auth/session")
                self.assertEqual(session.status_code, 200)
                self.assertEqual(session.json()["auth_enabled"], False)

                products = client.get("/products")
                self.assertEqual(products.status_code, 200)

    def test_protected_routes_require_setup_then_authentication(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            container = self._build_container(root)
            with patch("app.interfaces.api.http.app.build_container", return_value=container):
                client = TestClient(create_app())

                blocked_before_setup = client.get("/products")
                self.assertEqual(blocked_before_setup.status_code, 403)
                self.assertEqual(blocked_before_setup.json()["code"], "setup_required")

                setup_response = client.post("/auth/bootstrap", json={"password": "senha-forte-123"})
                self.assertEqual(setup_response.status_code, 200)
                self.assertIn(container.settings.auth_cookie_name, setup_response.cookies)

                allowed_after_setup = client.get("/products")
                self.assertEqual(allowed_after_setup.status_code, 200)

                logout_response = client.post("/auth/logout")
                self.assertEqual(logout_response.status_code, 200)

                blocked_after_logout = client.get("/products")
                self.assertEqual(blocked_after_logout.status_code, 401)
                self.assertEqual(blocked_after_logout.json()["code"], "auth_required")

    def test_login_and_password_change_rotate_access(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            container = self._build_container(root)
            with patch("app.interfaces.api.http.app.build_container", return_value=container):
                client = TestClient(create_app())

                self.assertEqual(client.post("/auth/bootstrap", json={"password": "senha-forte-123"}).status_code, 200)
                self.assertEqual(
                    client.post(
                        "/auth/change-password",
                        json={"current_password": "senha-forte-123", "new_password": "nova-senha-456"},
                    ).status_code,
                    200,
                )

                after_change = client.get("/auth/session").json()
                self.assertFalse(after_change["authenticated"])

                old_login = client.post("/auth/login", json={"password": "senha-forte-123"})
                self.assertEqual(old_login.status_code, 401)

                new_login = client.post("/auth/login", json={"password": "nova-senha-456"})
                self.assertEqual(new_login.status_code, 200)
                self.assertEqual(client.get("/products").status_code, 200)


if __name__ == "__main__":
    unittest.main()
