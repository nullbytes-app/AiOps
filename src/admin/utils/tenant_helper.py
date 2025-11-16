"""
Tenant Management Helper - Re-exports from focused modules.

This module re-exports functions from specialized tenant helper modules
for backward compatibility while maintaining the modularization strategy.

Focused modules:
- tenant_encryption_helpers: Fernet encryption, field masking
- tenant_validation_helpers: Form validation
- tenant_crud_helpers: Create, read, update, delete operations
"""

# Re-export encryption functions
from admin.utils.tenant_encryption_helpers import (
    decrypt_field,
    encrypt_field,
    get_fernet_cipher,
    mask_sensitive_field,
)

# Re-export validation functions
from admin.utils.tenant_validation_helpers import validate_tenant_form

# Re-export CRUD functions
from admin.utils.tenant_crud_helpers import (
    create_tenant,
    generate_tenant_id_slug,
    get_all_tenants,
    get_tenant_by_id,
    soft_delete_tenant,
    update_tenant,
)

__all__ = [
    # Encryption
    "get_fernet_cipher",
    "encrypt_field",
    "decrypt_field",
    "mask_sensitive_field",
    # Validation
    "validate_tenant_form",
    # CRUD
    "generate_tenant_id_slug",
    "create_tenant",
    "get_all_tenants",
    "get_tenant_by_id",
    "update_tenant",
    "soft_delete_tenant",
]
