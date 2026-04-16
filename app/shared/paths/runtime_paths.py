from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RuntimePaths:
    root_dir: Path
    app_dir: Path
    data_dir: Path
    web_static_dir: Path
    web_ts_dist_dir: Path

    @property
    def products_active_file(self) -> Path:
        return self.data_dir / "products_active.jsonl"

    @property
    def products_history_file(self) -> Path:
        return self.data_dir / "products_history.jsonl"

    @property
    def database_file(self) -> Path:
        return self.data_dir / "lojasync.db"

    @property
    def brands_file(self) -> Path:
        return self.data_dir / "brands.json"

    @property
    def metrics_file(self) -> Path:
        return self.data_dir / "metrics.json"

    @property
    def margin_file(self) -> Path:
        return self.data_dir / "margem.json"

    @property
    def auth_file(self) -> Path:
        return self.data_dir / "auth.json"


def build_runtime_paths() -> RuntimePaths:
    root_dir = Path(__file__).resolve().parents[3]
    app_dir = root_dir / "app"
    data_dir = root_dir / "data"
    web_static_dir = app_dir / "interfaces" / "webapp" / "static"
    web_ts_dist_dir = root_dir / "frontend-ts" / "dist"
    data_dir.mkdir(parents=True, exist_ok=True)
    web_static_dir.mkdir(parents=True, exist_ok=True)
    return RuntimePaths(
        root_dir=root_dir,
        app_dir=app_dir,
        data_dir=data_dir,
        web_static_dir=web_static_dir,
        web_ts_dist_dir=web_ts_dist_dir,
    )
