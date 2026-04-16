from __future__ import annotations

import json
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_CEILING
from typing import Any, Iterable

from app.domain.brands.repository import BrandRepository
from app.domain.metrics.entities import Metrics
from app.domain.products.entities import GradeItem, Product, calculate_sale_price, format_price, parse_price
from app.domain.products.repository import ProductRepository
from app.infrastructure.persistence.files.settings_files import MarginSettingsStore, MetricsStore


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


GRADE_SIZE_ORDER = [
    "1",
    "2",
    "3",
    "4",
    "6",
    "8",
    "10",
    "12",
    "14",
    "16",
    "18",
    "U",
    "PP",
    "P",
    "M",
    "G",
    "GG",
    "XG",
    "XXG",
    "G1",
    "G2",
    "G3",
    "34",
    "36",
    "38",
    "40",
    "42",
    "44",
    "46",
    "48",
    "50",
    "52",
    "54",
    "56",
]
GRADE_SIZE_INDEX = {label: index for index, label in enumerate(GRADE_SIZE_ORDER)}
AVERAGE_INVOICE_ITEMS = 50
MANUAL_MINUTES_PER_INVOICE = 90
AUTOMATED_MINUTES_PER_INVOICE = 20
SECONDS_SAVED_PER_INVOICE = (MANUAL_MINUTES_PER_INVOICE - AUTOMATED_MINUTES_PER_INVOICE) * 60
IMPORT_PRICE_MERGE_TOLERANCE = Decimal("0.01")
NAME_NOISE_TOKENS = {
    "bb",
    "bebe",
    "bebea",
    "bebea",
    "bebes",
    "inf",
    "infantil",
    "juvenil",
    "juv",
    "masc",
    "masculino",
    "fem",
    "feminino",
    "unisex",
    "unissex",
    "sort",
    "sortida",
    "sortido",
    "sortidos",
    "sortidas",
    "tam",
    "tamanho",
}

POST_PROCESS_KEEP_ACTIONS = {"manter", "keep", "none"}


def _fold_token(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", str(value or ""))
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "", ascii_text.lower())


