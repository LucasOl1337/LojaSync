"""Launcher utilitário para o protótipo web do LojaSync.

Responsabilidades principais:
- Inicializar (ou futuramente orquestrar) backend e frontend.
- Servir o protótipo estático em ``index.html`` numa porta local.
- Expor um CLI simples para configurar host/portas e abertura automática do navegador.

Interfaces esperadas (e opcionais) em ``backend.py`` e ``frontend.py``:
- Funções nomeadas entre ``run``, ``start``, ``serve`` ou ``main``.
  Cada função pode aceitar nenhum argumento ou (host, port).
- Opcionalmente, funções ``ensure_dependencies()`` para instalação/verificação de requisitos.

Caso os módulos não existam ou ainda não exponham os entrypoints, o launcher
utiliza fallbacks seguros (por exemplo, um servidor HTTP estático para o frontend).
"""
from __future__ import annotations

import argparse
import importlib
import os
import socket
import sys
import threading
import time
import webbrowser
from contextlib import suppress
from functools import partial
from http.server import SimpleHTTPRequestHandler
from pathlib import Path
from socketserver import ThreadingMixIn
from typing import Any, Callable, Optional

try:  # Prefer parâmetros customizados quando disponíveis
    from . import parametros as _user_params  # type: ignore
except ImportError:  # pragma: no cover - arquivo opcional
    _user_params = None


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


def _param_int(name: str, fallback: int) -> int:
    return _coerce_int(_param_value(name, fallback), fallback)


def _resolve_root_dir() -> Path:
    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
        if base.name.lower() == "_internal":
            base = base.parent
        return base
    return Path(__file__).resolve().parent


ROOT_DIR = _resolve_root_dir()

DEFAULT_HOST = os.getenv("LOJASYNC_HOST") or str(_param_value("HOST", "127.0.0.1"))
DEFAULT_FRONTEND_PORT = _coerce_int(
    os.getenv("LOJASYNC_FRONTEND_PORT"),
    _param_int("FRONTEND_PORT", 5173),
)
DEFAULT_BACKEND_PORT = _coerce_int(
    os.getenv("LOJASYNC_BACKEND_PORT"),
    _param_int("BACKEND_PORT", 8800),
)
DEFAULT_LLM_PORT = _coerce_int(
    os.getenv("LOJASYNC_LLM_PORT"),
    _param_int("LLM_PORT", 8002),
)
DEFAULT_LLM_MONITOR_PORT = _coerce_int(
    os.getenv("LOJASYNC_LLM_MONITOR_PORT"),
    _param_int("LLM_MONITOR_PORT", 5174),
)
DEFAULT_LLM_MONITOR_ENABLED = _coerce_bool(
    os.getenv("LOJASYNC_LLM_MONITOR_ENABLED"),
    True,
)
DEFAULT_LLM_HOST = os.getenv("LOJASYNC_LLM_HOST") or str(
    _param_value("LLM_HOST", DEFAULT_HOST)
)
DEFAULT_LLM_BIND = os.getenv("LOJASYNC_LLM_BIND", "0.0.0.0")
DEFAULT_BROWSER_HOST = os.getenv("LOJASYNC_BROWSER_HOST") or str(
    _param_value("BROWSER_OVERRIDE_HOST", "127.0.0.1")
)

PERFORMANCE_DEFAULTS = {
    "LLM_DOC_CHUNK_CHARS": "16000",
    "LLM_INCLUDE_IMAGES_WITH_TEXT": "0",
    "PDF_RENDER_MAX_PAGES": "12",
    "PDF_RENDER_ZOOM": "1.5",
    "LLM_ROMANEIO_RETRY_VISION_MAX_PAGES": "4",
    "LLM_ROMANEIO_RETRY_VISION_ZOOM": "1.5",
}


def _apply_performance_defaults() -> None:
    for key, value in PERFORMANCE_DEFAULTS.items():
        os.environ.setdefault(key, value)

if getattr(sys, "frozen", False):
    pyinstaller_tmp = Path(getattr(sys, "_MEIPASS", ROOT_DIR))
    candidates = [pyinstaller_tmp, pyinstaller_tmp.parent, ROOT_DIR, ROOT_DIR.parent]
    for candidate in candidates:
        candidate_str = str(candidate)
        if candidate_str not in sys.path:
            sys.path.insert(0, candidate_str)
else:
    parent_dir = ROOT_DIR.parent
    if str(parent_dir) not in sys.path:
        sys.path.insert(0, str(parent_dir))

_ENTRYPOINT_CANDIDATES = ("run", "start", "serve", "main")
_DEPENDENCY_HOOKS = ("ensure_dependencies", "install_dependencies")

