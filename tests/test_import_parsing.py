from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.application.imports.parsing import (
    analyze_parsed_document,
    extract_structured_invoice_row_lines,
    filter_suspect_records,
    parse_candidate_content,
    split_structured_invoice_chunks,
    split_text_chunks,
)
from app.application.products.service import ProductService
from app.domain.metrics.entities import Metrics
from app.domain.products.entities import Product
from app.interfaces.api.http.jobs.runtime import run_import_job
from app.interfaces.api.http.jobs.store import create_import_job, get_import_job, get_import_result, remove_import_job


class _DummyRepo:
    def __init__(self, items: list[Product] | None = None) -> None:
        self.items = list(items or [])

    def list_active(self) -> list[Product]:
        return [Product.from_dict(item.to_dict()) for item in self.items]

    def list_history(self) -> list[Product]:
        return []

    def append_active(self, product: Product) -> None:
        self.items.append(Product.from_dict(product.to_dict()))

    def append_history(self, products: list[Product]) -> None:
        return None

    def replace_active(self, products: list[Product]) -> None:
        self.items = [Product.from_dict(item.to_dict()) for item in products]


class _DummyBrands:
    def list_brands(self) -> list[str]:
        return []

    def save_brands(self, brands: list[str]) -> None:
        return None


class _DummyMarginStore:
    def load_margin(self) -> float:
        return 1.0

    def save_margin(self, margin: float) -> None:
        return None


class _DummyMetricsStore:
    def load_metrics(self) -> Metrics:
        return Metrics()

    def save_metrics(self, metrics: Metrics) -> None:
        return None


class _RecordingImportService:
    def __init__(self) -> None:
        self.created: list[Product] = []

    def compact_import_batch(self, products: list[Product]) -> tuple[list[Product], dict[str, int]]:
        return products, {
            "originais": len(products),
            "resultantes": len(products),
            "removidos": 0,
            "atualizados_grades": 0,
        }

    def create_many(self, products: list[Product]) -> list[Product]:
        self.created = list(products)
        return list(products)


class _FakeResponse:
    def __init__(self, payload: object) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> object:
        return self._payload


class _FakeHttpxClient:
    def __init__(self, upload_payload: dict[str, object]) -> None:
        self.upload_payload = upload_payload
        self.upload_calls = 0

    def __enter__(self) -> "_FakeHttpxClient":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def post(self, url: str, **_: object) -> _FakeResponse:
        if url.endswith("/api/upload"):
            self.upload_calls += 1
            return _FakeResponse(self.upload_payload)
        raise AssertionError(f"unexpected direct post to {url}")


def _sample_invoice_rows() -> str:
    return "\n".join(
        [
            "1000108790 CALCA JOGGER BASICO(A) Cor 00004 Tam 2 6104.62.00 000 6101 PEC 1,000 27,1300 27,13 27,13 3,26 0,00 12,00 0,00",
            "1000108790 CALCA JOGGER BASICO(A) Cor 00004 Tam 3 6104.62.00 000 6101 PEC 1,000 27,1300 27,13 27,13 3,26 0,00 12,00 0,00",
            "1000108790 CALCA JOGGER BASICO(A) Cor 00004 Tam 6 6104.62.00 000 6101 PEC 2,000 33,4950 66,99 66,99 8,04 0,00 12,00 0,00",
            "1000108790 CALCA JOGGER BASICO(A) Cor 00004 Tam 8 6104.62.00 000 6101 PEC 1,000 33,4900 33,49 33,49 4,02 0,00 12,00 0,00",
            "1000108790 CALCA JOGGER BASICO(A) Cor 00004 Tam 12 6104.62.00 000 6101 PEC 1,000 41,7000 41,70 41,70 5,00 0,00 12,00 0,00",
            "1000108790 CALCA JOGGER BASICO(A) Cor 00004 Tam 14 6104.62.00 000 6101 PEC 2,000 41,7050 83,41 83,41 10,01 0,00 12,00 0,00",
            "1000121354 CAMISETA REGULAR Cor 00004 Tam 4 6109.90.00 000 6101 PEC 2,000 29,1450 58,29 58,29 6,99 0,00 12,00 0,00",
            "1000121354 CAMISETA REGULAR Cor 00004 Tam 12 6109.90.00 000 6101 PEC 2,000 39,2900 78,58 78,58 9,43 0,00 12,00 0,00",
        ]
    )


