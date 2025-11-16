"""
Integration tests for MCP Server Health Metrics Workflow.

Story: 11.2.4 - Enhanced MCP Health Monitoring

Test Coverage:
    - End-to-end health check → metrics recording → aggregation → API
    - Metrics cleanup task
    - Prometheus metrics instrumentation
    - Streamlit dashboard helpers
"""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import MCPServer, MCPServerMetric, TenantConfig
from src.main import app
from src.monitoring.metrics import (
    mcp_health_check_duration_seconds,
    mcp_health_checks_total,
    mcp_server_health_status,
)
from src.services.mcp_health_monitor import (
    check_server_health,
    perform_detailed_health_check,
    record_metric,
)


@pytest.mark.asyncio
async def test_health_check_to_metrics_workflow(db_session: AsyncSession):
    """Test complete workflow: health check → detailed check → record metric → database."""
    # Setup: Create tenant and server
    tenant = TenantConfig(
        id=uuid4(),
        tenant_id=f"test-tenant-{uuid4().hex[:8]}",
        name="Test Tenant",
        servicedesk_url="https://test.servicedesk.com",
        servicedesk_api_key_encrypted="encrypted-test-key",
        webhook_signing_secret_encrypted="encrypted-test-secret",
    )
    db_session.add(tenant)

    server = MCPServer(
        id=uuid4(),
        tenant_id=tenant.id,
        name="test-filesystem-server",
        transport_type="stdio",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
        status="active",
    )
    db_session.add(server)
    await db_session.commit()

    # Execute: Perform detailed health check
    metric = await perform_detailed_health_check(server)

    # Verify: MCPHealthMetric created
    assert metric.mcp_server_id == server.id
    assert metric.tenant_id == tenant.id
    assert metric.response_time_ms >= 0
    assert metric.status in ["success", "timeout", "error", "connection_failed"]
    assert metric.check_type == "tools_list"
    assert metric.transport_type == "stdio"

    # Execute: Record metric to database
    await record_metric(metric, db_session)

    # Verify: Metric persisted to database
    stmt = select(MCPServerMetric).where(MCPServerMetric.mcp_server_id == server.id)
    result = await db_session.execute(stmt)
    db_metrics = result.scalars().all()

    assert len(db_metrics) == 1
    assert db_metrics[0].response_time_ms == metric.response_time_ms
    assert db_metrics[0].status == metric.status.value


@pytest.mark.asyncio
async def test_metrics_api_endpoint_integration(db_session: AsyncSession):
    """Test GET /api/v1/mcp-servers/{id}/metrics endpoint with real data."""
    # Setup: Create tenant and server
    tenant = TenantConfig(
        id=uuid4(),
        tenant_id=f"test-tenant-{uuid4().hex[:8]}",
        name="Test Tenant",
        servicedesk_url="https://test.servicedesk.com",
        servicedesk_api_key_encrypted="encrypted-test-key",
        webhook_signing_secret_encrypted="encrypted-test-secret",
    )
    db_session.add(tenant)

    server = MCPServer(
        id=uuid4(),
        tenant_id=tenant.id,
        name="test-server",
        transport_type="stdio",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
        status="active",
    )
    db_session.add(server)
    await db_session.commit()

    # Create metrics (50 checks over last hour)
    now = datetime.now(timezone.utc)
    for i in range(50):
        metric = MCPServerMetric(
            mcp_server_id=server.id,
            tenant_id=tenant.id,
            response_time_ms=100 + i,
            check_timestamp=now - timedelta(minutes=i),
            status="success" if i % 10 != 0 else "timeout",
            error_message="Timeout" if i % 10 == 0 else None,
            error_type="TimeoutError" if i % 10 == 0 else None,
            check_type="tools_list",
            transport_type="stdio",
        )
        db_session.add(metric)

    await db_session.commit()

    # Execute: Call API endpoint
    client = TestClient(app)
    response = client.get(
        f"/api/v1/mcp-servers/{server.id}/metrics",
        params={"period_hours": 1},
        headers={"X-Tenant-ID": str(tenant.id)},
    )

    # Verify: Response structure and values
    assert response.status_code == 200
    data = response.json()

    assert data["server_id"] == str(server.id)
    assert data["server_name"] == "test-server"
    assert data["period_hours"] == 1

    metrics = data["metrics"]
    assert metrics["total_checks"] == 50
    assert 0.80 <= metrics["success_rate"] <= 0.92  # ~90% success
    assert 0.08 <= metrics["error_rate"] <= 0.20  # ~10% error
    assert metrics["avg_response_time_ms"] > 0
    assert metrics["p50_response_time_ms"] > 0
    assert metrics["p95_response_time_ms"] > 0
    assert metrics["p99_response_time_ms"] > 0
    assert metrics["max_response_time_ms"] > 0
    assert "TimeoutError" in metrics["errors_by_type"]
    assert 80.0 <= metrics["uptime_percentage"] <= 92.0
    assert metrics["last_24h_trend"] in ["improving", "stable", "degrading"]


