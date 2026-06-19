from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any, Callable

import httpx

from app.application.imports.parsing import (
    build_romaneio_image_message,
    extract_llm_json_items,
    extract_structured_invoice_row_lines,
    parse_candidate_content,
    products_to_text,
    save_romaneio_text,
    split_structured_invoice_chunks,
    slice_image_payloads,
    split_image_batches,
    split_text_chunks,
)
from app.application.imports.local_experiment import parse_local_romaneio_experiment
from app.application.imports.job_validation import (
    append_llm_chat_call_metrics as _append_llm_chat_call_metrics,
    append_process_event as _append_process_event,
    build_import_job_metrics as _build_import_job_metrics,
    evaluate_final_import_validation as _evaluate_final_import_validation,
    evaluate_local_parser_attempt as _evaluate_local_parser_attempt,
    prepare_import_batch_metadata as _prepare_import_batch_metadata,
    prepare_llm_vertical_slice_fallback as _prepare_llm_vertical_slice_fallback,
    products_total_quantity as _products_total_quantity,
    resolve_import_content_to_save as _resolve_import_content_to_save,
    select_llm_import_result as _select_llm_import_result,
    summarize_llm_upload_payload as _summarize_llm_upload_payload,
)
from app.domain.grades.parser import parse_grade_extraction
from app.domain.products.entities import Product
from app.interfaces.api.http.jobs.llm import coerce_int_env, llm_base_url, llm_timeout_seconds, post_llm_chat
from app.interfaces.api.http.jobs.store import update_grade_job, update_import_job
from app.interfaces.api.http.route_models import (
    GradeExtractionProduct,
    GradeExtractionResponse,
    ImportRomaneioResultResponse,
)
from app.interfaces.api.http.route_shared import CATALOG_SIZES
from app.shared.logging.setup import log_event

logger = logging.getLogger(__name__)


def build_import_text_chunk_message(
    *,
    expected_rows: int,
    chunk_index: int,
    total_chunks: int,
    first_code: str | None,
    last_code: str | None,
    retry: bool = False,
) -> str:
    range_hint = ""
    if first_code or last_code:
        range_hint = f" O primeiro codigo esperado deste trecho e {first_code or '-'} e o ultimo e {last_code or '-'}."
    retry_hint = (
        " A tentativa anterior deste trecho ficou incompleta; desta vez seja estritamente exaustivo e nao encerre antes da ultima linha."
        if retry
        else ""
    )
    return (
        "O anexo abaixo contem texto bruto de linhas de produtos de uma DANFE/NF-e. "
        "Extraia TODAS as linhas deste trecho e retorne JSON apenas no formato "
        '{"items":[{"codigo":"","descricao_original":"","nome_curto":"","quantidade":0,"preco":0,"tamanho":""}]}. '
        "Regras obrigatorias: uma saida por linha de produto; nao resumir; nao deduplicar; nao agrupar cores; nao pular linhas repetidas; "
        "preservar o codigo curto da linha; copiar a descricao completa em descricao_original; preencher tamanho quando existir; "
        "se houver 2 linhas quase iguais, mas ambas existirem no trecho, ambas devem aparecer na saida. "
        f"Este e o trecho {chunk_index}/{total_chunks} e contem {expected_rows} linhas de produto esperadas.{range_hint}{retry_hint}"
    )


def _chunk_row_codes(chunk_text: str) -> tuple[str | None, str | None]:
    rows = extract_structured_invoice_row_lines(chunk_text)
    if not rows:
        return None, None
    first_code = rows[0].split(" ", 1)[0].strip() if rows[0].strip() else None
    last_code = rows[-1].split(" ", 1)[0].strip() if rows[-1].strip() else None
    return first_code or None, last_code or None


def _llm_item_codes(items: list[dict[str, Any]]) -> list[str]:
    codes: list[str] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        for key in ("codigo", "code", "cod", "sku", "referencia", "ref"):
            value = str(item.get(key) or "").strip()
            if value:
                codes.append(value)
                break
    return codes


