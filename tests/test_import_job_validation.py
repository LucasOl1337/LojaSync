from __future__ import annotations

from app.application.imports.job_validation import (
    append_llm_chat_call_metrics,
    append_process_event,
    build_import_job_metrics,
    build_local_import_text,
    build_local_parser_products,
    evaluate_final_import_validation,
    evaluate_local_parser_attempt,
    evaluate_import_validation,
    prepare_import_batch_metadata,
    prepare_llm_vertical_slice_fallback,
    products_total_quantity,
    resolve_import_content_to_save,
    select_llm_import_result,
    summarize_llm_upload_payload,
)
from app.domain.products.entities import Product


def test_evaluate_import_validation_approves_when_anchor_matches() -> None:
    result = evaluate_import_validation(
        total_items=2,
        remessa_quantity=5,
        quantity_matches_remessa=True,
        document_total_products=None,
        document_total_note=None,
        products_value_matches_document=None,
    )

    assert result["approved"]
    assert not result["rejected"]
    assert not result["unverified"]
    assert result["has_quantity_anchor"]
    assert result["reasons"] == []


def test_evaluate_import_validation_rejects_mismatched_invoice_total() -> None:
    result = evaluate_import_validation(
        total_items=2,
        remessa_quantity=None,
        quantity_matches_remessa=None,
        document_total_products="100,00",
        document_total_note=None,
        products_value_matches_document=False,
    )

    assert not result["approved"]
    assert result["rejected"]
    assert result["reasons"] == ["the extracted product total does not match the invoice total"]
    assert result["reason_codes"] == ["product_total_mismatch"]


def test_evaluate_import_validation_returns_every_rejection_reason_code() -> None:
    result = evaluate_import_validation(
        total_items=0,
        remessa_quantity=3,
        quantity_matches_remessa=False,
        document_total_products="100,00",
        document_total_note=None,
        products_value_matches_document=False,
    )

    assert result["rejected"]
    assert result["reason_codes"] == [
        "no_importable_items",
        "product_total_mismatch",
        "remessa_quantity_mismatch",
    ]


def test_evaluate_import_validation_marks_positive_unanchored_import_as_unverified() -> None:
    result = evaluate_import_validation(
        total_items=2,
        remessa_quantity=None,
        quantity_matches_remessa=None,
        document_total_products=None,
        document_total_note=None,
        products_value_matches_document=None,
    )

    assert not result["approved"]
    assert not result["rejected"]
    assert result["unverified"]


def test_append_process_event_adds_monotonic_indexes_without_losing_existing_events() -> None:
    metrics = {"process_log": [{"index": 1, "source": "local", "level": "info", "message": "started"}]}

    append_process_event(metrics, source="llm", level="warning", message="fallback")

    assert metrics["process_log"] == [
        {"index": 1, "source": "local", "level": "info", "message": "started"},
        {"index": 2, "source": "llm", "level": "warning", "message": "fallback"},
    ]


def test_build_import_job_metrics_initializes_all_import_defaults() -> None:
    metrics = build_import_job_metrics(
        filename="",
        content_type=None,
        file_size_bytes=123,
        llm_base_url="http://llm.local",
        llm_timeout_seconds=45,
    )

    assert metrics == {
        "file_name": "romaneio",
        "content_type": "",
        "file_size_bytes": 123,
        "llm_base_url": "http://llm.local",
        "llm_timeout_seconds": 45,
        "llm_upload_used": False,
        "llm_chat_used": False,
        "llm_chat_calls": 0,
        "llm_chat_total_ms": 0,
        "llm_chat_calls_details": [],
        "upload_documents_chars": 0,
        "upload_images": 0,
        "local_decode_ms": 0,
        "local_text_chars": 0,
        "local_structured_candidates": 0,
        "local_parser_items": 0,
        "local_validation_status": "not_run",
        "llm_fallback_triggered": False,
        "final_validation_status": "pending",
        "process_log": [],
        "selected_source": "",
    }


def test_append_llm_chat_call_metrics_initializes_counters_and_copies_detail() -> None:
    metrics: dict[str, object] = {}
    detail = {
        "chunk": 1,
        "attempt": "full_page",
        "duration_ms": 25,
        "document_chars": 0,
        "images": 2,
    }

    append_llm_chat_call_metrics(metrics, detail)
    detail["duration_ms"] = 99

    assert metrics == {
        "llm_chat_used": True,
        "llm_chat_calls": 1,
        "llm_chat_total_ms": 25,
        "llm_chat_calls_details": [
            {
                "chunk": 1,
                "attempt": "full_page",
                "duration_ms": 25,
                "document_chars": 0,
                "images": 2,
            }
        ],
    }


