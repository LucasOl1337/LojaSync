from __future__ import annotations

from app.domain.products.entities import Product
from app.domain.products.post_processing import (
    coerce_confidence,
    needs_llm_post_review,
    normalize_price_to_next_tenth,
    price_has_visual_noise,
    sanitize_code_for_store,
    sanitize_store_name,
)


def test_sanitize_store_name_removes_invoice_noise_and_common_ocr_artifacts() -> None:
    assert (
        sanitize_store_name("REGATA CROPPED [50CM] BASICO(A) Cor 00004 Tam 12 *AB-CD* AD")
        == "REGATA CROPPED BASICO"
    )
    assert sanitize_store_name("CALA JOGGER BASICO(A) Cor 00004 Tam 8") == "CALCA JOGGER BASICO"


def test_sanitize_code_for_store_collapses_repeated_or_visual_noise() -> None:
    assert sanitize_code_for_store("AB12-AB12") == "AB12"
    assert sanitize_code_for_store("090840002") == "090840002"
    assert sanitize_code_for_store("AAAAB") == "AAB"


def test_normalize_price_to_next_tenth_ceil_rounds_visual_noise() -> None:
    assert normalize_price_to_next_tenth("20,37") == "20,40"
    assert normalize_price_to_next_tenth("90,91") == "91,00"
    assert normalize_price_to_next_tenth("sem preco") == "sem preco"


def test_price_has_visual_noise_accepts_clean_tenth_cent_values() -> None:
    assert price_has_visual_noise("20,37")
    assert not price_has_visual_noise("20,40")
    assert not price_has_visual_noise("sem preco")


def test_coerce_confidence_clamps_untrusted_values() -> None:
    assert coerce_confidence("0.75") == 0.75
    assert coerce_confidence(2) == 1.0
    assert coerce_confidence(-1) == 0.0
    assert coerce_confidence("n/a") == 0.0


def test_needs_llm_post_review_detects_only_ambiguous_items() -> None:
    noisy = Product(
        nome="REGATA CROPPED 50CM BASICO A COR",
        codigo="1000086766",
        quantidade=5,
        preco="20,37",
        categoria="",
        marca="",
        descricao_completa="REGATA CROPPED 50CM BASICO(A) COR 00004",
    )
    clean = Product(
        nome="EMBALAGEM KRAFT MALWEE KIDS",
        codigo="1000131724",
        quantidade=3,
        preco="19,00",
        categoria="",
        marca="",
        descricao_completa="EMBALAGEM KRAFT MALWEE KIDS",
    )

    assert needs_llm_post_review(noisy)
    assert not needs_llm_post_review(clean)
