"""LojaSync Launcher — entry point.

Refactored from monolithic 600-line file into modular structure:
- app.bootstrap.launcher.env    — configuration & defaults
- app.bootstrap.launcher.net    — networking utilities
- app.bootstrap.launcher.frontend — TS build & frontend serving

Usage: python launcher.py [--host HOST] [--backend-port PORT] ...
"""
from __future__ import annotations

import argparse
import importlib
import os
import subprocess
import sys
import threading
import time
import webbrowser
from contextlib import suppress
from typing import Any, Callable, Optional

import uvicorn

from app.interfaces.api.http.app import create_app

# Import refactored modules
from app.bootstrap.launcher.env import (
    DEFAULT_AUTH_ENABLED,
    DEFAULT_AUTH_PORT,
    DEFAULT_BACKEND_PORT,
    DEFAULT_BROWSER_HOST,
    DEFAULT_FRONTEND_PORT,
    DEFAULT_HOST,
    DEFAULT_LLM_BIND,
    DEFAULT_LLM_HOST,
    DEFAULT_LLM_MONITOR_ENABLED,
    DEFAULT_LLM_MONITOR_PORT,
    DEFAULT_LLM_PORT,
    ENGINE_DIR,
    FRONTEND_TS_DIR,
    PERFORMANCE_DEFAULTS,
    ROOT_DIR,
    _coerce_int,
    _param_value,
)
from app.bootstrap.launcher.net import (
    connect_host,
    guess_public_host,
    is_port_bindable,
    is_tcp_listening,
)
from app.bootstrap.launcher.frontend import (
    ensure_typescript_frontend_ready,
    make_http_server,
    typescript_frontend_is_available,
    _iter_files,
    _latest_mtime,
    locate_npm_command,
)


# ---------------------------------------------------------------------------
# Module discovery helper
# ---------------------------------------------------------------------------

_ENTRYPOINT_CANDIDATES = ("run", "start", "serve", "main")


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


# ---------------------------------------------------------------------------
# Launcher class
# ---------------------------------------------------------------------------

