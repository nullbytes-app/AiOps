"""
Tenant Management Helper for Streamlit Admin UI.

This module provides synchronous CRUD operations for tenant management,
including field-level encryption for sensitive data (API keys, webhook secrets).

Key Features:
- Synchronous database operations compatible with Streamlit
- Fernet symmetric encryption for sensitive fields
- Form validation (required fields, URL format, duplicate check)
- Soft delete support with is_active flag
- Google-style docstrings with type hints

Security:
- Encryption key stored in environment variable or Streamlit secrets
- Sensitive fields masked in display (show only last 4 characters)
- No plaintext credentials logged or displayed
"""

import os
import re
import secrets
from typing import Optional

import streamlit as st
from cryptography.fernet import Fernet
from loguru import logger
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from admin.utils.db_helper import get_db_session
from database.models import TenantConfig


# ============================================================================
# Encryption Functions
# ============================================================================


def get_fernet_cipher() -> Fernet:
    """
    Get Fernet cipher instance using encryption key from secrets.

    The encryption key is loaded from environment variable or Streamlit secrets.
    Key must be 32 URL-safe base64-encoded bytes generated with Fernet.generate_key().

    Returns:
        Fernet: Cipher instance for encryption/decryption operations

    Raises:
        ValueError: If encryption key is not set or invalid format

    Environment Variables:
        TENANT_ENCRYPTION_KEY: 32-byte URL-safe base64-encoded encryption key

    Example:
        >>> cipher = get_fernet_cipher()
        >>> encrypted = cipher.encrypt(b"secret_value")
    """
    # Try Streamlit secrets first, then fall back to environment variable
    key = None
    if hasattr(st, "secrets") and "TENANT_ENCRYPTION_KEY" in st.secrets:
        key = st.secrets["TENANT_ENCRYPTION_KEY"]
    else:
        key = os.getenv("TENANT_ENCRYPTION_KEY")

    if not key:
        raise ValueError(
            "TENANT_ENCRYPTION_KEY not found in environment or Streamlit secrets. "
            "Generate with: from cryptography.fernet import Fernet; Fernet.generate_key()"
        )

    # Ensure key is bytes
    if isinstance(key, str):
        key = key.encode()

    return Fernet(key)


def encrypt_field(plaintext: str) -> str:
    """
    Encrypt sensitive field value using Fernet symmetric encryption.

    Args:
        plaintext: The plaintext value to encrypt (e.g., API key, webhook secret)

    Returns:
        str: Base64-encoded ciphertext

    Raises:
        ValueError: If encryption key is unavailable

    Example:
        >>> encrypted_key = encrypt_field("my_api_key_12345")
        >>> print(encrypted_key)
        'gAAAAABf...'  # Base64-encoded ciphertext
    """
    cipher = get_fernet_cipher()
    ciphertext = cipher.encrypt(plaintext.encode())
    return ciphertext.decode()


def decrypt_field(ciphertext: str) -> str:
    """
    Decrypt sensitive field value using Fernet symmetric encryption.

    Args:
        ciphertext: The base64-encoded ciphertext to decrypt

    Returns:
        str: Decrypted plaintext value

    Raises:
        ValueError: If encryption key is unavailable
        cryptography.fernet.InvalidToken: If ciphertext is corrupted or key is wrong

    Example:
        >>> plaintext = decrypt_field("gAAAAABf...")
        >>> print(plaintext)
        'my_api_key_12345'
    """
    cipher = get_fernet_cipher()
    plaintext = cipher.decrypt(ciphertext.encode())
    return plaintext.decode()


def mask_sensitive_field(value: str, visible_chars: int = 4) -> str:
    """
    Mask sensitive value showing only last N characters.

    Used for displaying encrypted fields in UI without exposing full value.
    If value is shorter than visible_chars, fully masks it.

    Args:
        value: The value to mask (usually decrypted sensitive field)
        visible_chars: Number of trailing characters to show (default: 4)

    Returns:
        str: Masked value with format "****xyz123" (last 4 chars visible)

    Example:
        >>> mask_sensitive_field("my_api_key_12345", 4)
        '*************2345'
        >>> mask_sensitive_field("abc", 4)
        '***'
    """
    if len(value) <= visible_chars:
        return "*" * len(value)
    return "*" * (len(value) - visible_chars) + value[-visible_chars:]


# ============================================================================
# Validation Functions
# ============================================================================


