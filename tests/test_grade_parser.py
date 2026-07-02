from __future__ import annotations

from app.domain.grades.parser import parse_grade_extraction


def test_parse_grade_extraction_accepts_json_embedded_in_text() -> None:
    content = (
        "Resultado extraido do romaneio:\n"
        '{"items":[{"codigo":"C10","nome":"CAMISETA","grades":{"P":2,"M":1}}]}\n'
        "Conferencia finalizada."
    )

    items, warnings = parse_grade_extraction(content, allowed_sizes=["P", "M"])

    assert warnings == []
    assert len(items) == 1
    assert items[0].codigo == "C10"
    assert items[0].nome == "CAMISETA"
    assert items[0].grades == {"P": 2, "M": 1}


def test_parse_grade_extraction_skips_unrelated_embedded_json_array() -> None:
    content = (
        "Tentativa anterior [1] sem estrutura util.\n"
        '[{"codigo":"C20","nome":"CALCA","grades":[{"tamanho":"G","quantidade":3}]}]'
    )

    items, warnings = parse_grade_extraction(content, allowed_sizes=["G"])

    assert warnings == []
    assert len(items) == 1
    assert items[0].grades == {"G": 3}
