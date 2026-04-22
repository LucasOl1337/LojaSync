"""LojaSync Launcher — Networking utilities.

Extracted from launcher.py to isolate network-related helpers.
"""
from __future__ import annotations

import socket
from contextlib import suppress


def guess_public_host() -> str:
    """Return the local IP that reaches the internet (best-effort)."""
    with suppress(Exception):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            return sock.getsockname()[0]
    return "127.0.0.1"


def connect_host(host: str) -> str:
    return "127.0.0.1" if host in {"0.0.0.0", "::"} else host


def is_tcp_listening(host: str, port: int, timeout: float = 0.25) -> bool:
    target_host = connect_host(host)
    with suppress(Exception):
        with socket.create_connection((target_host, port), timeout=timeout):
            return True
    return False


def is_port_bindable(host: str, port: int) -> bool:
    bind_host = "0.0.0.0" if host in {"0.0.0.0", "::"} else host
    family = socket.AF_INET6 if ":" in bind_host and bind_host != "0.0.0.0" else socket.AF_INET
    with suppress(Exception):
        with socket.socket(family, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind((bind_host, port))
            return True
    return False
