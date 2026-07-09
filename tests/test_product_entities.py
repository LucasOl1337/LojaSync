from __future__ import annotations

from app.domain.products.entities import Product, parse_non_negative_quantity


def test_parse_non_negative_quantity_accepts_decimal_strings() -> None:
    assert parse_non_negative_quantity("2.0") == 2
    assert parse_non_negative_quantity("3,0") == 3


def test_product_from_dict_coerces_invalid_or_negative_quantity_to_zero() -> None:
    invalid = Product.from_dict(
        {
            "nome": "Legado Invalido",
            "codigo": "LEG-1",
            "quantidade": "x",
            "preco": "10,00",
            "categoria": "",
            "marca": "",
        }
    )
    negative = Product.from_dict(
        {
            "nome": "Legado Negativo",
            "codigo": "LEG-2",
            "quantidade": "-5",
            "preco": "10,00",
            "categoria": "",
            "marca": "",
        }
    )

    assert invalid.quantidade == 0
    assert negative.quantidade == 0


def test_product_normalize_coerces_invalid_quantity_to_zero() -> None:
    product = Product(
        nome="Produto",
        codigo="P-1",
        quantidade=1,
        preco="10,00",
        categoria="",
        marca="",
    )
    product.quantidade = "x"  # type: ignore[assignment]

    product.normalize(margin=1.0)

    assert product.quantidade == 0