def _run_import_text_chunk(
    *,
    client: httpx.Client,
    job_id: str,
    chunk_text: str,
    chunk_name: str,
    images: list[dict[str, Any]],
    chunk_index: int,
    total_chunks: int,
    metrics: dict[str, Any],
    retry_depth: int = 0,
) -> tuple[list[str], str | None, list[Product], list[dict[str, Any]], list[str]]:
    warnings: list[str] = []
    expected_rows = extract_structured_invoice_row_lines(chunk_text)
    expected_row_count = len(expected_rows)
    expected_candidates = parse_candidate_content(chunk_text) if expected_row_count else []
    expected_total_quantity = _products_total_quantity(expected_candidates)
    first_code, last_code = _chunk_row_codes(chunk_text)
    message = build_import_text_chunk_message(
        expected_rows=expected_row_count,
        chunk_index=chunk_index,
        total_chunks=total_chunks,
        first_code=first_code,
        last_code=last_code,
        retry=retry_depth > 0,
    )

    call_started = time.perf_counter()
    chat_text, chat_saved = post_llm_chat(
        client,
        job_id=job_id,
        message=message,
        documents=[{"name": chunk_name, "content": chunk_text}],
        images=images,
    )
    call_ms = int((time.perf_counter() - call_started) * 1000)

    response_items = extract_llm_json_items(chat_text)
    parsed_candidates = parse_candidate_content(chat_text) if chat_text else []
    response_item_count = len(response_items) or len(parsed_candidates)
    response_total_quantity = _products_total_quantity(parsed_candidates)
    response_codes = _llm_item_codes(response_items)
    if not response_codes and parsed_candidates:
        response_codes = [str(item.codigo or "").strip() for item in parsed_candidates if str(item.codigo or "").strip()]
    response_last_code = response_codes[-1] if response_codes else None
    response_first_code = response_codes[0] if response_codes else None
    last_code_matches = not last_code or response_last_code == last_code
    first_code_matches = not first_code or response_first_code == first_code
    chunk_detail = {
        "chunk": chunk_index,
        "name": chunk_name,
        "duration_ms": call_ms,
        "document_chars": len(chunk_text),
        "images": len(images),
        "retry_depth": retry_depth,
        "expected_rows": expected_row_count,
        "response_items": response_item_count,
        "expected_quantity": expected_total_quantity,
        "response_quantity": response_total_quantity,
        "expected_first_code": first_code,
        "expected_last_code": last_code,
        "response_first_code": response_first_code,
        "response_last_code": response_last_code,
        "first_code_matches": first_code_matches,
        "last_code_matches": last_code_matches,
    }
    _append_llm_chat_call_metrics(metrics, chunk_detail)

    if not expected_row_count:
        return ([chat_text] if chat_text else []), chat_saved, parsed_candidates, [chunk_detail], warnings

    retry_enabled = retry_depth < coerce_int_env("LLM_IMPORT_CHUNK_RETRY_DEPTH", 1)
    is_incomplete = (
        response_item_count < expected_row_count
        or response_total_quantity < expected_total_quantity
        or not last_code_matches
        or not first_code_matches
    )
    if is_incomplete and retry_enabled and expected_row_count > 1:
        sub_max_lines = min(
            max(coerce_int_env("LLM_IMPORT_RETRY_MAX_LINES", 8), 1),
            max(expected_row_count - 1, 1),
        )
        subchunks = split_structured_invoice_chunks(
            chunk_text,
            max_lines=sub_max_lines,
            max_chars=coerce_int_env("LLM_IMPORT_RETRY_MAX_CHARS", 2600),
        )
        if len(subchunks) > 1:
            metrics["llm_chunk_retry_count"] = int(metrics.get("llm_chunk_retry_count") or 0) + 1
            mismatch_reasons: list[str] = []
            if response_item_count < expected_row_count:
                mismatch_reasons.append(f"itens {response_item_count}/{expected_row_count}")
            if response_total_quantity < expected_total_quantity:
                mismatch_reasons.append(f"quantidade {response_total_quantity}/{expected_total_quantity}")
            if not first_code_matches:
                mismatch_reasons.append(f"primeiro codigo {response_first_code or '-'} != {first_code or '-'}")
            if not last_code_matches:
                mismatch_reasons.append(f"ultimo codigo {response_last_code or '-'} != {last_code or '-'}")
            warnings.append(
                f"Chunk {chunk_name} voltou inconsistente ({'; '.join(mismatch_reasons)}); subdividindo o trecho para reprocessar via LLM."
            )
            texts: list[str] = []
            combined_candidates: list[Product] = []
            combined_details: list[dict[str, Any]] = [chunk_detail]
            saved_file = chat_saved
            sub_total = len(subchunks)
            for sub_index, subchunk in enumerate(subchunks, start=1):
                sub_texts, sub_saved, sub_candidates, sub_details, sub_warnings = _run_import_text_chunk(
                    client=client,
                    job_id=job_id,
                    chunk_text=subchunk,
                    chunk_name=f"{chunk_name}_retry{sub_index}",
                    images=[],
                    chunk_index=sub_index,
                    total_chunks=sub_total,
                    metrics=metrics,
                    retry_depth=retry_depth + 1,
                )
                if sub_saved and not saved_file:
                    saved_file = sub_saved
                texts.extend(sub_texts)
                combined_candidates.extend(sub_candidates)
                combined_details.extend(sub_details)
                warnings.extend(sub_warnings)
            return texts, saved_file, combined_candidates, combined_details, warnings

    return ([chat_text] if chat_text else []), chat_saved, parsed_candidates, [chunk_detail], warnings


