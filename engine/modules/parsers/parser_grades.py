from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Tuple


@dataclass
class ParsedGradeItem:
    codigo: Optional[str]
    nome: Optional[str]
    grades: Dict[str, int]
    warnings: List[str] = field(default_factory=list)
    raw: Optional[Dict[str, Any]] = None


def _load_json_payload(text: str) -> Optional[Any]:
    candidate = (text or "").strip()
    if not candidate:
        return None
    try:
        if candidate.startswith("{") or candidate.startswith("["):
            return json.loads(candidate)
    except Exception:
        pass

    blocks = re.findall(r"```(?:json)?\s*(.*?)```", text, flags=re.IGNORECASE | re.DOTALL)
    for block in blocks:
        try:
            return json.loads(block)
        except Exception:
            continue
    return None


def _normalize_size(label: str) -> str:
    return re.sub(r"\s+", "", str(label or "").strip()).upper()


def _coerce_grades(
    value: Any,
    warnings: List[str],
    allowed_sizes: Optional[Iterable[str]] = None,
) -> Dict[str, int]:
    allowed = {_normalize_size(size): size for size in (allowed_sizes or []) if size}
    result: Dict[str, int] = {}

    def _register(size: str, qty: Any) -> None:
        size_norm = _normalize_size(size)
        if not size_norm:
            return
        try:
            quantidade = int(qty)
        except Exception:
            warnings.append(f"Quantidade inválida para tamanho '{size}': {qty}")
            return
        if quantidade <= 0:
            return
        if allowed and size_norm not in allowed:
            warnings.append(f"Tamanho '{size}' fora do catálogo permitido")
            return
        key = allowed.get(size_norm, size_norm) if allowed else size_norm
        result[key] = quantidade

    if isinstance(value, dict):
        for key, qty in value.items():
            _register(str(key), qty)
        return result

    if isinstance(value, list):
        for entry in value:
            if isinstance(entry, dict):
                size = entry.get("tamanho") or entry.get("size") or entry.get("label")
                qty = entry.get("quantidade") or entry.get("qtd") or entry.get("qty")
                _register(size, qty)
            elif isinstance(entry, (list, tuple)) and len(entry) >= 2:
                _register(entry[0], entry[1])
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
                warnings.append(f"Entrada de grade não reconhecida: '{part}'")
                continue
            _register(size, qty)
        return result

    warnings.append("Formato de grades não suportado pelo parser")
    return result


def _extract_items(data: Any) -> List[Dict[str, Any]]:
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        for key in ("items", "produtos", "products", "grades"):
            bucket = data.get(key)
            if isinstance(bucket, list):
                return [item for item in bucket if isinstance(item, dict)]
    return []


def parse_grade_extraction(
    text: str,
    *,
    allowed_sizes: Optional[Iterable[str]] = None,
) -> Tuple[List[ParsedGradeItem], List[str]]:
    warnings: List[str] = []
    payload = _load_json_payload(text)
    if payload is None:
        return [], ["Conteúdo retornado pelo LLM não pôde ser interpretado como JSON"]

    items = _extract_items(payload)
    if not items:
        return [], ["Nenhum item com grades foi encontrado no JSON retornado pelo LLM"]

    results: List[ParsedGradeItem] = []
    for entry in items:
        codigo = entry.get("codigo") or entry.get("code") or entry.get("sku")
        nome = entry.get("nome") or entry.get("descricao") or entry.get("produto")
        grades_raw = entry.get("grades") or entry.get("grade")
        if grades_raw is None:
            entry_warnings = ["Campo 'grades' ausente no item"]
            warnings.extend(entry_warnings)
            continue
        item_warnings: List[str] = []
        grades = _coerce_grades(grades_raw, item_warnings, allowed_sizes)
        if not grades:
            item_warnings.append("Nenhum tamanho válido encontrado para o item")
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
        warnings.append("Parser não conseguiu mapear nenhum item válido")

    return results, warnings


__all__ = ["ParsedGradeItem", "parse_grade_extraction"]
