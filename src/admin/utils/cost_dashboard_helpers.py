"""
Cost Dashboard UI Helpers.

Rendering functions for LLM cost dashboard visualizations.
Separates UI logic from page logic for maintainability.

Following 2025 Streamlit/Plotly best practices:
- Plotly Express for interactive charts
- Consistent color schemes
- Responsive layouts
- Proper data formatting
"""

import logging
from datetime import date
from typing import List

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.schemas.llm_cost import (
    AgentSpendDTO,
    BudgetUtilizationDTO,
    DailySpendDTO,
    ModelSpendDTO,
    SpendLogDetailDTO,
    TokenBreakdownDTO,
)

logger = logging.getLogger(__name__)


def render_cost_metrics_row_1(
    today_spend: float,
    week_spend: float,
    month_spend: float,
    total_30d: float,
    yesterday_spend: float = 0.0,
    last_week_spend: float = 0.0,
    last_month_spend: float = 0.0,
) -> None:
    """
    Render first row of cost metrics (4 columns).

    Args:
        today_spend: Today's total spend
        week_spend: This week's total spend
        month_spend: This month's total spend
        total_30d: Last 30 days total spend
        yesterday_spend: Yesterday's spend for delta
        last_week_spend: Last week's spend for delta
        last_month_spend: Last month's spend for delta
    """
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        delta_today = today_spend - yesterday_spend
        st.metric(
            label="💵 Today's Spend",
            value=f"${today_spend:.2f}",
            delta=f"${delta_today:.2f}" if delta_today != 0 else None,
            delta_color="inverse",  # Red for increase, green for decrease
        )

    with col2:
        delta_week = week_spend - last_week_spend
        st.metric(
            label="📅 This Week",
            value=f"${week_spend:.2f}",
            delta=f"${delta_week:.2f}" if delta_week != 0 else None,
            delta_color="inverse",
        )

    with col3:
        delta_month = month_spend - last_month_spend
        st.metric(
            label="📊 This Month",
            value=f"${month_spend:.2f}",
            delta=f"${delta_month:.2f}" if delta_month != 0 else None,
            delta_color="inverse",
        )

    with col4:
        st.metric(
            label="🗓️ Last 30 Days",
            value=f"${total_30d:.2f}",
        )


def render_cost_metrics_row_2(
    top_tenant_name: str,
    top_tenant_spend: float,
    top_agent_name: str,
    top_agent_spend: float,
) -> None:
    """
    Render second row of cost metrics (2 columns).

    Args:
        top_tenant_name: Name of top spending tenant
        top_tenant_spend: Top tenant's spend amount
        top_agent_name: Name of top spending agent
        top_agent_spend: Top agent's spend amount
    """
    col1, col2 = st.columns(2)

    with col1:
        st.metric(
            label=f"🏢 Top Tenant: {top_tenant_name}",
            value=f"${top_tenant_spend:.2f}",
        )

    with col2:
        st.metric(
            label=f"🤖 Top Agent: {top_agent_name}",
            value=f"${top_agent_spend:.2f}",
        )


def create_daily_spend_chart(trend_data: List[DailySpendDTO]) -> go.Figure:
    """
    Create interactive line chart for daily spend trend (AC#3).

    Args:
        trend_data: List of daily spend aggregations

    Returns:
        Plotly figure with line chart
    """
    if not trend_data:
        # Empty state
        fig = go.Figure()
        fig.add_annotation(
            text="No data available",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
        )
        return fig

    # Convert to DataFrame
    df = pd.DataFrame([
        {
            "Date": item.date,
            "Spend": item.total_spend,
            "Transactions": item.transaction_count,
        }
        for item in trend_data
    ])

    # Create line chart
    fig = px.line(
        df,
        x="Date",
        y="Spend",
        title="Daily Spend Trend (Last 30 Days)",
        labels={"Spend": "Cost ($)", "Date": "Date"},
        hover_data={"Transactions": True},
    )

    # Styling
    fig.update_traces(
        line_color="#1f77b4",
        line_width=2,
        mode="lines+markers",
    )
    fig.update_layout(
        hovermode="x unified",
        showlegend=False,
        height=400,
    )
    fig.update_xaxes(title_text="Date")
    fig.update_yaxes(title_text="Cost (USD)")

    return fig