def _run_import_image_batches(
    *,
    client: httpx.Client,
    job_id: str,
    image_batches: list[list[dict[str, Any]]],
    attempt: str,
    first_chunk_index: int,
    metrics: dict[str, Any],
    update_stage: Callable[[str, str], None],
    single_label: str,
    multiple_label: str,
) -> tuple[list[str], str | None, list[Product]]:
    parts: list[str] = []
    saved_file: str | None = None
    candidates: list[Product] = []
    total = len(image_batches)

    for idx, image_batch in enumerate(image_batches, start=1):
        label = multiple_label.format(index=idx, total=total) if total > 1 else single_label
        update_stage("processing", label)
        call_started = time.perf_counter()
        chat_text, chat_saved = post_llm_chat(
            client,
            job_id=job_id,
            message=build_romaneio_image_message(image_batch),
            documents=[],
            images=image_batch,
        )
        call_ms = int((time.perf_counter() - call_started) * 1000)
        _append_llm_chat_call_metrics(
            metrics,
            {
                "chunk": first_chunk_index + idx - 1,
                "attempt": attempt,
                "duration_ms": call_ms,
                "document_chars": 0,
                "images": len(image_batch),
            },
        )
        if chat_saved and not saved_file:
            saved_file = chat_saved
        if chat_text:
            parts.append(chat_text)
            candidates.extend(parse_candidate_content(chat_text))

    return parts, saved_file, candidates


