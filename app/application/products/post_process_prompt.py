from __future__ import annotations

import re

from app.domain.products.entities import Product


def _table_field(value: object) -> str:
    text = str(value or "").strip()
    text = re.sub(r"\s+", " ", text)
    return text.replace("|", "/")


def build_post_process_message() -> str:
    return (
        "Voce esta revisando itens ja extraidos de romaneios para uso real de loja. "
        "Seu objetivo e sugerir melhorias conservadoras para descricao, codigo e custo sem inventar dados incertos. "
        "Regras para descricao: detecte caracteres estranhos, palavras sem relacao com o nome final de venda, numeros soltos, "
        "anomalias e formatacao ruim; limpe e reescreva para um nome curto, claro e natural para uso de loja, mas sem supor "
        "marca, tecido, genero, cor ou detalhe que nao estejam realmente confiaveis. "
        "Regras para codigo: detecte repeticoes sem utilidade, excesso de caracteres e trechos redundantes; mantenha apenas a "
        "parte primordial que ainda diferencie o item e ajude os funcionarios a reconhecer o produto. "
        "Regras para custo: quando houver variacoes visuais pequenas e conflitantes no mesmo padrao decimal, como 40,46 e 40,47, "
        "prefira normalizar para um valor superior terminado em 0,50 para reduzir conflito visual; nao altere custos sem motivo claro. "
        "Retorne JSON com uma lista 'items'. Cada item deve conter: ordering_key, nome_atual, nome_sugerido, codigo_atual, "
        "codigo_sugerido, preco_atual, preco_sugerido, acoes, justificativa e confianca. "
        "Em 'acoes', use apenas os valores entre: manter, ajustar_descricao, ajustar_codigo, ajustar_preco, ajustar_tudo. "
        "Se nao houver seguranca suficiente, mantenha os valores atuais e explique na justificativa. "
        "Este fluxo ainda esta em modo skeleton/dry-run, entao priorize formato consistente e decisao conservadora."
    )


def build_post_process_products_text(products: list[Product]) -> str:
    if not products:
        return ""
    lines = ["ordering_key|codigo|nome|descricao_completa|quantidade|preco"]
    for item in products:
        lines.append(
            "|".join(
                [
                    _table_field(item.ordering_key()),
                    _table_field(item.codigo),
                    _table_field(item.nome),
                    _table_field(item.descricao_completa),
                    _table_field(int(item.quantidade or 0)),
                    _table_field(item.preco),
                ]
            )
        )
    return "\n".join(lines)


def build_post_process_context_text(*, total_products: int, review_products: list[Product]) -> str:
    summary_lines = [
        f"total_produtos_lista={int(total_products or 0)}",
        f"total_produtos_para_revisao={len(review_products)}",
        "revise apenas os itens enviados abaixo; os demais itens da lista ja estao fora do escopo de surpresa/ambiguidade.",
    ]
    return "\n".join(summary_lines)
