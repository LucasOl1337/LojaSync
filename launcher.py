from __future__ import annotations

import argparse
import importlib
import os
import shutil
import socket
import subprocess
import sys
import threading
import time
import webbrowser
from contextlib import suppress
from http.server import SimpleHTTPRequestHandler
from pathlib import Path
from typing import Any, Callable, Optional

import uvicorn

from app.interfaces.api.http.app import create_app


ROOT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT_DIR
ENGINE_DIR = PROJECT_ROOT / "Legacy" / "engine"
FRONTEND_TS_DIR = ROOT_DIR / "frontend-ts"
FRONTEND_TS_DIST_DIR = FRONTEND_TS_DIR / "dist"
NODEJS_DIR = Path(r"C:\Program Files\nodejs")

for candidate in (ROOT_DIR, ENGINE_DIR):
    candidate_str = str(candidate)
    if candidate_str not in sys.path:
        sys.path.insert(0, candidate_str)

try:
    import webapp.parametros as _user_params  # type: ignore
except Exception:
    _user_params = None


_ENTRYPOINT_CANDIDATES = ("run", "start", "serve", "main")


def _coerce_int(value: Any, fallback: int) -> int:
    try:
        if value in (None, ""):
            raise ValueError
        return int(value)
    except (TypeError, ValueError):
        return fallback


def _coerce_bool(value: Any, fallback: bool) -> bool:
    if value in (None, ""):
        return fallback
    if isinstance(value, bool):
        return value
    raw = str(value).strip().lower()
    if raw in {"1", "true", "yes", "y", "on"}:
        return True
    if raw in {"0", "false", "no", "n", "off"}:
        return False
    return fallback


def _param_value(name: str, fallback: Any) -> Any:
    if _user_params and hasattr(_user_params, name):
        value = getattr(_user_params, name)
        if value not in (None, ""):
            return value
    return fallback


def _find_callable(module: Any, names: tuple[str, ...]) -> Optional[Callable[..., Any]]:
    for name in names:
        candidate = getattr(module, name, None)
        if callable(candidate):
            return candidate
    return None


def _maybe_call(func: Optional[Callable[..., Any]], *args: Any) -> None:
    if not callable(func):
        return
    try:
        func(*args)
    except TypeError:
        func()


def _guess_public_host() -> str:
    with suppress(Exception):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            return sock.getsockname()[0]
    return "127.0.0.1"


def _connect_host(host: str) -> str:
    return "127.0.0.1" if host in {"0.0.0.0", "::"} else host


def _is_tcp_listening(host: str, port: int, timeout: float = 0.25) -> bool:
    target_host = _connect_host(host)
    with suppress(Exception):
        with socket.create_connection((target_host, port), timeout=timeout):
            return True
    return False