@pytest.mark.asyncio
async def test_metrics_api_endpoint_tenant_isolation(db_session: AsyncSession):
    """Test metrics API endpoint enforces tenant isolation."""
    # Setup: Create two tenants with servers
    tenant1 = TenantConfig(
        id=uuid4(),
        tenant_id=f"tenant-1-{uuid4().hex[:8]}",
        name="Tenant 1",
        servicedesk_url="https://tenant1.servicedesk.com",
        servicedesk_api_key_encrypted="encrypted-key-1",
        webhook_signing_secret_encrypted="encrypted-secret-1",
    )
    tenant2 = TenantConfig(
        id=uuid4(),
        tenant_id=f"tenant-2-{uuid4().hex[:8]}",
        name="Tenant 2",
        servicedesk_url="https://tenant2.servicedesk.com",
        servicedesk_api_key_encrypted="encrypted-key-2",
        webhook_signing_secret_encrypted="encrypted-secret-2",
    )
    db_session.add_all([tenant1, tenant2])

    server1 = MCPServer(
        id=uuid4(),
        tenant_id=tenant1.id,
        name="tenant1-server",
        transport_type="stdio",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
        status="active",
    )
    server2 = MCPServer(
        id=uuid4(),
        tenant_id=tenant2.id,
        name="tenant2-server",
        transport_type="stdio",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
        status="active",
    )
    db_session.add_all([server1, server2])
    await db_session.commit()

    # Execute: Tenant1 tries to access Tenant2's server metrics
    client = TestClient(app)
    response = client.get(
        f"/api/v1/mcp-servers/{server2.id}/metrics",
        params={"period_hours": 24},
        headers={"X-Tenant-ID": str(tenant1.id)},
    )

    # Verify: 404 Not Found (tenant isolation)
    assert response.status_code == 404
    assert "not found or not accessible" in response.json()["detail"]


