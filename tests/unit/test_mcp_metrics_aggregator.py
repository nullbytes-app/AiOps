"""
Unit tests for MCP Server Metrics Aggregation Service.

Story: 11.2.4 - Enhanced MCP Health Monitoring
Module: src/services/mcp_metrics_aggregator.py

Test Coverage:
    - get_server_metrics() - aggregation with SQL percentiles
    - calculate_trend() - 24h trend analysis
    - get_percentile() - manual percentile calculation
    - Error handling and edge cases
"""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import MCPServer, MCPServerMetric, TenantConfig
from src.schemas.mcp_metrics import MCPServerMetrics
from src.services.mcp_metrics_aggregator import (
    calculate_trend,
    get_percentile,
    get_server_metrics,
)


@pytest.mark.asyncio
async def test_get_server_metrics_success_with_data(db_session: AsyncSession):
    """Test get_server_metrics returns aggregated metrics with real data."""
    # Create tenant
    tenant = TenantConfig(
        id=uuid4(),
        tenant_id=f"test-tenant-{uuid4().hex[:8]}",
        name="Test Tenant",
        servicedesk_url="https://test.servicedesk.com",
        servicedesk_api_key_encrypted="encrypted-test-key",
        webhook_signing_secret_encrypted="encrypted-test-secret",
    )
    db_session.add(tenant)

    # Create MCP server
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

    # Create metrics (288 checks over 24h @ 5min intervals)
    now = datetime.now(timezone.utc)
    for i in range(288):
        timestamp = now - timedelta(minutes=i * 5)
        # 95% success, 5% timeout
        status = "success" if i % 20 != 0 else "timeout"
        response_time = 100 + (i % 10) * 10 if status == "success" else 5000

        metric = MCPServerMetric(
            mcp_server_id=server.id,
            tenant_id=tenant.id,
            response_time_ms=response_time,
            check_timestamp=timestamp,
            status=status,
            error_message="Timeout" if status == "timeout" else None,
            error_type="TimeoutError" if status == "timeout" else None,
            check_type="tools_list",
            transport_type="stdio",
        )
        db_session.add(metric)

    await db_session.commit()

    # Test: Get metrics for 24 hours
    result = await get_server_metrics(server.id, 24, db_session)

    # Assertions
    assert isinstance(result, MCPServerMetrics)
    assert result.server_id == server.id
    assert result.server_name == "test-server"
    assert result.period_hours == 24
    assert result.metrics.total_checks == 288
    assert 0.94 <= result.metrics.success_rate <= 0.96  # ~95%
    assert 0.04 <= result.metrics.error_rate <= 0.06  # ~5%
    assert result.metrics.avg_response_time_ms > 0
    assert result.metrics.p50_response_time_ms > 0
    assert result.metrics.p95_response_time_ms > 0
    assert result.metrics.p99_response_time_ms > 0
    assert result.metrics.max_response_time_ms == 5000
    assert result.metrics.errors_by_type == {"TimeoutError": 15}  # 288 checks: i % 20 == 0 → 0, 20, 40, ..., 280 (15 timeouts)
    assert 94.0 <= result.metrics.uptime_percentage <= 96.0
    assert result.metrics.last_24h_trend in ["improving", "stable", "degrading"]


@pytest.mark.asyncio
async def test_get_server_metrics_no_data_returns_empty(db_session: AsyncSession):
    """Test get_server_metrics returns empty metrics when no data exists."""
    # Create tenant and server without metrics
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

    # Test: Get metrics (no data)
    result = await get_server_metrics(server.id, 24, db_session)

    # Assertions
    assert result.metrics.total_checks == 0
    assert result.metrics.success_rate == 0.0
    assert result.metrics.error_rate == 0.0
    assert result.metrics.avg_response_time_ms == 0
    assert result.metrics.p50_response_time_ms == 0
    assert result.metrics.p95_response_time_ms == 0
    assert result.metrics.p99_response_time_ms == 0
    assert result.metrics.max_response_time_ms == 0
    assert result.metrics.errors_by_type == {}
    assert result.metrics.uptime_percentage == 0.0
    assert result.metrics.last_24h_trend == "stable"


@pytest.mark.asyncio
async def test_get_server_metrics_server_not_found_raises_error(db_session: AsyncSession):
    """Test get_server_metrics raises ValueError when server not found."""
    non_existent_id = uuid4()

    with pytest.raises(ValueError, match="Server .* not found"):
        await get_server_metrics(non_existent_id, 24, db_session)


@pytest.mark.asyncio
async def test_get_server_metrics_invalid_period_raises_error(db_session: AsyncSession):
    """Test get_server_metrics raises ValueError for invalid period_hours."""
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

    # Test: period_hours < 1
    with pytest.raises(ValueError, match="period_hours must be between 1 and 168"):
        await get_server_metrics(server.id, 0, db_session)

    # Test: period_hours > 168
    with pytest.raises(ValueError, match="period_hours must be between 1 and 168"):
        await get_server_metrics(server.id, 200, db_session)


@pytest.mark.asyncio
async def test_calculate_trend_improving(db_session: AsyncSession):
    """Test calculate_trend returns 'improving' when response time decreases > 10%."""
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

    # Previous 24h: avg 200ms
    for i in range(48):
        metric = MCPServerMetric(
            mcp_server_id=server.id,
            tenant_id=tenant.id,
            response_time_ms=200,
            check_timestamp=now - timedelta(hours=48 - i),
            status="success",
            check_type="tools_list",
            transport_type="stdio",
        )
        db_session.add(metric)

    # Last 24h: avg 100ms (50% improvement > 10% threshold)
    for i in range(48):
        metric = MCPServerMetric(
            mcp_server_id=server.id,
            tenant_id=tenant.id,
            response_time_ms=100,
            check_timestamp=now - timedelta(hours=24 - i),
            status="success",
            check_type="tools_list",
            transport_type="stdio",
        )
        db_session.add(metric)

    await db_session.commit()

    # Test
    trend = await calculate_trend(server.id, db_session)
    assert trend == "improving"


