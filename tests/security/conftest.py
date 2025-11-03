"""
Pytest fixtures for security tests.

Provides shared test data, mocked services, and database fixtures for
security testing including OWASP vulnerabilities, tenant isolation, and
webhook signature validation.
"""

import hmac
import hashlib
from datetime import datetime
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture
def test_tenant_id() -> str:
    """
    Test tenant ID constant.

    Returns:
        str: Tenant identifier for testing
    """
    return "test-tenant-001"


@pytest.fixture
def test_secret() -> str:
    """
    Test webhook shared secret (minimum 32 characters).

    Returns:
        str: Test secret key
    """
    return "test-webhook-secret-minimum-32-chars-required-here"


@pytest.fixture
def test_webhook_payload() -> dict:
    """
    Standard webhook payload for testing.

    Returns:
        dict: Sample webhook payload with event data
    """
    return {
        "event": "ticket_created",
        "ticket_id": "TKT-001",
        "tenant_id": "test-tenant-001",
        "title": "Test Ticket",
        "description": "Test ticket description",
        "created_at": datetime.utcnow().isoformat(),
    }


@pytest.fixture
def valid_signature(test_webhook_payload: dict, test_secret: str) -> str:
    """
    Generate valid HMAC-SHA256 signature for test payload.

    Args:
        test_webhook_payload: Test webhook data
        test_secret: Test secret key

    Returns:
        str: Hex-encoded HMAC-SHA256 signature
    """
    import json
    payload_bytes = json.dumps(test_webhook_payload).encode("utf-8")
    return hmac.new(
        key=test_secret.encode("utf-8"),
        msg=payload_bytes,
        digestmod=hashlib.sha256,
    ).hexdigest()


@pytest.fixture
def invalid_signature() -> str:
    """
    Invalid signature that won't match any payload.

    Returns:
        str: Hex string representing invalid signature
    """
    return "0" * 64  # Valid hex format but wrong signature


@pytest.fixture
def mock_audit_logger() -> Mock:
    """
    Mock AuditLogger for verification of security event logging.

    Returns:
        Mock: Mocked AuditLogger instance
    """
    logger = Mock()
    logger.log_security_event = AsyncMock()
    return logger


@pytest.fixture
def sql_injection_payloads() -> list:
    """
    Common SQL injection test payloads.

    Returns:
        list: SQL injection attack payloads
    """
    return [
        "'; DROP TABLE tenant_configs; --",
        "1' OR '1'='1",
        "admin' --",
        "1; DELETE FROM users; --",
        "' UNION SELECT * FROM passwords --",
    ]


@pytest.fixture
def xss_payloads() -> list:
    """
    Common XSS test payloads.

    Returns:
        list: XSS attack payloads
    """
    return [
        "<script>alert('xss')</script>",
        "<img src=x onerror=alert('xss')>",
        "javascript:alert('xss')",
        "<svg onload=alert('xss')>",
        "<iframe src=javascript:alert('xss')>",
    ]


@pytest.fixture
def command_injection_payloads() -> list:
    """
    Common command injection test payloads.

    Returns:
        list: Command injection attack payloads
    """
    return [
        "$(whoami)",
        "`id`",
        "| cat /etc/passwd",
        "; rm -rf /",
        "& del C:\\Windows\\*.*",
    ]


@pytest.fixture
def path_traversal_payloads() -> list:
    """
    Common path traversal test payloads.

    Returns:
        list: Path traversal attack payloads
    """
    return [
        "../../etc/passwd",
        "..\\..\\windows\\system32\\",
        "/etc/passwd",
        "C:\\Windows\\System32\\drivers\\etc\\hosts",
    ]
