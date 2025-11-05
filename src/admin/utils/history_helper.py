"""
Enhancement History Helper for Streamlit Admin UI.

This module provides query functions for the Enhancement History page,
enabling filtering, pagination, and export of enhancement_history records.

Key Features:
- Server-side filtering by tenant, status, date range, and search query
- Pagination with LIMIT/OFFSET for performance (AC7: < 5 seconds for 10K rows)
- CSV export with flattened JSON fields
- Status badge formatting with Streamlit color syntax
- Caching with @st.cache_data(ttl=30) for near-real-time updates
"""

import json
from datetime import date, datetime, timedelta
from typing import Optional

import pandas as pd
import streamlit as st
from loguru import logger
from sqlalchemy import and_, func, or_

from admin.utils.db_helper import get_db_session
from database.models import EnhancementHistory


@st.cache_data(ttl=30)
def get_enhancement_history(
    tenant_id: Optional[str] = None,
    status: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    search_query: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[dict], int]:
    """
    Query enhancement history with filters and pagination.

    Server-side filtering and pagination for optimal performance with large datasets.
    All WHERE clauses and LIMIT/OFFSET are applied at database level.

    Args:
        tenant_id: Filter by tenant_id (None for all tenants)
        status: Filter by status (pending/completed/failed, None for all)
        date_from: Filter records created_at >= date_from
        date_to: Filter records created_at <= date_to
        search_query: Case-insensitive partial match on ticket_id
        page: Page number (1-indexed)
        page_size: Records per page (default 50)

    Returns:
        tuple[list[dict], int]: (records for current page, total matching count)
            Each record dict contains all EnhancementHistory fields

    Raises:
        Exception: If database query fails

    Examples:
        >>> records, total = get_enhancement_history(tenant_id="acme", page=1, page_size=50)
        >>> print(f"Found {total} records, showing first {len(records)}")
        Found 156 records, showing first 50
    """
    try:
        with get_db_session() as session:
            # Build base query
            query = session.query(EnhancementHistory)

            # Apply filters dynamically (server-side WHERE clauses)
            filters = []

            if tenant_id and tenant_id != "All":
                filters.append(EnhancementHistory.tenant_id == tenant_id)

            if status and status != "All":
                filters.append(EnhancementHistory.status == status)

            if date_from:
                # Convert date to datetime for comparison
                datetime_from = datetime.combine(date_from, datetime.min.time())
                filters.append(EnhancementHistory.created_at >= datetime_from)

            if date_to:
                # Include entire day (until 23:59:59)
                datetime_to = datetime.combine(date_to, datetime.max.time())
                filters.append(EnhancementHistory.created_at <= datetime_to)

            if search_query:
                # Case-insensitive partial match on ticket_id
                filters.append(EnhancementHistory.ticket_id.ilike(f"%{search_query}%"))

            # Apply all filters
            if filters:
                query = query.filter(and_(*filters))

            # Get total count before pagination
            total_count = query.count()

            # Apply ordering (most recent first)
            query = query.order_by(EnhancementHistory.created_at.desc())

            # Apply pagination (LIMIT/OFFSET)
            offset = (page - 1) * page_size
            query = query.limit(page_size).offset(offset)

            # Execute query and convert to dict list
            records = query.all()
            records_dict = [
                {
                    "id": str(rec.id),
                    "tenant_id": rec.tenant_id,
                    "ticket_id": rec.ticket_id,
                    "status": rec.status,
                    "context_gathered": rec.context_gathered,
                    "llm_output": rec.llm_output,
                    "error_message": rec.error_message,
                    "processing_time_ms": rec.processing_time_ms,
                    "created_at": rec.created_at,
                    "completed_at": rec.completed_at,
                }
                for rec in records
            ]

            return records_dict, total_count

    except Exception as e:
        logger.error(f"Failed to query enhancement history: {e}")
        raise


@st.cache_data(ttl=60)
def get_all_tenant_ids() -> list[str]:
    """
    Get distinct tenant_id values from enhancement_history table.

    Used to populate tenant filter dropdown on History page.

    Returns:
        list[str]: Sorted list of unique tenant_id values

    Examples:
        >>> get_all_tenant_ids()
        ['acme', 'globex', 'initech']
    """
    try:
        with get_db_session() as session:
            # Query distinct tenant_id values
            tenant_ids = (
                session.query(EnhancementHistory.tenant_id)
                .distinct()
                .order_by(EnhancementHistory.tenant_id)
                .all()
            )

            # Extract strings from tuples
            return [tenant[0] for tenant in tenant_ids]

    except Exception as e:
        logger.error(f"Failed to get tenant IDs: {e}")
        return []


@st.cache_data
def convert_to_csv(df: pd.DataFrame) -> bytes:
    """
    Convert DataFrame to CSV bytes with UTF-8 encoding.

    Flattens nested JSON fields (context_gathered) to CSV-compatible string format.
    Applied @st.cache_data for performance on repeated exports.

    Args:
        df: Pandas DataFrame with enhancement history data

    Returns:
        bytes: UTF-8 encoded CSV data ready for download

    Examples:
        >>> df = pd.DataFrame([{"ticket_id": "INC-123", "status": "completed"}])
        >>> csv_bytes = convert_to_csv(df)
        >>> print(len(csv_bytes))
        45
    """
    try:
        # Create copy to avoid modifying original
        export_df = df.copy()

        # Flatten JSON fields to string for CSV compatibility
        if "context_gathered" in export_df.columns:
            export_df["context_summary"] = export_df["context_gathered"].apply(
                lambda x: json.dumps(x) if x and isinstance(x, dict) else ""
            )
            export_df = export_df.drop(columns=["context_gathered"])

        # Convert to CSV with UTF-8 encoding
        csv_string = export_df.to_csv(index=False)
        return csv_string.encode("utf-8")

    except Exception as e:
        logger.error(f"Failed to convert DataFrame to CSV: {e}")
        # Return empty CSV with headers on error
        return "".encode("utf-8")


def format_status_badge(status: str) -> str:
    """
    Format status as colored badge using Streamlit markdown syntax.

    Uses Streamlit's native color syntax: :green[], :red[], :blue[]

    Args:
        status: Enhancement status (pending/completed/failed)

    Returns:
        str: Markdown string with colored status indicator

    Examples:
        >>> format_status_badge("completed")
        ':green[● completed]'
        >>> format_status_badge("failed")
        ':red[● failed]'
        >>> format_status_badge("pending")
        ':blue[● pending]'
    """
    status_lower = status.lower()

    if status_lower == "completed":
        return ":green[● completed]"
    elif status_lower == "failed":
        return ":red[● failed]"
    elif status_lower == "pending":
        return ":blue[● pending]"
    else:
        # Fallback for unknown status
        return f":gray[● {status}]"
