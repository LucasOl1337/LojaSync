from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True, frozen=True)
class WindowCandidate:
    backend: str
    pid: int
    handle: int
    title: str
    class_name: str
    visible: bool
    enabled: bool
    rect: tuple[int, int, int, int]
    process_path: str | None = None
    is_elevated: bool | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True, frozen=True)
class HealthFinding:
    code: str
    severity: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
