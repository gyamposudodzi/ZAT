from __future__ import annotations


class ApiError(Exception):
    def __init__(self, status_code: int, message: str, *, details: dict | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.message = message
        self.details = details or {}


class ValidationError(ApiError):
    def __init__(self, message: str, *, details: dict | None = None) -> None:
        super().__init__(400, message, details=details)


class UnauthorizedError(ApiError):
    def __init__(self, message: str = "Authentication is required.") -> None:
        super().__init__(401, message)


class ForbiddenError(ApiError):
    def __init__(self, message: str = "You do not have permission to perform this action.") -> None:
        super().__init__(403, message)


class NotFoundError(ApiError):
    def __init__(self, message: str = "Resource not found.") -> None:
        super().__init__(404, message)
