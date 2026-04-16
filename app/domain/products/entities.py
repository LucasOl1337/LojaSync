from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class GradeItem:
    tamanho: str
    quantidade: int


@dataclass(slots=True)
class CorItem:
    cor: str
    quantidade: int


def _parse_grades(value: Any) -> list[GradeItem] | None:
    if not value:
        return None
    if isinstance(value, dict):
        items = [{"tamanho": key, "quantidade": qty} for key, qty in value.items()]
    elif isinstance(value, list):
        items = value
    else:
        return None

    parsed: list[GradeItem] = []
    for item in items:
        try:
            if isinstance(item, dict):
                tamanho = str(item.get("tamanho", "")).strip()
                quantidade = int(item.get("quantidade", 0) or 0)
            else:
                tamanho = str(getattr(item, "tamanho", "")).strip()
                quantidade = int(getattr(item, "quantidade", 0) or 0)
        except Exception:
            continue
        if not tamanho:
            continue
        parsed.append(GradeItem(tamanho=tamanho, quantidade=max(quantidade, 0)))
    return parsed or None


def _parse_cores(value: Any) -> list[CorItem] | None:
    if not value:
        return None
    if isinstance(value, dict):
        items = [{"cor": key, "quantidade": qty} for key, qty in value.items()]
    elif isinstance(value, list):
        items = value
    else:
        return None

    parsed: list[CorItem] = []
    for item in items:
        try:
            if isinstance(item, dict):
                cor = str(item.get("cor", "")).strip()
                quantidade = int(item.get("quantidade", 0) or 0)
            else:
                cor = str(getattr(item, "cor", "")).strip()
                quantidade = int(getattr(item, "quantidade", 0) or 0)
        except Exception:
            continue
        if not cor:
            continue
        parsed.append(CorItem(cor=cor, quantidade=max(quantidade, 0)))
    return parsed or None


@dataclass(slots=True)
class Product:
    nome: str
    codigo: str
    quantidade: int
    preco: str
    categoria: str
    marca: str
    preco_final: str | None = None
    descricao_completa: str | None = None
    codigo_original: str | None = None
    ordering_key_value: str | None = None
    grades: list[GradeItem] | None = None
    cores: list[CorItem] | None = None
    source_type: str | None = None
    import_batch_id: str | None = None
    import_source_name: str | None = None
    pending_grade_import: bool = False
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def normalize(self, *, margin: float) -> "Product":
        self.nome = self.nome.strip()
        self.codigo = self.codigo.strip()
        self.categoria = self.categoria.strip()
        self.marca = self.marca.strip()
        self.preco = str(self.preco).strip()
        self.preco_final = str(self.preco_final).strip() if self.preco_final not in (None, "") else None
        self.descricao_completa = (
            str(self.descricao_completa).strip() if self.descricao_completa not in (None, "") else None
        )
        self.codigo_original = (self.codigo_original or self.codigo).strip()
        self.source_type = str(self.source_type).strip() if self.source_type not in (None, "") else None
        self.import_batch_id = str(self.import_batch_id).strip() if self.import_batch_id not in (None, "") else None
        self.import_source_name = (
            str(self.import_source_name).strip() if self.import_source_name not in (None, "") else None
        )
        self.pending_grade_import = bool(self.pending_grade_import)
        self.grades = _parse_grades(self.grades)
        self.cores = _parse_cores(self.cores)
        if self.quantidade < 0:
            self.quantidade = 0
        if not self.preco_final:
            self.preco_final = calculate_sale_price(self.preco, margin)
        return self

    def ordering_key(self) -> str:
        stored = str(self.ordering_key_value or "").strip()
        if stored:
            return stored
        return f"{self.codigo.strip()}::{self.timestamp.isoformat()}"

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload.pop("ordering_key_value", None)
        payload["timestamp"] = self.timestamp.isoformat()
        payload["ordering_key"] = self.ordering_key()
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "Product":
        timestamp_raw = payload.get("timestamp")
        timestamp = (
            datetime.fromisoformat(timestamp_raw)
            if isinstance(timestamp_raw, str) and timestamp_raw
            else datetime.utcnow()
        )
        return cls(
            nome=str(payload.get("nome", "")),
            codigo=str(payload.get("codigo", "")),
            quantidade=int(payload.get("quantidade", 0) or 0),
            preco=str(payload.get("preco", "")),
            categoria=str(payload.get("categoria", "")),
            marca=str(payload.get("marca", "")),
            preco_final=payload.get("preco_final"),
            descricao_completa=payload.get("descricao_completa"),
            codigo_original=payload.get("codigo_original") or payload.get("codigo"),
            ordering_key_value=payload.get("ordering_key") or payload.get("ordering_key_value"),
            grades=_parse_grades(payload.get("grades")),
            cores=_parse_cores(payload.get("cores")),
            source_type=payload.get("source_type"),
            import_batch_id=payload.get("import_batch_id"),
            import_source_name=payload.get("import_source_name"),
            pending_grade_import=bool(payload.get("pending_grade_import", False)),
            timestamp=timestamp,
        )


def parse_price(value: str | None) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    text = text.replace("R$", "").replace(" ", "").replace("\u00a0", "")
    if "." in text and "," in text:
        text = text.replace(".", "").replace(",", ".")
    elif "," in text:
        text = text.replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return None


def format_price(value: float | None) -> str | None:
    if value is None:
        return None
    return f"{value:.2f}".replace(".", ",")


def calculate_sale_price(cost_price: str, margin: float) -> str | None:
    parsed = parse_price(cost_price)
    if parsed is None:
        return None
    safe_margin = margin if margin > 0 else 1.0
    gross = parsed * safe_margin
    whole = math.floor(gross)
    target = whole + 0.9
    if target < gross:
        target = whole + 1.9
    return format_price(target)