def _is_missing_target_module(exc: ModuleNotFoundError, module_name: str, package: Optional[str]) -> bool:
    if module_name.startswith("."):
        if not package:
            return True
        full = f"{package}{module_name}"
        return exc.name in {package, full}
    root = module_name.split(".")[0]
    return exc.name in {module_name, root}


def _import_optional_module(
    module_name: str,
    *,
    package_candidates: Optional[list[str]] = None,
    absolute_candidates: Optional[list[str]] = None,
) -> tuple[Optional[Any], Optional[ModuleNotFoundError]]:
    packages = [p for p in (package_candidates or []) if p]
    absolutes = [m for m in (absolute_candidates or []) if m]

    attempts: list[tuple[str, Optional[str]]] = []
    for package in packages:
        attempts.append((module_name, package))
    for absolute in absolutes:
        attempts.append((absolute, None))

    for name, package in attempts:
        try:
            if package:
                return importlib.import_module(name, package=package), None
            return importlib.import_module(name), None
        except ModuleNotFoundError as exc:
            if _is_missing_target_module(exc, name, package):
                continue
            return None, exc

    return None, None


def _print_install_hint() -> None:
    req_abs = str((ROOT_DIR / "requirements.txt").resolve())
    print('[launcher] instale as dependências do webapp com um destes comandos:')
    print('[launcher] - na raiz do projeto: python -m pip install -r "engine/webapp/requirements.txt"')
    print(f'[launcher] - dentro de engine/webapp: python -m pip install -r "{req_abs}"')


def _guess_public_host() -> str:
    with suppress(Exception):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            return sock.getsockname()[0]
    return "127.0.0.1"


class _ThreadingHTTPServer(ThreadingMixIn, socket.socket.__class__):
    """Placeholder type definition.

    OBS: usado apenas para tipagem. A implementação real aparece na factory
    ``_make_http_server`` que instancia ``ThreadingMixIn`` + ``HTTPServer``.
    """


def _make_http_server(host: str, port: int) -> Any:
    """Cria um servidor HTTP threaded apontando para ``webapp/``.

    Utiliza ``SimpleHTTPRequestHandler`` com diretório fixado no protótipo
    (``webapp/``). Caso a porta já esteja em uso, levanta ``OSError``.
    """

    from http.server import ThreadingHTTPServer

    handler_cls = partial(SimpleHTTPRequestHandler, directory=str(ROOT_DIR))
    return ThreadingHTTPServer((host, port), handler_cls)


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
        # Tenta com os argumentos fornecidos; se falhar por assinatura, chama sem nada.
        func(*args)
    except TypeError:
        func()


