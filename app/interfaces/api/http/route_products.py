from __future__ import annotations

import json

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from fastapi.responses import Response

from app.domain.products.entities import Product
from app.interfaces.api.http.route_jobs import (
    create_post_process_job,
    get_post_process_job,
    get_post_process_result,
    remove_post_process_job,
    run_post_process_job,
    update_post_process_job,
)
from app.interfaces.api.http.route_models import (
    BulkActionPayload,
    CreateSetPayload,
    CreateSetResponse,
    FormatCodesPayload,
    FormatCodesResponse,
    ImproveDescriptionPayload,
    ImproveDescriptionResponse,
    JoinGradesPayload,
    JoinGradesResponse,
    MarginPayload,
    MarginResponse,
    PostProcessProductsResultResponse,
    PostProcessProductsStartResponse,
    PostProcessProductsStatusResponse,
    ReorderPayload,
    RestoreCodesResponse,
    SnapshotRestorePayload,
    SnapshotRestoreResponse,
)
from app.interfaces.api.http.route_shared import CATALOG_SIZES, get_product_service, product_to_response
from app.interfaces.api.schemas.products import (
    BrandPayload,
    BrandsResponse,
    MarginSettingsPayload,
    MarginSettingsResponse,
    ProductItemResponse,
    ProductListResponse,
    ProductPatchPayload,
    ProductPayload,
    TotalsInfo,
    TotalsResponse,
)
from app.shared.ui_events import publish_state_changed

router = APIRouter()


@router.get("/products", response_model=ProductListResponse)
async def list_products(request: Request) -> ProductListResponse:
    products = get_product_service(request).list_products()
    return ProductListResponse(items=[product_to_response(item) for item in products])


@router.get("/catalog/sizes")
async def catalog_sizes() -> dict[str, list[str]]:
    return {"sizes": CATALOG_SIZES}


@router.post("/products", response_model=ProductItemResponse, status_code=201)
async def create_product(payload: ProductPayload, request: Request) -> ProductItemResponse:
    created = get_product_service(request).create_product(
        Product(
            nome=payload.nome,
            codigo=payload.codigo,
            quantidade=payload.quantidade,
            preco=payload.preco,
            categoria=payload.categoria,
            marca=payload.marca,
            preco_final=payload.preco_final,
            descricao_completa=payload.descricao_completa,
            codigo_original=payload.codigo,
            grades=payload.grades,
            cores=payload.cores,
            source_type="manual",
            pending_grade_import=False,
        )
    )
    publish_state_changed(["products", "totals", "brands"])
    return ProductItemResponse(item=product_to_response(created))


@router.patch("/products/{ordering_key:path}", response_model=ProductItemResponse)
async def patch_product(ordering_key: str, payload: ProductPatchPayload, request: Request) -> ProductItemResponse:
    updated = get_product_service(request).update_product(
        ordering_key,
        payload.model_dump(exclude_unset=True),
    )
    if updated is None:
        raise HTTPException(status_code=404, detail="Produto nao encontrado")
    publish_state_changed(["products", "totals", "brands"])
    return ProductItemResponse(item=product_to_response(updated))


@router.delete("/products")
async def clear_products(request: Request) -> dict[str, int]:
    removed = get_product_service(request).clear_products()
    if removed:
        publish_state_changed(["products", "totals", "brands"])
    return {"removed": removed}


@router.delete("/products/{ordering_key:path}")
async def delete_product(ordering_key: str, request: Request) -> dict[str, str]:
    success = get_product_service(request).delete_product(ordering_key)
    if not success:
        raise HTTPException(status_code=404, detail="Produto nao encontrado")
    publish_state_changed(["products", "totals"])
    return {"status": "deleted", "ordering_key": ordering_key}


@router.get("/brands", response_model=BrandsResponse)
async def list_brands(request: Request) -> BrandsResponse:
    return BrandsResponse(marcas=get_product_service(request).list_brands())


