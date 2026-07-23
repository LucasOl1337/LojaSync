from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, Request, UploadFile

from app.application.imports.parsing import parse_candidate_content, products_to_text, save_romaneio_text
from app.interfaces.api.http.jobs.store import cancel_import_job
from app.interfaces.api.http.route_jobs import (
    create_grade_job,
    create_import_job,
    get_grade_job,
    get_grade_result,
    get_import_job,
    get_import_result,
    remove_grade_job,
    remove_import_job,
    run_grade_extraction_job,
    run_import_job,
    update_grade_job,
    update_import_job,
)
from app.interfaces.api.http.route_models import (
    GradeExtractionResponse,
    GradeExtractionStartResponse,
    GradeExtractionStatusResponse,
    ImportRomaneioResultResponse,
    ImportRomaneioStartResponse,
    ImportRomaneioStatusResponse,
    ReapplyImportPayload,
)
from app.shared.ui_events import publish_state_changed

router = APIRouter()


def _safe_romaneio_text(data_dir: Path, local_file: str | None) -> str:
    """Read a previously saved romaneio text only if it stays under data_dir/romaneios."""
    raw = str(local_file or "").strip()
    if not raw:
        return ""
    try:
        candidate = Path(raw).expanduser().resolve()
        romaneio_root = (data_dir / "romaneios").resolve()
        if romaneio_root not in candidate.parents and candidate.parent != romaneio_root:
            return ""
        if not candidate.is_file():
            return ""
        return candidate.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


@router.post("/actions/parser-grades", response_model=GradeExtractionStartResponse)
async def start_grade_parser(
    request: Request,
    background: BackgroundTasks,
    file: UploadFile = File(...),
) -> GradeExtractionStartResponse:
    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Arquivo vazio ou invalido")
    job = create_grade_job()
    update_grade_job(job.job_id, "uploading")
    background.add_task(
        run_grade_extraction_job,
        job_id=job.job_id,
        contents=contents,
        filename=file.filename or "nota_fiscal",
        content_type=file.content_type,
        service=request.app.state.container.product_service,
    )
    return GradeExtractionStartResponse(job_id=job.job_id)


@router.get("/actions/parser-grades/status/{job_id}", response_model=GradeExtractionStatusResponse)
async def parser_grades_status(job_id: str) -> GradeExtractionStatusResponse:
    job = get_grade_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job nao encontrado")
    return job


