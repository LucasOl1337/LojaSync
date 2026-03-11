from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class GradeItemPayload(BaseModel):
    tamanho: str = Field(..., min_length=1)
    quantidade: int = Field(..., ge=0)


class CorItemPayload(BaseModel):
    cor: str = Field(..., min_length=1)
    quantidade: int = Field(..., ge=0)


class ProductPayload(BaseModel):
    nome: str = Field(..., min_length=1)
    codigo: str = ""
    quantidade: int = Field(1, ge=0)
    preco: str = Field(..., min_length=1)
    categoria: str = ""
    marca: str = ""
    preco_final: str | None = None
    descricao_completa: str | None = None
    grades: list[GradeItemPayload] | None = None
    cores: list[CorItemPayload] | None = None


class ProductResponse(BaseModel):
    nome: str
    codigo: str
    codigo_original: str | None
    quantidade: int
    preco: str
    categoria: str
    marca: str
    preco_final: str | None
    descricao_completa: str | None
    grades: list[GradeItemPayload] | None = None
    cores: list[CorItemPayload] | None = None
    timestamp: datetime
    ordering_key: str


class ProductListResponse(BaseModel):
    items: list[ProductResponse]


class ProductItemResponse(BaseModel):
    item: ProductResponse


class ProductPatchPayload(BaseModel):
    nome: str | None = None
    codigo: str | None = None
    quantidade: int | None = Field(default=None, ge=0)
    preco: str | None = None
    categoria: str | None = None
    marca: str | None = None
    preco_final: str | None = None
    descricao_completa: str | None = None
    grades: list[GradeItemPayload] | None = None
    cores: list[CorItemPayload] | None = None


class BrandPayload(BaseModel):
    nome: str = Field(..., min_length=1)


class BrandsResponse(BaseModel):
    marcas: list[str]


class TotalsInfo(BaseModel):
    quantidade: int
    custo: float
    venda: float


class TotalsResponse(BaseModel):
    atual: TotalsInfo
    historico: TotalsInfo
    tempo_economizado: int
    caracteres_digitados: int


class MarginSettingsPayload(BaseModel):
    percentual: float = Field(..., gt=0)


class MarginSettingsResponse(BaseModel):
    margem: float
    percentual: float
