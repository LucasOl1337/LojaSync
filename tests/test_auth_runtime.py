from __future__ import annotations

import tempfile
import unittest
import json
import sqlite3
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.application.auth.service import AuthService
from app.bootstrap.wiring.auth_container import AuthRuntimeContainer
from app.infrastructure.persistence.sqlite import SQLiteAuthStore
from app.interfaces.auth_api.http.app import create_auth_app
from app.shared.config.settings import AppSettings


class AuthRuntimeTests(unittest.TestCase):
    def _build_container(self, root: Path) -> AuthRuntimeContainer:
        data_dir = root / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        settings = AppSettings()
        paths = SimpleNamespace(
            data_dir=data_dir,
            database_file=data_dir / "lojasync.db",
            auth_file=data_dir / "auth.json",
        )
        auth_store = SQLiteAuthStore(paths.database_file, paths.auth_file, settings.auth_session_ttl_minutes)
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

    def test_sqlite_auth_store_migrates_legacy_json_and_becomes_source_of_truth(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            db_file = root / "lojasync.db"
            auth_file = root / "auth.json"
            auth_file.write_text(
                json.dumps(
                    {
                        "password_hash": "hash-legado",
                        "password_salt": "salt-legado",
                        "secret_key": "secret-legado",
                        "session_ttl_minutes": 45,
                        "password_updated_at": 123.5,
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            store = SQLiteAuthStore(db_file, auth_file, session_ttl_minutes=720)
            migrated = store.load()
            auth_file.unlink()
            reloaded = SQLiteAuthStore(db_file, auth_file, session_ttl_minutes=720).load()

            self.assertEqual(migrated.password_hash, "hash-legado")
            self.assertEqual(migrated.password_salt, "salt-legado")
            self.assertEqual(migrated.secret_key, "secret-legado")
            self.assertEqual(migrated.session_ttl_minutes, 45)
            self.assertEqual(migrated.password_updated_at, 123.5)
            self.assertEqual(reloaded, migrated)

            connection = sqlite3.connect(db_file)
            try:
                row = connection.execute("SELECT value_json FROM app_settings WHERE key = 'auth'").fetchone()
            finally:
                connection.close()

            self.assertIsNotNone(row)
            self.assertEqual(json.loads(row[0])["secret_key"], "secret-legado")


if __name__ == "__main__":
    unittest.main()
