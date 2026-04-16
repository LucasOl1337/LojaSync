from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, File, HTTPException, Request, UploadFile

from app.application.imports.local_experiment import parse_local_romaneio_experiment
from app.application.imports.parsing import save_romaneio_text
from app.domain.products.entities import Product
from app.interfaces.api.http.route_models import ImportRomaneioResultResponse
from app.shared.ui_events import publish_state_changed

router = APIRouter()


def _build_local_import_products(payload: dict[str, object], *, filename: str, import_batch_id: str) -> list[Product]:
    products: list[Product] = []
    for raw in payload.get("items") or []:
        if not isinstance(raw, dict):
            continue
        grades = raw.get("grades") if isinstance(raw.get("grades"), list) else None
        cor = str(raw.get("cor") or "").strip()
        quantidade = int(raw.get("quantidade") or 0)
        products.append(
            Product(
                nome=str(raw.get("nome") or "").strip(),
                codigo=str(raw.get("codigo") or "").strip(),
                codigo_original=str(raw.get("codigo") or "").strip(),
                quantidade=max(quantidade, 0),
                preco=str(raw.get("preco") or "").strip(),
                categoria="",
                marca="",
                descricao_completa=str(raw.get("descricao_completa") or raw.get("nome") or "").strip() or None,
                grades=grades,
                cores=[{"cor": cor, "quantidade": quantidade}] if cor and quantidade > 0 else None,
                source_type="romaneio_local",
                import_batch_id=import_batch_id,
                import_source_name=filename.strip() or "romaneio",
                pending_grade_import=False,
            )
        )
    return products


def _build_local_import_text(payload: dict[str, object]) -> str:
    items = payload.get("items") or []
    if not isinstance(items, list) or not items:
        return ""
    lines = ["codigo|nome|cor|quantidade|preco|grades"]
    for item in items:
        if not isinstance(item, dict):
            continue
        grades = item.get("grades") if isinstance(item.get("grades"), list) else []
        grades_text = ",".join(
            f"{str(grade.get('tamanho') or '').strip()}:{int(grade.get('quantidade') or 0)}"
            for grade in grades
            if isinstance(grade, dict)
        )
        lines.append(
            "|".join(
                [
                    str(item.get("codigo") or "").strip(),
                    str(item.get("nome") or "").strip(),
                    str(item.get("cor") or "").strip(),
                    str(int(item.get("quantidade") or 0)),
                    str(item.get("preco") or "").strip(),
                    grades_text,
                ]
            )
        )
    return "\n".join(lines)


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
    items = _build_local_import_products(
        payload,
        filename=file.filename or "romaneio",
        import_batch_id=uuid4().hex,
    )
    if not items:
        raise HTTPException(status_code=422, detail="Local parsing did not find any importable items.")

    container = request.app.state.container
    created = container.product_service.create_many(items)
    local_file = save_romaneio_text(container.paths.data_dir, _build_local_import_text(payload))
    publish_state_changed(["products", "totals", "brands"])
    metrics = dict(payload.get("metrics") or {})
    metrics["selected_source"] = "local_parsing_import"
    metrics["imported_items"] = len(created)

    return ImportRomaneioResultResponse(
        status="ok",
        saved_file=None,
        local_file=str(local_file),
        content=None,
        warnings=list(payload.get("warnings") or []),
        total_itens=len(created),
        grades_disponiveis=False,
        total_grades_disponiveis=0,
        imported_keys=[item.ordering_key() for item in created],
        import_batch_id=str(created[0].import_batch_id or "") if created else None,
        metrics=metrics,
    )
