# Story 8.10B: Budget Enforcement - Admin UI

Status: drafted

Parent Story: 8.10 (Budget Enforcement with Grace Period)

## Story

As a tenant administrator,
I want a dashboard to view budget usage and configure budget limits,
So that I can monitor LLM costs and adjust thresholds before hitting limits.

## Acceptance Criteria

1. Budget dashboard displays current spend, max budget, percentage used, and days remaining
2. Progress bar visualization: Green (<80%), Yellow (80-100%), Red (>100%), Dark Red (>110% blocked)
3. Alert history table shows last 10 budget alerts with timestamp, event type, and spend
4. Real-time data fetched from LiteLLM API with 60-second cache (via BudgetService.get_budget_status())
5. Budget configuration form allows editing: max_budget, alert_threshold (50-100%), grace_threshold (100-150%), budget_duration (30d/60d/90d)
6. Form validation prevents invalid inputs: max_budget > 0, thresholds within valid ranges
7. "Save Budget Config" button updates tenant_configs database and LiteLLM virtual key
8. Error handling displays clear messages: "Budget data unavailable" if API fails, validation errors for invalid inputs

## Tasks / Subtasks

- [ ] Task 1: Create Budget Dashboard Section (AC: #1, #2, #3, #4) [file: src/admin/pages/02_Tenant_Management.py]
  - [ ] Subtask 1.1: Add "Budget Usage" section to tenant detail view (after existing sections)
  - [ ] Subtask 1.2: Fetch budget status via BudgetService.get_budget_status(tenant_id)
  - [ ] Subtask 1.3: Display metrics: Current Spend ($), Max Budget ($), Percentage Used (%), Days Until Reset
  - [ ] Subtask 1.4: Implement progress bar with color coding: st.progress() with custom CSS
  - [ ] Subtask 1.5: Add grace period indicator: "Grace Period: Active" (if 100-110%) or "Blocked" (if >110%)
  - [ ] Subtask 1.6: Display budget reset date: "Resets on 2025-12-01 (25 days)"
  - [ ] Subtask 1.7: Add @st.cache_data(ttl=60) for budget status (60-second cache)
  - [ ] Subtask 1.8: Handle API failures gracefully: display "Budget data unavailable" with st.error()

- [ ] Task 2: Create Alert History Table (AC: #3) [file: src/admin/pages/02_Tenant_Management.py]
  - [ ] Subtask 2.1: Query budget_alert_history table for tenant (ORDER BY created_at DESC LIMIT 10)
  - [ ] Subtask 2.2: Display table with columns: Timestamp, Event Type, Spend, Max Budget, Percentage
  - [ ] Subtask 2.3: Format event types: "80% Threshold", "100% Budget Exceeded", "Projected Limit"
  - [ ] Subtask 2.4: Color-code rows: Yellow (80%), Red (100%), Dark Red (>110%)
  - [ ] Subtask 2.5: Add "No alerts yet" message if table empty
  - [ ] Subtask 2.6: Add pagination if > 10 alerts (st.expander for older alerts)

- [ ] Task 3: Create Budget Configuration Form (AC: #5, #6, #7) [file: src/admin/pages/02_Tenant_Management.py]
  - [ ] Subtask 3.1: Add "Budget Configuration" form section (st.form())
  - [ ] Subtask 3.2: Input field: max_budget (st.number_input, min=0.01, step=50.00, default=500.00)
  - [ ] Subtask 3.3: Input field: alert_threshold (st.slider, min=50, max=100, default=80, format="%d%%")
  - [ ] Subtask 3.4: Input field: grace_threshold (st.slider, min=100, max=150, default=110, format="%d%%")
  - [ ] Subtask 3.5: Input field: budget_duration (st.selectbox, options=["30d", "60d", "90d"], default="30d")
  - [ ] Subtask 3.6: Add form validation: Ensure max_budget > 0, alert_threshold 50-100, grace_threshold 100-150
  - [ ] Subtask 3.7: Display calculated block amount: "Will block at $550 (110% of $500)"
  - [ ] Subtask 3.8: "Save Budget Config" submit button (st.form_submit_button())

- [ ] Task 4: Implement Budget Config Save Logic (AC: #7, #8) [file: src/admin/utils/budget_helpers.py]
  - [ ] Subtask 4.1: Create helper function: update_tenant_budget_config(tenant_id, max_budget, alert_threshold, grace_threshold, budget_duration)
  - [ ] Subtask 4.2: Update tenant_configs table with new values (via TenantService)
  - [ ] Subtask 4.3: Call LiteLLM API to update virtual key max_budget: POST /key/update
  - [ ] Subtask 4.4: Calculate new budget_reset_at: created_at + parse_duration(budget_duration)
  - [ ] Subtask 4.5: Create audit log entry: "budget_config_updated" with old/new values
  - [ ] Subtask 4.6: Handle API failures: display error message, rollback database update
  - [ ] Subtask 4.7: Success feedback: st.success("Budget configuration updated successfully")
  - [ ] Subtask 4.8: Clear cache to force refresh: st.cache_data.clear()

- [ ] Task 5: Add Budget Visualization Charts (AC: #2) [file: src/admin/pages/02_Tenant_Management.py]
  - [ ] Subtask 5.1: Create spend trend chart: last 30 days daily spend (if data available)
  - [ ] Subtask 5.2: Use st.line_chart() or plotly for interactive chart
  - [ ] Subtask 5.3: Add threshold lines: 80% (yellow dashed), 100% (red solid), 110% (dark red solid)
  - [ ] Subtask 5.4: Display chart only if >= 7 days of data available
  - [ ] Subtask 5.5: Add "Insufficient data" message if < 7 days

- [ ] Task 6: Create Budget Helper Module (AC: #4, #7) [file: src/admin/utils/budget_helpers.py]
  - [ ] Subtask 6.1: Create module: src/admin/utils/budget_helpers.py
  - [ ] Subtask 6.2: Function: get_budget_display_data(tenant_id) -> dict (spend, budget, percentage, days_remaining, color)
  - [ ] Subtask 6.3: Function: calculate_progress_bar_color(percentage: int) -> str (green/yellow/red/darkred)
  - [ ] Subtask 6.4: Function: format_budget_duration(duration: str) -> str ("30 days", "60 days", "90 days")
  - [ ] Subtask 6.5: Function: update_tenant_budget_config(tenant_id, **config) -> bool
  - [ ] Subtask 6.6: Add comprehensive docstrings (Google style)
  - [ ] Subtask 6.7: Add type hints for all functions

- [ ] Task 7: Unit Tests (AC: #6, #8) [file: tests/unit/test_budget_ui_helpers.py]
  - [ ] Subtask 7.1: Test get_budget_display_data - returns correct formatted data
  - [ ] Subtask 7.2: Test calculate_progress_bar_color - correct colors for all ranges
  - [ ] Subtask 7.3: Test format_budget_duration - correct formatting for 30d/60d/90d
  - [ ] Subtask 7.4: Test update_tenant_budget_config - database updated, API called
  - [ ] Subtask 7.5: Test validation errors - invalid max_budget raises exception
  - [ ] Subtask 7.6: Test API failure handling - rollback on LiteLLM error
  - [ ] Subtask 7.7: Test audit logging - budget_config_updated event logged

- [ ] Task 8: Integration Tests (AC: #1-8) [file: tests/integration/test_budget_ui.py]
  - [ ] Subtask 8.1: Test dashboard displays budget status correctly
  - [ ] Subtask 8.2: Test progress bar color changes with percentage
  - [ ] Subtask 8.3: Test alert history table populated from database
  - [ ] Subtask 8.4: Test configuration form saves successfully
  - [ ] Subtask 8.5: Test configuration validation rejects invalid inputs
  - [ ] Subtask 8.6: Test cache invalidation after config update
  - [ ] Subtask 8.7: Test error handling when LiteLLM API unavailable

## Dev Notes

### Streamlit UI Patterns (2025)

**Progress Bar with Color Coding:**
```python
import streamlit as st

def render_budget_progress_bar(percentage: int) -> None:
    """Render budget progress bar with color coding."""
    color = calculate_progress_bar_color(percentage)

    # Custom CSS for progress bar colors
    st.markdown(f"""
        <style>
        .stProgress > div > div > div > div {{
            background-color: {color};
        }}
        </style>
    """, unsafe_allow_html=True)

    st.progress(min(percentage, 100) / 100.0)

def calculate_progress_bar_color(percentage: int) -> str:
    """Calculate progress bar color based on percentage."""
    if percentage < 80:
        return "#28a745"  # Green
    elif percentage < 100:
        return "#ffc107"  # Yellow
    elif percentage < 110:
        return "#dc3545"  # Red
    else:
        return "#8b0000"  # Dark Red
```

**Cached Budget Data Fetching:**
```python
@st.cache_data(ttl=60)  # Cache for 60 seconds
def fetch_budget_status(tenant_id: str) -> dict:
    """Fetch budget status from BudgetService."""
    try:
        budget_service = BudgetService()
        status = await budget_service.get_budget_status(tenant_id)
        return {
            "spend": status.spend,
            "max_budget": status.max_budget,
            "percentage": status.percentage_used,
            "days_remaining": status.days_until_reset,
            "grace_remaining": status.grace_remaining,
        }
    except Exception as e:
        logger.error(f"Budget status fetch failed: {e}")
        return None
```

**Budget Configuration Form:**
```python
with st.form("budget_config_form"):
    st.subheader("Budget Configuration")

    max_budget = st.number_input(
        "Maximum Budget ($)",
        min_value=0.01,
        value=current_config.max_budget,
        step=50.0,
        help="Maximum monthly LLM spend in USD"
    )

    alert_threshold = st.slider(
        "Alert Threshold (%)",
        min_value=50,
        max_value=100,
        value=current_config.alert_threshold,
        format="%d%%",
        help="Send alert when spend reaches this percentage"
    )

    grace_threshold = st.slider(
        "Grace Threshold (%)",
        min_value=100,
        max_value=150,
        value=current_config.grace_threshold,
        format="%d%%",
        help="Block requests when spend exceeds this percentage"
    )

    budget_duration = st.selectbox(
        "Budget Period",
        options=["30d", "60d", "90d"],
        index=["30d", "60d", "90d"].index(current_config.budget_duration),
        help="Budget reset cycle"
    )

    # Calculate and display block amount
    block_amount = max_budget * (grace_threshold / 100)
    st.info(f"Will block at ${block_amount:.2f} ({grace_threshold}% of ${max_budget:.2f})")

    submitted = st.form_submit_button("Save Budget Configuration")

    if submitted:
        # Validate and save
        if max_budget <= 0:
            st.error("Max budget must be greater than $0")
        elif alert_threshold < 50 or alert_threshold > 100:
            st.error("Alert threshold must be between 50% and 100%")
        elif grace_threshold < 100 or grace_threshold > 150:
            st.error("Grace threshold must be between 100% and 150%")
        else:
            success = update_tenant_budget_config(
                tenant_id=tenant_id,
                max_budget=max_budget,
                alert_threshold=alert_threshold,
                grace_threshold=grace_threshold,
                budget_duration=budget_duration
            )
            if success:
                st.success("Budget configuration updated successfully!")
                st.cache_data.clear()  # Clear cache to refresh data
                st.rerun()
            else:
                st.error("Failed to update budget configuration. Please try again.")
```

**Alert History Table:**
```python
def render_alert_history(tenant_id: str) -> None:
    """Render budget alert history table."""
    alerts = fetch_alert_history(tenant_id, limit=10)

    if not alerts:
        st.info("No budget alerts yet")
        return

    # Format data for display
    data = []
    for alert in alerts:
        event_type = format_event_type(alert.event_type)
        color = get_alert_color(alert.percentage)
        data.append({
            "Timestamp": alert.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "Event": event_type,
            "Spend": f"${alert.spend:.2f}",
            "Budget": f"${alert.max_budget:.2f}",
            "Percentage": f"{alert.percentage}%",
        })

    # Display with custom styling
    st.dataframe(
        data,
        use_container_width=True,
        hide_index=True,
    )
```

### File Size Management

**Current File Size:**
- `02_Tenant_Management.py`: ~450 lines (estimated)
- Adding budget UI: ~150 lines
- **Total: ~600 lines** (20% over 500-line limit)

**Mitigation Strategy:**
1. Extract budget UI to separate module: `src/admin/components/budget_ui.py` (~150 lines)
2. Extract budget helpers: `src/admin/utils/budget_helpers.py` (~200 lines)
3. Keep main file at ~450 lines (within limit)

**Refactored Structure:**
```
src/admin/
├── pages/
│   └── 02_Tenant_Management.py (450 lines) - Main tenant UI
├── components/
│   ├── agent_forms.py (existing)
│   └── budget_ui.py (150 lines) - Budget dashboard/config components
└── utils/
    ├── agent_helpers.py (existing)
    └── budget_helpers.py (200 lines) - Budget data fetching/updating
```

### LiteLLM Virtual Key Update

**Update Virtual Key Budget:**
```python
import httpx
from src.config import settings

async def update_virtual_key_budget(
    tenant_id: str,
    virtual_key: str,
    max_budget: float
) -> bool:
    """Update LiteLLM virtual key max_budget."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{settings.litellm_proxy_url}/key/update",
                headers={"Authorization": f"Bearer {settings.litellm_master_key}"},
                json={
                    "key": virtual_key,
                    "max_budget": max_budget,
                }
            )
            response.raise_for_status()
            return True
    except Exception as e:
        logger.error(f"Virtual key update failed: {e}")
        return False
```

### Learnings from Story 6.x (Admin UI)

**Best Practices:**
- Use `@st.cache_data(ttl=60)` for API calls (60-second cache)
- Use `st.form()` for grouped inputs (prevents re-runs on each input change)
- Use `st.rerun()` after database updates to refresh UI
- Use custom CSS sparingly (Streamlit theming preferred)
- Use `st.error()`, `st.warning()`, `st.success()` for feedback

**Performance:**
- Cache budget status (60s TTL reduces API calls)
- Use `@st.fragment` for auto-refresh sections (Streamlit 1.30+)
- Limit database queries (pagination for alert history)

**Testing:**
- Mock database calls (AsyncSession fixtures)
- Mock LiteLLM API calls (httpx mock)
- Test validation logic (pytest parametrize for edge cases)
- Test Streamlit UI rendering (streamlit.testing.v1 - if available)

### References

**Story 8.10 Context:**
- [Source: docs/stories/8-10-budget-enforcement-with-grace-period.md] - Parent story with backend implementation
- [Source: src/services/budget_service.py] - BudgetService.get_budget_status() to use

**Streamlit Admin UI Patterns:**
- [Source: src/admin/pages/02_Tenant_Management.py] - Existing tenant management UI patterns
- [Source: src/admin/components/agent_forms.py] - Form patterns to follow
- [Source: src/admin/utils/agent_helpers.py] - Helper module structure

**Story 6.2-6.7 Learnings:**
- [Source: docs/stories/6-2-implement-system-status-dashboard-page.md] - Dashboard patterns
- [Source: docs/stories/6-6-integrate-real-time-metrics-display.md] - Real-time data with caching

---

## Dev Agent Record

### Context Reference

- Parent story: `docs/stories/8-10-budget-enforcement-with-grace-period.md`
- Backend services: `src/services/budget_service.py`, `src/services/llm_service.py`
- Existing UI patterns: `src/admin/pages/02_Tenant_Management.py`

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

*To be filled during implementation*

### Completion Notes List

*To be filled during implementation*

### File List

**New Files:**
- `src/admin/components/budget_ui.py` (150 lines) - Budget dashboard and configuration UI components
- `src/admin/utils/budget_helpers.py` (200 lines) - Budget data fetching and update helpers
- `tests/unit/test_budget_ui_helpers.py` (250 lines, 7 tests)
- `tests/integration/test_budget_ui.py` (300 lines, 7 tests)

**Modified Files:**
- `src/admin/pages/02_Tenant_Management.py` (+50 lines, import and render budget components)

## Change Log

### Version 1.0 - 2025-11-06
**Story Created as Follow-Up to 8.10**
- Defined Admin UI scope for budget enforcement
- 8 tasks identified: dashboard, alert history, configuration form, save logic, charts, helpers, unit tests, integration tests
- File size mitigation: Extract components and helpers to stay under 500-line limit
- Estimated effort: 6-8 hours
- Priority: MEDIUM (operational enhancement, not blocking core deployment)
