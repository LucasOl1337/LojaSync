from __future__ import annotations

from abc import ABC, abstractmethod

from app.domain.products.entities import Product


class ProductRepository(ABC):
    @abstractmethod
    def list_active(self) -> list[Product]:
        raise NotImplementedError

    @abstractmethod
    def list_history(self) -> list[Product]:
        raise NotImplementedError

    @abstractmethod
    def replace_active(self, products: list[Product]) -> None:
        raise NotImplementedError

    @abstractmethod
    def append_active(self, product: Product) -> None:
        raise NotImplementedError

    @abstractmethod
    def append_history(self, products: list[Product]) -> None:
        raise NotImplementedError

    @abstractmethod
    def update(self, ordering_key: str, changes: dict[str, object]) -> Product | None:
        raise NotImplementedError