@pytest.mark.asyncio
async def test_metrics_api_endpoint_invalid_period(db_session: AsyncSession):
    """Test metrics API endpoint validates period_hours parameter."""
    tenant = TenantConfig(
        id=uuid4(),
        tenant_id=f"test-tenant-{uuid4().hex[:8]}",
        name="Test Tenant",
        servicedesk_url="https://test.servicedesk.com",
        servicedesk_api_key_encrypted="encrypted-test-key",
        webhook_signing_secret_encrypted="encrypted-test-secret",
    )
    db_session.add(tenant)

    server = MCPServer(
        id=uuid4(),
        tenant_id=tenant.id,
        name="test-server",
        transport_type="stdio",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
        status="active",
    )
    db_session.add(server)
    await db_session.commit()

    client = TestClient(app)

    # Test: period_hours < 1
    response = client.get(
        f"/api/v1/mcp-servers/{server.id}/metrics",
        params={"period_hours": 0},
        headers={"X-Tenant-ID": str(tenant.id)},
    )
    assert response.status_code == 422  # Validation error

    # Test: period_hours > 168
    response = client.get(
        f"/api/v1/mcp-servers/{server.id}/metrics",
        params={"period_hours": 200},
        headers={"X-Tenant-ID": str(tenant.id)},
    )
    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_cleanup_task_deletes_old_metrics(db_session: AsyncSession):
    """Test cleanup_old_mcp_metrics_task deletes metrics older than 7 days."""
    from src.workers.tasks import cleanup_old_mcp_metrics_task

    # Setup: Create tenant and server
    tenant = TenantConfig(
        id=uuid4(),
        tenant_id=f"test-tenant-{uuid4().hex[:8]}",
        name="Test Tenant",
        servicedesk_url="https://test.servicedesk.com",
        servicedesk_api_key_encrypted="encrypted-test-key",
        webhook_signing_secret_encrypted="encrypted-test-secret",
    )
    db_session.add(tenant)

    server = MCPServer(
        id=uuid4(),
        tenant_id=tenant.id,
        name="test-server",
        transport_type="stdio",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
        status="active",
    )
    db_session.add(server)
    await db_session.commit()

    now = datetime.now(timezone.utc)

    # Create 10 recent metrics (within 7 days)
    for i in range(10):
        metric = MCPServerMetric(
            mcp_server_id=server.id,
            tenant_id=tenant.id,
            response_time_ms=100,
            check_timestamp=now - timedelta(days=i),
            status="success",
            check_type="tools_list",
            transport_type="stdio",
        )
        db_session.add(metric)

    # Create 10 old metrics (older than 7 days)
    for i in range(10):
        metric = MCPServerMetric(
            mcp_server_id=server.id,
            tenant_id=tenant.id,
            response_time_ms=100,
            check_timestamp=now - timedelta(days=8 + i),
            status="success",
            check_type="tools_list",
            transport_type="stdio",
        )
        db_session.add(metric)

    await db_session.commit()

    # Verify: 20 total metrics before cleanup
    stmt = select(MCPServerMetric).where(MCPServerMetric.mcp_server_id == server.id)
    result = await db_session.execute(stmt)
    assert len(result.scalars().all()) == 20

    # Execute: Run cleanup task
    result = cleanup_old_mcp_metrics_task()

    # Verify: Cleanup result
    assert result["deleted"] == 10
    assert result["retention_days"] == 7

    # Verify: Only recent metrics remain
    await db_session.expire_all()  # Refresh from database
    result = await db_session.execute(stmt)
    remaining_metrics = result.scalars().all()
    assert len(remaining_metrics) == 10

    # Verify: All remaining metrics are within 7 days
    for metric in remaining_metrics:
        age_days = (now - metric.check_timestamp).days
        assert age_days <= 7


@pytest.mark.asyncio
async def test_streamlit_fetch_metrics_helper(db_session: AsyncSession):
    """Test metrics endpoint (used by Streamlit dashboard fetch_mcp_server_metrics helper)."""
    # Setup: Create tenant, server, and metrics
    tenant = TenantConfig(
        id=uuid4(),
        tenant_id=f"test-tenant-{uuid4().hex[:8]}",
        name="Test Tenant",
        servicedesk_url="https://test.servicedesk.com",
        servicedesk_api_key_encrypted="encrypted-test-key",
        webhook_signing_secret_encrypted="encrypted-test-secret",
    )
    db_session.add(tenant)

    server = MCPServer(
        id=uuid4(),
        tenant_id=tenant.id,
        name="test-server",
        transport_type="stdio",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
        status="active",
    )
    db_session.add(server)
    await db_session.commit()

    # Create 100 metrics
    now = datetime.now(timezone.utc)
    for i in range(100):
        metric = MCPServerMetric(
            mcp_server_id=server.id,
            tenant_id=tenant.id,
            response_time_ms=100 + i,
            check_timestamp=now - timedelta(hours=i),
            status="success",
            check_type="tools_list",
            transport_type="stdio",
        )
        db_session.add(metric)

    await db_session.commit()

    # Execute: Fetch metrics via API endpoint (TestClient simulates HTTP calls)
    client = TestClient(app)
    response = client.get(
        f"/api/v1/mcp-servers/{server.id}/metrics",
        params={"period_hours": 24},
        headers={"X-Tenant-ID": str(tenant.id)},
    )

    # Verify: Response structure
    assert response.status_code == 200
    result = response.json()
    assert result["server_id"] == str(server.id)
    assert result["server_name"] == "test-server"
    assert result["period_hours"] == 24
    assert result["metrics"]["total_checks"] == 24  # Last 24 hours
    assert result["metrics"]["success_rate"] == 1.0  # All success
    assert result["metrics"]["avg_response_time_ms"] > 0


