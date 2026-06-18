from __future__ import annotations

import json
import re
from typing import Any

from app.domain.products.entities import Product
from app.domain.products.post_processing import (
    coerce_confidence,
    normalize_price_to_next_tenth,
    sanitize_code_for_store,
    sanitize_store_name,
)


POST_PROCESS_KEEP_ACTIONS = {"manter", "keep", "none"}


def empty_post_process_result() -> dict[str, Any]:
    return {
        "total": 0,
        "modificados": 0,
        "warnings": [],
        "llm_suggestions_applied": 0,
        "local_adjustments_applied": 0,
        "dry_run": False,
    }


def extract_post_process_suggestions(text: str | None) -> dict[str, dict[str, Any]]:
    raw = str(text or "").strip()
    if not raw:
        return {}

    payloads: list[Any] = []
    fenced = re.findall(r"```(?:json)?\s*(.*?)```", raw, flags=re.IGNORECASE | re.DOTALL)
    for fragment in fenced:
        try:
            payloads.append(json.loads(fragment.strip()))
        except Exception:
            continue

    if not payloads:
        decoder = json.JSONDecoder()
        for start in range(len(raw)):
            if raw[start] not in "[{":
                continue
            try:
                payload, _ = decoder.raw_decode(raw[start:])
            except Exception:
                continue
            payloads.append(payload)
            break

    extracted: dict[str, dict[str, Any]] = {}
    for payload in payloads:
        items: list[Any]
        if isinstance(payload, dict) and isinstance(payload.get("items"), list):
            items = payload["items"]
        elif isinstance(payload, list):
            items = payload
        else:
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            ordering_key = str(item.get("ordering_key") or "").strip()
            if ordering_key:
                extracted[ordering_key] = item
    return extracted


def resolve_post_process_name(item: Product, suggestion: dict[str, Any]) -> str:
    confidence = coerce_confidence(suggestion.get("confianca"))
    llm_name = str(suggestion.get("nome_sugerido") or "").strip()
    if llm_name and confidence >= 0.7:
        cleaned_llm = sanitize_store_name(llm_name)
        if cleaned_llm:
            return cleaned_llm

    source = str(item.descricao_completa or item.nome or "").strip()
    fallback = sanitize_store_name(source)
    return fallback or (item.nome or "").strip()


def resolve_post_process_code(item: Product, suggestion: dict[str, Any]) -> str:
    confidence = coerce_confidence(suggestion.get("confianca"))
    llm_code = str(suggestion.get("codigo_sugerido") or "").strip()
    if llm_code and confidence >= 0.75:
        cleaned_llm = sanitize_code_for_store(llm_code)
        if cleaned_llm:
            return cleaned_llm
    return sanitize_code_for_store(item.codigo or "")


def resolve_post_process_price(item: Product, suggestion: dict[str, Any]) -> str:
    confidence = coerce_confidence(suggestion.get("confianca"))
    llm_price = str(suggestion.get("preco_sugerido") or "").strip()
    if llm_price and confidence >= 0.75:
        normalized_llm = normalize_price_to_next_tenth(llm_price)
        if normalized_llm:
            return normalized_llm
    normalized = normalize_price_to_next_tenth(item.preco or "")
    return normalized or (item.preco or "").strip()


def apply_post_process_updates(
    items: list[Product],
    *,
    llm_response_text: str | None,
    margin: float,
) -> dict[str, Any]:
    if not items:
        return empty_post_process_result()

    suggestions = extract_post_process_suggestions(llm_response_text)
    warnings: list[str] = []
    changed = 0
    llm_applied = 0
    local_applied = 0

    for item in items:
        original_name = item.nome or ""
        original_code = item.codigo or ""
        original_price = item.preco or ""
        suggestion = suggestions.get(item.ordering_key()) or {}

        next_name = resolve_post_process_name(item, suggestion)
        next_code = resolve_post_process_code(item, suggestion)
        next_price = resolve_post_process_price(item, suggestion)

        modified = False
        if next_name and next_name != original_name:
            item.nome = next_name
            modified = True
        if next_code and next_code != original_code:
            item.codigo = next_code
            modified = True
        if next_price and next_price != original_price:
            item.preco = next_price
            item.preco_final = None
            modified = True

        if modified:
            action_name = str(suggestion.get("acoes") or suggestion.get("action") or "").strip().lower()
            if action_name and action_name not in POST_PROCESS_KEEP_ACTIONS:
                llm_applied += 1
            else:
                local_applied += 1
            item.normalize(margin=margin)
            changed += 1

    if llm_response_text and not suggestions:
        warnings.append("Resposta da IA recebida sem JSON estruturado aproveitavel; aplicadas apenas regras locais seguras.")

    return {
        "total": len(items),
        "modificados": changed,
        "warnings": warnings,
        "llm_suggestions_applied": llm_applied,
        "local_adjustments_applied": local_applied,
        "dry_run": False,
    }
