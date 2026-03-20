from __future__ import annotations

from typing import Any

from fastapi import Request

from app.domain.products.entities import Product
from app.interfaces.api.http.route_models import TargetPoint, TargetsResponse
from app.interfaces.api.schemas.products import ProductResponse

CATALOG_SIZES = [
    "1",
    "2",
    "3",
    "01",
    "02",
    "03",
    "04",
    "06",
    "08",
    "10",
    "12",
    "14",
    "16",
    "18",
    "U",
    "PP",
    "P",
    "M",
    "G",
    "GG",
    "XG",
    "XXG",
    "G1",
    "G2",
    "G3",
    "34",
    "36",
    "38",
    "40",
    "42",
    "44",
    "46",
    "48",
    "50",
    "52",
    "54",
    "56",
]


def get_product_service(request: Request):
    return request.app.state.container["product_service"]


def get_automation_service(request: Request):
    return request.app.state.container["automation_service"]


def product_to_response(product: Product) -> ProductResponse:
    grades = (
        [{"tamanho": item.tamanho, "quantidade": int(item.quantidade)} for item in (product.grades or [])]
        if product.grades
        else None
    )
    cores = (
        [{"cor": item.cor, "quantidade": int(item.quantidade)} for item in (product.cores or [])]
        if product.cores
        else None
    )
    return ProductResponse(
        nome=product.nome,
        codigo=product.codigo,
        codigo_original=product.codigo_original,
        quantidade=product.quantidade,
        preco=product.preco,
        categoria=product.categoria,
        marca=product.marca,
        preco_final=product.preco_final,
        descricao_completa=product.descricao_completa,
        grades=grades,
        cores=cores,
        timestamp=product.timestamp,
        ordering_key=product.ordering_key(),
    )


def as_target_point(value: Any) -> TargetPoint | None:
    if isinstance(value, dict) and "x" in value and "y" in value:
        try:
            return TargetPoint(x=int(value["x"]), y=int(value["y"]))
        except Exception:
            return None
    return None


def build_targets_response(payload: dict[str, Any]) -> TargetsResponse:
    return TargetsResponse(
        title=str(payload.get("title")).strip() if isinstance(payload.get("title"), str) and payload.get("title") else None,
        byte_empresa_posicao=as_target_point(payload.get("byte_empresa_posicao")),
        campo_descricao=as_target_point(payload.get("campo_descricao")),
        tres_pontinhos=as_target_point(payload.get("tres_pontinhos")),
        cadastro_completo_passo_1=as_target_point(payload.get("cadastro_completo_passo_1")),
        cadastro_completo_passo_2=as_target_point(payload.get("cadastro_completo_passo_2")),
        cadastro_completo_passo_3=as_target_point(payload.get("cadastro_completo_passo_3")),
        cadastro_completo_passo_4=as_target_point(payload.get("cadastro_completo_passo_4")),
    )
