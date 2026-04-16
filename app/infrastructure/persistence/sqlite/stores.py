from __future__ import annotations

from contextlib import contextmanager
import json
import sqlite3
from pathlib import Path

from app.domain.brands.repository import BrandRepository
from app.domain.metrics.entities import Metrics
from app.domain.products.entities import Product
from app.domain.products.repository import ProductRepository


@contextmanager
def _connect(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(path), timeout=30.0)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA journal_mode = WAL")
    try:
        yield connection
    finally:
        connection.close()


def _bootstrap_database(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS active_products (
            ordering_key TEXT PRIMARY KEY,
            position INTEGER NOT NULL,
            timestamp TEXT NOT NULL,
            nome TEXT NOT NULL,
            codigo TEXT NOT NULL,
            quantidade INTEGER NOT NULL,
            preco TEXT NOT NULL,
            categoria TEXT NOT NULL,
            marca TEXT NOT NULL,
            preco_final TEXT,
            descricao_completa TEXT,
            codigo_original TEXT,
            grades_json TEXT,
            cores_json TEXT,
            source_type TEXT,
            import_batch_id TEXT,
            import_source_name TEXT,
            pending_grade_import INTEGER NOT NULL DEFAULT 0
        );

        CREATE INDEX IF NOT EXISTS idx_active_products_position
        ON active_products(position, timestamp, ordering_key);

        CREATE TABLE IF NOT EXISTS history_products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ordering_key TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            nome TEXT NOT NULL,
            codigo TEXT NOT NULL,
            quantidade INTEGER NOT NULL,
            preco TEXT NOT NULL,
            categoria TEXT NOT NULL,
            marca TEXT NOT NULL,
            preco_final TEXT,
            descricao_completa TEXT,
            codigo_original TEXT,
            grades_json TEXT,
            cores_json TEXT,
            source_type TEXT,
            import_batch_id TEXT,
            import_source_name TEXT,
            pending_grade_import INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS brands (
            name TEXT PRIMARY KEY,
            position INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS app_settings (
            key TEXT PRIMARY KEY,
            value_json TEXT NOT NULL
        );
        """
    )
    _ensure_column(connection, "active_products", "source_type", "TEXT")
    _ensure_column(connection, "active_products", "import_batch_id", "TEXT")
    _ensure_column(connection, "active_products", "import_source_name", "TEXT")
    _ensure_column(connection, "active_products", "pending_grade_import", "INTEGER NOT NULL DEFAULT 0")
    _ensure_column(connection, "history_products", "source_type", "TEXT")
    _ensure_column(connection, "history_products", "import_batch_id", "TEXT")
    _ensure_column(connection, "history_products", "import_source_name", "TEXT")
    _ensure_column(connection, "history_products", "pending_grade_import", "INTEGER NOT NULL DEFAULT 0")
    connection.commit()


def _ensure_column(connection: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    columns = {
        str(row["name"])
        for row in connection.execute(f"PRAGMA table_info({table})").fetchall()
    }
    if column in columns:
        return
    connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def _load_jsonl_products(path: Path) -> list[Product]:
    products: list[Product] = []
    if not path.exists():
        return products
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            payload = line.strip()
            if not payload:
                continue
            try:
                products.append(Product.from_dict(json.loads(payload)))
            except Exception:
                continue
    return products


def _serialize_items(value: object) -> str | None:
    if not value:
        return None
    try:
        return json.dumps(value, ensure_ascii=False)
    except Exception:
        return None


def _deserialize_items(raw: str | None) -> object:
    if not raw:
        return None
    try:
        return json.loads(raw)
    except Exception:
        return None


def _product_row_payload(row: sqlite3.Row) -> dict[str, object]:
    return {
        "nome": row["nome"],
        "codigo": row["codigo"],
        "quantidade": row["quantidade"],
        "preco": row["preco"],
        "categoria": row["categoria"],
        "marca": row["marca"],
        "preco_final": row["preco_final"],
        "descricao_completa": row["descricao_completa"],
        "codigo_original": row["codigo_original"],
        "ordering_key": row["ordering_key"],
        "grades": _deserialize_items(row["grades_json"]),
        "cores": _deserialize_items(row["cores_json"]),
        "source_type": row["source_type"],
        "import_batch_id": row["import_batch_id"],
        "import_source_name": row["import_source_name"],
        "pending_grade_import": bool(row["pending_grade_import"]),
        "timestamp": row["timestamp"],
    }


def _product_to_record(product: Product) -> tuple[object, ...]:
    payload = product.to_dict()
    ordering_key = str(payload.get("ordering_key") or product.ordering_key()).strip()
    return (
        ordering_key,
        payload.get("timestamp") or product.timestamp.isoformat(),
        product.nome,
        product.codigo,
        int(product.quantidade or 0),
        product.preco,
        product.categoria,
        product.marca,
        product.preco_final,
        product.descricao_completa,
        product.codigo_original,
        _serialize_items(payload.get("grades")),
        _serialize_items(payload.get("cores")),
        product.source_type,
        product.import_batch_id,
        product.import_source_name,
        int(bool(product.pending_grade_import)),
    )


class SQLiteProductRepository(ProductRepository):
    def __init__(self, db_file: Path, legacy_active_file: Path | None = None, legacy_history_file: Path | None = None) -> None:
        self._db_file = db_file
        self._legacy_active_file = legacy_active_file
        self._legacy_history_file = legacy_history_file
        with _connect(self._db_file) as connection:
            _bootstrap_database(connection)
            self._migrate_legacy_data(connection)

    def list_active(self) -> list[Product]:
        with _connect(self._db_file) as connection:
            rows = connection.execute(
                """
                SELECT ordering_key, timestamp, nome, codigo, quantidade, preco, categoria, marca,
                       preco_final, descricao_completa, codigo_original, grades_json, cores_json,
                       source_type, import_batch_id, import_source_name, pending_grade_import
                FROM active_products
                ORDER BY position ASC, timestamp ASC, ordering_key ASC
                """
            ).fetchall()
        return [Product.from_dict(_product_row_payload(row)) for row in rows]

    def list_history(self) -> list[Product]:
        with _connect(self._db_file) as connection:
            rows = connection.execute(
                """
                SELECT ordering_key, timestamp, nome, codigo, quantidade, preco, categoria, marca,
                       preco_final, descricao_completa, codigo_original, grades_json, cores_json,
                       source_type, import_batch_id, import_source_name, pending_grade_import
                FROM history_products
                ORDER BY id ASC
                """
            ).fetchall()
        return [Product.from_dict(_product_row_payload(row)) for row in rows]

    def replace_active(self, products: list[Product]) -> None:
        with _connect(self._db_file) as connection:
            self._replace_active(connection, products)

    def append_active(self, product: Product) -> None:
        with _connect(self._db_file) as connection:
            next_position = int(
                connection.execute("SELECT COALESCE(MAX(position), -1) + 1 FROM active_products").fetchone()[0]
            )
            record = _product_to_record(product)
            connection.execute(
                """
                INSERT OR REPLACE INTO active_products (
                    ordering_key, position, timestamp, nome, codigo, quantidade, preco, categoria, marca,
                    preco_final, descricao_completa, codigo_original, grades_json, cores_json,
                    source_type, import_batch_id, import_source_name, pending_grade_import
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (record[0], next_position, *record[1:]),
            )
            connection.commit()

    def append_history(self, products: list[Product]) -> None:
        if not products:
            return
        with _connect(self._db_file) as connection:
            connection.executemany(
                """
                INSERT INTO history_products (
                    ordering_key, timestamp, nome, codigo, quantidade, preco, categoria, marca,
                    preco_final, descricao_completa, codigo_original, grades_json, cores_json,
                    source_type, import_batch_id, import_source_name, pending_grade_import
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [_product_to_record(product) for product in products],
            )
            connection.commit()

    def update(self, ordering_key: str, changes: dict[str, object]) -> Product | None:
        products = self.list_active()
        updated: Product | None = None
        for product in products:
            if product.ordering_key() != ordering_key:
                continue
            for field_name, value in changes.items():
                if hasattr(product, field_name):
                    setattr(product, field_name, value)
            updated = product
            break
        if updated is None:
            return None
        self.replace_active(products)
        return updated

    def reorder_active(self, ordering_keys: list[str]) -> int:
        if not ordering_keys:
            with _connect(self._db_file) as connection:
                return int(connection.execute("SELECT COUNT(*) FROM active_products").fetchone()[0])
        with _connect(self._db_file) as connection:
            rows = connection.execute("SELECT ordering_key FROM active_products ORDER BY position ASC, ordering_key ASC").fetchall()
            existing = [str(row["ordering_key"]) for row in rows]
            if not existing:
                return 0
            ordered_keys: list[str] = []
            seen: set[str] = set()
            existing_set = set(existing)
            for key in ordering_keys:
                normalized = str(key or "").strip()
                if not normalized or normalized in seen or normalized not in existing_set:
                    continue
                ordered_keys.append(normalized)
                seen.add(normalized)
            for key in existing:
                if key not in seen:
                    ordered_keys.append(key)
            connection.executemany(
                "UPDATE active_products SET position = ? WHERE ordering_key = ?",
                [(index, key) for index, key in enumerate(ordered_keys)],
            )
            connection.commit()
            return len(ordered_keys)

    def export_active_jsonl(self) -> str:
        return "\n".join(json.dumps(product.to_dict(), ensure_ascii=False) for product in self.list_active())

    def _replace_active(self, connection: sqlite3.Connection, products: list[Product]) -> None:
        connection.execute("DELETE FROM active_products")
        connection.executemany(
            """
            INSERT INTO active_products (
                ordering_key, position, timestamp, nome, codigo, quantidade, preco, categoria, marca,
                preco_final, descricao_completa, codigo_original, grades_json, cores_json,
                source_type, import_batch_id, import_source_name, pending_grade_import
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [(record[0], index, *record[1:]) for index, record in enumerate(_product_to_record(product) for product in products)],
        )
        connection.commit()

    def _migrate_legacy_data(self, connection: sqlite3.Connection) -> None:
        active_count = int(connection.execute("SELECT COUNT(*) FROM active_products").fetchone()[0])
        if active_count == 0 and self._legacy_active_file is not None:
            legacy_active = _load_jsonl_products(self._legacy_active_file)
            if legacy_active:
                self._replace_active(connection, legacy_active)

        history_count = int(connection.execute("SELECT COUNT(*) FROM history_products").fetchone()[0])
        if history_count == 0 and self._legacy_history_file is not None:
            legacy_history = _load_jsonl_products(self._legacy_history_file)
            if legacy_history:
                connection.executemany(
                    """
                    INSERT INTO history_products (
                        ordering_key, timestamp, nome, codigo, quantidade, preco, categoria, marca,
                        preco_final, descricao_completa, codigo_original, grades_json, cores_json,
                        source_type, import_batch_id, import_source_name, pending_grade_import
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [_product_to_record(product) for product in legacy_history],
                )
                connection.commit()


class SQLiteBrandRepository(BrandRepository):
    def __init__(self, db_file: Path, legacy_brands_file: Path | None, default_brands: tuple[str, ...]) -> None:
        self._db_file = db_file
        self._legacy_brands_file = legacy_brands_file
        self._default_brands = list(default_brands)
        with _connect(self._db_file) as connection:
            _bootstrap_database(connection)
            self._migrate_legacy_data(connection)

    def list_brands(self) -> list[str]:
        with _connect(self._db_file) as connection:
            rows = connection.execute("SELECT name FROM brands ORDER BY position ASC, name ASC").fetchall()
        return [str(row["name"]).strip() for row in rows if str(row["name"]).strip()]

    def save_brands(self, brands: list[str]) -> None:
        cleaned = [str(item).strip() for item in brands if str(item).strip()]
        with _connect(self._db_file) as connection:
            connection.execute("DELETE FROM brands")
            connection.executemany(
                "INSERT INTO brands (name, position) VALUES (?, ?)",
                [(name, index) for index, name in enumerate(cleaned)],
            )
            connection.commit()

    def _migrate_legacy_data(self, connection: sqlite3.Connection) -> None:
        count = int(connection.execute("SELECT COUNT(*) FROM brands").fetchone()[0])
        if count > 0:
            return
        brands: list[str] = []
        if self._legacy_brands_file is not None and self._legacy_brands_file.exists():
            try:
                payload = json.loads(self._legacy_brands_file.read_text(encoding="utf-8"))
                if isinstance(payload, list):
                    brands = [str(item).strip() for item in payload if str(item).strip()]
            except Exception:
                brands = []
        if not brands:
            brands = list(self._default_brands)
        connection.executemany(
            "INSERT INTO brands (name, position) VALUES (?, ?)",
            [(name, index) for index, name in enumerate(brands)],
        )
        connection.commit()


class SQLiteMarginSettingsStore:
    def __init__(self, db_file: Path, legacy_margin_file: Path | None, default_margin: float) -> None:
        self._db_file = db_file
        self._legacy_margin_file = legacy_margin_file
        self._default_margin = default_margin
        with _connect(self._db_file) as connection:
            _bootstrap_database(connection)
            self._migrate_legacy_data(connection)

    def load_margin(self) -> float:
        with _connect(self._db_file) as connection:
            row = connection.execute("SELECT value_json FROM app_settings WHERE key = 'margin'").fetchone()
        if row is None:
            return self._default_margin
        try:
            payload = json.loads(str(row["value_json"]))
            margin = float(payload.get("margem", self._default_margin))
            return margin if margin > 0 else self._default_margin
        except Exception:
            return self._default_margin

    def save_margin(self, margin: float) -> None:
        payload = json.dumps({"margem": margin}, ensure_ascii=False)
        with _connect(self._db_file) as connection:
            connection.execute(
                """
                INSERT INTO app_settings (key, value_json) VALUES ('margin', ?)
                ON CONFLICT(key) DO UPDATE SET value_json = excluded.value_json
                """,
                (payload,),
            )
            connection.commit()

    def _migrate_legacy_data(self, connection: sqlite3.Connection) -> None:
        existing = connection.execute("SELECT 1 FROM app_settings WHERE key = 'margin'").fetchone()
        if existing is not None:
            return
        margin = self._default_margin
        if self._legacy_margin_file is not None and self._legacy_margin_file.exists():
            try:
                payload = json.loads(self._legacy_margin_file.read_text(encoding="utf-8"))
                margin = float(payload.get("margem", self._default_margin))
                if margin <= 0:
                    margin = self._default_margin
            except Exception:
                margin = self._default_margin
        connection.execute(
            "INSERT INTO app_settings (key, value_json) VALUES ('margin', ?)",
            (json.dumps({"margem": margin}, ensure_ascii=False),),
        )
        connection.commit()


class SQLiteMetricsStore:
    def __init__(self, db_file: Path, legacy_metrics_file: Path | None) -> None:
        self._db_file = db_file
        self._legacy_metrics_file = legacy_metrics_file
        with _connect(self._db_file) as connection:
            _bootstrap_database(connection)
            self._migrate_legacy_data(connection)

    def load_metrics(self) -> Metrics:
        with _connect(self._db_file) as connection:
            row = connection.execute("SELECT value_json FROM app_settings WHERE key = 'metrics'").fetchone()
        if row is None:
            return Metrics()
        try:
            payload = json.loads(str(row["value_json"]))
            return Metrics(
                tempo_economizado=int(payload.get("tempo_economizado", 0) or 0),
                caracteres_digitados=int(payload.get("caracteres_digitados", 0) or 0),
                historico_quantidade=int(payload.get("historico_quantidade", 0) or 0),
                historico_custo=float(payload.get("historico_custo", 0.0) or 0.0),
                historico_venda=float(payload.get("historico_venda", 0.0) or 0.0),
            )
        except Exception:
            return Metrics()

    def save_metrics(self, metrics: Metrics) -> None:
        payload = json.dumps(
            {
                "tempo_economizado": metrics.tempo_economizado,
                "caracteres_digitados": metrics.caracteres_digitados,
                "historico_quantidade": metrics.historico_quantidade,
                "historico_custo": metrics.historico_custo,
                "historico_venda": metrics.historico_venda,
            },
            ensure_ascii=False,
        )
        with _connect(self._db_file) as connection:
            connection.execute(
                """
                INSERT INTO app_settings (key, value_json) VALUES ('metrics', ?)
                ON CONFLICT(key) DO UPDATE SET value_json = excluded.value_json
                """,
                (payload,),
            )
            connection.commit()

    def _migrate_legacy_data(self, connection: sqlite3.Connection) -> None:
        existing = connection.execute("SELECT 1 FROM app_settings WHERE key = 'metrics'").fetchone()
        if existing is not None:
            return
        metrics = Metrics()
        if self._legacy_metrics_file is not None and self._legacy_metrics_file.exists():
            try:
                payload = json.loads(self._legacy_metrics_file.read_text(encoding="utf-8"))
                metrics = Metrics(
                    tempo_economizado=int(payload.get("tempo_economizado", 0) or 0),
                    caracteres_digitados=int(payload.get("caracteres_digitados", 0) or 0),
                    historico_quantidade=int(payload.get("historico_quantidade", 0) or 0),
                    historico_custo=float(payload.get("historico_custo", 0.0) or 0.0),
                    historico_venda=float(payload.get("historico_venda", 0.0) or 0.0),
                )
            except Exception:
                metrics = Metrics()
        connection.execute(
            "INSERT INTO app_settings (key, value_json) VALUES ('metrics', ?)",
            (
                json.dumps(
                    {
                        "tempo_economizado": metrics.tempo_economizado,
                        "caracteres_digitados": metrics.caracteres_digitados,
                        "historico_quantidade": metrics.historico_quantidade,
                        "historico_custo": metrics.historico_custo,
                        "historico_venda": metrics.historico_venda,
                    },
                    ensure_ascii=False,
                ),
            ),
        )
        connection.commit()
