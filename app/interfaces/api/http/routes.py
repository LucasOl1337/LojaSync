from __future__ import annotations

from fastapi import APIRouter

from app.interfaces.api.http.route_automation import router as automation_router
from app.interfaces.api.http.route_core import router as core_router
from app.interfaces.api.http.route_imports import router as imports_router
from app.interfaces.api.http.route_products import router as products_router

router = APIRouter()
router.include_router(core_router)
router.include_router(products_router)
router.include_router(automation_router)
router.include_router(imports_router)
