"""Prompts for romaneio / DANFE extraction via LLM.

Contract (LLM3-style, simple):
  input  = PDF text | photo | TXT  +  this task
  output = JSON only, LojaSync schema
  always LLM — no deterministic judgment of completeness
"""

from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# Fixed system role: short extractor contract (LLM3 spirit)
# ---------------------------------------------------------------------------

ROMANEIO_SYSTEM_PROMPT = """You are LojaSync's invoice/romaneio extractor for Brazilian product lists (DANFE, NF-e, supplier packing lists).

Return ONLY valid JSON. No markdown fences. No commentary.

Schema:
{
  "items": [
    {
      "codigo": "product SKU as printed",
      "descricao_original": "full description as printed",
      "nome_curto": "short name UPPERCASE, size tokens removed from the end",
      "ncm_sh": "NCM if visible else empty string",
      "quantidade": 0,
      "preco": 0.0,
      "tamanho": "size if one size on the row else empty string",
      "grades": null
    }
  ],
  "document_total_products": null,
  "document_total_note": null,
  "remessa_quantity": null
}

Rules:
- One JSON item per printed product line. Do not merge, summarize, or invent rows.
- If the same SKU appears twice, emit two items.
- preco = unit price (not line total).
- codigo = product code/SKU column. Never use NCM, CFOP, access key, or long barcodes as codigo.
- If a code cell has two lines (SKU + size token like 0502, 5240, 981P): codigo = first line; tamanho = second.
- tamanho: copy exactly as printed. Never convert numeric sizes to letters.
- If the document already shows a full size grid for one product, set grades as an object mapping size label to integer qty (e.g. {"P":2,"M":3}) and set quantidade to the sum; leave tamanho empty.
- Fill document_total_products / document_total_note / remessa_quantity when visible (Brazilian numbers ok). Else null.
- Skip headers, taxes, carrier, invoice footer that are not product rows.
- If a line is cut off or unreadable, skip it (do not guess).
""".strip()


JSON_SCHEMA_HINT = (
    '{"items":[{"codigo":"","descricao_original":"","nome_curto":"","ncm_sh":"",'
    '"quantidade":0,"preco":0,"tamanho":"","grades":null}],'
    '"document_total_products":null,"document_total_note":null,"remessa_quantity":null}'
)


def build_import_text_chunk_message(
    *,
    expected_rows: int = 0,
    chunk_index: int = 1,
    total_chunks: int = 1,
    first_code: str | None = None,
    last_code: str | None = None,
    retry: bool = False,
    filename: str | None = None,
    source_kind: str = "text",
) -> str:
    """User task for a text/PDF document (full file or one chunk)."""
    kind_label = {
        "text": "plain text (TXT/CSV)",
        "pdf_text": "embedded text extracted from a digital PDF",
        "pdf": "embedded text from a PDF",
    }.get(source_kind, "text")

    parts: list[str] = [
        "## Task",
        f"Input: {kind_label}.",
    ]
    if filename:
        parts.append(f"Source file: {filename}.")

    if total_chunks > 1:
        parts.append(
            f"You receive segment {chunk_index}/{total_chunks} of the document. "
            "Extract ALL product rows in this segment only."
        )
        if expected_rows > 0:
            parts.append(f"About {expected_rows} product row(s) are expected in this segment.")
        if first_code or last_code:
            parts.append(
                f"Anchors: first printed code ≈ {first_code or '-'}; "
                f"last printed code ≈ {last_code or '-'}."
            )
    else:
        parts.append(
            "Extract EVERY product row from the full document into the JSON schema."
        )
        if expected_rows > 0:
            parts.append(f"About {expected_rows} product row(s) are expected overall.")

    if retry:
        parts.append(
            "Previous attempt was incomplete. Be exhaustive: do not stop before the last product row."
        )

    parts.append(
        f"Return only JSON matching: {JSON_SCHEMA_HINT}. "
        "Unit price in preco; sizes in tamanho or grades; no markdown."
    )
    return " ".join(parts)


def build_romaneio_image_message(
    images: list[dict[str, Any]],
    *,
    filename: str | None = None,
    page_index: int | None = None,
    page_total: int | None = None,
) -> str:
    names = [str(image.get("name") or "").lower() for image in (images or []) if isinstance(image, dict)]
    is_crop = any("#slice" in name for name in names)
    file_hint = f" File: {filename}." if filename else ""
    page_hint = ""
    if page_index and page_total:
        page_hint = f" Visual page/batch {page_index} of {page_total}."
    elif page_index:
        page_hint = f" Visual page/batch {page_index}."

    if is_crop:
        return (
            f"## Task{file_hint}{page_hint} "
            "Input: vertical crop of a fiscal product table image. "
            "Extract ONLY fully visible product rows in this crop. Skip rows cut by the crop edge. "
            f"Return only JSON ({JSON_SCHEMA_HINT}). preco = unit price; sizes in tamanho or grades."
        )

    return (
        f"## Task{file_hint}{page_hint} "
        "Input: image of a Brazilian DANFE/NF-e/romaneio product table. "
        "Read product columns (code, description, NCM, qty, unit price, etc.). "
        "Extract every visible product row. "
        f"Return only JSON ({JSON_SCHEMA_HINT}). preco = UNIT price (not line total). "
        "If a code cell has two lines, the second is tamanho. "
        "Full size grids go into grades. Do not merge rows."
    )


def build_kimi_user_prompt(
    *,
    message: str,
    documents: list[dict[str, Any]],
    mode: str = "romaneio_extractor",
) -> str:
    """Assemble user message: task + optional document text."""
    parts: list[str] = []
    task = str(message or "").strip()
    if task:
        parts.append(task)
    else:
        parts.append(
            f"## Task\nExtract products from the attached material. "
            f"Return only JSON ({JSON_SCHEMA_HINT})."
        )

    if mode == "grade_extractor":
        parts.append(
            "Focus: detect sizes/grades per product when the note lists a grade grid. "
            "Still return the items JSON schema (use grades object when appropriate)."
        )
    elif mode and mode not in {"romaneio_extractor", "grade_extractor", "default"}:
        parts.append(f"Operational mode: {mode}.")

    for index, document in enumerate(documents or [], start=1):
        if not isinstance(document, dict):
            continue
        name = str(document.get("name") or f"documento_{index}").strip()
        content = str(document.get("content") or "").strip()
        if not content:
            continue
        parts.append(f"## Document {index}: {name}\n{content}")

    parts.append("## Final reminder\nRespond with the JSON object only. No markdown, no explanation.")
    return "\n\n".join(parts).strip()
