"""
shared_interfaces.py — Example contract file for Round 1.

Commit this BEFORE starting agents. No agent may modify this file.
All agents import from here to ensure consistent types across modules.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Protocol


# ---------------------------------------------------------------------------
# Domain Models
# ---------------------------------------------------------------------------

@dataclass
class User:
    """Core user model shared across all agents."""
    id: str
    email: str
    name: str
    role: str = "user"
    is_active: bool = True


@dataclass
class AuthToken:
    """JWT token wrapper."""
    access_token: str
    refresh_token: str
    expires_in: int = 3600
    token_type: str = "Bearer"


@dataclass
class APIResponse:
    """Standard API response envelope."""
    success: bool
    data: dict | list | None = None
    error: str | None = None
    error_code: str | None = None


# ---------------------------------------------------------------------------
# Protocols (Interfaces)
# ---------------------------------------------------------------------------

class AuthProvider(Protocol):
    """Interface for authentication providers."""

    def verify_token(self, token: str) -> User | None:
        """Verify a JWT token and return the user, or None if invalid."""
        ...

    def create_token(self, user: User) -> AuthToken:
        """Create a new JWT token pair for a user."""
        ...

    def refresh_token(self, refresh_token: str) -> AuthToken | None:
        """Refresh an expired token. Returns None if refresh token is invalid."""
        ...


class UserRepository(Protocol):
    """Interface for user data access."""

    def get_by_id(self, user_id: str) -> User | None: ...
    def get_by_email(self, email: str) -> User | None: ...
    def create(self, user: User) -> User: ...
    def update(self, user: User) -> User: ...
    def delete(self, user_id: str) -> bool: ...


class NotificationService(Protocol):
    """Interface for sending notifications."""

    def send_email(self, to: str, subject: str, body: str) -> bool: ...
    def send_welcome(self, user: User) -> bool: ...
