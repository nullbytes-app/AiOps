"""
Unit tests for tenant_helper.py.

Tests CRUD operations, encryption functions, and form validation.
Uses pytest fixtures and mocking for database operations.
"""

import os
from unittest.mock import MagicMock, patch

import pytest
from cryptography.fernet import Fernet
from sqlalchemy.exc import IntegrityError

from admin.utils.tenant_helper import (
    create_tenant,
    decrypt_field,
    encrypt_field,
    generate_tenant_id_slug,
    get_all_tenants,
    get_tenant_by_id,
    mask_sensitive_field,
    soft_delete_tenant,
    update_tenant,
    validate_tenant_form,
)
from database.models import TenantConfig


@pytest.fixture(autouse=True)
def setup_encryption_key(monkeypatch):
    """Set encryption key for all tests."""
    key = Fernet.generate_key().decode()
    monkeypatch.setenv("TENANT_ENCRYPTION_KEY", key)


@pytest.fixture
def mock_session():
    """Mock database session."""
    session = MagicMock()
    session.query.return_value = session
    session.filter.return_value = session
    session.order_by.return_value = session
    return session


# ============================================================================
# Encryption Tests
# ============================================================================


def test_encrypt_decrypt_field():
    """Test encryption and decryption round-trip."""
    plaintext = "my_api_key_12345"
    encrypted = encrypt_field(plaintext)

    # Verify encrypted value is different from plaintext
    assert encrypted != plaintext

    # Verify decryption returns original value
    decrypted = decrypt_field(encrypted)
    assert decrypted == plaintext


def test_encrypt_field_produces_different_ciphertext():
    """Test that encryption produces different ciphertext each time (IV randomization)."""
    plaintext = "my_api_key_12345"
    encrypted1 = encrypt_field(plaintext)
    encrypted2 = encrypt_field(plaintext)

    # Different ciphertexts due to random IV
    assert encrypted1 != encrypted2

    # Both decrypt to same plaintext
    assert decrypt_field(encrypted1) == plaintext
    assert decrypt_field(encrypted2) == plaintext


def test_mask_sensitive_field():
    """Test masking shows only last N characters."""
    # Normal case: show last 4 chars
    value = "my_api_key_12345"
    masked = mask_sensitive_field(value, 4)
    assert masked == "************2345"
    assert len(masked) == len(value)

    # Short value: fully masked
    short_value = "abc"
    masked_short = mask_sensitive_field(short_value, 4)
    assert masked_short == "***"


def test_mask_sensitive_field_edge_cases():
    """Test masking edge cases."""
    # Empty string
    assert mask_sensitive_field("", 4) == ""

    # Exactly 4 chars
    assert mask_sensitive_field("abcd", 4) == "****"

    # Custom visible chars
    assert mask_sensitive_field("password123", 6) == "*****ord123"


# ============================================================================
# Slug Generation Tests
# ============================================================================


def test_generate_tenant_id_slug_basic():
    """Test basic slug generation from tenant name."""
    assert generate_tenant_id_slug("Acme Corporation") == "acme-corporation"
    assert generate_tenant_id_slug("Tech Solutions") == "tech-solutions"


def test_generate_tenant_id_slug_special_chars():
    """Test slug generation removes special characters."""
    assert generate_tenant_id_slug("Tech Solutions, Inc.") == "tech-solutions-inc"
    assert generate_tenant_id_slug("Acme & Sons") == "acme-sons"
    assert generate_tenant_id_slug("O'Reilly Media") == "oreilly-media"


def test_generate_tenant_id_slug_whitespace():
    """Test slug generation handles various whitespace."""
    assert generate_tenant_id_slug("Multiple   Spaces") == "multiple-spaces"
    assert generate_tenant_id_slug("  Leading Trailing  ") == "leading-trailing"


def test_generate_tenant_id_slug_hyphens():
    """Test slug generation handles hyphens correctly."""
    assert generate_tenant_id_slug("Already-Hyphenated") == "already-hyphenated"
    assert generate_tenant_id_slug("Multiple---Hyphens") == "multiple-hyphens"


def test_create_tenant_auto_generates_tenant_id():
    """Test create_tenant generates tenant_id from name if not provided."""
    with patch("admin.utils.tenant_helper.get_db_session") as mock_session:
        mock_db = MagicMock()
        mock_session.return_value.__enter__.return_value = mock_db

        tenant_data = {
            "name": "Acme Corporation",
            # tenant_id not provided - should be auto-generated
            "servicedesk_url": "https://acme.servicedesk.com",
            "api_key": "test_key_123",
        }

        tenant = create_tenant(tenant_data)

        # Verify tenant_id was generated from name
        assert tenant.tenant_id == "acme-corporation"
        assert tenant.name == "Acme Corporation"


