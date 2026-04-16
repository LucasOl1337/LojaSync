from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


_TRAILING_COMMA_RE = re.compile(r",(?=\s*[}\]])")
_TARGET_KEYS = (
    "byte_empresa_posicao",
    "campo_descricao",
    "tres_pontinhos",
    "cadastro_completo_passo_1",
    "cadastro_completo_passo_2",
    "cadastro_completo_passo_3",
    "cadastro_completo_passo_4",
)
_DEFAULT_ERP_SIZE_ORDER = (
    "PP",
    "P",
    "M",
    "G",
    "GG",
    "XG",
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
    "32",
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
    "G1",
    "G2",
    "G3",
    "G4",
    "G5",
    "G6",
    "6M",
    "9M",
    "12M",
    "18M",
    "U",
    "XXG",
    "XGG",
    "P/M",
)


def _canonicalize_size_label(value: Any) -> str:
    text = str(value or "").strip().upper()
    text = re.sub(r"[^A-Z0-9]+", "", text)
    if not text:
        return ""
    if text.isdigit():
        try:
            number = int(text)
        except Exception:
            return ""
        return str(number) if number > 0 else ""
    return text


def _clean_json_text(text: str) -> str:
    return _TRAILING_COMMA_RE.sub("", text or "")


def load_json_object(path: Path, *, repair: bool = False) -> dict[str, Any]:
    if not path.exists():
        return {}

    try:
        raw_text = path.read_text(encoding="utf-8")
    except Exception:
        return {}

    payload: Any
    try:
        payload = json.loads(raw_text)
        normalized_text = raw_text
    except Exception:
        normalized_text = _clean_json_text(raw_text)
        try:
            payload = json.loads(normalized_text)
        except Exception:
            return {}

    if repair and normalized_text != raw_text:
        save_json_object(path, payload if isinstance(payload, dict) else {})

    return payload if isinstance(payload, dict) else {}


