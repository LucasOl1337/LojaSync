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

    order_raw = data.get("erp_size_order")
    order_list = order_raw if isinstance(order_raw, list) else []
    erp_size_order = [str(item).strip() for item in order_list if str(item).strip()]

    normalized: dict[str, Any] = {
        "buttons": buttons,
        "grid": grid,
        "model": model,
        "erp_size_order": erp_size_order,
    }
    return normalized


def has_gradebot_configuration(payload: dict[str, Any] | None) -> bool:
    if not isinstance(payload, dict):
        return False
    buttons = payload.get("buttons")
    grid = payload.get("grid")
    order = payload.get("erp_size_order")
    return bool(buttons) or bool(grid) or bool(order)


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

    erp_size_order = current_normalized.get("erp_size_order") or []
    if isinstance(updates.get("erp_size_order"), list):
        erp_size_order = [str(item).strip() for item in updates["erp_size_order"] if str(item).strip()]

    return normalize_gradebot_config(
        {
            "buttons": buttons,
            "grid": grid,
            "model": model,
            "erp_size_order": erp_size_order,
        }
    )
