from __future__ import annotations

from app.application.automation.service import AutomationService
from app.application.products.service import ProductService
from app.infrastructure.persistence.files.settings_files import (
    JsonBrandRepository,
    MarginSettingsStore,
    MetricsStore,
)
from app.infrastructure.persistence.jsonl.stores import JsonlProductRepository
from app.shared.config.settings import AppSettings
from app.shared.paths.runtime_paths import build_runtime_paths


def build_container() -> dict[str, object]:
    settings = AppSettings()
    paths = build_runtime_paths()
    products = JsonlProductRepository(paths.products_active_file, paths.products_history_file)
    brands = JsonBrandRepository(paths.brands_file, settings.default_brands)
    margin_store = MarginSettingsStore(paths.margin_file, settings.default_margin)
    metrics_store = MetricsStore(paths.metrics_file)
    product_service = ProductService(products, brands, margin_store, metrics_store)
    automation_service = AutomationService(product_service, paths.data_dir)
    return {
        "settings": settings,
        "paths": paths,
        "product_service": product_service,
        "automation_service": automation_service,
    }