@router.get("/actions/parser-grades/result/{job_id}", response_model=GradeExtractionResponse)
async def parser_grades_result(job_id: str) -> GradeExtractionResponse:
    job = get_grade_job(job_id)
    result = get_grade_result(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job nao encontrado")
    if job.stage != "completed":
        raise HTTPException(status_code=409, detail="Processamento ainda em andamento")
    if result is None:
        raise HTTPException(status_code=500, detail="Resultado indisponivel")
    return result


@router.delete("/actions/parser-grades/status/{job_id}")
async def parser_grades_cleanup(job_id: str) -> dict[str, str]:
    if not remove_grade_job(job_id):
        raise HTTPException(status_code=404, detail="Job nao encontrado")
    return {"status": "removed", "job_id": job_id}


@router.post("/actions/import-romaneio", response_model=ImportRomaneioStartResponse)
async def import_romaneio(
    request: Request,
    background: BackgroundTasks,
    file: UploadFile = File(...),
) -> ImportRomaneioStartResponse:
    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Arquivo vazio ou invalido")

    job = create_import_job()
    update_import_job(job.job_id, "uploading")
    container = request.app.state.container
    background.add_task(
        run_import_job,
        job_id=job.job_id,
        contents=contents,
        filename=file.filename or "romaneio",
        content_type=file.content_type,
        service=container.product_service,
        data_dir=container.paths.data_dir,
        prefer_llm=True,
        skip_local_parser=True,
    )
    return ImportRomaneioStartResponse(job_id=job.job_id)


@router.get("/actions/import-romaneio/status/{job_id}", response_model=ImportRomaneioStatusResponse)
async def import_romaneio_status(job_id: str) -> ImportRomaneioStatusResponse:
    job = get_import_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job nao encontrado")
    return job


@router.get("/actions/import-romaneio/result/{job_id}", response_model=ImportRomaneioResultResponse)
async def import_romaneio_result(job_id: str) -> ImportRomaneioResultResponse:
    job = get_import_job(job_id)
    result = get_import_result(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job nao encontrado")
    if job.stage != "completed":
        raise HTTPException(status_code=409, detail="Processamento ainda em andamento")
    if result is None:
        raise HTTPException(status_code=500, detail="Resultado indisponivel")
    return result


@router.post("/actions/import-romaneio/cancel/{job_id}")
async def import_romaneio_cancel(job_id: str) -> dict[str, str]:
    """Abort a running import: cooperative flag + close active LLM HTTP client."""
    job = cancel_import_job(job_id)
    if job is None:
        # Still signal cancel in case the worker exists but status was already removed.
        from app.interfaces.api.http.jobs.cancel import request_import_cancel

        request_import_cancel(job_id)
        raise HTTPException(status_code=404, detail="Job nao encontrado")
    return {
        "status": "cancelled",
        "job_id": job_id,
        "stage": str(getattr(job, "stage", "cancelled") or "cancelled"),
    }


@router.delete("/actions/import-romaneio/status/{job_id}")
async def import_romaneio_cleanup(job_id: str) -> dict[str, str]:
    # DELETE also cancels any in-flight worker, then drops job state.
    if not remove_import_job(job_id):
        raise HTTPException(status_code=404, detail="Job nao encontrado")
    return {"status": "removed", "job_id": job_id}


@router.post("/actions/import-romaneio/reapply", response_model=ImportRomaneioResultResponse)
async def reapply_import_to_catalog(
    payload: ReapplyImportPayload,
    request: Request,
) -> ImportRomaneioResultResponse:
    """Send already-processed import text back into the catalog without LLM/local rescan."""
    container = request.app.state.container
    content = str(payload.content or "").strip()
    if not content:
        content = _safe_romaneio_text(container.paths.data_dir, payload.local_file).strip()
    if not content:
        raise HTTPException(
            status_code=400,
            detail="Nao ha conteudo processado para reenviar ao catalogo. Reabra a importacao ou importe o romaneio de novo.",
        )

    products = parse_candidate_content(content)
    if not products:
        raise HTTPException(
            status_code=422,
            detail="O resultado processado nao contem itens reaplicaveis. Use Reabrir para conferir ou importe de novo.",
        )

    import_batch_id = uuid4().hex
    source_name = str(payload.source_name or "romaneio").strip() or "romaneio"
    mode = str(payload.import_mode or "").strip().lower()
    source_type = "romaneio_local" if mode in {"local", "leitura local", "leitura_local"} else "romaneio"
    grades_available = bool(payload.grades_disponiveis)

    for item in products:
        item.source_type = source_type
        item.import_batch_id = import_batch_id
        item.import_source_name = source_name
        item.pending_grade_import = grades_available

    created = container.product_service.create_many(products)
    local_file = save_romaneio_text(container.paths.data_dir, products_to_text(created) if created else content)
    publish_state_changed(["products", "totals", "brands"])

    return ImportRomaneioResultResponse(
        status="ok",
        saved_file=None,
        local_file=str(local_file),
        content=products_to_text(created) if created else content,
        warnings=[],
        total_itens=len(created),
        grades_disponiveis=grades_available,
        total_grades_disponiveis=0,
        imported_keys=[item.ordering_key() for item in created],
        import_batch_id=import_batch_id,
        metrics={
            "selected_source": "reapply_processed",
            "imported_items": len(created),
            "reapplied": True,
            "llm_skipped": True,
        },
    )
