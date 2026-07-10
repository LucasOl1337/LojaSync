from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

from app.domain.products.entities import Product


@dataclass(slots=True)
class UndoRedoHistoryState:
    undo_count: int
    redo_count: int
    limit: int

    @property
    def can_undo(self) -> bool:
        return self.undo_count > 0

    @property
    def can_redo(self) -> bool:
        return self.redo_count > 0


@dataclass(slots=True)
class UndoRedoSnapshot:
    products: list[Product]
    default_margin: float | None = None


class InMemoryUndoRedoHistoryStore:
    def __init__(self, limit: int) -> None:
        self._limit = max(0, int(limit or 0))
        self._undo: list[UndoRedoSnapshot] = []
        self._redo: list[UndoRedoSnapshot] = []

    def state(self) -> UndoRedoHistoryState:
        return UndoRedoHistoryState(undo_count=len(self._undo), redo_count=len(self._redo), limit=self._limit)

    def record_undo_snapshot(
        self,
        products: list[Product],
        *,
        default_margin: float | None = None,
        clear_redo: bool = True,
    ) -> UndoRedoHistoryState:
        self._push_bounded(
            self._undo,
            UndoRedoSnapshot(products=products, default_margin=self._normalize_margin(default_margin)),
        )
        if clear_redo:
            self._redo = []
        return self.state()

    def undo(
        self,
        current_products: list[Product],
        *,
        current_default_margin: float | None = None,
    ) -> tuple[UndoRedoSnapshot | None, UndoRedoHistoryState]:
        if not self._undo:
            return None, self.state()
        snapshot = self._undo.pop()
        self._push_bounded(
            self._redo,
            UndoRedoSnapshot(
                products=current_products,
                default_margin=self._normalize_margin(current_default_margin),
            ),
        )
        return self._clone_snapshot(snapshot), self.state()

    def redo(
        self,
        current_products: list[Product],
        *,
        current_default_margin: float | None = None,
    ) -> tuple[UndoRedoSnapshot | None, UndoRedoHistoryState]:
        if not self._redo:
            return None, self.state()
        snapshot = self._redo.pop()
        self._push_bounded(
            self._undo,
            UndoRedoSnapshot(
                products=current_products,
                default_margin=self._normalize_margin(current_default_margin),
            ),
        )
        return self._clone_snapshot(snapshot), self.state()

    def _push_bounded(self, stack: list[UndoRedoSnapshot], snapshot: UndoRedoSnapshot) -> None:
        if self._limit <= 0:
            stack.clear()
            return
        stack.append(self._clone_snapshot(snapshot))
        overflow = len(stack) - self._limit
        if overflow > 0:
            del stack[:overflow]

    @classmethod
    def _clone_snapshot(cls, snapshot: UndoRedoSnapshot) -> UndoRedoSnapshot:
        return UndoRedoSnapshot(
            products=[Product.from_dict(item.to_dict()) for item in snapshot.products],
            default_margin=cls._normalize_margin(snapshot.default_margin),
        )

    @staticmethod
    def _normalize_margin(value: object) -> float | None:
        if value is None:
            return None
        try:
            margin = float(value)
        except (TypeError, ValueError):
            return None
        return margin if math.isfinite(margin) and margin > 0 else None


class JsonUndoRedoHistoryStore(InMemoryUndoRedoHistoryStore):
    def __init__(self, history_file: Path, limit: int) -> None:
        super().__init__(limit)
        self._history_file = history_file
        self._history_file.parent.mkdir(parents=True, exist_ok=True)
        self._undo, self._redo = self._load()

    def record_undo_snapshot(
        self,
        products: list[Product],
        *,
        default_margin: float | None = None,
        clear_redo: bool = True,
    ) -> UndoRedoHistoryState:
        state = super().record_undo_snapshot(
            products,
            default_margin=default_margin,
            clear_redo=clear_redo,
        )
        self._save()
        return state

    def undo(
        self,
        current_products: list[Product],
        *,
        current_default_margin: float | None = None,
    ) -> tuple[UndoRedoSnapshot | None, UndoRedoHistoryState]:
        snapshot, state = super().undo(
            current_products,
            current_default_margin=current_default_margin,
        )
        if snapshot is not None:
            self._save()
        return snapshot, state

    def redo(
        self,
        current_products: list[Product],
        *,
        current_default_margin: float | None = None,
    ) -> tuple[UndoRedoSnapshot | None, UndoRedoHistoryState]:
        snapshot, state = super().redo(
            current_products,
            current_default_margin=current_default_margin,
        )
        if snapshot is not None:
            self._save()
        return snapshot, state

    def _load(self) -> tuple[list[UndoRedoSnapshot], list[UndoRedoSnapshot]]:
        if not self._history_file.exists():
            return [], []
        try:
            payload = json.loads(self._history_file.read_text(encoding="utf-8"))
        except Exception:
            return [], []
        if not isinstance(payload, dict):
            return [], []
        return self._coerce_stack(payload.get("undo")), self._coerce_stack(payload.get("redo"))

    def _coerce_stack(self, value: object) -> list[UndoRedoSnapshot]:
        if self._limit <= 0 or not isinstance(value, list):
            return []
        stack: list[UndoRedoSnapshot] = []
        for raw_snapshot in value[-self._limit:]:
            snapshot = self._coerce_snapshot(raw_snapshot)
            if snapshot is not None:
                stack.append(snapshot)
        return stack

    def _coerce_snapshot(self, value: object) -> UndoRedoSnapshot | None:
        if isinstance(value, list):
            raw_products = value
            default_margin = None
        elif isinstance(value, dict):
            raw_products = value.get("products")
            default_margin = self._normalize_margin(value.get("default_margin"))
        else:
            return None
        if not isinstance(raw_products, list):
            return None
        products = [Product.from_dict(item) for item in raw_products if isinstance(item, dict)]
        return UndoRedoSnapshot(products=products, default_margin=default_margin)

    def _save(self) -> None:
        payload = {
            "version": 2,
            "limit": self._limit,
            "undo": [self._serialize_snapshot(snapshot) for snapshot in self._undo],
            "redo": [self._serialize_snapshot(snapshot) for snapshot in self._redo],
        }
        temporary = self._history_file.with_suffix(f"{self._history_file.suffix}.tmp")
        temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(self._history_file)

    @staticmethod
    def _serialize_snapshot(snapshot: UndoRedoSnapshot) -> dict[str, object]:
        payload: dict[str, object] = {
            "products": [item.to_dict() for item in snapshot.products],
        }
        if snapshot.default_margin is not None:
            payload["default_margin"] = snapshot.default_margin
        return payload
