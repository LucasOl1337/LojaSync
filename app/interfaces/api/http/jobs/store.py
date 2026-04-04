from __future__ import annotations

from typing import Any

from app.interfaces.api.http.route_models import (
    GradeExtractionResponse,
    GradeExtractionStatusResponse,
    ImportRomaneioResultResponse,
    ImportRomaneioStatusResponse,
)
from app.shared.jobs.in_memory import InMemoryJobStore
from app.shared.ui_events import publish_job_updated, publish_state_changed

IMPORT_JOB_STAGES = {
    "pending": "Aguardando inicio",
    "uploading": "Enviando arquivo para servico LLM",
    "processing": "Processando com servico LLM",
    "parsing": "Interpretando itens detectados",
    "completed": "Concluido",
    "error": "Falha no processamento",
}

GRADE_JOB_STAGES = {
    "pending": "Aguardando inicio",
    "uploading": "Enviando nota para servico LLM",
    "processing": "Detectando grades via LLM",
    "parsing": "Interpretando grades e aplicando nos produtos",
    "completed": "Processo de grades concluido",
    "error": "Processamento de grades interrompido",
}
_import_jobs = InMemoryJobStore[ImportRomaneioStatusResponse, ImportRomaneioResultResponse](
    stage_messages=IMPORT_JOB_STAGES,
    status_factory=ImportRomaneioStatusResponse,
)

_grade_jobs = InMemoryJobStore[GradeExtractionStatusResponse, GradeExtractionResponse](
    stage_messages=GRADE_JOB_STAGES,
    status_factory=GradeExtractionStatusResponse,
)


def create_import_job() -> ImportRomaneioStatusResponse:
    job = _import_jobs.create()
    publish_job_updated(job="import_romaneio", job_id=job.job_id, stage=job.stage, message=job.message, error=job.error)
    return job


def update_import_job(
    job_id: str,
    stage: str,
    *,
    message: str | None = None,
    error: str | None = None,
    result: ImportRomaneioResultResponse | None = None,
    metrics: dict[str, Any] | None = None,
) -> None:
    _import_jobs.update(
        job_id,
        stage,
        message=message,
        error=error,
        result=result,
        metrics=metrics,
    )
    job = _import_jobs.get_job(job_id)
    if job is not None:
        publish_job_updated(
            job="import_romaneio",
            job_id=job.job_id,
            stage=job.stage,
            message=job.message,
            error=job.error,
        )
    if stage == "completed":
        publish_state_changed(["products", "totals", "brands"])


def get_import_job(job_id: str) -> ImportRomaneioStatusResponse | None:
    return _import_jobs.get_job(job_id)


def get_import_result(job_id: str) -> ImportRomaneioResultResponse | None:
    return _import_jobs.get_result(job_id)


def remove_import_job(job_id: str) -> bool:
    return _import_jobs.remove(job_id)


def create_grade_job() -> GradeExtractionStatusResponse:
    job = _grade_jobs.create()
    publish_job_updated(job="parser_grades", job_id=job.job_id, stage=job.stage, message=job.message, error=job.error)
    return job


def update_grade_job(
    job_id: str,
    stage: str,
    *,
    message: str | None = None,
    error: str | None = None,
    result: GradeExtractionResponse | None = None,
) -> None:
    _grade_jobs.update(
        job_id,
        stage,
        message=message,
        error=error,
        result=result,
    )
    job = _grade_jobs.get_job(job_id)
    if job is not None:
        publish_job_updated(
            job="parser_grades",
            job_id=job.job_id,
            stage=job.stage,
            message=job.message,
            error=job.error,
        )
    if stage == "completed":
        publish_state_changed(["products", "totals"])


def get_grade_job(job_id: str) -> GradeExtractionStatusResponse | None:
    return _grade_jobs.get_job(job_id)


def get_grade_result(job_id: str) -> GradeExtractionResponse | None:
    return _grade_jobs.get_result(job_id)


def remove_grade_job(job_id: str) -> bool:
    return _grade_jobs.remove(job_id)
