from __future__ import annotations

import logging
import re
from collections import Counter
from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable

from app.domain.brands.repository import BrandRepository
from app.domain.metrics.entities import Metrics
from app.domain.products.entities import Product, calculate_sale_price, format_price, parse_non_negative_price, parse_price
from app.domain.products.grade_utils import (
    canonicalize_product_name,
    detect_size_from_name,
    extract_code_size_candidate,
    normalize_grade_label,
    normalize_grades_map,
    sort_grade_items,
    strip_size_suffix,
)
from app.domain.products.money import parse_price_decimal
from app.domain.products.repository import ProductRepository
from app.infrastructure.persistence.files.settings_files import MarginSettingsStore, MetricsStore
from app.infrastructure.persistence.files.undo_history import InMemoryUndoRedoHistoryStore, UndoRedoHistoryState
from app.shared.logging.setup import log_event

logger = logging.getLogger(__name__)


class ProductSetCompositionConflictError(ValueError):
    """Raised when creating a set would leave variant totals above stock."""


@dataclass(slots=True)
class TotalsSnapshot:
    quantidade: int
    custo: float
    venda: float


@dataclass(slots=True)
class ProductsSummary:
    atual: TotalsSnapshot
    historico: TotalsSnapshot
    metrics: Metrics


AVERAGE_INVOICE_ITEMS = 50
MANUAL_MINUTES_PER_INVOICE = 90
AUTOMATED_MINUTES_PER_INVOICE = 20
SECONDS_SAVED_PER_INVOICE = (MANUAL_MINUTES_PER_INVOICE - AUTOMATED_MINUTES_PER_INVOICE) * 60
IMPORT_PRICE_MERGE_TOLERANCE = Decimal("0.01")
MAX_UNDO_HISTORY = 50