def test_append_llm_chat_call_metrics_extends_existing_metrics() -> None:
    metrics = {
        "llm_chat_used": False,
        "llm_chat_calls": 1,
        "llm_chat_total_ms": 10,
        "llm_chat_calls_details": [
            {
                "chunk": 1,
                "attempt": "initial",
                "duration_ms": 10,
                "document_chars": 80,
                "images": 0,
            }
        ],
    }

    append_llm_chat_call_metrics(
        metrics,
        {
            "chunk": 2,
            "attempt": "vertical_slices",
            "duration_ms": 15,
            "document_chars": 0,
            "images": 1,
        },
    )

    assert metrics["llm_chat_used"] is True
    assert metrics["llm_chat_calls"] == 2
    assert metrics["llm_chat_total_ms"] == 25
    assert metrics["llm_chat_calls_details"] == [
        {
            "chunk": 1,
            "attempt": "initial",
            "duration_ms": 10,
            "document_chars": 80,
            "images": 0,
        },
        {
            "chunk": 2,
            "attempt": "vertical_slices",
            "duration_ms": 15,
            "document_chars": 0,
            "images": 1,
        },
    ]


def test_summarize_llm_upload_payload_filters_payload_and_reports_metrics() -> None:
    payload = {
        "errors": [" first warning ", "", None],
        "documents": [
            {"name": "nota.txt", "content": "linha inicial"},
            "ignored",
            {
                "name": "rows.txt",
                "content": (
                    "1000135918 CONJUNTO BLUSAO/CALCA Cor 02226 Tam 6M "
                    "6111.20.00 000 6101 PEC 1,000 41,7000 41,70 41,70 5,00 0,00 12,00 0,00"
                ),
            },
        ],
        "images": [{"name": "page-1.png"}, None, {"name": "page-2.png"}],
    }

    summary = summarize_llm_upload_payload(payload)

    assert summary.documents == [
        {"name": "nota.txt", "content": "linha inicial"},
        {
            "name": "rows.txt",
            "content": (
                "1000135918 CONJUNTO BLUSAO/CALCA Cor 02226 Tam 6M "
                "6111.20.00 000 6101 PEC 1,000 41,7000 41,70 41,70 5,00 0,00 12,00 0,00"
            ),
        },
    ]
    assert summary.images == [{"name": "page-1.png"}, {"name": "page-2.png"}]
    assert summary.documents_text.startswith("linha inicial")
    assert summary.structured_row_count == 1
    assert summary.metrics == {
        "upload_documents_chars": len(summary.documents_text),
        "upload_images": 2,
        "upload_structured_candidates": 1,
    }
    assert summary.warnings == [" first warning ", "None"]
    assert summary.event == {
        "source": "llm",
        "level": "info",
        "message": "LLM upload prepared 2 document(s), 2 image(s), and 1 structured candidate row(s).",
    }


def test_summarize_llm_upload_payload_handles_non_dict_payload() -> None:
    summary = summarize_llm_upload_payload(["not", "a", "dict"])

    assert summary.documents == []
    assert summary.images == []
    assert summary.documents_text == ""
    assert summary.structured_row_count == 0
    assert summary.metrics == {
        "upload_documents_chars": 0,
        "upload_images": 0,
        "upload_structured_candidates": 0,
    }
    assert summary.warnings == []
    assert summary.event["message"] == "LLM upload prepared 0 document(s), 0 image(s), and 0 structured candidate row(s)."


def test_prepare_llm_vertical_slice_fallback_builds_batches_warning_event_and_metrics() -> None:
    images = [{"name": "page#p1", "data": "not-a-real-image"}]

    fallback = prepare_llm_vertical_slice_fallback(
        images=images,
        image_batch_size=2,
        full_page_total=1,
        fallback_slices=3,
        llm_candidates=[],
    )

    assert fallback.enabled
    assert fallback.image_batches == [[images[0]]]
    assert fallback.metrics["llm_chunk_count"] == 2
    assert fallback.metrics["llm_recovery_attempt"] == "vertical_slices"
    assert fallback.metrics["llm_recovery_forced"] is False
    assert fallback.warnings == [
        "OCR por pagina inteira sem itens validos; tentando recortes verticais como fallback."
    ]
    assert fallback.event == {
        "source": "llm",
        "level": "warning",
        "message": "Full-page OCR fallback returned no valid items; trying vertical slices.",
    }