def validate_tenant_form(
    form_data: dict, skip_duplicate_check: bool = False
) -> tuple[bool, list[str]]:
    """
    Validate tenant form data before database operation.

    Performs validation checks:
    - Required fields present (name, tenant_id, servicedesk_url, api_key)
    - URL format (starts with http/https)
    - tenant_id alphanumeric + hyphens only
    - Duplicate tenant_id check (unless skip_duplicate_check=True)

    Args:
        form_data: Dictionary with form fields (name, tenant_id, servicedesk_url, api_key, etc.)
        skip_duplicate_check: If True, skip duplicate tenant_id check (for edit operations)

    Returns:
        tuple[bool, list[str]]: (is_valid, error_messages)
            is_valid: True if all validations pass, False otherwise
            error_messages: List of validation error strings (empty if valid)

    Example:
        >>> is_valid, errors = validate_tenant_form({"name": "Acme Corp", ...})
        >>> if not is_valid:
        ...     for error in errors:
        ...         st.error(error)
    """
    errors = []

    # Required fields check
    required_fields = ["name", "tenant_id", "servicedesk_url", "api_key"]
    for field in required_fields:
        if not form_data.get(field):
            errors.append(f"❌ {field.replace('_', ' ').title()} is required")

    # URL format validation
    servicedesk_url = form_data.get("servicedesk_url", "")
    if servicedesk_url and not re.match(r"^https?://", servicedesk_url):
        errors.append("❌ ServiceDesk URL must start with http:// or https://")

    # tenant_id format validation (alphanumeric + hyphens only)
    tenant_id = form_data.get("tenant_id", "")
    if tenant_id and not re.match(r"^[a-zA-Z0-9-]+$", tenant_id):
        errors.append("❌ Tenant ID can only contain letters, numbers, and hyphens")

    # Duplicate tenant_id check (unless editing existing tenant)
    if not skip_duplicate_check and tenant_id:
        try:
            with get_db_session() as session:
                existing = (
                    session.query(TenantConfig)
                    .filter(TenantConfig.tenant_id == tenant_id)
                    .first()
                )
                if existing:
                    errors.append(f"❌ Tenant ID '{tenant_id}' already exists")
        except Exception as e:
            logger.error(f"Duplicate check failed: {e}")
            errors.append("❌ Database error during duplicate check")

    return (len(errors) == 0, errors)


# ============================================================================
# CRUD Functions
# ============================================================================


def generate_tenant_id_slug(name: str) -> str:
    """
    Generate a URL-safe slug from tenant name for use as tenant_id.

    Converts name to lowercase, replaces spaces and special chars with hyphens,
    removes consecutive hyphens, and strips leading/trailing hyphens.

    Args:
        name: Human-readable tenant name

    Returns:
        str: URL-safe slug (lowercase alphanumeric + hyphens)

    Example:
        >>> generate_tenant_id_slug("Acme Corporation")
        'acme-corporation'
        >>> generate_tenant_id_slug("Tech Solutions, Inc.")
        'tech-solutions-inc'
    """
    # Convert to lowercase
    slug = name.lower()
    # Replace spaces and special characters with hyphens
    slug = re.sub(r"[^\w\s-]", "", slug)  # Remove special chars except spaces and hyphens
    slug = re.sub(r"[\s_]+", "-", slug)  # Replace spaces/underscores with hyphens
    slug = re.sub(r"-+", "-", slug)  # Remove consecutive hyphens
    slug = slug.strip("-")  # Remove leading/trailing hyphens
    return slug


