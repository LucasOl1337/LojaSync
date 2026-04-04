from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, Request, UploadFile

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
)

router = APIRouter()


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


@router.delete("/actions/import-romaneio/status/{job_id}")
async def import_romaneio_cleanup(job_id: str) -> dict[str, str]:
    if not remove_import_job(job_id):
        raise HTTPException(status_code=404, detail="Job nao encontrado")
    return {"status": "removed", "job_id": job_id}