@pytest.mark.asyncio
async def test_calculate_trend_degrading(db_session: AsyncSession):
    """Test calculate_trend returns 'degrading' when response time increases > 10%."""
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

    # Previous 24h: avg 100ms
    for i in range(48):
        metric = MCPServerMetric(
            mcp_server_id=server.id,
            tenant_id=tenant.id,
            response_time_ms=100,
            check_timestamp=now - timedelta(hours=48 - i),
            status="success",
            check_type="tools_list",
            transport_type="stdio",
        )
        db_session.add(metric)

    # Last 24h: avg 200ms (100% degradation > 10% threshold)
    for i in range(48):
        metric = MCPServerMetric(
            mcp_server_id=server.id,
            tenant_id=tenant.id,
            response_time_ms=200,
            check_timestamp=now - timedelta(hours=24 - i),
            status="success",
            check_type="tools_list",
            transport_type="stdio",
        )
        db_session.add(metric)

    await db_session.commit()

    # Test
    trend = await calculate_trend(server.id, db_session)
    assert trend == "degrading"


@pytest.mark.asyncio
async def test_calculate_trend_stable(db_session: AsyncSession):
    """Test calculate_trend returns 'stable' when change within ±10%."""
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

    # Previous 24h: avg 100ms
    for i in range(48):
        metric = MCPServerMetric(
            mcp_server_id=server.id,
            tenant_id=tenant.id,
            response_time_ms=100,
            check_timestamp=now - timedelta(hours=48 - i),
            status="success",
            check_type="tools_list",
            transport_type="stdio",
        )
        db_session.add(metric)

    # Last 24h: avg 105ms (5% increase, within ±10%)
    for i in range(48):
        metric = MCPServerMetric(
            mcp_server_id=server.id,
            tenant_id=tenant.id,
            response_time_ms=105,
            check_timestamp=now - timedelta(hours=24 - i),
            status="success",
            check_type="tools_list",
            transport_type="stdio",
        )
        db_session.add(metric)

    await db_session.commit()

    # Test
    trend = await calculate_trend(server.id, db_session)
    assert trend == "stable"


@pytest.mark.asyncio
async def test_calculate_trend_no_data_returns_stable(db_session: AsyncSession):
    """Test calculate_trend returns 'stable' when no data exists."""
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

    # Test
    trend = await calculate_trend(server.id, db_session)
    assert trend == "stable"


@pytest.mark.asyncio
async def test_get_percentile_success():
    """Test get_percentile calculates correct percentile values."""
    values = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]

    # P50 (median)
    p50 = await get_percentile(values, 50)
    assert p50 == 50

    # P95
    p95 = await get_percentile(values, 95)
    assert p95 >= 85  # Allow ±10% tolerance for small datasets (95 - 10)

    # P99
    p99 = await get_percentile(values, 99)
    assert p99 >= 89  # Allow ±10% tolerance for small datasets (99 - 10)

    # P0 (min)
    p0 = await get_percentile(values, 0)
    assert p0 == 10

    # P100 (max)
    p100 = await get_percentile(values, 100)
    assert p100 == 100


@pytest.mark.asyncio
async def test_get_percentile_empty_list_raises_error():
    """Test get_percentile raises ValueError for empty list."""
    with pytest.raises(ValueError, match="Cannot calculate percentile of empty list"):
        await get_percentile([], 50)


@pytest.mark.asyncio
async def test_get_percentile_invalid_percentile_raises_error():
    """Test get_percentile raises ValueError for invalid percentile."""
    values = [10, 20, 30]

    # percentile < 0
    with pytest.raises(ValueError, match="Percentile must be between 0 and 100"):
        await get_percentile(values, -1)

    # percentile > 100
    with pytest.raises(ValueError, match="Percentile must be between 0 and 100"):
        await get_percentile(values, 101)


@pytest.mark.asyncio
async def test_get_server_metrics_filters_by_period(db_session: AsyncSession):
    """Test get_server_metrics only includes metrics within period_hours."""
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

    # Add 10 metrics within last hour
    for i in range(10):
        metric = MCPServerMetric(
            mcp_server_id=server.id,
            tenant_id=tenant.id,
            response_time_ms=100,
            check_timestamp=now - timedelta(minutes=i * 5),
            status="success",
            check_type="tools_list",
            transport_type="stdio",
        )
        db_session.add(metric)

    # Add 10 metrics from 25 hours ago (outside 24h period)
    for i in range(10):
        metric = MCPServerMetric(
            mcp_server_id=server.id,
            tenant_id=tenant.id,
            response_time_ms=200,
            check_timestamp=now - timedelta(hours=25, minutes=i * 5),
            status="success",
            check_type="tools_list",
            transport_type="stdio",
        )
        db_session.add(metric)

    await db_session.commit()

    # Test: Get metrics for 1 hour
    result_1h = await get_server_metrics(server.id, 1, db_session)
    assert result_1h.metrics.total_checks == 10  # Only last hour

    # Test: Get metrics for 24 hours
    result_24h = await get_server_metrics(server.id, 24, db_session)
    assert result_24h.metrics.total_checks == 10  # Excludes 25h ago metrics

    # Test: Get metrics for 168 hours (7 days)
    result_168h = await get_server_metrics(server.id, 168, db_session)
    assert result_168h.metrics.total_checks == 20  # Includes all metrics
