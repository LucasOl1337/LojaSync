"""LojaSync Launcher — Frontend build & serving utilities.

Extracted from launcher.py to isolate TS frontend build logic.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional

from .env import (
    FRONTEND_TS_DIR,
    FRONTEND_TS_DIST_DIR,
    NODEJS_DIR,
    TS_BUILD_INPUTS,
)


def _iter_files(paths: tuple[Path, ...]) -> list[Path]:
    files: list[Path] = []
    for path in paths:
        if not path.exists():
            continue
        if path.is_file():
            files.append(path)
            continue
        files.extend(candidate for candidate in path.rglob("*") if candidate.is_file())
    return files


def _latest_mtime(paths: tuple[Path, ...]) -> float:
    mtimes = [candidate.stat().st_mtime for candidate in _iter_files(paths)]
    return max(mtimes, default=0.0)


def typescript_frontend_needs_build() -> bool:
    if not FRONTEND_TS_DIR.exists():
        return False
    if not FRONTEND_TS_DIST_DIR.exists():
        return True
    dist_mtime = _latest_mtime((FRONTEND_TS_DIST_DIR,))
    source_mtime = _latest_mtime(TS_BUILD_INPUTS)
    return source_mtime > dist_mtime


def typescript_frontend_is_available() -> bool:
    return (FRONTEND_TS_DIST_DIR / "index.html").exists()


def _run_command(command: list[str], cwd: Path, step_name: str) -> None:
    print(f"[launcher] {step_name}: {' '.join(command)}")
    try:
        subprocess.run(command, cwd=str(cwd), check=True)
    except FileNotFoundError as exc:
        missing = command[0]
        raise RuntimeError(f"{missing} nao encontrado no PATH; nao foi possivel preparar o frontend TypeScript.") from exc
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"falha ao executar {step_name} (codigo {exc.returncode}).") from exc


def locate_npm_command() -> Optional[str]:
    npm_cmd = shutil.which("npm")
    if npm_cmd:
        return npm_cmd
    for candidate in (NODEJS_DIR / "npm.cmd", NODEJS_DIR / "npm"):
        if candidate.exists():
            return str(candidate)
    return None


def npm_environment(npm_cmd: str) -> dict[str, str]:
    env = os.environ.copy()
    node_dir = str(Path(npm_cmd).resolve().parent)
    current_path = env.get("PATH", "")
    env["PATH"] = node_dir if not current_path else f"{node_dir}{os.pathsep}{current_path}"
    return env


def ensure_typescript_frontend_ready(force_build: bool = False, skip_build: bool = False) -> None:
    if skip_build or not FRONTEND_TS_DIR.exists():
        return

    npm_cmd = locate_npm_command()
    if not npm_cmd:
        if force_build:
            raise RuntimeError("npm nao encontrado no PATH; nao foi possivel preparar o frontend TypeScript.")
        print(
            "[launcher] npm nao encontrado no PATH; pulando preparacao do frontend-ts. "
            "O frontend principal continua disponivel, mas /ts pode ficar indisponivel ou desatualizado."
        )
        return

    package_lock = FRONTEND_TS_DIR / "package-lock.json"
    package_json = FRONTEND_TS_DIR / "package.json"
    node_modules = FRONTEND_TS_DIR / "node_modules"

    install_cmd = [npm_cmd, "ci"] if package_lock.exists() else [npm_cmd, "install"]

    needs_install = not node_modules.exists()
    if not needs_install and package_lock.exists():
        lock_mtime = package_lock.stat().st_mtime
        installed_mtime = _latest_mtime((node_modules,))
        needs_install = installed_mtime < lock_mtime
    elif not needs_install and package_json.exists():
        package_mtime = package_json.stat().st_mtime
        installed_mtime = _latest_mtime((node_modules,))
        needs_install = installed_mtime < package_mtime

    if needs_install:
        subprocess.run(install_cmd, cwd=str(FRONTEND_TS_DIR), check=True, env=npm_environment(npm_cmd))

    if force_build or typescript_frontend_needs_build():
        subprocess.run([npm_cmd, "run", "build"], cwd=str(FRONTEND_TS_DIR), check=True, env=npm_environment(npm_cmd))
    else:
        print("[launcher] frontend-ts/dist ja esta atualizado; pulando build.")


# ---------------------------------------------------------------------------
# Simple HTTP frontend server (legacy redirect)
# ---------------------------------------------------------------------------

from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer


def make_http_server(host: str, port: int, backend_url: str):
    class FrontendHandler(SimpleHTTPRequestHandler):
        def do_GET(self) -> None:
            target_url = backend_url + self.path
            self.send_response(307)
            self.send_header("Location", target_url)
            self.send_header("Content-Length", "0")
            self.end_headers()

    return ThreadingHTTPServer((host, port), FrontendHandler)
