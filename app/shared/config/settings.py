from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AppSettings:
    app_name: str = "LojaSync"
    api_host: str = "127.0.0.1"
    api_port: int = 8800
    default_margin: float = 1.0
    default_brands: tuple[str, ...] = ("OGOCHI", "MALWEE", "REVANCHE", "COQ")
