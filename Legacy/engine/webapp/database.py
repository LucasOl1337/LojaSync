Camada de dados para o LojaSync Web.

Define duas "bases" coordenadas:
- Storage momentâneo (in-memory) usado para refletir imediatamente na UI.
- Storage permanente persistido em arquivo JSONL (compatível com a lógica legada).

A API é simples por enquanto, mas preparada para evoluções (ex.: múltiplas
instâncias, usuários simultâneos, persistência em DB real).
"""
from __future__ import annotations

import json
import math
import re
import threading
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional, Tuple

from modules.core.file_manager import carregar_margem_padrao, salvar_margem_padrao


def _remove_digits_from_end(text: str, amount: int) -> str:
    if amount <= 0:
        return text
    result = []
    digits_removed = 0
    for ch in reversed(text):
        if ch.isdigit() and digits_removed < amount:
            digits_removed += 1
            continue
        result.append(ch)
    return "".join(reversed(result))


def _remove_digits_from_start(text: str, amount: int) -> str:
    if amount <= 0:
        return text
    result = []
    digits_removed = 0
    for ch in text:
        if ch.isdigit() and digits_removed < amount:
            digits_removed += 1
            continue
        result.append(ch)
    return "".join(result)


def _remove_terms(text: str, terms: List[str]) -> str:
    result = text
    for term in terms:
        if not term:
            continue
        parts = term.split()
        if not parts:
            continue
        pattern = r"\b" + r"\s+".join(re.escape(part) for part in parts) + r"\b"
        result = re.sub(pattern, " ", result, flags=re.IGNORECASE)
    return result


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
ACTIVE_FILE = DATA_DIR / "products_active.jsonl"
HISTORY_FILE = DATA_DIR / "products_history.jsonl"
BRANDS_FILE = DATA_DIR / "brands.json"
ROMANEIO_DIR = DATA_DIR / "romaneios"
ROMANEIO_DIR.mkdir(parents=True, exist_ok=True)
METRICS_FILE = DATA_DIR / "metrics.json"

DEFAULT_BRANDS = ["OGOCHI", "MALWEE", "REVANCHE", "COQ"]

_lock = threading.RLock()


@dataclass
class GradeItem:
    tamanho: str
    quantidade: int


@dataclass
class CorItem:
    cor: str
    quantidade: int


def _parse_grades(value: Any) -> Optional[List[GradeItem]]:
    if not value:
        return None
    items: List[Any]
    if isinstance(value, dict):
        items = [{"tamanho": k, "quantidade": v} for k, v in value.items()]
    elif isinstance(value, list):
        items = value
    else:
        return None
    out: List[GradeItem] = []
    for it in items:
        try:
            if isinstance(it, dict):
                tamanho = str(it.get("tamanho", "")).strip()
                quantidade = int((it.get("quantidade") or 0))
            else:
                tamanho = str(getattr(it, "tamanho", "")).strip()
                quantidade = int(getattr(it, "quantidade", 0))
        except Exception:
            continue
        if not tamanho:
            continue
        out.append(GradeItem(tamanho=tamanho, quantidade=max(quantidade, 0)))
    return out or None


def _parse_cores(value: Any) -> Optional[List[CorItem]]:
    if not value:
        return None
    items: List[Any]
    if isinstance(value, dict):
        items = [{"cor": k, "quantidade": v} for k, v in value.items()]
    elif isinstance(value, list):
        items = value
    else:
        return None
    out: List[CorItem] = []
    for it in items:
        try:
            if isinstance(it, dict):
                cor = str(it.get("cor", "")).strip()
                quantidade = int((it.get("quantidade") or 0))
            else:
                cor = str(getattr(it, "cor", "")).strip()
                quantidade = int(getattr(it, "quantidade", 0))
        except Exception:
            continue
        if not cor:
            continue
        out.append(CorItem(cor=cor, quantidade=max(quantidade, 0)))
    return out or None


# Catálogo fixo de tamanhos para grades
SIZES_CATALOG = [
    "U",
    "PP",
    "P",
    "M",
    "G",
    "GG",
    "XG",
    "XXG", 
    "XGG",
    "G1",
    "G2",
    "G3",
    "G4",
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
    "56"
]


def _detect_size_from_name(name: str) -> Optional[str]:
    if not name:
        return None
    import re as _re
    m = _re.search(r"(?i)\b(?:tam(?:anho)?\.?\s*)([0-9]{1,3}|pp|p|m|g|gg|xg|g[1-4])\b", name or "")
    label = m.group(1) if m else ""
    label = str(label or "").strip().upper()
    if not label:
        return None
    if label in SIZES_CATALOG:
        return label
    return None


def _strip_size_suffix(name: str) -> str:
    if not name:
        return ""
    import re as _re
    base = _re.sub(r"(?i)\bTam(?:anho)?\.?\s*[A-Z0-9]+\b", "", name).strip()
    return base or name


@dataclass
class ProductRecord:
    nome: str
    codigo: str
    quantidade: int
    preco: str
    categoria: str
    marca: str
    preco_final: Optional[str] = None
    descricao_completa: Optional[str] = None
    codigo_original: Optional[str] = None
    grades: Optional[List[GradeItem]] = None
    cores: Optional[List[CorItem]] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, str]:
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        return data

    @classmethod
    def from_dict(cls, payload: Dict[str, str]) -> "ProductRecord":
        timestamp_raw = payload.get("timestamp")
        timestamp = (
            datetime.fromisoformat(timestamp_raw)
            if isinstance(timestamp_raw, str)
            else datetime.utcnow()
        )
        grades = _parse_grades(payload.get("grades"))
        cores = _parse_cores(payload.get("cores"))
        return cls(
            nome=payload.get("nome", ""),
            codigo=payload.get("codigo", ""),
            codigo_original=payload.get("codigo_original") or payload.get("codigo", ""),
            quantidade=int(payload.get("quantidade", 1)),
            preco=str(payload.get("preco", "")),
            categoria=payload.get("categoria", ""),
            marca=payload.get("marca", ""),
            preco_final=payload.get("preco_final"),
            descricao_completa=payload.get("descricao_completa"),
            grades=grades,
            cores=cores,
            timestamp=timestamp,
        )


class MomentaryStore:
    """Mantém a lista atual em memória."""

    def __init__(self) -> None:
        self._items: List[ProductRecord] = []

    def list(self) -> List[ProductRecord]:
        return list(self._items)

    def clear(self) -> None:
        self._items.clear()

    def extend(self, items: Iterable[ProductRecord]) -> None:
        self._items.extend(items)

    def append(self, item: ProductRecord) -> None:
        self._items.append(item)


class JSONLStore:
    """Persistência simples baseada em arquivo JSONL."""

    def __init__(self, file_path: Path) -> None:
        self.file_path = file_path
        if not self.file_path.exists():
            self.file_path.touch()

    def append(self, item: ProductRecord) -> None:
        with self.file_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(item.to_dict(), ensure_ascii=False) + "\n")

    def overwrite(self, items: Iterable[ProductRecord]) -> None:
        with self.file_path.open("w", encoding="utf-8") as fh:
            for item in items:
                fh.write(json.dumps(item.to_dict(), ensure_ascii=False) + "\n")

    def load_all(self) -> List[ProductRecord]:
        records: List[ProductRecord] = []
        if not self.file_path.exists():
            return records
        with self.file_path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    continue
                records.append(ProductRecord.from_dict(data))
        return records


class ProductDatabase:
    """Coordena store momentâneo (ativo) e log histórico permanente."""

    def __init__(self) -> None:
        self._momentary = MomentaryStore()
        self._active_store = JSONLStore(ACTIVE_FILE)
        self._history_store = JSONLStore(HISTORY_FILE)
        self._brands: List[str] = []
        self._brand_index: set[str] = set()
        self._metrics: Dict[str, int] = {
            "tempo_economizado": 0,
            "caracteres_digitados": 0,
        }
        with _lock:
            existing = self._active_store.load_all()
            existing = [self._normalize_record(item) for item in existing]
            self._momentary.extend(existing)
            self._brands = self._load_brands()
            self._brand_index = {brand.lower() for brand in self._brands}
            self._merge_brands_from_items(existing)
            self._metrics = self._load_metrics()

    # ------------------------------------------------------------------
    def _normalize_record(self, item: ProductRecord) -> ProductRecord:
        if not item.codigo_original:
            item.codigo_original = item.codigo
        if not item.preco_final:
            item.preco_final = self._calculate_sale_price(item.preco)
        if item.grades:
            try:
                total = 0
                for g in item.grades:
                    try:
                        total += max(int(getattr(g, "quantidade", 0)), 0)
                    except Exception:
                        continue
                if total > 0:
                    item.quantidade = total
            except Exception:
                pass
        return item

    def list(self) -> List[ProductRecord]:
        with _lock:
            return self._momentary.list()

    def count(self) -> int:
        with _lock:
            return len(self._momentary.list())

    def add(self, item: ProductRecord) -> ProductRecord:
        with _lock:
            item = self._normalize_record(item)
            self._momentary.append(item)
            self._active_store.append(item)
            if self._add_brand_no_lock(item.marca):
                self._save_brands_locked()
            return item

    def add_many(self, items: Iterable[ProductRecord]) -> List[ProductRecord]:
        items = [item for item in items]
        if not items:
            return []

        with _lock:
            brands_changed = False
            for item in items:
                item = self._normalize_record(item)
                self._momentary.append(item)
                self._active_store.append(item)
                if self._add_brand_no_lock(item.marca):
                    brands_changed = True

            if brands_changed:
                self._save_brands_locked()

            return items

    def commit_history(self, items: Iterable[ProductRecord]) -> None:
        with _lock:
            for item in items:
                if not item.preco_final:
                    item.preco_final = self._calculate_sale_price(item.preco)
                self._history_store.append(item)

    def record_automation_success(self, items: Iterable[ProductRecord]) -> Dict[str, int]:
        registros = list(items)
        if not registros:
            return {"tempo_economizado": 0, "caracteres_digitados": 0}
        self.commit_history(registros)
        tempo, caracteres = self._calculate_metrics(registros)
        self.add_metrics(tempo, caracteres)
        return {"tempo_economizado": tempo, "caracteres_digitados": caracteres}

    def add_metrics(self, tempo_economizado: int, caracteres_digitados: int) -> None:
        if not tempo_economizado and not caracteres_digitados:
            return
        with _lock:
            self._metrics["tempo_economizado"] = self._metrics.get("tempo_economizado", 0) + tempo_economizado
            self._metrics["caracteres_digitados"] = self._metrics.get("caracteres_digitados", 0) + caracteres_digitados
            self._save_metrics_locked()

    def get_metrics(self) -> Dict[str, int]:
        with _lock:
            return dict(self._metrics)

    def make_key(self, record: ProductRecord) -> str:
        return self._make_key(record)

    def get_by_ordering_keys(self, ordering_keys: Iterable[str]) -> List[ProductRecord]:
        keys = {key for key in ordering_keys if key}
        if not keys:
            return []
        with _lock:
            items = self._momentary.list()
            return [item for item in items if self._make_key(item) in keys]

    def replace_all(self, items: Iterable[ProductRecord]) -> None:
        items = list(items)
        with _lock:
            items = [self._normalize_record(item) for item in items]
            self._momentary.clear()
            self._momentary.extend(items)
            self._active_store.overwrite(items)
            self._merge_brands_from_items(items)

    def clear_current(self) -> int:
        with _lock:
            removed = len(self._momentary.list())
            self._momentary.clear()
            self._active_store.overwrite([])
            return removed

    def update(self, ordering_key: str, changes: Dict[str, Any]) -> Optional[ProductRecord]:
        if not ordering_key:
            return None

        normalized = dict(changes or {})
        if not normalized:
            return None

        with _lock:
            items = self._momentary.list()
            target_index: Optional[int] = None
            for idx, item in enumerate(items):
                if self._make_key(item) == ordering_key:
                    target_index = idx
                    break

            if target_index is None:
                return None

            target = items[target_index]

            if "descricao" in normalized and "descricao_completa" not in normalized:
                normalized["descricao_completa"] = normalized.pop("descricao")

            if "nome" in normalized and normalized["nome"] is not None:
                target.nome = str(normalized["nome"]).strip()

            if "marca" in normalized and normalized["marca"] is not None:
                target.marca = str(normalized["marca"]).strip()

            if "categoria" in normalized and normalized["categoria"] is not None:
                target.categoria = str(normalized["categoria"]).strip()

            if "codigo" in normalized and normalized["codigo"] is not None:
                novo_codigo = str(normalized["codigo"]).strip()
                if novo_codigo:
                    target.codigo = novo_codigo

            if "descricao_completa" in normalized:
                descricao = normalized["descricao_completa"]
                target.descricao_completa = (
                    str(descricao).strip() if descricao is not None else None
                )

            if "quantidade" in normalized and normalized["quantidade"] is not None:
                try:
                    target.quantidade = max(int(normalized["quantidade"]), 0)
                except Exception:
                    pass

            if "preco" in normalized:
                preco_val = normalized["preco"]
                target.preco = str(preco_val).strip() if preco_val not in (None, "") else ""

            if "preco_final" in normalized:
                preco_final = normalized["preco_final"]
                target.preco_final = (
                    str(preco_final).strip() if preco_final not in (None, "") else None
                )

            if "grades" in normalized:
                target.grades = _parse_grades(normalized["grades"])  # type: ignore[arg-type]

            if "cores" in normalized:
                target.cores = _parse_cores(normalized["cores"])  # type: ignore[arg-type]

            if "marca" in normalized:
                if self._add_brand_no_lock(target.marca):
                    self._save_brands_locked()

            target = self._normalize_record(target)
            self._momentary.clear()
            self._momentary.extend(items)
            self._active_store.overwrite(items)
            return target

    def update_grades_by_identifier(
        self,
        *,
        codigo: Optional[str],
        nome: Optional[str],
        grades: Dict[str, int],
    ) -> Optional[ProductRecord]:
        if not grades:
            return None

        normalized_grades: List[GradeItem] = []
        for tamanho, quantidade in grades.items():
            tamanho_str = str(tamanho or "").strip()
            if not tamanho_str:
                continue
            try:
                quantidade_int = int(quantidade)
            except Exception:
                continue
            if quantidade_int <= 0:
                continue
            normalized_grades.append(GradeItem(tamanho=tamanho_str, quantidade=quantidade_int))

        if not normalized_grades:
            return None

        codigo_norm = (codigo or "").strip().lower()
        nome_norm = (nome or "").strip().lower()

        with _lock:
            items = self._momentary.list()
            target: Optional[ProductRecord] = None

            if codigo_norm:
                for item in items:
                    codigo_atual = (item.codigo or "").strip().lower()
                    codigo_original = (item.codigo_original or "").strip().lower()
                    if codigo_norm in {codigo_atual, codigo_original}:
                        target = item
                        break

            if target is None and nome_norm:
                matches = [item for item in items if (item.nome or "").strip().lower() == nome_norm]
                if len(matches) == 1:
                    target = matches[0]

            if target is None:
                return None

            target.grades = normalized_grades
            total_quantidade = sum(g.quantidade for g in normalized_grades)
            if total_quantidade > 0:
                target.quantidade = total_quantidade

            self._momentary.clear()
            self._momentary.extend(items)
            self._active_store.overwrite(items)
            return target

    def apply_category(self, categoria: str) -> None:
        with _lock:
            items = self._momentary.list()
            for item in items:
                item.categoria = categoria
            self._momentary.clear()
            self._momentary.extend(items)
            self._active_store.overwrite(items)

    def apply_brand(self, marca: str) -> None:
        with _lock:
            items = self._momentary.list()
            for item in items:
                item.marca = marca
            self._momentary.clear()
            self._momentary.extend(items)
            self._active_store.overwrite(items)
            if self._add_brand_no_lock(marca):
                self._save_brands_locked()

    def list_brands(self) -> List[str]:
        with _lock:
            return list(self._brands)

    def add_brand(self, marca: str) -> List[str]:
        with _lock:
            if self._add_brand_no_lock(marca):
                self._save_brands_locked()
            return list(self._brands)

    def get_totals(self) -> Dict[str, Dict[str, float]]:
        with _lock:
            active_items = self._momentary.list()
            history_items = self._history_store.load_all()
            totals = {
                "atual": self._compute_totals(active_items),
                "historico": self._compute_totals(history_items),
            }
            totals.update(self._metrics)
            return totals

    @staticmethod
    def _make_key(record: ProductRecord) -> str:
        return f"{record.codigo.strip()}::{record.timestamp.isoformat()}"

    @staticmethod
    def _make_key_from_parts(codigo: str, timestamp: datetime) -> str:
        return f"{codigo.strip()}::{timestamp.isoformat()}"

    def join_duplicates(self) -> Dict[str, int]:
        with _lock:
            items = self._momentary.list()
            if not items:
                return {"originais": 0, "resultantes": 0, "removidos": 0}

            agrupados: Dict[tuple, ProductRecord] = {}
            for item in items:
                chave = (
                    item.nome.strip().upper(),
                    item.codigo.strip(),
                    item.preco.strip(),
                )
                if chave not in agrupados:
                    agrupados[chave] = ProductRecord.from_dict(item.to_dict())
                else:
                    existente = agrupados[chave]
                    existente.quantidade += item.quantidade

            resultantes = list(agrupados.values())
            originais = len(items)
            removidos = originais - len(resultantes)

            self._momentary.clear()
            self._momentary.extend(resultantes)
            self._active_store.overwrite(resultantes)

            return {
                "originais": originais,
                "resultantes": len(resultantes),
                "removidos": removidos,
            }

    def create_set_by_keys(self, key_a: str, key_b: str) -> Optional[Dict[str, int]]:
        if not key_a or not key_b or key_a == key_b:
            return None

        with _lock:
            items = self._momentary.list()
            if not items:
                return None

            idx_a = None
            idx_b = None
            for idx, item in enumerate(items):
                ordering_key = self._make_key(item)
                if ordering_key == key_a:
                    idx_a = idx
                elif ordering_key == key_b:
                    idx_b = idx
            if idx_a is None or idx_b is None:
                return None

            item_a = items[idx_a]
            item_b = items[idx_b]
            qtd_conjunto = min(int(item_a.quantidade or 0), int(item_b.quantidade or 0))
            if qtd_conjunto <= 0:
                return None

            base_a = _strip_size_suffix(item_a.nome or "").strip()
            base_b = _strip_size_suffix(item_b.nome or "").strip()
            if base_a and base_b:
                nome_conjunto = base_a if base_a == base_b else f"{base_a} + {base_b}"
            else:
                nome_conjunto = (item_a.nome or item_b.nome or "").strip()

            codigo_a = (item_a.codigo or "").strip()
            codigo_b = (item_b.codigo or "").strip()
            codigo_conjunto = f"{codigo_a} / {codigo_b}".strip(" /")

            custo_a = self._parse_price(item_a.preco) or 0.0
            custo_b = self._parse_price(item_b.preco) or 0.0
            custo_conjunto = custo_a + custo_b
            preco_conjunto = self._format_price(custo_conjunto) if custo_conjunto > 0 else ""

            def _sale_price(item: ProductRecord) -> float:
                if item.preco_final:
                    parsed = self._parse_price(item.preco_final)
                    if parsed is not None:
                        return parsed
                calc = self._calculate_sale_price(item.preco)
                return self._parse_price(calc) or 0.0

            venda_conjunto = _sale_price(item_a) + _sale_price(item_b)
            preco_final_conjunto = (
                self._format_price(venda_conjunto) if venda_conjunto > 0 else None
            )

            conjunto = ProductRecord(
                nome=nome_conjunto or "Conjunto",
                codigo=codigo_conjunto,
                quantidade=qtd_conjunto,
                preco=preco_conjunto,
                categoria=item_a.categoria,
                marca=item_a.marca,
                preco_final=preco_final_conjunto,
            )
            conjunto = self._normalize_record(conjunto)

            item_a.quantidade = max(item_a.quantidade - qtd_conjunto, 0)
            item_b.quantidade = max(item_b.quantidade - qtd_conjunto, 0)

            resultantes: List[ProductRecord] = []
            removed = 0
            for idx, item in enumerate(items):
                if idx == idx_a:
                    if item_a.quantidade > 0:
                        resultantes.append(item_a)
                    else:
                        removed += 1
                    continue
                if idx == idx_b:
                    if item_b.quantidade > 0:
                        resultantes.append(item_b)
                    else:
                        removed += 1
                    continue
                resultantes.append(item)

            resultantes.append(conjunto)

            self._momentary.clear()
            self._momentary.extend(resultantes)
            self._active_store.overwrite(resultantes)
            self._merge_brands_from_items(resultantes)

            return {
                "created": 1,
                "removed": removed,
                "remaining_a": item_a.quantidade,
                "remaining_b": item_b.quantidade,
            }

    def join_with_grades(self) -> Dict[str, int]:
        with _lock:
            items = self._momentary.list()
            if not items:
                return {"originais": 0, "resultantes": 0, "removidos": 0, "atualizados_grades": 0}

            grupos: Dict[str, Dict[str, Any]] = {}
            for item in items:
                codigo = (item.codigo or "").strip()
                if not codigo:
                    # ignora itens sem código na consolidação de grades
                    continue
                entrada = grupos.setdefault(
                    codigo,
                    {
                        "base": ProductRecord.from_dict(item.to_dict()),
                        "grades": {},
                        "qtd_livre": 0,
                        "nome_base": _strip_size_suffix(item.nome or ""),
                    },
                )

                if item.grades:
                    for g in item.grades:
                        try:
                            tamanho = str(getattr(g, "tamanho", "") or "").strip()
                            quantidade = int(getattr(g, "quantidade", 0) or 0)
                        except Exception:
                            continue
                        if not tamanho or quantidade <= 0:
                            continue
                        entrada["grades"][tamanho] = entrada["grades"].get(tamanho, 0) + quantidade
                else:
                    size = _detect_size_from_name(item.nome or "")
                    qtd = int(getattr(item, "quantidade", 0) or 0) or 1
                    if size:
                        entrada["grades"][size] = entrada["grades"].get(size, 0) + qtd
                    else:
                        entrada["qtd_livre"] += qtd

            resultantes: List[ProductRecord] = []
            atualizados_grades = 0
            for codigo, data in grupos.items():
                base = data["base"]
                if data["nome_base"]:
                    base.nome = data["nome_base"]
                if data["grades"]:
                    base.grades = [GradeItem(tamanho=k, quantidade=v) for k, v in data["grades"].items()]
                    base.quantidade = sum(g.quantidade for g in base.grades)
                    atualizados_grades += 1
                else:
                    if data["qtd_livre"] > 0:
                        base.quantidade = data["qtd_livre"]
                resultantes.append(self._normalize_record(base))

            self._momentary.clear()
            self._momentary.extend(resultantes)
            self._active_store.overwrite(resultantes)

            return {
                "originais": len(items),
                "resultantes": len(resultantes),
                "removidos": len(items) - len(resultantes),
                "atualizados_grades": atualizados_grades,
            }

    def _calculate_metrics(self, registros: Iterable[ProductRecord]) -> Tuple[int, int]:
        itens = list(registros)
        tempo = len(itens) * 40
        caracteres = 0
        for item in itens:
            caracteres += len(item.nome or "")
            caracteres += len(item.codigo or "")
            caracteres += len(item.marca or "")
            descricao = item.descricao_completa or ""
            caracteres += len(descricao)
        return tempo, caracteres

    def _load_metrics(self) -> Dict[str, int]:
        if not METRICS_FILE.exists():
            return {
                "tempo_economizado": 0,
                "caracteres_digitados": 0,
            }
        try:
            data = json.loads(METRICS_FILE.read_text(encoding="utf-8") or "{}")
            tempo = int(data.get("tempo_economizado", 0))
            caracteres = int(data.get("caracteres_digitados", 0))
            return {
                "tempo_economizado": tempo,
                "caracteres_digitados": caracteres,
            }
        except Exception:
            return {
                "tempo_economizado": 0,
                "caracteres_digitados": 0,
            }

    def _save_metrics_locked(self) -> None:
        try:
            METRICS_FILE.write_text(
                json.dumps(self._metrics, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception:
            pass

    def format_codes(self, options: Dict[str, Any]) -> Dict[str, Any]:
        remover_prefixo = bool(options.get("remover_prefixo5"))
        remover_zeros = bool(options.get("remover_zeros_a_esquerda"))
        ultimos_digitos = options.get("ultimos_digitos")
        primeiros_digitos = options.get("primeiros_digitos")
        remover_ultimos_numeros = options.get("remover_ultimos_numeros")
        remover_primeiros_numeros = options.get("remover_primeiros_numeros")
        prefixo_utilizado: Optional[str] = None

        with _lock:
            items = self._momentary.list()
            if not items:
                return {"total": 0, "alterados": 0, "prefixo": prefixo_utilizado}

            for item in items:
                if not item.codigo_original:
                    item.codigo_original = item.codigo

            if remover_prefixo:
                candidatos = [
                    item.codigo.strip()[:5]
                    for item in items
                    if len(item.codigo.strip()) >= 5 and item.codigo.strip()[:5].isdigit()
                ]
                if candidatos:
                    prefixo, quantidade = Counter(candidatos).most_common(1)[0]
                    if quantidade >= 5:
                        prefixo_utilizado = prefixo
                    else:
                        prefixo_utilizado = None
                else:
                    prefixo_utilizado = None

            alterados = 0
            for item in items:
                codigo_original = item.codigo
                codigo_novo = codigo_original

                if prefixo_utilizado and codigo_novo.startswith(prefixo_utilizado):
                    codigo_novo = codigo_novo[len(prefixo_utilizado) :] or codigo_novo

                if remover_zeros:
                    codigo_sem_zeros = codigo_novo.lstrip("0")
                    codigo_novo = codigo_sem_zeros or "0"

                if isinstance(remover_ultimos_numeros, int) and remover_ultimos_numeros > 0:
                    codigo_novo = _remove_digits_from_end(codigo_novo, remover_ultimos_numeros)

                if isinstance(remover_primeiros_numeros, int) and remover_primeiros_numeros > 0:
                    codigo_novo = _remove_digits_from_start(codigo_novo, remover_primeiros_numeros)

                if isinstance(primeiros_digitos, int) and primeiros_digitos > 0:
                    apenas_digitos_inicio = re.sub(r"\D+", "", codigo_novo)
                    if apenas_digitos_inicio:
                        if len(apenas_digitos_inicio) >= primeiros_digitos:
                            codigo_novo = apenas_digitos_inicio[:primeiros_digitos]
                        else:
                            codigo_novo = apenas_digitos_inicio
                    else:
                        codigo_novo = codigo_novo[:primeiros_digitos]

                if isinstance(ultimos_digitos, int) and ultimos_digitos > 0:
                    apenas_digitos = re.sub(r"\D+", "", codigo_novo)
                    if len(apenas_digitos) >= ultimos_digitos:
                        codigo_novo = apenas_digitos[-ultimos_digitos:]
                    elif apenas_digitos:
                        codigo_novo = apenas_digitos

                if codigo_novo != codigo_original:
                    if not item.codigo_original:
                        item.codigo_original = codigo_original
                    item.codigo = codigo_novo
                    alterados += 1

            self._momentary.clear()
            self._momentary.extend(items)
            self._active_store.overwrite(items)

        return {"total": len(items), "alterados": alterados, "prefixo": prefixo_utilizado}

    def restore_original_codes(self) -> Dict[str, int]:
        with _lock:
            items = self._momentary.list()
            if not items:
                return {"total": 0, "restaurados": 0}

            restaurados = 0
            for item in items:
                if item.codigo_original and item.codigo != item.codigo_original:
                    item.codigo = item.codigo_original
                    restaurados += 1

            if restaurados:
                self._momentary.clear()
                self._momentary.extend(items)
                self._active_store.overwrite(items)

            return {"total": len(items), "restaurados": restaurados}

    def reorder_by_keys(self, keys: List[str]) -> int:
        with _lock:
            items = self._momentary.list()
            if not items:
                return 0

            mapping = {self._make_key(item): item for item in items}
            ordered: List[ProductRecord] = []
            vistos = set()

            for key in keys:
                item = mapping.get(key)
                if item is None or key in vistos:
                    continue
                ordered.append(item)
                vistos.add(key)

            for key, item in mapping.items():
                if key not in vistos:
                    ordered.append(item)

            self._momentary.clear()
            self._momentary.extend(ordered)
            self._active_store.overwrite(ordered)
            return len(ordered)

    def apply_margin(self, margin: float) -> int:
        with _lock:
            items = self._momentary.list()
            if not items:
                return 0

            updated = 0
            for item in items:
                novo_preco = self._calculate_sale_price(item.preco, margin)
                if novo_preco != item.preco_final:
                    item.preco_final = novo_preco
                    updated += 1

            self._momentary.clear()
            self._momentary.extend(items)
            self._active_store.overwrite(items)
            return updated

    def improve_descriptions(
        self,
        remove_numbers: bool,
        remove_special: bool,
        terms: Iterable[str],
    ) -> Dict[str, int]:
        normalized_terms = [term.strip() for term in terms if term and term.strip()]
        # sort by length descending to handle multi-word before single-word
        normalized_terms.sort(key=len, reverse=True)

        with _lock:
            items = self._momentary.list()
            if not items:
                return {"total": 0, "modificados": 0}

            alterados = 0
            for item in items:
                modificou = False

                def _sanitize(value: str) -> str:
                    texto = value
                    if remove_numbers:
                        texto = re.sub(r"\d+", "", texto)
                    if remove_special:
                        texto = re.sub(r"[^\w\s]", "", texto, flags=re.UNICODE)
                    if normalized_terms:
                        texto = _remove_terms(texto, normalized_terms)
                    return re.sub(r"\s+", " ", texto).strip()

                campos = [
                    ("descricao_completa", item.descricao_completa or ""),
                    ("nome", item.nome or ""),
                ]

                for attr, valor in campos:
                    if not valor:
                        continue
                    novo = _sanitize(valor)
                    if novo != valor:
                        setattr(item, attr, novo)
                        modificou = True

                if modificou:
                    alterados += 1

            if alterados:
                self._momentary.clear()
                self._momentary.extend(items)
                self._active_store.overwrite(items)

            return {"total": len(items), "modificados": alterados}

    def delete_by_key(self, ordering_key: str) -> bool:
        with _lock:
            items = self._momentary.list()
            mapping = {self._make_key(item): item for item in items}
            if ordering_key not in mapping:
                return False

            filtered = [item for key, item in mapping.items() if key != ordering_key]
            self._momentary.clear()
            self._momentary.extend(filtered)
            self._active_store.overwrite(filtered)
            return True

    def get_active_file(self) -> Path:
        return self._active_store.file_path

    def set_default_margin(self, margin: float) -> float:
        if margin <= 0:
            raise ValueError("Margem deve ser positiva")
        salvar_margem_padrao(margin)
        return margin

    def get_default_margin(self) -> float:
        margin = carregar_margem_padrao()
        if margin is None or margin <= 0:
            return 1.0
        return margin

    @staticmethod
    def _parse_price(value: str) -> Optional[float]:
        if value is None:
            return None
        texto = str(value).strip()
        if not texto:
            return None
        texto = texto.replace("R$", "").replace(" ", "").replace("\u00a0", "")

        if "." in texto and "," in texto:
            texto = texto.replace(".", "").replace(",", ".")
        elif "," in texto:
            texto = texto.replace(",", ".")
        else:
            texto = texto
        try:
            return float(texto)
        except ValueError:
            return None

    @staticmethod
    def _format_price(value: Optional[float]) -> Optional[str]:
        if value is None:
            return None
        return f"{value:.2f}".replace(".", ",")

    def _calculate_sale_price(self, preco_custo: str, margin: Optional[float] = None) -> Optional[str]:
        custo = self._parse_price(preco_custo)
        if custo is None:
            return None

        margem = margin if margin is not None else self.get_default_margin()
        if margem is None or margem <= 0:
            margem = 1.0

        bruto = custo * margem
        inteiro = math.floor(bruto)
        alvo = inteiro + 0.9
        if alvo < bruto:
            alvo = inteiro + 1.9
        return self._format_price(alvo)

    # ------------------------------------------------------------------
    # Helpers internos
    # ------------------------------------------------------------------

    def _load_brands(self) -> List[str]:
        if BRANDS_FILE.exists():
            try:
                data = json.loads(BRANDS_FILE.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    return [str(item).strip() for item in data if str(item).strip()]
            except json.JSONDecodeError:
                pass
        return list(DEFAULT_BRANDS)

    def _save_brands_locked(self) -> None:
        BRANDS_FILE.write_text(json.dumps(self._brands, ensure_ascii=False, indent=2), encoding="utf-8")

    @staticmethod
    def _normalize_brand(marca: str) -> str:
        return str(marca or "").strip()

    def _add_brand_no_lock(self, marca: str) -> bool:
        nome = self._normalize_brand(marca)
        if not nome:
            return False
        if nome.lower() in self._brand_index:
            return False
        self._brands.append(nome)
        self._brand_index.add(nome.lower())
        return True

    def _merge_brands_from_items(self, items: Iterable[ProductRecord]) -> None:
        mudou = False
        for item in items:
            mudou = self._add_brand_no_lock(item.marca) or mudou
        if mudou:
            self._save_brands_locked()

    def _compute_totals(self, items: Iterable[ProductRecord]) -> Dict[str, float]:
        quantidade = 0
        custo_total = 0.0
        venda_total = 0.0

        for item in items:
            quantidade += item.quantidade

            preco_custo = self._parse_price(item.preco) or 0.0
            preco_venda = None
            if item.preco_final:
                preco_venda = self._parse_price(item.preco_final)
            if preco_venda is None:
                calculado = self._calculate_sale_price(item.preco)
                preco_venda = self._parse_price(calculado) or 0.0

            custo_total += preco_custo * item.quantidade
            venda_total += preco_venda * item.quantidade

        return {
            "quantidade": quantidade,
            "custo": round(custo_total, 2),
            "venda": round(venda_total, 2),
        }

    # ------------------------------------------------------------------
    # Romaneio helpers
    # ------------------------------------------------------------------
    @staticmethod
    def save_romaneio_text(content: str, prefix: str = "romaneio") -> Path:
        from pathlib import Path as _Path
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        desktop_dir = _Path.home() / "Desktop" / "RomaneiosProcessados"
        try:
            desktop_dir.mkdir(parents=True, exist_ok=True)
            file_path = desktop_dir / f"{prefix}_{timestamp}.txt"
            file_path.write_text(content, encoding="utf-8")
            return file_path
        except Exception:
            file_path = ROMANEIO_DIR / f"{prefix}_{timestamp}.txt"
            file_path.write_text(content, encoding="utf-8")
            return file_path

    @staticmethod
    def parse_romaneio_lines(content: str) -> Iterator[ProductRecord]:
        number_regex = re.compile(r"\d")
        delimiter_only = re.compile(r"^[\s\-|]+$")

        for raw_line in content.splitlines():
            line = raw_line.strip()
            if not line or delimiter_only.match(line):
                continue

            parts = [segment.strip() for segment in line.split("|")]
            parts = [segment for segment in parts if segment]
            if len(parts) < 3:
                continue

            codigo = parts[0]
            if not number_regex.search(codigo):
                continue

            descricao = parts[1] if len(parts) > 1 else ""

            quantidade_raw = parts[2] if len(parts) > 2 else "1"
            quantidade_str = quantidade_raw.replace(" ", "")
            if "," in quantidade_str and "." in quantidade_str:
                quantidade_str = quantidade_str.replace(".", "").replace(",", ".")
            else:
                quantidade_str = quantidade_str.replace(",", ".")

            try:
                quantidade_valor = float(quantidade_str)
            except ValueError:
                quantidade_valor = 1.0

            quantidade = max(int(round(quantidade_valor)), 1)

            preco = parts[3] if len(parts) > 3 else ""

            yield ProductRecord(
                nome=descricao,
                codigo=codigo,
                codigo_original=codigo,
                quantidade=quantidade,
                preco=preco,
                categoria="",
                marca="",
                preco_final=None,
            )


product_db = ProductDatabase()
