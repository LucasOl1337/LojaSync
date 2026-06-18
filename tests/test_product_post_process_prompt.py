from __future__ import annotations

from app.application.products.post_process_prompt import (
    build_post_process_context_text,
    build_post_process_message,
    build_post_process_products_text,
)
from app.domain.products.entities import Product


def test_build_post_process_products_text_sanitizes_table_delimiters_and_newlines() -> None:
    product = Product(
        nome="BLUSA | MANGA\nLONGA",
        codigo="A|10",
        quantidade=2,
        preco="29,90",
        categoria="",
        marca="",
        descricao_completa="BLUSA\nMANGA | LONGA",
    )

    text = build_post_process_products_text([product])

    lines = text.splitlines()
    assert lines[0] == "ordering_key|codigo|nome|descricao_completa|quantidade|preco"
    assert len(lines) == 2
    assert lines[1].count("|") == 5
    assert "BLUSA / MANGA LONGA" in lines[1]
    assert "A/10" in lines[1]


def test_build_post_process_products_text_returns_empty_for_no_products() -> None:
    assert build_post_process_products_text([]) == ""


def test_build_post_process_context_text_reports_scope_counts() -> None:
    product = Product(nome="A", codigo="1", quantidade=1, preco="1,00", categoria="", marca="")

    text = build_post_process_context_text(total_products=10, review_products=[product])

    assert "total_produtos_lista=10" in text
    assert "total_produtos_para_revisao=1" in text


def test_build_post_process_message_keeps_required_json_contract() -> None:
    message = build_post_process_message()

    assert "Retorne JSON com uma lista 'items'" in message
    assert "ordering_key" in message
    assert "ajustar_preco" in message