def create_tenant(tenant_data: dict) -> Optional[TenantConfig]:
    """
    Create new tenant configuration with encrypted credentials.

    Args:
        tenant_data: Dictionary with tenant fields:
            - name (str): Human-readable tenant name
            - tenant_id (str, optional): Unique tenant identifier (auto-generated from name if not provided)
            - tool_type (str): Plugin type (servicedesk_plus, jira, zendesk, etc.) - Story 7.8
            - servicedesk_url (str): ServiceDesk Plus instance URL
            - api_key (str): ServiceDesk API key (will be encrypted)
            - webhook_secret (str, optional): Webhook secret (will be encrypted, auto-generated if not provided)
            - enhancement_preferences (dict, optional): Feature toggles (defaults to {})
            - rate_limits (dict, optional): Rate limit config (defaults to standard limits)

    Returns:
        TenantConfig: Created tenant object, or None if creation fails

    Raises:
        IntegrityError: If tenant_id already exists (duplicate key)
        Exception: For other database errors

    Example:
        >>> tenant = create_tenant({
        ...     "name": "Acme Corp",
        ...     "tenant_id": "acme-corp",
        ...     "tool_type": "servicedesk_plus",
        ...     "servicedesk_url": "https://acme.servicedesk.com",
        ...     "api_key": "key_12345",
        ...     "webhook_secret": "secret_xyz",
        ...     "enhancement_preferences": {"ticket_history": True}
        ... })
        >>> print(tenant.tenant_id)
        'acme-corp'
    """
    try:
        from admin.utils.operations_audit import log_operation

        # Generate tenant_id slug if not provided
        if not tenant_data.get("tenant_id"):
            tenant_data["tenant_id"] = generate_tenant_id_slug(tenant_data["name"])

        # Auto-generate webhook secret if not provided
        if not tenant_data.get("webhook_secret"):
            tenant_data["webhook_secret"] = secrets.token_urlsafe(32)

        # Encrypt sensitive fields
        api_key_encrypted = encrypt_field(tenant_data["api_key"])
        webhook_secret_encrypted = encrypt_field(tenant_data["webhook_secret"])

        # Create tenant object
        tenant = TenantConfig(
            tenant_id=tenant_data["tenant_id"],
            name=tenant_data["name"],
            tool_type=tenant_data.get("tool_type", "servicedesk_plus"),  # Story 7.8: Plugin assignment
            servicedesk_url=tenant_data["servicedesk_url"],
            servicedesk_api_key_encrypted=api_key_encrypted,
            webhook_signing_secret_encrypted=webhook_secret_encrypted,
            enhancement_preferences=tenant_data.get("enhancement_preferences", {}),
            rate_limits=tenant_data.get(
                "rate_limits",
                {"webhooks": {"ticket_created": 100, "ticket_resolved": 100}},
            ),
            is_active=True,
        )

        # Insert into database
        with get_db_session() as session:
            session.add(tenant)
            session.flush()  # Get generated UUID
            session.refresh(tenant)

        # AC#8: Log tenant creation with plugin assignment to audit log
        log_operation(
            user="admin",  # TODO: Get from Streamlit session when auth is implemented
            operation="tenant_plugin_assignment",
            details={
                "tenant_id": tenant_data["tenant_id"],
                "tenant_name": tenant_data["name"],
                "plugin_id": tenant_data.get("tool_type", "servicedesk_plus"),
                "action": "create",
            },
            status="success",
        )

        logger.info(f"Created tenant: {tenant.tenant_id} with plugin: {tenant.tool_type}")
        return tenant

    except IntegrityError as e:
        logger.error(f"Tenant creation failed (duplicate tenant_id): {e}")
        
        # AC#8: Log failure to audit log
        try:
            from admin.utils.operations_audit import log_operation
            log_operation(
                user="admin",
                operation="tenant_plugin_assignment",
                details={
                    "tenant_id": tenant_data.get("tenant_id"),
                    "error": "duplicate_tenant_id",
                },
                status="failure",
            )
        except:
            pass  # Don't block exception if logging fails
        
        raise
    except Exception as e:
        logger.error(f"Tenant creation failed: {e}")
        
        # AC#8: Log failure to audit log
        try:
            from admin.utils.operations_audit import log_operation
            log_operation(
                user="admin",
                operation="tenant_plugin_assignment",
                details={
                    "tenant_id": tenant_data.get("tenant_id"),
                    "error": str(e),
                },
                status="failure",
            )
        except:
            pass  # Don't block exception if logging fails
        
        return None


def get_all_tenants(include_inactive: bool = False) -> list[TenantConfig]:
    """
    Retrieve all tenant configurations from database.

    Args:
        include_inactive: If True, include soft-deleted tenants (is_active=False)
                         If False (default), return only active tenants

    Returns:
        list[TenantConfig]: List of tenant objects (empty list if none found)

    Example:
        >>> active_tenants = get_all_tenants()
        >>> print(f"Found {len(active_tenants)} active tenants")
        >>> all_tenants = get_all_tenants(include_inactive=True)
        >>> print(f"Found {len(all_tenants)} total tenants (including inactive)")
    """
    try:
        with get_db_session() as session:
            query = session.query(TenantConfig)

            # Filter by is_active unless include_inactive is True
            if not include_inactive:
                query = query.filter(TenantConfig.is_active == True)

            tenants = query.order_by(TenantConfig.created_at.desc()).all()
            return tenants

    except Exception as e:
        logger.error(f"Failed to retrieve tenants: {e}")
        return []


def get_tenant_by_id(tenant_id: str) -> Optional[TenantConfig]:
    """
    Retrieve single tenant by tenant_id.

    Args:
        tenant_id: Unique tenant identifier

    Returns:
        TenantConfig: Tenant object if found, None otherwise

    Example:
        >>> tenant = get_tenant_by_id("acme-corp")
        >>> if tenant:
        ...     print(f"Found tenant: {tenant.name}")
        ... else:
        ...     print("Tenant not found")
    """
    try:
        with get_db_session() as session:
            tenant = (
                session.query(TenantConfig)
                .filter(TenantConfig.tenant_id == tenant_id)
                .first()
            )
            return tenant

    except Exception as e:
        logger.error(f"Failed to retrieve tenant {tenant_id}: {e}")
        return None


