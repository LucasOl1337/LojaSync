"""Dump raw OCR output for image invoices."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.application.imports.local_experiment import _ocr_image_bytes

NOTAS = Path("C:/Users/user/Downloads/notas/notas")

for name in sys.argv[1:] or ["WhatsApp Image 2026-03-30 at 08.59.40.jpeg", "nota1.jpeg"]:
    path = NOTAS / name
    contents = path.read_bytes()
    suffix = path.suffix or ".jpg"
    pages = _ocr_image_bytes(contents, suffix)
    print("=" * 70)
    print(f"FILE: {name} -- pages={len(pages)}")
    for i, page in enumerate(pages):
        print(f"--- page {i} width={page.width} height={page.height} lines={len(page.lines)}")
        lines = sorted(page.lines, key=lambda it: (int(it.get("y") or 0), int(it.get("x") or 0)))
        for ln in lines:
            print(f"  y={int(ln.get('y') or 0):5d} x={int(ln.get('x') or 0):5d}  {ln.get('text')!r}")
