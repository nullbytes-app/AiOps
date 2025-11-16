"""
Execution History Helper for Streamlit Admin UI.

This module provides query functions for the Execution History page (Story 10.2),
enabling filtering, pagination, and display of agent test execution records.

Key Features:
- Server-side filtering by agent, tenant, status, and date range
- Pagination with LIMIT/OFFSET for performance
- Status badge formatting with Streamlit color syntax
- Caching with @st.cache_data(ttl=30) for near-real-time updates
- Agent and tenant list retrieval for filter dropdowns
"""

from datetime import date, datetime
from typing import Optional
from uuid import UUID

import pandas as pd
import streamlit as st
from loguru import logger
from sqlalchemy import and_

from admin.utils.db_helper import get_db_session
from database.models import Agent, AgentTestExecution, TenantConfig


def get_execution_history(
    agent_id: Optional[str] = None,
    tenant_id: Optional[str] = None,
    status: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[dict], int]:
    """
    Query agent test execution history with filters and pagination.

    Server-side filtering and pagination for optimal performance with large datasets.
    All WHERE clauses and LIMIT/OFFSET are applied at database level.

    Args:
        agent_id: Filter by agent_id UUID (None for all agents)
        tenant_id: Filter by tenant_id (None for all tenants)
        status: Filter by status (success/failed, None for all)
        date_from: Filter records created_at >= date_from
        date_to: Filter records created_at <= date_to
        page: Page number (1-indexed)
        page_size: Records per page (default 50)

    Returns:
        tuple[list[dict], int]: (records for current page, total matching count)
            Each record dict contains execution fields with agent and tenant names

    Raises:
        Exception: If database query fails

    Examples:
        >>> records, total = get_execution_history(tenant_id="acme", page=1, page_size=50)
        >>> print(f"Found {total} records, showing first {len(records)}")
        Found 156 records, showing first 50
    """
    try:
        with get_db_session() as session:
            # Build base query with joins for agent and tenant names
            query = (
                session.query(
                    AgentTestExecution,
                    Agent.name.label("agent_name"),
                    TenantConfig.name.label("tenant_name"),
                )
                .join(Agent, AgentTestExecution.agent_id == Agent.id)
                # FIX: Join to tenant_configs.tenant_id (VARCHAR), not .id (UUID)
                # This matches the schema change in migration 008
                .join(TenantConfig, AgentTestExecution.tenant_id == TenantConfig.tenant_id)
            )

            # Apply filters dynamically (server-side WHERE clauses)
            filters = []

            if agent_id and agent_id != "All":
                try:
                    agent_uuid = UUID(agent_id)
                    filters.append(AgentTestExecution.agent_id == agent_uuid)
                except ValueError:
                    logger.warning(f"Invalid agent_id UUID format: {agent_id}")

            if tenant_id and tenant_id != "All":
                filters.append(AgentTestExecution.tenant_id == tenant_id)

            if status and status != "All":
                # Normalize status: API returns "success" but display shows "completed"
                db_status = "success" if status.lower() == "completed" else status.lower()
                filters.append(AgentTestExecution.status == db_status)

            if date_from:
                # Convert date to datetime for comparison
                datetime_from = datetime.combine(date_from, datetime.min.time())
                filters.append(AgentTestExecution.created_at >= datetime_from)

            if date_to:
                # Include entire day (until 23:59:59)
                datetime_to = datetime.combine(date_to, datetime.max.time())
                filters.append(AgentTestExecution.created_at <= datetime_to)

            # Apply all filters
            if filters:
                query = query.filter(and_(*filters))

            # Get total count before pagination
            total_count = query.count()

            # Apply ordering (most recent first - AC5)
            query = query.order_by(AgentTestExecution.created_at.desc())

            # Apply pagination (LIMIT/OFFSET)
            offset = (page - 1) * page_size
            query = query.limit(page_size).offset(offset)

            # Execute query and convert to dict list
            results = query.all()
            records_dict = [
                {
                    "id": str(result.AgentTestExecution.id),
                    "agent_id": str(result.AgentTestExecution.agent_id),
                    "agent_name": result.agent_name,
                    "tenant_id": result.AgentTestExecution.tenant_id,
                    "tenant_name": result.tenant_name,
                    "status": result.AgentTestExecution.status,
                    "execution_time": result.AgentTestExecution.execution_time,
                    "created_at": result.AgentTestExecution.created_at,
                    "payload": result.AgentTestExecution.payload,
                    "execution_trace": result.AgentTestExecution.execution_trace,
                    "token_usage": result.AgentTestExecution.token_usage,
                    "errors": result.AgentTestExecution.errors,
                }
                for result in results
            ]

            return records_dict, total_count

    except Exception as e:
        logger.error(f"Failed to query execution history: {e}")
        raise