# ============================================================================
# Validation Tests
# ============================================================================


@patch("admin.utils.tenant_helper.get_db_session")
def test_validate_tenant_form_success(mock_get_session, mock_session):
    """Test form validation with valid data."""
    mock_get_session.return_value.__enter__.return_value = mock_session
    mock_session.first.return_value = None  # No duplicate

    form_data = {
        "name": "Acme Corp",
        "tenant_id": "acme-corp",
        "servicedesk_url": "https://acme.servicedesk.com",
        "api_key": "key_12345",
    }

    is_valid, errors = validate_tenant_form(form_data)
    assert is_valid is True
    assert errors == []


@patch("admin.utils.tenant_helper.get_db_session")
def test_validate_tenant_form_missing_fields(mock_get_session):
    """Test validation fails for missing required fields."""
    form_data = {
        "name": "Acme Corp",
        # Missing tenant_id, servicedesk_url, api_key
    }

    is_valid, errors = validate_tenant_form(form_data)
    assert is_valid is False
    assert len(errors) == 3  # Three missing fields


@patch("admin.utils.tenant_helper.get_db_session")
def test_validate_tenant_form_invalid_url(mock_get_session):
    """Test validation fails for invalid URL format."""
    form_data = {
        "name": "Acme Corp",
        "tenant_id": "acme-corp",
        "servicedesk_url": "invalid-url",  # Missing http/https
        "api_key": "key_12345",
    }

    is_valid, errors = validate_tenant_form(form_data)
    assert is_valid is False
    assert any("http" in err.lower() for err in errors)


@patch("admin.utils.tenant_helper.get_db_session")
def test_validate_tenant_form_invalid_tenant_id(mock_get_session):
    """Test validation fails for tenant_id with special characters."""
    form_data = {
        "name": "Acme Corp",
        "tenant_id": "acme@corp!",  # Invalid characters
        "servicedesk_url": "https://acme.servicedesk.com",
        "api_key": "key_12345",
    }

    is_valid, errors = validate_tenant_form(form_data)
    assert is_valid is False
    assert any("alphanumeric" in err.lower() or "hyphens" in err.lower() for err in errors)


@patch("admin.utils.tenant_helper.get_db_session")
def test_validate_tenant_form_duplicate_tenant_id(mock_get_session, mock_session):
    """Test validation fails for duplicate tenant_id."""
    mock_get_session.return_value.__enter__.return_value = mock_session

    # Mock existing tenant with same ID
    existing_tenant = MagicMock()
    mock_session.first.return_value = existing_tenant

    form_data = {
        "name": "Acme Corp",
        "tenant_id": "acme-corp",
        "servicedesk_url": "https://acme.servicedesk.com",
        "api_key": "key_12345",
    }

    is_valid, errors = validate_tenant_form(form_data)
    assert is_valid is False
    assert any("already exists" in err.lower() for err in errors)


@patch("admin.utils.tenant_helper.get_db_session")
def test_validate_tenant_form_skip_duplicate_check(mock_get_session):
    """Test skip_duplicate_check parameter for edit operations."""
    form_data = {
        "name": "Acme Corp",
        "tenant_id": "acme-corp",
        "servicedesk_url": "https://acme.servicedesk.com",
        "api_key": "key_12345",
    }

    # Should not query database when skip_duplicate_check=True
    is_valid, errors = validate_tenant_form(form_data, skip_duplicate_check=True)
    assert is_valid is True
    mock_get_session.assert_not_called()


# ============================================================================
# CRUD Tests
# ============================================================================


@patch("admin.utils.tenant_helper.get_db_session")
def test_create_tenant_success(mock_get_session, mock_session):
    """Test successful tenant creation."""
    mock_get_session.return_value.__enter__.return_value = mock_session

    tenant_data = {
        "name": "Acme Corp",
        "tenant_id": "acme-corp",
        "servicedesk_url": "https://acme.servicedesk.com",
        "api_key": "key_12345",
        "webhook_secret": "secret_xyz",
        "enhancement_preferences": {"ticket_history": True},
    }

    tenant = create_tenant(tenant_data)

    assert tenant is not None
    assert tenant.name == "Acme Corp"
    assert tenant.tenant_id == "acme-corp"
    assert tenant.is_active is True
    mock_session.add.assert_called_once()


@patch("admin.utils.tenant_helper.get_db_session")
def test_create_tenant_auto_generates_webhook_secret(mock_get_session, mock_session):
    """Test webhook secret is auto-generated if not provided."""
    mock_get_session.return_value.__enter__.return_value = mock_session

    tenant_data = {
        "name": "Acme Corp",
        "tenant_id": "acme-corp",
        "servicedesk_url": "https://acme.servicedesk.com",
        "api_key": "key_12345",
        # No webhook_secret provided
    }

    tenant = create_tenant(tenant_data)

    assert tenant is not None
    # Verify webhook secret was encrypted (indicates it was generated)
    assert tenant.webhook_signing_secret_encrypted


