"""
Tenant Form Validation Helpers.

This module provides validation functions for tenant configuration forms:
- Required field checks
- URL format validation
- Tenant ID format validation
- Duplicate detection
"""

import re
from typing import Tuple

from loguru import logger

from admin.utils.db_helper import get_db_session
from database.models import TenantConfig


def validate_tenant_form(
    form_data: dict, skip_duplicate_check: bool = False
) -> Tuple[bool, list]:
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
        Tuple[bool, list]: (is_valid, error_messages)
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
