from __future__ import annotations

import json
from pathlib import Path

from app.domain.products.entities import Product
from app.domain.products.repository import ProductRepository


class JsonlProductRepository(ProductRepository):
    def __init__(self, active_file: Path, history_file: Path) -> None:
        self._active_file = active_file
        self._history_file = history_file
        self._active_file.parent.mkdir(parents=True, exist_ok=True)
        self._history_file.parent.mkdir(parents=True, exist_ok=True)
        self._active_file.touch(exist_ok=True)
        self._history_file.touch(exist_ok=True)

    def list_active(self) -> list[Product]:
        return self._load_jsonl(self._active_file)

    def list_history(self) -> list[Product]:
        return self._load_jsonl(self._history_file)

    def replace_active(self, products: list[Product]) -> None:
        self._write_jsonl(self._active_file, products)

    def append_active(self, product: Product) -> None:
        with self._active_file.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(product.to_dict(), ensure_ascii=False) + "\n")

    def append_history(self, products: list[Product]) -> None:
        with self._history_file.open("a", encoding="utf-8") as handle:
            for product in products:
                handle.write(json.dumps(product.to_dict(), ensure_ascii=False) + "\n")

    def _load_jsonl(self, path: Path) -> list[Product]:
        items: list[Product] = []
        if not path.exists():
            return items
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                payload = line.strip()
                if not payload:
                    continue
                try:
                    items.append(Product.from_dict(json.loads(payload)))
                except Exception:
                    continue
        return items

    def _write_jsonl(self, path: Path, products: list[Product]) -> None:
        with path.open("w", encoding="utf-8") as handle:
            for product in products:
                handle.write(json.dumps(product.to_dict(), ensure_ascii=False) + "\n")
