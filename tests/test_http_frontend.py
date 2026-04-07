from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.interfaces.api.http.app import create_app


class HttpFrontendRoutingTests(unittest.TestCase):
    def test_root_serves_ts_when_build_exists_and_keeps_legacy_available(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            ts_dir = root / "frontend-ts" / "dist"
            legacy_dir = root / "app" / "interfaces" / "webapp" / "static"
            ts_dir.mkdir(parents=True, exist_ok=True)
            legacy_dir.mkdir(parents=True, exist_ok=True)
            (ts_dir / "index.html").write_text("<!doctype html><title>TS</title>", encoding="utf-8")
            (legacy_dir / "index.html").write_text("<!doctype html><title>Legacy</title>", encoding="utf-8")

            fake_paths = SimpleNamespace(web_ts_dist_dir=ts_dir, web_static_dir=legacy_dir)
            fake_container = SimpleNamespace(paths=fake_paths)

            with patch("app.interfaces.api.http.app.build_container", return_value=fake_container):
                client = TestClient(create_app())

                root_response = client.get("/")
                legacy_response = client.get("/legacy/")
                ts_redirect = client.get("/ts/", follow_redirects=False)

                self.assertEqual(root_response.status_code, 200)
                self.assertIn("TS", root_response.text)
                self.assertEqual(legacy_response.status_code, 200)
                self.assertIn("Legacy", legacy_response.text)
                self.assertEqual(ts_redirect.status_code, 307)
                self.assertEqual(ts_redirect.headers["location"], "/")

    def test_api_routes_disable_browser_cache(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            ts_dir = root / "frontend-ts" / "dist"
            legacy_dir = root / "app" / "interfaces" / "webapp" / "static"
            ts_dir.mkdir(parents=True, exist_ok=True)
            legacy_dir.mkdir(parents=True, exist_ok=True)
            (ts_dir / "index.html").write_text("<!doctype html><title>TS</title>", encoding="utf-8")
            (legacy_dir / "index.html").write_text("<!doctype html><title>Legacy</title>", encoding="utf-8")

            fake_paths = SimpleNamespace(web_ts_dist_dir=ts_dir, web_static_dir=legacy_dir)
            fake_container = SimpleNamespace(paths=fake_paths)

            with patch("app.interfaces.api.http.app.build_container", return_value=fake_container):
                client = TestClient(create_app())

                response = client.get("/health")

                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.headers["cache-control"], "no-store, no-cache, must-revalidate, max-age=0")
                self.assertEqual(response.headers["pragma"], "no-cache")
                self.assertEqual(response.headers["expires"], "0")


if __name__ == "__main__":
    unittest.main()