def update_tenant(tenant_id: str, updates: dict) -> bool:
    """
    Update existing tenant configuration with partial updates.

    Only provided fields are updated (partial update support).
    Sensitive fields (api_key, webhook_secret) are re-encrypted if updated.

    Args:
        tenant_id: Unique tenant identifier
        updates: Dictionary with fields to update (only provided fields are updated):
            - name (str, optional): New tenant name
            - tool_type (str, optional): New plugin type (Story 7.8)
            - servicedesk_url (str, optional): New ServiceDesk URL
            - api_key (str, optional): New API key (will be encrypted)
            - webhook_secret (str, optional): New webhook secret (will be encrypted)
            - enhancement_preferences (dict, optional): Updated preferences
            - rate_limits (dict, optional): Updated rate limits

    Returns:
        bool: True if update succeeded, False otherwise

    Raises:
        Exception: For database errors

    Example:
        >>> success = update_tenant("acme-corp", {
        ...     "name": "Acme Corporation",
        ...     "tool_type": "jira",
        ...     "api_key": "new_key_67890"
        ... })
        >>> if success:
        ...     print("Tenant updated successfully")
    """
    try:
        from admin.utils.operations_audit import log_operation

        with get_db_session() as session:
            tenant = (
                session.query(TenantConfig)
                .filter(TenantConfig.tenant_id == tenant_id)
                .first()
            )

            if not tenant:
                logger.error(f"Tenant {tenant_id} not found for update")
                return False

            # Track plugin reassignment for audit logging
            old_plugin = tenant.tool_type
            plugin_changed = False

            # Update fields (only if provided in updates dict)
            if "name" in updates:
                tenant.name = updates["name"]
            if "tool_type" in updates:
                tenant.tool_type = updates["tool_type"]
                plugin_changed = old_plugin != updates["tool_type"]
            if "servicedesk_url" in updates:
                tenant.servicedesk_url = updates["servicedesk_url"]
            if "api_key" in updates:
                tenant.servicedesk_api_key_encrypted = encrypt_field(updates["api_key"])
            if "webhook_secret" in updates:
                tenant.webhook_signing_secret_encrypted = encrypt_field(
                    updates["webhook_secret"]
                )
            if "enhancement_preferences" in updates:
                tenant.enhancement_preferences = updates["enhancement_preferences"]
            if "rate_limits" in updates:
                tenant.rate_limits = updates["rate_limits"]

            # Update timestamp
            tenant.updated_at = func.now()

            session.flush()

        # AC#8: Log plugin reassignment to audit log if plugin changed
        if plugin_changed:
            log_operation(
                user="admin",  # TODO: Get from Streamlit session when auth is implemented
                operation="tenant_plugin_assignment",
                details={
                    "tenant_id": tenant_id,
                    "old_plugin": old_plugin,
                    "new_plugin": updates["tool_type"],
                    "action": "reassign",
                },
                status="success",
            )

        logger.info(f"Updated tenant: {tenant_id}")
        return True

    except Exception as e:
        logger.error(f"Failed to update tenant {tenant_id}: {e}")
        
        # AC#8: Log failure to audit log
        try:
            from admin.utils.operations_audit import log_operation
            log_operation(
                user="admin",
                operation="tenant_plugin_assignment",
                details={
                    "tenant_id": tenant_id,
                    "error": str(e),
                    "action": "update",
                },
                status="failure",
            )
        except:
            pass  # Don't block exception if logging fails
        
        return False


def soft_delete_tenant(tenant_id: str) -> bool:
    """
    Soft delete tenant by marking is_active = False.

    Tenant record remains in database for audit trail, but is hidden from
    default queries and considered inactive.

    Args:
        tenant_id: Unique tenant identifier

    Returns:
        bool: True if deletion succeeded, False otherwise

    Example:
        >>> success = soft_delete_tenant("acme-corp")
        >>> if success:
        ...     print("Tenant marked as inactive")
    """
    try:
        with get_db_session() as session:
            tenant = (
                session.query(TenantConfig)
                .filter(TenantConfig.tenant_id == tenant_id)
                .first()
            )

            if not tenant:
                logger.error(f"Tenant {tenant_id} not found for deletion")
                return False

            # Mark as inactive (soft delete)
            tenant.is_active = False
            tenant.updated_at = func.now()

            session.flush()

        logger.info(f"Soft deleted tenant: {tenant_id}")
        return True

    except Exception as e:
        logger.error(f"Failed to soft delete tenant {tenant_id}: {e}")
        return False
