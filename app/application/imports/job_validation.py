from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.application.imports.parsing import (
    analyze_parsed_document,
    extract_structured_invoice_row_lines,
    filter_suspect_records,
    looks_like_binary_blob,
    parse_candidate_content,
    products_to_text,
    slice_image_payloads,
    split_image_batches,
)
from app.domain.products.entities import Product


@dataclass(frozen=True, slots=True)
class LocalParserAttempt:
    products: list[Product]
    validation: dict[str, Any]
    metrics: dict[str, Any]
    approved_for_import: bool
    fallback_message: str | None
    payload_warnings: list[str]


@dataclass(frozen=True, slots=True)
class LlmImportSelection:
    products: list[Product]
    selected_source: str
    selected_text: str
    metrics: dict[str, Any]
    warnings: list[str]


@dataclass(frozen=True, slots=True)
class LlmUploadSummary:
    documents: list[dict[str, Any]]
    images: list[dict[str, Any]]
    documents_text: str
    structured_row_count: int
    metrics: dict[str, Any]
    warnings: list[str]
    event: dict[str, str]


@dataclass(frozen=True, slots=True)
class LlmVerticalSliceFallback:
    enabled: bool
    image_batches: list[list[dict[str, Any]]]
    metrics: dict[str, Any]
    warnings: list[str]
    event: dict[str, str] | None


@dataclass(frozen=True, slots=True)
class FinalImportValidationDecision:
    validation: dict[str, Any]
    metrics: dict[str, Any]
    warnings: list[str]
    event: dict[str, str]


@dataclass(frozen=True, slots=True)
class ImportBatchPreparation:
    import_batch_id: str | None
    grades_available: bool
    grade_preview_summary: dict[str, int]
    metrics: dict[str, Any]


VALIDATION_REASON_CODES = {
    "no importable items were detected": "no_importable_items",
    "the extracted product total does not match the invoice total": "product_total_mismatch",
    "the extracted quantity does not match the remessa quantity": "remessa_quantity_mismatch",
}

VALIDATION_REASON_MESSAGES_PT_BR = {
    "no_importable_items": "A IA não encontrou itens de produto que pudessem ser importados.",
    "product_total_mismatch": "A soma dos produtos extraídos não confere com o total de produtos impresso na nota.",
    "remessa_quantity_mismatch": "A quantidade extraída não confere com a quantidade da remessa.",
}


def build_validation_rejection_message(reason_codes: list[str]) -> str:
    reasons = [VALIDATION_REASON_MESSAGES_PT_BR[code] for code in reason_codes if code in VALIDATION_REASON_MESSAGES_PT_BR]
    if not reasons:
        return "Importação bloqueada porque a validação da nota foi rejeitada."
    return "Importação bloqueada. " + " ".join(reasons)


def coerce_nonnegative_int(value: Any) -> int:
    try:
        return max(int(value or 0), 0)
    except Exception:
        return 0


def products_total_quantity(items: list[Product]) -> int:
    return sum(coerce_nonnegative_int(getattr(item, "quantidade", 0)) for item in items)


def append_process_event(
    metrics: dict[str, Any],
    *,
    source: str,
    level: str,
    message: str,
) -> None:
    events = list(metrics.get("process_log") or [])
    events.append(
        {
            "index": len(events) + 1,
            "source": source,
            "level": level,
            "message": message,
        }
    )
    metrics["process_log"] = events


