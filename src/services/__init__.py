"""
Services package for business logic layer.

This package contains service modules that implement core business logic
separate from the API layer, making them easily testable and reusable.

Story 1B Services:
- auth_service: Authentication logic (JWT, password hashing, account lockout)
- user_service: User CRUD operations and role management
"""

# Story 1B: Authentication and User Management Services
from src.services.auth_service import (
    AuthService,
    hash_password,
    verify_password,
    validate_password_strength,
    create_access_token,
    create_refresh_token,
    verify_token,
    revoke_token,
    is_token_revoked,
    authenticate_user,
    handle_failed_login,
    reset_failed_attempts,
)
from src.services.user_service import UserService

__all__ = [
    # AuthService exports
    "AuthService",
    "hash_password",
    "verify_password",
    "validate_password_strength",
    "create_access_token",
    "create_refresh_token",
    "verify_token",
    "revoke_token",
    "is_token_revoked",
    "authenticate_user",
    "handle_failed_login",
    "reset_failed_attempts",
    # UserService exports
    "UserService",
]
