from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response

from app.domain.products.entities import Product
from app.application.products.service import ProductSetCompositionConflictError
from app.interfaces.api.http.route_models import (
    BulkActionPayload,
    CreateSetPayload,
    CreateSetResponse,
    FormatCodesPayload,
    FormatCodesResponse,
    HistorySnapshotPayload,
    ImproveDescriptionPayload,
    ImproveDescriptionResponse,
    JoinGradesPayload,
    JoinGradesResponse,
    JoinDuplicatesPayload,
    MarginPayload,
    MarginResponse,
    ReorderPayload,
    RestoreCodesPayload,
    RestoreCodesResponse,
    SnapshotRestorePayload,
    SnapshotRestoreResponse,
    UndoRedoApplyResponse,
    UndoRedoHistoryResponse,
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


def _maybe_record_undo(service, *, dry_run: bool) -> None:
    if not dry_run:
        service.record_undo_snapshot(clear_redo=True)


def _with_dry_run_meta(payload: dict[str, object], *, dry_run: bool) -> dict[str, object]:
    return {**payload, "dry_run": dry_run}


def _history_response(state) -> UndoRedoHistoryResponse:
    return UndoRedoHistoryResponse(
        undo_count=state.undo_count,
        redo_count=state.redo_count,
        limit=state.limit,
        can_undo=state.can_undo,
        can_redo=state.can_redo,
    )


def _history_apply_response(*, restored: bool, total: int, state) -> UndoRedoApplyResponse:
    return UndoRedoApplyResponse(
        **_history_response(state).model_dump(),
        restored=restored,
        total=total,
    )


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
    changes = payload.model_dump(exclude_unset=True)
    for field_name in ("nome", "codigo", "quantidade", "preco", "categoria", "marca"):
        if field_name in changes and changes[field_name] is None:
            changes.pop(field_name)
    updated = get_product_service(request).update_product(
        ordering_key,
        changes,
    )
    if updated is None:
        raise HTTPException(status_code=404, detail="Produto nao encontrado")
    publish_state_changed(["products", "totals", "brands"])
    return ProductItemResponse(item=product_to_response(updated))


@router.delete("/products")
async def clear_products(request: Request, dry_run: bool = False) -> dict[str, object]:
    service = get_product_service(request)
    if not dry_run:
        _maybe_record_undo(service, dry_run=False)
    removed = service.clear_products(persist=not dry_run)
    if removed and not dry_run:
        publish_state_changed(["products", "totals", "brands"])
    return _with_dry_run_meta({"removed": removed}, dry_run=dry_run)


@router.delete("/products/{ordering_key:path}")
async def delete_product(ordering_key: str, request: Request) -> dict[str, str]:
    service = get_product_service(request)
    service.record_undo_snapshot(clear_redo=True)
    success = service.delete_product(ordering_key)
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
    service = get_product_service(request)
    _maybe_record_undo(service, dry_run=payload.dry_run)
    total = service.apply_category(payload.valor, payload.keys, persist=not payload.dry_run)
    if total and not payload.dry_run:
        publish_state_changed(["products", "totals"])
    return _with_dry_run_meta(
        {"status": "categoria aplicada", "categoria": payload.valor, "total": total},
        dry_run=payload.dry_run,
    )


@router.post("/actions/apply-brand")
async def apply_brand(payload: BulkActionPayload, request: Request) -> dict[str, object]:
    service = get_product_service(request)
    _maybe_record_undo(service, dry_run=payload.dry_run)
    total = service.apply_brand(payload.valor, payload.keys, persist=not payload.dry_run)
    if total and not payload.dry_run:
        publish_state_changed(["products", "totals", "brands"])
    return _with_dry_run_meta(
        {"status": "marca aplicada", "marca": payload.valor, "total": total},
        dry_run=payload.dry_run,
    )


@router.post("/actions/join-duplicates")
async def join_duplicates(request: Request, payload: JoinDuplicatesPayload | None = None, dry_run: bool = False) -> dict[str, object]:
    service = get_product_service(request)
    _maybe_record_undo(service, dry_run=dry_run)
    result = service.join_duplicates(payload.keys if payload else None, persist=not dry_run)
    if result.get("removidos") and not dry_run:
        publish_state_changed(["products", "totals"])
    return _with_dry_run_meta(result, dry_run=dry_run) if payload is None else result


@router.post("/actions/reorder")
async def reorder_products(payload: ReorderPayload, request: Request) -> dict[str, int]:
    total = get_product_service(request).reorder_by_keys(payload.keys)
    if total:
        publish_state_changed(["products"])
    return {"total": total}


@router.post("/actions/join-grades")
async def join_grades(payload: JoinGradesPayload, request: Request) -> dict[str, object]:
    service = get_product_service(request)
    _maybe_record_undo(service, dry_run=payload.dry_run)
    result = service.join_with_grades(payload.keys, persist=not payload.dry_run)
    if (result.get("removidos") or result.get("atualizados_grades") or result.get("lotes_processados")) and not payload.dry_run:
        publish_state_changed(["products", "totals"])
    return _with_dry_run_meta(JoinGradesResponse(**result).model_dump(), dry_run=payload.dry_run)


@router.post("/actions/restore-snapshot", response_model=SnapshotRestoreResponse)
async def restore_snapshot(payload: SnapshotRestorePayload, request: Request) -> SnapshotRestoreResponse:
    products = [Product.from_dict(item.model_dump()) for item in payload.items]
    total = get_product_service(request).restore_snapshot(products)
    publish_state_changed(["products", "totals", "brands"])
    return SnapshotRestoreResponse(total=total)


@router.get("/actions/history", response_model=UndoRedoHistoryResponse)
async def get_undo_redo_history(request: Request) -> UndoRedoHistoryResponse:
    return _history_response(get_product_service(request).get_undo_redo_history_state())


@router.post("/actions/history/snapshot", response_model=UndoRedoHistoryResponse)
async def record_undo_snapshot(request: Request, payload: HistorySnapshotPayload | None = None) -> UndoRedoHistoryResponse:
    state = get_product_service(request).record_undo_snapshot(clear_redo=True if payload is None else payload.clear_redo)
    publish_state_changed(["history"])
    return _history_response(state)


@router.post("/actions/history/undo", response_model=UndoRedoApplyResponse)
async def undo_last_snapshot(request: Request) -> UndoRedoApplyResponse:
    restored, total, state = get_product_service(request).undo_last_snapshot()
    if restored:
        publish_state_changed(["products", "totals", "brands", "history"])
    return _history_apply_response(restored=restored, total=total, state=state)


@router.post("/actions/history/redo", response_model=UndoRedoApplyResponse)
async def redo_last_snapshot(request: Request) -> UndoRedoApplyResponse:
    restored, total, state = get_product_service(request).redo_last_snapshot()
    if restored:
        publish_state_changed(["products", "totals", "brands", "history"])
    return _history_apply_response(restored=restored, total=total, state=state)


@router.post("/actions/format-codes")
async def format_codes(payload: FormatCodesPayload, request: Request) -> dict[str, object]:
    service = get_product_service(request)
    _maybe_record_undo(service, dry_run=payload.dry_run)
    options = payload.model_dump(exclude={"dry_run"})
    result = service.format_codes(options, payload.keys, persist=not payload.dry_run)
    if result.get("alterados") and not payload.dry_run:
        publish_state_changed(["products"])
    return _with_dry_run_meta(FormatCodesResponse(**result).model_dump(), dry_run=payload.dry_run)


@router.post("/actions/restore-original-codes", response_model=RestoreCodesResponse)
async def restore_original_codes(request: Request, payload: RestoreCodesPayload | None = None) -> RestoreCodesResponse:
    service = get_product_service(request)
    service.record_undo_snapshot(clear_redo=True)
    result = service.restore_original_codes(payload.keys if payload else None)
    if result.get("restaurados"):
        publish_state_changed(["products"])
    return RestoreCodesResponse(**result)


@router.post("/actions/apply-margin")
async def apply_margin(payload: MarginPayload, request: Request) -> dict[str, object]:
    margin_factor = payload.margem if payload.margem is not None else None
    if margin_factor is None and payload.percentual is not None:
        margin_factor = 1 + payload.percentual / 100.0
    if margin_factor is None or margin_factor <= 0:
        raise HTTPException(status_code=400, detail="Margem invalida")
    service = get_product_service(request)
    total = service.apply_margin_to_products(margin_factor, payload.keys, persist=not payload.dry_run)
    percentual = (margin_factor - 1) * 100
    if total and not payload.dry_run:
        publish_state_changed(["products", "totals", "margin"])
    return _with_dry_run_meta(
        MarginResponse(
            total_atualizados=total,
            margem_utilizada=margin_factor,
            percentual_utilizado=percentual,
        ).model_dump(),
        dry_run=payload.dry_run,
    )


@router.post("/actions/create-set", response_model=CreateSetResponse)
async def create_set(payload: CreateSetPayload, request: Request) -> CreateSetResponse:
    service = get_product_service(request)
    try:
        result = service.create_set_by_keys(payload.key_a, payload.key_b)
    except ProductSetCompositionConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if not result:
        raise HTTPException(status_code=400, detail="Nao foi possivel criar o conjunto selecionado.")
    service.record_undo_snapshot(clear_redo=True)
    publish_state_changed(["products", "totals"])
    return CreateSetResponse(**result)


@router.post("/actions/improve-descriptions")
async def improve_descriptions(payload: ImproveDescriptionPayload, request: Request) -> dict[str, object]:
    has_terms = bool([term for term in payload.remover_termos if str(term).strip()])
    if not payload.remover_numeros and not payload.remover_especiais and not has_terms:
        raise HTTPException(status_code=400, detail="Selecione ao menos uma opcao de limpeza.")
    service = get_product_service(request)
    _maybe_record_undo(service, dry_run=payload.dry_run)
    result = service.improve_descriptions(
        payload.remover_numeros,
        payload.remover_especiais,
        False,
        payload.remover_termos,
        payload.keys,
        persist=not payload.dry_run,
    )
    if result.get("modificados") and not payload.dry_run:
        publish_state_changed(["products"])
    return _with_dry_run_meta(ImproveDescriptionResponse(**result).model_dump(), dry_run=payload.dry_run)


@router.get("/actions/export-json")
async def export_json(request: Request) -> Response:
    items = get_product_service(request).list_products()
    content = "\n".join(json.dumps(item.to_dict(), ensure_ascii=False) for item in items)
    return Response(
        content=content,
        media_type="application/x-ndjson",
        headers={"Content-Disposition": 'attachment; filename="products_active.jsonl"'},
    )