def test_prepare_llm_vertical_slice_fallback_is_disabled_when_candidates_exist() -> None:
    candidate = Product(nome="CAMISETA", codigo="C200", quantidade=1, preco="20,00", categoria="", marca="")

    fallback = prepare_llm_vertical_slice_fallback(
        images=[{"name": "page#p1"}],
        image_batch_size=1,
        full_page_total=1,
        fallback_slices=4,
        llm_candidates=[candidate],
    )

    assert not fallback.enabled
    assert fallback.image_batches == []
    assert fallback.metrics == {}
    assert fallback.warnings == []
    assert fallback.event is None


def test_build_local_parser_products_coerces_invalid_quantities_without_raising() -> None:
    payload = {
        "items": [
            {
                "nome": "CALCA",
                "codigo": "C10",
                "quantidade": "x",
                "preco": "30,00",
                "cor": "Azul",
            }
        ]
    }

    products = build_local_parser_products(payload)

    assert len(products) == 1
    assert products[0].quantidade == 0
    assert products[0].cores is None


def test_build_local_parser_products_can_attach_local_import_metadata() -> None:
    payload = {
        "items": [
            {
                "nome": "CAMISETA",
                "codigo": "C20",
                "quantidade": 2,
                "preco": "20,00",
                "cor": "Preto",
            }
        ]
    }

    products = build_local_parser_products(
        payload,
        import_source_name="  romaneio-local.pdf  ",
        import_batch_id="batch-123",
        source_type="romaneio_local",
        pending_grade_import=False,
    )

    assert len(products) == 1
    assert products[0].source_type == "romaneio_local"
    assert products[0].import_batch_id == "batch-123"
    assert products[0].import_source_name == "romaneio-local.pdf"
    assert products[0].pending_grade_import is False
    assert products[0].cores == [{"cor": "Preto", "quantidade": 2}]


def test_evaluate_local_parser_attempt_returns_decision_metrics_and_products() -> None:
    payload = {
        "total_rows": 2,
        "total_itens": 1,
        "remessa_quantity": 2,
        "quantity_matches_remessa": True,
        "document_total_products": "40,00",
        "document_total_note": None,
        "extracted_total_products": "40,00",
        "products_value_matches_document": True,
        "warnings": ["minor parser warning"],
        "metrics": {"text_chars": 250, "ocr_pages_used": 1},
        "items": [
            {
                "nome": "CAMISETA",
                "codigo": "C20",
                "quantidade": 2,
                "preco": "20,00",
                "cor": "Preto",
            }
        ],
    }

    result = evaluate_local_parser_attempt(payload, decode_ms=37)

    assert result.approved_for_import
    assert result.fallback_message is None
    assert result.payload_warnings == ["minor parser warning"]
    assert result.validation["approved"]
    assert len(result.products) == 1
    assert result.products[0].codigo == "C20"
    assert result.metrics == {
        "local_decode_ms": 37,
        "local_text_chars": 250,
        "local_structured_candidates": 2,
        "local_parser_items": 1,
        "local_ocr_pages_used": 1,
        "local_document_total_products": "40,00",
        "local_document_total_note": None,
        "local_extracted_total_products": "40,00",
        "local_remessa_quantity": 2,
        "local_quantity_matches_remessa": True,
        "local_products_value_matches_document": True,
        "local_warnings": ["minor parser warning"],
        "local_validation_status": "approved",
    }


def test_evaluate_local_parser_attempt_reports_fallback_reason() -> None:
    payload = {
        "total_rows": 1,
        "total_itens": 1,
        "remessa_quantity": None,
        "quantity_matches_remessa": None,
        "document_total_products": "100,00",
        "document_total_note": None,
        "products_value_matches_document": False,
        "warnings": ["printed total mismatch"],
        "items": [
            {
                "nome": "CAMISETA",
                "codigo": "C20",
                "quantidade": 1,
                "preco": "20,00",
            }
        ],
    }

    result = evaluate_local_parser_attempt(payload, decode_ms=0)

    assert not result.approved_for_import
    assert result.validation["rejected"]
    assert result.payload_warnings == ["printed total mismatch"]
    assert result.fallback_message == (
        "Local parser not approved: the extracted product total does not match the invoice total."
    )


