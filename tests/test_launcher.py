from __future__ import annotations

import http.client
import io
import tempfile
import threading
import time
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

import launcher


class LauncherFrontendPreparationTests(unittest.TestCase):
    def test_skips_typescript_preparation_when_npm_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            frontend_dir = Path(tmpdir)
            (frontend_dir / "package.json").write_text('{"name":"frontend-ts"}', encoding="utf-8")
            output = io.StringIO()

            with (
                patch.object(launcher, "FRONTEND_TS_DIR", frontend_dir),
                patch("launcher._locate_npm_command", return_value=None),
                redirect_stdout(output),
            ):
                launcher._ensure_typescript_frontend_ready()

            self.assertIn("npm nao encontrado no PATH; pulando preparacao do frontend-ts", output.getvalue())

    def test_force_build_still_requires_npm(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            frontend_dir = Path(tmpdir)
            (frontend_dir / "package.json").write_text('{"name":"frontend-ts"}', encoding="utf-8")

            with patch.object(launcher, "FRONTEND_TS_DIR", frontend_dir), patch("launcher._locate_npm_command", return_value=None):
                with self.assertRaisesRegex(RuntimeError, "npm nao encontrado no PATH"):
                    launcher._ensure_typescript_frontend_ready(force_build=True)


class LauncherFrontendServerTests(unittest.TestCase):
    def _start_server(self) -> tuple[object, int, threading.Thread]:
        server = launcher._make_http_server("127.0.0.1", 0, "http://127.0.0.1:8800")
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        time.sleep(0.05)
        return server, server.server_address[1], thread

    def test_frontend_port_redirects_to_backend_root(self) -> None:
        server, port, thread = self._start_server()
        self.addCleanup(server.server_close)
        self.addCleanup(thread.join, 2)
        self.addCleanup(server.shutdown)

        connection = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        self.addCleanup(connection.close)
        connection.request("GET", "/")
        response = connection.getresponse()
        body = response.read()

        self.assertEqual(response.status, 307)
        self.assertEqual(response.getheader("Location"), "http://127.0.0.1:8800/")
        self.assertEqual(body, b"")


class LauncherMainTests(unittest.TestCase):
    def test_main_exits_cleanly_with_actionable_message_when_force_build_has_no_npm(self) -> None:
        output = io.StringIO()

        with (
            patch("launcher.Launcher.run", side_effect=RuntimeError("npm nao encontrado no PATH; nao foi possivel preparar o frontend TypeScript.")),
            redirect_stdout(output),
        ):
            with self.assertRaises(SystemExit) as exc_info:
                launcher.main(["--force-ts-build"])

        self.assertEqual(exc_info.exception.code, 1)
        rendered = output.getvalue()
        self.assertIn("[launcher] erro: npm nao encontrado no PATH", rendered)
        self.assertIn("instale Node.js/npm e rode novamente com --force-ts-build", rendered)


if __name__ == "__main__":
    unittest.main()
def test_latest_mtime_returns_zero_for_missing_paths(tmp_path: Path) -> None:
    assert launcher._latest_mtime((tmp_path / "missing",)) == 0.0


def test_iter_files_collects_nested_files(tmp_path: Path) -> None:
    nested = tmp_path / "src" / "nested"
    nested.mkdir(parents=True)
    target = nested / "file.ts"
    target.write_text("export {};\n", encoding="utf-8")

    files = launcher._iter_files((tmp_path / "src",))

    assert files == [target]
