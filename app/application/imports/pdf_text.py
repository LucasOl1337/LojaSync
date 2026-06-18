from __future__ import annotations

import io
import warnings
from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True, slots=True)
class PdfTextCandidate:
    text: str
    page_count: int
    reader: str


def extract_pdf_text_candidates(contents: bytes) -> list[PdfTextCandidate]:
    if not contents:
        return []

    candidates: list[PdfTextCandidate] = []
    seen: set[str] = set()
    for reader_name, reader_loader in (
        ("PyPDF2", _load_pypdf2_reader),
        ("pypdf", _load_pypdf_reader),
    ):
        reader_cls = reader_loader()
        if reader_cls is None:
            continue
        text, page_count = _read_pdf_text(contents, reader_cls)
        normalized_key = text.strip()
        if not normalized_key or normalized_key in seen:
            continue
        candidates.append(PdfTextCandidate(text=normalized_key, page_count=page_count, reader=reader_name))
        seen.add(normalized_key)
    return candidates


def _load_pypdf2_reader() -> Any | None:
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            from PyPDF2 import PdfReader  # type: ignore

        return PdfReader
    except Exception:
        return None


def _load_pypdf_reader() -> Any | None:
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            from pypdf import PdfReader  # type: ignore

        return PdfReader
    except Exception:
        return None


def _read_pdf_text(contents: bytes, reader_cls: Callable[..., Any]) -> tuple[str, int]:
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            reader = reader_cls(io.BytesIO(contents))
            parts: list[str] = []
            for page in reader.pages:
                text = page.extract_text() or ""
                if text.strip():
                    parts.append(text)
            return "\n\n".join(parts).strip(), len(reader.pages)
    except Exception:
        return "", 0
