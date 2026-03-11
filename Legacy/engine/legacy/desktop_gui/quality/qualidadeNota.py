#!/usr/bin/env python3
"""
Módulo de Verificação de Qualidade do Romaneio
- Avalia a qualidade dos itens extraídos para o domínio de roupas/acessórios
- Regras configuráveis via data/config_quality.json
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import json
import re
from pathlib import Path
from datetime import datetime

CONFIG_DEFAULT = {
    "min_nome_len": 3,
    "max_nome_len": 120,
    "codigo_regex": r"^[A-Za-z0-9\-_/.]{2,30}$",
    "min_codigo_len": 2,
    "max_codigo_len": 30,
    "min_qtd": 1,
    "max_qtd": 999,
    "min_custo": 0.01,
    "max_custo": 5000.0,
    "custo_alerta_baixo": 5.0,
    "custo_alerta_alto": 1500.0,
    "margem_min_alerta": 0.10,   # 10%
    "margem_max_alerta": 4.00,   # 400%
    "duplicidade_codigo": "alerta",
    "palavras_chave_produto": [
        "CAMISA", "CALCA", "CALÇA", "VESTIDO", "CINTO", "BOLSA", "MEIA", "BLUSA", "JAQUETA", "SHORT",
        "REGATA", "SAIA", "BERMUDA", "MOLETOM", "CARDIGAN", "MACACAO", "MACACÃO", "SAPATO", "TENIS", "TÊNIS",
        "CONJUNTO", "MINI", "SANDALIA", "SANDÁLIA", "CHINELO", "BOTA", "SAPATILHA"
    ],
    "limiar_score_atencao": 85,
    "limiar_score_critico": 70,
    "modo_bloqueio_erros": False,
    "habilitar_log": True,
}

CONFIG_PATH = Path(__file__).resolve().parents[2] / "data" / "config_quality.json"
LOG_PATH = Path(__file__).resolve().parents[2] / "data" / "quality_logs.jsonl"


def _load_config() -> Dict[str, Any]:
    try:
        if CONFIG_PATH.exists():
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            # merge defaults
            cfg = {**CONFIG_DEFAULT, **(data or {})}
            return cfg
    except Exception:
        pass
    return CONFIG_DEFAULT.copy()


@dataclass
class Issue:
    idx: int
    codigo: str
    severidade: str  # "erro" | "alerta"
    tipo: str
    mensagem: str


@dataclass
class QualityReport:
    score_geral: int
    itens_ok: int
    itens_com_alerta: int
    itens_com_erro: int
    issues: List[Issue] = field(default_factory=list)
    sugestoes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "score_geral": self.score_geral,
            "itens_ok": self.itens_ok,
            "itens_com_alerta": self.itens_com_alerta,
            "itens_com_erro": self.itens_com_erro,
            "issues": [issue.__dict__ for issue in self.issues],
            "sugestoes": self.sugestoes,
        }


def _str_norm(s: str) -> str:
    return (s or "").strip()


def _is_nome_pobre(nome: str, palavras_chave: List[str]) -> bool:
    if not nome or len(nome) < 3:
        return True
    # avaliar se contem alguma palavra-chave típica do segmento
    upper = nome.upper()
    return not any(p in upper for p in palavras_chave)


def _first_non_empty(p: Dict[str, Any], keys: List[str]):
    for k in keys:
        if k in p and p.get(k) not in (None, ""):
            return p.get(k)
    return None


def _avaliar_item(idx: int, p: Dict[str, Any], cfg: Dict[str, Any], cod_dups: Dict[str, int]) -> List[Issue]:
    issues: List[Issue] = []
    # Usar campos exatos do parser
    nome = _str_norm(str(p.get("nome", "")))
    marca = _str_norm(str(p.get("marca", "")))
    codigo = _str_norm(str(p.get("codigo", "")))
    qtd = p.get("quantidade")
    custo = p.get("preco")
    preco_final = p.get("preco_final")
    categoria = _str_norm(str(p.get("categoria", ""))) 

    # NOME - Validações inteligentes
    if not nome or len(nome) < cfg["min_nome_len"]:
        issues.append(Issue(idx, codigo, "erro", "nome_invalido", "Nome ausente ou muito curto."))
    elif len(nome) > cfg["max_nome_len"]:
        issues.append(Issue(idx, codigo, "erro", "nome_muito_longo", "Nome muito longo (>120 chars)."))
    else:
        # Nome genérico demais (só uma palavra)
        if len(nome.split()) <= 1:
            issues.append(Issue(idx, codigo, "erro", "nome_generico", "Nome muito genérico (uma palavra só)."))
        
        # Nome com ruído de cor/código (detecta COR seguido de números/códigos)
        if re.search(r"\bCOR\b[\s]*\d", nome.upper()):
            issues.append(Issue(idx, codigo, "erro", "nome_ruido_cor", "Nome contém código de cor/tamanho; limpe para título claro."))
        
        # Nome com códigos numéricos longos (>5 dígitos seguidos)
        elif re.search(r"\d{6,}", nome):
            issues.append(Issue(idx, codigo, "erro", "nome_codigo_numerico", "Nome contém códigos numéricos longos; simplifique."))
        
        # Nome terminando com números (códigos no final)
        elif re.search(r"\d+\s*\d*\s*$", nome):
            issues.append(Issue(idx, codigo, "erro", "nome_codigo_final", "Nome termina com códigos numéricos; remova."))
        
        # Nome com muitos números misturados
        elif len(re.findall(r"\d+", nome)) >= 3:
            issues.append(Issue(idx, codigo, "erro", "nome_muitos_numeros", "Nome com muitos números; simplifique para descrição clara."))
        
        # Nome sem palavras-chave do produto (só alerta)
        elif _is_nome_pobre(nome, cfg["palavras_chave_produto"]):
            issues.append(Issue(idx, codigo, "alerta", "nome_pobre", "Nome sem palavras típicas de produto."))

    # codigo
    if not codigo or len(codigo) < cfg["min_codigo_len"] or len(codigo) > cfg["max_codigo_len"]:
        issues.append(Issue(idx, codigo, "erro", "codigo_invalido", "Código ausente ou de tamanho inválido."))
    else:
        if not re.match(cfg["codigo_regex"], codigo):
            issues.append(Issue(idx, codigo, "alerta", "codigo_formato", "Código com formato atípico."))

    # QUANTIDADE - Validações práticas
    try:
        # Tentar converter quantidade (pode vir como string "67,99" ou float)
        if isinstance(qtd, str):
            qtd_clean = qtd.replace(',', '.').strip()
            qtd_float = float(qtd_clean)
        else:
            qtd_float = float(qtd) if qtd is not None else 0
        qtd_int = int(qtd_float)
    except Exception:
        qtd_int = 0
        qtd_float = 0
    
    if qtd_int <= 0:
        issues.append(Issue(idx, codigo, "erro", "quantidade_invalida", "Quantidade zero ou inválida."))
    elif qtd_float != qtd_int:  # Não é número inteiro
        issues.append(Issue(idx, codigo, "erro", "quantidade_nao_unitaria", f"Quantidade não unitária ({qtd}); deveria ser 1, 2, 3..."))
    elif qtd_int > cfg["max_qtd"]:
        issues.append(Issue(idx, codigo, "alerta", "quantidade_alta", "Quantidade muito alta (>999)."))

    # custo
    def _parse_num(x) -> float:
        try:
            s = str(x).strip()
            if not s:
                return -1.0
            # Caso 1: possui ambos '.' e ',' => assume '.' milhares e ',' decimal (pt-BR)
            if '.' in s and ',' in s:
                s2 = s.replace('.', '').replace(',', '.')
                return float(s2)
            # Caso 2: apenas ',' => vírgula decimal
            if ',' in s:
                return float(s.replace(',', '.'))
            # Caso 3: apenas '.' => pode ser decimal inglês
            return float(s)
        except Exception:
            return -1.0

    custo_f = _parse_num(custo)
    if custo_f < cfg["min_custo"]:
        issues.append(Issue(idx, codigo, "erro", "custo_invalido", "Preço de custo ausente ou zero."))
    else:
        if custo_f < cfg["custo_alerta_baixo"]:
            issues.append(Issue(idx, codigo, "alerta", "custo_muito_baixo", "Preço de custo muito baixo."))
        if custo_f > cfg["custo_alerta_alto"]:
            issues.append(Issue(idx, codigo, "alerta", "custo_muito_alto", "Preço de custo muito alto."))

    # preco_final/margem
    if preco_final is not None:
        try:
            pf = _parse_num(preco_final)
            if pf < custo_f:
                issues.append(Issue(idx, codigo, "alerta", "margem_negativa", "Preço final abaixo do custo."))
            else:
                if custo_f > 0:
                    margem = (pf - custo_f) / max(custo_f, 1e-9)
                    if margem < cfg["margem_min_alerta"] or margem > cfg["margem_max_alerta"]:
                        issues.append(Issue(idx, codigo, "alerta", "margem_atipica", "Margem fora do intervalo típico."))
        except Exception:
            pass

    # MARCA - Validações
    if not marca or marca.upper() in ["GENERICA", "GENÉRICA", "SEM MARCA"]:
        issues.append(Issue(idx, codigo, "alerta", "marca_ausente", "Marca não identificada ou genérica."))
    
    # CATEGORIA - Validações
    if not categoria:
        issues.append(Issue(idx, codigo, "alerta", "categoria_ausente", "Categoria não definida."))
    
    # PREÇO FINAL - Validações de margem
    if preco_final and custo_f > 0:
        try:
            pf = _parse_num(preco_final)
            if pf > 0:
                margem = (pf - custo_f) / custo_f
                if margem < 0.05:  # menos de 5% de margem
                    issues.append(Issue(idx, codigo, "erro", "margem_muito_baixa", "Margem de lucro muito baixa (<5%)."))
                elif margem > 10.0:  # mais de 1000% de margem
                    issues.append(Issue(idx, codigo, "alerta", "margem_muito_alta", "Margem de lucro muito alta (>1000%)."))
        except Exception:
            pass

    # duplicidades
    if codigo:
        if cod_dups.get(codigo, 0) > 1:
            sev = "erro" if cfg.get("duplicidade_codigo") == "erro" else "alerta"
            issues.append(Issue(idx, codigo, sev, "codigo_duplicado", "Código duplicado no romaneio."))

    return issues


def _score(itens: int, issues: List[Issue]) -> int:
    # penalidades simples
    erros = sum(1 for i in issues if i.severidade == "erro")
    alertas = sum(1 for i in issues if i.severidade == "alerta")
    score = 100 - erros * 10 - alertas * 3
    return max(0, min(100, score))


def avaliar_romaneio(produtos: List[Dict[str, Any]], contexto: Optional[Dict[str, Any]] = None) -> QualityReport:
    cfg = _load_config()

    # mapear duplicidades de código
    cod_counts: Dict[str, int] = {}
    for p in produtos:
        c = _str_norm(str(p.get("codigo", "")))
        if not c:
            continue
        cod_counts[c] = cod_counts.get(c, 0) + 1

    all_issues: List[Issue] = []
    for idx, p in enumerate(produtos):
        all_issues.extend(_avaliar_item(idx, p, cfg, cod_counts))

    score = _score(len(produtos), all_issues)
    itens_com_erro = len({i.idx for i in all_issues if i.severidade == "erro"})
    itens_com_alerta = len({i.idx for i in all_issues if i.severidade == "alerta"})
    itens_ok = max(0, len(produtos) - len({i.idx for i in all_issues}))

    report = QualityReport(
        score_geral=score,
        itens_ok=itens_ok,
        itens_com_alerta=itens_com_alerta,
        itens_com_erro=itens_com_erro,
        issues=all_issues,
        sugestoes=[],
    )

    # log opcional
    if cfg.get("habilitar_log", True):
        try:
            LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(LOG_PATH, "a", encoding="utf-8") as f:
                payload = {
                    "ts": datetime.utcnow().isoformat() + "Z",
                    "score": report.score_geral,
                    "counts": {
                        "ok": report.itens_ok,
                        "alerta": report.itens_com_alerta,
                        "erro": report.itens_com_erro,
                    },
                    "issues": [i.__dict__ for i in report.issues[:50]],  # limitar
                }
                f.write(json.dumps(payload, ensure_ascii=False) + "\n")
        except Exception:
            pass

    return report
