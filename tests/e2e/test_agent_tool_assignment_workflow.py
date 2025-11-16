"""
E2E Test: Workflow 2 - Agent Tool Assignment with MCP Tools.

This test validates agent tool assignment with MCP tool discovery UI integration,
specifically preventing the Story 11.2.5 regression (render functions exist but
not called).

Test Journey:
1. Setup prerequisites (MCP server, agent via API)
2. Navigate to Agent Management page
3. Open tool assignment tab
4. Assign MCP tool to agent
5. Verify tool assignment persisted

Acceptance Criteria: AC3
"""

import pytest
from playwright.sync_api import Page, expect

from src.database.models import Agent, MCPServer, TenantConfig  # type: ignore[attr-defined]


@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.skip(
    reason="E2E test requires live Streamlit server on localhost:8502. Run manually during E2E testing phase. Issue tracked in Story 12.4"
)
def test_agent_tool_assignment_workflow(
    admin_page: Page,
    streamlit_app_url: str,
    test_tenant: TenantConfig,
    test_mcp_server: MCPServer,
    test_agent: Agent,
) -> None:
    """
    Test agent tool assignment with MCP tool discovery UI.

    This E2E test validates:
    - Navigation to Agent Management works
    - Agent edit form opens correctly
    - Tools tab is accessible
    - MCP Tools section APPEARS (Story 11.2.5 regression test)
    - MCP tools are RENDERED (Story 11.2.5 regression test)
    - Tool assignment checkbox works
    - Assignment persists after save

    Prevents: Story 11.2.5 style bugs (render_mcp_tool_discovery_ui exists but not called)
    """
    page = admin_page

    # =========================================================================
    # Step 1: Setup prerequisites (handled by fixtures)
    # =========================================================================

    # test_mcp_server: Created via fixture (stdio transport, everything server)
    # test_agent: Created via fixture (E2E Test Agent)
    # Note: Tool discovery may need to be triggered separately if not auto-run

    # =========================================================================
    # Step 2: Navigate to Agent Management page
    # =========================================================================

    # Navigate to Agent Management (Page 5)
    page.goto(f"{streamlit_app_url}/Agent_Management")

    # Verify page title contains "Agent Management"
    expect(page.locator("h1, h2, h3")).to_contain_text("Agent")

    # =========================================================================
    # Step 3: Open tool assignment tab
    # =========================================================================

    # Locate test agent in agents table/list
    # Agent name: "E2E Test Agent"
    agent_name = page.get_by_text("E2E Test Agent")
    expect(agent_name).to_be_visible(timeout=10000)

    # Click "Edit" button for test agent
    # Button may be in same row or nearby
    edit_button = page.get_by_role("button", name="Edit", exact=False).first
    if edit_button.count() == 0:
        # Fallback: Find by text
        edit_button = page.get_by_text("Edit", exact=False).first

    edit_button.click()

    # Wait for agent edit form to appear
    expect(
        page.locator("text=Agent Configuration").or_(page.locator("text=Edit Agent"))
    ).to_be_visible(timeout=5000)

    # Click "Tools" tab in agent edit form
    # Use accessibility-based selector (role=tab)
    tools_tab = page.get_by_role("tab", name="Tools", exact=False)
    if tools_tab.count() == 0:
        # Fallback: Find by text
        tools_tab = page.get_by_text("Tools", exact=False)

    tools_tab.click()

    # Verify "Tools" tab is active/selected
    expect(tools_tab).to_be_visible()

    # =========================================================================
    # Step 4: Assign MCP tool to agent
    # =========================================================================

    # CRITICAL: Verify "MCP Tools" section appears
    # This is the Story 11.2.5 regression test
    # If render_mcp_tool_discovery_ui() is not called, this will FAIL
    mcp_tools_section = page.locator("text=MCP Tools").or_(page.locator("text=Available MCP Tools"))
    expect(mcp_tools_section).to_be_visible(timeout=5000)

    # CRITICAL: Verify MCP tools are RENDERED (not just section header)
    # Story 11.2.5 bug: Functions exist but never called
    # Look for MCP tool names (e.g., "echo" tool from everything server)
    mcp_tool_list = page.locator('[data-testid="mcp-tools-list"]').or_(
        page.locator(".mcp-tools-section")
    )

    # Flexible check: Either specific tool names or any tool checkboxes
    echo_tool = page.get_by_text("echo", exact=False)
    tool_checkbox = (
        page.locator('input[type="checkbox"]')
        .filter(has_text="echo")
        .or_(page.locator('input[type="checkbox"]').first)
    )

    # Verify at least one MCP tool appears
    if echo_tool.count() > 0:
        expect(echo_tool).to_be_visible()
        # Click checkbox to select "echo" MCP tool
        nearby_checkbox = echo_tool.locator("..").locator('input[type="checkbox"]').first
        if nearby_checkbox.count() > 0:
            nearby_checkbox.check()
    elif tool_checkbox.count() > 0:
        # Fallback: Check first available tool checkbox
        tool_checkbox.first.check()
    else:
        # If no MCP tools found, test should FAIL (regression detected)
        pytest.fail("MCP tools not rendered - Story 11.2.5 regression detected!")

    # Verify checkbox shows checked state
    checked_checkbox = page.locator('input[type="checkbox"]:checked')
    expect(checked_checkbox).to_have_count(1, timeout=3000)  # At least 1 checkbox should be checked

    # Click "Save" button
    save_button = page.get_by_role("button", name="Save", exact=False)
    if save_button.count() == 0:
        # Fallback: Find by text
        save_button = page.get_by_text("Save", exact=False)

    save_button.click()

    # =========================================================================
    # Step 5: Verify tool assignment persisted
    # =========================================================================

    # Wait for success message
    success_message = page.locator("text=updated successfully").or_(
        page.locator("text=Agent updated")
    )
    expect(success_message).to_be_visible(timeout=10000)

    # Refresh page or navigate away and back
    page.reload()

    # Wait for page to load
    expect(page.locator("text=Agent Management")).to_be_visible(timeout=5000)

    # Click "Edit" for test agent again
    page.get_by_text("E2E Test Agent").click()
    edit_button_again = page.get_by_role("button", name="Edit", exact=False).first
    if edit_button_again.count() > 0:
        edit_button_again.click()

    # Click "Tools" tab again
    tools_tab_again = page.get_by_role("tab", name="Tools", exact=False)
    if tools_tab_again.count() > 0:
        tools_tab_again.click()

    # Verify tool checkbox is still checked (assignment persisted)
    persisted_checkbox = page.locator('input[type="checkbox"]:checked')
    expect(persisted_checkbox).to_have_count(1, timeout=5000)  # Checkbox should still be checked

    # =========================================================================
    # Cleanup
    # =========================================================================

    # Test data cleanup handled by fixtures (automatic rollback)
    # No manual cleanup needed
