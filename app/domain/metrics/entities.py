from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class Metrics:
    tempo_economizado: int = 0
    caracteres_digitados: int = 0
