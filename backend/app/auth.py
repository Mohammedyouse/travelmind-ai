from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
import time
import uuid
from typing import Any

from .db import create_user, get_user_by_email, get_user_by_id


def _secret() -> str:
    secret = os.getenv("JWT_SECRET_KEY")
    environment = os.getenv("APP_ENV", "development").lower()
    if environment in {"production", "prod"} and (not secret or len(secret) < 32):
        raise RuntimeError("JWT_SECRET_KEY must contain at least 32 characters in production")
    return secret or "travelmind-dev-secret"


def hash_password(password: str) -> str:
    salt = os.urandom(16).hex()
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 200_000)
    return f"pbkdf2_sha256${salt}${digest.hex()}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        algorithm, salt, digest_hex = password_hash.split("$", 2)
    except ValueError:
        return False
    if algorithm != "pbkdf2_sha256":
        return False
    candidate = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 200_000)
    return hmac.compare_digest(candidate.hex(), digest_hex)


def register_user(email: str, password: str, full_name: str, role: str = "traveler") -> dict[str, Any]:
    if not all(isinstance(value, str) for value in (email, password, full_name)):
        raise ValueError("email, password, and full_name must be strings")
    email = email.strip().lower()
    full_name = full_name.strip()
    if not email or not password or not full_name:
        raise ValueError("email, password, and full_name are required")
    if len(password) < 8:
        raise ValueError("password must contain at least 8 characters")
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
        raise ValueError("email address is invalid")
    if role not in {"traveler", "admin"}:
        raise ValueError("role is invalid")
    if get_user_by_email(email) is not None:
        raise ValueError("user already exists")
    user = create_user(email.strip().lower(), hash_password(password), full_name.strip(), role)
    if user is None:
        raise ValueError("unable to create user")
    return {
        "id": user["id"],
        "email": user["email"],
        "full_name": user["full_name"],
        "role": user["role"],
        "password_hash": user["password_hash"],
        "created_at": user["created_at"],
    }


def authenticate_user(email: str, password: str) -> dict[str, Any]:
    if not isinstance(email, str) or not isinstance(password, str):
        raise ValueError("invalid credentials")
    user = get_user_by_email(email.strip().lower())
    if user is None:
        raise ValueError("invalid credentials")
    if not verify_password(password, user["password_hash"]):
        raise ValueError("invalid credentials")
    return {
        "id": user["id"],
        "email": user["email"],
        "full_name": user["full_name"],
        "role": user["role"],
    }


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(value: str) -> bytes:
    padded = value + "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(padded.encode("ascii"))


def issue_token(user: dict[str, Any]) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    now = int(time.time())
    payload = {
        "sub": user["id"],
        "email": user["email"],
        "role": user.get("role", "traveler"),
        "iat": now,
        "exp": now + 3600,
    }
    header_segment = _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_segment = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{header_segment}.{payload_segment}".encode("utf-8")
    signature = hmac.new(_secret().encode("utf-8"), signing_input, hashlib.sha256).digest()
    return f"{header_segment}.{payload_segment}.{_b64url_encode(signature)}"


def verify_token(token: str) -> dict[str, Any]:
    try:
        header_segment, payload_segment, signature_segment = token.split(".")
    except ValueError as exc:
        raise ValueError("invalid token") from exc
    try:
        header = json.loads(_b64url_decode(header_segment).decode("utf-8"))
    except (ValueError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ValueError("invalid token header") from exc
    if header.get("alg") != "HS256" or header.get("typ") != "JWT":
        raise ValueError("unsupported token header")
    signing_input = f"{header_segment}.{payload_segment}".encode("utf-8")
    expected = _b64url_encode(hmac.new(_secret().encode("utf-8"), signing_input, hashlib.sha256).digest())
    if not hmac.compare_digest(signature_segment, expected):
        raise ValueError("token signature mismatch")
    payload = json.loads(_b64url_decode(payload_segment).decode("utf-8"))
    if not isinstance(payload.get("exp"), int) or payload["exp"] <= int(time.time()):
        raise ValueError("token expired")
    user = get_user_by_id(payload.get("sub", ""))
    if user is None:
        raise ValueError("user not found")
    return {"sub": user["id"], "email": user["email"], "role": user["role"], "full_name": user["full_name"]}


def require_roles(*roles: str):
    def decorator(func):
        def wrapper(*args, **kwargs):
            token = kwargs.get("token")
            if token is None:
                raise PermissionError("missing token")
            payload = verify_token(token)
            if payload.get("role") not in roles:
                raise PermissionError("insufficient role")
            return func(*args, **kwargs)
        return wrapper
    return decorator
