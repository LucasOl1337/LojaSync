from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any

import httpx

from app.application.imports.parsing import (
    analyze_parsed_document,
    build_romaneio_image_message,
    extract_llm_json_items,
    extract_structured_invoice_row_lines,
    filter_suspect_records,
    looks_like_binary_blob,
    parse_candidate_content,
    products_to_text,
    save_romaneio_text,
    split_structured_invoice_chunks,
    slice_image_payloads,
    split_image_batches,
    split_text_chunks,
)
from app.application.imports.local_experiment import parse_local_romaneio_experiment
from app.domain.grades.parser import parse_grade_extraction
from app.domain.products.entities import Product
from app.interfaces.api.http.jobs.llm import coerce_int_env, llm_base_url, llm_timeout_seconds, post_llm_chat
from app.interfaces.api.http.jobs.store import update_grade_job, update_import_job, update_post_process_job
from app.interfaces.api.http.route_models import (
    GradeExtractionProduct,
    GradeExtractionResponse,
    ImportRomaneioResultResponse,
    PostProcessProductsResultResponse,
)
from app.interfaces.api.http.route_shared import CATALOG_SIZES

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


def _products_total_quantity(items: list[Product]) -> int:
    return sum(max(int(item.quantidade or 0), 0) for item in items)


def _append_process_event(
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


def _build_local_parser_products(payload: dict[str, Any]) -> list[Product]:
    products: list[Product] = []
    for raw in payload.get("items") or []:
        if not isinstance(raw, dict):
            continue
        grades = raw.get("grades") if isinstance(raw.get("grades"), list) else None
        cor = str(raw.get("cor") or "").strip()
        quantidade = max(int(raw.get("quantidade") or 0), 0)
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
            )
        )
    return products


def _evaluate_import_validation(
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
    }


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
    metrics["llm_chat_used"] = True
    metrics["llm_chat_calls"] = int(metrics.get("llm_chat_calls") or 0) + 1
    metrics["llm_chat_total_ms"] = int(metrics.get("llm_chat_total_ms") or 0) + call_ms

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
    details = list(metrics.get("llm_chat_calls_details") or [])
    details.append(chunk_detail)
    metrics["llm_chat_calls_details"] = details

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


def build_post_process_message() -> str:
    return (
        "Voce esta revisando itens ja extraidos de romaneios para uso real de loja. "
        "Seu objetivo e sugerir melhorias conservadoras para descricao, codigo e custo sem inventar dados incertos. "
        "Regras para descricao: detecte caracteres estranhos, palavras sem relacao com o nome final de venda, numeros soltos, "
        "anomalias e formatacao ruim; limpe e reescreva para um nome curto, claro e natural para uso de loja, mas sem supor "
        "marca, tecido, genero, cor ou detalhe que nao estejam realmente confiaveis. "
        "Regras para codigo: detecte repeticoes sem utilidade, excesso de caracteres e trechos redundantes; mantenha apenas a "
        "parte primordial que ainda diferencie o item e ajude os funcionarios a reconhecer o produto. "
        "Regras para custo: quando houver variacoes visuais pequenas e conflitantes no mesmo padrao decimal, como 40,46 e 40,47, "
        "prefira normalizar para um valor superior terminado em 0,50 para reduzir conflito visual; nao altere custos sem motivo claro. "
        "Retorne JSON com uma lista 'items'. Cada item deve conter: ordering_key, nome_atual, nome_sugerido, codigo_atual, "
        "codigo_sugerido, preco_atual, preco_sugerido, acoes, justificativa e confianca. "
        "Em 'acoes', use apenas os valores entre: manter, ajustar_descricao, ajustar_codigo, ajustar_preco, ajustar_tudo. "
        "Se nao houver seguranca suficiente, mantenha os valores atuais e explique na justificativa. "
        "Este fluxo ainda esta em modo skeleton/dry-run, entao priorize formato consistente e decisao conservadora."
    )


def build_post_process_products_text(products: list[Product]) -> str:
    if not products:
        return ""
    lines = ["ordering_key|codigo|nome|descricao_completa|quantidade|preco"]
    for item in products:
        lines.append(
            "|".join(
                [
                    str(item.ordering_key()).strip(),
                    str(item.codigo or "").strip(),
                    str(item.nome or "").strip(),
                    str(item.descricao_completa or "").strip(),
                    str(int(item.quantidade or 0)),
                    str(item.preco or "").strip(),
                ]
            )
        )
    return "\n".join(lines)


def build_post_process_context_text(*, total_products: int, review_products: list[Product]) -> str:
    summary_lines = [
        f"total_produtos_lista={int(total_products or 0)}",
        f"total_produtos_para_revisao={len(review_products)}",
        "revise apenas os itens enviados abaixo; os demais itens da lista ja estao fora do escopo de surpresa/ambiguidade.",
    ]
    return "\n".join(summary_lines)


