from __future__ import annotations

import re
import unicodedata
from collections import Counter
from dataclasses import dataclass
from typing import Iterable

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
    "01",
    "02",
    "03",
    "04",
    "06",
    "08",
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
        margin = self.get_default_margin()
        return [item.normalize(margin=margin) for item in self._products.list_active()]

    def create_product(self, product: Product) -> Product:
        margin = self.get_default_margin()
        normalized = product.normalize(margin=margin)
        self._products.append_active(normalized)
        self._sync_brand(normalized.marca)
        return normalized

    def create_many(self, products: list[Product]) -> list[Product]:
        created: list[Product] = []
        for product in products:
            created.append(self.create_product(product))
        return created

    def restore_snapshot(self, products: list[Product]) -> int:
        margin = self.get_default_margin()
        normalized = [item.normalize(margin=margin) for item in products]
        self._products.replace_active(normalized)
        self._merge_brands_from_items(normalized)
        return len(normalized)

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
        active = self.list_products()
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

    def join_with_grades(self) -> dict[str, int]:
        items = self.list_products()
        if not items:
            return {"originais": 0, "resultantes": 0, "removidos": 0, "atualizados_grades": 0}
        results, summary = self._compact_products_with_grades(items, force_merge_all_codes=True)

        self._products.replace_active(results)
        return {
            "originais": len(items),
            "resultantes": len(results),
            "removidos": len(items) - len(results),
            "atualizados_grades": summary["atualizados_grades"],
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
        items = self.list_products()
        if not items:
            return 0
        mapping = {item.ordering_key(): item for item in items}
        ordered: list[Product] = []
        seen: set[str] = set()
        for key in keys:
            item = mapping.get(key)
            if item is None or key in seen:
                continue
            ordered.append(item)
            seen.add(key)
        for key, item in mapping.items():
            if key not in seen:
                ordered.append(item)
        self._products.replace_active(ordered)
        return len(ordered)

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
            family_key = (
                base_code.strip().lower(),
                canonical_name.strip().lower(),
                (current.preco or "").strip(),
            )
            code_size_families.setdefault(family_key, set()).add(size)
            code_family_codes.setdefault(family_key, set()).add((current.codigo or "").strip().lower())

        groups: dict[str, dict[str, object]] = {}
        ordered_codes: list[str] = []
        passthrough: list[Product] = []

        for item in products:
            current = Product.from_dict(item.to_dict()).normalize(margin=margin)
            source_name = str(current.descricao_completa or current.nome or "").strip()
            canonical_name = self._canonicalize_product_name(current.nome or "", current.descricao_completa)
            family_candidate = self._extract_code_size_candidate(current.codigo or "")
            family_size: str | None = None
            codigo = (current.codigo or "").strip()
            if family_candidate and canonical_name:
                base_code, size = family_candidate
                family_key = (
                    base_code.strip().lower(),
                    canonical_name.strip().lower(),
                    (current.preco or "").strip(),
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

            entry = groups.setdefault(
                codigo,
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
            if codigo not in ordered_codes:
                ordered_codes.append(codigo)

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
        for codigo in ordered_codes:
            data = groups[codigo]
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
            if number in {4, 6, 8}:
                return str(number).zfill(2)
            if len(label) >= 3:
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