class ProductService:
    def __init__(
        self,
        products: ProductRepository,
        brands: BrandRepository,
        margin_store: MarginSettingsStore,
        metrics_store: MetricsStore,
    ) -> None:
        self._products = products
        self._brands = brands
        self._margin_store = margin_store
        self._metrics_store = metrics_store

    def list_products(self) -> list[Product]:
        return [Product.from_dict(item.to_dict()) for item in self._products.list_active()]

    def get_post_process_review_candidates(self) -> list[Product]:
        return [
            Product.from_dict(item.to_dict())
            for item in self.list_products()
            if self._needs_llm_post_review(item)
        ]

    def create_product(self, product: Product) -> Product:
        occupied_keys = {item.ordering_key() for item in self._products.list_active()}
        return self._create_product_with_occupied_keys(product, occupied_keys)

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
        return len(restored)

    def delete_product(self, ordering_key: str) -> bool:
        items = self.list_products()
        filtered = [item for item in items if item.ordering_key() != ordering_key]
        if len(filtered) == len(items):
            return False
        self._products.replace_active(filtered)
        return True

    def clear_products(self) -> int:
        items = self.list_products()
        self._products.replace_active([])
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
        return updated

    def update_grades_by_identifier(
        self,
        *,
        codigo: str | None,
        nome: str | None,
        grades: dict[str, int],
    ) -> Product | None:
        normalized_grades = self._normalize_grades_map(grades)
        if not normalized_grades:
            return None

        items = self.list_products()
        codigo_norm = (codigo or "").strip().lower()
        nome_norm = (nome or "").strip().lower()
        target: Product | None = None
        codigo_candidates: list[str] = []
        if codigo_norm:
            codigo_candidates.append(codigo_norm)
            base_candidate = self._extract_code_size_candidate(codigo or "")
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

    def apply_margin_to_products(self, margin: float) -> int:
        items = self.list_products()
        if not items:
            return 0
        updated = 0
        for item in items:
            new_price = calculate_sale_price(item.preco, margin)
            if new_price != item.preco_final:
                item.preco_final = new_price
                updated += 1
        self._products.replace_active(items)
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

    def apply_category(self, category: str) -> int:
        value = category.strip()
        items = self.list_products()
        if not items:
            return 0
        for item in items:
            item.categoria = value
        self._products.replace_active(items)
        return len(items)

    def apply_brand(self, brand: str) -> int:
        value = brand.strip()
        items = self.list_products()
        if not items:
            return 0
        for item in items:
            item.marca = value
        self._products.replace_active(items)
        if value:
            self._sync_brand(value)
        return len(items)

    def join_duplicates(self) -> dict[str, int]:
        items = self.list_products()
        if not items:
            return {"originais": 0, "resultantes": 0, "removidos": 0}
        grouped: dict[tuple[str, ...], Product] = {}
        for item in items:
            key = (
                (item.nome or "").strip().lower(),
                (item.codigo or "").strip().lower(),
                (item.preco or "").strip(),
                (item.categoria or "").strip().lower(),
                (item.marca or "").strip().lower(),
            )
            existing = grouped.get(key)
            if existing is None:
                grouped[key] = Product.from_dict(item.to_dict())
                continue
            existing.quantidade += item.quantidade
        result = list(grouped.values())
        self._products.replace_active(result)
        return {
            "originais": len(items),
            "resultantes": len(result),
            "removidos": len(items) - len(result),
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

        base_a = self._strip_size_suffix(item_a.nome or "").strip()
        base_b = self._strip_size_suffix(item_b.nome or "").strip()
        if base_a and base_b:
            set_name = base_a if base_a == base_b else f"{base_a} + {base_b}"
        else:
            set_name = (item_a.nome or item_b.nome or "").strip() or "Conjunto"

        code_a = (item_a.codigo or "").strip()
        code_b = (item_b.codigo or "").strip()
        set_code = f"{code_a} / {code_b}".strip(" /")

        cost_a = parse_price(item_a.preco) or 0.0
        cost_b = parse_price(item_b.preco) or 0.0
        set_cost = cost_a + cost_b
        set_price = format_price(set_cost) if set_cost > 0 else ""

        def _sale_price(product: Product) -> float:
            if product.preco_final:
                parsed = parse_price(product.preco_final)
                if parsed is not None:
                    return parsed
            parsed = parse_price(calculate_sale_price(product.preco, self.get_default_margin()))
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

        item_a.quantidade = max(item_a.quantidade - qtd_set, 0)
        item_b.quantidade = max(item_b.quantidade - qtd_set, 0)

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
        return {
            "created": 1,
            "removed": removed,
            "remaining_a": item_a.quantidade,
            "remaining_b": item_b.quantidade,
        }

    def format_codes(self, options: dict[str, object]) -> dict[str, object]:
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

        for item in items:
            if not item.codigo_original:
                item.codigo_original = item.codigo

        if remove_prefix:
            candidates = [
                (item.codigo or "").strip()[:5]
                for item in items
                if len((item.codigo or "").strip()) >= 5 and (item.codigo or "").strip()[:5].isdigit()
            ]
            if candidates:
                prefix, count = Counter(candidates).most_common(1)[0]
                if count >= 5:
                    prefix_used = prefix

        changed = 0
        for item in items:
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
        return {"total": len(items), "alterados": changed, "prefixo": prefix_used}

    def restore_original_codes(self) -> dict[str, int]:
        items = self.list_products()
        if not items:
            return {"total": 0, "restaurados": 0}
        restored = 0
        for item in items:
            if item.codigo_original and item.codigo != item.codigo_original:
                item.codigo = item.codigo_original
                restored += 1
        if restored:
            self._products.replace_active(items)
        return {"total": len(items), "restaurados": restored}

    def reorder_by_keys(self, keys: list[str]) -> int:
        return self._products.reorder_active(keys)

    def improve_descriptions(
        self,
        remove_numbers: bool,
        remove_special: bool,
        remove_letters: bool,
        terms: Iterable[str],
    ) -> dict[str, int]:
        normalized_terms = [term.strip() for term in terms if term and term.strip()]
        normalized_terms.sort(key=len, reverse=True)
        items = self.list_products()
        if not items:
            return {"total": 0, "modificados": 0}

        changed = 0
        for item in items:
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
        return {"total": len(items), "modificados": changed}

    def apply_post_processing(self, llm_response_text: str | None = None) -> dict[str, Any]:
        items = self.list_products()
        if not items:
            return {
                "total": 0,
                "modificados": 0,
                "warnings": [],
                "llm_suggestions_applied": 0,
                "local_adjustments_applied": 0,
                "dry_run": False,
            }

        suggestions = self._extract_post_process_suggestions(llm_response_text)
        warnings: list[str] = []
        margin = self.get_default_margin()
        changed = 0
        llm_applied = 0
        local_applied = 0

        for item in items:
            original_name = item.nome or ""
            original_code = item.codigo or ""
            original_price = item.preco or ""
            suggestion = suggestions.get(item.ordering_key()) or {}

            next_name = self._post_process_name(item, suggestion)
            next_code = self._post_process_code(item, suggestion)
            next_price = self._post_process_price(item, suggestion)

            modified = False
            if next_name and next_name != original_name:
                item.nome = next_name
                modified = True
            if next_code and next_code != original_code:
                item.codigo = next_code
                modified = True
            if next_price and next_price != original_price:
                item.preco = next_price
                item.preco_final = None
                modified = True

            if modified:
                action_name = str(suggestion.get("acoes") or suggestion.get("action") or "").strip().lower()
                if action_name and action_name not in POST_PROCESS_KEEP_ACTIONS:
                    llm_applied += 1
                else:
                    local_applied += 1
                item.normalize(margin=margin)
                changed += 1

        if changed:
            self._products.replace_active(items)

        if llm_response_text and not suggestions:
            warnings.append("Resposta da IA recebida sem JSON estruturado aproveitavel; aplicadas apenas regras locais seguras.")

        return {
            "total": len(items),
            "modificados": changed,
            "warnings": warnings,
            "llm_suggestions_applied": llm_applied,
            "local_adjustments_applied": local_applied,
            "dry_run": False,
        }

    def _extract_post_process_suggestions(self, text: str | None) -> dict[str, dict[str, Any]]:
        raw = str(text or "").strip()
        if not raw:
            return {}

        payloads: list[Any] = []
        fenced = re.findall(r"```(?:json)?\s*(.*?)```", raw, flags=re.IGNORECASE | re.DOTALL)
        for fragment in fenced:
            try:
                payloads.append(json.loads(fragment.strip()))
            except Exception:
                continue

        if not payloads:
            decoder = json.JSONDecoder()
            for start in range(len(raw)):
                if raw[start] not in "[{":
                    continue
                try:
                    payload, _ = decoder.raw_decode(raw[start:])
                except Exception:
                    continue
                payloads.append(payload)
                break

        extracted: dict[str, dict[str, Any]] = {}
        for payload in payloads:
            items: list[Any]
            if isinstance(payload, dict) and isinstance(payload.get("items"), list):
                items = payload["items"]
            elif isinstance(payload, list):
                items = payload
            else:
                continue
            for item in items:
                if not isinstance(item, dict):
                    continue
                ordering_key = str(item.get("ordering_key") or "").strip()
                if ordering_key:
                    extracted[ordering_key] = item
        return extracted

    def _post_process_name(self, item: Product, suggestion: dict[str, Any]) -> str:
        confidence = self._coerce_confidence(suggestion.get("confianca"))
        llm_name = str(suggestion.get("nome_sugerido") or "").strip()
        if llm_name and confidence >= 0.7:
            cleaned_llm = self._sanitize_store_name(llm_name)
            if cleaned_llm:
                return cleaned_llm

        source = str(item.descricao_completa or item.nome or "").strip()
        fallback = self._sanitize_store_name(source)
        return fallback or (item.nome or "").strip()

    def _post_process_code(self, item: Product, suggestion: dict[str, Any]) -> str:
        confidence = self._coerce_confidence(suggestion.get("confianca"))
        llm_code = str(suggestion.get("codigo_sugerido") or "").strip()
        if llm_code and confidence >= 0.75:
            cleaned_llm = self._sanitize_code_for_store(llm_code)
            if cleaned_llm:
                return cleaned_llm
        return self._sanitize_code_for_store(item.codigo or "")

    def _post_process_price(self, item: Product, suggestion: dict[str, Any]) -> str:
        confidence = self._coerce_confidence(suggestion.get("confianca"))
        llm_price = str(suggestion.get("preco_sugerido") or "").strip()
        if llm_price and confidence >= 0.75:
            normalized_llm = self._normalize_price_to_next_tenth(llm_price)
            if normalized_llm:
                return normalized_llm
        normalized = self._normalize_price_to_next_tenth(item.preco or "")
        return normalized or (item.preco or "").strip()

    @classmethod
    def _sanitize_store_name(cls, value: str) -> str:
        text = str(value or "").upper().strip()
        if not text:
            return ""

        text = re.sub(r"\[[^\]]*\]", " ", text)
        text = re.sub(r"\([^)]*\)", " ", text)
        text = re.sub(r"\*[^*]*\*", " ", text)
        text = re.sub(r"(?i)\bCOR\s+[A-Z0-9]+\b", " ", text)
        text = re.sub(r"(?i)\bTAM(?:ANHO)?\s*[A-Z0-9]+\b", " ", text)
        text = re.sub(r"(?i)\b\d+\s*CM\b", " ", text)
        text = re.sub(r"(?i)\bREF(?:ERENCIA)?\s*[A-Z0-9-]+\b", " ", text)
        text = re.sub(r"(?i)\bCOD(?:IGO)?\s*[A-Z0-9-]+\b", " ", text)

        tokens = re.findall(r"[A-ZÀ-Ÿ0-9]+", text)
        cleaned: list[str] = []
        for token in tokens:
            folded = _fold_token(token)
            normalized_size = cls._normalize_grade_label(token)
            if not folded:
                continue
            if cls._is_known_grade_size(normalized_size):
                continue
            if folded in NAME_NOISE_TOKENS:
                continue
            if folded.isdigit():
                continue
            if len(token) <= 2:
                continue
            if re.fullmatch(r"[A-Z]{3,4}", token) and not re.search(r"[AEIOUÁÉÍÓÚÃÕÂÊÔ]", token):
                continue
            cleaned.append(token)

        result = " ".join(cleaned)
        result = re.sub(r"\bBASICOA\b", "BASICO", result)
        result = re.sub(r"\bCALA\b", "CALCA", result)
        result = re.sub(r"\bCAMISETAA\b", "CAMISETA", result)
        result = re.sub(r"\bBLUSAA\b", "BLUSA", result)
        result = re.sub(r"\s+", " ", result).strip()
        return result

    @staticmethod
    def _sanitize_code_for_store(value: str) -> str:
        code = re.sub(r"[^A-Za-z0-9]+", "", str(value or "").strip().upper())
        if not code:
            return ""

        repeated_chunk = re.fullmatch(r"([A-Z0-9]{2,})(?:\1)+", code)
        if repeated_chunk:
            return repeated_chunk.group(1)

        if re.search(r"(.)\1{3,}", code):
            code = re.sub(r"(.)\1{2,}", r"\1\1", code)

        for size in range(2, max(3, len(code) // 2 + 1)):
            if len(code) < size * 2:
                continue
            chunk = code[:size]
            if code == chunk * (len(code) // size) and len(code) % size == 0:
                return chunk
        return code

    def _normalize_price_to_next_tenth(self, value: str) -> str:
        parsed = self._parse_price_decimal(value)
        if parsed is None:
            return str(value or "").strip()
        normalized = (parsed * Decimal("10")).to_integral_value(rounding=ROUND_CEILING) / Decimal("10")
        return format_price(float(normalized)) or str(value or "").strip()

    @staticmethod
    def _coerce_confidence(value: Any) -> float:
        try:
            parsed = float(value)
        except Exception:
            return 0.0
        return max(0.0, min(parsed, 1.0))

    def _needs_llm_post_review(self, item: Product) -> bool:
        raw_name = str(item.descricao_completa or item.nome or "").strip().upper()
        current_name = str(item.nome or "").strip().upper()
        code = str(item.codigo or "").strip().upper()
        price = str(item.preco or "").strip()

        suspicious_name_patterns = [
            r"\bCOR\b",
            r"\[[^\]]+\]",
            r"\*[^*]+\*",
            r"\b[A-Z]{1}\b",
            r"\b[0-9]{2,}\s*CM\b",
            r"\bBASICO\s+A\b",
            r"\bCALA\b",
        ]
        if any(re.search(pattern, raw_name) for pattern in suspicious_name_patterns):
            return True
        if raw_name and current_name and raw_name != current_name:
            if len(raw_name) - len(current_name) >= 8:
                return True

        if len(code) >= 16:
            return True
        if re.fullmatch(r"([A-Z0-9]{2,})(?:\1)+", code):
            return True
        if re.search(r"(.)\1{4,}", code):
            return True

        if self._price_has_visual_noise(price):
            return True
        return False

    def _price_has_visual_noise(self, value: str) -> bool:
        parsed = self._parse_price_decimal(value)
        if parsed is None:
            return False
        cents = int((parsed * 100) % 100)
        return cents not in {0, 10, 20, 30, 40, 50, 60, 70, 80, 90}

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
        return {"tempo_economizado": tempo, "caracteres_digitados": caracteres}

    def _compute_totals(self, items: list[Product]) -> TotalsSnapshot:
        margin = self.get_default_margin()
        quantidade = 0
        custo = 0.0
        venda = 0.0
        for item in items:
            quantidade += item.quantidade
            cost_value = parse_price(item.preco) or 0.0
            sale_value = parse_price(item.preco_final) or parse_price(calculate_sale_price(item.preco, margin)) or 0.0
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

    @staticmethod
    def _parse_price_decimal(value: str | None) -> Decimal | None:
        text = str(value or "").strip()
        if not text:
            return None
        normalized = text.replace("R$", "").replace(" ", "").replace("\u00a0", "")
        if "." in normalized and "," in normalized:
            normalized = normalized.replace(".", "").replace(",", ".")
        else:
            normalized = normalized.replace(",", ".")
        try:
            return Decimal(normalized)
        except (InvalidOperation, ValueError):
            return None

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
        parsed_price = self._parse_price_decimal(normalized_price)
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
            canonical_name = self._canonicalize_product_name(current.nome or "", current.descricao_completa)
            family_candidate = self._extract_code_size_candidate(current.codigo or "")
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

        groups: dict[tuple[str, str], dict[str, object]] = {}
        ordered_group_keys: list[tuple[str, str]] = []
        passthrough: list[Product] = []

        for item in products:
            current = Product.from_dict(item.to_dict()).normalize(margin=margin)
            source_name = str(current.descricao_completa or current.nome or "").strip()
            canonical_name = self._canonicalize_product_name(current.nome or "", current.descricao_completa)
            family_candidate = self._extract_code_size_candidate(current.codigo or "")
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

            group_key = (codigo, price_bucket)
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
                    size = self._normalize_grade_label(str(getattr(grade, "tamanho", "") or "").strip())
                    qty = int(getattr(grade, "quantidade", 0) or 0)
                    if not size or qty <= 0:
                        continue
                    grades_map[size] = grades_map.get(size, 0) + qty
            else:
                size = self._detect_size_from_name(source_name) or family_size
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
            base.grades = self._sort_grade_items(grades_map)
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

    @staticmethod
    def _normalize_grades_map(grades: dict[str, int]) -> list[GradeItem]:
        normalized: list[GradeItem] = []
        for tamanho, quantidade in (grades or {}).items():
            size = ProductService._normalize_grade_label(str(tamanho or "").strip())
            try:
                qty = int(quantidade)
            except Exception:
                continue
            if not size or qty <= 0:
                continue
            normalized.append(GradeItem(tamanho=size, quantidade=qty))
        normalized.sort(key=lambda item: ProductService._grade_sort_key(item.tamanho))
        return normalized

    @classmethod
    def _detect_size_from_name(cls, name: str) -> str | None:
        if not name:
            return None
        match = re.search(
            r"(?i)\b(?:tam(?:anho)?\.?\s*)([0-9]{1,3}|pp|p|m|g|gg|xg|xxg|g[1-4])\b",
            name,
        )
        if match:
            label = cls._normalize_grade_label(match.group(1))
            if label:
                return label

        tokens = re.findall(r"[A-Za-zÀ-ÿ0-9]+", str(name or "").upper())
        for token in reversed(tokens):
            label = cls._normalize_grade_label(token)
            if cls._is_known_grade_size(label):
                return label
        return None

    @classmethod
    def _strip_size_suffix(cls, name: str) -> str:
        if not name:
            return ""
        return cls._canonicalize_product_name(name)

    @staticmethod
    def _normalize_grade_label(size: str) -> str:
        label = re.sub(r"(?i)\b(?:tam(?:anho)?\.?)\b", "", str(size or "")).strip().upper()
        label = re.sub(r"[^A-Z0-9]+", "", label)
        if not label:
            return ""
        if label.isdigit():
            try:
                number = int(label)
            except Exception:
                number = 0
            if number <= 0:
                return ""
            return str(number)
        return label

    @staticmethod
    def _is_known_grade_size(size: str) -> bool:
        label = ProductService._normalize_grade_label(size)
        if not label:
            return False
        if label in GRADE_SIZE_INDEX:
            return True
        if label.isdigit():
            try:
                return 1 <= int(label) <= 56
            except Exception:
                return False
        return False

    @staticmethod
    def _grade_sort_key(size: str) -> tuple[int, int | str]:
        label = ProductService._normalize_grade_label(size)
        if label in GRADE_SIZE_INDEX:
            return (0, GRADE_SIZE_INDEX[label])
        if label.isdigit():
            return (1, int(label))
        return (2, label)

    @staticmethod
    def _sort_grade_items(grades_map: dict[str, int]) -> list[GradeItem]:
        return [
            GradeItem(tamanho=size, quantidade=int(qty))
            for size, qty in sorted(
                (
                    (ProductService._normalize_grade_label(size), int(qty))
                    for size, qty in (grades_map or {}).items()
                    if ProductService._normalize_grade_label(size) and int(qty or 0) > 0
                ),
                key=lambda item: ProductService._grade_sort_key(item[0]),
            )
        ]

    @classmethod
    def _extract_code_size_candidate(cls, code: str) -> tuple[str, str] | None:
        value = str(code or "").strip()
        if not value:
            return None
        match = re.fullmatch(r"(.+?)([-_/])([A-Za-z0-9]+)", value)
        if not match:
            return None
        base = str(match.group(1) or "").strip()
        suffix = cls._normalize_grade_label(match.group(3))
        if not base or not suffix or not cls._is_known_grade_size(suffix):
            return None
        separators = sum(value.count(token) for token in "-_/")
        if suffix.isdigit() and not any(char.isalpha() for char in base) and separators < 2:
            return None
        return base, suffix

    @staticmethod
    def _canonicalize_product_name(name: str, descricao_completa: str | None = None) -> str:
        source = str(descricao_completa or name or "").strip()
        if not source:
            return ""

        tokens = re.findall(r"[A-Za-zÀ-ÿ0-9]+", source.upper())
        cleaned: list[str] = []
        for token in tokens:
            folded = _fold_token(token)
            normalized_size = ProductService._normalize_grade_label(token)
            if not folded:
                continue
            if ProductService._is_known_grade_size(normalized_size):
                continue
            if folded in NAME_NOISE_TOKENS:
                continue
            if folded.isdigit():
                continue
            if cleaned and cleaned[-1] == token:
                continue
            cleaned.append(token)

        result = " ".join(cleaned).strip()
        if result:
            return result

        fallback = re.sub(r"[\-_]+", " ", source)
        fallback = re.sub(r"\s+", " ", fallback).strip()
        return fallback or str(name or "").strip()
