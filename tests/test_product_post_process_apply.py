from __future__ import annotations

import json

from app.application.products.post_process_apply import apply_post_process_updates, extract_post_process_suggestions
from app.domain.products.entities import Product


def test_extract_post_process_suggestions_reads_fenced_json() -> None:
    payload = """
    A resposta segue abaixo:

    ```json
    {"items":[{"ordering_key":"abc","nome_sugerido":"Produto limpo"},{"nome_sugerido":"sem chave"}]}
    ```
    """

    suggestions = extract_post_process_suggestions(payload)

    assert list(suggestions) == ["abc"]
    assert suggestions["abc"]["nome_sugerido"] == "Produto limpo"


def test_apply_post_process_updates_counts_llm_and_local_changes() -> None:
    product_with_llm = Product(
        nome="JAQUETA SOLIRA",
        codigo="AB12-AB12",
        quantidade=2,
        preco="90,91",
        categoria="",
        marca="",
        descricao_completa="JAQUETA SOLIRA *SA-FKII* AD",
    )
    product_with_local_cleanup = Product(
        nome="CALA JOGGER BASICO(A)",
        codigo="1000108790",
        quantidade=2,
        preco="33,49",
        categoria="",
        marca="",
        descricao_completa="CALA JOGGER BASICO(A) Cor 00004 Tam 8",
    )
    items = [product_with_llm, product_with_local_cleanup]
    llm_payload = json.dumps(
        {
            "items": [
                {
                    "ordering_key": product_with_llm.ordering_key(),
                    "nome_sugerido": "JAQUETA SOLAR",
                    "codigo_sugerido": "AB12",
                    "preco_sugerido": "90,91",
                    "acoes": "ajustar_tudo",
                    "confianca": 0.91,
                }
            ]
        }
    )

    result = apply_post_process_updates(items, llm_response_text=llm_payload, margin=2.0)

    assert result["modificados"] == 2
    assert result["llm_suggestions_applied"] == 1
    assert result["local_adjustments_applied"] == 1
    assert items[0].nome == "JAQUETA SOLAR"
    assert items[0].codigo == "AB12"
    assert items[0].preco == "91,00"
    assert items[1].nome == "CALCA JOGGER BASICO"
    assert items[1].preco == "33,50"
