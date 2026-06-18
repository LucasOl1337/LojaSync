from __future__ import annotations

from typing import Any

from app.domain.products.entities import Product


def coerce_nonnegative_int(value: Any) -> int:
    try:
        return max(int(value or 0), 0)
    except Exception:
        return 0


def build_catalog_description(product: Product) -> str:
    parts: list[str] = []

    base_description = str(product.descricao_completa or product.nome or "").strip()
    if base_description:
        parts.append(base_description)

    brand = str(product.marca or "").strip()
    code = str(product.codigo or "").strip()

    normalized_description = f" {base_description.casefold()} " if base_description else ""
    if brand and f" {brand.casefold()} " not in normalized_description:
        parts.append(brand)
    if code and f" {code.casefold()} " not in normalized_description:
        parts.append(code)

    description = " ".join(part for part in parts if part).strip()
    if description:
        return description
    return f"{product.nome} {brand} {code}".strip()


def product_to_payload(product: Product) -> dict[str, Any]:
    descricao = build_catalog_description(product)
    grades = [
        {"tamanho": item.tamanho, "quantidade": coerce_nonnegative_int(item.quantidade)}
        for item in (product.grades or [])
    ]
    cores = [
        {"cor": item.cor, "quantidade": coerce_nonnegative_int(item.quantidade)}
        for item in (product.cores or [])
    ]
    return {
        "nome": product.nome,
        "codigo": product.codigo,
        "quantidade": str(product.quantidade),
        "preco": product.preco,
        "preco_final": product.preco_final or product.preco,
        "categoria": product.categoria,
        "marca": product.marca,
        "descricao_completa": descricao,
        "grades": grades if grades else None,
        "cores": cores if cores else None,
        "ordering_key": product.ordering_key(),
    }


def prepare_grade_tasks(products: list[Product]) -> list[dict[str, Any]]:
    tasks: list[dict[str, Any]] = []
    for product in products:
        if not product.grades:
            continue
        grades_map: dict[str, int] = {}
        for item in product.grades:
            size = str(getattr(item, "tamanho", "")).strip()
            qty = coerce_nonnegative_int(getattr(item, "quantidade", 0))
            if size and qty > 0:
                grades_map[size] = qty
        if grades_map:
            tasks.append({"grades": grades_map})
    return tasks


def find_incomplete_grade_products(products: list[Product]) -> list[dict[str, Any]]:
    pending: list[dict[str, Any]] = []
    for product in products:
        if not product.grades:
            continue
        total_grades = sum(coerce_nonnegative_int(getattr(item, "quantidade", 0)) for item in product.grades)
        expected = coerce_nonnegative_int(product.quantidade)
        if total_grades == expected:
            continue
        pending.append(
            {
                "nome": str(product.nome or "").strip() or str(product.codigo or "").strip() or "Item sem nome",
                "total_grades": total_grades,
                "quantidade": expected,
            }
        )
    return pending


def build_incomplete_grades_message(pending: list[dict[str, Any]]) -> str:
    if not pending:
        return "Existem grades pendentes."
    sample = ", ".join(
        f"{item['nome']} ({item['total_grades']}/{item['quantidade']})" for item in pending[:3]
    )
    remaining = len(pending) - min(len(pending), 3)
    suffix = f" e mais {remaining} item(ns)" if remaining > 0 else ""
    return (
        "Nao e possivel executar o Cadastro Completo porque existem grades pendentes: "
        f"{sample}{suffix}. Abra 'Inserir Grade' e finalize esses itens antes de continuar."
    )
