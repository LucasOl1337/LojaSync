from __future__ import annotations

import json
import secrets
from pathlib import Path

from app.domain.auth import AuthConfig


class JsonAuthStore:
    def __init__(self, auth_file: Path, session_ttl_minutes: int) -> None:
        self._auth_file = auth_file
        self._session_ttl_minutes = session_ttl_minutes
        self._auth_file.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> AuthConfig:
        payload: dict[str, object] = {}
        if self._auth_file.exists():
            try:
                raw_payload = json.loads(self._auth_file.read_text(encoding="utf-8"))
                if isinstance(raw_payload, dict):
                    payload = raw_payload
            except Exception:
                payload = {}
        config = AuthConfig(
            password_hash=self._normalize_optional_text(payload.get("password_hash")),
            password_salt=self._normalize_optional_text(payload.get("password_salt")),
            secret_key=self._normalize_optional_text(payload.get("secret_key")) or secrets.token_urlsafe(32),
            session_ttl_minutes=self._normalize_positive_int(payload.get("session_ttl_minutes")) or self._session_ttl_minutes,
            password_updated_at=self._normalize_optional_float(payload.get("password_updated_at")),
        )
        self.save(config)
        return config

    def save(self, config: AuthConfig) -> None:
        self._auth_file.write_text(
            json.dumps(
                {
                    "password_hash": config.password_hash,
                    "password_salt": config.password_salt,
                    "secret_key": config.secret_key,
                    "session_ttl_minutes": config.session_ttl_minutes,
                    "password_updated_at": config.password_updated_at,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    @staticmethod
    def _normalize_optional_text(value: object) -> str | None:
        text = str(value).strip() if value is not None else ""
        return text or None

    @staticmethod
    def _normalize_positive_int(value: object) -> int | None:
        try:
            parsed = int(value)
        except Exception:
            return None
        return parsed if parsed > 0 else None

    @staticmethod
    def _normalize_optional_float(value: object) -> float | None:
        try:
            return float(value) if value is not None else None
        except Exception:
            return None