def run_grade_extraction_job(
    *,
    job_id: str,
    contents: bytes,
    filename: str,
    content_type: str | None,
    service: object,
) -> None:
    warnings: list[str] = []
    llm_text = ""

    update_grade_job(job_id, "uploading")
    try:
        timeout = httpx.Timeout(llm_timeout_seconds(), connect=10.0)
        files = {
            "files": (
                filename or "nota_fiscal",
                contents,
                content_type or "application/octet-stream",
            )
        }
        with httpx.Client(timeout=timeout) as client:
            upload_response = client.post(
                f"{llm_base_url()}/api/upload",
                files=files,
                headers={"X-Job-Id": job_id},
            )
            upload_response.raise_for_status()
            parsed_upload: Any = upload_response.json()
            upload_data = parsed_upload if isinstance(parsed_upload, dict) else {}

            upload_errors = upload_data.get("errors") if isinstance(upload_data.get("errors"), list) else []
            warnings.extend([str(item) for item in upload_errors if str(item).strip()])

            documents = [doc for doc in (upload_data.get("documents") or []) if isinstance(doc, dict)]
            images = [img for img in (upload_data.get("images") or []) if isinstance(img, dict)]
            upload_docs_text = "\n\n".join(str(doc.get("content") or "") for doc in documents).strip()

            update_grade_job(job_id, "processing")
            chunks = split_text_chunks(upload_docs_text, max_chars=coerce_int_env("LLM_DOC_CHUNK_CHARS", 8000))
            if chunks:
                parts: list[str] = []
                total = len(chunks)
                for idx, chunk in enumerate(chunks, start=1):
                    update_grade_job(
                        job_id,
                        "processing",
                        message=f"Processando texto {idx}/{total} com servico LLM",
                    )
                    chat_text, _ = post_llm_chat(
                        client,
                        job_id=job_id,
                        mode="grade_extractor",
                        message="",
                        documents=[{"name": f"parte_{idx}", "content": chunk}],
                        images=images if idx == 1 else [],
                    )
                    if chat_text:
                        parts.append(chat_text)
                llm_text = "\n\n".join(parts).strip()
            elif images:
                image_inputs = slice_image_payloads(
                    images,
                    vertical_slices=coerce_int_env("LLM_PDF_PAGE_VERTICAL_SLICES", 4),
                )
                image_batches = split_image_batches(
                    image_inputs,
                    batch_size=coerce_int_env("LLM_IMAGE_BATCH_SIZE", 1),
                )
                parts = []
                total = len(image_batches)
                for idx, image_batch in enumerate(image_batches, start=1):
                    label = (
                        f"Processando imagens {idx}/{total} com servico LLM"
                        if total > 1
                        else "Processando imagens com servico LLM"
                    )
                    update_grade_job(job_id, "processing", message=label)
                    chat_text, _ = post_llm_chat(
                        client,
                        job_id=job_id,
                        mode="grade_extractor",
                        message=build_romaneio_image_message(image_batch),
                        documents=[],
                        images=image_batch,
                    )
                    if chat_text:
                        parts.append(chat_text)
                llm_text = "\n\n".join(parts).strip()
            else:
                warnings.append("Upload do LLM nao retornou documentos ou imagens.")
    except Exception as exc:
        log_event(
            logger,
            logging.WARNING,
            "grade_extraction_llm_failed",
            "grade extraction LLM pipeline failed",
            job_id=job_id,
            exception_type=type(exc).__name__,
        )
        logger.warning("Falha no pipeline LLM de grades (job_id=%s): %s", job_id, exc)
        warnings.append(f"Falha ao processar grades com o servico LLM: {exc}")

    update_grade_job(job_id, "parsing")
    parsed_items, parser_warnings = parse_grade_extraction(llm_text, allowed_sizes=CATALOG_SIZES)
    warnings.extend(parser_warnings)

    total_atualizados = 0
    detalhes: list[GradeExtractionProduct] = []
    for item in parsed_items:
        updated = service.update_grades_by_identifier(  # type: ignore[attr-defined]
            codigo=item.codigo,
            nome=item.nome,
            grades=item.grades,
        )
        atualizado = updated is not None
        if atualizado:
            total_atualizados += 1
        else:
            warnings.append(
                f"Produto nao localizado para aplicacao de grade (codigo={item.codigo or '-'}, nome={item.nome or '-'})"
            )
        detalhes.append(
            GradeExtractionProduct(
                codigo=item.codigo,
                nome=item.nome,
                grades=item.grades,
                atualizado=atualizado,
                warnings=item.warnings,
            )
        )

    result = GradeExtractionResponse(
        status="ok" if total_atualizados else "partial",
        total_itens=len(parsed_items),
        total_atualizados=total_atualizados,
        warnings=warnings,
        itens=detalhes,
        content=llm_text or None,
    )
    update_grade_job(job_id, "completed", result=result)
    log_event(
        logger,
        logging.INFO,
        "grade_extraction_job_completed",
        "grade extraction job completed",
        job_id=job_id,
        status=result.status,
        parsed_items=len(parsed_items),
        updated_products=total_atualizados,
        warnings=len(warnings),
    )


