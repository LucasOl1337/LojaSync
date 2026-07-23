"""Offline regression tests for the evidence-first romaneio extraction pipeline."""

from __future__ import annotations

import os

from app.application.imports.evidence_pipeline import (
    DocumentEvidence,
    apply_evidence_to_metrics,
    assess_completeness,
    build_import_outcome,
    choose_better_candidate_set,
    deduplicate_products,
    extract_document_evidence,
    find_implausible_quantities,
    import_pipeline_mode,
    merge_product_passes,
    product_fingerprint,
    products_total_quantity,
    use_evidence_pipeline,
)
from app.application.imports.job_validation import (
    evaluate_final_import_validation,
    evaluate_import_validation,
    prepare_llm_vertical_slice_fallback,
)
from app.domain.products.entities import Product


def _product(codigo: str, nome: str, quantidade: int, preco: str = "10,00") -> Product:
    return Product(
        nome=nome,
        codigo=codigo,
        quantidade=quantidade,
        preco=preco,
        categoria="",
        marca="",
    )


def _evidence(
    *,
    remessa: int | None = 12,
    total_products: str | None = "1258,80",
    rows: int = 12,
    text: str = "",
) -> DocumentEvidence:
    body = text
    if not body:
        parts = []
        if remessa is not None:
            parts.append(f"Qtd de volumes da remessa: {remessa}")
        if total_products:
            parts.append(f"VALOR TOTAL DOS PRODUTOS {total_products}")
        body = "\n".join(parts)
    return DocumentEvidence(
        text=body,
        page_hint=2,
        structured_row_count=rows,
        remessa_quantity=remessa,
        document_total_products=total_products,
        document_total_note=None,
        source="test",
        warnings=[],
    )


def test_import_pipeline_defaults_to_evidence() -> None:
    saved = {
        key: os.environ.pop(key, None)
        for key in ("LOJASYNC_IMPORT_PIPELINE", "IMPORT_PIPELINE")
    }
    try:
        assert import_pipeline_mode() == "evidence"
        assert use_evidence_pipeline() is True
    finally:
        for key, value in saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def test_import_pipeline_legacy_flag() -> None:
    saved = os.environ.get("LOJASYNC_IMPORT_PIPELINE")
    os.environ["LOJASYNC_IMPORT_PIPELINE"] = "legacy"
    try:
        assert import_pipeline_mode() == "legacy"
        assert use_evidence_pipeline() is False
    finally:
        if saved is None:
            os.environ.pop("LOJASYNC_IMPORT_PIPELINE", None)
        else:
            os.environ["LOJASYNC_IMPORT_PIPELINE"] = saved


def test_extract_document_evidence_reads_remessa_and_totals() -> None:
    text = (
        "Qtd de volumes da remessa: 12\n"
        "VALOR TOTAL DOS PRODUTOS 1.258,80\n"
        "VALOR TOTAL DA NOTA 1.258,80\n"
    )
    evidence = extract_document_evidence(text.encode("utf-8"), "romaneio.txt", "text/plain")
    assert evidence.remessa_quantity == 12
    assert evidence.document_total_products is not None
    assert evidence.has_quantity_anchor
    assert evidence.has_total_anchor
    assert evidence.metrics()["evidence_remessa_quantity"] == 12


def test_assess_completeness_flags_minimax_shaped_qty_shortfall() -> None:
    """Historical imperfect case: qty 10 vs remessa 12 must need recovery."""
    products = [
        _product("10001", "ITEM A", 5, "104,90"),
        _product("10002", "ITEM B", 5, "104,90"),
    ]
    assessment = assess_completeness(products, _evidence(remessa=12, total_products="1258,80", rows=12))
    assert assessment.total_quantity == 10
    assert assessment.quantity_matches is False
    assert assessment.incomplete is True
    assert assessment.needs_recovery is True
    assert any("quantity_mismatch" in reason for reason in assessment.reasons)


def test_assess_completeness_passes_when_qty_matches() -> None:
    products = [_product("10001", "ITEM A", 12, "104,90")]
    assessment = assess_completeness(products, _evidence(remessa=12, total_products=None, rows=0))
    assert assessment.quantity_matches is True
    assert assessment.needs_recovery is False


def test_vertical_fallback_enabled_for_partial_nonempty_candidates() -> None:
    candidate = _product("C200", "CAMISETA", 1, "20,00")
    fallback = prepare_llm_vertical_slice_fallback(
        images=[{"name": "page#p1", "data": "not-a-real-image"}],
        image_batch_size=1,
        full_page_total=1,
        fallback_slices=2,
        llm_candidates=[candidate],
        incomplete=True,
        overlap_ratio=0.12,
    )
    assert fallback.enabled is True
    assert fallback.metrics["llm_recovery_forced"] is True
    assert "incompleta" in fallback.warnings[0].lower() or "incomplete" in (fallback.event or {}).get("message", "").lower()


def test_vertical_fallback_still_disabled_when_complete_candidates_exist() -> None:
    candidate = _product("C200", "CAMISETA", 1, "20,00")
    fallback = prepare_llm_vertical_slice_fallback(
        images=[{"name": "page#p1"}],
        image_batch_size=1,
        full_page_total=1,
        fallback_slices=4,
        llm_candidates=[candidate],
        incomplete=False,
        force_recovery=False,
    )
    assert fallback.enabled is False


def test_vertical_fallback_still_enabled_for_empty_candidates() -> None:
    fallback = prepare_llm_vertical_slice_fallback(
        images=[{"name": "page#p1", "data": "x"}],
        image_batch_size=1,
        full_page_total=1,
        fallback_slices=3,
        llm_candidates=[],
    )
    assert fallback.enabled is True


