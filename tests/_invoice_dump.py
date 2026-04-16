"""Dump extracted text from invoices for inspection."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.application.imports.local_experiment import _extract_pdf_text

NOTAS_DIR = Path("C:/Users/user/Downloads/notas/notas")

for name in ["NF-e_453073.pdf", "NF-e_467623.pdf", "NF-e_862303.pdf", "2866.pdf"]:
    path = NOTAS_DIR / name
    if not path.exists():
        continue
    text, pages = _extract_pdf_text(path.read_bytes())
    print("=" * 80)
    print(f"FILE: {name}  pages={pages}  chars={len(text)}")
    print("=" * 80)
    print(text[:6000])
    print("\n... (truncated) ...\n")
    tail = text[-3000:] if len(text) > 3000 else ""
    if tail:
        print("### TAIL:")
        print(tail)
    print()
