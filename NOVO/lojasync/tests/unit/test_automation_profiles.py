from __future__ import annotations

from pathlib import Path

from app.application.automation.profiles import (
    has_gradebot_configuration,
    load_json_object,
    normalize_gradebot_config,
)


def test_load_json_object_repairs_trailing_commas(tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    path.write_text('{"buttons":{"focus_app":{"x":1,"y":2},},"erp_size_order":["P",],}', encoding="utf-8")

    payload = load_json_object(path, repair=True)

    assert payload["buttons"]["focus_app"]["x"] == 1
    repaired = path.read_text(encoding="utf-8")
    assert ",}" not in repaired
    assert ",]" not in repaired


def test_has_gradebot_configuration_detects_empty_defaults() -> None:
    empty = normalize_gradebot_config({})
    configured = normalize_gradebot_config(
        {
            "buttons": {"focus_app": {"x": 10, "y": 20}},
            "grid": {"first_quant_cell": [30, 40], "row_height": 17},
            "erp_size_order": ["P", "M"],
        }
    )

    assert has_gradebot_configuration(empty) is False
    assert has_gradebot_configuration(configured) is True