@router.post("/brands", response_model=BrandsResponse)
async def add_brand(payload: BrandPayload, request: Request) -> BrandsResponse:
    result = BrandsResponse(marcas=get_product_service(request).add_brand(payload.nome))
    publish_state_changed(["brands"])
    return result


@router.get("/settings/margin", response_model=MarginSettingsResponse)
async def get_margin(request: Request) -> MarginSettingsResponse:
    margin = get_product_service(request).get_default_margin()
    percentual = (margin - 1) * 100
    return MarginSettingsResponse(margem=margin, percentual=percentual)


@router.post("/settings/margin", response_model=MarginSettingsResponse)
async def set_margin(payload: MarginSettingsPayload, request: Request) -> MarginSettingsResponse:
    margin = get_product_service(request).set_default_margin(1 + payload.percentual / 100.0)
    publish_state_changed(["margin", "products", "totals"])
    return MarginSettingsResponse(margem=margin, percentual=payload.percentual)


@router.get("/totals", response_model=TotalsResponse)
async def get_totals(request: Request) -> TotalsResponse:
    summary = get_product_service(request).get_summary()
    return TotalsResponse(
        atual=TotalsInfo(
            quantidade=summary.atual.quantidade,
            custo=summary.atual.custo,
            venda=summary.atual.venda,
        ),
        historico=TotalsInfo(
            quantidade=summary.historico.quantidade,
            custo=summary.historico.custo,
            venda=summary.historico.venda,
        ),
        tempo_economizado=summary.metrics.tempo_economizado,
        caracteres_digitados=summary.metrics.caracteres_digitados,
    )


@router.post("/actions/apply-category")
async def apply_category(payload: BulkActionPayload, request: Request) -> dict[str, object]:
    total = get_product_service(request).apply_category(payload.valor)
    if total:
        publish_state_changed(["products", "totals"])
    return {"status": "categoria aplicada", "categoria": payload.valor, "total": total}


@router.post("/actions/apply-brand")
async def apply_brand(payload: BulkActionPayload, request: Request) -> dict[str, object]:
    total = get_product_service(request).apply_brand(payload.valor)
    if total:
        publish_state_changed(["products", "totals", "brands"])
    return {"status": "marca aplicada", "marca": payload.valor, "total": total}


@router.post("/actions/join-duplicates")
async def join_duplicates(request: Request) -> dict[str, int]:
    result = get_product_service(request).join_duplicates()
    if result.get("removed"):
        publish_state_changed(["products", "totals"])
    return result


@router.post("/actions/reorder")
async def reorder_products(payload: ReorderPayload, request: Request) -> dict[str, int]:
    total = get_product_service(request).reorder_by_keys(payload.keys)
    if total:
        publish_state_changed(["products"])
    return {"total": total}


@router.post("/actions/join-grades")
async def join_grades(payload: JoinGradesPayload, request: Request) -> JoinGradesResponse:
    result = get_product_service(request).join_with_grades(payload.keys)
    if result.get("removidos") or result.get("atualizados_grades") or result.get("lotes_processados"):
        publish_state_changed(["products", "totals"])
    return JoinGradesResponse(**result)


@router.post("/actions/restore-snapshot", response_model=SnapshotRestoreResponse)
async def restore_snapshot(payload: SnapshotRestorePayload, request: Request) -> SnapshotRestoreResponse:
    products = [Product.from_dict(item.model_dump()) for item in payload.items]
    total = get_product_service(request).restore_snapshot(products)
    publish_state_changed(["products", "totals", "brands"])
    return SnapshotRestoreResponse(total=total)


@router.post("/actions/format-codes", response_model=FormatCodesResponse)
async def format_codes(payload: FormatCodesPayload, request: Request) -> FormatCodesResponse:
    result = get_product_service(request).format_codes(payload.model_dump())
    if result.get("alterados"):
        publish_state_changed(["products"])
    return FormatCodesResponse(**result)


@router.post("/actions/restore-original-codes", response_model=RestoreCodesResponse)
async def restore_original_codes(request: Request) -> RestoreCodesResponse:
    result = get_product_service(request).restore_original_codes()
    if result.get("restaurados"):
        publish_state_changed(["products"])
    return RestoreCodesResponse(**result)