class ImportParsingTests(unittest.TestCase):
    def setUp(self) -> None:
        self._env_patcher = patch.dict(
            os.environ,
            {"LOJASYNC_LLM_PROVIDER": "legacy", "LLM_PROVIDER": "legacy"},
            clear=False,
        )
        self._env_patcher.start()

    def tearDown(self) -> None:
        self._env_patcher.stop()

    def test_parse_candidate_content_reads_json_items(self) -> None:
        payload = """
        {"items":[
          {"codigo":"12345","nome":"CAMISETA BASICA","quantidade":2,"preco":"19,90"},
          {"codigo":"88990","nome":"SHORT JEANS","quantidade":1,"preco":"39,90"}
        ]}
        """

        records = parse_candidate_content(payload)

        self.assertEqual([item.codigo for item in records], ["12345", "88990"])
        self.assertEqual([item.quantidade for item in records], [2, 1])

    def test_filter_suspect_records_merges_duplicates_and_preserves_longer_description(self) -> None:
        records = [
            Product(
                nome="VESTIDO MIDI",
                codigo="ABC123",
                quantidade=1,
                preco="79,90",
                categoria="",
                marca="",
                descricao_completa="VESTIDO MIDI",
            ),
            Product(
                nome="VESTIDO MIDI",
                codigo="ABC123",
                quantidade=2,
                preco="79,90",
                categoria="",
                marca="",
                descricao_completa="VESTIDO MIDI COM DETALHE",
            ),
        ]

        filtered = filter_suspect_records(records)

        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0].quantidade, 3)
        self.assertEqual(filtered[0].descricao_completa, "VESTIDO MIDI COM DETALHE")

    def test_parse_candidate_content_keeps_short_numeric_skus(self) -> None:
        payload = """
        {"items":[
          {"codigo":"24002","nome":"CALCA TE","quantidade":5,"preco":"95,00"},
          {"codigo":"24019","nome":"REGATA P","quantidade":5,"preco":"38,00"},
          {"codigo":"24133","nome":"CALCA PA","quantidade":3,"preco":"95,00"},
          {"codigo":"25020","nome":"REGATA B","quantidade":7,"preco":"40,00"}
        ]}
        """

        records = parse_candidate_content(payload)

        self.assertEqual([item.codigo for item in records], ["24002", "24019", "24133", "25020"])

    def test_split_text_chunks_prefers_newline_boundaries(self) -> None:
        text = "linha 1 muito longa\nlinha 2 muito longa\nlinha 3 muito longa"

        chunks = split_text_chunks(text, max_chars=24)

        self.assertGreaterEqual(len(chunks), 2)
        self.assertTrue(all(chunk for chunk in chunks))
        self.assertTrue(chunks[0].endswith("longa"))

    def test_split_structured_invoice_chunks_preserves_complete_rows(self) -> None:
        text = _sample_invoice_rows()

        chunks = split_structured_invoice_chunks(text, max_lines=3, max_chars=500)

        self.assertEqual(len(chunks), 3)
        self.assertEqual(sum(len(extract_structured_invoice_row_lines(chunk)) for chunk in chunks), 8)
        self.assertTrue(all(extract_structured_invoice_row_lines(chunk) for chunk in chunks))

    def test_compact_import_batch_keeps_same_code_with_different_prices_separate(self) -> None:
        service = ProductService(
            _DummyRepo(),
            _DummyBrands(),
            _DummyMarginStore(),
            _DummyMetricsStore(),
        )
        payload = """
        {"items":[
          {"codigo":"07249600200","descricao_original":"CALCA INF BOLSO RETO 0510 ESSENCIAL","nome_curto":"CALCA BOLSO RETO","quantidade":2,"preco":"84,99","tamanho":"10"},
          {"codigo":"07249600200","descricao_original":"CALCA INF BOLSO RETO 0512 ESSENCIAL","nome_curto":"CALCA BOLSO RETO","quantidade":2,"preco":"84,99","tamanho":"12"},
          {"codigo":"07249600200","descricao_original":"CALCA INF BOLSO RETO 0502 ESSENCIAL","nome_curto":"CALCA BOLSO RETO","quantidade":1,"preco":"79,99","tamanho":"02"},
          {"codigo":"07249600200","descricao_original":"CALCA INF BOLSO RETO 0508 ESSENCIAL","nome_curto":"CALCA BOLSO RETO","quantidade":2,"preco":"79,99","tamanho":"08"},
          {"codigo":"02649601000","descricao_original":"JAQUETA INF C/ ZIPER TRAD 0510 ESSE","nome_curto":"JAQUETA ZIPER TRAD","quantidade":2,"preco":"99,99","tamanho":"10"},
          {"codigo":"02649601000","descricao_original":"JAQUETA INF C/ ZIPER TRAD 0518 ESSE","nome_curto":"JAQUETA ZIPER TRAD","quantidade":2,"preco":"99,99","tamanho":"18"},
          {"codigo":"02649601000","descricao_original":"JAQUETA INF C/ ZIPER TRAD 0502 ESSE","nome_curto":"JAQUETA ZIPER TRAD","quantidade":1,"preco":"94,99","tamanho":"02"},
          {"codigo":"02649601000","descricao_original":"JAQUETA INF C/ ZIPER TRAD 0508 ESSE","nome_curto":"JAQUETA ZIPER TRAD","quantidade":2,"preco":"94,99","tamanho":"08"}
        ]}
        """

        parsed = parse_candidate_content(payload)
        # Size rows of the same SKU+price already merge during parse.
        self.assertEqual(len(parsed), 4)
        compacted, summary = service.compact_import_batch(parsed)

        self.assertEqual(len(compacted), 4)
        self.assertEqual(summary["resultantes"], 4)
        self.assertEqual(summary["removidos"], 0)
        self.assertEqual(
            [(item.codigo, item.preco, item.quantidade) for item in compacted],
            [
                ("07249600200", "84,99", 4),
                ("07249600200", "79,99", 3),
                ("02649601000", "99,99", 4),
                ("02649601000", "94,99", 3),
            ],
        )
        self.assertEqual(
            [[(grade.tamanho, grade.quantidade) for grade in (item.grades or [])] for item in compacted],
            [
                [("10", 2), ("12", 2)],
                [("2", 1), ("8", 2)],
                [("10", 2), ("18", 2)],
                [("2", 1), ("8", 2)],
            ],
        )

    def test_compact_import_batch_keeps_same_code_and_price_with_different_names_separate(self) -> None:
        service = ProductService(
            _DummyRepo(),
            _DummyBrands(),
            _DummyMarginStore(),
            _DummyMetricsStore(),
        )
        payload = """
        {"items":[
          {"codigo":"DUP-001","descricao_original":"CALCA BOLSO RETO TAM 36","nome_curto":"CALCA BOLSO RETO","quantidade":2,"preco":"84,99","tamanho":"36"},
          {"codigo":"DUP-001","descricao_original":"CALCA BOLSO RETO TAM 38","nome_curto":"CALCA BOLSO RETO","quantidade":1,"preco":"84,99","tamanho":"38"},
          {"codigo":"DUP-001","descricao_original":"JAQUETA ZIPER TRAD TAM P","nome_curto":"JAQUETA ZIPER TRAD","quantidade":2,"preco":"84,99","tamanho":"P"},
          {"codigo":"DUP-001","descricao_original":"JAQUETA ZIPER TRAD TAM M","nome_curto":"JAQUETA ZIPER TRAD","quantidade":1,"preco":"84,99","tamanho":"M"}
        ]}
        """

        parsed = parse_candidate_content(payload)
        self.assertEqual(len(parsed), 2)
        compacted, summary = service.compact_import_batch(parsed)

        self.assertEqual(len(compacted), 2)
        self.assertEqual(summary["resultantes"], 2)
        self.assertEqual(summary["removidos"], 0)
        self.assertEqual(
            [(item.nome, item.codigo, item.preco, item.quantidade) for item in compacted],
            [
                ("CALCA BOLSO RETO", "DUP-001", "84,99", 3),
                ("JAQUETA ZIPER TRAD", "DUP-001", "84,99", 3),
            ],
        )
        self.assertEqual(
            [[(grade.tamanho, grade.quantidade) for grade in (item.grades or [])] for item in compacted],
            [
                [("36", 2), ("38", 1)],
                [("P", 2), ("M", 1)],
            ],
        )

    def test_parse_candidate_content_reads_structured_invoice_rows(self) -> None:
        records = parse_candidate_content(_sample_invoice_rows())

        # Same SKU+name+price size rows merge into one product with accumulated grades.
        self.assertEqual(len(records), 7)
        self.assertEqual(records[0].codigo, "1000108790")
        self.assertEqual(records[0].nome, "CALCA JOGGER BASICO(A)")
        self.assertEqual(records[0].preco, "27,13")
        self.assertEqual(records[0].quantidade, 2)
        self.assertIsNotNone(records[0].grades)
        self.assertEqual(
            [(grade["tamanho"], grade["quantidade"]) for grade in (records[0].grades or [])],
            [("2", 1), ("3", 1)],
        )
        self.assertEqual(records[1].preco, "33,50")
        self.assertEqual(records[4].preco, "41,71")
        self.assertEqual(records[6].preco, "39,29")

    def test_compact_import_batch_keeps_price_tiers_from_structured_invoice_rows(self) -> None:
        service = ProductService(
            _DummyRepo(),
            _DummyBrands(),
            _DummyMarginStore(),
            _DummyMetricsStore(),
        )

        parsed = parse_candidate_content(_sample_invoice_rows())
        compacted, summary = service.compact_import_batch(parsed)

        joggers = [item for item in compacted if item.codigo == "1000108790"]
        self.assertEqual(len(joggers), 3)
        self.assertEqual(summary["resultantes"], len(compacted))
        self.assertEqual(
            [(item.preco, item.quantidade) for item in joggers],
            [
                ("27,13", 2),
                ("33,50", 3),
                ("41,70", 3),
            ],
        )

    def test_compact_import_batch_normalizes_zero_padded_grade_sizes_into_numeric_slots(self) -> None:
        service = ProductService(
            _DummyRepo(),
            _DummyBrands(),
            _DummyMarginStore(),
            _DummyMetricsStore(),
        )
        payload = """
        {"items":[
          {"codigo":"1000108790","descricao_original":"CALCA JOGGER BASICO(A) Cor 00004 Tam 04","nome_curto":"CALCA JOGGER","quantidade":2,"preco":"33,49","tamanho":"04"},
          {"codigo":"1000108790","descricao_original":"CALCA JOGGER BASICO(A) Cor 00004 Tam 06","nome_curto":"CALCA JOGGER","quantidade":3,"preco":"33,49","tamanho":"06"},
          {"codigo":"1000108790","descricao_original":"CALCA JOGGER BASICO(A) Cor 00004 Tam 08","nome_curto":"CALCA JOGGER","quantidade":1,"preco":"33,49","tamanho":"08"}
        ]}
        """

        parsed = parse_candidate_content(payload)
        compacted, summary = service.compact_import_batch(parsed)

        self.assertEqual(summary["resultantes"], 1)
        self.assertEqual(
            [(item.tamanho, item.quantidade) for item in (compacted[0].grades or [])],
            [("4", 2), ("6", 3), ("8", 1)],
        )

    def test_analyze_parsed_document_flags_total_mismatch_against_printed_note(self) -> None:
        analysis = analyze_parsed_document(
            "VALOR TOTAL DOS PRODUTOS 19.214,49\nVALOR TOTAL DA NOTA 19.214,49",
            [
                Product(
                    nome="CALCA JOGGER",
                    codigo="1000108790",
                    quantidade=1,
                    preco="33,49",
                    categoria="",
                    marca="",
                )
            ],
        )

        self.assertTrue(analysis["warnings"])
        self.assertIn("total extraido dos itens", analysis["warnings"][0].lower())
        self.assertEqual(analysis["metrics"]["document_total_products"], "19214,49")
        self.assertEqual(analysis["metrics"]["document_total_note"], "19214,49")
        self.assertFalse(analysis["metrics"]["products_value_matches_document"])

    def test_compact_import_batch_merges_near_equal_llm_float_price_tiers(self) -> None:
        service = ProductService(
            _DummyRepo(),
            _DummyBrands(),
            _DummyMarginStore(),
            _DummyMetricsStore(),
        )
        payload = """
        {"items":[
          {"codigo":"1000108790","descricao_original":"CALCA JOGGER BASICO(A) Cor 00004 Tam 6","nome_curto":"CALCA JOGGER","quantidade":2,"preco":33.495,"tamanho":"6"},
          {"codigo":"1000108790","descricao_original":"CALCA JOGGER BASICO(A) Cor 00004 Tam 8","nome_curto":"CALCA JOGGER","quantidade":1,"preco":33.49,"tamanho":"8"},
          {"codigo":"1000108790","descricao_original":"CALCA JOGGER BASICO(A) Cor 00004 Tam 10","nome_curto":"CALCA JOGGER","quantidade":2,"preco":33.495,"tamanho":"10"},
          {"codigo":"1000108790","descricao_original":"CALCA JOGGER BASICO(A) Cor 00004 Tam 12","nome_curto":"CALCA JOGGER","quantidade":1,"preco":41.7,"tamanho":"12"},
          {"codigo":"1000108790","descricao_original":"CALCA JOGGER BASICO(A) Cor 00004 Tam 14","nome_curto":"CALCA JOGGER","quantidade":2,"preco":41.705,"tamanho":"14"},
          {"codigo":"1000108790","descricao_original":"CALCA JOGGER BASICO(A) Cor 00004 Tam 16","nome_curto":"CALCA JOGGER","quantidade":2,"preco":41.705,"tamanho":"16"},
          {"codigo":"1000108790","descricao_original":"CALCA JOGGER BASICO(A) Cor 00004 Tam 18","nome_curto":"CALCA JOGGER","quantidade":2,"preco":41.705,"tamanho":"18"}
        ]}
        """

        parsed = parse_candidate_content(payload)
        compacted, _ = service.compact_import_batch(parsed)

        self.assertEqual(
            [(item.preco, item.quantidade) for item in compacted],
            [
                ("33,50", 5),
                ("41,70", 7),
            ],
        )

    def test_run_import_job_uses_only_llm_output_for_romaneio_selection(self) -> None:
        service = _RecordingImportService()
        job = create_import_job()

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                data_dir = Path(tmpdir)
                fake_client = _FakeHttpxClient(
                    {
                        "documents": [{"name": "parte_1", "content": _sample_invoice_rows()}],
                        "images": [],
                        "errors": ["PDF renderer unavailable"],
                    }
                )
                with patch("app.interfaces.api.http.jobs.runtime.httpx.Client", return_value=fake_client):
                    with patch(
                        "app.interfaces.api.http.jobs.runtime.post_llm_chat",
                        return_value=(_sample_invoice_rows(), None),
                    ) as mocked_chat:
                        run_import_job(
                            job_id=job.job_id,
                            contents=_sample_invoice_rows().encode("utf-8"),
                            filename="romaneio.txt",
                            content_type="text/plain",
                            service=service,
                            data_dir=data_dir,
                        )

                result = get_import_result(job.job_id)
                self.assertIsNotNone(result)
                assert result is not None
                self.assertEqual(result.status, "ok")
                self.assertEqual(result.metrics["selected_source"], "llm")
                self.assertEqual(result.total_itens, 7)
                self.assertTrue(result.metrics["llm_upload_used"])
                self.assertTrue(result.metrics["llm_chat_used"])
                self.assertTrue(bool(result.metrics.get("llm_oneshot")))
                self.assertEqual(result.metrics["upload_structured_candidates"], 8)
                self.assertIn("PDF renderer unavailable", result.warnings)
                self.assertTrue(
                    any(
                        event.get("source") == "llm"
                        and event.get("level") == "warning"
                        and event.get("message") == "PDF renderer unavailable"
                        for event in result.metrics["process_log"]
                    )
                )
                self.assertEqual(fake_client.upload_calls, 1)
                self.assertEqual(mocked_chat.call_count, 1)
                joggers = [item for item in service.created if item.codigo == "1000108790"]
                # 6 printed size rows collapse into 5 price-tier products (sizes 2+3 share 27,13).
                self.assertEqual(len(joggers), 5)
        finally:
            remove_import_job(job.job_id)

    def test_run_import_job_prefer_llm_does_not_skip_llm_when_local_parser_is_approved(self) -> None:
        service = _RecordingImportService()
        job = create_import_job()
        local_payload = {
            "total_rows": 1,
            "total_itens": 1,
            "remessa_quantity": 2,
            "quantity_matches_remessa": True,
            "document_total_products": "40,00",
            "document_total_note": None,
            "extracted_total_products": "40,00",
            "products_value_matches_document": True,
            "items": [
                {
                    "nome": "CAMISETA LOCAL",
                    "codigo": "LOCAL-1",
                    "quantidade": 2,
                    "preco": "20,00",
                }
            ],
        }
        upload_text = "\n".join(["Qtd de Peças da Remessa: 12", _sample_invoice_rows()])

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                data_dir = Path(tmpdir)
                fake_client = _FakeHttpxClient(
                    {
                        "documents": [{"name": "parte_1", "content": upload_text}],
                        "images": [],
                        "errors": [],
                    }
                )
                with patch(
                    "app.interfaces.api.http.jobs.runtime.parse_local_romaneio_experiment",
                    return_value=local_payload,
                ):
                    with patch("app.interfaces.api.http.jobs.runtime.httpx.Client", return_value=fake_client):
                        with patch(
                            "app.interfaces.api.http.jobs.runtime.post_llm_chat",
                            return_value=(_sample_invoice_rows(), None),
                        ) as mocked_chat:
                            run_import_job(
                                job_id=job.job_id,
                                contents=b"fake-pdf",
                                filename="romaneio.pdf",
                                content_type="application/pdf",
                                service=service,
                                data_dir=data_dir,
                                prefer_llm=True,
                                skip_local_parser=False,
                            )

                result = get_import_result(job.job_id)
                self.assertIsNotNone(result)
                assert result is not None
                self.assertEqual(result.status, "ok")
                self.assertEqual(result.metrics["local_validation_status"], "approved")
                self.assertTrue(result.metrics["local_parser_preapproved"])
                self.assertEqual(result.metrics["selected_source"], "llm")
                self.assertEqual(fake_client.upload_calls, 1)
                self.assertEqual(mocked_chat.call_count, 1)
                self.assertEqual(mocked_chat.call_count, 1)
                self.assertEqual(len(service.created), 7)
        finally:
            remove_import_job(job.job_id)

    def test_run_import_job_skip_local_parser_does_not_probe_local_parser(self) -> None:
        service = _RecordingImportService()
        job = create_import_job()
        approved_upload_text = "\n".join(["Qtd de PeÃ§as da Remessa: 12", _sample_invoice_rows()])

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                data_dir = Path(tmpdir)
                fake_client = _FakeHttpxClient(
                    {
                        "documents": [{"name": "parte_1", "content": approved_upload_text}],
                        "images": [],
                        "errors": [],
                    }
                )
                with patch(
                    "app.interfaces.api.http.jobs.runtime.parse_local_romaneio_experiment",
                    side_effect=AssertionError("local parser should not run for IA import"),
                ) as mocked_local_parser:
                    with patch("app.interfaces.api.http.jobs.runtime.httpx.Client", return_value=fake_client):
                        with patch(
                            "app.interfaces.api.http.jobs.runtime.post_llm_chat",
                            return_value=(_sample_invoice_rows(), None),
                        ) as mocked_chat:
                            run_import_job(
                                job_id=job.job_id,
                                contents=b"fake-pdf",
                                filename="romaneio.pdf",
                                content_type="application/pdf",
                                service=service,
                                data_dir=data_dir,
                                prefer_llm=True,
                                skip_local_parser=True,
                            )

                result = get_import_result(job.job_id)
                self.assertIsNotNone(result)
                assert result is not None
                self.assertEqual(result.status, "ok")
                self.assertTrue(result.metrics["local_parser_skipped"])
                self.assertEqual(result.metrics["selected_source"], "llm")
                self.assertEqual(fake_client.upload_calls, 1)
                self.assertEqual(mocked_chat.call_count, 1)
                self.assertEqual(mocked_local_parser.call_count, 0)
                self.assertEqual(len(service.created), 7)
        finally:
            remove_import_job(job.job_id)

    def test_run_import_job_does_not_replace_llm_with_local_guard(self) -> None:
        """Local guard is off by default: incomplete LLM result is not swapped for local parse."""
        service = _RecordingImportService()
        job = create_import_job()
        incomplete_ocr = """
        {"items":[
          {"codigo":"CO.FEM.00018","descricao_original":"COLETE ALFAIATARIA","nome_curto":"COLETE ALFAIATARIA","quantidade":5,"preco":79.90},
          {"codigo":"CA.FEM.00327","descricao_original":"CALCA ALFAIATARIA","nome_curto":"CALCA ALFAIATARIA","quantidade":5,"preco":129.90}
        ]}
        """

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                data_dir = Path(tmpdir)
                fake_client = _FakeHttpxClient(
                    {
                        "documents": [],
                        "images": [{"name": "romaneio.pdf#p1", "data": "not-a-real-image"}],
                        "errors": [],
                    }
                )
                with patch(
                    "app.interfaces.api.http.jobs.runtime.parse_local_romaneio_experiment",
                ) as mocked_local_parser:
                    with patch("app.interfaces.api.http.jobs.runtime.httpx.Client", return_value=fake_client):
                        with patch(
                            "app.interfaces.api.http.jobs.runtime.post_llm_chat",
                            return_value=(incomplete_ocr, None),
                        ) as mocked_chat:
                            run_import_job(
                                job_id=job.job_id,
                                contents=b"fake-pdf-image",
                                filename="romaneio.pdf",
                                content_type="application/pdf",
                                service=service,
                                data_dir=data_dir,
                                prefer_llm=True,
                                skip_local_parser=True,
                            )

                result = get_import_result(job.job_id)
                self.assertIsNotNone(result)
                assert result is not None
                self.assertEqual(result.metrics.get("selected_source"), "llm")
                self.assertFalse(bool(result.metrics.get("local_guard_used")))
                self.assertEqual(mocked_local_parser.call_count, 0)
                self.assertEqual(mocked_chat.call_count, 1)
        finally:
            remove_import_job(job.job_id)

    def test_run_import_job_keeps_empty_llm_result_without_local_rescue(self) -> None:
        service = _RecordingImportService()
        job = create_import_job()

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                data_dir = Path(tmpdir)
                fake_client = _FakeHttpxClient(
                    {
                        "documents": [{"name": "parte_1", "content": "texto sem linhas suficientes"}],
                        "images": [],
                        "errors": [],
                    }
                )
                with patch(
                    "app.interfaces.api.http.jobs.runtime.parse_local_romaneio_experiment",
                ) as mocked_local_parser:
                    with patch("app.interfaces.api.http.jobs.runtime.httpx.Client", return_value=fake_client):
                        with patch(
                            "app.interfaces.api.http.jobs.runtime.post_llm_chat",
                            return_value=('{"items":[]}', None),
                        ):
                            run_import_job(
                                job_id=job.job_id,
                                contents=b"fake-pdf",
                                filename="romaneio.pdf",
                                content_type="application/pdf",
                                service=service,
                                data_dir=data_dir,
                                prefer_llm=True,
                                skip_local_parser=True,
                            )

                result = get_import_result(job.job_id)
                job_status = get_import_job(job.job_id)
                self.assertIsNone(result)
                self.assertIsNotNone(job_status)
                assert job_status is not None
                self.assertEqual(job_status.stage, "error")
                self.assertEqual(mocked_local_parser.call_count, 0)
                self.assertEqual(len(service.created), 0)
        finally:
            remove_import_job(job.job_id)

    def test_run_import_job_retries_incomplete_llm_chunk_with_smaller_structured_subchunks(self) -> None:
        service = _RecordingImportService()
        job = create_import_job()
        upload_text = "\n".join(
            [
                "Qtd de Peças da Remessa: 12",
                _sample_invoice_rows(),
            ]
        )
        rows = _sample_invoice_rows().splitlines()
        partial_llm_output = "\n".join(rows[:4])
        retry_first_half = "\n".join(rows[:4])
        retry_second_half = "\n".join(rows[4:])

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                data_dir = Path(tmpdir)
                fake_client = _FakeHttpxClient(
                    {
                        "documents": [{"name": "parte_1", "content": upload_text}],
                        "images": [],
                        "errors": [],
                    }
                )
                with patch.dict(os.environ, {"LLM_IMPORT_RETRY_MAX_LINES": "4"}):
                    with patch("app.interfaces.api.http.jobs.runtime.httpx.Client", return_value=fake_client):
                        with patch(
                            "app.interfaces.api.http.jobs.runtime.post_llm_chat",
                            side_effect=[
                                (partial_llm_output, None),
                                (retry_first_half, None),
                                (retry_second_half, None),
                            ],
                        ) as mocked_chat:
                            run_import_job(
                                job_id=job.job_id,
                                contents=upload_text.encode("utf-8"),
                                filename="romaneio.txt",
                                content_type="text/plain",
                                service=service,
                                data_dir=data_dir,
                            )

                result = get_import_result(job.job_id)
                self.assertIsNotNone(result)
                assert result is not None
                self.assertEqual(result.status, "ok")
                self.assertEqual(result.metrics["selected_source"], "llm")
                self.assertEqual(result.metrics["upload_structured_candidates"], 8)
                self.assertEqual(result.total_itens, 7)
                self.assertTrue(result.metrics["llm_quantity_matches_remessa"])
                self.assertIn("subdividindo o trecho", " ".join(result.warnings).lower())
                self.assertEqual(fake_client.upload_calls, 1)
                self.assertEqual(mocked_chat.call_count, 3)
                self.assertEqual(len(service.created), 7)
        finally:
            remove_import_job(job.job_id)

    def test_run_import_job_retries_when_llm_returns_same_count_but_wrong_chunk_tail(self) -> None:
        service = _RecordingImportService()
        job = create_import_job()
        upload_text = "\n".join(
            [
                "Qtd de Peças da Remessa: 12",
                _sample_invoice_rows(),
            ]
        )
        rows = _sample_invoice_rows().splitlines()
        same_count_wrong_tail = "\n".join(rows[:6] + rows[:2])
        retry_first_half = "\n".join(rows[:4])
        retry_second_half = "\n".join(rows[4:])

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                data_dir = Path(tmpdir)
                fake_client = _FakeHttpxClient(
                    {
                        "documents": [{"name": "parte_1", "content": upload_text}],
                        "images": [],
                        "errors": [],
                    }
                )
                with patch.dict(os.environ, {"LLM_IMPORT_RETRY_MAX_LINES": "4"}):
                    with patch("app.interfaces.api.http.jobs.runtime.httpx.Client", return_value=fake_client):
                        with patch(
                            "app.interfaces.api.http.jobs.runtime.post_llm_chat",
                            side_effect=[
                                (same_count_wrong_tail, None),
                                (retry_first_half, None),
                                (retry_second_half, None),
                            ],
                        ) as mocked_chat:
                            run_import_job(
                                job_id=job.job_id,
                                contents=upload_text.encode("utf-8"),
                                filename="romaneio.txt",
                                content_type="text/plain",
                                service=service,
                                data_dir=data_dir,
                            )

                result = get_import_result(job.job_id)
                self.assertIsNotNone(result)
                assert result is not None
                self.assertEqual(result.status, "ok")
                self.assertEqual(result.metrics["selected_source"], "llm")
                self.assertTrue(result.metrics["llm_quantity_matches_remessa"])
                self.assertGreaterEqual(int(result.metrics.get("llm_chunk_retry_count") or 0), 1)
                self.assertIn("ultimo codigo", " ".join(result.warnings).lower())
                self.assertEqual(mocked_chat.call_count, 3)
                self.assertEqual(len(service.created), 7)
        finally:
            remove_import_job(job.job_id)

    def test_run_import_job_blocks_persist_when_invoice_totals_still_do_not_match(self) -> None:
        service = _RecordingImportService()
        job = create_import_job()
        upload_text = "\n".join(
            [
                "VALOR TOTAL DOS PRODUTOS 999,99",
                "VALOR TOTAL DA NOTA 999,99",
                _sample_invoice_rows(),
            ]
        )

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                data_dir = Path(tmpdir)
                fake_client = _FakeHttpxClient(
                    {
                        "documents": [{"name": "parte_1", "content": upload_text}],
                        "images": [],
                        "errors": [],
                    }
                )
                with patch("app.interfaces.api.http.jobs.runtime.httpx.Client", return_value=fake_client):
                    with patch(
                        "app.interfaces.api.http.jobs.runtime.post_llm_chat",
                        return_value=(_sample_invoice_rows(), None),
                    ):
                        run_import_job(
                            job_id=job.job_id,
                            contents=upload_text.encode("utf-8"),
                            filename="romaneio.txt",
                            content_type="text/plain",
                            service=service,
                            data_dir=data_dir,
                        )

                status = get_import_job(job.job_id)
                result = get_import_result(job.job_id)
                self.assertIsNotNone(status)
                assert status is not None
                self.assertEqual(status.stage, "error")
                self.assertIn("não confere com o total de produtos impresso na nota", str(status.error))
                self.assertEqual(status.metrics["failure_code"], "validation_rejected")
                self.assertEqual(status.metrics["final_validation_reason_codes"], ["product_total_mismatch"])
                self.assertIsNone(result)
                self.assertEqual(len(service.created), 0)
        finally:
            remove_import_job(job.job_id)

    def test_run_import_job_uses_vertical_image_fallback_when_full_page_returns_no_items(self) -> None:
        service = _RecordingImportService()
        job = create_import_job()

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                data_dir = Path(tmpdir)
                fake_client = _FakeHttpxClient(
                    {
                        "documents": [],
                        "images": [{"name": "page#p1", "data": "not-a-real-image"}],
                        "errors": [],
                    }
                )
                with patch.dict(
                    os.environ,
                    {
                        "LLM_IMAGE_BATCH_SIZE": "1",
                        "LLM_ROMANEIO_PDF_PAGE_VERTICAL_SLICES": "2",
                        "LLM_PDF_PAGE_VERTICAL_SLICES": "2",
                    },
                ):
                    with patch("app.interfaces.api.http.jobs.runtime.httpx.Client", return_value=fake_client):
                        with patch(
                            "app.interfaces.api.http.jobs.runtime.post_llm_chat",
                            side_effect=[("", None), (_sample_invoice_rows(), None)],
                        ) as mocked_chat:
                            run_import_job(
                                job_id=job.job_id,
                                contents=b"raw image upload",
                                filename="romaneio.png",
                                content_type="image/png",
                                service=service,
                                data_dir=data_dir,
                            )

                result = get_import_result(job.job_id)
                self.assertIsNotNone(result)
                assert result is not None
                self.assertEqual(result.status, "ok")
                self.assertEqual(result.metrics["selected_source"], "llm")
                self.assertEqual(result.total_itens, 7)
                self.assertEqual(mocked_chat.call_count, 2)
                self.assertEqual(result.metrics["llm_chunk_count"], 2)
                self.assertEqual(
                    [item["attempt"] for item in result.metrics["llm_chat_calls_details"]],
                    ["full_page", "vertical_slices"],
                )
                self.assertIn("recortes verticais", " ".join(result.warnings).lower())
                self.assertEqual(len(service.created), 7)
        finally:
            remove_import_job(job.job_id)

if __name__ == "__main__":
    unittest.main()
