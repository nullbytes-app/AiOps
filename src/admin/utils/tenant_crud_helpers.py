"""
Tenant CRUD Operations Helper.

Provides synchronous CRUD operations for tenant management compatible with Streamlit.
Integrates with encryption, validation, and audit logging functions.

Key Features:
- Create, read, update, delete tenant configurations
- Slug generation for tenant IDs
- Soft delete support with is_active flag
- Audit logging integration
"""

import re
import secrets
from typing import Optional

from loguru import logger
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from admin.utils.db_helper import get_db_session
from database.models import TenantConfig
from admin.utils.tenant_encryption_helpers import encrypt_field


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
    slug = name.lower()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    slug = slug.strip("-")
    return slug


def create_tenant(tenant_data: dict) -> Optional[TenantConfig]:
    """
    Create new tenant configuration with encrypted credentials.

    Args:
        tenant_data: Dictionary with tenant fields:
            - name (str): Human-readable tenant name
            - tenant_id (str, optional): Unique identifier (auto-generated if not provided)
            - tool_type (str): Plugin type (servicedesk_plus, jira, zendesk, etc.)
            - servicedesk_url (str): ServiceDesk Plus instance URL
            - api_key (str): ServiceDesk API key (will be encrypted)
            - webhook_secret (str, optional): Webhook secret (auto-generated if not provided)
            - enhancement_preferences (dict, optional): Feature toggles (defaults to {})
            - rate_limits (dict, optional): Rate limit config (defaults to standard limits)

    Returns:
        TenantConfig: Created tenant object, or None if creation fails

    Raises:
        IntegrityError: If tenant_id already exists (duplicate key)
        Exception: For other database errors
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
            tool_type=tenant_data.get("tool_type", "servicedesk_plus"),
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
            session.flush()
            session.refresh(tenant)

        # Log tenant creation with plugin assignment to audit log
        log_operation(
            user="admin",
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
            pass
        raise
    except Exception as e:
        logger.error(f"Tenant creation failed: {e}")
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
            pass
        return None


def get_all_tenants(include_inactive: bool = False) -> list:
    """
    Retrieve all tenant configurations from database.

    Args:
        include_inactive: If True, include soft-deleted tenants (is_active=False)
                         If False (default), return only active tenants

    Returns:
        list[TenantConfig]: List of tenant objects (empty list if none found)
    """
    try:
        with get_db_session() as session:
            query = session.query(TenantConfig)
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
        updates: Dictionary with fields to update:
            - name, tool_type, servicedesk_url, api_key, webhook_secret
            - enhancement_preferences, rate_limits

    Returns:
        bool: True if update succeeded, False otherwise
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

            old_plugin = tenant.tool_type
            plugin_changed = False

            # Update fields (only if provided)
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

            tenant.updated_at = func.now()
            session.flush()

        # Log plugin reassignment if plugin changed
        if plugin_changed:
            log_operation(
                user="admin",
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
            pass
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

            tenant.is_active = False
            tenant.updated_at = func.now()
            session.flush()

        logger.info(f"Soft deleted tenant: {tenant_id}")
        return True

    except Exception as e:
        logger.error(f"Failed to soft delete tenant {tenant_id}: {e}")
        return False