def save_json_object(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def normalize_point(value: Any) -> dict[str, int] | None:
    if isinstance(value, dict) and "x" in value and "y" in value:
        try:
            return {"x": int(value["x"]), "y": int(value["y"])}
        except Exception:
            return None
    if isinstance(value, (list, tuple)) and len(value) >= 2:
        try:
            return {"x": int(value[0]), "y": int(value[1])}
        except Exception:
            return None
    return None


def normalize_targets(payload: Any) -> dict[str, Any]:
    data = payload if isinstance(payload, dict) else {}
    normalized: dict[str, Any] = {}

    title = data.get("title")
    if isinstance(title, str):
        normalized["title"] = title.strip()

    for key in _TARGET_KEYS:
        point = normalize_point(data.get(key))
        if point is not None:
            normalized[key] = point

    return normalized


def _normalize_string_list(value: Any) -> list[str]:
    items = value if isinstance(value, list) else []
    normalized: list[str] = []
    seen: set[str] = set()
    for item in items:
        text = _canonicalize_size_label(item)
        if not text:
            continue
        key = text.upper()
        if key in seen:
            continue
        seen.add(key)
        normalized.append(key)
    return normalized


def _normalize_ui_families(value: Any) -> list[dict[str, Any]]:
    items = value if isinstance(value, list) else []
    normalized: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            continue
        family_id = str(item.get("id") or f"family-{index + 1}").strip().lower()
        if not family_id or family_id in seen_ids:
            family_id = f"family-{index + 1}"
        seen_ids.add(family_id)
        label = str(item.get("label") or f"Familia {index + 1}").strip() or f"Familia {index + 1}"
        sizes = _normalize_string_list(item.get("sizes"))
        normalized.append(
            {
                "id": family_id,
                "label": label,
                "sizes": sizes,
            }
        )
    return normalized


def normalize_gradebot_config(payload: Any) -> dict[str, Any]:
    data = payload if isinstance(payload, dict) else {}

    buttons_raw = data.get("buttons")
    buttons_data = buttons_raw if isinstance(buttons_raw, dict) else {}
    buttons: dict[str, dict[str, int]] = {}
    for key, value in buttons_data.items():
        point = normalize_point(value)
        if point is not None:
            buttons[str(key).strip()] = point

    if "open_grade" not in buttons and "alterar_grade" in buttons:
        buttons["open_grade"] = dict(buttons["alterar_grade"])
    if "alterar_grade" not in buttons and "open_grade" in buttons:
        buttons["alterar_grade"] = dict(buttons["open_grade"])

    grid_raw = data.get("grid")
    grid_data = grid_raw if isinstance(grid_raw, dict) else {}
    grid: dict[str, Any] = {}
    first_quant = normalize_point(grid_data.get("first_quant_cell"))
    if first_quant is not None:
        grid["first_quant_cell"] = [first_quant["x"], first_quant["y"]]
    row_height = grid_data.get("row_height")
    try:
        if row_height is not None and int(row_height) > 0:
            grid["row_height"] = int(row_height)
    except Exception:
        pass

    model_raw = data.get("model")
    model_data = model_raw if isinstance(model_raw, dict) else {}
    strategy = str(model_data.get("strategy") or "index").strip().lower()
    if strategy not in {"index", "hotkey"}:
        strategy = "index"
    try:
        index = int(model_data.get("index", 0) or 0)
    except Exception:
        index = 0
    hotkey = str(model_data.get("hotkey") or "").strip()
    model = {
        "strategy": "hotkey" if hotkey else strategy,
        "index": max(index, 0),
        "hotkey": hotkey,
    }

    erp_size_order = _normalize_string_list(data.get("erp_size_order")) or list(_DEFAULT_ERP_SIZE_ORDER)
    ui_size_order = _normalize_string_list(data.get("ui_size_order")) or list(erp_size_order)
    ui_families = _normalize_ui_families(data.get("ui_families"))
    try:
        ui_family_version = int(data.get("ui_family_version") or 0)
    except Exception:
        ui_family_version = 0

    normalized: dict[str, Any] = {
        "buttons": buttons,
        "grid": grid,
        "model": model,
        "erp_size_order": erp_size_order,
        "ui_size_order": ui_size_order,
        "ui_families": ui_families,
        "ui_family_version": max(ui_family_version, 0),
    }
    return normalized


def has_gradebot_configuration(payload: dict[str, Any] | None) -> bool:
    if not isinstance(payload, dict):
        return False
    buttons = payload.get("buttons")
    grid = payload.get("grid")
    erp_order = payload.get("erp_size_order")
    ui_order = payload.get("ui_size_order")
    ui_families = payload.get("ui_families")
    ui_family_version = payload.get("ui_family_version")
    return bool(buttons) or bool(grid) or bool(erp_order) or bool(ui_order) or bool(ui_families) or bool(ui_family_version)


def merge_gradebot_config(current: dict[str, Any], updates: dict[str, Any]) -> dict[str, Any]:
    current_normalized = normalize_gradebot_config(current)

    buttons = dict(current_normalized.get("buttons") or {})
    for key, value in (updates.get("buttons") or {}).items():
        point = normalize_point(value)
        if point is not None:
            buttons[str(key).strip()] = point

    grid = dict(current_normalized.get("grid") or {})
    first_quant = normalize_point(updates.get("first_quant_cell"))
    second_quant = normalize_point(updates.get("second_quant_cell"))
    if first_quant is not None:
        grid["first_quant_cell"] = [first_quant["x"], first_quant["y"]]
    if updates.get("row_height") is not None:
        try:
            row_height = int(updates["row_height"])
            if row_height > 0:
                grid["row_height"] = row_height
        except Exception:
            pass
    elif first_quant is not None and second_quant is not None:
        grid["row_height"] = max(1, int(second_quant["y"]) - int(first_quant["y"]))

    model = dict(current_normalized.get("model") or {"strategy": "index", "index": 0, "hotkey": ""})
    if updates.get("model_index") is not None:
        try:
            model["index"] = max(int(updates["model_index"]), 0)
            model["strategy"] = "index"
        except Exception:
            pass
    if updates.get("model_hotkey") is not None:
        hotkey = str(updates["model_hotkey"]).strip()
        model["hotkey"] = hotkey
        model["strategy"] = "hotkey" if hotkey else "index"

    erp_size_order = current_normalized.get("erp_size_order") or list(_DEFAULT_ERP_SIZE_ORDER)
    if isinstance(updates.get("erp_size_order"), list):
        erp_size_order = _normalize_string_list(updates.get("erp_size_order")) or list(_DEFAULT_ERP_SIZE_ORDER)

    ui_size_order = current_normalized.get("ui_size_order") or list(erp_size_order)
    if isinstance(updates.get("ui_size_order"), list):
        ui_size_order = _normalize_string_list(updates.get("ui_size_order")) or list(erp_size_order)
    ui_families = current_normalized.get("ui_families") or []
    if isinstance(updates.get("ui_families"), list):
        ui_families = _normalize_ui_families(updates.get("ui_families"))
    try:
        ui_family_version = int(updates.get("ui_family_version") or current_normalized.get("ui_family_version") or 0)
    except Exception:
        ui_family_version = 0

    return normalize_gradebot_config(
        {
            "buttons": buttons,
            "grid": grid,
            "model": model,
            "erp_size_order": erp_size_order,
            "ui_size_order": ui_size_order,
            "ui_families": ui_families,
            "ui_family_version": ui_family_version,
        }
    )
