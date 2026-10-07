from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class RegisterRequest:
    email: str
    password: str
    full_name: str


@dataclass
class LoginRequest:
    email: str
    password: str


@dataclass
class AuthToken:
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 3600
    refresh_token: str | None = None
