"""Ad-hoc harness for validating the local romaneio parser against real invoices."""
from __future__ import annotations

import json
import mimetypes
import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.application.imports.local_experiment import (
    _parse_decimal,
    parse_local_romaneio_experiment,
)

NOTAS_DIR = Path("C:/Users/user/Downloads/notas/notas")
TARGETS = [
    "2866.pdf",
    "NF-e_453073.pdf",
    "NF-e_467623.pdf",
    "NF-e_862303.pdf",
    "WhatsApp Image 2026-03-30 at 08.59.40.jpeg",
    "nota1.jpeg",
]


def _fmt(value) -> str:
    if value is None:
        return "-"
    return str(value)


def _check_item_math(item: dict) -> str | None:
    qty = int(item.get("quantidade") or 0)
    preco = _parse_decimal(item.get("preco"))
    total = _parse_decimal(item.get("valor_total"))
    if qty <= 0:
        return f"qty<=0"
    if preco is None:
        return f"preco is None"
    if total is None:
        return None  # no valor_total to check
    expected = preco * Decimal(qty)
    # Accept small rounding tolerance proportional to qty (e.g. R$0.01 per unit).
    tolerance = Decimal("0.02") * Decimal(max(qty, 1)) + Decimal("0.05")
    if abs(expected - total) > tolerance:
        return f"qty*preco({expected}) != valor_total({total}) [tol={tolerance}]"
    return None


def run_one(path: Path) -> dict:
    contents = path.read_bytes()
    content_type, _ = mimetypes.guess_type(str(path))
    result = parse_local_romaneio_experiment(
        contents=contents,
        filename=path.name,
        content_type=content_type,
    )

    item_errors: list[str] = []
    for idx, item in enumerate(result.get("items") or [], start=1):
        err = _check_item_math(item)
        if err:
            item_errors.append(f"item#{idx} {item.get('codigo')}: {err}")

    extracted_products = _parse_decimal(result.get("extracted_total_products")) or Decimal("0")
    doc_products = _parse_decimal(result.get("document_total_products"))
    doc_note = _parse_decimal(result.get("document_total_note"))
    # Soma das linhas extraídas deve bater com "VALOR TOTAL DOS PRODUTOS"
    # (bruto) OU "VALOR TOTAL DA NOTA" (líquido), pois alguns fornecedores
    # emitem linhas com valor bruto e desconto rateado, outros já emitem líquido.
    total_match_ok = False
    total_ref = None
    if doc_note is not None and abs(extracted_products - doc_note) <= Decimal("0.05"):
        total_match_ok = True
        total_ref = doc_note
    elif doc_products is not None and abs(extracted_products - doc_products) <= Decimal("0.05"):
        total_match_ok = True
        total_ref = doc_products
    elif doc_note is None and doc_products is None:
        total_match_ok = True  # no document total to compare against
        total_ref = None

    remessa_qty = result.get("remessa_quantity")
    total_qty = int(result.get("total_quantity") or 0)
    if remessa_qty is None:
        remessa_match_ok = True  # no remessa info to validate
    else:
        remessa_match_ok = total_qty == int(remessa_qty)

    rows_ok = int(result.get("total_rows") or 0) > 0

    ok = rows_ok and total_match_ok and remessa_match_ok and not item_errors

    return {
        "file": path.name,
        "ok": ok,
        "status": result.get("status"),
        "total_rows": result.get("total_rows"),
        "total_itens": result.get("total_itens"),
        "total_quantity": result.get("total_quantity"),
        "remessa_quantity": remessa_qty,
        "remessa_match_ok": remessa_match_ok,
        "document_total_products": _fmt(result.get("document_total_products")),
        "document_total_note": _fmt(result.get("document_total_note")),
        "extracted_total_products": _fmt(result.get("extracted_total_products")),
        "total_match_ok": total_match_ok,
        "total_ref": str(total_ref) if total_ref is not None else None,
        "warnings": result.get("warnings") or [],
        "item_errors": item_errors,
        "items": result.get("items") or [],
        "metrics": result.get("metrics") or {},
    }


def main() -> int:
    if len(sys.argv) > 1 and not sys.argv[1].startswith("--"):
        names = [arg for arg in sys.argv[1:] if not arg.startswith("--")]
    else:
        names = TARGETS
    failures = 0
    summary_rows: list[str] = []
    dump_all = "--dump" in sys.argv
    dumps = []
    for name in names:
        path = NOTAS_DIR / name
        if not path.exists():
            print(f"[MISS] {name} -- not found")
            failures += 1
            continue
        try:
            info = run_one(path)
        except Exception as exc:
            import traceback
            print(f"[ERR ] {name} -- {exc}")
            traceback.print_exc()
            failures += 1
            continue
        ok = info["ok"]
        tag = "[OK  ]" if ok else "[FAIL]"
        if not ok:
            failures += 1
        summary_rows.append(
            f"{tag} {name}  rows={info['total_rows']} qty={info['total_quantity']}/{info['remessa_quantity']}"
            f"  extracted={info['extracted_total_products']}  doc_prod={info['document_total_products']}  doc_nota={info['document_total_note']}"
        )
        if not ok:
            summary_rows.append(f"       status={info['status']}  total_match_ok={info['total_match_ok']} remessa_match_ok={info['remessa_match_ok']}")
            for warn in info["warnings"]:
                summary_rows.append(f"       warn: {warn}")
            for err in info["item_errors"][:5]:
                summary_rows.append(f"       {err}")
            if len(info["item_errors"]) > 5:
                summary_rows.append(f"       ... {len(info['item_errors']) - 5} more item errors")
            if not info["items"]:
                summary_rows.append(f"       no items extracted; metrics={info['metrics']}")
        if dump_all:
            dumps.append({k: v for k, v in info.items() if k != "items"})

    print("\n".join(summary_rows))
    print(f"\nTotal failures: {failures}/{len(names)}")
    if dump_all:
        Path("tests/_invoice_harness_last.json").write_text(
            json.dumps(dumps, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
    return failures


if __name__ == "__main__":
    raise SystemExit(main())
