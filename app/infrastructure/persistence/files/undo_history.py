from __future__ import annotations

import json
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


class InMemoryUndoRedoHistoryStore:
    def __init__(self, limit: int) -> None:
        self._limit = max(0, int(limit or 0))
        self._undo: list[list[Product]] = []
        self._redo: list[list[Product]] = []

    def state(self) -> UndoRedoHistoryState:
        return UndoRedoHistoryState(undo_count=len(self._undo), redo_count=len(self._redo), limit=self._limit)

    def record_undo_snapshot(self, snapshot: list[Product], *, clear_redo: bool = True) -> UndoRedoHistoryState:
        self._push_bounded(self._undo, snapshot)
        if clear_redo:
            self._redo = []
        return self.state()

    def undo(self, current_snapshot: list[Product]) -> tuple[list[Product] | None, UndoRedoHistoryState]:
        if not self._undo:
            return None, self.state()
        snapshot = self._undo.pop()
        self._push_bounded(self._redo, current_snapshot)
        return self._clone_snapshot(snapshot), self.state()

    def redo(self, current_snapshot: list[Product]) -> tuple[list[Product] | None, UndoRedoHistoryState]:
        if not self._redo:
            return None, self.state()
        snapshot = self._redo.pop()
        self._push_bounded(self._undo, current_snapshot)
        return self._clone_snapshot(snapshot), self.state()

    def _push_bounded(self, stack: list[list[Product]], snapshot: list[Product]) -> None:
        if self._limit <= 0:
            stack.clear()
            return
        stack.append(self._clone_snapshot(snapshot))
        overflow = len(stack) - self._limit
        if overflow > 0:
            del stack[:overflow]

    @staticmethod
    def _clone_snapshot(snapshot: list[Product]) -> list[Product]:
        return [Product.from_dict(item.to_dict()) for item in snapshot]


class JsonUndoRedoHistoryStore(InMemoryUndoRedoHistoryStore):
    def __init__(self, history_file: Path, limit: int) -> None:
        super().__init__(limit)
        self._history_file = history_file
        self._history_file.parent.mkdir(parents=True, exist_ok=True)
        self._undo, self._redo = self._load()

    def record_undo_snapshot(self, snapshot: list[Product], *, clear_redo: bool = True) -> UndoRedoHistoryState:
        state = super().record_undo_snapshot(snapshot, clear_redo=clear_redo)
        self._save()
        return state

    def undo(self, current_snapshot: list[Product]) -> tuple[list[Product] | None, UndoRedoHistoryState]:
        snapshot, state = super().undo(current_snapshot)
        if snapshot is not None:
            self._save()
        return snapshot, state

    def redo(self, current_snapshot: list[Product]) -> tuple[list[Product] | None, UndoRedoHistoryState]:
        snapshot, state = super().redo(current_snapshot)
        if snapshot is not None:
            self._save()
        return snapshot, state

    def _load(self) -> tuple[list[list[Product]], list[list[Product]]]:
        if not self._history_file.exists():
            return [], []
        try:
            payload = json.loads(self._history_file.read_text(encoding="utf-8"))
        except Exception:
            return [], []
        if not isinstance(payload, dict):
            return [], []
        return self._coerce_stack(payload.get("undo")), self._coerce_stack(payload.get("redo"))

    def _coerce_stack(self, value: object) -> list[list[Product]]:
        if self._limit <= 0 or not isinstance(value, list):
            return []
        stack: list[list[Product]] = []
        for raw_snapshot in value[-self._limit:]:
            if not isinstance(raw_snapshot, list):
                continue
            snapshot = [Product.from_dict(item) for item in raw_snapshot if isinstance(item, dict)]
            stack.append(snapshot)
        return stack

    def _save(self) -> None:
        payload = {
            "version": 1,
            "limit": self._limit,
            "undo": [self._serialize_snapshot(snapshot) for snapshot in self._undo],
            "redo": [self._serialize_snapshot(snapshot) for snapshot in self._redo],
        }
        temporary = self._history_file.with_suffix(f"{self._history_file.suffix}.tmp")
        temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(self._history_file)

    @staticmethod
    def _serialize_snapshot(snapshot: list[Product]) -> list[dict[str, object]]:
        return [item.to_dict() for item in snapshot]
