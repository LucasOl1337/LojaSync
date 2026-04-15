from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from app.application.products.service import ProductService
from app.domain.products.entities import Product
from app.infrastructure.persistence.sqlite.stores import (
    SQLiteBrandRepository,
    SQLiteMarginSettingsStore,
    SQLiteMetricsStore,
    SQLiteProductRepository,
)


class SQLitePersistenceTests(unittest.TestCase):
    def test_migrates_legacy_files_into_single_database(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            db_file = root / "lojasync.db"
            active_file = root / "products_active.jsonl"
            history_file = root / "products_history.jsonl"
            brands_file = root / "brands.json"
            margin_file = root / "margem.json"
            metrics_file = root / "metrics.json"

            active_product = Product.from_dict(
                {
                    "ordering_key": "prod-1",
                    "nome": "CAMISETA",
                    "codigo": "ABC123",
                    "codigo_original": "ABC123",
                    "quantidade": 2,
                    "preco": "19,90",
                    "preco_final": None,
                    "categoria": "Infantil",
                    "marca": "Marca X",
                    "timestamp": "2026-04-15T10:00:00",
                }
            )
            history_product = Product.from_dict(
                {
                    "ordering_key": "hist-1",
                    "nome": "BERMUDA",
                    "codigo": "XYZ999",
                    "codigo_original": "XYZ999",
                    "quantidade": 1,
                    "preco": "29,90",
                    "preco_final": "39,90",
                    "categoria": "Masculino",
                    "marca": "Marca Y",
                    "timestamp": "2026-04-14T09:00:00",
                }
            )
            active_file.write_text(json.dumps(active_product.to_dict(), ensure_ascii=False) + "\n", encoding="utf-8")
            history_file.write_text(json.dumps(history_product.to_dict(), ensure_ascii=False) + "\n", encoding="utf-8")
            brands_file.write_text(json.dumps(["Marca X", "Marca Y"], ensure_ascii=False), encoding="utf-8")
            margin_file.write_text(json.dumps({"margem": 1.35}, ensure_ascii=False), encoding="utf-8")
            metrics_file.write_text(
                json.dumps(
                    {
                        "tempo_economizado": 10,
                        "caracteres_digitados": 20,
                        "historico_quantidade": 3,
                        "historico_custo": 40.5,
                        "historico_venda": 60.5,
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            products = SQLiteProductRepository(db_file, active_file, history_file)
            brands = SQLiteBrandRepository(db_file, brands_file, ())
            margin = SQLiteMarginSettingsStore(db_file, margin_file, 1.0)
            metrics = SQLiteMetricsStore(db_file, metrics_file)

            self.assertTrue(db_file.exists())
            self.assertEqual([item.ordering_key() for item in products.list_active()], ["prod-1"])
            self.assertEqual([item.ordering_key() for item in products.list_history()], ["hist-1"])
            self.assertEqual(brands.list_brands(), ["Marca X", "Marca Y"])
            self.assertEqual(margin.load_margin(), 1.35)
            loaded_metrics = metrics.load_metrics()
            self.assertEqual(loaded_metrics.tempo_economizado, 10)
            self.assertEqual(loaded_metrics.historico_venda, 60.5)

    def test_reorder_by_keys_preserves_record_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            db_file = root / "lojasync.db"
            products_repo = SQLiteProductRepository(db_file)
            brands_repo = SQLiteBrandRepository(db_file, None, ())
            margin_store = SQLiteMarginSettingsStore(db_file, None, 1.0)
            metrics_store = SQLiteMetricsStore(db_file, None)
            service = ProductService(products_repo, brands_repo, margin_store, metrics_store)

            first = Product.from_dict(
                {
                    "ordering_key": "item-1",
                    "nome": "  CAMISETA TESTE  ",
                    "codigo": "  ABC123  ",
                    "codigo_original": "",
                    "quantidade": 1,
                    "preco": " 10,00 ",
                    "preco_final": None,
                    "categoria": "  Infantil ",
                    "marca": "  Marca X ",
                    "descricao_completa": "  CAMISETA TESTE COMPLETA  ",
                    "timestamp": "2026-04-15T10:00:00",
                }
            )
            second = Product.from_dict(
                {
                    "ordering_key": "item-2",
                    "nome": "  BERMUDA TESTE  ",
                    "codigo": "  XYZ999  ",
                    "codigo_original": "",
                    "quantidade": 2,
                    "preco": " 20,00 ",
                    "preco_final": None,
                    "categoria": "  Masculino ",
                    "marca": "  Marca Y ",
                    "descricao_completa": "  BERMUDA TESTE COMPLETA  ",
                    "timestamp": "2026-04-15T11:00:00",
                }
            )
            products_repo.replace_active([first, second])
            before = [item.to_dict() for item in products_repo.list_active()]

            total = service.reorder_by_keys(["item-2", "item-1"])
            after = [item.to_dict() for item in products_repo.list_active()]

            self.assertEqual(total, 2)
            self.assertEqual([item["ordering_key"] for item in after], ["item-2", "item-1"])
            self.assertEqual(before[0], after[1])
            self.assertEqual(before[1], after[0])
            self.assertIsNone(after[0]["preco_final"])
            self.assertEqual(after[1]["nome"], "  CAMISETA TESTE  ")

    def test_update_product_keeps_stable_ordering_key_when_code_changes(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            db_file = root / "lojasync.db"
            products_repo = SQLiteProductRepository(db_file)
            brands_repo = SQLiteBrandRepository(db_file, None, ())
            margin_store = SQLiteMarginSettingsStore(db_file, None, 1.0)
            metrics_store = SQLiteMetricsStore(db_file, None)
            service = ProductService(products_repo, brands_repo, margin_store, metrics_store)

            created = service.create_product(
                Product(
                    nome="Produto Teste",
                    codigo="COD-1",
                    codigo_original="COD-1",
                    quantidade=1,
                    preco="10,00",
                    categoria="",
                    marca="",
                )
            )
            original_key = created.ordering_key()

            updated = service.update_product(original_key, {"codigo": "COD-2"})

            self.assertIsNotNone(updated)
            current = products_repo.list_active()[0]
            self.assertEqual(current.codigo, "COD-2")
            self.assertEqual(current.ordering_key(), original_key)

    def test_create_many_keeps_distinct_rows_when_code_and_timestamp_repeat(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            db_file = root / "lojasync.db"
            products_repo = SQLiteProductRepository(db_file)
            brands_repo = SQLiteBrandRepository(db_file, None, ())
            margin_store = SQLiteMarginSettingsStore(db_file, None, 1.0)
            metrics_store = SQLiteMetricsStore(db_file, None)
            service = ProductService(products_repo, brands_repo, margin_store, metrics_store)

            payloads = [
                {
                    "nome": "CALCA JOGGER",
                    "codigo": "1000108790",
                    "codigo_original": "1000108790",
                    "quantidade": 5,
                    "preco": "27,13",
                    "preco_final": None,
                    "categoria": "",
                    "marca": "",
                    "grades": [{"tamanho": "02", "quantidade": 2}, {"tamanho": "03", "quantidade": 3}],
                    "timestamp": "2026-04-15T15:43:08.240369",
                },
                {
                    "nome": "CALCA JOGGER",
                    "codigo": "1000108790",
                    "codigo_original": "1000108790",
                    "quantidade": 8,
                    "preco": "33,50",
                    "preco_final": None,
                    "categoria": "",
                    "marca": "",
                    "grades": [{"tamanho": "06", "quantidade": 4}, {"tamanho": "10", "quantidade": 4}],
                    "timestamp": "2026-04-15T15:43:08.240369",
                },
                {
                    "nome": "CALCA JOGGER",
                    "codigo": "1000108790",
                    "codigo_original": "1000108790",
                    "quantidade": 12,
                    "preco": "41,71",
                    "preco_final": None,
                    "categoria": "",
                    "marca": "",
                    "grades": [{"tamanho": "14", "quantidade": 4}, {"tamanho": "16", "quantidade": 4}, {"tamanho": "18", "quantidade": 4}],
                    "timestamp": "2026-04-15T15:43:08.240369",
                },
            ]

            service.create_many([Product.from_dict(payload) for payload in payloads])

            current = products_repo.list_active()
            self.assertEqual(len(current), 3)
            self.assertEqual([item.preco for item in current], ["27,13", "33,50", "41,71"])
            self.assertEqual(len({item.ordering_key() for item in current}), 3)


if __name__ == "__main__":
    unittest.main()