def test_select_llm_import_result_filters_candidates_and_merges_analysis_metrics() -> None:
    upload_text = "\n".join(
        [
            "Qtd de Peças da Remessa: 2",
            "Valor total dos produtos 40,00",
        ]
    )
    candidates = [
        Product(nome="CAMISETA", codigo="C200", quantidade=2, preco="20,00", categoria="", marca=""),
    ]

    result = select_llm_import_result(
        upload_docs_text=upload_text,
        selected_text="",
        llm_text="raw llm text",
        llm_candidates=candidates,
    )

    assert len(result.products) == 1
    assert result.products[0].codigo == "C200"
    assert result.products[0].quantidade == 2
    assert result.selected_source == "llm"
    assert result.selected_text == "raw llm text"
    assert result.warnings == []
    assert result.metrics["llm_quantity_matches_remessa"] is True
    assert result.metrics["llm_selected_quantity"] == 2
    assert result.metrics["remessa_quantity"] == 2
    assert result.metrics["quantity_matches_remessa"] is True
    assert result.metrics["document_total_products"] == "40,00"
    assert result.metrics["products_value_matches_document"] is True


def test_select_llm_import_result_parses_text_when_candidates_are_empty() -> None:
    result = select_llm_import_result(
        upload_docs_text="Qtd de Peças da Remessa: 1",
        selected_text="",
        llm_text='{"items":[{"codigo":"C200","nome_curto":"CAMISETA","quantidade":1,"preco":20.0}]}',
        llm_candidates=[],
    )

    assert len(result.products) == 1
    assert result.products[0].codigo == "C200"
    assert result.selected_source == "llm"
    assert result.selected_text.startswith('{"items"')
    assert result.metrics["llm_quantity_matches_remessa"] is True
    assert result.metrics["llm_selected_quantity"] == 1


def test_evaluate_final_import_validation_returns_success_event() -> None:
    decision = evaluate_final_import_validation(
        total_items=2,
        remessa_quantity=2,
        quantity_matches_remessa=True,
        document_total_products=None,
        document_total_note=None,
        products_value_matches_document=None,
        selected_source="local",
    )

    assert decision.validation["approved"]
    assert decision.metrics == {
        "final_validation_status": "approved",
        "final_validation_reasons": [],
        "final_validation_reason_codes": [],
    }
    assert decision.warnings == []
    assert decision.event == {
        "source": "local",
        "level": "success",
        "message": "Import approved by automatic validation.",
    }


def test_evaluate_final_import_validation_warns_when_unverified() -> None:
    decision = evaluate_final_import_validation(
        total_items=2,
        remessa_quantity=None,
        quantity_matches_remessa=None,
        document_total_products=None,
        document_total_note=None,
        products_value_matches_document=None,
        selected_source="",
    )

    warning = (
        "Import completed without printed totals or remessa quantity to validate against. "
        "Result is unverified and needs manual review — not a fully validated success."
    )
    assert decision.validation["unverified"]
    assert decision.metrics["final_validation_status"] == "unverified"
    assert decision.metrics["final_validation_reasons"] == []
    assert decision.metrics["final_validation_reason_codes"] == []
    assert decision.warnings == [warning]
    assert decision.event == {
        "source": "system",
        "level": "warning",
        "message": warning,
    }


def test_evaluate_final_import_validation_blocks_mismatched_totals() -> None:
    decision = evaluate_final_import_validation(
        total_items=2,
        remessa_quantity=None,
        quantity_matches_remessa=None,
        document_total_products="100,00",
        document_total_note=None,
        products_value_matches_document=False,
        selected_source="llm",
    )

    message = "Import blocked after validation: the extracted product total does not match the invoice total"
    assert decision.validation["rejected"]
    assert decision.metrics["final_validation_status"] == "rejected"
    assert decision.metrics["final_validation_reasons"] == [
        "the extracted product total does not match the invoice total"
    ]
    assert decision.metrics["final_validation_reason_codes"] == ["product_total_mismatch"]
    assert decision.warnings == [message]
    assert decision.event == {
        "source": "llm",
        "level": "error",
        "message": message,
    }


def test_resolve_import_content_to_save_prefers_selected_text() -> None:
    product = Product(nome="CAMISETA", codigo="C200", quantidade=1, preco="20,00", categoria="", marca="")

    assert (
        resolve_import_content_to_save(
            selected_text="codigo|nome\nC200|CAMISETA",
            llm_text="ignored",
            products=[product],
        )
        == "codigo|nome\nC200|CAMISETA"
    )


