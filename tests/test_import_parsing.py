from __future__ import annotations

import unittest

from app.application.imports.parsing import (
    filter_suspect_records,
    parse_candidate_content,
    split_text_chunks,
)
from app.domain.products.entities import Product


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


if __name__ == "__main__":
    unittest.main()
