from __future__ import annotations

from app.errors import ForbiddenError, UnauthorizedError


ROLE_PERMISSIONS = {
    "viewer": {"dashboard:read"},
    "analyst": {"dashboard:read", "records:read"},
    "admin": {"dashboard:read", "records:read", "records:write", "users:manage"},
}


def extract_bearer_token(authorization_header: str | None) -> str:
    if not authorization_header:
        raise UnauthorizedError("Missing Authorization header.")
    parts = authorization_header.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer" or not parts[1].strip():
        raise UnauthorizedError("Authorization header must use Bearer token format.")
    return parts[1].strip()


def ensure_active_user(user: dict | None) -> dict:
    if not user:
        raise UnauthorizedError("Invalid API token.")
    if user["status"] != "active":
        raise ForbiddenError("Inactive users cannot access the API.")
    return user


def require_permission(user: dict, permission: str) -> None:
    allowed_permissions = ROLE_PERMISSIONS.get(user["role"], set())
    if permission not in allowed_permissions:
        raise ForbiddenError()