class Launcher:
    """Orquestra backend e frontend para o protótipo web."""

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
    ) -> None:
        _apply_performance_defaults()
        self.host = host
        self.frontend_port = frontend_port
        self.backend_port = backend_port
        self.open_browser = open_browser
        self.llm_port = llm_port
        self.llm_monitor_port = llm_monitor_port
        self.llm_monitor_enabled = llm_monitor_enabled
        self.llm_host = llm_host
        self.llm_bind_host = llm_bind_host

        self._frontend_server: Optional[Any] = None
        self._frontend_thread: Optional[threading.Thread] = None
        self._backend_thread: Optional[threading.Thread] = None
        self._llm_thread: Optional[threading.Thread] = None
        self._llm_monitor_thread: Optional[threading.Thread] = None

    # ------------------------------------------------------------------
    # Backend
    # ------------------------------------------------------------------
    def _load_backend(self) -> Optional[Any]:
        module, err = _import_optional_module(
            ".backend",
            package_candidates=[__package__ or "", "webapp"],
            absolute_candidates=["webapp.backend"],
        )
        if err is not None:
            missing = err.name or "dependência desconhecida"
            print(f"[launcher] backend indisponível: dependência ausente ({missing}).")
            _print_install_hint()
            return None
        return module

    def _ensure_backend_dependencies(self, module: Any) -> None:
        hook = _find_callable(module, _DEPENDENCY_HOOKS)
        _maybe_call(hook)

    def _run_backend(self) -> None:
        os.environ.setdefault("LLM_HOST", self.llm_host)
        os.environ.setdefault("LLM_PORT", str(self.llm_port))
        if self.llm_monitor_enabled:
            os.environ.setdefault(
                "LLM_MONITOR_UPSTREAM_BASE_URL",
                f"http://{self.llm_host}:{self.llm_port}",
            )
            os.environ.setdefault("LLM_BASE_URL", f"http://127.0.0.1:{self.llm_monitor_port}")
        else:
            os.environ.setdefault("LLM_BASE_URL", f"http://{self.llm_host}:{self.llm_port}")

        module = self._load_backend()
        if module is None:
            return

        self._ensure_backend_dependencies(module)
        entrypoint = _find_callable(module, _ENTRYPOINT_CANDIDATES)
        if entrypoint is None:
            print("[launcher] backend.py encontrado mas nenhum entrypoint válido foi exposto.")
            return

        if self.host in {"0.0.0.0", "::"}:
            public_host = _guess_public_host()
            print(
                f"[launcher] iniciando backend em {self.host}:{self.backend_port} (acesso externo: http://{public_host}:{self.backend_port})..."
            )
        else:
            print(f"[launcher] iniciando backend em {self.host}:{self.backend_port}...")
        _maybe_call(entrypoint, self.host, self.backend_port)

    def start_backend_async(self) -> None:
        self._backend_thread = threading.Thread(
            target=self._run_backend,
            name="backend-thread",
            daemon=True,
        )
        self._backend_thread.start()

    def _load_llm_monitor(self) -> Optional[Any]:
        module, err = _import_optional_module(
            ".llm_monitor",
            package_candidates=[__package__ or "", "webapp"],
            absolute_candidates=["webapp.llm_monitor"],
        )
        if err is not None:
            missing = err.name or "dependência desconhecida"
            print(f"[launcher] llm_monitor indisponível: dependência ausente ({missing}).")
            _print_install_hint()
            return None
        return module

    def _run_llm_monitor(self) -> None:
        os.environ.setdefault("LLM_HOST", self.llm_host)
        os.environ.setdefault("LLM_PORT", str(self.llm_port))
        os.environ.setdefault("LLM_MONITOR_HOST", "127.0.0.1")
        os.environ.setdefault("LLM_MONITOR_PORT", str(self.llm_monitor_port))
        os.environ.setdefault(
            "LLM_MONITOR_UPSTREAM_BASE_URL",
            f"http://{self.llm_host}:{self.llm_port}",
        )

        module = self._load_llm_monitor()
        if module is None:
            return

        entrypoint = _find_callable(module, _ENTRYPOINT_CANDIDATES)
        if entrypoint is None:
            print("[launcher] llm_monitor.py encontrado mas nenhum entrypoint válido foi exposto.")
            return

        monitor_host = self.host
        if monitor_host not in {"127.0.0.1", "0.0.0.0", "::"}:
            monitor_host = "127.0.0.1"
        print(f"[launcher] iniciando LLM monitor em {monitor_host}:{self.llm_monitor_port}...")
        _maybe_call(entrypoint, monitor_host, self.llm_monitor_port)

    def start_llm_monitor_async(self) -> None:
        self._llm_monitor_thread = threading.Thread(
            target=self._run_llm_monitor,
            name="llm-monitor-thread",
            daemon=True,
        )
        self._llm_monitor_thread.start()

    # ------------------------------------------------------------------
    # LLM service (romaneio extractor)
    # ------------------------------------------------------------------
    def _load_llm(self) -> Optional[Any]:
        with suppress(ModuleNotFoundError):
            return importlib.import_module("LLM3.launcher")
        return None

    def _run_llm(self) -> None:
        module = self._load_llm()
        if module is None:
            print("[launcher] LLM3.launcher não localizado – fluxo de romaneio indisponível.")
            return

        entrypoint = _find_callable(module, _ENTRYPOINT_CANDIDATES)
        if entrypoint is None:
            entrypoint = getattr(module, "run", None)

        if entrypoint is None:
            print("[launcher] LLM3.launcher encontrado mas sem entrypoint válido.")
            return

        descriptor = self.llm_bind_host
        if self.llm_bind_host in {"0.0.0.0", "::"}:
            descriptor = _guess_public_host()
        print(
            f"[launcher] iniciando serviço LLM em {self.llm_bind_host}:{self.llm_port} (acesso pelo backend via http://{self.llm_host}:{self.llm_port})..."
        )
        _maybe_call(entrypoint, self.llm_bind_host, self.llm_port)

    def start_llm_async(self) -> None:
        self._llm_thread = threading.Thread(
            target=self._run_llm,
            name="llm-thread",
            daemon=True,
        )
        self._llm_thread.start()

    # ------------------------------------------------------------------
    # Frontend
    # ------------------------------------------------------------------
    def _load_frontend(self) -> Optional[Any]:
        module, err = _import_optional_module(
            ".frontend",
            package_candidates=[__package__ or "", "webapp"],
            absolute_candidates=["webapp.frontend"],
        )
        if err is not None:
            missing = err.name or "dependência desconhecida"
            print(f"[launcher] frontend indisponível: dependência ausente ({missing}).")
            _print_install_hint()
            return None
        return module

    def _ensure_frontend_dependencies(self, module: Any) -> None:
        hook = _find_callable(module, _DEPENDENCY_HOOKS)
        _maybe_call(hook)

    def _browser_url(self) -> str:
        host = self.host
        if self.host in {"0.0.0.0", "::"}:
            host = DEFAULT_BROWSER_HOST or "127.0.0.1"
        return f"http://{host}:{self.frontend_port}"

    def _run_frontend_fallback(self) -> None:
        server = None
        last_exc = None
        start_port = self.frontend_port
        for candidate in [start_port] + list(range(start_port + 1, start_port + 20)):
            try:
                server = _make_http_server(self.host, candidate)
                self.frontend_port = candidate
                break
            except OSError as exc:
                last_exc = exc
        if server is None:
            raise last_exc  # type: ignore[misc]
        self._frontend_server = server

        url = self._browser_url()
        print(f"[launcher] servindo protótipo estático em {url}")

        if self.open_browser:
            threading.Thread(
                target=lambda: self._open_browser_delayed(url),
                name="browser-opener",
                daemon=True,
            ).start()

        try:
            server.serve_forever()
        finally:
            server.server_close()

    def _run_frontend(self) -> None:
        module = self._load_frontend()
        if module is None:
            self._run_frontend_fallback()
            return

        self._ensure_frontend_dependencies(module)
        entrypoint = _find_callable(module, _ENTRYPOINT_CANDIDATES)

        if entrypoint is None:
            print("[launcher] frontend.py não expõe entrypoint; usando fallback estático.")
            self._run_frontend_fallback()
            return

        if self.host in {"0.0.0.0", "::"}:
            public_host = _guess_public_host()
            print(
                f"[launcher] iniciando frontend customizado em {self.host}:{self.frontend_port} (acesso externo: http://{public_host}:{self.frontend_port})..."
            )
        else:
            print(f"[launcher] iniciando frontend customizado em {self.host}:{self.frontend_port}...")
        url = self._browser_url()
        if self.open_browser:
            threading.Thread(
                target=lambda: self._open_browser_delayed(url),
                name="browser-opener",
                daemon=True,
            ).start()
        _maybe_call(entrypoint, self.host, self.frontend_port)

    def start_frontend_async(self) -> None:
        self._frontend_thread = threading.Thread(
            target=self._run_frontend,
            name="frontend-thread",
            daemon=True,
        )
        self._frontend_thread.start()

    # ------------------------------------------------------------------
    # Utilidades
    # ------------------------------------------------------------------
    def _open_browser_delayed(self, url: str, delay: float = 1.2) -> None:
        time.sleep(delay)
        try:
            webbrowser.open(url, new=2)
        except webbrowser.Error:
            print(f"[launcher] não foi possível abrir o navegador automaticamente. Acesse {url}")

    def run(self) -> None:
        """Executa backend e frontend, mantendo o processo principal ativo."""
        self.start_llm_async()
        if self.llm_monitor_enabled:
            self.start_llm_monitor_async()
        self.start_backend_async()
        self.start_frontend_async()

        try:
            while True:
                time.sleep(0.5)
        except KeyboardInterrupt:
            print("\n[launcher] encerrando servidores...")
            self.shutdown()

    def shutdown(self) -> None:
        if self._frontend_server is not None:
            with suppress(Exception):
                self._frontend_server.shutdown()
        if self._frontend_thread is not None and self._frontend_thread.is_alive():
            self._frontend_thread.join(timeout=2)
        if self._backend_thread is not None and self._backend_thread.is_alive():
            self._backend_thread.join(timeout=2)
        if self._llm_thread is not None and self._llm_thread.is_alive():
            self._llm_thread.join(timeout=2)
        if self._llm_monitor_thread is not None and self._llm_monitor_thread.is_alive():
            self._llm_monitor_thread.join(timeout=2)


# ----------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------

def _parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Launcher do protótipo LojaSync web")
    parser.add_argument("--host", default=DEFAULT_HOST, help="Host para os servidores (default: %(default)s)")
    parser.add_argument(
        "--frontend-port",
        type=int,
        default=DEFAULT_FRONTEND_PORT,
        help="Porta do frontend (default: %(default)s)",
    )
    parser.add_argument(
        "--backend-port",
        type=int,
        default=DEFAULT_BACKEND_PORT,
        help="Porta do backend (default: %(default)s)",
    )
    parser.add_argument(
        "--llm-port",
        type=int,
        default=DEFAULT_LLM_PORT,
        help="Porta do serviço LLM (default: %(default)s)",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Não abrir automaticamente o navegador",
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
    )
    launcher.run()


if __name__ == "__main__":  # pragma: no cover - execução direta
    main(sys.argv[1:])
