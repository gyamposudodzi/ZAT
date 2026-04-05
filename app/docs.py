from __future__ import annotations


def build_openapi_spec() -> dict:
    return {
        "openapi": "3.0.3",
        "info": {
            "title": "Finance Data Processing and Access Control Backend",
            "version": "1.1.0",
            "description": "Assessment backend with role-based access control, finance record management, and dashboard analytics.",
        },
        "servers": [{"url": "http://127.0.0.1:8000"}],
        "components": {
            "securitySchemes": {
                "bearerAuth": {
                    "type": "http",
                    "scheme": "bearer",
                    "bearerFormat": "API Token",
                }
            }
        },
        "security": [{"bearerAuth": []}],
        "paths": {
            "/health": {"get": {"summary": "Health check", "security": []}},
            "/users": {
                "get": {"summary": "List users", "tags": ["Users"]},
                "post": {"summary": "Create user", "tags": ["Users"]},
            },
            "/users/{id}": {
                "get": {"summary": "Get user detail", "tags": ["Users"]},
                "patch": {"summary": "Update user", "tags": ["Users"]},
            },
            "/records": {
                "get": {"summary": "List records", "tags": ["Records"]},
                "post": {"summary": "Create record", "tags": ["Records"]},
            },
            "/records/{id}": {
                "get": {"summary": "Get record detail", "tags": ["Records"]},
                "patch": {"summary": "Update record", "tags": ["Records"]},
                "delete": {"summary": "Soft delete record", "tags": ["Records"]},
            },
            "/dashboard/summary": {"get": {"summary": "Get dashboard summary", "tags": ["Dashboard"]}},
            "/openapi.json": {"get": {"summary": "OpenAPI document", "security": []}},
        },
    }
