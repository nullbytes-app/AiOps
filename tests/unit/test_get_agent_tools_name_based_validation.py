"""
Unit tests for AgentService.get_agent_tools() name-based validation (Story 11.2.7).

Bug Fix: Tests that MCP tools are validated by name (not ID) to handle server restarts.

When MCP servers restart, tool UUIDs change but names remain stable. The fix changed
validation from ID-based to name-based matching to prevent all tools being excluded
after server restart.

Test Coverage:
- Tools with matching names are included after server restart
- Tools with new IDs but same names pass validation
- Stale tools (removed from discovery) are still excluded
- Edge case: Missing tool names are handled gracefully
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select

from src.services.agent_service import AgentService


class TestGetAgentToolsNameBasedValidation:
    """Tests for get_agent_tools() with name-based MCP tool validation."""

    @pytest.mark.asyncio
    async def test_mcp_tools_validated_by_name_after_server_restart(self):
        """
        Test MCP tools are matched by name, not ID, after server restart.

        Scenario: MCP server restarts, tools get new UUIDs but same names.
        Expected: Tools still included in agent tools list (name-based match succeeds).

        This is the core fix for Bug #1 in Story 11.2.7.
        """
        service = AgentService()
        tenant_id = str(uuid4())
        agent_id = uuid4()

        # Simulate tool IDs BEFORE server restart
        old_tool_id_1 = str(uuid4())
        old_tool_id_2 = str(uuid4())

        # Simulate tool IDs AFTER server restart (new UUIDs!)
        new_tool_id_1 = str(uuid4())
        new_tool_id_2 = str(uuid4())

        # Mock agent with assigned MCP tools using OLD IDs (stored before restart)
        mock_agent = MagicMock()
        mock_agent.id = agent_id
        mock_agent.tenant_id = tenant_id
        mock_agent.status = "active"
        mock_agent.tools = []  # No OpenAPI tools
        mock_agent.assigned_mcp_tools = [
            {
                "id": old_tool_id_1,  # OLD UUID from before restart
                "name": "jira_create_issue",  # NAME stays the same
                "source_type": "mcp",
                "mcp_server_id": str(uuid4()),
                "mcp_server_name": "jira-server",
                "mcp_primitive_type": "tool",
            },
            {
                "id": old_tool_id_2,  # OLD UUID from before restart
                "name": "jira_add_comment",  # NAME stays the same
                "source_type": "mcp",
                "mcp_server_id": str(uuid4()),
                "mcp_server_name": "jira-server",
                "mcp_primitive_type": "tool",
            },
        ]

        # Mock current MCP tool discovery with NEW IDs (after restart)
        mock_unified_tool_1 = MagicMock()
        mock_unified_tool_1.id = UUID(new_tool_id_1)  # NEW UUID
        mock_unified_tool_1.name = "jira_create_issue"  # SAME name

        mock_unified_tool_2 = MagicMock()
        mock_unified_tool_2.id = UUID(new_tool_id_2)  # NEW UUID
        mock_unified_tool_2.name = "jira_add_comment"  # SAME name

        # Mock database session
        db_mock = AsyncMock()

        # Mock agent query
        agent_result_mock = MagicMock()
        agent_result_mock.scalar_one_or_none.return_value = mock_agent
        db_mock.execute.return_value = agent_result_mock

        # Mock UnifiedToolService.list_tools to return tools with NEW IDs
        with patch("src.services.unified_tool_service.UnifiedToolService") as mock_unified_service_class:
            mock_unified_service = AsyncMock()
            mock_unified_service.list_tools.return_value = [
                mock_unified_tool_1,
                mock_unified_tool_2,
            ]
            mock_unified_service_class.return_value = mock_unified_service

            # Call get_agent_tools
            result = await service.get_agent_tools(
                agent_id=agent_id,
                tenant_id=tenant_id,
                db=db_mock,
            )

        # Assert: Both tools included despite ID mismatch (name-based validation passed)
        assert len(result) == 2
        assert result[0]["name"] == "jira_create_issue"
        assert result[1]["name"] == "jira_add_comment"

        # Verify: Tools retain their original IDs from agent.assigned_mcp_tools
        # (we don't update IDs, just validate by name)
        assert result[0]["id"] == old_tool_id_1
        assert result[1]["id"] == old_tool_id_2

    @pytest.mark.asyncio
    async def test_stale_mcp_tools_excluded_by_name(self):
        """
        Test tools removed from server are still excluded (name not in discovery).

        Scenario: Tool was assigned but MCP server no longer provides it.
        Expected: Tool excluded from agent tools list.
        """
        service = AgentService()
        tenant_id = str(uuid4())
        agent_id = uuid4()

        # Mock agent with assigned tool that no longer exists
        mock_agent = MagicMock()
        mock_agent.id = agent_id
        mock_agent.tenant_id = tenant_id
        mock_agent.status = "active"
        mock_agent.tools = []
        mock_agent.assigned_mcp_tools = [
            {
                "id": str(uuid4()),
                "name": "deleted_tool",  # This tool was removed from server
                "source_type": "mcp",
                "mcp_server_id": str(uuid4()),
                "mcp_server_name": "test-server",
                "mcp_primitive_type": "tool",
            }
        ]

        # Mock current discovery with NO tools (server removed the tool)
        mock_unified_tool = MagicMock()
        mock_unified_tool.id = uuid4()
        mock_unified_tool.name = "other_tool"  # Different name

        # Mock database session
        db_mock = AsyncMock()
        agent_result_mock = MagicMock()
        agent_result_mock.scalar_one_or_none.return_value = mock_agent
        db_mock.execute.return_value = agent_result_mock

        # Mock UnifiedToolService
        with patch("src.services.unified_tool_service.UnifiedToolService") as mock_unified_service_class:
            mock_unified_service = AsyncMock()
            mock_unified_service.list_tools.return_value = [mock_unified_tool]
            mock_unified_service_class.return_value = mock_unified_service

            result = await service.get_agent_tools(
                agent_id=agent_id,
                tenant_id=tenant_id,
                db=db_mock,
            )

        # Assert: Stale tool excluded (name not in current discovery)
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_mcp_tools_missing_name_excluded(self):
        """
        Test tools with missing 'name' field are excluded gracefully.

        Scenario: Assigned tool has malformed data (missing name).
        Expected: Tool excluded without error.
        """
        service = AgentService()
        tenant_id = str(uuid4())
        agent_id = uuid4()

        # Mock agent with tool missing 'name' field
        mock_agent = MagicMock()
        mock_agent.id = agent_id
        mock_agent.tenant_id = tenant_id
        mock_agent.status = "active"
        mock_agent.tools = []
        mock_agent.assigned_mcp_tools = [
            {
                "id": str(uuid4()),
                # "name" field is missing!
                "source_type": "mcp",
                "mcp_server_id": str(uuid4()),
                "mcp_server_name": "test-server",
                "mcp_primitive_type": "tool",
            }
        ]

        # Mock database session
        db_mock = AsyncMock()
        agent_result_mock = MagicMock()
        agent_result_mock.scalar_one_or_none.return_value = mock_agent
        db_mock.execute.return_value = agent_result_mock

        # Mock UnifiedToolService
        with patch("src.services.unified_tool_service.UnifiedToolService") as mock_unified_service_class:
            mock_unified_service = AsyncMock()
            mock_unified_service.list_tools.return_value = []
            mock_unified_service_class.return_value = mock_unified_service

            # Should not raise error
            result = await service.get_agent_tools(
                agent_id=agent_id,
                tenant_id=tenant_id,
                db=db_mock,
            )

        # Assert: Malformed tool excluded gracefully
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_mixed_openapi_and_mcp_tools_both_included(self):
        """
        Test both OpenAPI and MCP tools are returned together.

        Scenario: Agent has both OpenAPI and MCP tools assigned.
        Expected: Unified list contains both types.
        """
        service = AgentService()
        tenant_id = str(uuid4())
        agent_id = uuid4()

        # Mock agent with BOTH OpenAPI and MCP tools
        mock_openapi_tool = MagicMock()
        mock_openapi_tool.tool_id = "openapi_tool_1"

        mock_agent = MagicMock()
        mock_agent.id = agent_id
        mock_agent.tenant_id = tenant_id
        mock_agent.status = "active"
        mock_agent.tools = [mock_openapi_tool]  # OpenAPI tool
        mock_agent.assigned_mcp_tools = [
            {
                "id": str(uuid4()),
                "name": "mcp_tool_1",
                "source_type": "mcp",
                "mcp_server_id": str(uuid4()),
                "mcp_server_name": "test-server",
                "mcp_primitive_type": "tool",
            }
        ]

        # Mock current MCP discovery
        mock_unified_tool = MagicMock()
        mock_unified_tool.id = uuid4()
        mock_unified_tool.name = "mcp_tool_1"

        # Mock database session
        db_mock = AsyncMock()
        agent_result_mock = MagicMock()
        agent_result_mock.scalar_one_or_none.return_value = mock_agent
        db_mock.execute.return_value = agent_result_mock

        # Mock UnifiedToolService
        with patch("src.services.unified_tool_service.UnifiedToolService") as mock_unified_service_class:
            mock_unified_service = AsyncMock()
            mock_unified_service.list_tools.return_value = [mock_unified_tool]
            mock_unified_service_class.return_value = mock_unified_service

            result = await service.get_agent_tools(
                agent_id=agent_id,
                tenant_id=tenant_id,
                db=db_mock,
            )

        # Assert: Both OpenAPI and MCP tools included
        assert len(result) == 2

        # OpenAPI tool
        assert result[0]["source_type"] == "openapi"
        assert result[0]["name"] == "openapi_tool_1"

        # MCP tool
        assert result[1]["source_type"] == "mcp"
        assert result[1]["name"] == "mcp_tool_1"