@router.post("/actions/apply-margin", response_model=MarginResponse)
async def apply_margin(payload: MarginPayload, request: Request) -> MarginResponse:
    margin_factor = payload.margem if payload.margem is not None else None
    if margin_factor is None and payload.percentual is not None:
        margin_factor = 1 + payload.percentual / 100.0
    if margin_factor is None or margin_factor <= 0:
        raise HTTPException(status_code=400, detail="Margem invalida")
    total = get_product_service(request).apply_margin_to_products(margin_factor)
    percentual = (margin_factor - 1) * 100
    if total:
        publish_state_changed(["products", "totals", "margin"])
    return MarginResponse(
        total_atualizados=total,
        margem_utilizada=margin_factor,
        percentual_utilizado=percentual,
    )


@router.post("/actions/create-set", response_model=CreateSetResponse)
async def create_set(payload: CreateSetPayload, request: Request) -> CreateSetResponse:
    result = get_product_service(request).create_set_by_keys(payload.key_a, payload.key_b)
    if not result:
        raise HTTPException(status_code=400, detail="Nao foi possivel criar o conjunto selecionado.")
    publish_state_changed(["products", "totals"])
    return CreateSetResponse(**result)


@router.post("/actions/improve-descriptions", response_model=ImproveDescriptionResponse)
async def improve_descriptions(payload: ImproveDescriptionPayload, request: Request) -> ImproveDescriptionResponse:
    has_terms = bool([term for term in payload.remover_termos if str(term).strip()])
    if not payload.remover_numeros and not payload.remover_especiais and not payload.remover_letras and not has_terms:
        raise HTTPException(status_code=400, detail="Selecione ao menos uma opcao de limpeza.")
    result = get_product_service(request).improve_descriptions(
        payload.remover_numeros,
        payload.remover_especiais,
        payload.remover_letras,
        payload.remover_termos,
    )
    if result.get("modificados"):
        publish_state_changed(["products"])
    return ImproveDescriptionResponse(**result)


@router.post("/actions/post-process-products", response_model=PostProcessProductsStartResponse)
async def start_post_process_products(
    request: Request,
    background: BackgroundTasks,
) -> PostProcessProductsStartResponse:
    service = get_product_service(request)
    if not service.list_products():
        raise HTTPException(status_code=400, detail="Nao ha produtos para pos-processar")

    job = create_post_process_job()
    update_post_process_job(job.job_id, "processing")
    background.add_task(
        run_post_process_job,
        job_id=job.job_id,
        service=service,
    )
    return PostProcessProductsStartResponse(job_id=job.job_id)


@router.get("/actions/post-process-products/status/{job_id}", response_model=PostProcessProductsStatusResponse)
async def post_process_products_status(job_id: str) -> PostProcessProductsStatusResponse:
    job = get_post_process_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job nao encontrado")
    return job


@router.get("/actions/post-process-products/result/{job_id}", response_model=PostProcessProductsResultResponse)
async def post_process_products_result(job_id: str) -> PostProcessProductsResultResponse:
    job = get_post_process_job(job_id)
    result = get_post_process_result(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job nao encontrado")
    if job.stage != "completed":
        raise HTTPException(status_code=409, detail="Processamento ainda em andamento")
    if result is None:
        raise HTTPException(status_code=500, detail="Resultado indisponivel")
    return result


@router.delete("/actions/post-process-products/status/{job_id}")
async def post_process_products_cleanup(job_id: str) -> dict[str, str]:
    if not remove_post_process_job(job_id):
        raise HTTPException(status_code=404, detail="Job nao encontrado")
    return {"status": "removed", "job_id": job_id}


@router.get("/actions/export-json")
async def export_json(request: Request) -> Response:
    items = get_product_service(request).list_products()
    content = "\n".join(json.dumps(item.to_dict(), ensure_ascii=False) for item in items)
    return Response(
        content=content,
        media_type="application/x-ndjson",
        headers={"Content-Disposition": 'attachment; filename="products_active.jsonl"'},
    )
