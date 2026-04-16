from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.application.auth.service import AuthService
from app.bootstrap.wiring.auth_container import AuthRuntimeContainer
from app.infrastructure.persistence.files.auth_store import JsonAuthStore
from app.interfaces.auth_api.http.app import create_auth_app
from app.shared.config.settings import AppSettings


class AuthRuntimeTests(unittest.TestCase):
    def _build_container(self, root: Path) -> AuthRuntimeContainer:
        data_dir = root / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        settings = AppSettings()
        paths = SimpleNamespace(data_dir=data_dir, auth_file=data_dir / "auth.json")
        auth_store = JsonAuthStore(paths.auth_file, settings.auth_session_ttl_minutes)
        auth_service = AuthService(auth_store, settings.auth_password_min_length, settings.auth_cookie_name)
        return AuthRuntimeContainer(settings=settings, paths=paths, auth_service=auth_service)

    def test_runtime_bootstrap_validate_and_change_password(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            container = self._build_container(root)
            with patch("app.interfaces.auth_api.http.app.build_auth_container", return_value=container):
                client = TestClient(create_auth_app())

                self.assertEqual(client.get("/internal/auth/status").json()["bootstrap_required"], True)

                bootstrap = client.post("/internal/auth/bootstrap", json={"password": "senha-forte-123"})
                self.assertEqual(bootstrap.status_code, 200)
                token = bootstrap.json()["token"]

                validated = client.post("/internal/auth/validate", json={"token": token})
                self.assertEqual(validated.status_code, 200)
                self.assertTrue(validated.json()["authenticated"])

                changed = client.post(
                    "/internal/auth/change-password",
                    json={
                        "token": token,
                        "current_password": "senha-forte-123",
                        "new_password": "nova-senha-456",
                    },
                )
                self.assertEqual(changed.status_code, 200)

                old_login = client.post("/internal/auth/login", json={"password": "senha-forte-123"})
                self.assertEqual(old_login.status_code, 401)

                new_login = client.post("/internal/auth/login", json={"password": "nova-senha-456"})
                self.assertEqual(new_login.status_code, 200)


if __name__ == "__main__":
    unittest.main()
