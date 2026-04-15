from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class BulkActionPayload(BaseModel):
    valor: str = ""


class ReorderPayload(BaseModel):
    keys: list[str] = Field(default_factory=list)


class SnapshotProductPayload(BaseModel):
    nome: str = ""
    codigo: str = ""
    ordering_key: str | None = None
    codigo_original: str | None = None
    quantidade: int = Field(0, ge=0)
    preco: str = ""
    categoria: str = ""
    marca: str = ""
    preco_final: str | None = None
    descricao_completa: str | None = None
    grades: list[dict[str, Any]] | None = None
    cores: list[dict[str, Any]] | None = None
    timestamp: str | None = None


class SnapshotRestorePayload(BaseModel):
    items: list[SnapshotProductPayload] = Field(default_factory=list)


class SnapshotRestoreResponse(BaseModel):
    total: int


class FormatCodesPayload(BaseModel):
    remover_prefixo5: bool = False
    remover_zeros_a_esquerda: bool = False
    ultimos_digitos: int | None = Field(default=None, ge=1, le=50)
    primeiros_digitos: int | None = Field(default=None, ge=1, le=50)
    remover_ultimos_numeros: int | None = Field(default=None, ge=1, le=50)
    remover_primeiros_numeros: int | None = Field(default=None, ge=1, le=50)
    manter_primeiros_caracteres: int | None = Field(default=None, ge=1, le=100)
    manter_ultimos_caracteres: int | None = Field(default=None, ge=1, le=100)
    remover_primeiros_caracteres: int | None = Field(default=None, ge=1, le=100)
    remover_ultimos_caracteres: int | None = Field(default=None, ge=1, le=100)
    remover_letras: bool = False
    remover_numeros: bool = False


class FormatCodesResponse(BaseModel):
    total: int
    alterados: int
    prefixo: str | None = None


class RestoreCodesResponse(BaseModel):
    total: int
    restaurados: int


class JoinGradesResponse(BaseModel):
    originais: int
    resultantes: int
    removidos: int
    atualizados_grades: int


class CreateSetPayload(BaseModel):
    key_a: str = Field(..., min_length=1)
    key_b: str = Field(..., min_length=1)


class CreateSetResponse(BaseModel):
    created: int
    removed: int
    remaining_a: int
    remaining_b: int


class MarginPayload(BaseModel):
    percentual: float | None = Field(default=None, gt=0)
    margem: float | None = Field(default=None, gt=0)


class MarginResponse(BaseModel):
    total_atualizados: int
    margem_utilizada: float
    percentual_utilizado: float


class TargetPoint(BaseModel):
    x: int
    y: int


class TargetsPayload(BaseModel):
    title: str | None = None
    byte_empresa_posicao: TargetPoint | None = None
    campo_descricao: TargetPoint | None = None
    tres_pontinhos: TargetPoint | None = None
    cadastro_completo_passo_1: TargetPoint | None = None
    cadastro_completo_passo_2: TargetPoint | None = None
    cadastro_completo_passo_3: TargetPoint | None = None
    cadastro_completo_passo_4: TargetPoint | None = None


class TargetsResponse(BaseModel):
    title: str | None = None
    byte_empresa_posicao: TargetPoint | None = None
    campo_descricao: TargetPoint | None = None
    tres_pontinhos: TargetPoint | None = None
    cadastro_completo_passo_1: TargetPoint | None = None
    cadastro_completo_passo_2: TargetPoint | None = None
    cadastro_completo_passo_3: TargetPoint | None = None
    cadastro_completo_passo_4: TargetPoint | None = None


class TargetCapturePayload(BaseModel):
    target: str = Field(..., min_length=1)


class TargetCaptureResponse(BaseModel):
    target: str
    point: TargetPoint


class ImproveDescriptionPayload(BaseModel):
    remover_numeros: bool = False
    remover_especiais: bool = False
    remover_letras: bool = False
    remover_termos: list[str] = Field(default_factory=list)


class ImproveDescriptionResponse(BaseModel):
    total: int
    modificados: int


class ImportRomaneioStartResponse(BaseModel):
    job_id: str


class ImportRomaneioStatusResponse(BaseModel):
    job_id: str
    stage: str
    message: str
    started_at: float
    updated_at: float
    completed_at: float | None = None
    error: str | None = None
    metrics: dict[str, Any] = Field(default_factory=dict)


class ImportRomaneioResultResponse(BaseModel):
    status: str
    saved_file: str | None = None
    local_file: str | None = None
    content: str | None = None
    warnings: list[str] = Field(default_factory=list)
    total_itens: int = 0
    metrics: dict[str, Any] = Field(default_factory=dict)


class GradeConfigPayload(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    buttons: dict[str, TargetPoint] | None = None
    first_quant_cell: TargetPoint | None = None
    second_quant_cell: TargetPoint | None = None
    row_height: int | None = None
    model_index: int | None = None
    model_hotkey: str | None = None
    erp_size_order: list[str] | None = None
    ui_size_order: list[str] | None = None
    ui_families: list[dict[str, Any]] | None = None
    ui_family_version: int | None = None


class GradeRunPayload(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    grades: dict[str, int] | None = None
    grades_json: str | None = None
    model_index: int | None = None
    pause: float | None = None
    speed: float | None = None


class GradesBatchPayload(BaseModel):
    tasks: list[GradeRunPayload] = Field(default_factory=list)
    pause: float | None = None
    speed: float | None = None


class GradeExtractionProduct(BaseModel):
    codigo: str | None = None
    nome: str | None = None
    grades: dict[str, int] = Field(default_factory=dict)
    atualizado: bool
    warnings: list[str] = Field(default_factory=list)


class GradeExtractionResponse(BaseModel):
    status: str
    total_itens: int
    total_atualizados: int
    warnings: list[str] = Field(default_factory=list)
    itens: list[GradeExtractionProduct] = Field(default_factory=list)
    content: str | None = None


class GradeExtractionStatusResponse(BaseModel):
    job_id: str
    stage: str
    message: str
    started_at: float
    updated_at: float
    completed_at: float | None = None
    error: str | None = None


class GradeExtractionStartResponse(BaseModel):
    job_id: str