@patch("admin.utils.tenant_helper.get_db_session")
def test_create_tenant_duplicate_fails(mock_get_session, mock_session):
    """Test tenant creation fails for duplicate tenant_id."""
    mock_get_session.return_value.__enter__.return_value = mock_session
    mock_session.add.side_effect = IntegrityError("mock", "mock", "mock")

    tenant_data = {
        "name": "Acme Corp",
        "tenant_id": "acme-corp",
        "servicedesk_url": "https://acme.servicedesk.com",
        "api_key": "key_12345",
    }

    with pytest.raises(IntegrityError):
        create_tenant(tenant_data)


@patch("admin.utils.tenant_helper.get_db_session")
def test_get_all_tenants_active_only(mock_get_session, mock_session):
    """Test get_all_tenants returns only active tenants by default."""
    mock_get_session.return_value.__enter__.return_value = mock_session

    # Mock two tenants: one active, one inactive
    active_tenant = MagicMock()
    active_tenant.is_active = True
    inactive_tenant = MagicMock()
    inactive_tenant.is_active = False

    mock_session.all.return_value = [active_tenant]

    tenants = get_all_tenants(include_inactive=False)

    assert len(tenants) == 1
    assert tenants[0].is_active is True


@patch("admin.utils.tenant_helper.get_db_session")
def test_get_all_tenants_include_inactive(mock_get_session, mock_session):
    """Test get_all_tenants returns all tenants when include_inactive=True."""
    mock_get_session.return_value.__enter__.return_value = mock_session

    active_tenant = MagicMock()
    active_tenant.is_active = True
    inactive_tenant = MagicMock()
    inactive_tenant.is_active = False

    mock_session.all.return_value = [active_tenant, inactive_tenant]

    tenants = get_all_tenants(include_inactive=True)

    assert len(tenants) == 2


@patch("admin.utils.tenant_helper.get_db_session")
def test_get_tenant_by_id_success(mock_get_session, mock_session):
    """Test get_tenant_by_id returns correct tenant."""
    mock_get_session.return_value.__enter__.return_value = mock_session

    mock_tenant = MagicMock()
    mock_tenant.tenant_id = "acme-corp"
    mock_session.first.return_value = mock_tenant

    tenant = get_tenant_by_id("acme-corp")

    assert tenant is not None
    assert tenant.tenant_id == "acme-corp"


@patch("admin.utils.tenant_helper.get_db_session")
def test_get_tenant_by_id_not_found(mock_get_session, mock_session):
    """Test get_tenant_by_id returns None for non-existent tenant."""
    mock_get_session.return_value.__enter__.return_value = mock_session
    mock_session.first.return_value = None

    tenant = get_tenant_by_id("nonexistent")

    assert tenant is None


@patch("admin.utils.tenant_helper.get_db_session")
def test_update_tenant_success(mock_get_session, mock_session):
    """Test successful tenant update."""
    mock_get_session.return_value.__enter__.return_value = mock_session

    mock_tenant = MagicMock()
    mock_tenant.name = "Acme Corp"
    mock_session.first.return_value = mock_tenant

    updates = {
        "name": "Acme Corporation",
        "servicedesk_url": "https://new.servicedesk.com",
    }

    success = update_tenant("acme-corp", updates)

    assert success is True
    assert mock_tenant.name == "Acme Corporation"
    assert mock_tenant.servicedesk_url == "https://new.servicedesk.com"


@patch("admin.utils.tenant_helper.get_db_session")
def test_update_tenant_not_found(mock_get_session, mock_session):
    """Test update fails for non-existent tenant."""
    mock_get_session.return_value.__enter__.return_value = mock_session
    mock_session.first.return_value = None

    success = update_tenant("nonexistent", {"name": "New Name"})

    assert success is False


@patch("admin.utils.tenant_helper.get_db_session")
def test_soft_delete_tenant_success(mock_get_session, mock_session):
    """Test successful soft delete."""
    mock_get_session.return_value.__enter__.return_value = mock_session

    mock_tenant = MagicMock()
    mock_tenant.is_active = True
    mock_session.first.return_value = mock_tenant

    success = soft_delete_tenant("acme-corp")

    assert success is True
    assert mock_tenant.is_active is False


@patch("admin.utils.tenant_helper.get_db_session")
def test_soft_delete_tenant_not_found(mock_get_session, mock_session):
    """Test soft delete fails for non-existent tenant."""
    mock_get_session.return_value.__enter__.return_value = mock_session
    mock_session.first.return_value = None

    success = soft_delete_tenant("nonexistent")

    assert success is False
