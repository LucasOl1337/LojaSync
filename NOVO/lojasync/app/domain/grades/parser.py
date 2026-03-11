from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Iterable


@dataclass(slots=True)
class ParsedGradeItem:
    codigo: str | None
    nome: str | None
    grades: dict[str, int]
    warnings: list[str] = field(default_factory=list)
    raw: dict[str, Any] | None = None


def _load_json_payload(text: str) -> Any | None:
    candidate = (text or "").strip()
    if not candidate:
        return None
    try:
        if candidate.startswith("{") or candidate.startswith("["):
            return json.loads(candidate)
    except Exception:
        pass

    blocks = re.findall(r"```(?:json)?\s*(.*?)```", text or "", flags=re.IGNORECASE | re.DOTALL)
    for block in blocks:
        try:
            return json.loads(block)
        except Exception:
            continue
    return None


def _normalize_size(label: str) -> str:
    return re.sub(r"\s+", "", str(label or "").strip()).upper()


def _extract_items(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        for key in ("items", "produtos", "products", "grades"):
            bucket = data.get(key)
            if isinstance(bucket, list):
                return [item for item in bucket if isinstance(item, dict)]
    return []


def _coerce_grades(
    value: Any,
    warnings: list[str],
    allowed_sizes: Iterable[str] | None = None,
) -> dict[str, int]:
    allowed = {_normalize_size(size): str(size) for size in (allowed_sizes or []) if size}
    result: dict[str, int] = {}

    def _register(size: str, qty: Any) -> None:
        size_norm = _normalize_size(size)
        if not size_norm:
            return
        try:
            quantity = int(qty)
        except Exception:
            warnings.append(f"Quantidade invalida para tamanho '{size}': {qty}")
            return
        if quantity <= 0:
            return
        if allowed and size_norm not in allowed:
            warnings.append(f"Tamanho '{size}' fora do catalogo permitido")
            return
        key = allowed.get(size_norm, size_norm) if allowed else size_norm
        result[key] = quantity

    if isinstance(value, dict):
        for key, qty in value.items():
            _register(str(key), qty)
        return result

    if isinstance(value, list):
        for entry in value:
            if isinstance(entry, dict):
                size = entry.get("tamanho") or entry.get("size") or entry.get("label")
                qty = entry.get("quantidade") or entry.get("qtd") or entry.get("qty")
                _register(str(size or ""), qty)
            elif isinstance(entry, (list, tuple)) and len(entry) >= 2:
                _register(str(entry[0]), entry[1])
        return result

    if isinstance(value, str):
        tokens = re.split(r"[;\n,]", value)
        for token in tokens:
            part = token.strip()
            if not part:
                continue
            if "=" in part:
                size, qty = part.split("=", 1)
            elif ":" in part:
                size, qty = part.split(":", 1)
            elif " " in part:
                size, qty = part.split(" ", 1)
            else:
                warnings.append(f"Entrada de grade nao reconhecida: '{part}'")
                continue
            _register(size, qty)
        return result

    warnings.append("Formato de grades nao suportado pelo parser")
    return result


def parse_grade_extraction(
    text: str,
    *,
    allowed_sizes: Iterable[str] | None = None,
) -> tuple[list[ParsedGradeItem], list[str]]:
    warnings: list[str] = []
    payload = _load_json_payload(text)
    if payload is None:
        return [], ["Conteudo retornado pelo LLM nao pode ser interpretado como JSON"]

    items = _extract_items(payload)
    if not items:
        return [], ["Nenhum item com grades foi encontrado no JSON retornado pelo LLM"]

    results: list[ParsedGradeItem] = []
    for entry in items:
        codigo = entry.get("codigo") or entry.get("code") or entry.get("sku")
        nome = entry.get("nome") or entry.get("descricao") or entry.get("produto")
        grades_raw = entry.get("grades") or entry.get("grade")
        if grades_raw is None:
            warnings.append("Campo 'grades' ausente no item")
            continue

        item_warnings: list[str] = []
        grades = _coerce_grades(grades_raw, item_warnings, allowed_sizes)
        if not grades:
            item_warnings.append("Nenhum tamanho valido encontrado para o item")
            warnings.extend(item_warnings)
            continue

        results.append(
            ParsedGradeItem(
                codigo=str(codigo).strip() if codigo else None,
                nome=str(nome).strip() if nome else None,
                grades=grades,
                warnings=item_warnings,
                raw=entry,
            )
        )

    if not results:
        warnings.append("Parser nao conseguiu mapear nenhum item valido")

    return results, warnings
