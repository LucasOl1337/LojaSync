from app.domain.products.entities import calculate_sale_price


def test_calculate_sale_price_rounds_to_ninety() -> None:
    assert calculate_sale_price("10,00", 2.06) == "20,90"
