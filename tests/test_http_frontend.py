from __future__ import annotations

import os
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.interfaces.api.http.app import _cors_origins, create_app


class _FrontendAssetParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.assets: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = dict(attrs)
        if tag == "script" and attr_map.get("type") == "module" and attr_map.get("src"):
            self.assets.append(attr_map["src"] or "")
        if tag == "link" and attr_map.get("rel") == "stylesheet" and attr_map.get("href"):
            href = attr_map["href"] or ""
            if href.startswith("/"):
                self.assets.append(href)


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

    def test_cors_uses_configured_origins_instead_of_wildcard_with_credentials(self) -> None:
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

            with (
                patch("app.interfaces.api.http.app.build_container", return_value=fake_container),
                patch.dict(os.environ, {"LOJASYNC_CORS_ORIGINS": "http://allowed.test"}, clear=False),
            ):
                client = TestClient(create_app())

                allowed = client.options(
                    "/health",
                    headers={
                        "Origin": "http://allowed.test",
                        "Access-Control-Request-Method": "GET",
                    },
                )
                blocked = client.options(
                    "/health",
                    headers={
                        "Origin": "http://blocked.test",
                        "Access-Control-Request-Method": "GET",
                    },
                )

                self.assertEqual(allowed.status_code, 200)
                self.assertEqual(allowed.headers["access-control-allow-origin"], "http://allowed.test")
                self.assertEqual(allowed.headers["access-control-allow-credentials"], "true")
                self.assertNotIn("access-control-allow-origin", blocked.headers)

    def test_cors_formats_ipv6_hosts_as_valid_origins(self) -> None:
        settings = SimpleNamespace(api_host="::1", auth_host="0.0.0.0", api_port=8800, auth_port=8810)
        container = SimpleNamespace(settings=settings)

        with patch.dict(os.environ, {"LOJASYNC_CORS_ORIGINS": "", "LOJASYNC_FRONTEND_PORT": "5173"}, clear=False):
            origins = _cors_origins(container)

        self.assertIn("http://[::1]:8800", origins)
        self.assertNotIn("http://::1:8800", origins)

    def test_bundled_frontend_index_references_existing_assets(self) -> None:
        dist_dir = Path(__file__).resolve().parents[1] / "frontend-ts" / "dist"
        index_file = dist_dir / "index.html"
        self.assertTrue(index_file.exists(), "frontend-ts/dist/index.html precisa estar versionado")

        parser = _FrontendAssetParser()
        parser.feed(index_file.read_text(encoding="utf-8"))

        self.assertGreaterEqual(len(parser.assets), 2)
        for asset in parser.assets:
            self.assertTrue(asset.startswith("/"), asset)
            asset_path = dist_dir / asset.lstrip("/")
            self.assertTrue(asset_path.exists(), f"asset referenciado nao existe: {asset}")

        with tempfile.TemporaryDirectory() as tmpdir:
            legacy_dir = Path(tmpdir) / "legacy"
            legacy_dir.mkdir(parents=True, exist_ok=True)
            (legacy_dir / "index.html").write_text("<!doctype html><title>Legacy</title>", encoding="utf-8")

            fake_paths = SimpleNamespace(web_ts_dist_dir=dist_dir, web_static_dir=legacy_dir)
            fake_container = SimpleNamespace(paths=fake_paths)

            with patch("app.interfaces.api.http.app.build_container", return_value=fake_container):
                client = TestClient(create_app())

                root_response = client.get("/")
                self.assertEqual(root_response.status_code, 200)
                self.assertIn("LojaSync", root_response.text)

                for asset in parser.assets:
                    asset_response = client.get(asset)
                    self.assertEqual(asset_response.status_code, 200, asset)


if __name__ == "__main__":
    unittest.main()