def build_import_job_metrics(
    *,
    filename: str,
    content_type: str | None,
    file_size_bytes: int,
    llm_base_url: str,
    llm_timeout_seconds: int | float,
) -> dict[str, Any]:
    return {
        "file_name": filename or "romaneio",
        "content_type": content_type or "",
        "file_size_bytes": int(file_size_bytes or 0),
        "llm_base_url": llm_base_url,
        "llm_timeout_seconds": llm_timeout_seconds,
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


def append_llm_chat_call_metrics(metrics: dict[str, Any], call_detail: dict[str, Any]) -> None:
    detail = dict(call_detail)
    duration_ms = coerce_nonnegative_int(detail.get("duration_ms"))
    detail["duration_ms"] = duration_ms

    metrics["llm_chat_used"] = True
    metrics["llm_chat_calls"] = coerce_nonnegative_int(metrics.get("llm_chat_calls")) + 1
    metrics["llm_chat_total_ms"] = coerce_nonnegative_int(metrics.get("llm_chat_total_ms")) + duration_ms
    details = list(metrics.get("llm_chat_calls_details") or [])
    details.append(detail)
    metrics["llm_chat_calls_details"] = details


def summarize_llm_upload_payload(upload_data: Any) -> LlmUploadSummary:
    payload = upload_data if isinstance(upload_data, dict) else {}
    upload_errors = payload.get("errors") if isinstance(payload.get("errors"), list) else []
    warnings = [str(item) for item in upload_errors if str(item).strip()]

    raw_documents = payload.get("documents")
    documents = [doc for doc in raw_documents if isinstance(doc, dict)] if isinstance(raw_documents, list) else []
    raw_images = payload.get("images")
    images = [img for img in raw_images if isinstance(img, dict)] if isinstance(raw_images, list) else []

    documents_text = "\n\n".join(str(doc.get("content") or "") for doc in documents).strip()
    structured_row_count = len(extract_structured_invoice_row_lines(documents_text))
    event = {
        "source": "llm",
        "level": "info",
        "message": (
            f"LLM upload prepared {len(documents)} document(s), {len(images)} image(s), "
            f"and {structured_row_count} structured candidate row(s)."
        ),
    }

    return LlmUploadSummary(
        documents=documents,
        images=images,
        documents_text=documents_text,
        structured_row_count=structured_row_count,
        metrics={
            "upload_documents_chars": len(documents_text or ""),
            "upload_images": len(images),
            "upload_structured_candidates": structured_row_count,
        },
        warnings=warnings,
        event=event,
    )


def prepare_llm_vertical_slice_fallback(
    *,
    images: list[dict[str, Any]],
    image_batch_size: int,
    full_page_total: int,
    fallback_slices: int,
    llm_candidates: list[Product],
    force_recovery: bool = False,
    incomplete: bool = False,
    overlap_ratio: float = 0.0,
) -> LlmVerticalSliceFallback:
    """Prepare vertical-slice recovery for empty or incomplete vision results.

    Historical behavior only retried when candidates were empty. Evidence-first
    mode also retries when candidates exist but completeness gates fail
    (quantity/total shortfalls vs document anchors).
    """
    has_candidates = bool(llm_candidates)
    if coerce_nonnegative_int(fallback_slices) <= 1:
        return LlmVerticalSliceFallback(
            enabled=False,
            image_batches=[],
            metrics={},
            warnings=[],
            event=None,
        )
    if has_candidates and not force_recovery and not incomplete:
        return LlmVerticalSliceFallback(
            enabled=False,
            image_batches=[],
            metrics={},
            warnings=[],
            event=None,
        )

    image_inputs = slice_image_payloads(
        images,
        vertical_slices=fallback_slices,
        overlap_ratio=overlap_ratio,
    )
    image_batches = split_image_batches(image_inputs, batch_size=image_batch_size)
    if has_candidates and (force_recovery or incomplete):
        warning = (
            "Leitura visual incompleta em relacao as ancoras do documento; "
            "tentando recortes verticais sobrepostos para recuperar linhas."
        )
        event_message = (
            "Vision extraction incomplete versus document evidence; trying overlapping vertical slices."
        )
        attempt = "recovery_slices"
    else:
        warning = "OCR por pagina inteira sem itens validos; tentando recortes verticais como fallback."
        event_message = "Full-page OCR fallback returned no valid items; trying vertical slices."
        attempt = "vertical_slices"

    return LlmVerticalSliceFallback(
        enabled=True,
        image_batches=image_batches,
        metrics={
            "llm_chunk_count": coerce_nonnegative_int(full_page_total) + len(image_batches),
            "llm_recovery_attempt": attempt,
            "llm_recovery_forced": bool(force_recovery or incomplete),
            "llm_recovery_overlap_ratio": float(overlap_ratio or 0.0),
        },
        warnings=[warning],
        event={
            "source": "llm",
            "level": "warning",
            "message": event_message,
        },
    )


def build_local_parser_products(
    payload: dict[str, Any],
    *,
    import_source_name: str | None = None,
    import_batch_id: str | None = None,
    source_type: str | None = None,
    pending_grade_import: bool | None = None,
) -> list[Product]:
    products: list[Product] = []
    normalized_source_name = str(import_source_name or "").strip() or None
    for raw in payload.get("items") or []:
        if not isinstance(raw, dict):
            continue
        grades = raw.get("grades") if isinstance(raw.get("grades"), list) else None
        cor = str(raw.get("cor") or "").strip()
        quantidade = coerce_nonnegative_int(raw.get("quantidade"))
        products.append(
            Product(
                nome=str(raw.get("nome") or "").strip(),
                codigo=str(raw.get("codigo") or "").strip(),
                codigo_original=str(raw.get("codigo") or "").strip(),
                quantidade=quantidade,
                preco=str(raw.get("preco") or "").strip(),
                categoria="",
                marca="",
                descricao_completa=str(raw.get("descricao_completa") or raw.get("nome") or "").strip() or None,
                grades=grades,
                cores=[{"cor": cor, "quantidade": quantidade}] if cor and quantidade > 0 else None,
                source_type=source_type,
                import_batch_id=import_batch_id,
                import_source_name=normalized_source_name,
                pending_grade_import=bool(pending_grade_import) if pending_grade_import is not None else False,
            )
        )
    return products


def build_local_import_text(payload: dict[str, Any]) -> str:
    items = payload.get("items") or []
    if not isinstance(items, list) or not items:
        return ""

    lines = ["codigo|nome|cor|quantidade|preco|grades"]
    for item in items:
        if not isinstance(item, dict):
            continue
        grades = item.get("grades") if isinstance(item.get("grades"), list) else []
        grades_text = ",".join(
            f"{str(grade.get('tamanho') or '').strip()}:{coerce_nonnegative_int(grade.get('quantidade'))}"
            for grade in grades
            if isinstance(grade, dict)
        )
        lines.append(
            "|".join(
                [
                    str(item.get("codigo") or "").strip(),
                    str(item.get("nome") or "").strip(),
                    str(item.get("cor") or "").strip(),
                    str(coerce_nonnegative_int(item.get("quantidade"))),
                    str(item.get("preco") or "").strip(),
                    grades_text,
                ]
            )
        )
    return "\n".join(lines)


def evaluate_local_parser_attempt(payload: dict[str, Any], *, decode_ms: int) -> LocalParserAttempt:
    payload_metrics = payload.get("metrics") or {}
    if not isinstance(payload_metrics, dict):
        payload_metrics = {}

    payload_warnings = [str(item) for item in (payload.get("warnings") or []) if str(item).strip()]
    products = build_local_parser_products(payload)
    validation = evaluate_import_validation(
        total_items=len(products),
        remessa_quantity=payload.get("remessa_quantity"),
        quantity_matches_remessa=payload.get("quantity_matches_remessa"),
        document_total_products=payload.get("document_total_products"),
        document_total_note=payload.get("document_total_note"),
        products_value_matches_document=payload.get("products_value_matches_document"),
    )
    validation_status = "approved" if validation["approved"] else "unverified" if validation["unverified"] else "rejected"
    approved_for_import = bool(validation["approved"] and validation["has_total_anchor"])
    fallback_message = None
    if not approved_for_import:
        reasons_text = "; ".join(validation["reasons"]) if validation["reasons"] else "automatic approval was not reached"
        fallback_message = f"Local parser not approved: {reasons_text}."

    metrics = {
        "local_decode_ms": int(decode_ms or 0),
        "local_text_chars": int(payload_metrics.get("text_chars") or 0),
        "local_structured_candidates": int(payload.get("total_rows") or 0),
        "local_parser_items": int(payload.get("total_itens") or 0),
        "local_ocr_pages_used": int(payload_metrics.get("ocr_pages_used") or 0),
        "local_document_total_products": payload.get("document_total_products"),
        "local_document_total_note": payload.get("document_total_note"),
        "local_extracted_total_products": payload.get("extracted_total_products"),
        "local_remessa_quantity": payload.get("remessa_quantity"),
        "local_quantity_matches_remessa": payload.get("quantity_matches_remessa"),
        "local_products_value_matches_document": payload.get("products_value_matches_document"),
        "local_warnings": payload_warnings,
        "local_validation_status": validation_status,
    }

    return LocalParserAttempt(
        products=products,
        validation=validation,
        metrics=metrics,
        approved_for_import=approved_for_import,
        fallback_message=fallback_message,
        payload_warnings=payload_warnings,
    )


def select_llm_import_result(
    *,
    upload_docs_text: str,
    selected_text: str,
    llm_text: str,
    llm_candidates: list[Product],
) -> LlmImportSelection:
    products: list[Product] = []
    next_selected_source = ""
    next_selected_text = selected_text

    if llm_candidates:
        products = filter_suspect_records(llm_candidates)
        if products:
            next_selected_source = "llm"
            next_selected_text = llm_text or selected_text

    if not products and llm_text:
        llm_fallback_text = llm_text.strip()
        if llm_fallback_text:
            products = parse_candidate_content(llm_fallback_text)
            if products:
                next_selected_source = "llm"
                next_selected_text = llm_fallback_text

    analysis = analyze_parsed_document(upload_docs_text or next_selected_text or llm_text, products)
    analysis_metrics = analysis.get("metrics") or {}
    if not isinstance(analysis_metrics, dict):
        analysis_metrics = {}
    quantity_match = bool(analysis_metrics.get("quantity_matches_remessa"))
    metrics = dict(analysis_metrics)
    metrics["llm_quantity_matches_remessa"] = (
        quantity_match if analysis_metrics.get("quantity_matches_remessa") is not None else None
    )
    metrics["llm_selected_quantity"] = products_total_quantity(products)
    warnings = [str(item) for item in (analysis.get("warnings") or []) if str(item).strip()]

    return LlmImportSelection(
        products=products,
        selected_source=next_selected_source,
        selected_text=next_selected_text,
        metrics=metrics,
        warnings=warnings,
    )


def evaluate_final_import_validation(
    *,
    total_items: int,
    remessa_quantity: Any,
    quantity_matches_remessa: Any,
    document_total_products: Any,
    document_total_note: Any,
    products_value_matches_document: Any,
    selected_source: str,
) -> FinalImportValidationDecision:
    validation = evaluate_import_validation(
        total_items=total_items,
        remessa_quantity=remessa_quantity,
        quantity_matches_remessa=quantity_matches_remessa,
        document_total_products=document_total_products,
        document_total_note=document_total_note,
        products_value_matches_document=products_value_matches_document,
    )
    validation_status = "approved" if validation["approved"] else "unverified" if validation["unverified"] else "rejected"
    metrics = {
        "final_validation_status": validation_status,
        "final_validation_reasons": list(validation["reasons"]),
        "final_validation_reason_codes": list(validation["reason_codes"]),
    }
    event_source = selected_source or "system"

    if validation["approved"]:
        warnings: list[str] = []
        event = {
            "source": event_source,
            "level": "success",
            "message": "Import approved by automatic validation.",
        }
    elif validation["unverified"]:
        warning_message = (
            "Import completed without printed totals or remessa quantity to validate against. "
            "Result is unverified and needs manual review — not a fully validated success."
        )
        warnings = [warning_message]
        event = {
            "source": event_source,
            "level": "warning",
            "message": warning_message,
        }
    else:
        rejection_message = (
            f"Import blocked after validation: {'; '.join(validation['reasons'])}"
            if validation["reasons"]
            else "Import blocked after validation."
        )
        warnings = [rejection_message]
        event = {
            "source": event_source,
            "level": "error",
            "message": rejection_message,
        }

    return FinalImportValidationDecision(
        validation=validation,
        metrics=metrics,
        warnings=warnings,
        event=event,
    )


def resolve_import_content_to_save(
    *,
    selected_text: str,
    llm_text: str,
    products: list[Product],
) -> str:
    content = selected_text or llm_text
    if looks_like_binary_blob(content):
        content = ""
    if not content and products:
        content = products_to_text(products)
    return content


def prepare_import_batch_metadata(
    products: list[Product],
    *,
    job_id: str,
    filename: str,
    grade_preview_summary: dict[str, Any],
) -> ImportBatchPreparation:
    summary = {
        "originais": coerce_nonnegative_int(grade_preview_summary.get("originais", len(products))),
        "resultantes": coerce_nonnegative_int(grade_preview_summary.get("resultantes", len(products))),
        "removidos": coerce_nonnegative_int(grade_preview_summary.get("removidos")),
        "atualizados_grades": coerce_nonnegative_int(grade_preview_summary.get("atualizados_grades")),
    }
    grades_available = summary["atualizados_grades"] > 0
    import_batch_id = job_id if products else None
    source_name = (filename or "romaneio").strip()

    for item in products:
        item.source_type = "romaneio"
        item.import_batch_id = import_batch_id
        item.import_source_name = source_name
        item.pending_grade_import = grades_available

    return ImportBatchPreparation(
        import_batch_id=import_batch_id,
        grades_available=grades_available,
        grade_preview_summary=summary,
        metrics={
            "import_compact_removed": summary["removidos"],
            "import_compact_groups": summary["atualizados_grades"],
            "import_grades_available": grades_available,
            "selected_items": len(products),
        },
    )


def evaluate_import_validation(
    *,
    total_items: int,
    remessa_quantity: Any,
    quantity_matches_remessa: Any,
    document_total_products: Any,
    document_total_note: Any,
    products_value_matches_document: Any,
) -> dict[str, Any]:
    has_total_anchor = bool(document_total_products or document_total_note)
    has_quantity_anchor = remessa_quantity is not None
    reasons: list[str] = []

    if total_items <= 0:
        reasons.append("no importable items were detected")
    if has_total_anchor and not bool(products_value_matches_document):
        reasons.append("the extracted product total does not match the invoice total")
    if has_quantity_anchor and not bool(quantity_matches_remessa):
        reasons.append("the extracted quantity does not match the remessa quantity")

    has_any_anchor = has_total_anchor or has_quantity_anchor
    approved = total_items > 0 and has_any_anchor and not reasons
    rejected = total_items <= 0 or (has_any_anchor and bool(reasons))
    unverified = total_items > 0 and not has_any_anchor
    return {
        "approved": approved,
        "rejected": rejected,
        "unverified": unverified,
        "has_total_anchor": has_total_anchor,
        "has_quantity_anchor": has_quantity_anchor,
        "reasons": reasons,
        "reason_codes": [VALIDATION_REASON_CODES[reason] for reason in reasons],
    }
