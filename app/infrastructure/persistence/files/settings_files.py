from __future__ import annotations

import json
from pathlib import Path

from app.domain.brands.repository import BrandRepository
from app.domain.metrics.entities import Metrics


class JsonBrandRepository(BrandRepository):
    def __init__(self, brands_file: Path, default_brands: tuple[str, ...]) -> None:
        self._brands_file = brands_file
        self._default_brands = list(default_brands)
        self._brands_file.parent.mkdir(parents=True, exist_ok=True)

    def list_brands(self) -> list[str]:
        if not self._brands_file.exists():
            return list(self._default_brands)
        try:
            payload = json.loads(self._brands_file.read_text(encoding="utf-8"))
        except Exception:
            return list(self._default_brands)
        if not isinstance(payload, list):
            return list(self._default_brands)
        return [str(item).strip() for item in payload if str(item).strip()]

    def save_brands(self, brands: list[str]) -> None:
        self._brands_file.write_text(
            json.dumps(brands, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


class MarginSettingsStore:
    def __init__(self, margin_file: Path, default_margin: float) -> None:
        self._margin_file = margin_file
        self._default_margin = default_margin
        self._margin_file.parent.mkdir(parents=True, exist_ok=True)

    def load_margin(self) -> float:
        if not self._margin_file.exists():
            return self._default_margin
        try:
            payload = json.loads(self._margin_file.read_text(encoding="utf-8"))
            margin = float(payload.get("margem", self._default_margin))
            return margin if margin > 0 else self._default_margin
        except Exception:
            return self._default_margin

    def save_margin(self, margin: float) -> None:
        self._margin_file.write_text(
            json.dumps({"margem": margin}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


class MetricsStore:
    def __init__(self, metrics_file: Path) -> None:
        self._metrics_file = metrics_file
        self._metrics_file.parent.mkdir(parents=True, exist_ok=True)

    def load_metrics(self) -> Metrics:
        if not self._metrics_file.exists():
            return Metrics()
        try:
            payload = json.loads(self._metrics_file.read_text(encoding="utf-8"))
            return Metrics(
                tempo_economizado=int(payload.get("tempo_economizado", 0) or 0),
                caracteres_digitados=int(payload.get("caracteres_digitados", 0) or 0),
                historico_quantidade=int(payload.get("historico_quantidade", 0) or 0),
                historico_custo=float(payload.get("historico_custo", 0.0) or 0.0),
                historico_venda=float(payload.get("historico_venda", 0.0) or 0.0),
            )
        except Exception:
            return Metrics()

    def save_metrics(self, metrics: Metrics) -> None:
        self._metrics_file.write_text(
            json.dumps(
                {
                    "tempo_economizado": metrics.tempo_economizado,
                    "caracteres_digitados": metrics.caracteres_digitados,
                    "historico_quantidade": metrics.historico_quantidade,
                    "historico_custo": metrics.historico_custo,
                    "historico_venda": metrics.historico_venda,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