def run_import_job(
    *,
    job_id: str,
    contents: bytes,
    filename: str,
    content_type: str | None,
    service: object,
    data_dir: Path,
    prefer_llm: bool = False,
) -> None:
    warnings: list[str] = []
    llm_text = ""
    upload_docs_text = ""
    saved_file: str | None = None
    parsed_items: list[Product] = []
    created_items: list[Product] = []
    selected_source = ""
    selected_text = ""
    llm_candidates: list[Product] = []
    total_started = time.perf_counter()
    metrics = _build_import_job_metrics(
        filename=filename,
        content_type=content_type,
        file_size_bytes=len(contents),
        llm_base_url=llm_base_url(),
        llm_timeout_seconds=llm_timeout_seconds(),
    )

    def _update_stage(stage: str, message: str) -> None:
        update_import_job(job_id, stage, message=message, metrics=metrics)

    _append_process_event(metrics, source="system", level="info", message="Import started.")
    _update_stage("processing", "Tentando parser local e validacao da nota")

    local_payload: dict[str, Any] | None = None
    try:
        local_started = time.perf_counter()
        local_payload = parse_local_romaneio_experiment(
            contents=contents,
            filename=filename,
            content_type=content_type,
        )
        local_decode_ms = int((time.perf_counter() - local_started) * 1000)
        local_attempt = _evaluate_local_parser_attempt(local_payload, decode_ms=local_decode_ms)
        metrics.update(local_attempt.metrics)

        if local_attempt.approved_for_import and not prefer_llm:
            parsed_items = local_attempt.products
            selected_source = "local"
            selected_text = products_to_text(parsed_items)
            _append_process_event(
                metrics,
                source="local",
                level="success",
                message="Local parser approved by invoice validation. Skipping the LLM fallback.",
            )
            _update_stage("parsing", "Parser local aprovado; preparando importacao")
        elif local_attempt.approved_for_import:
            metrics["local_parser_preapproved"] = True
            metrics["llm_requested"] = True
            _append_process_event(
                metrics,
                source="local",
                level="success",
                message="Validacao local aprovada; importacao via LLM solicitada.",
            )
            _update_stage("uploading", "Validacao local aprovada; enviando arquivo para servico LLM")
        else:
            fallback_message = local_attempt.fallback_message or "Local parser not approved: automatic approval was not reached."
            warnings.append(fallback_message)
            _append_process_event(metrics, source="local", level="warning", message=fallback_message)
            for item in local_attempt.payload_warnings:
                detail = str(item).strip()
                if detail:
                    _append_process_event(metrics, source="local", level="warning", message=detail)
            metrics["llm_fallback_triggered"] = True
    except Exception as exc:
        logger.warning("Falha ao executar parser local de romaneio (job_id=%s): %s", job_id, exc)
        metrics["local_validation_status"] = "error"
        metrics["llm_fallback_triggered"] = True
        warnings.append(f"Local parser failed before approval: {exc}")
        _append_process_event(
            metrics,
            source="local",
            level="error",
            message=f"Local parser failed before approval: {exc}",
        )

    if not parsed_items:
        _append_process_event(metrics, source="llm", level="info", message="Falling back to the LLM import pipeline.")
        _update_stage("uploading", "Parser local reprovado; enviando arquivo para servico LLM")
        try:
            timeout = httpx.Timeout(llm_timeout_seconds(), connect=10.0)
            files = {
                "files": (
                    filename or "romaneio",
                    contents,
                    content_type or "application/octet-stream",
                )
            }
            upload_started = time.perf_counter()
            with httpx.Client(timeout=timeout) as client:
                upload_response = client.post(
                    f"{llm_base_url()}/api/upload",
                    files=files,
                    headers={"X-Job-Id": job_id},
                )
                metrics["llm_upload_ms"] = int((time.perf_counter() - upload_started) * 1000)
                metrics["llm_upload_used"] = True
                upload_response.raise_for_status()
                parsed_upload: Any = upload_response.json()
                upload_data = parsed_upload if isinstance(parsed_upload, dict) else {}

                upload_summary = _summarize_llm_upload_payload(upload_data)
                warnings.extend(upload_summary.warnings)
                images = upload_summary.images
                upload_docs_text = upload_summary.documents_text
                metrics.update(upload_summary.metrics)
                for warning in upload_summary.warnings:
                    _append_process_event(metrics, source="llm", level="warning", message=warning)
                _append_process_event(
                    metrics,
                    source=upload_summary.event["source"],
                    level=upload_summary.event["level"],
                    message=upload_summary.event["message"],
                )

                _update_stage("processing", "Processando com servico LLM")
                structured_chunks = split_structured_invoice_chunks(
                    upload_docs_text,
                    max_lines=coerce_int_env("LLM_STRUCTURED_ROWS_PER_CHUNK", 18),
                    max_chars=coerce_int_env("LLM_STRUCTURED_CHUNK_CHARS", 4200),
                )
                chunks = structured_chunks or split_text_chunks(
                    upload_docs_text,
                    max_chars=coerce_int_env("LLM_DOC_CHUNK_CHARS", 8000),
                )
                if chunks:
                    parts: list[str] = []
                    total = len(chunks)
                    metrics["llm_chunk_count"] = total
                    metrics["llm_structured_chunk_count"] = len(structured_chunks)
                    for idx, chunk in enumerate(chunks, start=1):
                        _update_stage("processing", f"Processando texto {idx}/{total} com servico LLM")
                        chunk_texts, chat_saved, chunk_candidates, _chunk_details, chunk_warnings = _run_import_text_chunk(
                            client=client,
                            job_id=job_id,
                            chunk_text=chunk,
                            chunk_name=f"parte_{idx}",
                            images=images if idx == 1 else [],
                            chunk_index=idx,
                            total_chunks=total,
                            metrics=metrics,
                        )
                        warnings.extend(chunk_warnings)
                        if chat_saved and not saved_file:
                            saved_file = chat_saved
                        parts.extend(chunk_texts)
                        llm_candidates.extend(chunk_candidates)
                    llm_text = "\n\n".join(parts).strip()
                elif images:
                    parts = []
                    image_batch_size = coerce_int_env("LLM_IMAGE_BATCH_SIZE", 1)
                    full_page_batches = split_image_batches(images, batch_size=image_batch_size)
                    full_page_total = len(full_page_batches)
                    metrics["llm_chunk_count"] = full_page_total
                    metrics["llm_chat_used"] = True
                    metrics["llm_chat_calls"] = 0
                    metrics["llm_chat_total_ms"] = 0
                    metrics["llm_chat_calls_details"] = []

                    image_texts, image_saved, image_candidates = _run_import_image_batches(
                        client=client,
                        job_id=job_id,
                        image_batches=full_page_batches,
                        attempt="full_page",
                        first_chunk_index=1,
                        metrics=metrics,
                        update_stage=_update_stage,
                        single_label="Processando pagina com servico LLM",
                        multiple_label="Processando paginas {index}/{total} com servico LLM",
                    )
                    if image_saved and not saved_file:
                        saved_file = image_saved
                    parts.extend(image_texts)
                    llm_candidates.extend(image_candidates)

                    llm_text = "\n\n".join(parts).strip()

                    fallback_slices = max(
                        coerce_int_env("LLM_ROMANEIO_PDF_PAGE_VERTICAL_SLICES", 1),
                        coerce_int_env("LLM_PDF_PAGE_VERTICAL_SLICES", 4),
                    )
                    vertical_fallback = _prepare_llm_vertical_slice_fallback(
                        images=images,
                        image_batch_size=image_batch_size,
                        full_page_total=full_page_total,
                        fallback_slices=fallback_slices,
                        llm_candidates=llm_candidates,
                    )
                    if vertical_fallback.enabled:
                        warnings.extend(vertical_fallback.warnings)
                        fallback_event = vertical_fallback.event
                        if fallback_event is not None:
                            _append_process_event(
                                metrics,
                                source=fallback_event["source"],
                                level=fallback_event["level"],
                                message=fallback_event["message"],
                            )
                        metrics.update(vertical_fallback.metrics)
                        fallback_texts, fallback_saved, fallback_candidates = _run_import_image_batches(
                            client=client,
                            job_id=job_id,
                            image_batches=vertical_fallback.image_batches,
                            attempt="vertical_slices",
                            first_chunk_index=full_page_total + 1,
                            metrics=metrics,
                            update_stage=_update_stage,
                            single_label="Tentando recorte vertical com servico LLM",
                            multiple_label="Tentando recortes verticais {index}/{total} com servico LLM",
                        )
                        if fallback_saved and not saved_file:
                            saved_file = fallback_saved
                        parts.extend(fallback_texts)
                        llm_candidates.extend(fallback_candidates)
                        llm_text = "\n\n".join(parts).strip()
                else:
                    warnings.append("Upload do LLM nao retornou documentos ou imagens.")
        except Exception as exc:
            logger.warning("Falha no pipeline de importacao LLM (job_id=%s): %s", job_id, exc)
            warnings.append(f"Falha ao processar com o servico LLM: {exc}")
            _append_process_event(
                metrics,
                source="llm",
                level="error",
                message=f"LLM fallback failed: {exc}",
            )

    if not parsed_items:
        _update_stage("parsing", "Validando itens retornados pelo LLM")

        llm_selection = _select_llm_import_result(
            upload_docs_text=upload_docs_text,
            selected_text=selected_text,
            llm_text=llm_text,
            llm_candidates=llm_candidates,
        )
        parsed_items = llm_selection.products
        selected_source = llm_selection.selected_source or selected_source
        selected_text = llm_selection.selected_text
        warnings.extend(llm_selection.warnings)
        metrics.update(llm_selection.metrics)
    elif local_payload is not None:
        metrics["remessa_quantity"] = local_payload.get("remessa_quantity")
        metrics["quantity_matches_remessa"] = local_payload.get("quantity_matches_remessa")
        metrics["document_total_products"] = local_payload.get("document_total_products")
        metrics["document_total_note"] = local_payload.get("document_total_note")
        metrics["extracted_total_products"] = local_payload.get("extracted_total_products")
        metrics["products_value_matches_document"] = local_payload.get("products_value_matches_document")

    metrics["selected_source"] = selected_source or "none"
    metrics["selected_items"] = len(parsed_items)
    metrics["selected_items_raw"] = len(parsed_items)
    metrics["parsing_total_ms"] = int((time.perf_counter() - total_started) * 1000)
    metrics["quality_issues"] = []

    final_decision = _evaluate_final_import_validation(
        total_items=len(parsed_items),
        remessa_quantity=metrics.get("remessa_quantity"),
        quantity_matches_remessa=metrics.get("quantity_matches_remessa"),
        document_total_products=metrics.get("document_total_products"),
        document_total_note=metrics.get("document_total_note"),
        products_value_matches_document=metrics.get("products_value_matches_document"),
        selected_source=selected_source,
    )
    final_validation = final_decision.validation
    metrics.update(final_decision.metrics)
    warnings.extend(final_decision.warnings)
    _append_process_event(
        metrics,
        source=final_decision.event["source"],
        level=final_decision.event["level"],
        message=final_decision.event["message"],
    )

    grade_preview_summary = {
        "originais": len(parsed_items),
        "resultantes": len(parsed_items),
        "removidos": 0,
        "atualizados_grades": 0,
    }
    compact_import_batch = getattr(service, "compact_import_batch", None)
    if parsed_items and callable(compact_import_batch):
        try:
            _, grade_preview_summary = compact_import_batch(parsed_items)  # type: ignore[misc]
        except Exception as exc:
            logger.warning("Falha ao analisar grades disponiveis do lote importado (job_id=%s): %s", job_id, exc)
            warnings.append(f"Falha ao analisar grades disponiveis no romaneio: {exc}")
    import_preparation = _prepare_import_batch_metadata(
        parsed_items,
        job_id=job_id,
        filename=filename,
        grade_preview_summary=grade_preview_summary,
    )
    grade_preview_summary = import_preparation.grade_preview_summary
    grades_disponiveis = import_preparation.grades_available
    import_batch_id = import_preparation.import_batch_id
    metrics.update(import_preparation.metrics)

    content_to_save = _resolve_import_content_to_save(
        selected_text=selected_text,
        llm_text=llm_text,
        products=parsed_items,
    )

    if not content_to_save and not parsed_items:
        _append_process_event(
            metrics,
            source="system",
            level="error",
            message="Import stopped because no usable content or products were extracted.",
        )
        log_event(
            logger,
            logging.WARNING,
            "import_job_failed",
            "import job failed",
            job_id=job_id,
            failure_reason="no_usable_content",
            selected_source=selected_source or "none",
        )
        update_import_job(
            job_id,
            "error",
            error="Nao foi possivel extrair conteudo util do arquivo enviado.",
            metrics=metrics,
        )
        return

    if final_validation["rejected"]:
        log_event(
            logger,
            logging.WARNING,
            "import_job_failed",
            "import job failed",
            job_id=job_id,
            failure_reason="validation_rejected",
            selected_source=selected_source or "none",
            selected_items=len(parsed_items),
        )
        update_import_job(
            job_id,
            "error",
            error="Importação bloqueada porque os dados extraídos não bateram com a validação da nota.",
            metrics=metrics,
        )
        return

    try:
        persist_started = time.perf_counter()
        local_file = save_romaneio_text(data_dir, content_to_save)
        if parsed_items:
            created_items = service.create_many(parsed_items)  # type: ignore[attr-defined]
        else:
            warnings.append("Nenhum item de produto foi detectado no arquivo.")
        _append_process_event(
            metrics,
            source="system",
            level="success",
            message=f"Import persisted successfully with {len(created_items)} item(s).",
        )
        metrics["persist_ms"] = int((time.perf_counter() - persist_started) * 1000)
        metrics["total_ms"] = int((time.perf_counter() - total_started) * 1000)
        log_event(
            logger,
            logging.INFO,
            "import_job_completed",
            "import job completed",
            job_id=job_id,
            selected_source=metrics["selected_source"],
            imported_items=len(created_items),
            parsed_items=len(parsed_items),
            total_ms=metrics["total_ms"],
            llm_upload_ms=int(metrics.get("llm_upload_ms", 0) or 0),
            llm_chat_calls=int(metrics.get("llm_chat_calls", 0) or 0),
            llm_chat_total_ms=int(metrics.get("llm_chat_total_ms", 0) or 0),
        )

        result = ImportRomaneioResultResponse(
            status="ok",
            saved_file=saved_file,
            local_file=str(local_file),
            content=content_to_save,
            warnings=warnings,
            total_itens=len(parsed_items),
            grades_disponiveis=grades_disponiveis,
            total_grades_disponiveis=int(grade_preview_summary.get("atualizados_grades", 0) or 0),
            imported_keys=[item.ordering_key() for item in created_items],
            import_batch_id=import_batch_id,
            metrics=metrics,
        )
        update_import_job(job_id, "completed", result=result, metrics=metrics)
    except Exception as exc:
        log_event(
            logger,
            logging.ERROR,
            "import_job_failed",
            "import job failed",
            job_id=job_id,
            failure_reason="persist_failed",
            selected_source=selected_source or "none",
            exception_type=type(exc).__name__,
        )
        update_import_job(job_id, "error", error=f"Falha ao importar romaneio: {exc}", metrics=metrics)
