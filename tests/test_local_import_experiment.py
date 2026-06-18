from __future__ import annotations

import unittest
from decimal import Decimal
from pathlib import Path

import pytest

from app.application.imports.local_experiment import (
    LocalImportDocumentAnchors,
    LocalImportTotals,
    ParsedInvoiceRow,
    build_local_import_items,
    build_local_import_metrics,
    build_local_import_result_payload,
    build_local_import_totals,
    parse_local_romaneio_experiment,
    resolve_local_import_document_anchors,
    select_local_import_rows,
)


class LocalImportExperimentTests(unittest.TestCase):
    def _super_romaneios_file(self, filename: str) -> Path:
        return Path.home() / "Downloads" / "SuperRomaneios" / "notas" / filename

    def test_build_local_import_items_groups_rows_and_sorts_grades(self) -> None:
        rows = [
            ParsedInvoiceRow(
                codigo="1000135918",
                nome="CONJUNTO",
                descricao_completa="CONJUNTO BLUSAO/CALCA",
                cor="02226",
                tamanho="9M",
                quantidade=1,
                preco="41,70",
                unidade="PC",
                valor_total="41,70",
                desconto_total="1,00",
            ),
            ParsedInvoiceRow(
                codigo="1000135918",
                nome="CONJUNTO",
                descricao_completa="CONJUNTO BLUSAO/CALCA INFANTIL LONGO",
                cor="02226",
                tamanho="6M",
                quantidade=2,
                preco="41,70",
                unidade="PC",
                valor_total="83,40",
                desconto_total="2,00",
            ),
            ParsedInvoiceRow(
                codigo="1000135918",
                nome="CONJUNTO",
                descricao_completa="CONJUNTO BLUSAO/CALCA",
                cor="02226",
                tamanho="P",
                quantidade=1,
                preco="41,70",
                unidade="PC",
                valor_total="41,70",
            ),
            ParsedInvoiceRow(
                codigo="1000135918",
                nome="CONJUNTO",
                descricao_completa="CONJUNTO BLUSAO/CALCA",
                cor="02226",
                tamanho="2",
                quantidade=1,
                preco="41,70",
                unidade="PC",
                valor_total="41,70",
            ),
            ParsedInvoiceRow(
                codigo="1000135918",
                nome="CONJUNTO",
                descricao_completa="CONJUNTO BLUSAO/CALCA",
                cor="00004",
                tamanho=None,
                quantidade=3,
                preco="41,70",
                unidade="PC",
                valor_total="125,10",
            ),
        ]

        items = build_local_import_items(rows)

        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]["quantidade"], 5)
        self.assertEqual(items[0]["linhas_originais"], 4)
        self.assertEqual(items[0]["descricao_completa"], "CONJUNTO BLUSAO/CALCA INFANTIL LONGO")
        self.assertEqual(items[0]["valor_total"], "208,50")
        self.assertEqual(items[0]["desconto_total"], "3,00")
        self.assertEqual(
            [(grade["tamanho"], grade["quantidade"]) for grade in items[0]["grades"]],
            [("6M", 2), ("9M", 1), ("P", 1), ("2", 1)],
        )
        self.assertEqual(items[1]["cor"], "00004")
        self.assertEqual(items[1]["grades"], [])

    def test_build_local_import_totals_reports_quantity_value_and_discount_warnings(self) -> None:
        totals = build_local_import_totals(
            items=[
                {"quantidade": 2, "valor_total": "20,00", "desconto_total": "1,00"},
                {"quantidade": 1, "valor_total": "10,00", "desconto_total": "0,50"},
            ],
            row_count=2,
            remessa_quantity=4,
            document_total_products=Decimal("31.00"),
            document_total_note=None,
            document_discount_total=Decimal("2.00"),
        )

        self.assertEqual(totals.total_quantity, 3)
        self.assertEqual(totals.extracted_total_products, Decimal("30.00"))
        self.assertEqual(totals.extracted_discount_total, Decimal("1.50"))
        self.assertFalse(totals.quantity_matches_remessa)
        self.assertFalse(totals.products_value_matches_document)
        self.assertFalse(totals.discount_matches_document)
        self.assertEqual(
            totals.warnings,
            [
                "Extracted quantity (3) does not match the remessa quantity printed in the document (4).",
                "Extracted product total does not match the printed 'Valor total dos produtos' in the document.",
                "Extracted discount total does not match the printed discount value in the document.",
            ],
        )

    def test_build_local_import_totals_ignores_implausibly_low_printed_discount(self) -> None:
        totals = build_local_import_totals(
            items=[{"quantidade": 1, "valor_total": "100,00", "desconto_total": "10,00"}],
            row_count=1,
            remessa_quantity=1,
            document_total_products=Decimal("100.00"),
            document_total_note=None,
            document_discount_total=Decimal("1.00"),
        )

        self.assertIsNone(totals.document_discount_total)
        self.assertIsNone(totals.discount_matches_document)
        self.assertEqual(totals.warnings, [])

    def test_build_local_import_metrics_counts_parser_outputs(self) -> None:
        metrics = build_local_import_metrics(
            page_count=2,
            text="linha 1\nlinha 2",
            row_count=5,
            items=[
                {"cor": "02226", "grades": [{"tamanho": "6M", "quantidade": 1}]},
                {"cor": "  ", "grades": []},
                {"cor": "00004", "grades": [{"tamanho": "P", "quantidade": 2}]},
                {"cor": "02226", "grades": None},
            ],
            ocr_page_count=1,
        )

        self.assertEqual(
            metrics,
            {
                "page_count": 2,
                "text_chars": 15,
                "matched_invoice_rows": 5,
                "grouped_items": 4,
                "colors_detected": 2,
                "items_with_grades": 2,
                "ocr_pages_used": 1,
                "extraction_mode": "isolated_local_parser",
            },
        )

    def test_build_local_import_result_payload_formats_totals_and_status(self) -> None:
        items = [{"codigo": "1000135918", "quantidade": 2}]
        metrics = {"page_count": 1, "extraction_mode": "isolated_local_parser"}

        payload = build_local_import_result_payload(
            filename="",
            row_count=2,
            items=items,
            anchors=LocalImportDocumentAnchors(
                remessa_quantity=2,
                document_total_products=Decimal("123.45"),
                document_total_note=Decimal("120.00"),
                document_discount_total=Decimal("3.45"),
            ),
            totals=LocalImportTotals(
                total_quantity=2,
                extracted_total_products=Decimal("123.45"),
                extracted_discount_total=Decimal("3.45"),
                document_discount_total=Decimal("3.45"),
                quantity_matches_remessa=True,
                products_value_matches_document=True,
                discount_matches_document=True,
                warnings=[],
            ),
            metrics=metrics,
        )

        self.assertEqual(
            payload,
            {
                "status": "ok",
                "filename": "romaneio",
                "warnings": [],
                "total_rows": 2,
                "total_itens": 1,
                "total_quantity": 2,
                "remessa_quantity": 2,
                "quantity_matches_remessa": True,
                "document_total_products": "123,45",
                "document_total_note": "120,00",
                "document_discount_total": "3,45",
                "extracted_total_products": "123,45",
                "extracted_discount_total": "3,45",
                "products_value_matches_document": True,
                "discount_matches_document": True,
                "items": items,
                "metrics": metrics,
            },
        )

    def test_select_local_import_rows_parses_structured_text_without_ocr(self) -> None:
        text = "\n".join(
            [
                "Qtd de Peças da Remessa: 1",
                "1000135918 CONJUNTO BLUSAO/CALCA Cor 02226 Tam 6M 6111.20.00 000 6101 PEC 1,000 41,7000 41,70 41,70 5,00 0,00 12,00 0,00",
            ]
        )

        rows = select_local_import_rows(
            contents=text.encode("utf-8"),
            filename="romaneio.txt",
            content_type="text/plain",
            text=text,
            ocr_pages=[],
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].codigo, "1000135918")
        self.assertEqual(rows[0].cor, "02226")
        self.assertEqual(rows[0].tamanho, "6M")
        self.assertEqual(rows[0].quantidade, 1)

    def test_resolve_local_import_document_anchors_reads_regular_totals_and_remessa(self) -> None:
        anchors = resolve_local_import_document_anchors(
            "\n".join(
                [
                    "Qtd de Peças da Remessa: 6",
                    "Valor total dos produtos 123,45",
                    "Valor total da nota 120,00",
                    "Desconto 3,45",
                ]
            )
        )

        self.assertEqual(anchors.remessa_quantity, 6)
        self.assertEqual(anchors.document_total_products, Decimal("123.45"))
        self.assertEqual(anchors.document_total_note, Decimal("120.00"))
        self.assertEqual(anchors.document_discount_total, Decimal("3.45"))

    def test_resolve_local_import_document_anchors_uses_sisplan_special_totals(self) -> None:
        anchors = resolve_local_import_document_anchors(
            "\n".join(
                [
                    "Pedido de Venda",
                    "SISPLAN",
                    "R$ 10,00",
                    "R$ 90,00",
                    "R$ 100,00",
                ]
            )
        )

        self.assertIsNone(anchors.remessa_quantity)
        self.assertEqual(anchors.document_total_products, Decimal("100.00"))
        self.assertEqual(anchors.document_total_note, Decimal("90.00"))
        self.assertEqual(anchors.document_discount_total, Decimal("10.00"))

    def test_local_experiment_preserves_colors_and_month_sizes(self) -> None:
        payload = "\n".join(
            [
                "Qtd de Peças da Remessa: 6",
                "1000135918 CONJUNTO BLUSAO/CALCA Cor 02226 Tam 6M 6111.20.00 000 6101 PEC 1,000 41,7000 41,70 41,70 5,00 0,00 12,00 0,00",
                "1000135918 CONJUNTO BLUSAO/CALCA Cor 02226 Tam 9M 6111.20.00 000 6101 PEC 1,000 41,7000 41,70 41,70 5,00 0,00 12,00 0,00",
                "1000108790 CALCA JOGGER BASICO(A) Cor 00004 Tam 2 6104.62.00 000 6101 PEC 2,000 27,1300 54,26 54,26 6,52 0,00 12,00 0,00",
                "1000108790 CALCA JOGGER BASICO(A) Cor 02313 Tam 2 6104.62.00 000 6101 PEC 2,000 27,1300 54,26 54,26 6,52 0,00 12,00 0,00",
            ]
        ).encode("utf-8")

        result = parse_local_romaneio_experiment(
            contents=payload,
            filename="romaneio.txt",
            content_type="text/plain",
        )

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["total_rows"], 4)
        self.assertEqual(result["total_itens"], 3)
        self.assertEqual(result["total_quantity"], 6)
        self.assertTrue(result["quantity_matches_remessa"])

        by_key = {
            (item["codigo"], item.get("cor"), item["preco"]): item
            for item in result["items"]
        }
        self.assertIn(("1000135918", "02226", "41,70"), by_key)
        self.assertIn(("1000108790", "00004", "27,13"), by_key)
        self.assertIn(("1000108790", "02313", "27,13"), by_key)

        month_item = by_key[("1000135918", "02226", "41,70")]
        self.assertEqual(
            [(grade["tamanho"], grade["quantidade"]) for grade in month_item["grades"]],
            [("6M", 1), ("9M", 1)],
        )

    @pytest.mark.local_files
    def test_download_notes_folder_parses_without_empty_results(self) -> None:
        folder = Path.home() / "Downloads" / "notas" / "notas"
        if not folder.exists():
            self.skipTest(f"Folder not available: {folder}")

        files = sorted(path for path in folder.iterdir() if path.is_file())
        self.assertTrue(files, "Expected at least one note file in the downloads/notas/notas folder.")

        for path in files:
            suffix = path.suffix.lower()
            content_type = "application/pdf" if suffix == ".pdf" else "image/jpeg"
            result = parse_local_romaneio_experiment(
                contents=path.read_bytes(),
                filename=path.name,
                content_type=content_type,
            )

            self.assertEqual(result["status"], "ok", path.name)
            self.assertGreater(result["total_rows"], 0, path.name)
            self.assertGreater(result["total_itens"], 0, path.name)
            self.assertGreater(result["total_quantity"], 0, path.name)

            if suffix == ".pdf" and (result.get("document_total_products") or result.get("document_total_note")):
                self.assertTrue(result["products_value_matches_document"], path.name)

    @pytest.mark.local_files
    def test_scanned_revanche_invoice_matches_products_total(self) -> None:
        path = Path.home() / "Downloads" / "notas" / "notas" / "2866.pdf"
        if not path.exists():
            self.skipTest(f"File not available: {path}")

        result = parse_local_romaneio_experiment(
            contents=path.read_bytes(),
            filename=path.name,
            content_type="application/pdf",
        )

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["total_rows"], 12)
        self.assertEqual(result["total_quantity"], 12)
        self.assertEqual(result["document_total_products"], "1258,80")
        self.assertEqual(result["extracted_total_products"], "1258,80")
        self.assertTrue(result["products_value_matches_document"])

    @pytest.mark.local_files
    def test_scanned_revanche_invoice_2920_matches_products_total(self) -> None:
        path = Path.home() / "Downloads" / "2920.pdf"
        if not path.exists():
            self.skipTest(f"File not available: {path}")

        result = parse_local_romaneio_experiment(
            contents=path.read_bytes(),
            filename=path.name,
            content_type="application/pdf",
        )

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["total_rows"], 15)
        self.assertEqual(result["total_itens"], 4)
        self.assertEqual(result["total_quantity"], 15)
        self.assertEqual(result["document_total_products"], "1708,50")
        self.assertEqual(result["document_total_note"], "1537,65")
        self.assertEqual(result["extracted_total_products"], "1708,50")
        self.assertTrue(result["products_value_matches_document"])

    @pytest.mark.local_files
    def test_super_romaneios_special_pdf_layouts_parse_successfully(self) -> None:
        cases = {
            "NF-e_1054194.pdf": {"rows": 88, "total": "7152,60"},
            "ROMANEIO NF 68350 JULIANA MARIA HERREIRO DE OLIVEIRA.pdf": {"rows": 15, "total": "3223,86"},
            "Romaneio-Nota-0331403.PDF": {"rows": 48, "total": "2572,89"},
            "NF JULIANA.pdf": {"rows": 36, "total": "13861,40"},
            "DANFE.PDF": {"rows": 20, "total": "4965,30"},
            "6882300fb3bc32ac69997aec-doc-22-09-2025,-15-10-49-nf-2283-5542d165-0642-4b66-93c7-66cb7a1ca81b.pdf": {"rows": 12, "total": "5390,80"},
        }
        missing = [name for name in cases if not self._super_romaneios_file(name).exists()]
        if missing:
            self.skipTest(f"Files not available: {', '.join(missing)}")

        for filename, expected in cases.items():
            path = self._super_romaneios_file(filename)
            result = parse_local_romaneio_experiment(
                contents=path.read_bytes(),
                filename=path.name,
                content_type="application/pdf",
            )

            self.assertEqual(result["status"], "ok", filename)
            self.assertEqual(result["total_rows"], expected["rows"], filename)
            self.assertEqual(result["extracted_total_products"], expected["total"], filename)
            self.assertTrue(result["products_value_matches_document"], filename)

    @pytest.mark.local_files
    def test_super_romaneios_all_pdfs_parse_successfully(self) -> None:
        folder = Path.home() / "Downloads" / "SuperRomaneios" / "notas"
        if not folder.exists():
            self.skipTest(f"Folder not available: {folder}")

        files = sorted(path for path in folder.iterdir() if path.is_file() and path.suffix.lower() == ".pdf")
        self.assertTrue(files, "Expected at least one PDF in the SuperRomaneios folder.")

        for path in files:
            result = parse_local_romaneio_experiment(
                contents=path.read_bytes(),
                filename=path.name,
                content_type="application/pdf",
            )

            self.assertEqual(result["status"], "ok", path.name)
            self.assertGreater(result["total_rows"], 0, path.name)
            self.assertGreater(result["total_itens"], 0, path.name)
            self.assertGreater(result["total_quantity"], 0, path.name)

            if result.get("document_total_products") or result.get("document_total_note"):
                self.assertTrue(result["products_value_matches_document"], path.name)


if __name__ == "__main__":
    unittest.main()
