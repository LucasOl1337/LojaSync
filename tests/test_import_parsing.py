from __future__ import annotations

import json
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
        compacted, summary = service.compact_import_batch(parsed)

        self.assertEqual(len(compacted), 4)
        self.assertEqual(summary["resultantes"], 4)
        self.assertEqual(summary["removidos"], 4)
        self.assertEqual(
            [(item.codigo, item.preco, item.quantidade) for item in compacted],
            [
                ("07249600200", "84,99", 4),
                ("07249600200", "79,99", 3),
                ("02649601000", "99,99", 4),
                ("02649601000", "94,99", 3),
            ],
        )

    def test_parse_candidate_content_reads_structured_invoice_rows(self) -> None:
        records = parse_candidate_content(_sample_invoice_rows())

        self.assertEqual(len(records), 8)
        self.assertEqual(records[0].codigo, "1000108790")
        self.assertEqual(records[0].nome, "CALCA JOGGER BASICO(A)")
        self.assertEqual(records[0].preco, "27,13")
        self.assertIsNotNone(records[0].grades)
        self.assertEqual(records[0].grades[0]["tamanho"], "2")
        self.assertEqual(records[0].grades[0]["quantidade"], 1)
        self.assertEqual(records[2].preco, "33,50")
        self.assertEqual(records[5].preco, "41,71")
        self.assertEqual(records[7].preco, "39,29")

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
                        "errors": [],
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
                self.assertEqual(result.total_itens, 8)
                self.assertTrue(result.metrics["llm_upload_used"])
                self.assertTrue(result.metrics["llm_chat_used"])
                self.assertEqual(result.metrics["local_structured_candidates"], 8)
                self.assertEqual(result.metrics["upload_structured_candidates"], 8)
                self.assertEqual(fake_client.upload_calls, 1)
                self.assertEqual(mocked_chat.call_count, 1)
                joggers = [item for item in service.created if item.codigo == "1000108790"]
                self.assertEqual(len(joggers), 6)
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
                self.assertEqual(result.total_itens, 8)
                self.assertTrue(result.metrics["llm_quantity_matches_remessa"])
                self.assertIn("subdividindo o trecho", " ".join(result.warnings).lower())
                self.assertEqual(fake_client.upload_calls, 1)
                self.assertEqual(mocked_chat.call_count, 3)
                self.assertEqual(len(service.created), 8)
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
                self.assertEqual(len(service.created), 8)
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
                self.assertIn("did not match the invoice validation checks", str(status.error))
                self.assertIsNone(result)
                self.assertEqual(len(service.created), 0)
        finally:
            remove_import_job(job.job_id)

    def test_apply_post_processing_applies_local_safe_adjustments(self) -> None:
        repo = _DummyRepo(
            [
                Product(
                    nome="REGATA CROPPED [50CM] BASICO(A)",
                    codigo="1000086766",
                    quantidade=3,
                    preco="20,37",
                    categoria="",
                    marca="",
                    descricao_completa="REGATA CROPPED [50CM] BASICO(A) Cor 00004 Tam 12 *AB-CD* AD",
                ),
                Product(
                    nome="CALA JOGGER BASICO(A)",
                    codigo="1000108790",
                    quantidade=2,
                    preco="33,49",
                    categoria="",
                    marca="",
                    descricao_completa="CALA JOGGER BASICO(A) Cor 00004 Tam 8",
                ),
            ]
        )
        service = ProductService(
            repo,
            _DummyBrands(),
            _DummyMarginStore(),
            _DummyMetricsStore(),
        )

        result = service.apply_post_processing(None)
        items = service.list_products()

        self.assertFalse(result["dry_run"])
        self.assertEqual(result["modificados"], 2)
        self.assertEqual(items[0].nome, "REGATA CROPPED BASICO")
        self.assertEqual(items[0].preco, "20,40")
        self.assertEqual(items[1].nome, "CALCA JOGGER BASICO")
        self.assertEqual(items[1].preco, "33,50")

    def test_apply_post_processing_uses_structured_llm_suggestion_when_confident(self) -> None:
        product = Product(
            nome="JAQUETA SOLIRA",
            codigo="090840002",
            quantidade=6,
            preco="90,90",
            categoria="",
            marca="",
            descricao_completa="JAQUETA SOLIRA *SA-FKII* AD",
        )
        repo = _DummyRepo([product])
        service = ProductService(
            repo,
            _DummyBrands(),
            _DummyMarginStore(),
            _DummyMetricsStore(),
        )

        llm_payload = json.dumps(
            {
                "items": [
                    {
                        "ordering_key": product.ordering_key(),
                        "nome_sugerido": "JAQUETA SOLAR",
                        "codigo_sugerido": "090840002",
                        "preco_sugerido": "90,91",
                        "acoes": "ajustar_tudo",
                        "confianca": 0.92,
                    }
                ]
            }
        )

        result = service.apply_post_processing(llm_payload)
        items = service.list_products()

        self.assertEqual(result["llm_suggestions_applied"], 1)
        self.assertEqual(items[0].nome, "JAQUETA SOLAR")
        self.assertEqual(items[0].preco, "91,00")

    def test_get_post_process_review_candidates_keeps_only_ambiguous_items_for_llm(self) -> None:
        noisy = Product(
            nome="REGATA CROPPED 50CM BASICO A COR",
            codigo="1000086766",
            quantidade=5,
            preco="20,37",
            categoria="",
            marca="",
            descricao_completa="REGATA CROPPED 50CM BASICO(A) COR 00004",
        )
        clean = Product(
            nome="EMBALAGEM KRAFT MALWEE KIDS",
            codigo="1000131724",
            quantidade=3,
            preco="19,00",
            categoria="",
            marca="",
            descricao_completa="EMBALAGEM KRAFT MALWEE KIDS",
        )
        repo = _DummyRepo([noisy, clean])
        service = ProductService(
            repo,
            _DummyBrands(),
            _DummyMarginStore(),
            _DummyMetricsStore(),
        )

        candidates = service.get_post_process_review_candidates()

        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0].codigo, noisy.codigo)


if __name__ == "__main__":
    unittest.main()
