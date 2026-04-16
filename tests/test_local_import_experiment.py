from __future__ import annotations

import unittest
from pathlib import Path

from app.application.imports.local_experiment import parse_local_romaneio_experiment


class LocalImportExperimentTests(unittest.TestCase):
    def _super_romaneios_file(self, filename: str) -> Path:
        return Path.home() / "Downloads" / "SuperRomaneios" / "notas" / filename

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
