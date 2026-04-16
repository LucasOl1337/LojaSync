from __future__ import annotations

from dataclasses import dataclass

from app.application.automation.service import AutomationService
from app.application.products.service import ProductService
from app.domain.auth import AuthConnector
from app.infrastructure.auth.http_connector import HttpAuthConnector
from app.infrastructure.persistence.sqlite import (
    SQLiteBrandRepository,
    SQLiteMarginSettingsStore,
    SQLiteMetricsStore,
    SQLiteProductRepository,
)
from app.shared.config.settings import AppSettings
from app.shared.paths.runtime_paths import build_runtime_paths


@dataclass(frozen=True)
class AppContainer:
    settings: AppSettings
    paths: object
    auth_connector: AuthConnector
    product_service: ProductService
    automation_service: AutomationService

    def __getitem__(self, key: str) -> object:
        return getattr(self, key)


def build_container() -> AppContainer:
    settings = AppSettings()
    paths = build_runtime_paths()
    auth_connector = HttpAuthConnector(
        base_url=f"http://{settings.auth_host}:{settings.auth_port}",
        cookie_name=settings.auth_cookie_name,
        enabled=settings.auth_enabled,
    )
    products = SQLiteProductRepository(paths.database_file, paths.products_active_file, paths.products_history_file)
    brands = SQLiteBrandRepository(paths.database_file, paths.brands_file, settings.default_brands)
    margin_store = SQLiteMarginSettingsStore(paths.database_file, paths.margin_file, settings.default_margin)
    metrics_store = SQLiteMetricsStore(paths.database_file, paths.metrics_file)
    product_service = ProductService(products, brands, margin_store, metrics_store)
    automation_service = AutomationService(product_service, paths.data_dir)
    return AppContainer(
        settings=settings,
        paths=paths,
        auth_connector=auth_connector,
        product_service=product_service,
        automation_service=automation_service,
    )