def test_deduplicate_products_preserves_identical_rows_without_provenance() -> None:
    a = _product("100", "CAMISA", 1, "10,00")
    b = _product("100", "CAMISA", 1, "10,00")
    result = deduplicate_products([a, b])
    assert len(result) == 2
    assert products_total_quantity(result) == 2


def test_merge_product_passes_deduplicates_overlap_by_occurrence() -> None:
    primary = [_product("100", "CAMISA", 1), _product("100", "CAMISA", 1)]
    recovery = [
        _product("100", "CAMISA", 1),
        _product("100", "CAMISA", 1),
        _product("200", "CALCA", 1),
    ]
    result = merge_product_passes(primary, recovery)
    assert len(result) == 3
    assert products_total_quantity(result) == 3


def test_image_without_local_evidence_requires_recovery() -> None:
    evidence = DocumentEvidence(
        text="",
        page_hint=0,
        structured_row_count=0,
        remessa_quantity=None,
        document_total_products=None,
        document_total_note=None,
        source="empty",
        warnings=[],
    )
    assessment = assess_completeness([_product("100", "CAMISA", 1)], evidence)
    assert assessment.incomplete is True
    assert assessment.needs_recovery is True
    assert "image_without_local_evidence" in assessment.reasons


def test_choose_better_candidate_set_prefers_full_qty() -> None:
    primary = [_product("A", "X", 10)]
    recovery = [_product("A", "X", 6), _product("B", "Y", 6)]
    evidence = _evidence(remessa=12, total_products=None, rows=2)
    chosen, source, assessment = choose_better_candidate_set(primary, recovery, evidence)
    assert source in {"recovery", "merged"}
    assert assessment.total_quantity >= 10
    assert products_total_quantity(chosen) >= 10


def test_find_implausible_quantities() -> None:
    items = [_product("A", "X", 2), _product("B", "Y", 17011)]
    flagged = find_implausible_quantities(items, max_unit_qty=5000)
    assert len(flagged) == 1
    assert flagged[0]["quantidade"] == 17011


def test_apply_evidence_to_metrics_fills_missing_anchors() -> None:
    metrics: dict = {}
    products = [_product("A", "X", 10, "100,00")]
    evidence = _evidence(remessa=12, total_products="1258,80")
    apply_evidence_to_metrics(metrics, evidence, products)
    assert metrics["remessa_quantity"] == 12
    assert metrics["quantity_matches_remessa"] is False
    assert metrics["document_total_products"] is not None


def test_build_import_outcome_unverified_is_needs_review() -> None:
    validation = evaluate_import_validation(
        total_items=2,
        remessa_quantity=None,
        quantity_matches_remessa=None,
        document_total_products=None,
        document_total_note=None,
        products_value_matches_document=None,
    )
    outcome = build_import_outcome(validation=validation)
    assert validation["unverified"] is True
    assert outcome.outcome == "needs_review"
    assert outcome.result_status == "needs_review"
    assert outcome.final_validation_status == "unverified"
    assert outcome.metrics["import_needs_review"] is True
    assert any("revis" in w.lower() or "SEM validação" in w or "sem valid" in w.lower() for w in outcome.warnings)


def test_build_import_outcome_approved_ok() -> None:
    validation = evaluate_import_validation(
        total_items=2,
        remessa_quantity=5,
        quantity_matches_remessa=True,
        document_total_products=None,
        document_total_note=None,
        products_value_matches_document=None,
    )
    outcome = build_import_outcome(validation=validation)
    assert outcome.outcome == "approved"
    assert outcome.result_status == "ok"


def test_build_import_outcome_rejected() -> None:
    validation = evaluate_import_validation(
        total_items=2,
        remessa_quantity=12,
        quantity_matches_remessa=False,
        document_total_products=None,
        document_total_note=None,
        products_value_matches_document=None,
    )
    outcome = build_import_outcome(validation=validation)
    assert outcome.outcome == "rejected"
    assert validation["rejected"] is True


def test_evidence_anchored_qty_mismatch_rejects_not_unverified() -> None:
    """Once remessa anchors exist, partial vision results must reject, not silently unverified."""
    validation = evaluate_import_validation(
        total_items=4,
        remessa_quantity=12,
        quantity_matches_remessa=False,
        document_total_products="1258,80",
        document_total_note=None,
        products_value_matches_document=False,
    )
    assert validation["rejected"] is True
    assert validation["unverified"] is False
    decision = evaluate_final_import_validation(
        total_items=4,
        remessa_quantity=12,
        quantity_matches_remessa=False,
        document_total_products="1258,80",
        document_total_note=None,
        products_value_matches_document=False,
        selected_source="llm",
    )
    assert decision.metrics["final_validation_status"] == "rejected"


def test_unverified_warning_mentions_manual_review() -> None:
    decision = evaluate_final_import_validation(
        total_items=2,
        remessa_quantity=None,
        quantity_matches_remessa=None,
        document_total_products=None,
        document_total_note=None,
        products_value_matches_document=None,
        selected_source="llm",
    )
    assert decision.validation["unverified"] is True
    assert decision.metrics["final_validation_status"] == "unverified"
    assert any("review" in w.lower() or "manual" in w.lower() or "validat" in w.lower() for w in decision.warnings)


def test_product_fingerprint_stable() -> None:
    a = _product("ab", "Name", 1, "1,00")
    b = _product("AB", "name", 1, "1,00")
    # nome is uppercased in fingerprint
    assert product_fingerprint(a)[0] == product_fingerprint(b)[0]