class Launcher:
    def __init__(
        self,
        host: str = DEFAULT_HOST,
        frontend_port: int = DEFAULT_FRONTEND_PORT,
        backend_port: int = DEFAULT_BACKEND_PORT,
        auth_port: int = DEFAULT_AUTH_PORT,
        auth_enabled: bool = DEFAULT_AUTH_ENABLED,
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
        self.auth_port = auth_port
        self.auth_enabled = auth_enabled
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
        self._auth_process: Optional[subprocess.Popen[str]] = None
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
        os.environ["LOJASYNC_AUTH_ENABLED"] = "1" if self.auth_enabled else "0"
        os.environ.setdefault("LOJASYNC_AUTH_HOST", self.host)
        os.environ.setdefault("LOJASYNC_AUTH_PORT", str(self.auth_port))
        os.environ.setdefault("LLM_HOST", self.llm_host)
        os.environ.setdefault("LLM_PORT", str(self.llm_port))
        if self._use_monitor_base_url:
            os.environ.setdefault("LLM_MONITOR_UPSTREAM_BASE_URL", f"http://{self.llm_host}:{self.llm_port}")
            os.environ.setdefault("LLM_BASE_URL", f"http://127.0.0.1:{self.llm_monitor_port}")
        else:
            os.environ.setdefault("LLM_BASE_URL", f"http://{self.llm_host}:{self.llm_port}")

        if self.host in {"0.0.0.0", "::"}:
            public_host = guess_public_host()
            print(f"[launcher] backend em {self.host}:{self.backend_port} (externo: http://{public_host}:{self.backend_port})")
        else:
            print(f"[launcher] backend em {self.host}:{self.backend_port}")
        uvicorn.run(create_app(), host=self.host, port=self.backend_port, reload=False, log_level="info")

    def _run_frontend(self) -> None:
        server = None
        last_exc: Optional[Exception] = None
        start_port = self.frontend_port
        backend_url = f"http://{connect_host(self.host)}:{self.backend_port}"
        for candidate in [start_port] + list(range(start_port + 1, start_port + 20)):
            try:
                server = make_http_server(self.host, candidate, backend_url)
                self.frontend_port = candidate
                break
            except OSError as exc:
                last_exc = exc
        if server is None:
            raise last_exc or RuntimeError("nao foi possivel subir frontend")
        self._frontend_server = server

        url = self._browser_url()
        print(f"[launcher] frontend legado redireciona para {url}")
        if typescript_frontend_is_available():
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

    def start_auth_async(self) -> None:
        if not self.auth_enabled:
            print("[launcher] auth desabilitado; aguardando comando explicito para conectar.")
            return
        if self.host in {"0.0.0.0", "::"}:
            public_host = guess_public_host()
            print(f"[launcher] auth em {self.host}:{self.auth_port} (externo: http://{public_host}:{self.auth_port})")
        else:
            print(f"[launcher] auth em {self.host}:{self.auth_port}")
        command = [
            sys.executable,
            "-m",
            "uvicorn",
            "app.interfaces.auth_api.http.app:create_auth_app",
            "--factory",
            "--host",
            self.host,
            "--port",
            str(self.auth_port),
            "--log-level",
            "info",
        ]
        self._auth_process = subprocess.Popen(command, cwd=str(ROOT_DIR), env=os.environ.copy(), text=True)

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
        if self._auth_process is not None:
            with suppress(Exception):
                self._auth_process.terminate()
                self._auth_process.wait(timeout=5)
            if self._auth_process.poll() is None:
                with suppress(Exception):
                    self._auth_process.kill()
        for thread in (
            self._frontend_thread,
            self._backend_thread,
            self._llm_thread,
            self._llm_monitor_thread,
        ):
            if thread and thread.is_alive():
                thread.join(timeout=2)

    def run(self) -> None:
        ensure_typescript_frontend_ready(
            force_build=self.force_ts_build,
            skip_build=not self.prepare_ts_frontend,
        )

        if self.auth_enabled:
            auth_already_running = is_tcp_listening(self.host, self.auth_port)
            if auth_already_running:
                print(f"[launcher] auth ja ativo em {self.host}:{self.auth_port}; reutilizando.")
            elif is_port_bindable(self.host, self.auth_port):
                self.start_auth_async()
                time.sleep(0.4)
            else:
                print(
                    f"[launcher] porta do auth em uso ({self.host}:{self.auth_port}); "
                    "nao foi possivel iniciar outra instancia."
                )
        else:
            print("[launcher] auth remoto permanece desativado ate habilitacao explicita.")

        llm_already_running = is_tcp_listening(self.llm_host, self.llm_port)
        if llm_already_running:
            print(f"[launcher] LLM ja ativo em {self.llm_host}:{self.llm_port}; reutilizando.")
        elif is_port_bindable(self.llm_bind_host, self.llm_port):
            self.start_llm_async()
        else:
            print(
                f"[launcher] porta do LLM em uso ({self.llm_bind_host}:{self.llm_port}); "
                "nao foi possivel iniciar outra instancia."
            )

        self._use_monitor_base_url = False
        if self.llm_monitor_enabled:
            monitor_host = "127.0.0.1"
            monitor_running = is_tcp_listening(monitor_host, self.llm_monitor_port)
            if monitor_running:
                print(f"[launcher] monitor LLM ja ativo em {monitor_host}:{self.llm_monitor_port}; reutilizando.")
                self._use_monitor_base_url = True
            elif is_port_bindable(monitor_host, self.llm_monitor_port):
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


# ---------------------------------------------------------------------------
# CLI argument parser
# ---------------------------------------------------------------------------

def _parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Launcher do LojaSync")
    parser.add_argument("--host", default=DEFAULT_HOST, help="Host para os servidores")
    parser.add_argument("--frontend-port", type=int, default=DEFAULT_FRONTEND_PORT, help="Porta do frontend")
    parser.add_argument("--backend-port", type=int, default=DEFAULT_BACKEND_PORT, help="Porta do backend")
    parser.add_argument("--auth-port", type=int, default=DEFAULT_AUTH_PORT, help="Porta do servico de autenticacao")
    parser.add_argument("--enable-auth", action="store_true", help="Ativar o runtime de autenticacao e conectar o backend a ele")
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
        auth_port=args.auth_port,
        auth_enabled=args.enable_auth,
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


# ---------------------------------------------------------------------------
# Backward-compatible aliases (tests import these from launcher.*)
# ---------------------------------------------------------------------------
_ensure_typescript_frontend_ready = ensure_typescript_frontend_ready
_locate_npm_command = locate_npm_command
_make_http_server = make_http_server
_typescript_frontend_needs_build = typescript_frontend_is_available
