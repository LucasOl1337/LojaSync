"""Evidence-first romaneio extraction helpers.

Deterministic document evidence is extracted without the LLM. Vision/LLM
candidates are then reconciled against anchors (remessa quantity, printed
totals, structured row counts). Incomplete non-empty results can trigger
targeted recovery instead of being persisted as a silent success.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from app.application.imports.parsing import (
    analyze_parsed_document,
    decode_text_content,
    extract_structured_invoice_row_lines,
)
from app.domain.products.entities import Product
from app.domain.products.money import parse_price_decimal

# Quantities above this per single line are treated as implausible misreads
# of unit/QUANT columns (historical SuperRomaneios over-extraction pattern).
DEFAULT_IMPLAUSIBLE_QTY = 5000

PIPELINE_EVIDENCE = "evidence"
PIPELINE_LEGACY = "legacy"


def import_pipeline_mode() -> str:
    raw = str(os.getenv("LOJASYNC_IMPORT_PIPELINE") or os.getenv("IMPORT_PIPELINE") or "").strip().lower()
    if raw in {PIPELINE_LEGACY, "classic", "old"}:
        return PIPELINE_LEGACY
    return PIPELINE_EVIDENCE


def use_evidence_pipeline() -> bool:
    return import_pipeline_mode() == PIPELINE_EVIDENCE


@dataclass(frozen=True, slots=True)
class DocumentEvidence:
    """Ground-truth-ish signals extracted from the source file without LLM."""

    text: str
    page_hint: int
    structured_row_count: int
    remessa_quantity: int | None
    document_total_products: str | None
    document_total_note: str | None
    source: str
    warnings: list[str] = field(default_factory=list)

    @property
    def has_quantity_anchor(self) -> bool:
        return self.remessa_quantity is not None

    @property
    def has_total_anchor(self) -> bool:
        return bool(self.document_total_products or self.document_total_note)

    @property
    def has_any_anchor(self) -> bool:
        return self.has_quantity_anchor or self.has_total_anchor or self.structured_row_count > 0

    def metrics(self) -> dict[str, Any]:
        return {
            "evidence_source": self.source,
            "evidence_text_chars": len(self.text or ""),
            "evidence_page_hint": int(self.page_hint or 0),
            "evidence_structured_row_count": int(self.structured_row_count or 0),
            "evidence_remessa_quantity": self.remessa_quantity,
            "evidence_document_total_products": self.document_total_products,
            "evidence_document_total_note": self.document_total_note,
            "evidence_has_quantity_anchor": self.has_quantity_anchor,
            "evidence_has_total_anchor": self.has_total_anchor,
            "import_pipeline": import_pipeline_mode(),
        }


@dataclass(frozen=True, slots=True)
class CompletenessAssessment:
    """Compare extracted products against document evidence."""

    item_count: int
    total_quantity: int
    expected_quantity: int | None
    expected_row_count: int | None
    quantity_matches: bool | None
    row_count_matches: bool | None
    products_value_matches: bool | None
    incomplete: bool
    needs_recovery: bool
    implausible_quantities: list[dict[str, Any]]
    reasons: list[str]
    score: int
    metrics: dict[str, Any]


@dataclass(frozen=True, slots=True)
class ImportOutcome:
    """Explicit product outcome for UI/metrics (backward-compatible statuses)."""

    outcome: str  # approved | needs_review | rejected
    result_status: str  # ok | needs_review | rejected
    final_validation_status: str  # approved | unverified | rejected
    warnings: list[str]
    metrics: dict[str, Any]


def _money_to_display(value: Decimal | None) -> str | None:
    if value is None:
        return None
    quantized = value.quantize(Decimal("0.01"))
    text = f"{quantized:.2f}".replace(".", ",")
    return text


def extract_document_evidence(
    contents: bytes,
    filename: str,
    content_type: str | None,
) -> DocumentEvidence:
    """Extract deterministic anchors/text from the uploaded file."""
    text, warnings = decode_text_content(contents, filename or "romaneio", content_type)
    text = (text or "").strip()
    structured_rows = extract_structured_invoice_row_lines(text)
    analysis = analyze_parsed_document(text, [])
    analysis_metrics = analysis.get("metrics") if isinstance(analysis.get("metrics"), dict) else {}

    remessa = analysis_metrics.get("remessa_quantity")
    try:
        remessa_quantity = int(remessa) if remessa is not None else None
    except Exception:
        remessa_quantity = None

    total_products = analysis_metrics.get("document_total_products")
    total_note = analysis_metrics.get("document_total_note")
    if total_products is not None and not isinstance(total_products, str):
        total_products = _money_to_display(parse_price_decimal(total_products)) or str(total_products)
    if total_note is not None and not isinstance(total_note, str):
        total_note = _money_to_display(parse_price_decimal(total_note)) or str(total_note)

    page_hint = 0
    if text:
        # Lightweight page marker count for multi-page PDFs with form-feed / page labels.
        page_markers = len(re.findall(r"(?im)^\s*(?:página|pagina|page)\s+\d+", text))
        form_feeds = text.count("\x0c")
        page_hint = max(page_markers, form_feeds, 1 if text else 0)

    source = "local_text" if text else "empty"
    lower_name = (filename or "").lower()
    lower_type = (content_type or "").lower()
    if lower_name.endswith(".pdf") or "pdf" in lower_type:
        source = "pdf_text" if text else "pdf_empty"

    return DocumentEvidence(
        text=text,
        page_hint=page_hint,
        structured_row_count=len(structured_rows),
        remessa_quantity=remessa_quantity if remessa_quantity and remessa_quantity > 0 else None,
        document_total_products=str(total_products).strip() if total_products else None,
        document_total_note=str(total_note).strip() if total_note else None,
        source=source,
        warnings=[str(item) for item in (warnings or []) if str(item).strip()],
    )


def products_total_quantity(items: list[Product]) -> int:
    total = 0
    for item in items or []:
        try:
            total += max(int(getattr(item, "quantidade", 0) or 0), 0)
        except Exception:
            continue
    return total


def product_fingerprint(item: Product) -> tuple[str, str, int, str]:
    grades = getattr(item, "grades", None) or []
    size_bits: list[str] = []
    for grade in grades:
        if isinstance(grade, dict):
            size_bits.append(f"{grade.get('tamanho')}:{grade.get('quantidade')}")
        else:
            size_bits.append(f"{getattr(grade, 'tamanho', '')}:{getattr(grade, 'quantidade', '')}")
    size_key = ",".join(size_bits)
    return (
        str(getattr(item, "codigo", "") or "").strip().upper(),
        str(getattr(item, "nome", "") or "").strip().upper(),
        max(int(getattr(item, "quantidade", 0) or 0), 0),
        f"{str(getattr(item, 'preco', '') or '').strip()}|{size_key}",
    )


def deduplicate_products(items: list[Product]) -> list[Product]:
    """Drop exact multi-pass duplicates while preserving intentional repeated rows.

    Two rows with the same code/name but different quantity/price/size are kept
    (fiscal tables often print repeated SKUs). Only bitwise-identical extractions
    from overlapping recovery passes are collapsed.
    """
    seen: set[tuple[str, str, int, str]] = set()
    result: list[Product] = []
    for item in items or []:
        key = product_fingerprint(item)
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def find_implausible_quantities(
    items: list[Product],
    *,
    max_unit_qty: int = DEFAULT_IMPLAUSIBLE_QTY,
) -> list[dict[str, Any]]:
    flagged: list[dict[str, Any]] = []
    limit = max(int(max_unit_qty or DEFAULT_IMPLAUSIBLE_QTY), 1)
    for item in items or []:
        try:
            qty = int(getattr(item, "quantidade", 0) or 0)
        except Exception:
            continue
        if qty > limit:
            flagged.append(
                {
                    "codigo": str(getattr(item, "codigo", "") or ""),
                    "nome": str(getattr(item, "nome", "") or ""),
                    "quantidade": qty,
                }
            )
    return flagged


def assess_completeness(
    products: list[Product],
    evidence: DocumentEvidence | None,
    *,
    max_unit_qty: int = DEFAULT_IMPLAUSIBLE_QTY,
) -> CompletenessAssessment:
    items = list(products or [])
    item_count = len(items)
    total_quantity = products_total_quantity(items)
    expected_quantity = evidence.remessa_quantity if evidence else None
    expected_row_count = (
        evidence.structured_row_count if evidence and evidence.structured_row_count > 0 else None
    )

    quantity_matches: bool | None = None
    if expected_quantity is not None:
        quantity_matches = total_quantity == expected_quantity

    row_count_matches: bool | None = None
    if expected_row_count is not None and expected_row_count > 0:
        # Local structured rows may group multi-size lines; treat row count as a
        # lower-bound hint when item_count is smaller, not a hard equality.
        row_count_matches = item_count >= max(1, int(expected_row_count * 0.5)) and (
            item_count <= expected_row_count * 3
        )

    products_value_matches: bool | None = None
    if evidence and evidence.text and items:
        analysis = analyze_parsed_document(evidence.text, items)
        analysis_metrics = analysis.get("metrics") if isinstance(analysis.get("metrics"), dict) else {}
        if analysis_metrics.get("document_total_products") is not None or analysis_metrics.get(
            "document_total_note"
        ) is not None:
            products_value_matches = bool(analysis_metrics.get("products_value_matches_document"))

    implausible = find_implausible_quantities(items, max_unit_qty=max_unit_qty)
    reasons: list[str] = []
    incomplete = False

    if item_count <= 0:
        incomplete = True
        reasons.append("no_items")
    if quantity_matches is False:
        incomplete = True
        reasons.append(
            f"quantity_mismatch:{total_quantity}/{expected_quantity}"
            if expected_quantity is not None
            else "quantity_mismatch"
        )
    if products_value_matches is False:
        incomplete = True
        reasons.append("product_total_mismatch")
    if row_count_matches is False and expected_row_count is not None and item_count > 0:
        # Soft signal: only mark incomplete when we also lack quantity match confidence
        if quantity_matches is not True:
            incomplete = True
            reasons.append(f"row_coverage_low:{item_count}/{expected_row_count}")
    if implausible:
        incomplete = True
        reasons.append(f"implausible_quantity_count:{len(implausible)}")

    # Score: higher is better. Used to pick between full-page and recovery sets.
    score = item_count * 10 + total_quantity
    if quantity_matches is True:
        score += 1000
    if products_value_matches is True:
        score += 500
    if implausible:
        score -= 2000 + sum(int(item["quantidade"]) for item in implausible)
    if quantity_matches is False and expected_quantity is not None:
        score -= abs(total_quantity - expected_quantity) * 20

    needs_recovery = incomplete and (
        item_count == 0
        or quantity_matches is False
        or products_value_matches is False
        or bool(implausible)
        or (expected_row_count is not None and item_count > 0 and item_count < expected_row_count)
    )

    metrics = {
        "completeness_item_count": item_count,
        "completeness_total_quantity": total_quantity,
        "completeness_expected_quantity": expected_quantity,
        "completeness_expected_row_count": expected_row_count,
        "completeness_quantity_matches": quantity_matches,
        "completeness_row_count_matches": row_count_matches,
        "completeness_products_value_matches": products_value_matches,
        "completeness_incomplete": incomplete,
        "completeness_needs_recovery": needs_recovery,
        "completeness_implausible_count": len(implausible),
        "completeness_reasons": list(reasons),
        "completeness_score": score,
    }

    return CompletenessAssessment(
        item_count=item_count,
        total_quantity=total_quantity,
        expected_quantity=expected_quantity,
        expected_row_count=expected_row_count,
        quantity_matches=quantity_matches,
        row_count_matches=row_count_matches,
        products_value_matches=products_value_matches,
        incomplete=incomplete,
        needs_recovery=needs_recovery,
        implausible_quantities=implausible,
        reasons=reasons,
        score=score,
        metrics=metrics,
    )


def choose_better_candidate_set(
    primary: list[Product],
    recovery: list[Product],
    evidence: DocumentEvidence | None,
) -> tuple[list[Product], str, CompletenessAssessment]:
    """Pick the product set closer to document evidence after recovery."""
    primary_items = deduplicate_products(primary)
    recovery_items = deduplicate_products(recovery)
    primary_assessment = assess_completeness(primary_items, evidence)
    recovery_assessment = assess_completeness(recovery_items, evidence)

    if recovery_assessment.score > primary_assessment.score:
        return recovery_items, "recovery", recovery_assessment
    if recovery_assessment.score == primary_assessment.score and recovery_assessment.item_count > primary_assessment.item_count:
        return recovery_items, "recovery", recovery_assessment

    # Merge unique rows when recovery did not clearly win but added coverage.
    if recovery_items and primary_items:
        merged = deduplicate_products([*primary_items, *recovery_items])
        merged_assessment = assess_completeness(merged, evidence)
        if merged_assessment.score > primary_assessment.score:
            return merged, "merged", merged_assessment

    return primary_items, "primary", primary_assessment


def apply_evidence_to_metrics(
    metrics: dict[str, Any],
    evidence: DocumentEvidence,
    products: list[Product],
) -> dict[str, Any]:
    """Merge evidence anchors into job metrics for final validation."""
    metrics.update(evidence.metrics())

    analysis_text = evidence.text or str(metrics.get("selected_text") or "")
    analysis = analyze_parsed_document(analysis_text, products) if (analysis_text or products) else {
        "metrics": {},
        "warnings": [],
    }
    analysis_metrics = analysis.get("metrics") if isinstance(analysis.get("metrics"), dict) else {}

    # Prefer evidence anchors when LLM response text has none.
    if analysis_metrics.get("remessa_quantity") is None and evidence.remessa_quantity is not None:
        analysis_metrics["remessa_quantity"] = evidence.remessa_quantity
        extracted_qty = products_total_quantity(products)
        analysis_metrics["quantity_matches_remessa"] = extracted_qty == evidence.remessa_quantity
    if not analysis_metrics.get("document_total_products") and evidence.document_total_products:
        analysis_metrics["document_total_products"] = evidence.document_total_products
    if not analysis_metrics.get("document_total_note") and evidence.document_total_note:
        analysis_metrics["document_total_note"] = evidence.document_total_note

    if products and evidence.text:
        reanalysis = analyze_parsed_document(evidence.text, products)
        re_metrics = reanalysis.get("metrics") if isinstance(reanalysis.get("metrics"), dict) else {}
        if re_metrics.get("products_value_matches_document") is not None:
            analysis_metrics["products_value_matches_document"] = re_metrics.get(
                "products_value_matches_document"
            )
        if re_metrics.get("extracted_total_products") is not None:
            analysis_metrics["extracted_total_products"] = re_metrics.get("extracted_total_products")
        if re_metrics.get("quantity_matches_remessa") is not None:
            analysis_metrics["quantity_matches_remessa"] = re_metrics.get("quantity_matches_remessa")
        if re_metrics.get("remessa_quantity") is not None:
            analysis_metrics["remessa_quantity"] = re_metrics.get("remessa_quantity")

    for key in (
        "remessa_quantity",
        "quantity_matches_remessa",
        "document_total_products",
        "document_total_note",
        "extracted_total_products",
        "products_value_matches_document",
    ):
        if key in analysis_metrics:
            metrics[key] = analysis_metrics[key]

    return metrics


def build_import_outcome(
    *,
    validation: dict[str, Any],
    completeness: CompletenessAssessment | None = None,
) -> ImportOutcome:
    """Map validation + completeness into an explicit import outcome."""
    if validation.get("rejected"):
        return ImportOutcome(
            outcome="rejected",
            result_status="rejected",
            final_validation_status="rejected",
            warnings=[],
            metrics={
                "import_outcome": "rejected",
                "import_needs_review": False,
            },
        )
    if validation.get("approved"):
        extra_warnings: list[str] = []
        if completeness and completeness.implausible_quantities:
            extra_warnings.append(
                "Quantidades implausíveis detectadas após aprovação; revise o catálogo antes de enviar ao ERP."
            )
            return ImportOutcome(
                outcome="needs_review",
                result_status="needs_review",
                final_validation_status="approved",
                warnings=extra_warnings,
                metrics={
                    "import_outcome": "needs_review",
                    "import_needs_review": True,
                },
            )
        return ImportOutcome(
            outcome="approved",
            result_status="ok",
            final_validation_status="approved",
            warnings=[],
            metrics={
                "import_outcome": "approved",
                "import_needs_review": False,
            },
        )

    # Unverified: items present, no anchors. Persist but mark needs_review explicitly.
    warning = (
        "Importação concluída SEM validação de totais/remessa impressos. "
        "Revise quantidades e códigos antes de confiar no resultado — o status não é aprovação automática."
    )
    if completeness and completeness.incomplete:
        warning = (
            "Importação incompleta ou sem âncoras de validação. "
            "Itens foram salvos para revisão manual; confira quantidades e totais da nota."
        )
    return ImportOutcome(
        outcome="needs_review",
        result_status="needs_review",
        final_validation_status="unverified",
        warnings=[warning],
        metrics={
            "import_outcome": "needs_review",
            "import_needs_review": True,
        },
    )


def recovery_slice_count(*, configured: int | None = None) -> int:
    if configured is not None:
        return max(int(configured), 2)
    try:
        raw = str(os.getenv("LOJASYNC_RECOVERY_PAGE_SLICES") or os.getenv("LLM_ROMANEIO_PDF_PAGE_VERTICAL_SLICES") or "2").strip()
        return max(int(raw or "2"), 2)
    except Exception:
        return 2


def recovery_overlap_ratio() -> float:
    try:
        raw = str(os.getenv("LOJASYNC_RECOVERY_SLICE_OVERLAP") or "0.12").strip()
        value = float(raw or "0.12")
    except Exception:
        value = 0.12
    return min(max(value, 0.0), 0.4)


__all__ = [
    "CompletenessAssessment",
    "DocumentEvidence",
    "ImportOutcome",
    "PIPELINE_EVIDENCE",
    "PIPELINE_LEGACY",
    "apply_evidence_to_metrics",
    "assess_completeness",
    "build_import_outcome",
    "choose_better_candidate_set",
    "deduplicate_products",
    "extract_document_evidence",
    "find_implausible_quantities",
    "import_pipeline_mode",
    "product_fingerprint",
    "products_total_quantity",
    "recovery_overlap_ratio",
    "recovery_slice_count",
    "use_evidence_pipeline",
]
