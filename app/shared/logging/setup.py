from __future__ import annotations

import json
import logging
from typing import Any


_RESERVED_LOG_RECORD_FIELDS = set(logging.makeLogRecord({}).__dict__) | {"asctime", "message"}


def configure_logging(level: int = logging.INFO) -> None:
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def log_event(logger: logging.Logger, level: int, event: str, summary: str, **fields: Any) -> None:
    extra = _safe_extra_fields({"event": event, **fields})
    payload = json.dumps(extra, ensure_ascii=False, sort_keys=True, default=str)
    logger.log(level, "%s %s", summary, payload, extra=extra)


def _safe_extra_fields(fields: dict[str, Any]) -> dict[str, Any]:
    safe: dict[str, Any] = {}
    for key, value in fields.items():
        field_name = str(key).strip() or "field"
        if field_name in _RESERVED_LOG_RECORD_FIELDS:
            field_name = f"log_{field_name}"
        safe[field_name] = value
    return safe
