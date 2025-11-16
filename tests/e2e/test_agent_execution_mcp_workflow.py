"""
E2E Test: Workflow 3 - Agent Execution with MCP Tools.

This test validates end-to-end agent execution invoking MCP tools, ensuring
the complete MCP integration pipeline works from UI to tool invocation to
execution history.

Test Journey:
1. Setup prerequisites (MCP server with tools, agent with assigned tools)
2. Navigate to Agent Testing page
3. Execute agent with input
4. Verify execution completes successfully
5. Verify execution history

Acceptance Criteria: AC4
"""

import pytest
from playwright.sync_api import Page, expect

from src.database.models import Agent, MCPServer, TenantConfig  # type: ignore[attr-defined]


@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.skip(
    reason="E2E test requires live Streamlit server on localhost:8502. Run manually during E2E testing phase. Issue tracked in Story 12.4"
)
def test_agent_execution_mcp_workflow(
    admin_page: Page,
    streamlit_app_url: str,
    test_tenant: TenantConfig,
    test_mcp_server: MCPServer,
    test_agent: Agent,
) -> None:
    """
    Test agent execution with MCP tool invocation.

    This E2E test validates:
    - Navigation to Agent Testing page works
    - Agent execution form accepts input
    - Agent executes successfully
    - MCP tool is INVOKED (not just assigned)
    - Tool result appears in agent response
    - Execution appears in history
    - Execution details show MCP tool usage

    Prevents: MCP tools assigned but not actually invoked during execution
    """
    page = admin_page

    # =========================================================================
    # Step 1: Setup prerequisites
    # =========================================================================

    # test_mcp_server: Created via fixture (stdio transport, everything server)
    # test_agent: Created via fixture (E2E Test Agent)
    # Note: Agent's assigned_tools should include MCP tools
    # This may require API call to update agent if tools not assigned by default

    # For this test, we assume test_agent fixture has "echo" tool assigned
    # If not, test may need to assign tool via API first

    # =========================================================================
    # Step 2: Navigate to Agent Testing page
    # =========================================================================

    # Navigate to Agent Management page first
    page.goto(f"{streamlit_app_url}/Agent_Management")

    # Locate test agent
    agent_name = page.get_by_text("E2E Test Agent")
    expect(agent_name).to_be_visible(timeout=10000)

    # Click "Test" button for test agent
    test_button = page.get_by_role("button", name="Test", exact=False).first
    if test_button.count() == 0:
        # Fallback: Find by text
        test_button = page.get_by_text("Test", exact=False).first

    test_button.click()

    # Wait for agent testing/execution page to load
    expect(page.locator("text=Agent Testing").or_(page.locator("text=Test Agent"))).to_be_visible(
        timeout=5000
    )

    # =========================================================================
    # Step 3: Execute agent with input
    # =========================================================================

    # Locate input field for user message
    # May be text area or text input
    input_field = page.get_by_placeholder("Enter your message", exact=False).or_(
        page.get_by_label("Message", exact=False)
    )

    # Fill input with test message
    test_message = "Please echo this message: Hello from E2E test"
    input_field.fill(test_message)

    # Click "Execute" or "Run" button
    execute_button = page.get_by_role("button", name="Execute", exact=False).or_(
        page.get_by_role("button", name="Run", exact=False)
    )
    if execute_button.count() == 0:
        # Fallback: Find by text
        execute_button = page.get_by_text("Execute", exact=False).or_(
            page.get_by_text("Run", exact=False)
        )

    execute_button.click()

    # Wait for execution to start (loading indicator appears)
    loading_indicator = page.locator("text=Executing").or_(
        page.locator('[data-testid="stSpinner"]')
    )
    if loading_indicator.count() > 0:
        expect(loading_indicator).to_be_visible(timeout=5000)

    # =========================================================================
    # Step 4: Verify execution completes successfully
    # =========================================================================

    # Wait for execution to complete (loading indicator disappears)
    # Max wait: 30 seconds for agent execution
    if loading_indicator.count() > 0:
        expect(loading_indicator).not_to_be_visible(timeout=30000)

    # Verify success message or completion indicator appears
    completion_indicator = page.locator("text=Execution completed").or_(
        page.locator("text=Success")
    )
    expect(completion_indicator).to_be_visible(timeout=10000)

    # Verify execution results displayed
    # Agent response should contain echoed message: "Hello from E2E test"
    response_text = page.get_by_text("Hello from E2E test", exact=False)
    expect(response_text).to_be_visible(timeout=5000)

    # Verify execution metadata shown (duration, token usage, cost)
    # Flexible selectors for various metadata formats
    metadata_section = (
        page.locator("text=Duration")
        .or_(page.locator("text=Tokens"))
        .or_(page.locator("text=Cost"))
    )

    if metadata_section.count() > 0:
        expect(metadata_section.first).to_be_visible()

    # Verify no error messages displayed
    error_message = page.locator("text=Error").or_(page.locator("text=Failed"))
    expect(error_message).not_to_be_visible()

    # =========================================================================
    # Step 5: Verify execution history
    # =========================================================================

    # Navigate to Execution History page (Page 11)
    page.goto(f"{streamlit_app_url}/Execution_History")

    # Wait for page to load
    expect(page.locator("text=Execution History")).to_be_visible(timeout=5000)

    # Verify most recent execution appears in history table
    # Should show agent name: "E2E Test Agent"
    agent_name_in_history = page.get_by_text("E2E Test Agent")
    expect(agent_name_in_history).to_be_visible(timeout=10000)

    # Verify execution row contains status: "completed" or "success"
    status_indicator = page.get_by_text("completed", exact=False).or_(
        page.get_by_text("success", exact=False)
    )
    expect(status_indicator).to_be_visible()

    # Verify input preview contains test message
    input_preview = page.get_by_text("Hello from E2E test", exact=False)
    expect(input_preview).to_be_visible()

    # Click execution row to view details
    execution_row = page.get_by_text("E2E Test Agent").locator("..")
    if execution_row.count() > 0:
        execution_row.first.click()

    # Verify detail view shows full conversation
    # Should contain user message and agent response
    conversation_section = page.locator("text=Conversation").or_(page.locator("text=Messages"))
    expect(conversation_section).to_be_visible(timeout=5000)

    # Verify MCP tool invocation logged
    # Should mention "echo" tool was called
    tool_invocation_log = page.get_by_text("echo", exact=False)
    expect(tool_invocation_log).to_be_visible()

    # Verify execution cost tracked
    cost_display = page.locator("text=Cost").or_(page.locator("text=$"))
    expect(cost_display).to_be_visible()

    # =========================================================================
    # Cleanup
    # =========================================================================

    # Test data cleanup handled by fixtures (automatic rollback)
    # Execution records may need manual cleanup if persisted

    # Note: If execution records are not automatically cleaned up,
    # add API call here to delete test execution records
