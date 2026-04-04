from __future__ import annotations

import ctypes
from ctypes import wintypes
from dataclasses import dataclass
from typing import Iterable

from app.application.automation.byteempresa.models import HealthFinding, WindowCandidate

DEFAULT_TITLE_REGEX = r"Byte Empresa - .*"
DEFAULT_MAIN_TITLE = "Byte Empresa"
INFRA_TITLES = {"", "Default IME", "MSCTFIME UI", "GDI+ Window (ByteEmpresa.exe)"}
INFRA_CLASSES = {"TApplication", "GDI+ Hook Window Class", "IME"}

try:
    from pywinauto import Application, Desktop

    PYWINAUTO_AVAILABLE = True
    PYWINAUTO_IMPORT_ERROR: Exception | None = None
except Exception as exc:  # pragma: no cover - depends on local Windows environment
    Application = None  # type: ignore[assignment]
    Desktop = None  # type: ignore[assignment]
    PYWINAUTO_AVAILABLE = False
    PYWINAUTO_IMPORT_ERROR = exc


class DiscoveryError(RuntimeError):
    """Erro ao localizar uma janela utilizavel do ByteEmpresa."""


def ensure_pywinauto_available() -> None:
    if not PYWINAUTO_AVAILABLE:
        raise RuntimeError(
            "pywinauto nao esta disponivel neste ambiente. Instale pywinauto/comtypes para usar a automacao nativa."
        ) from PYWINAUTO_IMPORT_ERROR


@dataclass(slots=True)
class AttachOptions:
    backend: str = "win32"
    title_regex: str = DEFAULT_TITLE_REGEX
    prefer_non_elevated: bool = True


def _safe_call(func, default=None):
    try:
        return func()
    except Exception:
        return default


def is_process_elevated(pid: int) -> bool | None:
    process_query_limited_information = 0x1000
    token_query = 0x0008
    token_elevation = 20

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)

    open_process = kernel32.OpenProcess
    open_process.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    open_process.restype = wintypes.HANDLE

    close_handle = kernel32.CloseHandle
    close_handle.argtypes = [wintypes.HANDLE]
    close_handle.restype = wintypes.BOOL

    open_process_token = advapi32.OpenProcessToken
    open_process_token.argtypes = [
        wintypes.HANDLE,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.HANDLE),
    ]
    open_process_token.restype = wintypes.BOOL

    get_token_information = advapi32.GetTokenInformation
    get_token_information.argtypes = [
        wintypes.HANDLE,
        ctypes.c_uint,
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
    ]
    get_token_information.restype = wintypes.BOOL

    class TokenElevation(ctypes.Structure):
        _fields_ = [("TokenIsElevated", wintypes.DWORD)]

    h_process = open_process(process_query_limited_information, False, pid)
    if not h_process:
        return None
    try:
        h_token = wintypes.HANDLE()
        if not open_process_token(h_process, token_query, ctypes.byref(h_token)):
            return None
        try:
            elevation = TokenElevation()
            out_len = wintypes.DWORD()
            ok = get_token_information(
                h_token,
                token_elevation,
                ctypes.byref(elevation),
                ctypes.sizeof(elevation),
                ctypes.byref(out_len),
            )
            if not ok:
                return None
            return bool(elevation.TokenIsElevated)
        finally:
            close_handle(h_token)
    finally:
        close_handle(h_process)


def get_process_path(pid: int) -> str | None:
    process_query_limited_information = 0x1000
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

    open_process = kernel32.OpenProcess
    open_process.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    open_process.restype = wintypes.HANDLE

    query_full_process_image_name = kernel32.QueryFullProcessImageNameW
    query_full_process_image_name.argtypes = [
        wintypes.HANDLE,
        wintypes.DWORD,
        wintypes.LPWSTR,
        ctypes.POINTER(wintypes.DWORD),
    ]
    query_full_process_image_name.restype = wintypes.BOOL

    close_handle = kernel32.CloseHandle
    close_handle.argtypes = [wintypes.HANDLE]
    close_handle.restype = wintypes.BOOL

    h_process = open_process(process_query_limited_information, False, pid)
    if not h_process:
        return None
    try:
        size = wintypes.DWORD(32768)
        buffer = ctypes.create_unicode_buffer(size.value)
        ok = query_full_process_image_name(h_process, 0, buffer, ctypes.byref(size))
        if not ok:
            return None
        return buffer.value
    finally:
        close_handle(h_process)


def is_infrastructure_window(candidate: WindowCandidate) -> bool:
    if candidate.class_name in INFRA_CLASSES:
        return True
    if candidate.title in INFRA_TITLES:
        return True
    if candidate.title.startswith("GDI+ Window"):
        return True
    return False


def _window_candidate(wrapper, backend: str) -> WindowCandidate:
    process_id = _safe_call(wrapper.process_id, 0) or 0
    rect = _safe_call(wrapper.rectangle, None)
    if rect is None:
        rect_tuple = (0, 0, 0, 0)
    else:
        rect_tuple = (rect.left, rect.top, rect.right, rect.bottom)
    return WindowCandidate(
        backend=backend,
        pid=process_id,
        handle=_safe_call(lambda: int(wrapper.handle), 0) or 0,
        title=_safe_call(wrapper.window_text, "") or "",
        class_name=_safe_call(wrapper.class_name, "") or "",
        visible=_safe_call(wrapper.is_visible, False) or False,
        enabled=_safe_call(wrapper.is_enabled, False) or False,
        rect=rect_tuple,
        process_path=get_process_path(process_id) if process_id else None,
        is_elevated=is_process_elevated(process_id) if process_id else None,
    )


