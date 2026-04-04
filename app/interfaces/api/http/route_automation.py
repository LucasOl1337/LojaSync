from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request

from app.interfaces.api.http.route_models import (
    GradeConfigPayload,
    GradeRunPayload,
    GradesBatchPayload,
    TargetCapturePayload,
    TargetCaptureResponse,
    TargetsPayload,
    TargetsResponse,
)
from app.interfaces.api.http.route_shared import as_target_point, build_targets_response, get_automation_service
from app.shared.ui_events import publish_state_changed

router = APIRouter()


@router.get("/automation/targets", response_model=TargetsResponse)
async def get_targets(request: Request) -> TargetsResponse:
    return build_targets_response(get_automation_service(request).load_targets())


@router.post("/automation/targets", response_model=TargetsResponse)
async def set_targets(payload: TargetsPayload, request: Request) -> TargetsResponse:
    data = payload.model_dump(exclude_none=True)
    saved = get_automation_service(request).save_targets(data)
    publish_state_changed(["automation"])
    return build_targets_response(saved)


@router.post("/automation/targets/capture", response_model=TargetCaptureResponse)
async def capture_target(payload: TargetCapturePayload, request: Request) -> TargetCaptureResponse:
    try:
        captured = get_automation_service(request).capture_target(payload.target)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    point = as_target_point(captured.get("point"))
    if point is None:
        raise HTTPException(status_code=500, detail="Falha ao capturar coordenadas")
    return TargetCaptureResponse(target=payload.target, point=point)


@router.get("/automation/status")
async def automation_status(request: Request) -> dict[str, str | None]:
    return get_automation_service(request).status()


@router.post("/automation/execute")
async def automation_execute(request: Request) -> dict[str, str]:
    try:
        result = get_automation_service(request).execute()
        publish_state_changed(["automation"])
        return result
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/automation/execute-complete")
async def automation_execute_complete(request: Request) -> dict[str, str]:
    try:
        result = get_automation_service(request).execute_complete()
        publish_state_changed(["automation"])
        return result
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/automation/cancel")
async def automation_cancel(request: Request) -> dict[str, str]:
    result = get_automation_service(request).cancel()
    publish_state_changed(["automation"])
    return result


@router.get("/automation/agents")
async def automation_agents(request: Request) -> dict[str, list[dict[str, Any]]]:
    return get_automation_service(request).agents()


@router.get("/automation/byteempresa/context")
async def byteempresa_context(request: Request) -> dict[str, Any]:
    try:
        return get_automation_service(request).byte_empresa_context()
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/automation/byteempresa/prepare")
async def byteempresa_prepare(request: Request) -> dict[str, Any]:
    try:
        return get_automation_service(request).byte_empresa_prepare()
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/automation/grades/config")
async def grades_config_get(request: Request) -> dict[str, Any]:
    return {"config": get_automation_service(request).get_gradebot_config()}


@router.post("/automation/grades/config")
async def grades_config_set(payload: GradeConfigPayload, request: Request) -> dict[str, Any]:
    config = get_automation_service(request).set_gradebot_config(payload.model_dump(exclude_none=True))
    publish_state_changed(["automation"])
    return {"config": config}


@router.post("/automation/grades/run")
async def grades_run(payload: GradeRunPayload, request: Request) -> dict[str, str]:
    try:
        result = get_automation_service(request).run_gradebot(
            grades=payload.grades,
            grades_json=payload.grades_json,
            model_index=payload.model_index,
            pause=payload.pause,
            speed=payload.speed,
        )
        publish_state_changed(["automation"])
        return result
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/automation/grades/batch")
async def grades_batch(payload: GradesBatchPayload, request: Request) -> dict[str, Any]:
    tasks = [task.model_dump(exclude_none=True) for task in payload.tasks]
    try:
        result = get_automation_service(request).run_gradebot_batch(
            tasks=tasks,
            pause=payload.pause,
            speed=payload.speed,
        )
        publish_state_changed(["automation"])
        return result
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/automation/grades/execute-products")
async def grades_execute_products(request: Request) -> dict[str, Any]:
    try:
        result = get_automation_service(request).execute_grades_from_products()
        publish_state_changed(["automation"])
        return result
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/automation/grades/stop")
async def grades_stop(request: Request) -> dict[str, str]:
    result = get_automation_service(request).stop_gradebot()
    publish_state_changed(["automation"])
    return result