@pytest.mark.asyncio
async def test_prometheus_metrics_instrumentation(db_session: AsyncSession):
    """Test Prometheus metrics are updated by record_metric()."""
    # Setup: Create tenant and server
    tenant = TenantConfig(
        id=uuid4(),
        tenant_id=f"test-tenant-{uuid4().hex[:8]}",
        name="Test Tenant",
        servicedesk_url="https://test.servicedesk.com",
        servicedesk_api_key_encrypted="encrypted-test-key",
        webhook_signing_secret_encrypted="encrypted-test-secret",
    )
    db_session.add(tenant)

    server = MCPServer(
        id=uuid4(),
        tenant_id=tenant.id,
        name="test-prometheus-server",
        transport_type="stdio",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
        status="active",
    )
    db_session.add(server)
    await db_session.commit()

    # Get baseline Prometheus metric values
    health_status_before = mcp_server_health_status.labels(
        server_id=str(server.id),
        server_name=server.name,
        transport_type="stdio",
        tenant_id=str(tenant.id),
    )._value.get()

    checks_total_before = mcp_health_checks_total.labels(
        server_id=str(server.id),
        server_name=server.name,
        transport_type="stdio",
        status="success",
    )._value.get()

    # Execute: Perform health check and record metric
    from src.schemas.mcp_metrics import MCPHealthCheckStatus, MCPHealthMetric

    metric = MCPHealthMetric(
        mcp_server_id=server.id,
        tenant_id=tenant.id,
        response_time_ms=150,
        check_timestamp=datetime.now(timezone.utc),
        status=MCPHealthCheckStatus.SUCCESS,
        error_message=None,
        error_type=None,
        check_type="tools_list",
        transport_type="stdio",
    )

    await record_metric(metric, db_session)

    # Verify: Prometheus metrics updated
    health_status_after = mcp_server_health_status.labels(
        server_id=str(server.id),
        server_name=server.name,
        transport_type="stdio",
        tenant_id=str(tenant.id),
    )._value.get()

    checks_total_after = mcp_health_checks_total.labels(
        server_id=str(server.id),
        server_name=server.name,
        transport_type="stdio",
        status="success",
    )._value.get()

    assert health_status_after == 1  # Active
    assert checks_total_after > checks_total_before  # Counter incremented


@pytest.mark.asyncio
async def test_complete_health_check_workflow(db_session: AsyncSession):
    """Test complete workflow: check_server_health → updates server → records metric."""
    # Setup: Create tenant and server
    tenant = TenantConfig(
        id=uuid4(),
        tenant_id=f"test-tenant-{uuid4().hex[:8]}",
        name="Test Tenant",
        servicedesk_url="https://test.servicedesk.com",
        servicedesk_api_key_encrypted="encrypted-test-key",
        webhook_signing_secret_encrypted="encrypted-test-secret",
    )
    db_session.add(tenant)

    server = MCPServer(
        id=uuid4(),
        tenant_id=tenant.id,
        name="test-complete-workflow",
        transport_type="stdio",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
        status="active",
        consecutive_failures=0,
    )
    db_session.add(server)
    await db_session.commit()

    # Execute: Run complete health check
    result = await check_server_health(server, db_session)

    # Verify: Server status updated
    await db_session.refresh(server)
    assert server.last_health_check is not None
    assert server.status in ["active", "error", "inactive"]

    # Verify: Metric recorded to database
    stmt = select(MCPServerMetric).where(MCPServerMetric.mcp_server_id == server.id)
    db_result = await db_session.execute(stmt)
    metrics = db_result.scalars().all()

    assert len(metrics) == 1
    assert metrics[0].response_time_ms >= 0
    assert metrics[0].status in ["success", "timeout", "error", "connection_failed"]
