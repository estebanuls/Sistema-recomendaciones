"""Password hashing and token helpers."""

from __future__ import annotations

import base64
import bcrypt
import hashlib
import hmac
import json
import secrets
import time


PBKDF2_ITERATIONS = 240_000
BCRYPT_ROUNDS = 12


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _b64decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def _hash_password_legacy(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        PBKDF2_ITERATIONS,
    )
    return f"{salt}${_b64encode(digest)}"


def hash_password(password: str, rounds: int = BCRYPT_ROUNDS) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=rounds)).decode("utf-8")


def needs_password_rehash(stored_hash: str) -> bool:
    return not stored_hash.startswith("$2")


def verify_password(password: str, stored_hash: str) -> bool:
    if stored_hash.startswith("$2"):
        try:
            return bcrypt.checkpw(password.encode("utf-8"), stored_hash.encode("utf-8"))
        except ValueError:
            return False
    try:
        salt, current_hash = stored_hash.split("$", maxsplit=1)
    except ValueError:
        return False
    candidate = _hash_password_legacy(password, salt=salt).split("$", maxsplit=1)[1]
    return hmac.compare_digest(candidate, current_hash)


def create_access_token(subject: int, secret_key: str, ttl_minutes: int) -> str:
    payload = {
        "sub": subject,
        "exp": int(time.time()) + ttl_minutes * 60,
    }
    payload_bytes = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    payload_token = _b64encode(payload_bytes)
    signature = hmac.new(
        secret_key.encode("utf-8"),
        payload_token.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    return f"{payload_token}.{_b64encode(signature)}"


def decode_access_token(token: str, secret_key: str) -> dict[str, int]:
    try:
        payload_token, signature_token = token.split(".", maxsplit=1)
    except ValueError as exc:
        raise ValueError("Token invalido.") from exc

    expected_signature = hmac.new(
        secret_key.encode("utf-8"),
        payload_token.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    if not hmac.compare_digest(_b64encode(expected_signature), signature_token):
        raise ValueError("Firma de token invalida.")

    payload = json.loads(_b64decode(payload_token).decode("utf-8"))
    if int(payload["exp"]) < int(time.time()):
        raise ValueError("Token expirado.")
    return payload


def extract_bearer_token(header_value: str | None) -> str | None:
    if not header_value:
        return None
    prefix = "bearer "
    if header_value.lower().startswith(prefix):
        return header_value[len(prefix):].strip()
    return None
