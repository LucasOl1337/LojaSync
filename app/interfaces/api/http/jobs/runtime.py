from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any

import httpx

from app.application.imports.parsing import (
    build_romaneio_image_message,
    decode_text_content,
    filter_suspect_records,
    looks_like_binary_blob,
    parse_candidate_content,
    products_to_text,
    save_romaneio_text,
    slice_image_payloads,
    split_image_batches,
    split_text_chunks,
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

logger = logging.getLogger(__name__)


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


def run_import_job(
    *,
    job_id: str,
    contents: bytes,
    filename: str,
    content_type: str | None,
    service: object,
    data_dir: Path,
) -> None:
    warnings: list[str] = []
    llm_text = ""
    upload_docs_text = ""
    local_text = ""
    saved_file: str | None = None
    parsed_items: list[Product] = []
    local_candidates: list[Product] = []
    upload_candidates: list[Product] = []
    selected_source = ""
    selected_text = ""
    llm_candidates: list[Product] = []
    total_started = time.perf_counter()
    metrics: dict[str, Any] = {
        "file_name": filename or "romaneio",
        "content_type": content_type or "",
        "file_size_bytes": len(contents),
        "llm_base_url": llm_base_url(),
        "llm_timeout_seconds": llm_timeout_seconds(),
        "llm_upload_used": False,
        "llm_chat_used": False,
        "llm_chat_calls": 0,
        "llm_chat_total_ms": 0,
        "llm_chat_calls_details": [],
        "upload_documents_chars": 0,
        "upload_images": 0,
        "local_text_chars": 0,
        "selected_source": "",
    }

    update_import_job(
        job_id,
        "processing",
        message="Validando parser local antes do servico LLM",
        metrics=metrics,
    )
    decode_started = time.perf_counter()
    local_text, local_warnings = decode_text_content(contents, filename, content_type)
    metrics["local_decode_ms"] = int((time.perf_counter() - decode_started) * 1000)
    metrics["local_text_chars"] = len(local_text or "")
    warnings.extend(local_warnings)
    if local_text:
        local_candidates = parse_candidate_content(local_text)
    metrics["local_structured_candidates"] = len(local_candidates)

    update_import_job(
        job_id,
        "uploading",
        message="Enviando arquivo para servico LLM",
        metrics=metrics,
    )
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

            upload_errors = upload_data.get("errors") if isinstance(upload_data.get("errors"), list) else []
            warnings.extend([str(item) for item in upload_errors if str(item).strip()])

            documents = [doc for doc in (upload_data.get("documents") or []) if isinstance(doc, dict)]
            images = [img for img in (upload_data.get("images") or []) if isinstance(img, dict)]
            upload_docs_text = "\n\n".join(str(doc.get("content") or "") for doc in documents).strip()
            metrics["upload_documents_chars"] = len(upload_docs_text or "")
            metrics["upload_images"] = len(images)

            if upload_docs_text:
                upload_candidates = parse_candidate_content(upload_docs_text)
            metrics["upload_structured_candidates"] = len(upload_candidates)

            update_import_job(
                job_id,
                "processing",
                message="Processando com servico LLM",
                metrics=metrics,
            )
            chunks = split_text_chunks(upload_docs_text, max_chars=coerce_int_env("LLM_DOC_CHUNK_CHARS", 8000))
            if chunks:
                parts: list[str] = []
                total = len(chunks)
                metrics["llm_chunk_count"] = total
                for idx, chunk in enumerate(chunks, start=1):
                    update_import_job(
                        job_id,
                        "processing",
                        message=f"Processando texto {idx}/{total} com servico LLM",
                        metrics=metrics,
                    )
                    call_started = time.perf_counter()
                    chat_text, chat_saved = post_llm_chat(
                        client,
                        job_id=job_id,
                        message="",
                        documents=[{"name": f"parte_{idx}", "content": chunk}],
                        images=images if idx == 1 else [],
                    )
                    call_ms = int((time.perf_counter() - call_started) * 1000)
                    metrics["llm_chat_used"] = True
                    metrics["llm_chat_calls"] = int(metrics.get("llm_chat_calls") or 0) + 1
                    metrics["llm_chat_total_ms"] = int(metrics.get("llm_chat_total_ms") or 0) + call_ms
                    details = list(metrics.get("llm_chat_calls_details") or [])
                    details.append(
                        {
                            "chunk": idx,
                            "duration_ms": call_ms,
                            "document_chars": len(chunk),
                            "images": len(images) if idx == 1 else 0,
                        }
                    )
                    metrics["llm_chat_calls_details"] = details
                    if chat_saved and not saved_file:
                        saved_file = chat_saved
                    if chat_text:
                        parts.append(chat_text)
                        llm_candidates.extend(parse_candidate_content(chat_text))
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

                for idx, image_batch in enumerate(full_page_batches, start=1):
                    label = (
                        f"Processando paginas {idx}/{full_page_total} com servico LLM"
                        if full_page_total > 1
                        else "Processando pagina com servico LLM"
                    )
                    update_import_job(
                        job_id,
                        "processing",
                        message=label,
                        metrics=metrics,
                    )
                    call_started = time.perf_counter()
                    chat_text, chat_saved = post_llm_chat(
                        client,
                        job_id=job_id,
                        message=build_romaneio_image_message(image_batch),
                        documents=[],
                        images=image_batch,
                    )
                    call_ms = int((time.perf_counter() - call_started) * 1000)
                    metrics["llm_chat_calls"] = int(metrics.get("llm_chat_calls") or 0) + 1
                    metrics["llm_chat_total_ms"] = int(metrics.get("llm_chat_total_ms") or 0) + call_ms
                    details = list(metrics.get("llm_chat_calls_details") or [])
                    details.append(
                        {
                            "chunk": idx,
                            "attempt": "full_page",
                            "duration_ms": call_ms,
                            "document_chars": 0,
                            "images": len(image_batch),
                        }
                    )
                    metrics["llm_chat_calls_details"] = details
                    if chat_saved and not saved_file:
                        saved_file = chat_saved
                    if chat_text:
                        parts.append(chat_text)
                        llm_candidates.extend(parse_candidate_content(chat_text))

                llm_text = "\n\n".join(parts).strip()

                fallback_slices = max(
                    coerce_int_env("LLM_ROMANEIO_PDF_PAGE_VERTICAL_SLICES", 1),
                    coerce_int_env("LLM_PDF_PAGE_VERTICAL_SLICES", 4),
                )
                if not llm_candidates and fallback_slices > 1:
                    warnings.append(
                        "OCR por pagina inteira sem itens validos; tentando recortes verticais como fallback."
                    )
                    image_inputs = slice_image_payloads(images, vertical_slices=fallback_slices)
                    image_batches = split_image_batches(image_inputs, batch_size=image_batch_size)
                    metrics["llm_chunk_count"] = full_page_total + len(image_batches)
                    for idx, image_batch in enumerate(image_batches, start=1):
                        label = (
                            f"Tentando recortes verticais {idx}/{len(image_batches)} com servico LLM"
                            if len(image_batches) > 1
                            else "Tentando recorte vertical com servico LLM"
                        )
                        update_import_job(
                            job_id,
                            "processing",
                            message=label,
                            metrics=metrics,
                        )
                        call_started = time.perf_counter()
                        chat_text, chat_saved = post_llm_chat(
                            client,
                            job_id=job_id,
                            message=build_romaneio_image_message(image_batch),
                            documents=[],
                            images=image_batch,
                        )
                        call_ms = int((time.perf_counter() - call_started) * 1000)
                        metrics["llm_chat_calls"] = int(metrics.get("llm_chat_calls") or 0) + 1
                        metrics["llm_chat_total_ms"] = int(metrics.get("llm_chat_total_ms") or 0) + call_ms
                        details = list(metrics.get("llm_chat_calls_details") or [])
                        details.append(
                            {
                                "chunk": full_page_total + idx,
                                "attempt": "vertical_slices",
                                "duration_ms": call_ms,
                                "document_chars": 0,
                                "images": len(image_batch),
                            }
                        )
                        metrics["llm_chat_calls_details"] = details
                        if chat_saved and not saved_file:
                            saved_file = chat_saved
                        if chat_text:
                            parts.append(chat_text)
                            llm_candidates.extend(parse_candidate_content(chat_text))
                    llm_text = "\n\n".join(parts).strip()
            else:
                warnings.append("Upload do LLM nao retornou documentos ou imagens.")
    except Exception as exc:
        logger.warning("Falha no pipeline de importacao LLM (job_id=%s): %s", job_id, exc)
        warnings.append(f"Falha ao processar com o servico LLM: {exc}")

    update_import_job(
        job_id,
        "parsing",
        message="Interpretando itens detectados",
        metrics=metrics,
    )

    if not parsed_items and llm_candidates:
        parsed_items = filter_suspect_records(llm_candidates)
        if parsed_items:
            selected_source = "llm"
            selected_text = llm_text or selected_text

    if not parsed_items and llm_text:
        llm_fallback_text = llm_text.strip()
        if llm_fallback_text:
            parsed_items = parse_candidate_content(llm_fallback_text)
            if parsed_items:
                selected_source = "llm"
                selected_text = llm_fallback_text

    if not parsed_items and upload_candidates:
        parsed_items = upload_candidates
        selected_source = "upload_structured"
        selected_text = upload_docs_text

    if not parsed_items and local_candidates:
        parsed_items = local_candidates
        selected_source = "local_structured"
        selected_text = local_text

    metrics["selected_source"] = selected_source or "none"
    metrics["selected_items"] = len(parsed_items)
    metrics["selected_items_raw"] = len(parsed_items)
    metrics["parsing_total_ms"] = int((time.perf_counter() - total_started) * 1000)
    metrics["quality_issues"] = []

    compact_summary = {
        "originais": len(parsed_items),
        "resultantes": len(parsed_items),
        "removidos": 0,
        "atualizados_grades": 0,
    }
    compact_import_batch = getattr(service, "compact_import_batch", None)
    if parsed_items and callable(compact_import_batch):
        try:
            compacted_items, compact_summary = compact_import_batch(parsed_items)  # type: ignore[misc]
            if compacted_items:
                parsed_items = compacted_items
            if compact_summary.get("atualizados_grades", 0) > 0:
                warnings.append("Grades detectadas no romaneio e compactadas automaticamente na lista importada.")
        except Exception as exc:
            logger.warning("Falha ao compactar grades do lote importado (job_id=%s): %s", job_id, exc)
            warnings.append(f"Falha ao compactar grades automaticamente: {exc}")
    metrics["import_compact_removed"] = int(compact_summary.get("removidos", 0) or 0)
    metrics["import_compact_groups"] = int(compact_summary.get("atualizados_grades", 0) or 0)
    metrics["selected_items"] = len(parsed_items)

    content_to_save = selected_text or llm_text or upload_docs_text or local_text
    if looks_like_binary_blob(content_to_save):
        content_to_save = ""
    if not content_to_save and parsed_items:
        content_to_save = products_to_text(parsed_items)

    if not content_to_save and not parsed_items:
        update_import_job(
            job_id,
            "error",
            error="Nao foi possivel extrair conteudo util do arquivo enviado.",
            metrics=metrics,
        )
        return

    try:
        persist_started = time.perf_counter()
        local_file = save_romaneio_text(data_dir, content_to_save)
        if parsed_items:
            service.create_many(parsed_items)  # type: ignore[attr-defined]
        else:
            warnings.append("Nenhum item de produto foi detectado no arquivo.")
        metrics["persist_ms"] = int((time.perf_counter() - persist_started) * 1000)
        metrics["total_ms"] = int((time.perf_counter() - total_started) * 1000)
        logger.info(
            "romaneio job %s finalizado em %sms (source=%s, upload_ms=%s, chat_calls=%s, chat_ms=%s, items=%s)",
            job_id,
            metrics["total_ms"],
            metrics["selected_source"],
            metrics.get("llm_upload_ms", 0),
            metrics.get("llm_chat_calls", 0),
            metrics.get("llm_chat_total_ms", 0),
            len(parsed_items),
        )

        result = ImportRomaneioResultResponse(
            status="ok",
            saved_file=saved_file,
            local_file=str(local_file),
            content=content_to_save,
            warnings=warnings,
            total_itens=len(parsed_items),
            metrics=metrics,
        )
        update_import_job(job_id, "completed", result=result, metrics=metrics)
    except Exception as exc:
        update_import_job(job_id, "error", error=f"Falha ao importar romaneio: {exc}", metrics=metrics)
