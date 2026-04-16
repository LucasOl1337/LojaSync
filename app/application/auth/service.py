from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time

from fastapi import HTTPException, status

from app.domain.auth import AuthConfig, SessionIdentity
from app.infrastructure.persistence.files.auth_store import JsonAuthStore

PBKDF2_ITERATIONS = 310_000
DEFAULT_USERNAME = "admin"


class AuthService:
    def __init__(self, store: JsonAuthStore, password_min_length: int, cookie_name: str) -> None:
        self._store = store
        self._password_min_length = password_min_length
        self._cookie_name = cookie_name

    @property
    def cookie_name(self) -> str:
        return self._cookie_name

    def get_status(self) -> dict[str, object]:
        config = self._store.load()
        return {
            "password_configured": config.password_configured,
            "bootstrap_required": not config.password_configured,
            "session_ttl_minutes": config.session_ttl_minutes,
        }

    def bootstrap_password(self, password: str) -> str:
        config = self._store.load()
        if config.password_configured:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A senha inicial ja foi configurada.")
        self._validate_new_password(password)
        updated = self._build_config_with_password(config, password)
        self._store.save(updated)
        return self.issue_session_token(DEFAULT_USERNAME)

    def authenticate(self, password: str) -> str:
        config = self._store.load()
        if not config.password_configured:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Configure a senha inicial antes de entrar.")
        if not self._password_matches(password, config):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Senha invalida.")
        return self.issue_session_token(DEFAULT_USERNAME)

    def change_password(self, current_password: str, new_password: str) -> None:
        config = self._store.load()
        if not config.password_configured:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Configure a senha inicial antes de trocar a senha.")
        if not self._password_matches(current_password, config):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Senha atual invalida.")
        self._validate_new_password(new_password)
        updated = self._build_config_with_password(config, new_password)
        self._store.save(updated)

    def issue_session_token(self, username: str) -> str:
        config = self._store.load()
        expires_at = int(time.time() + (config.session_ttl_minutes * 60))
        payload = {"sub": username, "exp": expires_at}
        encoded_payload = self._encode_segment(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
        signature = self._sign_segment(encoded_payload, config.secret_key)
        return f"{encoded_payload}.{signature}"

    def validate_session_token(self, token: str | None) -> SessionIdentity | None:
        if not token:
            return None
        config = self._store.load()
        if not config.password_configured:
            return None
        try:
            payload_segment, signature = token.split(".", 1)
        except ValueError:
            return None
        expected_signature = self._sign_segment(payload_segment, config.secret_key)
        if not hmac.compare_digest(signature, expected_signature):
            return None
        try:
            payload = json.loads(self._decode_segment(payload_segment))
        except Exception:
            return None
        expires_at = int(payload.get("exp", 0) or 0)
        username = str(payload.get("sub", "")).strip()
        if not username or expires_at <= int(time.time()):
            return None
        return SessionIdentity(username=username, expires_at=expires_at)

    def require_authenticated_session(self, token: str | None) -> SessionIdentity:
        config = self._store.load()
        if not config.password_configured:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Configure a senha inicial antes de usar o sistema.")
        identity = self.validate_session_token(token)
        if identity is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sessao invalida ou expirada.")
        return identity

    def _build_config_with_password(self, config: AuthConfig, password: str) -> AuthConfig:
        salt = secrets.token_hex(16)
        password_hash = self._hash_password(password, salt)
        return AuthConfig(
            password_hash=password_hash,
            password_salt=salt,
            secret_key=config.secret_key,
            session_ttl_minutes=config.session_ttl_minutes,
            password_updated_at=time.time(),
        )

    def _password_matches(self, password: str, config: AuthConfig) -> bool:
        if not config.password_hash or not config.password_salt:
            return False
        return hmac.compare_digest(self._hash_password(password, config.password_salt), config.password_hash)

    def _validate_new_password(self, password: str) -> None:
        raw_password = str(password or "")
        if len(raw_password) < self._password_min_length:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"A senha precisa ter pelo menos {self._password_min_length} caracteres.",
            )

    @staticmethod
    def _hash_password(password: str, salt: str) -> str:
        derived = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            PBKDF2_ITERATIONS,
        )
        return derived.hex()

    @staticmethod
    def _encode_segment(payload: bytes) -> str:
        return base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")

    @staticmethod
    def _decode_segment(segment: str) -> bytes:
        padding = "=" * (-len(segment) % 4)
        return base64.urlsafe_b64decode(f"{segment}{padding}".encode("ascii"))

    @staticmethod
    def _sign_segment(segment: str, secret_key: str) -> str:
        digest = hmac.new(secret_key.encode("utf-8"), segment.encode("utf-8"), hashlib.sha256).digest()
        return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
