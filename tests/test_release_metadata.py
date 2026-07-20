from __future__ import annotations

import json
import re
import tempfile
import tomllib
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.interfaces.api.http.app import create_app


ROOT = Path(__file__).resolve().parents[1]


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class ReleaseMetadataTests(unittest.TestCase):
    def test_release_version_is_consistent_across_packaged_metadata(self) -> None:
        pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        version = pyproject["project"]["version"]

        package_json = _read_json(ROOT / "frontend-ts" / "package.json")
        package_lock = _read_json(ROOT / "frontend-ts" / "package-lock.json")
        versioned_openapi = _read_json(ROOT / "tools" / "agent" / "openapi.json")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")

        self.assertEqual(package_json["version"], version)
        self.assertEqual(package_lock["version"], version)
        self.assertEqual(package_lock["packages"][""]["version"], version)
        self.assertEqual(versioned_openapi["info"]["version"], version)
        self.assertRegex(readme, rf"Release atual: v{re.escape(version)}\b")

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

                self.assertEqual(client.app.version, version)
                self.assertEqual(client.app.openapi()["info"]["version"], version)
                self.assertEqual(client.get("/health").json()["version"], version)


if __name__ == "__main__":
    unittest.main()
