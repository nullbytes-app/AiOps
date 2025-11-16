"""
LLM Cost Dashboard Page.

Real-time cost tracking dashboard with metrics, charts, and CSV export.
Implements all 8 acceptance criteria from Story 8.16.

Following 2025 Streamlit best practices:
- @st.fragment for auto-refresh
- @st.cache_data(ttl=60) for performance
- Plotly for interactive charts
- Responsive layout with st.columns

AC Coverage:
- AC#1: Dashboard page created (07_LLM_Costs.py)
- AC#2: Overview metrics (today, week, month, top tenant/agent)
- AC#3: Daily spend trend chart (30 days)
- AC#4: Token usage pie chart
- AC#5: Budget utilization progress bars
- AC#6: Agent cost table
- AC#7: CSV export with filters
- AC#8: 60-second auto-refresh with timestamp
"""

import logging
from datetime import date, datetime, timedelta

import streamlit as st

from src.admin.utils.cost_dashboard_helpers import (
    create_agent_cost_table,
    create_daily_spend_chart,
    create_token_breakdown_chart,
    generate_cost_report_csv,
    get_csv_filename,
    render_budget_utilization_bars,
    render_cost_metrics_row_1,
    render_cost_metrics_row_2,
    render_model_spend_table,
)
from src.database.session import get_async_session
from src.services.llm_cost_service import LLMCostService

logger = logging.getLogger(__name__)

st.title("💰 LLM Cost Dashboard")
st.markdown("Real-time tracking of LLM API costs, token usage, and budget utilization")

# Initialize session state for refresh tracking
if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = datetime.now()


@st.cache_data(ttl=60, show_spinner=False)
def fetch_cost_summary(tenant_id_param):
    """
    Fetch cost summary with caching (AC#8 - performance optimization).

    Args:
        tenant_id_param: Tenant ID for filtering

    Returns:
        Cost summary DTO
    """
    import asyncio

    async def _fetch():
        async for db in get_async_session():
            cost_service = LLMCostService(db)
            return await cost_service.get_cost_summary(tenant_id=tenant_id_param)

    return asyncio.run(_fetch())


@st.cache_data(ttl=60, show_spinner=False)
def fetch_daily_trend(days, tenant_id_param):
    """Fetch daily spend trend with caching."""
    import asyncio

    async def _fetch():
        async for db in get_async_session():
            cost_service = LLMCostService(db)
            return await cost_service.get_daily_spend_trend(days=days, tenant_id=tenant_id_param)

    return asyncio.run(_fetch())


@st.cache_data(ttl=60, show_spinner=False)
def fetch_token_breakdown(start_date_param, end_date_param, tenant_id_param):
    """Fetch token breakdown with caching."""
    import asyncio

    async def _fetch():
        async for db in get_async_session():
            cost_service = LLMCostService(db)
            return await cost_service.get_token_breakdown(
                start_date=start_date_param,
                end_date=end_date_param,
                tenant_id=tenant_id_param,
            )

    return asyncio.run(_fetch())


@st.cache_data(ttl=60, show_spinner=False)
def fetch_budget_utilization(tenant_id_param):
    """Fetch budget utilization with caching."""
    import asyncio

    async def _fetch():
        async for db in get_async_session():
            cost_service = LLMCostService(db)
            return await cost_service.get_budget_utilization(tenant_id=tenant_id_param)

    return asyncio.run(_fetch())


@st.cache_data(ttl=60, show_spinner=False)
def fetch_agent_stats(start_date_param, end_date_param, tenant_id_param, limit):
    """Fetch agent execution stats with caching."""
    import asyncio

    async def _fetch():
        async for db in get_async_session():
            cost_service = LLMCostService(db)
            return await cost_service.get_spend_by_agent(
                start_date=start_date_param,
                end_date=end_date_param,
                tenant_id=tenant_id_param,
                limit=limit,
            )

    return asyncio.run(_fetch())


@st.cache_data(ttl=60, show_spinner=False)
def fetch_model_spend(start_date_param, end_date_param, tenant_id_param):
    """Fetch model spend breakdown with caching."""
    import asyncio

    async def _fetch():
        async for db in get_async_session():
            cost_service = LLMCostService(db)
            return await cost_service.get_spend_by_model(
                start_date=start_date_param,
                end_date=end_date_param,
                tenant_id=tenant_id_param,
            )

    return asyncio.run(_fetch())