def discover_windows(
    title_regex: str = DEFAULT_TITLE_REGEX,
    backends: Iterable[str] = ("win32", "uia"),
) -> list[WindowCandidate]:
    ensure_pywinauto_available()
    found: dict[tuple[str, int], WindowCandidate] = {}
    for backend in backends:
        desktop = Desktop(backend=backend)
        for wrapper in desktop.windows(title_re=title_regex):
            candidate = _window_candidate(wrapper, backend)
            found[(candidate.backend, candidate.handle)] = candidate
    return sorted(
        found.values(),
        key=lambda item: (
            item.backend != "win32",
            item.is_elevated is True,
            item.pid,
            item.handle,
        ),
    )


def top_level_windows_for_pid(pid: int, backend: str) -> list[WindowCandidate]:
    ensure_pywinauto_available()
    desktop = Desktop(backend=backend)
    windows = []
    for wrapper in desktop.windows(process=pid):
        windows.append(_window_candidate(wrapper, backend))
    return sorted(windows, key=lambda item: item.handle)


def best_window(
    title_regex: str = DEFAULT_TITLE_REGEX,
    backend: str = "win32",
    prefer_non_elevated: bool = True,
) -> WindowCandidate:
    candidates = [item for item in discover_windows(title_regex=title_regex, backends=(backend,))]
    if not candidates:
        raise DiscoveryError(f"Nenhuma janela do ByteEmpresa encontrada para backend={backend!r}.")
    candidates.sort(
        key=lambda item: (
            prefer_non_elevated and item.is_elevated is True,
            item.title != DEFAULT_MAIN_TITLE and not item.title.startswith("Byte Empresa - "),
            not item.visible,
            item.handle,
        )
    )
    return candidates[0]


class ByteEmpresaSession:
    def __init__(self, candidate: WindowCandidate):
        ensure_pywinauto_available()
        self.candidate = candidate
        self.backend = candidate.backend
        self.app = Application(backend=self.backend).connect(handle=candidate.handle)
        self.window = self.app.window(handle=candidate.handle)

    @classmethod
    def attach(
        cls,
        backend: str = "win32",
        title_regex: str = DEFAULT_TITLE_REGEX,
        handle: int | None = None,
        pid: int | None = None,
    ) -> "ByteEmpresaSession":
        ensure_pywinauto_available()
        if handle is not None:
            app = Application(backend=backend).connect(handle=handle)
            wrapper = app.window(handle=handle)
            return cls(_window_candidate(wrapper, backend))
        if pid is not None:
            desktop = Desktop(backend=backend)
            matches = [
                _window_candidate(wrapper, backend)
                for wrapper in desktop.windows(process=pid)
                if _safe_call(wrapper.window_text, "").startswith("Byte Empresa")
            ]
            if not matches:
                raise DiscoveryError(f"Nenhuma janela do ByteEmpresa encontrada no PID {pid}.")
            return cls(matches[0])
        return cls(best_window(title_regex=title_regex, backend=backend))

    def refresh(self) -> None:
        self.window = self.app.window(handle=self.candidate.handle)
        self.candidate = _window_candidate(self.window, self.backend)

    def top_level_windows(self) -> list[WindowCandidate]:
        return top_level_windows_for_pid(self.candidate.pid, self.backend)

    def significant_windows(self) -> list[WindowCandidate]:
        return [item for item in self.top_level_windows() if item.visible and not is_infrastructure_window(item)]

    def interaction_candidate(self) -> WindowCandidate:
        windows = self.significant_windows()
        if not windows:
            return self.candidate
        windows.sort(
            key=lambda item: (
                not item.enabled,
                item.title == DEFAULT_MAIN_TITLE,
                item.title.startswith("Byte Empresa - ") and not item.enabled,
                item.handle,
            )
        )
        return windows[0]

    def interaction_window(self):
        candidate = self.interaction_candidate()
        return self.app.window(handle=candidate.handle)

    def health_findings(self) -> list[HealthFinding]:
        findings: list[HealthFinding] = []
        self.refresh()
        if not self.candidate.visible:
            findings.append(
                HealthFinding(
                    code="main_window_hidden",
                    severity="high",
                    message="A janela principal existe, mas nao esta visivel.",
                )
            )
        if not self.candidate.enabled:
            findings.append(
                HealthFinding(
                    code="main_window_disabled",
                    severity="high",
                    message="A janela principal esta desabilitada; possivel modal bloqueando o fluxo.",
                )
            )
        visible_peers = [item for item in self.significant_windows() if item.handle != self.candidate.handle]
        for peer in visible_peers:
            findings.append(
                HealthFinding(
                    code="secondary_window_visible",
                    severity="medium",
                    message="Existe outra janela do processo visivel. Pode ser modal, popup ou tela paralela.",
                    details=peer.to_dict(),
                )
            )
        if self.candidate.is_elevated:
            findings.append(
                HealthFinding(
                    code="process_elevated",
                    severity="medium",
                    message="O ByteEmpresa esta rodando elevado. A automacao precisa do mesmo nivel de privilegio.",
                )
            )
        interaction = self.interaction_candidate()
        if interaction.handle != self.candidate.handle:
            findings.append(
                HealthFinding(
                    code="interaction_window_changed",
                    severity="info",
                    message="A janela interativa atual nao e a principal. A automacao deve agir sobre a tela ativa.",
                    details=interaction.to_dict(),
                )
            )
        return findings