def _is_port_bindable(host: str, port: int) -> bool:
    bind_host = "0.0.0.0" if host in {"0.0.0.0", "::"} else host
    family = socket.AF_INET6 if ":" in bind_host and bind_host != "0.0.0.0" else socket.AF_INET
    with suppress(Exception):
        with socket.socket(family, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind((bind_host, port))
            return True
    return False


def _make_http_server(host: str, port: int, backend_url: str):
    from http.server import ThreadingHTTPServer

    class FrontendHandler(SimpleHTTPRequestHandler):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(*args, **kwargs)

        def do_GET(self) -> None:  # pragma: no cover - exercised via launcher smoke test
            target_url = backend_url + self.path
            self.send_response(307)
            self.send_header("Location", target_url)
            self.send_header("Content-Length", "0")
            self.end_headers()

    handler_cls = FrontendHandler
    return ThreadingHTTPServer((host, port), handler_cls)


DEFAULT_HOST = os.getenv("LOJASYNC_HOST") or str(_param_value("HOST", "127.0.0.1"))
DEFAULT_FRONTEND_PORT = _coerce_int(
    os.getenv("LOJASYNC_FRONTEND_PORT"),
    _coerce_int(_param_value("FRONTEND_PORT", 5173), 5173),
)
DEFAULT_BACKEND_PORT = _coerce_int(
    os.getenv("LOJASYNC_BACKEND_PORT"),
    _coerce_int(_param_value("BACKEND_PORT", 8800), 8800),
)
DEFAULT_LLM_PORT = _coerce_int(
    os.getenv("LOJASYNC_LLM_PORT"),
    _coerce_int(_param_value("LLM_PORT", 8002), 8002),
)
DEFAULT_LLM_MONITOR_PORT = _coerce_int(
    os.getenv("LOJASYNC_LLM_MONITOR_PORT"),
    _coerce_int(_param_value("LLM_MONITOR_PORT", 5174), 5174),
)
DEFAULT_LLM_MONITOR_ENABLED = _coerce_bool(
    os.getenv("LOJASYNC_LLM_MONITOR_ENABLED"),
    True,
)
DEFAULT_LLM_HOST = os.getenv("LOJASYNC_LLM_HOST") or str(_param_value("LLM_HOST", DEFAULT_HOST))
DEFAULT_LLM_BIND = os.getenv("LOJASYNC_LLM_BIND", "0.0.0.0")
DEFAULT_BROWSER_HOST = os.getenv("LOJASYNC_BROWSER_HOST") or str(_param_value("BROWSER_OVERRIDE_HOST", "127.0.0.1"))

PERFORMANCE_DEFAULTS = {
    "LLM_DOC_CHUNK_CHARS": "16000",
    "LLM_INCLUDE_IMAGES_WITH_TEXT": "0",
    "PDF_RENDER_MAX_PAGES": "12",
    "PDF_RENDER_ZOOM": "1.5",
    "LLM_ROMANEIO_RETRY_VISION_MAX_PAGES": "4",
    "LLM_ROMANEIO_RETRY_VISION_ZOOM": "1.5",
}

TS_BUILD_INPUTS = (
    FRONTEND_TS_DIR / "index.html",
    FRONTEND_TS_DIR / "package.json",
    FRONTEND_TS_DIR / "package-lock.json",
    FRONTEND_TS_DIR / "tsconfig.json",
    FRONTEND_TS_DIR / "tsconfig.app.json",
    FRONTEND_TS_DIR / "vite.config.ts",
    FRONTEND_TS_DIR / "src",
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


def _typescript_frontend_needs_build() -> bool:
    if not FRONTEND_TS_DIR.exists():
        return False
    if not FRONTEND_TS_DIST_DIR.exists():
        return True
    dist_mtime = _latest_mtime((FRONTEND_TS_DIST_DIR,))
    source_mtime = _latest_mtime(TS_BUILD_INPUTS)
    return source_mtime > dist_mtime

def _typescript_frontend_is_available() -> bool:
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

def _locate_npm_command() -> Optional[str]:
    npm_cmd = shutil.which("npm")
    if npm_cmd:
        return npm_cmd

    for candidate in (NODEJS_DIR / "npm.cmd", NODEJS_DIR / "npm"):
        if candidate.exists():
            return str(candidate)

    return None


def _npm_environment(npm_cmd: str) -> dict[str, str]:
    env = os.environ.copy()
    node_dir = str(Path(npm_cmd).resolve().parent)
    current_path = env.get("PATH", "")
    env["PATH"] = node_dir if not current_path else f"{node_dir}{os.pathsep}{current_path}"
    return env
def _ensure_typescript_frontend_ready(force_build: bool = False, skip_build: bool = False) -> None:
    if skip_build or not FRONTEND_TS_DIR.exists():
        return

    npm_cmd = _locate_npm_command()
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
        install_cmd = [npm_cmd, "ci"] if package_lock.exists() else [npm_cmd, "install"]
        subprocess.run(install_cmd, cwd=str(FRONTEND_TS_DIR), check=True, env=_npm_environment(npm_cmd))

    if force_build or _typescript_frontend_needs_build():
        subprocess.run([npm_cmd, "run", "build"], cwd=str(FRONTEND_TS_DIR), check=True, env=_npm_environment(npm_cmd))
        subprocess.run(install_cmd, cwd=str(FRONTEND_TS_DIR), check=True, env=_npm_environment(npm_cmd))

    if force_build or _typescript_frontend_needs_build():
        subprocess.run([npm_cmd, "run", "build"], cwd=str(FRONTEND_TS_DIR), check=True, env=_npm_environment(npm_cmd))
    else:
        print("[launcher] frontend-ts/dist ja esta atualizado; pulando build.")


class Launcher:
    def __init__(
        self,
        host: str = DEFAULT_HOST,
        frontend_port: int = DEFAULT_FRONTEND_PORT,
        backend_port: int = DEFAULT_BACKEND_PORT,
        open_browser: bool = True,
        llm_port: int = DEFAULT_LLM_PORT,
        llm_monitor_port: int = DEFAULT_LLM_MONITOR_PORT,
        llm_monitor_enabled: bool = DEFAULT_LLM_MONITOR_ENABLED,
        llm_host: str = DEFAULT_LLM_HOST,
        llm_bind_host: str = DEFAULT_LLM_BIND,
        prepare_ts_frontend: bool = True,
        force_ts_build: bool = False,
    ) -> None:
        for key, value in PERFORMANCE_DEFAULTS.items():
            os.environ.setdefault(key, value)
        self.host = host
        self.frontend_port = frontend_port
        self.backend_port = backend_port
        self.open_browser = open_browser
        self.llm_port = llm_port
        self.llm_monitor_port = llm_monitor_port
        self.llm_monitor_enabled = llm_monitor_enabled
        self.llm_host = llm_host
        self.llm_bind_host = llm_bind_host
        self.prepare_ts_frontend = prepare_ts_frontend
        self.force_ts_build = force_ts_build

        self._frontend_server: Optional[Any] = None
        self._frontend_thread: Optional[threading.Thread] = None
        self._backend_thread: Optional[threading.Thread] = None
        self._llm_thread: Optional[threading.Thread] = None
        self._llm_monitor_thread: Optional[threading.Thread] = None
        self._use_monitor_base_url = bool(llm_monitor_enabled)

    def _browser_url(self) -> str:
        host = self.host
        if host in {"0.0.0.0", "::"}:
            host = DEFAULT_BROWSER_HOST or "127.0.0.1"
        return f"http://{host}:{self.backend_port}/"

    def _open_browser_delayed(self, url: str, delay: float = 1.2) -> None:
        time.sleep(delay)
        with suppress(Exception):
            webbrowser.open(url, new=2)

    def _run_backend(self) -> None:
        os.environ.setdefault("LLM_HOST", self.llm_host)
        os.environ.setdefault("LLM_PORT", str(self.llm_port))
        if self._use_monitor_base_url:
            os.environ.setdefault("LLM_MONITOR_UPSTREAM_BASE_URL", f"http://{self.llm_host}:{self.llm_port}")
            os.environ.setdefault("LLM_BASE_URL", f"http://127.0.0.1:{self.llm_monitor_port}")
        else:
            os.environ.setdefault("LLM_BASE_URL", f"http://{self.llm_host}:{self.llm_port}")

        if self.host in {"0.0.0.0", "::"}:
            public_host = _guess_public_host()
            print(f"[launcher] backend em {self.host}:{self.backend_port} (externo: http://{public_host}:{self.backend_port})")
        else:
            print(f"[launcher] backend em {self.host}:{self.backend_port}")
        uvicorn.run(create_app(), host=self.host, port=self.backend_port, reload=False, log_level="info")

    def _run_frontend(self) -> None:
        server = None
        last_exc: Optional[Exception] = None
        start_port = self.frontend_port
        backend_url = f"http://{_connect_host(self.host)}:{self.backend_port}"
        for candidate in [start_port] + list(range(start_port + 1, start_port + 20)):
            try:
                server = _make_http_server(self.host, candidate, backend_url)
                self.frontend_port = candidate
                break
            except OSError as exc:
                last_exc = exc
        if server is None:
            raise last_exc or RuntimeError("nao foi possivel subir frontend")
        self._frontend_server = server

        url = self._browser_url()
        print(f"[launcher] frontend legado redireciona para {url}")
        if _typescript_frontend_is_available():
            print(f"[launcher] frontend-ts principal em {url}")
        else:
            print("[launcher] frontend-ts indisponivel; o frontend legado segue acessivel em /legacy.")
        if self.open_browser:
            threading.Thread(
                target=self._open_browser_delayed,
                args=(url,),
                name="browser-opener",
                daemon=True,
            ).start()
        try:
            server.serve_forever()
        finally:
            server.server_close()

    def _run_llm(self) -> None:
        with suppress(ModuleNotFoundError):
            module = importlib.import_module("LLM3.launcher")
            entrypoint = _find_callable(module, _ENTRYPOINT_CANDIDATES) or getattr(module, "run", None)
            if entrypoint:
                print(
                    f"[launcher] LLM em {self.llm_bind_host}:{self.llm_port} (backend -> http://{self.llm_host}:{self.llm_port})"
                )
                _maybe_call(entrypoint, self.llm_bind_host, self.llm_port)
                return
        print("[launcher] LLM3.launcher nao encontrado; fluxos LLM ficam indisponiveis.")

    def _run_llm_monitor(self) -> None:
        os.environ.setdefault("LLM_HOST", self.llm_host)
        os.environ.setdefault("LLM_PORT", str(self.llm_port))
        os.environ.setdefault("LLM_MONITOR_HOST", "127.0.0.1")
        os.environ.setdefault("LLM_MONITOR_PORT", str(self.llm_monitor_port))
        os.environ.setdefault("LLM_MONITOR_UPSTREAM_BASE_URL", f"http://{self.llm_host}:{self.llm_port}")
        try:
            module = importlib.import_module("webapp.llm_monitor")
        except ModuleNotFoundError:
            print("[launcher] webapp.llm_monitor nao encontrado; monitor desabilitado.")
            return
        entrypoint = _find_callable(module, _ENTRYPOINT_CANDIDATES) or getattr(module, "run", None)
        if not entrypoint:
            print("[launcher] llm_monitor encontrado sem entrypoint valido.")
            return
        monitor_host = "127.0.0.1"
        print(f"[launcher] monitor LLM em {monitor_host}:{self.llm_monitor_port}")
        _maybe_call(entrypoint, monitor_host, self.llm_monitor_port)

    def start_backend_async(self) -> None:
        self._backend_thread = threading.Thread(target=self._run_backend, name="backend-thread", daemon=True)
        self._backend_thread.start()

    def start_frontend_async(self) -> None:
        self._frontend_thread = threading.Thread(target=self._run_frontend, name="frontend-thread", daemon=True)
        self._frontend_thread.start()

    def start_llm_async(self) -> None:
        self._llm_thread = threading.Thread(target=self._run_llm, name="llm-thread", daemon=True)
        self._llm_thread.start()

    def start_llm_monitor_async(self) -> None:
        self._llm_monitor_thread = threading.Thread(
            target=self._run_llm_monitor,
            name="llm-monitor-thread",
            daemon=True,
        )
        self._llm_monitor_thread.start()

    def shutdown(self) -> None:
        if self._frontend_server is not None:
            with suppress(Exception):
                self._frontend_server.shutdown()
        for thread in (
            self._frontend_thread,
            self._backend_thread,
            self._llm_thread,
            self._llm_monitor_thread,
        ):
            if thread and thread.is_alive():
                thread.join(timeout=2)

    def run(self) -> None:
        _ensure_typescript_frontend_ready(
            force_build=self.force_ts_build,
            skip_build=not self.prepare_ts_frontend,
        )

        llm_already_running = _is_tcp_listening(self.llm_host, self.llm_port)
        if llm_already_running:
            print(f"[launcher] LLM ja ativo em {self.llm_host}:{self.llm_port}; reutilizando.")
        elif _is_port_bindable(self.llm_bind_host, self.llm_port):
            self.start_llm_async()
        else:
            print(
                f"[launcher] porta do LLM em uso ({self.llm_bind_host}:{self.llm_port}); "
                "nao foi possivel iniciar outra instancia."
            )

        self._use_monitor_base_url = False
        if self.llm_monitor_enabled:
            monitor_host = "127.0.0.1"
            monitor_running = _is_tcp_listening(monitor_host, self.llm_monitor_port)
            if monitor_running:
                print(f"[launcher] monitor LLM ja ativo em {monitor_host}:{self.llm_monitor_port}; reutilizando.")
                self._use_monitor_base_url = True
            elif _is_port_bindable(monitor_host, self.llm_monitor_port):
                self.start_llm_monitor_async()
                self._use_monitor_base_url = True
            else:
                print(
                    f"[launcher] porta do monitor em uso ({monitor_host}:{self.llm_monitor_port}); "
                    "backend vai usar LLM direto."
                )

        self.start_backend_async()
        self.start_frontend_async()
        print("[launcher] servicos iniciados. Pressione CTRL+C para encerrar.")
        try:
            while True:
                time.sleep(0.5)
        except KeyboardInterrupt:
            print("\n[launcher] encerrando...")
            self.shutdown()


def _parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Launcher do LojaSync")
    parser.add_argument("--host", default=DEFAULT_HOST, help="Host para os servidores")
    parser.add_argument("--frontend-port", type=int, default=DEFAULT_FRONTEND_PORT, help="Porta do frontend")
    parser.add_argument("--backend-port", type=int, default=DEFAULT_BACKEND_PORT, help="Porta do backend")
    parser.add_argument("--llm-port", type=int, default=DEFAULT_LLM_PORT, help="Porta do servico LLM")
    parser.add_argument("--no-browser", action="store_true", help="Nao abrir navegador automaticamente")
    parser.add_argument("--disable-llm-monitor", action="store_true", help="Desabilitar monitor LLM")
    parser.add_argument(
        "--skip-ts-build",
        action="store_true",
        help="Nao instalar nem gerar o frontend TypeScript antes de iniciar",
    )
    parser.add_argument(
        "--force-ts-build",
        action="store_true",
        help="Forcar npm run build no frontend TypeScript antes de iniciar",
    )
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> None:
    args = _parse_args(argv)
    launcher = Launcher(
        host=args.host,
        frontend_port=args.frontend_port,
        backend_port=args.backend_port,
        llm_port=args.llm_port,
        open_browser=not args.no_browser,
        llm_monitor_enabled=not args.disable_llm_monitor,
        prepare_ts_frontend=not args.skip_ts_build,
        force_ts_build=args.force_ts_build,
    )
    try:
        launcher.run()
    except RuntimeError as exc:
        print(f"[launcher] erro: {exc}")
        if args.force_ts_build and "npm nao encontrado no PATH" in str(exc):
            print(
                "[launcher] instale Node.js/npm e rode novamente com --force-ts-build, "
                "ou remova essa flag para usar o frontend principal."
            )
        raise SystemExit(1) from exc


if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    except KeyboardInterrupt:
        print("\n[launcher] encerrado pelo usuario.")
