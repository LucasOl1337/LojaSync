from __future__ import annotations

from unittest.mock import patch

from app.application.imports.pdf_text import extract_pdf_text_candidates


def _reader_with_pages(*texts: str):
    class Reader:
        def __init__(self, _stream):
            self.pages = [Page(text) for text in texts]

    class Page:
        def __init__(self, text: str):
            self._text = text

        def extract_text(self) -> str:
            return self._text

    return Reader


def test_extract_pdf_text_candidates_returns_empty_for_empty_content() -> None:
    assert extract_pdf_text_candidates(b"") == []


def test_extract_pdf_text_candidates_preserves_reader_order_and_deduplicates_text() -> None:
    first_reader = _reader_with_pages("produto 1", "produto 2")
    second_reader = _reader_with_pages("produto 1\n\nproduto 2")

    with (
        patch("app.application.imports.pdf_text._load_pypdf2_reader", return_value=first_reader),
        patch("app.application.imports.pdf_text._load_pypdf_reader", return_value=second_reader),
    ):
        candidates = extract_pdf_text_candidates(b"%PDF")

    assert [(candidate.reader, candidate.text, candidate.page_count) for candidate in candidates] == [
        ("PyPDF2", "produto 1\n\nproduto 2", 2)
    ]


def test_extract_pdf_text_candidates_falls_back_to_second_reader() -> None:
    with (
        patch("app.application.imports.pdf_text._load_pypdf2_reader", return_value=None),
        patch("app.application.imports.pdf_text._load_pypdf_reader", return_value=_reader_with_pages("ok")),
    ):
        candidates = extract_pdf_text_candidates(b"%PDF")

    assert [(candidate.reader, candidate.text, candidate.page_count) for candidate in candidates] == [
        ("pypdf", "ok", 1)
    ]