@st.cache_data(ttl=60)
def get_agent_list() -> list[dict]:
    """
    Get list of agents with ID and name for filter dropdown.

    Used to populate agent filter dropdown on Execution History page.

    Returns:
        list[dict]: List of dicts with 'id' and 'name' keys, sorted by name

    Examples:
        >>> get_agent_list()
        [{'id': '123e4567-...', 'name': 'Support Agent'}, {'id': '987fcdeb-...', 'name': 'Ticket Agent'}]
    """
    try:
        with get_db_session() as session:
            # Query agents ordered by name
            agents = session.query(Agent.id, Agent.name).order_by(Agent.name).all()

            # Convert to list of dicts
            return [{"id": str(agent.id), "name": agent.name} for agent in agents]

    except Exception as e:
        logger.error(f"Failed to get agent list: {e}")
        return []


def get_tenant_list() -> list[dict]:
    """
    Get list of tenants with ID and name for filter dropdown.

    Used to populate tenant filter dropdown on Execution History page.

    Returns:
        list[dict]: List of dicts with 'id' and 'name' keys, sorted by name

    Examples:
        >>> get_tenant_list()
        [{'id': 'acme-corp', 'name': 'Acme Corp'}, {'id': 'globex-inc', 'name': 'Globex Inc'}]
    """
    try:
        with get_db_session() as session:
            # Query tenants with tenant_id (VARCHAR), not id (UUID)
            tenants = (
                session.query(TenantConfig.tenant_id, TenantConfig.name)
                .order_by(TenantConfig.name)
                .all()
            )

            # Convert to list of dicts - using tenant_id as 'id' field
            return [{"id": tenant.tenant_id, "name": tenant.name} for tenant in tenants]

    except Exception as e:
        logger.error(f"Failed to get tenant list: {e}")
        return []


def format_execution_table(records: list[dict]) -> pd.DataFrame:
    """
    Format execution records for st.dataframe display.

    Transforms execution records into a pandas DataFrame with formatted columns:
    - Status with color-coded badges (AC1)
    - Execution time with millisecond formatting (AC1)
    - Timestamps formatted to human-readable strings (AC1)

    Args:
        records: List of execution record dicts from get_execution_history()

    Returns:
        pd.DataFrame: Formatted DataFrame ready for st.dataframe display

    Examples:
        >>> records = [{"id": "123", "agent_name": "Agent", "status": "success", ...}]
        >>> df = format_execution_table(records)
        >>> print(df.columns.tolist())
        ['ID', 'Agent', 'Tenant', 'Status', 'Time (ms)', 'Created']
    """
    if not records:
        return pd.DataFrame()

    data = []
    for record in records:
        # Normalize status: "success" -> "completed" for display (Constraint 4)
        display_status = "completed" if record["status"] == "success" else record["status"]

        # Extract execution time milliseconds (JSON field)
        execution_time_ms = record.get("execution_time", {}).get("total_duration_ms", 0)

        data.append(
            {
                "ID": record["id"][:8] + "...",  # Truncate UUID for display
                "Agent": record["agent_name"],
                "Tenant": record["tenant_name"],
                "Status": format_status_badge(display_status),
                "Time (ms)": execution_time_ms,
                "Created": record["created_at"].strftime("%Y-%m-%d %H:%M:%S"),
            }
        )

    return pd.DataFrame(data)


def format_status_badge(status: str) -> str:
    """
    Format status as colored badge using Streamlit markdown syntax.

    Uses Streamlit's native color syntax: :green[], :red[] (Constraint 5)

    Args:
        status: Execution status (completed/failed)

    Returns:
        str: Markdown string with colored status indicator

    Examples:
        >>> format_status_badge("completed")
        '🟢 Completed'
        >>> format_status_badge("failed")
        '🔴 Failed'
    """
    status_lower = status.lower()

    if status_lower == "completed" or status_lower == "success":
        return "🟢 Completed"
    elif status_lower == "failed":
        return "🔴 Failed"
    else:
        # Fallback for unknown status
        return f"⚪ {status.title()}"