def run_post_process_job(
    *,
    job_id: str,
    service: object,
) -> None:
    warnings: list[str] = []
    raw_response = ""
    saved_file: str | None = None
    total_started = time.perf_counter()
    metrics: dict[str, Any] = {
        "llm_base_url": llm_base_url(),
        "llm_timeout_seconds": llm_timeout_seconds(),
        "llm_chat_used": False,
        "llm_chat_calls": 0,
        "llm_chat_total_ms": 0,
        "total_products": 0,
        "dry_run": True,
    }

    update_post_process_job(
        job_id,
        "processing",
        message="Carregando produtos atuais para pos-processamento",
        metrics=metrics,
    )

    list_products = getattr(service, "list_products", None)
    get_review_candidates = getattr(service, "get_post_process_review_candidates", None)
    if not callable(list_products):
        update_post_process_job(job_id, "error", error="Servico de produtos indisponivel", metrics=metrics)
        return

    products = list_products()  # type: ignore[misc]
    metrics["total_products"] = len(products)
    if not products:
        update_post_process_job(job_id, "error", error="Nao ha produtos para pos-processar", metrics=metrics)
        return

    review_products = products
    if callable(get_review_candidates):
        try:
            review_products = get_review_candidates()  # type: ignore[misc]
        except Exception as exc:
            logger.warning("Falha ao selecionar candidatos para revisao IA (job_id=%s): %s", job_id, exc)
            warnings.append(f"Falha ao selecionar itens prioritarios para IA: {exc}")
            review_products = products

    metrics["review_candidate_products"] = len(review_products)

    documents: list[dict[str, Any]] = []
    if review_products:
        products_text = build_post_process_products_text(review_products)
        context_text = build_post_process_context_text(
            total_products=len(products),
            review_products=review_products,
        )
        documents = [
            {"name": "contexto_revisao.txt", "content": context_text},
            {"name": "produtos_prioritarios.txt", "content": products_text},
        ]
    else:
        products_text = ""
        warnings.append("Nenhum item ambiguo detectado para revisao via IA; executadas apenas regras locais seguras.")

    if review_products:
        try:
            update_post_process_job(
                job_id,
                "reviewing",
                message="Enviando apenas os itens mais ambiguos para revisao inteligente via LLM",
                metrics=metrics,
            )
            timeout = httpx.Timeout(llm_timeout_seconds(), connect=10.0)
            with httpx.Client(timeout=timeout) as client:
                selected_mode = "product_post_processor"
                call_started = time.perf_counter()
                try:
                    raw_response, saved_file = post_llm_chat(
                        client,
                        job_id=job_id,
                        mode=selected_mode,
                        message=build_post_process_message(),
                        documents=documents,
                        images=[],
                    )
                except httpx.HTTPStatusError as exc:
                    response_text = ""
                    try:
                        response_text = exc.response.text
                    except Exception:
                        response_text = str(exc)
                    if exc.response.status_code == 422 and "mode" in response_text.lower():
                        warnings.append(
                            "Servidor LLM atual nao reconhece o modo dedicado de revisao; usando modo padrao como fallback."
                        )
                        selected_mode = "default"
                        raw_response, saved_file = post_llm_chat(
                            client,
                            job_id=job_id,
                            mode=selected_mode,
                            message=build_post_process_message(),
                            documents=documents,
                            images=[],
                        )
                    else:
                        raise
                call_ms = int((time.perf_counter() - call_started) * 1000)
                metrics["llm_chat_used"] = True
                metrics["llm_chat_calls"] = 1
                metrics["llm_chat_total_ms"] = call_ms
                metrics["llm_mode_used"] = selected_mode
                metrics["input_chars"] = len(products_text)
                metrics["output_chars"] = len(raw_response or "")
        except Exception as exc:
            logger.warning("Falha no pos-processamento LLM (job_id=%s): %s", job_id, exc)
            warnings.append(f"Falha ao consultar o servico LLM: {exc}")

    if not raw_response:
        warnings.append("A IA nao retornou sugestoes estruturadas; foram aplicadas apenas as regras locais seguras.")

    apply_post_processing = getattr(service, "apply_post_processing", None)
    application_result: dict[str, Any] = {
        "total": len(products),
        "modificados": 0,
        "warnings": [],
        "llm_suggestions_applied": 0,
        "local_adjustments_applied": 0,
        "dry_run": True,
    }
    if callable(apply_post_processing):
        try:
            application_result = apply_post_processing(raw_response)  # type: ignore[misc]
        except Exception as exc:
            logger.warning("Falha ao aplicar pos-processamento local (job_id=%s): %s", job_id, exc)
            warnings.append(f"Falha ao aplicar ajustes do pos-processamento: {exc}")

    warnings.extend([str(item) for item in application_result.get("warnings", []) if str(item).strip()])
    metrics["total_ms"] = int((time.perf_counter() - total_started) * 1000)
    metrics["post_process_modified"] = int(application_result.get("modificados", 0) or 0)
    metrics["llm_suggestions_applied"] = int(application_result.get("llm_suggestions_applied", 0) or 0)
    metrics["local_adjustments_applied"] = int(application_result.get("local_adjustments_applied", 0) or 0)
    result = PostProcessProductsResultResponse(
        status="ok" if raw_response or application_result.get("modificados") else "partial",
        total_itens=len(products),
        total_modificados=int(application_result.get("modificados", 0) or 0),
        dry_run=bool(application_result.get("dry_run", False)),
        saved_file=saved_file,
        raw_response=raw_response or None,
        warnings=warnings,
        metrics=metrics,
    )
    update_post_process_job(job_id, "completed", result=result, metrics=metrics)


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
    saved_file: str | None = None
    parsed_items: list[Product] = []
    created_items: list[Product] = []
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
        "process_log": [],
        "selected_source": "",
    }

    def _update_stage(stage: str, message: str) -> None:
        update_import_job(job_id, stage, message=message, metrics=metrics)

    metrics["local_decode_ms"] = 0
    metrics["local_text_chars"] = 0
    metrics["local_structured_candidates"] = 0
    metrics["local_parser_items"] = 0
    metrics["local_validation_status"] = "not_run"
    metrics["llm_fallback_triggered"] = False
    metrics["final_validation_status"] = "pending"

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
        metrics["local_decode_ms"] = int((time.perf_counter() - local_started) * 1000)
        metrics["local_text_chars"] = int((local_payload.get("metrics") or {}).get("text_chars") or 0)
        metrics["local_structured_candidates"] = int(local_payload.get("total_rows") or 0)
        metrics["local_parser_items"] = int(local_payload.get("total_itens") or 0)
        metrics["local_ocr_pages_used"] = int((local_payload.get("metrics") or {}).get("ocr_pages_used") or 0)
        metrics["local_document_total_products"] = local_payload.get("document_total_products")
        metrics["local_document_total_note"] = local_payload.get("document_total_note")
        metrics["local_extracted_total_products"] = local_payload.get("extracted_total_products")
        metrics["local_remessa_quantity"] = local_payload.get("remessa_quantity")
        metrics["local_quantity_matches_remessa"] = local_payload.get("quantity_matches_remessa")
        metrics["local_products_value_matches_document"] = local_payload.get("products_value_matches_document")
        metrics["local_warnings"] = list(local_payload.get("warnings") or [])

        local_products = _build_local_parser_products(local_payload)
        local_validation = _evaluate_import_validation(
            total_items=len(local_products),
            remessa_quantity=local_payload.get("remessa_quantity"),
            quantity_matches_remessa=local_payload.get("quantity_matches_remessa"),
            document_total_products=local_payload.get("document_total_products"),
            document_total_note=local_payload.get("document_total_note"),
            products_value_matches_document=local_payload.get("products_value_matches_document"),
        )
        metrics["local_validation_status"] = (
            "approved" if local_validation["approved"] else "unverified" if local_validation["unverified"] else "rejected"
        )

        if local_validation["approved"] and local_validation["has_total_anchor"]:
            parsed_items = local_products
            selected_source = "local"
            selected_text = products_to_text(parsed_items)
            _append_process_event(
                metrics,
                source="local",
                level="success",
                message="Local parser approved by invoice validation. Skipping the LLM fallback.",
            )
            _update_stage("parsing", "Parser local aprovado; preparando importacao")
        else:
            reasons_text = "; ".join(local_validation["reasons"]) if local_validation["reasons"] else "automatic approval was not reached"
            fallback_message = f"Local parser not approved: {reasons_text}."
            warnings.append(fallback_message)
            _append_process_event(metrics, source="local", level="warning", message=fallback_message)
            for item in local_payload.get("warnings") or []:
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

                upload_errors = upload_data.get("errors") if isinstance(upload_data.get("errors"), list) else []
                warnings.extend([str(item) for item in upload_errors if str(item).strip()])

                documents = [doc for doc in (upload_data.get("documents") or []) if isinstance(doc, dict)]
                images = [img for img in (upload_data.get("images") or []) if isinstance(img, dict)]
                upload_docs_text = "\n\n".join(str(doc.get("content") or "") for doc in documents).strip()
                metrics["upload_documents_chars"] = len(upload_docs_text or "")
                metrics["upload_images"] = len(images)
                structured_row_lines = extract_structured_invoice_row_lines(upload_docs_text)
                metrics["upload_structured_candidates"] = len(structured_row_lines)
                _append_process_event(
                    metrics,
                    source="llm",
                    level="info",
                    message=(
                        f"LLM upload prepared {len(documents)} document(s), {len(images)} image(s), "
                        f"and {len(structured_row_lines)} structured candidate row(s)."
                    ),
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

                    for idx, image_batch in enumerate(full_page_batches, start=1):
                        label = (
                            f"Processando paginas {idx}/{full_page_total} com servico LLM"
                            if full_page_total > 1
                            else "Processando pagina com servico LLM"
                        )
                        _update_stage("processing", label)
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
                        _append_process_event(
                            metrics,
                            source="llm",
                            level="warning",
                            message="Full-page OCR fallback returned no valid items; trying vertical slices.",
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
                            _update_stage("processing", label)
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
            _append_process_event(
                metrics,
                source="llm",
                level="error",
                message=f"LLM fallback failed: {exc}",
            )

    if not parsed_items:
        _update_stage("parsing", "Validando itens retornados pelo LLM")

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

        llm_analysis = analyze_parsed_document(upload_docs_text or selected_text or llm_text, parsed_items)
        llm_metrics = llm_analysis.get("metrics") or {}
        llm_qty_match = bool(llm_metrics.get("quantity_matches_remessa"))
        llm_qty = sum(int(item.quantidade or 0) for item in parsed_items)

        metrics["llm_quantity_matches_remessa"] = llm_qty_match if llm_metrics.get("quantity_matches_remessa") is not None else None
        metrics["llm_selected_quantity"] = llm_qty
        warnings.extend([str(item) for item in (llm_analysis.get("warnings") or []) if str(item).strip()])
        for key, value in llm_metrics.items():
            metrics[key] = value
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

    final_validation = _evaluate_import_validation(
        total_items=len(parsed_items),
        remessa_quantity=metrics.get("remessa_quantity"),
        quantity_matches_remessa=metrics.get("quantity_matches_remessa"),
        document_total_products=metrics.get("document_total_products"),
        document_total_note=metrics.get("document_total_note"),
        products_value_matches_document=metrics.get("products_value_matches_document"),
    )
    metrics["final_validation_status"] = (
        "approved" if final_validation["approved"] else "unverified" if final_validation["unverified"] else "rejected"
    )
    metrics["final_validation_reasons"] = list(final_validation["reasons"])

    if final_validation["approved"]:
        _append_process_event(
            metrics,
            source=selected_source or "system",
            level="success",
            message="Import approved by automatic validation.",
        )
    elif final_validation["unverified"]:
        warning_message = "Import completed without printed totals or remessa quantity to validate against."
        warnings.append(warning_message)
        _append_process_event(
            metrics,
            source=selected_source or "system",
            level="warning",
            message=warning_message,
        )
    else:
        rejection_message = (
            f"Import blocked after validation: {'; '.join(final_validation['reasons'])}"
            if final_validation["reasons"]
            else "Import blocked after validation."
        )
        warnings.append(rejection_message)
        _append_process_event(
            metrics,
            source=selected_source or "system",
            level="error",
            message=rejection_message,
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
    grades_disponiveis = int(grade_preview_summary.get("atualizados_grades", 0) or 0) > 0
    import_batch_id = job_id if parsed_items else None
    if parsed_items:
        for item in parsed_items:
            item.source_type = "romaneio"
            item.import_batch_id = import_batch_id
            item.import_source_name = (filename or "romaneio").strip()
            item.pending_grade_import = grades_disponiveis
    metrics["import_compact_removed"] = int(grade_preview_summary.get("removidos", 0) or 0)
    metrics["import_compact_groups"] = int(grade_preview_summary.get("atualizados_grades", 0) or 0)
    metrics["import_grades_available"] = grades_disponiveis
    metrics["selected_items"] = len(parsed_items)

    content_to_save = selected_text or llm_text
    if looks_like_binary_blob(content_to_save):
        content_to_save = ""
    if not content_to_save and parsed_items:
        content_to_save = products_to_text(parsed_items)

    if not content_to_save and not parsed_items:
        _append_process_event(
            metrics,
            source="system",
            level="error",
            message="Import stopped because no usable content or products were extracted.",
        )
        update_import_job(
            job_id,
            "error",
            error="Nao foi possivel extrair conteudo util do arquivo enviado.",
            metrics=metrics,
        )
        return

    if final_validation["rejected"]:
        update_import_job(
            job_id,
            "error",
            error="Import blocked because the extracted data did not match the invoice validation checks.",
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
            grades_disponiveis=grades_disponiveis,
            total_grades_disponiveis=int(grade_preview_summary.get("atualizados_grades", 0) or 0),
            imported_keys=[item.ordering_key() for item in created_items],
            import_batch_id=import_batch_id,
            metrics=metrics,
        )
        update_import_job(job_id, "completed", result=result, metrics=metrics)
    except Exception as exc:
        update_import_job(job_id, "error", error=f"Falha ao importar romaneio: {exc}", metrics=metrics)