def test_resolve_import_content_to_save_discards_binary_blob_and_serializes_products() -> None:
    product = Product(nome="CAMISETA", codigo="C200", quantidade=2, preco="20,00", categoria="", marca="")
    blob_like_text = "A" * 130

    result = resolve_import_content_to_save(
        selected_text=blob_like_text,
        llm_text="",
        products=[product],
    )

    assert result == "codigo|nome|quantidade|preco\nC200|CAMISETA|2|20,00"


def test_resolve_import_content_to_save_returns_empty_without_text_or_products() -> None:
    assert resolve_import_content_to_save(selected_text="", llm_text="", products=[]) == ""


def test_prepare_import_batch_metadata_marks_products_and_metrics() -> None:
    products = [
        Product(nome="CAMISETA", codigo="C200", quantidade=2, preco="20,00", categoria="", marca=""),
        Product(nome="CALCA", codigo="C300", quantidade=1, preco="30,00", categoria="", marca=""),
    ]

    prepared = prepare_import_batch_metadata(
        products,
        job_id="job-123",
        filename="  romaneio.pdf  ",
        grade_preview_summary={
            "originais": 3,
            "resultantes": 2,
            "removidos": 1,
            "atualizados_grades": 2,
        },
    )

    assert prepared.import_batch_id == "job-123"
    assert prepared.grades_available is True
    assert prepared.grade_preview_summary == {
        "originais": 3,
        "resultantes": 2,
        "removidos": 1,
        "atualizados_grades": 2,
    }
    assert prepared.metrics == {
        "import_compact_removed": 1,
        "import_compact_groups": 2,
        "import_grades_available": True,
        "selected_items": 2,
    }
    assert {item.source_type for item in products} == {"romaneio"}
    assert {item.import_batch_id for item in products} == {"job-123"}
    assert {item.import_source_name for item in products} == {"romaneio.pdf"}
    assert all(item.pending_grade_import for item in products)


def test_prepare_import_batch_metadata_handles_empty_products() -> None:
    prepared = prepare_import_batch_metadata(
        [],
        job_id="job-123",
        filename="",
        grade_preview_summary={},
    )

    assert prepared.import_batch_id is None
    assert prepared.grades_available is False
    assert prepared.grade_preview_summary == {
        "originais": 0,
        "resultantes": 0,
        "removidos": 0,
        "atualizados_grades": 0,
    }
    assert prepared.metrics == {
        "import_compact_removed": 0,
        "import_compact_groups": 0,
        "import_grades_available": False,
        "selected_items": 0,
    }


def test_build_local_import_text_serializes_local_parser_items() -> None:
    payload = {
        "items": [
            {
                "codigo": " C20 ",
                "nome": " CAMISETA ",
                "cor": " Preto ",
                "quantidade": "2",
                "preco": "20,00",
                "grades": [
                    {"tamanho": "P", "quantidade": "1"},
                    {"tamanho": "M", "quantidade": 1},
                ],
            }
        ]
    }

    assert build_local_import_text(payload) == (
        "codigo|nome|cor|quantidade|preco|grades\n"
        "C20|CAMISETA|Preto|2|20,00|P:1,M:1"
    )


def test_build_local_import_text_coerces_invalid_quantities_without_raising() -> None:
    payload = {
        "items": [
            {
                "codigo": "C30",
                "nome": "BLUSA",
                "cor": "Verde",
                "quantidade": "x",
                "preco": "15,00",
                "grades": [
                    {"tamanho": "G", "quantidade": "invalid"},
                    "ignored",
                ],
            }
        ]
    }

    assert build_local_import_text(payload) == (
        "codigo|nome|cor|quantidade|preco|grades\n"
        "C30|BLUSA|Verde|0|15,00|G:0"
    )


def test_products_total_quantity_ignores_invalid_or_negative_values() -> None:
    product = Product(nome="A", codigo="1", quantidade=2, preco="1,00", categoria="", marca="")
    invalid = Product(nome="B", codigo="2", quantidade=1, preco="1,00", categoria="", marca="")
    invalid.quantidade = "x"  # type: ignore[assignment]
    negative = Product(nome="C", codigo="3", quantidade=-5, preco="1,00", categoria="", marca="")

    assert products_total_quantity([product, invalid, negative]) == 2
