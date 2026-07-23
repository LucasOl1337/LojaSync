from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, File, HTTPException, Request, UploadFile

from app.application.imports.job_validation import build_local_import_text, build_local_parser_products
from app.application.imports.local_experiment import parse_local_romaneio_experiment
from app.application.imports.parsing import products_to_text, save_romaneio_text
from app.interfaces.api.http.route_models import ImportRomaneioResultResponse
from app.shared.ui_events import publish_state_changed

router = APIRouter()


@router.post("/actions/import-romaneio-local-experiment", response_model=ImportRomaneioResultResponse)
async def import_romaneio_local_experiment(
    request: Request,
    file: UploadFile = File(...),
) -> ImportRomaneioResultResponse:
    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Arquivo vazio ou invalido")
    payload = parse_local_romaneio_experiment(
        contents=contents,
        filename=file.filename or "romaneio",
        content_type=file.content_type,
    )
    items = build_local_parser_products(
        payload,
        import_source_name=file.filename or "romaneio",
        import_batch_id=uuid4().hex,
        source_type="romaneio_local",
        pending_grade_import=False,
    )
    if not items:
        raise HTTPException(status_code=422, detail="Local parsing did not find any importable items.")

    container = request.app.state.container
    created = container.product_service.create_many(items)
    local_file = save_romaneio_text(container.paths.data_dir, build_local_import_text(payload))
    publish_state_changed(["products", "totals", "brands"])
    metrics = dict(payload.get("metrics") or {})
    metrics["selected_source"] = "local_parsing_import"
    metrics["imported_items"] = len(created)
    for key in (
        "document_total_products",
        "document_total_note",
        "extracted_total_products",
        "products_value_matches_document",
        "quantity_matches_remessa",
        "total_quantity",
        "remessa_quantity",
    ):
        if key in payload and payload.get(key) is not None:
            metrics[key] = payload.get(key)

    # Persist a re-parseable products dump so "Enviar ao catálogo" can reapply without re-scanning.
    reapply_content = products_to_text(created) if created else build_local_import_text(payload)
    return ImportRomaneioResultResponse(
        status="ok",
        saved_file=None,
        local_file=str(local_file),
        content=reapply_content,
        warnings=list(payload.get("warnings") or []),
        total_itens=len(created),
        grades_disponiveis=False,
        total_grades_disponiveis=0,
        imported_keys=[item.ordering_key() for item in created],
        import_batch_id=str(created[0].import_batch_id or "") if created else None,
        metrics=metrics,
    )