def create_token_breakdown_chart(breakdown_data: List[TokenBreakdownDTO]) -> go.Figure:
    """
    Create pie chart for token usage breakdown (AC#4).

    Args:
        breakdown_data: List of token breakdowns by model

    Returns:
        Plotly figure with pie chart
    """
    if not breakdown_data:
        # Empty state
        fig = go.Figure()
        fig.add_annotation(
            text="No data available",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
        )
        return fig

    # Aggregate all models' tokens
    total_prompt = sum(item.prompt_tokens for item in breakdown_data)
    total_completion = sum(item.completion_tokens for item in breakdown_data)

    # Create pie chart data
    labels = ["Input Tokens", "Output Tokens"]
    values = [total_prompt, total_completion]
    colors = ["#636EFA", "#EF553B"]

    fig = go.Figure(
        data=[
            go.Pie(
                labels=labels,
                values=values,
                hole=0.3,  # Donut chart
                marker=dict(colors=colors),
                textposition="inside",
                textinfo="label+percent",
            )
        ]
    )

    fig.update_layout(
        title="Token Usage Breakdown (Input vs Output)",
        showlegend=True,
        height=400,
    )

    return fig


def render_budget_utilization_bars(
    utilization_data: List[BudgetUtilizationDTO],
) -> None:
    """
    Render budget utilization progress bars (AC#5).

    Args:
        utilization_data: List of tenant budget utilizations
    """
    if not utilization_data:
        st.info("No budget data available")
        return

    st.subheader("💰 Budget Utilization by Tenant")

    for util in utilization_data:
        # Color mapping
        color_map = {
            "green": "#00D26A",
            "yellow": "#FFD700",
            "red": "#FF4B4B",
        }
        progress_color = color_map.get(util.color, "#00D26A")

        # Display tenant name and utilization
        col1, col2 = st.columns([3, 1])

        with col1:
            # Progress bar
            progress_value = min(util.utilization_pct / 100, 1.0)
            st.markdown(
                f"**{util.tenant_name}** {'🔑 BYOK' if util.is_byok else ''}"
            )
            st.progress(
                progress_value,
                text=f"${util.current_spend:.2f} / ${util.budget_limit:.2f} ({util.utilization_pct:.1f}%)",
            )

        with col2:
            st.metric(
                label="Remaining",
                value=f"${util.remaining:.2f}",
            )


def create_agent_cost_table(agent_data: List[AgentSpendDTO]) -> pd.DataFrame:
    """
    Create formatted DataFrame for agent cost analysis (AC#6).

    Args:
        agent_data: List of agent spend summaries

    Returns:
        Pandas DataFrame with formatted columns
    """
    if not agent_data:
        return pd.DataFrame(
            columns=["Agent Name", "Executions", "Total Cost", "Avg Cost"]
        )

    df = pd.DataFrame([
        {
            "Agent Name": item.agent_name,
            "Executions": f"{item.execution_count:,}",
            "Total Cost": f"${item.total_cost:.2f}",
            "Avg Cost": f"${item.avg_cost:.4f}",
        }
        for item in agent_data
    ])

    return df


def generate_cost_report_csv(
    detail_data: List[SpendLogDetailDTO],
    start_date: date,
    end_date: date,
) -> str:
    """
    Generate CSV export for cost report (AC#7).

    Args:
        detail_data: List of detailed spend logs
        start_date: Start date for filename
        end_date: End date for filename

    Returns:
        CSV string
    """
    if not detail_data:
        # Empty CSV
        df = pd.DataFrame(
            columns=[
                "Date",
                "Tenant",
                "Agent",
                "Model",
                "Input Tokens",
                "Output Tokens",
                "Total Tokens",
                "Cost ($)",
            ]
        )
    else:
        df = pd.DataFrame([
            {
                "Date": item.date.isoformat(),
                "Tenant": item.tenant_name,
                "Agent": item.agent_name or "N/A",
                "Model": item.model,
                "Input Tokens": item.prompt_tokens,
                "Output Tokens": item.completion_tokens,
                "Total Tokens": item.total_tokens,
                "Cost ($)": f"{item.cost:.4f}",
            }
            for item in detail_data
        ])

    csv_string = df.to_csv(index=False)
    return csv_string


def get_csv_filename(start_date: date, end_date: date) -> str:
    """
    Generate CSV filename with date range.

    Args:
        start_date: Start date
        end_date: End date

    Returns:
        Filename string (e.g., "llm-costs-2025-11-01-to-2025-11-07.csv")
    """
    return f"llm-costs-{start_date.isoformat()}-to-{end_date.isoformat()}.csv"


def render_model_spend_table(model_data: List[ModelSpendDTO]) -> None:
    """
    Render model spend breakdown table.

    Args:
        model_data: List of model spend summaries
    """
    if not model_data:
        st.info("No model spend data available")
        return

    st.subheader("📊 Spend by Model")

    df = pd.DataFrame([
        {
            "Model": item.model_name,
            "Total Spend": f"${item.total_spend:.2f}",
            "Total Tokens": f"{item.total_tokens:,}",
            "Input Tokens": f"{item.prompt_tokens:,}",
            "Output Tokens": f"{item.completion_tokens:,}",
        }
        for item in model_data
    ])

    st.dataframe(df, use_container_width=True, hide_index=True)