@st.fragment(run_every=60)  # AC#8: Auto-refresh every 60 seconds
def dashboard_fragment():
    """
    Dashboard content with auto-refresh.

    Uses @st.fragment decorator (2025 Streamlit best practice) for
    isolated updates without full page reload.
    """
    # Update last refresh timestamp
    st.session_state.last_refresh = datetime.now()

    # Filters row
    st.markdown("### 🔍 Filters")
    filter_col1, filter_col2, filter_col3 = st.columns([2, 2, 1])

    with filter_col1:
        # Date range selector (default: last 30 days)
        default_start = date.today() - timedelta(days=30)
        default_end = date.today()
        date_range = st.date_input(
            "Date Range",
            value=(default_start, default_end),
            max_value=date.today(),
            help="Select start and end dates for cost analysis",
        )
        if isinstance(date_range, tuple) and len(date_range) == 2:
            start_date, end_date = date_range
        else:
            start_date = default_start
            end_date = default_end

    with filter_col2:
        # Tenant filter (TODO: Implement tenant dropdown)
        st.selectbox(
            "Tenant",
            options=["All Tenants"],
            help="Filter by specific tenant (admin only)",
        )
        tenant_id = None  # TODO: Get from authentication

    with filter_col3:
        # Manual refresh button
        if st.button("🔄 Refresh Now", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    # Last updated timestamp (AC#8)
    st.caption(
        f"Last Updated: {st.session_state.last_refresh.strftime('%Y-%m-%d %H:%M:%S')}"
    )

    st.divider()

    # Fetch data with spinner
    with st.spinner("Loading cost data..."):
        try:
            # Fetch all data in a single async context (avoid multiple event loops)
            import asyncio

            async def fetch_all_data():
                async for db in get_async_session():
                    cost_service = LLMCostService(db)

                    # Fetch all data sequentially (AsyncPG doesn't support concurrent ops on same session)
                    summary_data = await cost_service.get_cost_summary(tenant_id=tenant_id)
                    trend_data_result = await cost_service.get_daily_spend_trend(
                        days=30, tenant_id=tenant_id
                    )
                    token_data_result = await cost_service.get_token_breakdown(
                        start_date=start_date, end_date=end_date, tenant_id=tenant_id
                    )
                    budget_data_result = await cost_service.get_budget_utilization(
                        tenant_id=tenant_id
                    )
                    agent_data_result = await cost_service.get_spend_by_agent(
                        start_date=start_date,
                        end_date=end_date,
                        tenant_id=tenant_id,
                        limit=10,
                    )
                    model_data_result = await cost_service.get_spend_by_model(
                        start_date=start_date, end_date=end_date, tenant_id=tenant_id
                    )
                    export_logs = await cost_service.get_detailed_logs(
                        start_date=start_date, end_date=end_date, tenant_id=tenant_id
                    )

                    return (
                        summary_data,
                        trend_data_result,
                        token_data_result,
                        budget_data_result,
                        agent_data_result,
                        model_data_result,
                        export_logs,
                    )

            (
                summary,
                trend_data,
                token_data,
                budget_data,
                agent_data,
                model_data,
                detail_logs,
            ) = asyncio.run(fetch_all_data())

        except Exception as e:
            st.error(f"Error loading cost data: {e}")
            logger.error(f"Dashboard data fetch error: {e}", exc_info=True)
            return

    # AC#2: Overview Metrics (Row 1)
    st.markdown("### 📊 Overview Metrics")
    render_cost_metrics_row_1(
        today_spend=summary.today_spend,
        week_spend=summary.week_spend,
        month_spend=summary.month_spend,
        total_30d=summary.total_spend_30d,
    )

    # AC#2: Overview Metrics (Row 2)
    if summary.top_tenant or summary.top_agent:
        top_tenant_name = summary.top_tenant.tenant_name if summary.top_tenant else "N/A"
        top_tenant_spend = (
            summary.top_tenant.total_spend if summary.top_tenant else 0.0
        )
        top_agent_name = summary.top_agent.agent_name if summary.top_agent else "N/A"
        top_agent_spend = summary.top_agent.total_cost if summary.top_agent else 0.0

        render_cost_metrics_row_2(
            top_tenant_name, top_tenant_spend, top_agent_name, top_agent_spend
        )

    st.divider()

    # Charts Section (AC#3, AC#4)
    st.markdown("### 📈 Cost Trends & Token Usage")
    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        # AC#3: Daily spend trend chart
        trend_fig = create_daily_spend_chart(trend_data)
        st.plotly_chart(trend_fig, use_container_width=True, key="trend_chart")

    with chart_col2:
        # AC#4: Token breakdown pie chart
        token_fig = create_token_breakdown_chart(token_data)
        st.plotly_chart(token_fig, use_container_width=True, key="token_chart")

    st.divider()

    # AC#5: Budget Utilization
    render_budget_utilization_bars(budget_data)

    st.divider()

    # AC#6: Agent Cost Analysis Table
    st.markdown("### 🤖 Cost Per Agent")
    agent_df = create_agent_cost_table(agent_data)
    st.dataframe(
        agent_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Agent Name": st.column_config.TextColumn("Agent Name", width="medium"),
            "Executions": st.column_config.TextColumn("Executions", width="small"),
            "Total Cost": st.column_config.TextColumn("Total Cost", width="small"),
            "Avg Cost": st.column_config.TextColumn("Avg Cost/Exec", width="small"),
        },
    )

    st.divider()

    # Model Spend Table
    render_model_spend_table(model_data)

    st.divider()

    # AC#7: CSV Export
    st.markdown("### 📥 Export Cost Report")
    export_col1, export_col2 = st.columns([3, 1])

    with export_col1:
        st.markdown(
            f"Export detailed cost logs from **{start_date}** to **{end_date}**"
        )

    with export_col2:
        # Generate CSV on demand (using already-fetched data)
        try:
            csv_data = generate_cost_report_csv(detail_logs, start_date, end_date)
            csv_filename = get_csv_filename(start_date, end_date)

            st.download_button(
                label="📥 Export CSV",
                data=csv_data,
                file_name=csv_filename,
                mime="text/csv",
                use_container_width=True,
            )
        except Exception as e:
            st.error(f"Export failed: {e}")
            logger.error(f"CSV export error: {e}", exc_info=True)


# Render dashboard
dashboard_fragment()
