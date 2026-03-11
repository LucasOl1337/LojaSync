from __future__ import annotations

from abc import ABC, abstractmethod


class BrandRepository(ABC):
    @abstractmethod
    def list_brands(self) -> list[str]:
        raise NotImplementedError

    @abstractmethod
    def save_brands(self, brands: list[str]) -> None:
        raise NotImplementedError