class ProductService:
    def __init__(
        self,
        products: ProductRepository,
        brands: BrandRepository,
        margin_store: MarginSettingsStore,
        metrics_store: MetricsStore,
        undo_history_store: InMemoryUndoRedoHistoryStore | None = None,
    ) -> None:
        self._products = products
        self._brands = brands
        self._margin_store = margin_store
        self._metrics_store = metrics_store
        self._undo_history_store = undo_history_store or InMemoryUndoRedoHistoryStore(MAX_UNDO_HISTORY)

    def list_products(self) -> list[Product]:
        return [Product.from_dict(item.to_dict()) for item in self._products.list_active()]

    def create_product(self, product: Product) -> Product:
        occupied_keys = {item.ordering_key() for item in self._products.list_active()}
        created = self._create_product_with_occupied_keys(product, occupied_keys)
        log_event(
            logger,
            logging.INFO,
            "product_created",
            "product created",
            ordering_key=created.ordering_key(),
            source_type=created.source_type or "manual",
            quantity=int(created.quantidade or 0),
        )
        return created

    def _create_product_with_occupied_keys(self, product: Product, occupied_keys: set[str]) -> Product:
        margin = self.get_default_margin()
        normalized = product.normalize(margin=margin)
        if not normalized.source_type:
            normalized.source_type = "manual"
        if normalized.import_batch_id is None:
            normalized.pending_grade_import = False
        self._ensure_unique_ordering_key(normalized, occupied_keys)
        self._products.append_active(normalized)
        occupied_keys.add(normalized.ordering_key())
        self._sync_brand(normalized.marca)
        return normalized

    def create_many(self, products: list[Product]) -> list[Product]:
        occupied_keys = {item.ordering_key() for item in self._products.list_active()}
        created: list[Product] = []
        for product in products:
            created.append(self._create_product_with_occupied_keys(product, occupied_keys))
        if created:
            log_event(
                logger,
                logging.INFO,
                "products_created_batch",
                "products created batch",
                count=len(created),
                total_quantity=sum(int(item.quantidade or 0) for item in created),
                source_types=sorted({item.source_type or "manual" for item in created}),
            )
        return created

    def restore_snapshot(self, products: list[Product]) -> int:
        current_items = self._products.list_active()
        timestamp_lookup: dict[str, str] = {}
        for item in current_items:
            timestamp = item.timestamp.isoformat()
            if timestamp and timestamp not in timestamp_lookup:
                timestamp_lookup[timestamp] = item.ordering_key()

        restored: list[Product] = []
        for item in products:
            cloned = Product.from_dict(item.to_dict())
            if not cloned.ordering_key_value:
                preserved_key = timestamp_lookup.get(cloned.timestamp.isoformat())
                if preserved_key:
                    cloned.ordering_key_value = preserved_key
            restored.append(cloned)
        self._products.replace_active(restored)
        self._merge_brands_from_items(restored)
        log_event(
            logger,
            logging.INFO,
            "products_snapshot_restored",
            "products snapshot restored",
            count=len(restored),
            total_quantity=sum(int(item.quantidade or 0) for item in restored),
        )
        return len(restored)

    def get_undo_redo_history_state(self) -> UndoRedoHistoryState:
        return self._undo_history_store.state()

    def record_undo_snapshot(self, *, clear_redo: bool = True) -> UndoRedoHistoryState:
        return self._undo_history_store.record_undo_snapshot(self.list_products(), clear_redo=clear_redo)

    def undo_last_snapshot(self) -> tuple[bool, int, UndoRedoHistoryState]:
        snapshot, state = self._undo_history_store.undo(self.list_products())
        if snapshot is None:
            return False, 0, state
        total = self.restore_snapshot(snapshot)
        return True, total, state

    def redo_last_snapshot(self) -> tuple[bool, int, UndoRedoHistoryState]:
        snapshot, state = self._undo_history_store.redo(self.list_products())
        if snapshot is None:
            return False, 0, state
        total = self.restore_snapshot(snapshot)
        return True, total, state

    def delete_product(self, ordering_key: str) -> bool:
        items = self.list_products()
        filtered = [item for item in items if item.ordering_key() != ordering_key]
        if len(filtered) == len(items):
            return False
        self._products.replace_active(filtered)
        log_event(
            logger,
            logging.INFO,
            "product_deleted",
            "product deleted",
            ordering_key=ordering_key,
            remaining=len(filtered),
        )
        return True

    def clear_products(self) -> int:
        items = self.list_products()
        self._products.replace_active([])
        if items:
            log_event(
                logger,
                logging.INFO,
                "products_cleared",
                "products cleared",
                removed=len(items),
            )
        return len(items)

    def update_product(self, ordering_key: str, changes: dict[str, object]) -> Product | None:
        margin = self.get_default_margin()
        items = self.list_products()
        updated: Product | None = None
        for item in items:
            if item.ordering_key() != ordering_key:
                continue
            for field_name, value in changes.items():
                if not hasattr(item, field_name):
                    continue
                setattr(item, field_name, value)
            if "preco" in changes and "preco_final" not in changes:
                item.preco_final = None
            item.normalize(margin=margin)
            updated = item
            if "marca" in changes:
                self._sync_brand(item.marca)
            break
        if updated is None:
            return None
        self._products.replace_active(items)
        log_event(
            logger,
            logging.INFO,
            "product_updated",
            "product updated",
            ordering_key=updated.ordering_key(),
            updated_fields=sorted(str(field) for field in changes),
        )
        return updated

    def update_grades_by_identifier(
        self,
        *,
        codigo: str | None,
        nome: str | None,
        grades: dict[str, int],
    ) -> Product | None:
        normalized_grades = normalize_grades_map(grades)
        if not normalized_grades:
            return None

        items = self.list_products()
        codigo_norm = (codigo or "").strip().lower()
        nome_norm = (nome or "").strip().lower()
        target: Product | None = None
        codigo_candidates: list[str] = []
        if codigo_norm:
            codigo_candidates.append(codigo_norm)
            base_candidate = extract_code_size_candidate(codigo or "")
            if base_candidate:
                base_code, _ = base_candidate
                normalized_base = base_code.strip().lower()
                if normalized_base and normalized_base not in codigo_candidates:
                    codigo_candidates.append(normalized_base)

        if codigo_candidates:
            for item in items:
                code_now = (item.codigo or "").strip().lower()
                code_original = (item.codigo_original or "").strip().lower()
                if any(candidate in {code_now, code_original} for candidate in codigo_candidates):
                    target = item
                    break

        if target is None and nome_norm:
            matches = [item for item in items if (item.nome or "").strip().lower() == nome_norm]
            if len(matches) == 1:
                target = matches[0]

        if target is None:
            return None

        target.grades = normalized_grades
        total = sum(item.quantidade for item in normalized_grades)
        if total > 0:
            target.quantidade = total
        target.normalize(margin=self.get_default_margin())
        self._products.replace_active(items)
        log_event(
            logger,
            logging.INFO,
            "product_grades_updated",
            "product grades updated",
            ordering_key=target.ordering_key(),
            grades=len(target.grades or []),
            total_quantity=int(target.quantidade or 0),
        )
        return target

    def list_brands(self) -> list[str]:
        return self._brands.list_brands()

    def add_brand(self, brand: str) -> list[str]:
        name = brand.strip()
        if not name:
            return self._brands.list_brands()
        current = self._brands.list_brands()
        index = {item.lower() for item in current}
        if name.lower() not in index:
            current.append(name)
            self._brands.save_brands(current)
        return current

    def get_default_margin(self) -> float:
        margin = self._margin_store.load_margin()
        return margin if margin > 0 else 1.0

    def set_default_margin(self, margin: float) -> float:
        safe = margin if margin > 0 else 1.0
        self._margin_store.save_margin(safe)
        return safe

    @staticmethod
    def _products_in_scope(items: list[Product], ordering_keys: list[str] | None) -> list[Product]:
        if ordering_keys is None:
            return items
        lookup = {str(key).strip() for key in ordering_keys if str(key).strip()}
        return [item for item in items if item.ordering_key() in lookup]

    def apply_margin_to_products(self, margin: float, ordering_keys: list[str] | None = None) -> int:
        items = self.list_products()
        if not items:
            return 0
        targets = self._products_in_scope(items, ordering_keys)
        if not targets:
            return 0
        updated = 0
        for item in targets:
            new_price = calculate_sale_price(item.preco, margin)
            if new_price != item.preco_final:
                item.preco_final = new_price
                updated += 1
        self._products.replace_active(items)
        if updated:
            log_event(
                logger,
                logging.INFO,
                "products_margin_applied",
                "products margin applied",
                updated=updated,
                total=len(targets),
            )
        return updated

    def get_summary(self) -> ProductsSummary:
        active = [Product.from_dict(item.to_dict()) for item in self._products.list_active()]
        history = self._products.list_history()
        metrics = self._metrics_store.load_metrics()
        history_totals = self._compute_totals(history)
        merged_history = TotalsSnapshot(
            quantidade=history_totals.quantidade + metrics.historico_quantidade,
            custo=round(history_totals.custo + metrics.historico_custo, 2),
            venda=round(history_totals.venda + metrics.historico_venda, 2),
        )
        return ProductsSummary(
            atual=self._compute_totals(active),
            historico=merged_history,
            metrics=metrics,
        )

    def apply_category(self, category: str, ordering_keys: list[str] | None = None) -> int:
        value = category.strip()
        items = self.list_products()
        if not items:
            return 0
        targets = self._products_in_scope(items, ordering_keys)
        if not targets:
            return 0
        for item in targets:
            item.categoria = value
        self._products.replace_active(items)
        log_event(
            logger,
            logging.INFO,
            "products_category_applied",
            "products category applied",
            updated=len(targets),
        )
        return len(targets)

    def apply_brand(self, brand: str, ordering_keys: list[str] | None = None) -> int:
        value = brand.strip()
        items = self.list_products()
        if not items:
            return 0
        targets = self._products_in_scope(items, ordering_keys)
        if not targets:
            return 0
        for item in targets:
            item.marca = value
        self._products.replace_active(items)
        if value:
            self._sync_brand(value)
        log_event(
            logger,
            logging.INFO,
            "products_brand_applied",
            "products brand applied",
            updated=len(targets),
            brand_set=bool(value),
        )
        return len(targets)

    def join_duplicates(self, ordering_keys: list[str] | None = None) -> dict[str, int]:
        items = self.list_products()
        if not items:
            return {"originais": 0, "resultantes": 0, "removidos": 0}
        targets = self._products_in_scope(items, ordering_keys)
        if not targets:
            return {"originais": 0, "resultantes": 0, "removidos": 0}

        target_keys = {item.ordering_key() for item in targets}
        grouped: dict[tuple[object, ...], Product] = {}
        result: list[Product] = []
        for item in items:
            if item.ordering_key() not in target_keys:
                result.append(item)
                continue
            key = (
                (item.nome or "").strip().lower(),
                (item.codigo or "").strip().lower(),
                (item.preco or "").strip(),
                (item.categoria or "").strip().lower(),
                (item.marca or "").strip().lower(),
                (item.preco_final or "").strip(),
                (item.descricao_completa or "").strip(),
                (item.codigo_original or "").strip().lower(),
                tuple(
                    sorted(
                        ((grade.tamanho or "").strip().lower(), int(grade.quantidade or 0))
                        for grade in (item.grades or [])
                    )
                ),
                tuple(
                    sorted(
                        ((cor.cor or "").strip().lower(), int(cor.quantidade or 0))
                        for cor in (item.cores or [])
                    )
                ),
                (item.source_type or "").strip().lower(),
                (item.import_batch_id or "").strip(),
                (item.import_source_name or "").strip(),
                bool(item.pending_grade_import),
            )
            existing = grouped.get(key)
            if existing is None:
                copy = Product.from_dict(item.to_dict())
                grouped[key] = copy
                result.append(copy)
                continue
            existing.quantidade += item.quantidade
            grades_by_size = {
                (grade.tamanho or "").strip().lower(): grade
                for grade in (existing.grades or [])
            }
            for incoming_grade in item.grades or []:
                grades_by_size[(incoming_grade.tamanho or "").strip().lower()].quantidade += incoming_grade.quantidade
            colors_by_name = {
                (color.cor or "").strip().lower(): color
                for color in (existing.cores or [])
            }
            for incoming_color in item.cores or []:
                colors_by_name[(incoming_color.cor or "").strip().lower()].quantidade += incoming_color.quantidade
        removed = len(targets) - len(grouped)
        if removed:
            self._products.replace_active(result)
            log_event(
                logger,
                logging.INFO,
                "products_duplicates_joined",
                "products duplicates joined",
                originals=len(targets),
                result_count=len(grouped),
                removed=removed,
                catalog_total=len(items),
            )
        return {
            "originais": len(targets),
            "resultantes": len(grouped),
            "removidos": removed,
        }

    def join_with_grades(self, keys: list[str] | None = None) -> dict[str, int]:
        items = self.list_products()
        if not items:
            return {"originais": 0, "resultantes": 0, "removidos": 0, "atualizados_grades": 0, "lotes_processados": 0}

        scoped_keys = {str(key or "").strip() for key in (keys or []) if str(key or "").strip()}
        if scoped_keys:
            scoped_items: list[Product] = []
            passthrough_items: list[Product] = []
            for item in items:
                cloned = Product.from_dict(item.to_dict())
                if cloned.ordering_key() in scoped_keys:
                    scoped_items.append(cloned)
                else:
                    passthrough_items.append(cloned)
            if not scoped_items:
                return {"originais": 0, "resultantes": 0, "removidos": 0, "atualizados_grades": 0, "lotes_processados": 0}
            results, summary = self._compact_products_with_grades(scoped_items, force_merge_all_codes=True)
            for item in results:
                item.pending_grade_import = False
            final_items = passthrough_items + results
            processed_batches = 1
        else:
            pending_batches: dict[str, list[Product]] = {}
            pending_batch_order: list[str] = []
            item_batch_lookup: dict[str, str] = {}

            for item in items:
                cloned = Product.from_dict(item.to_dict())
                if not cloned.pending_grade_import:
                    continue
                batch_id = str(cloned.import_batch_id or cloned.ordering_key()).strip()
                if batch_id not in pending_batches:
                    pending_batches[batch_id] = []
                    pending_batch_order.append(batch_id)
                pending_batches[batch_id].append(cloned)
                item_batch_lookup[cloned.ordering_key()] = batch_id

            if not pending_batch_order:
                return {"originais": 0, "resultantes": 0, "removidos": 0, "atualizados_grades": 0, "lotes_processados": 0}

            batch_results: dict[str, list[Product]] = {}
            originais = 0
            resultantes = 0
            removidos = 0
            atualizados_grades = 0
            emitted_batches: set[str] = set()
            final_items = []

            for batch_id in pending_batch_order:
                compacted, summary = self._compact_products_with_grades(pending_batches[batch_id], force_merge_all_codes=True)
                for item in compacted:
                    item.pending_grade_import = False
                batch_results[batch_id] = compacted
                originais += int(summary["originais"])
                resultantes += int(summary["resultantes"])
                removidos += int(summary["removidos"])
                atualizados_grades += int(summary["atualizados_grades"])

            for item in items:
                cloned = Product.from_dict(item.to_dict())
                batch_id = item_batch_lookup.get(cloned.ordering_key())
                if not batch_id:
                    final_items.append(cloned)
                    continue
                if batch_id in emitted_batches:
                    continue
                final_items.extend(Product.from_dict(result.to_dict()) for result in batch_results.get(batch_id, []))
                emitted_batches.add(batch_id)

            summary = {
                "originais": originais,
                "resultantes": resultantes,
                "removidos": removidos,
                "atualizados_grades": atualizados_grades,
            }
            processed_batches = len(pending_batch_order)

        self._products.replace_active(final_items)
        if summary["removidos"] or summary["atualizados_grades"] or processed_batches:
            log_event(
                logger,
                logging.INFO,
                "products_grades_joined",
                "products grades joined",
                originals=summary["originais"],
                result_count=summary["resultantes"],
                removed=summary["removidos"],
                grades_updated=summary["atualizados_grades"],
                batches=processed_batches,
            )
        return {
            "originais": summary["originais"],
            "resultantes": summary["resultantes"],
            "removidos": summary["removidos"],
            "atualizados_grades": summary["atualizados_grades"],
            "lotes_processados": processed_batches,
        }

    def compact_import_batch(self, products: list[Product]) -> tuple[list[Product], dict[str, int]]:
        if not products:
            return [], {"originais": 0, "resultantes": 0, "removidos": 0, "atualizados_grades": 0}
        return self._compact_products_with_grades(products, force_merge_all_codes=False)

    def create_set_by_keys(self, key_a: str, key_b: str) -> dict[str, int] | None:
        if not key_a or not key_b or key_a == key_b:
            return None

        items = self.list_products()
        if not items:
            return None

        idx_a = next((idx for idx, item in enumerate(items) if item.ordering_key() == key_a), None)
        idx_b = next((idx for idx, item in enumerate(items) if item.ordering_key() == key_b), None)
        if idx_a is None or idx_b is None:
            return None

        item_a = items[idx_a]
        item_b = items[idx_b]
        qtd_set = min(int(item_a.quantidade or 0), int(item_b.quantidade or 0))
        if qtd_set <= 0:
            return None

        remaining_a = max(int(item_a.quantidade or 0) - qtd_set, 0)
        remaining_b = max(int(item_b.quantidade or 0) - qtd_set, 0)
        composition_conflicts: list[str] = []
        for item, remaining in ((item_a, remaining_a), (item_b, remaining_b)):
            if remaining <= 0:
                continue
            grade_total = sum(max(int(grade.quantidade or 0), 0) for grade in (item.grades or []))
            color_total = sum(max(int(color.quantidade or 0), 0) for color in (item.cores or []))
            overflowing = [
                f"{label} somam {total}"
                for label, total in (("grades", grade_total), ("cores", color_total))
                if total > remaining
            ]
            if not overflowing:
                continue
            product_name = (item.nome or item.codigo or "Produto").strip()
            unit_label = "unidade" if remaining == 1 else "unidades"
            composition_conflicts.append(
                f'"{product_name}" ficaria com {remaining} {unit_label}, mas ' + " e ".join(overflowing)
            )
        if composition_conflicts:
            raise ProductSetCompositionConflictError(
                "Nao foi possivel criar o conjunto sem perder a composicao do estoque: "
                + "; ".join(composition_conflicts)
                + ". Ajuste grades/cores para o saldo que deve restar ou use toda a quantidade."
            )

        base_a = strip_size_suffix(item_a.nome or "").strip()
        base_b = strip_size_suffix(item_b.nome or "").strip()
        if base_a and base_b:
            set_name = base_a if base_a == base_b else f"{base_a} + {base_b}"
        else:
            set_name = (item_a.nome or item_b.nome or "").strip() or "Conjunto"

        code_a = (item_a.codigo or "").strip()
        code_b = (item_b.codigo or "").strip()
        set_code = f"{code_a} / {code_b}".strip(" /")

        cost_a = parse_non_negative_price(item_a.preco) or 0.0
        cost_b = parse_non_negative_price(item_b.preco) or 0.0
        set_cost = cost_a + cost_b
        set_price = format_price(set_cost) if set_cost > 0 else ""

        def _sale_price(product: Product) -> float:
            if product.preco_final:
                parsed = parse_non_negative_price(product.preco_final)
                if parsed is not None:
                    return parsed
            parsed = parse_non_negative_price(calculate_sale_price(product.preco, self.get_default_margin()))
            return parsed or 0.0

        sale_total = _sale_price(item_a) + _sale_price(item_b)
        final_price = format_price(sale_total) if sale_total > 0 else None

        created = Product(
            nome=set_name,
            codigo=set_code,
            codigo_original=set_code,
            quantidade=qtd_set,
            preco=set_price,
            categoria=item_a.categoria,
            marca=item_a.marca,
            preco_final=final_price,
        ).normalize(margin=self.get_default_margin())

        item_a.quantidade = remaining_a
        item_b.quantidade = remaining_b

        result: list[Product] = []
        removed = 0
        for idx, item in enumerate(items):
            if idx == idx_a:
                if item_a.quantidade > 0:
                    result.append(item_a)
                else:
                    removed += 1
                continue
            if idx == idx_b:
                if item_b.quantidade > 0:
                    result.append(item_b)
                else:
                    removed += 1
                continue
            result.append(item)
        result.append(created)
        self._products.replace_active(result)
        self._merge_brands_from_items(result)
        log_event(
            logger,
            logging.INFO,
            "product_set_created",
            "product set created",
            created=1,
            removed=removed,
            remaining_a=item_a.quantidade,
            remaining_b=item_b.quantidade,
        )
        return {
            "created": 1,
            "removed": removed,
            "remaining_a": item_a.quantidade,
            "remaining_b": item_b.quantidade,
        }

    def format_codes(
        self,
        options: dict[str, object],
        ordering_keys: list[str] | None = None,
    ) -> dict[str, object]:
        remove_prefix = bool(options.get("remover_prefixo5"))
        remove_left_zeros = bool(options.get("remover_zeros_a_esquerda"))
        last_digits = self._coerce_positive_int(options.get("ultimos_digitos"))
        first_digits = self._coerce_positive_int(options.get("primeiros_digitos"))
        remove_last_numbers = self._coerce_positive_int(options.get("remover_ultimos_numeros"))
        remove_first_numbers = self._coerce_positive_int(options.get("remover_primeiros_numeros"))
        keep_first_chars = self._coerce_positive_int(options.get("manter_primeiros_caracteres"))
        keep_last_chars = self._coerce_positive_int(options.get("manter_ultimos_caracteres"))
        remove_first_chars = self._coerce_positive_int(options.get("remover_primeiros_caracteres"))
        remove_last_chars = self._coerce_positive_int(options.get("remover_ultimos_caracteres"))
        remove_letters = bool(options.get("remover_letras"))
        remove_numbers = bool(options.get("remover_numeros"))
        prefix_used: str | None = None

        items = self.list_products()
        if not items:
            return {"total": 0, "alterados": 0, "prefixo": prefix_used}
        targets = self._products_in_scope(items, ordering_keys)
        if not targets:
            return {"total": 0, "alterados": 0, "prefixo": prefix_used}

        for item in targets:
            if not item.codigo_original:
                item.codigo_original = item.codigo

        if remove_prefix:
            candidates = [
                (item.codigo or "").strip()[:5]
                for item in targets
                if len((item.codigo or "").strip()) >= 5 and (item.codigo or "").strip()[:5].isdigit()
            ]
            if candidates:
                prefix, count = Counter(candidates).most_common(1)[0]
                if count >= 5:
                    prefix_used = prefix

        changed = 0
        for item in targets:
            original = item.codigo
            updated = original
            if prefix_used and updated.startswith(prefix_used):
                updated = updated[len(prefix_used) :] or updated
            if remove_left_zeros:
                updated = updated.lstrip("0") or "0"
            if remove_letters:
                updated = re.sub(r"[A-Za-z]+", "", updated)
            if remove_numbers:
                updated = re.sub(r"\d+", "", updated)
            if remove_first_chars:
                updated = updated[remove_first_chars:]
            if remove_last_chars:
                updated = updated[:-remove_last_chars] if remove_last_chars < len(updated) else ""
            if remove_last_numbers:
                updated = self._remove_digits_from_end(updated, remove_last_numbers)
            if remove_first_numbers:
                updated = self._remove_digits_from_start(updated, remove_first_numbers)
            if keep_first_chars:
                updated = updated[:keep_first_chars]
            if keep_last_chars:
                updated = updated[-keep_last_chars:] if keep_last_chars < len(updated) else updated
            if first_digits:
                digits_only = re.sub(r"\D+", "", updated)
                updated = digits_only[:first_digits] if digits_only else updated[:first_digits]
            if last_digits:
                digits_only = re.sub(r"\D+", "", updated)
                if len(digits_only) >= last_digits:
                    updated = digits_only[-last_digits:]
                elif digits_only:
                    updated = digits_only
            if updated != original:
                item.codigo = updated
                changed += 1

        self._products.replace_active(items)
        if changed:
            log_event(
                logger,
                logging.INFO,
                "product_codes_formatted",
                "product codes formatted",
                total=len(targets),
                changed=changed,
                prefix_removed=bool(prefix_used),
            )
        return {"total": len(targets), "alterados": changed, "prefixo": prefix_used}

    def restore_original_codes(self, ordering_keys: list[str] | None = None) -> dict[str, int]:
        items = self.list_products()
        if not items:
            return {"total": 0, "restaurados": 0}
        targets = self._products_in_scope(items, ordering_keys)
        if not targets:
            return {"total": 0, "restaurados": 0}
        restored = 0
        for item in targets:
            if item.codigo_original and item.codigo != item.codigo_original:
                item.codigo = item.codigo_original
                restored += 1
        if restored:
            self._products.replace_active(items)
            log_event(
                logger,
                logging.INFO,
                "product_codes_restored",
                "product codes restored",
                total=len(targets),
                restored=restored,
            )
        return {"total": len(targets), "restaurados": restored}

    def reorder_by_keys(self, keys: list[str]) -> int:
        total = self._products.reorder_active(keys)
        if total:
            log_event(
                logger,
                logging.INFO,
                "products_reordered",
                "products reordered",
                total=total,
                requested_keys=len(keys),
            )
        return total

    def improve_descriptions(
        self,
        remove_numbers: bool,
        remove_special: bool,
        remove_letters: bool,
        terms: Iterable[str],
        ordering_keys: list[str] | None = None,
    ) -> dict[str, int]:
        normalized_terms = [term.strip() for term in terms if term and term.strip()]
        normalized_terms.sort(key=len, reverse=True)
        items = self.list_products()
        if not items:
            return {"total": 0, "modificados": 0}
        targets = self._products_in_scope(items, ordering_keys)
        if not targets:
            return {"total": 0, "modificados": 0}

        changed = 0
        for item in targets:
            modified = False
            for attr in ("descricao_completa", "nome"):
                current = getattr(item, attr) or ""
                if not current:
                    continue
                updated = current
                if remove_numbers:
                    updated = re.sub(r"\d+", "", updated)
                if remove_letters:
                    updated = re.sub(r"[A-Za-zÀ-ÿ]+", "", updated, flags=re.UNICODE)
                if remove_special:
                    updated = re.sub(r"[^\w\s]", "", updated, flags=re.UNICODE)
                if normalized_terms:
                    updated = self._remove_terms(updated, normalized_terms)
                updated = re.sub(r"\s+", " ", updated).strip()
                if updated != current:
                    setattr(item, attr, updated)
                    modified = True
            if modified:
                changed += 1

        if changed:
            self._products.replace_active(items)
            log_event(
                logger,
                logging.INFO,
                "product_descriptions_improved",
                "product descriptions improved",
                total=len(targets),
                changed=changed,
            )
        return {"total": len(targets), "modificados": changed}

    def get_active_file(self):
        return getattr(self._products, "_active_file")

    def get_by_ordering_keys(self, ordering_keys: list[str]) -> list[Product]:
        lookup = set(ordering_keys)
        return [item for item in self.list_products() if item.ordering_key() in lookup]

    def record_automation_success(self, items: Iterable[Product]) -> dict[str, int]:
        records = list(items)
        if not records:
            return {"tempo_economizado": 0, "caracteres_digitados": 0}
        self._products.append_history(records)
        tempo, caracteres = self._calculate_metrics(records)
        metrics = self._metrics_store.load_metrics()
        metrics.tempo_economizado += tempo
        metrics.caracteres_digitados += caracteres
        self._metrics_store.save_metrics(metrics)
        log_event(
            logger,
            logging.INFO,
            "automation_success_recorded",
            "automation success recorded",
            products=len(records),
            time_saved_seconds=tempo,
            typed_characters=caracteres,
        )
        return {"tempo_economizado": tempo, "caracteres_digitados": caracteres}

    def _compute_totals(self, items: list[Product]) -> TotalsSnapshot:
        margin = self.get_default_margin()
        quantidade = 0
        custo = 0.0
        venda = 0.0
        for item in items:
            quantidade += item.quantidade
            cost_value = parse_non_negative_price(item.preco) or 0.0
            sale_value = parse_non_negative_price(item.preco_final)
            if sale_value is None:
                sale_value = parse_non_negative_price(calculate_sale_price(item.preco, margin))
            if sale_value is None:
                sale_value = 0.0
            custo += cost_value * item.quantidade
            venda += sale_value * item.quantidade
        return TotalsSnapshot(
            quantidade=quantidade,
            custo=round(custo, 2),
            venda=round(venda, 2),
        )

    def _sync_brand(self, brand: str) -> None:
        if not brand.strip():
            return
        self.add_brand(brand)

    def _merge_brands_from_items(self, items: Iterable[Product]) -> None:
        brands = self._brands.list_brands()
        lowered = {item.lower() for item in brands}
        changed = False
        for item in items:
            name = (item.marca or "").strip()
            if not name or name.lower() in lowered:
                continue
            brands.append(name)
            lowered.add(name.lower())
            changed = True
        if changed:
            self._brands.save_brands(brands)

    @staticmethod
    def _ensure_unique_ordering_key(product: Product, occupied_keys: set[str]) -> None:
        base_key = product.ordering_key()
        if base_key not in occupied_keys:
            product.ordering_key_value = base_key
            return

        price_suffix = re.sub(r"[^0-9A-Za-z]+", "_", str(product.preco or "").strip()).strip("_")
        if price_suffix:
            candidate = f"{base_key}::{price_suffix}"
            if candidate not in occupied_keys:
                product.ordering_key_value = candidate
                return

        quantity = int(product.quantidade or 0)
        if quantity > 0:
            candidate = f"{base_key}::q{quantity}"
            if candidate not in occupied_keys:
                product.ordering_key_value = candidate
                return

        suffix = 2
        while True:
            candidate = f"{base_key}::{suffix}"
            if candidate not in occupied_keys:
                product.ordering_key_value = candidate
                return
            suffix += 1

    def _resolve_import_price_bucket(
        self,
        codigo: str,
        canonical_name: str,
        raw_price: str | None,
        buckets: dict[tuple[str, str], list[tuple[str, Decimal | None]]],
    ) -> str:
        normalized_price = str(raw_price or "").strip()
        if not normalized_price:
            return normalized_price
        identity = (codigo.strip().lower(), canonical_name.strip().lower())
        candidates = buckets.setdefault(identity, [])
        parsed_price = parse_price_decimal(normalized_price)
        for existing_label, existing_value in candidates:
            if normalized_price == existing_label:
                return existing_label
            if parsed_price is None or existing_value is None:
                continue
            if abs(parsed_price - existing_value) <= IMPORT_PRICE_MERGE_TOLERANCE:
                return existing_label
        candidates.append((normalized_price, parsed_price))
        return normalized_price

    @staticmethod
    def _calculate_metrics(records: Iterable[Product]) -> tuple[int, int]:
        items = list(records)
        total_quantidade = sum(max(int(item.quantidade or 0), 0) for item in items)
        notas_equivalentes = total_quantidade / AVERAGE_INVOICE_ITEMS if total_quantidade > 0 else 0
        tempo = int(round(notas_equivalentes * SECONDS_SAVED_PER_INVOICE))
        caracteres = 0
        for item in items:
            caracteres += len(item.nome or "")
            caracteres += len(item.codigo or "")
            caracteres += len(item.marca or "")
            caracteres += len(item.descricao_completa or "")
        return tempo, caracteres

    @staticmethod
    def _remove_terms(text: str, terms: list[str]) -> str:
        result = text
        for term in terms:
            parts = term.split()
            if not parts:
                continue
            pattern = r"\b" + r"\s+".join(re.escape(part) for part in parts) + r"\b"
            result = re.sub(pattern, " ", result, flags=re.IGNORECASE)
        return result

    @staticmethod
    def _coerce_positive_int(value: object) -> int | None:
        try:
            parsed = int(value)  # type: ignore[arg-type]
        except Exception:
            return None
        return parsed if parsed > 0 else None

    @staticmethod
    def _remove_digits_from_end(text: str, amount: int) -> str:
        if amount <= 0:
            return text
        result: list[str] = []
        removed = 0
        for char in reversed(text):
            if char.isdigit() and removed < amount:
                removed += 1
                continue
            result.append(char)
        return "".join(reversed(result))

    @staticmethod
    def _remove_digits_from_start(text: str, amount: int) -> str:
        if amount <= 0:
            return text
        result: list[str] = []
        removed = 0
        for char in text:
            if char.isdigit() and removed < amount:
                removed += 1
                continue
            result.append(char)
        return "".join(result)

    def _compact_products_with_grades(
        self,
        products: list[Product],
        *,
        force_merge_all_codes: bool,
    ) -> tuple[list[Product], dict[str, int]]:
        if not products:
            return [], {"originais": 0, "resultantes": 0, "removidos": 0, "atualizados_grades": 0}

        margin = self.get_default_margin()
        price_buckets: dict[tuple[str, str], list[tuple[str, Decimal | None]]] = {}
        code_size_families: dict[tuple[str, str, str], set[str]] = {}
        code_family_codes: dict[tuple[str, str, str], set[str]] = {}
        for item in products:
            current = Product.from_dict(item.to_dict()).normalize(margin=margin)
            source_name = str(current.descricao_completa or current.nome or "").strip()
            canonical_name = canonicalize_product_name(current.nome or "", current.descricao_completa)
            family_candidate = extract_code_size_candidate(current.codigo or "")
            if not family_candidate or not canonical_name:
                continue
            base_code, size = family_candidate
            price_bucket = self._resolve_import_price_bucket(base_code, canonical_name, current.preco, price_buckets)
            family_key = (
                base_code.strip().lower(),
                canonical_name.strip().lower(),
                price_bucket,
            )
            code_size_families.setdefault(family_key, set()).add(size)
            code_family_codes.setdefault(family_key, set()).add((current.codigo or "").strip().lower())

        groups: dict[tuple[str, str, str], dict[str, object]] = {}
        ordered_group_keys: list[tuple[str, str, str]] = []
        passthrough: list[Product] = []

        for item in products:
            current = Product.from_dict(item.to_dict()).normalize(margin=margin)
            source_name = str(current.descricao_completa or current.nome or "").strip()
            canonical_name = canonicalize_product_name(current.nome or "", current.descricao_completa)
            family_candidate = extract_code_size_candidate(current.codigo or "")
            family_size: str | None = None
            codigo = (current.codigo or "").strip()
            price_bucket = self._resolve_import_price_bucket(codigo, canonical_name, current.preco, price_buckets)
            if family_candidate and canonical_name:
                base_code, size = family_candidate
                price_bucket = self._resolve_import_price_bucket(base_code, canonical_name, current.preco, price_buckets)
                family_key = (
                    base_code.strip().lower(),
                    canonical_name.strip().lower(),
                    price_bucket,
                )
                family_sizes = code_size_families.get(family_key) or set()
                family_codes = code_family_codes.get(family_key) or set()
                if len(family_sizes) >= 2 or len(family_codes) >= 2:
                    codigo = base_code.strip()
                    family_size = size
                    current.codigo = codigo
                    current.codigo_original = codigo
            if not codigo:
                passthrough.append(current)
                continue

            group_key = (codigo, canonical_name.strip().lower(), price_bucket)
            entry = groups.setdefault(
                group_key,
                {
                    "items": [],
                    "base": Product.from_dict(current.to_dict()),
                    "grades": {},
                    "qtd_livre": 0,
                    "nome_base": canonical_name,
                    "descricao_base": source_name,
                    "has_grade_signal": False,
                },
            )
            if group_key not in ordered_group_keys:
                ordered_group_keys.append(group_key)

            group_items = entry["items"]
            assert isinstance(group_items, list)
            group_items.append(Product.from_dict(current.to_dict()))

            if canonical_name:
                entry["nome_base"] = canonical_name
            if source_name and len(source_name) >= len(str(entry.get("descricao_base") or "")):
                entry["descricao_base"] = source_name

            grades_map = entry["grades"]
            assert isinstance(grades_map, dict)
            if current.grades:
                entry["has_grade_signal"] = True
                for grade in current.grades:
                    size = normalize_grade_label(str(getattr(grade, "tamanho", "") or "").strip())
                    qty = int(getattr(grade, "quantidade", 0) or 0)
                    if not size or qty <= 0:
                        continue
                    grades_map[size] = grades_map.get(size, 0) + qty
            else:
                size = detect_size_from_name(source_name) or family_size
                qty = int(current.quantidade or 0) or 1
                if size:
                    entry["has_grade_signal"] = True
                    grades_map[size] = grades_map.get(size, 0) + qty
                else:
                    entry["qtd_livre"] = int(entry["qtd_livre"] or 0) + qty

        results: list[Product] = []
        updated_grades = 0
        for group_key in ordered_group_keys:
            data = groups[group_key]
            group_items = data["items"]
            assert isinstance(group_items, list)
            should_merge = bool(data.get("has_grade_signal")) and (
                force_merge_all_codes or len(group_items) > 1
            )

            if not should_merge:
                for item in group_items:
                    assert isinstance(item, Product)
                    results.append(Product.from_dict(item.to_dict()).normalize(margin=margin))
                continue

            base = Product.from_dict(data["base"].to_dict())  # type: ignore[union-attr]
            grades_map = data["grades"]
            assert isinstance(grades_map, dict)
            if data.get("nome_base"):
                base.nome = str(data["nome_base"])
            if data.get("descricao_base"):
                base.descricao_completa = str(data["descricao_base"]).strip() or None
            free_qty = int(data.get("qtd_livre") or 0)
            base.grades = sort_grade_items(grades_map)
            base.quantidade = sum(item.quantidade for item in base.grades) + free_qty
            if base.grades:
                updated_grades += 1
            results.append(base.normalize(margin=margin))

        results.extend(passthrough)
        return (
            results,
            {
                "originais": len(products),
                "resultantes": len(results),
                "removidos": len(products) - len(results),
                "atualizados_grades": updated_grades,
            },
        )
