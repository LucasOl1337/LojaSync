from __future__ import annotations

from types import SimpleNamespace

from app.application.automation.product_payload import (
    build_catalog_description,
    build_incomplete_grades_message,
    find_incomplete_grade_products,
    prepare_grade_tasks,
    product_to_payload,
)
from app.domain.products.entities import CorItem, GradeItem, Product


def test_build_catalog_description_appends_brand_and_code_only_when_missing() -> None:
    product = Product(
        nome="VESTIDO MIDI",
        codigo="ABC123",
        quantidade=2,
        preco="79,90",
        categoria="Feminino",
        marca="Marca",
        descricao_completa="VESTIDO MIDI Marca",
    )

    assert build_catalog_description(product) == "VESTIDO MIDI Marca ABC123"


def test_product_to_payload_uses_sale_price_fallback_and_serializes_variations() -> None:
    product = Product(
        nome="BLUSA",
        codigo="B10",
        quantidade=3,
        preco="20,00",
        categoria="Feminino",
        marca="Loja",
        grades=[GradeItem(tamanho="P", quantidade=1), GradeItem(tamanho="M", quantidade=2)],
        cores=[CorItem(cor="Azul", quantidade=3)],
    )

    payload = product_to_payload(product)

    assert payload["preco_final"] == "20,00"
    assert payload["descricao_completa"] == "BLUSA Loja B10"
    assert payload["grades"] == [{"tamanho": "P", "quantidade": 1}, {"tamanho": "M", "quantidade": 2}]
    assert payload["cores"] == [{"cor": "Azul", "quantidade": 3}]
    assert payload["ordering_key"] == product.ordering_key()


def test_prepare_grade_tasks_skips_invalid_or_zero_quantities_without_losing_valid_sizes() -> None:
    product = Product(
        nome="CALCA",
        codigo="C10",
        quantidade=3,
        preco="30,00",
        categoria="Feminino",
        marca="Loja",
        grades=[
            GradeItem(tamanho="P", quantidade=0),
            SimpleNamespace(tamanho="M", quantidade="x"),
            SimpleNamespace(tamanho="GG", quantidade="2,0"),
            GradeItem(tamanho="G", quantidade=2),
        ],
    )

    assert prepare_grade_tasks([product]) == [{"grades": {"GG": 2, "G": 2}}]


def test_prepare_grade_tasks_combines_repeated_sizes() -> None:
    product = Product(
        nome="CALCA",
        codigo="C10",
        quantidade=4,
        preco="30,00",
        categoria="Feminino",
        marca="Loja",
        grades=[
            GradeItem(tamanho="M", quantidade=1),
            GradeItem(tamanho="M", quantidade=2),
            GradeItem(tamanho=" G ", quantidade=1),
        ],
    )

    assert prepare_grade_tasks([product]) == [{"grades": {"M": 3, "G": 1}}]


def test_find_incomplete_grade_products_treats_invalid_quantities_as_zero() -> None:
    product = Product(
        nome="CALCA",
        codigo="C10",
        quantidade=3,
        preco="30,00",
        categoria="Feminino",
        marca="Loja",
        grades=[GradeItem(tamanho="P", quantidade=1), SimpleNamespace(tamanho="M", quantidade="x")],
    )

    assert find_incomplete_grade_products([product]) == [
        {"nome": "CALCA", "total_grades": 1, "quantidade": 3}
    ]


def test_build_incomplete_grades_message_limits_sample_and_reports_remaining_count() -> None:
    pending = [
        {"nome": "Item 1", "total_grades": 1, "quantidade": 2},
        {"nome": "Item 2", "total_grades": 2, "quantidade": 3},
        {"nome": "Item 3", "total_grades": 3, "quantidade": 4},
        {"nome": "Item 4", "total_grades": 4, "quantidade": 5},
    ]

    message = build_incomplete_grades_message(pending)

    assert "Item 1 (1/2), Item 2 (2/3), Item 3 (3/4)" in message
    assert "e mais 1 item(ns)" in message
