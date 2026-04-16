from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AuthConfig:
    password_hash: str | None
    password_salt: str | None
    secret_key: str
    session_ttl_minutes: int
    password_updated_at: float | None = None

    @property
    def password_configured(self) -> bool:
        return bool(self.password_hash and self.password_salt)


@dataclass(frozen=True)
class SessionIdentity:
    username: str
    expires_at: int
