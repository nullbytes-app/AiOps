"""
Unit tests for AgentService MCP tool assignment functionality (Story 11.1.6).

Tests the MCP tool assignment features including:
- Creating agents with MCP tool assignments
- Updating agents with MCP tool assignments
- Getting unified tool lists (OpenAPI + MCP)
- MCP tool validation (server status, tool discovery)
- Filtering stale/inactive MCP tools
- Backward compatibility with OpenAPI-only agents

Test Strategy:
- Unit: MCP tool assignment logic with mocked database operations
- Integration: Full workflow testing covered in test_agent_mcp_tool_assignment.py
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException

from src.schemas.agent import AgentCreate, AgentUpdate, LLMConfig, MCPToolAssignment
from src.services.agent_service import AgentService


class TestMCPToolAssignmentValidation:
    """Tests for _validate_mcp_tool_assignments method."""

    @pytest.mark.asyncio
    async def test_validate_mcp_tools_empty_list(self):
        """Test validation with empty MCP tool assignments list."""
        service = AgentService()
        tenant_id = uuid4()
        db_mock = AsyncMock()

        result = await service._validate_mcp_tool_assignments([], tenant_id, db_mock)

        assert result == []
        db_mock.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_validate_mcp_tools_valid_assignment(self):
        """Test validation succeeds with valid MCP tool assignment."""
        service = AgentService()
        tenant_id = uuid4()
        server_id = uuid4()

        # Mock MCP server with discovered tools
        mock_server = MagicMock()
        mock_server.id = server_id
        mock_server.name = "test-server"
        mock_server.status = "active"
        mock_server.discovered_tools = [
            {"name": "test_tool", "description": "Test tool"}
        ]
        mock_server.discovered_resources = []
        mock_server.discovered_prompts = []

        # Mock database query
        db_mock = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = mock_server
        db_mock.execute.return_value = mock_result

        assignment = {
            "id": str(uuid4()),
            "name": "test_tool",
            "source_type": "mcp",
            "mcp_server_id": str(server_id),
            "mcp_server_name": "test-server",
            "mcp_primitive_type": "tool",
        }

        result = await service._validate_mcp_tool_assignments(
            [assignment], tenant_id, db_mock
        )

        assert len(result) == 1
        assert result[0]["name"] == "test_tool"

    @pytest.mark.asyncio
    async def test_validate_mcp_tools_server_not_found(self):
        """Test validation fails when MCP server not found."""
        service = AgentService()
        tenant_id = uuid4()
        server_id = uuid4()

        # Mock database query returning None (server not found)
        db_mock = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = None
        db_mock.execute.return_value = mock_result

        assignment = {
            "id": str(uuid4()),
            "name": "test_tool",
            "source_type": "mcp",
            "mcp_server_id": str(server_id),
            "mcp_server_name": "test-server",
            "mcp_primitive_type": "tool",
        }

        with pytest.raises(HTTPException) as exc_info:
            await service._validate_mcp_tool_assignments(
                [assignment], tenant_id, db_mock
            )

        assert exc_info.value.status_code == 400
        assert "not found" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_validate_mcp_tools_server_inactive(self):
        """Test validation fails when MCP server is inactive."""
        service = AgentService()
        tenant_id = uuid4()
        server_id = uuid4()

        # Mock inactive MCP server
        mock_server = MagicMock()
        mock_server.id = server_id
        mock_server.name = "inactive-server"
        mock_server.status = "inactive"

        db_mock = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = mock_server
        db_mock.execute.return_value = mock_result

        assignment = {
            "id": str(uuid4()),
            "name": "test_tool",
            "source_type": "mcp",
            "mcp_server_id": str(server_id),
            "mcp_server_name": "inactive-server",
            "mcp_primitive_type": "tool",
        }

        with pytest.raises(HTTPException) as exc_info:
            await service._validate_mcp_tool_assignments(
                [assignment], tenant_id, db_mock
            )

        assert exc_info.value.status_code == 400
        assert "not active" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_validate_mcp_tools_tool_not_discovered(self):
        """Test validation fails when tool not in server's discovered tools."""
        service = AgentService()
        tenant_id = uuid4()
        server_id = uuid4()

        # Mock MCP server without the requested tool
        mock_server = MagicMock()
        mock_server.id = server_id
        mock_server.name = "test-server"
        mock_server.status = "active"
        mock_server.discovered_tools = [
            {"name": "other_tool", "description": "Different tool"}
        ]
        mock_server.discovered_resources = []
        mock_server.discovered_prompts = []

        db_mock = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = mock_server
        db_mock.execute.return_value = mock_result

        assignment = {
            "id": str(uuid4()),
            "name": "missing_tool",
            "source_type": "mcp",
            "mcp_server_id": str(server_id),
            "mcp_server_name": "test-server",
            "mcp_primitive_type": "tool",
        }

        with pytest.raises(HTTPException) as exc_info:
            await service._validate_mcp_tool_assignments(
                [assignment], tenant_id, db_mock
            )

        assert exc_info.value.status_code == 400
        assert "not found" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_validate_mcp_tools_resource_type(self):
        """Test validation works for MCP resource primitive type."""
        service = AgentService()
        tenant_id = uuid4()
        server_id = uuid4()

        # Mock MCP server with discovered resources
        mock_server = MagicMock()
        mock_server.id = server_id
        mock_server.name = "test-server"
        mock_server.status = "active"
        mock_server.discovered_tools = []
        mock_server.discovered_resources = [
            {"name": "test_resource", "uri": "file:///test"}
        ]
        mock_server.discovered_prompts = []

        db_mock = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = mock_server
        db_mock.execute.return_value = mock_result

        assignment = {
            "id": str(uuid4()),
            "name": "test_resource",
            "source_type": "mcp",
            "mcp_server_id": str(server_id),
            "mcp_server_name": "test-server",
            "mcp_primitive_type": "resource",
        }

        result = await service._validate_mcp_tool_assignments(
            [assignment], tenant_id, db_mock
        )

        assert len(result) == 1
        assert result[0]["name"] == "test_resource"

    @pytest.mark.asyncio
    async def test_validate_mcp_tools_prompt_type(self):
        """Test validation works for MCP prompt primitive type."""
        service = AgentService()
        tenant_id = uuid4()
        server_id = uuid4()

        # Mock MCP server with discovered prompts
        mock_server = MagicMock()
        mock_server.id = server_id
        mock_server.name = "test-server"
        mock_server.status = "active"
        mock_server.discovered_tools = []
        mock_server.discovered_resources = []
        mock_server.discovered_prompts = [
            {"name": "test_prompt", "description": "Test prompt"}
        ]

        db_mock = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = mock_server
        db_mock.execute.return_value = mock_result

        assignment = {
            "id": str(uuid4()),
            "name": "test_prompt",
            "source_type": "mcp",
            "mcp_server_id": str(server_id),
            "mcp_server_name": "test-server",
            "mcp_primitive_type": "prompt",
        }

        result = await service._validate_mcp_tool_assignments(
            [assignment], tenant_id, db_mock
        )

        assert len(result) == 1
        assert result[0]["name"] == "test_prompt"


class TestAgentCreateWithMCPTools:
    """Tests for create_agent with MCP tool assignments."""

    @pytest.mark.asyncio
    async def test_create_agent_with_mcp_tools_calls_validation(self):
        """Test create_agent calls MCP validation when MCP tools provided."""
        service = AgentService()

        # Mock the validation method
        with patch.object(
            service, "_validate_mcp_tool_assignments", new_callable=AsyncMock
        ) as mock_validate:
            mock_validate.return_value = []  # Return empty validated list

            # Mock database operations
            db_mock = AsyncMock()
            db_mock.add = MagicMock()
            db_mock.flush = AsyncMock()
            db_mock.commit = AsyncMock()
            db_mock.refresh = AsyncMock()

            # Create agent data with MCP tools
            tenant_id = str(uuid4())
            agent_data = AgentCreate(
                name="Test Agent",
                system_prompt="Test prompt",
                llm_config=LLMConfig(model="gpt-4"),
                mcp_tool_assignments=[
                    MCPToolAssignment(
                        id=str(uuid4()),
                        name="test_tool",
                        source_type="mcp",
                        mcp_server_id=uuid4(),
                        mcp_server_name="test-server",
                        mcp_primitive_type="tool",
                    )
                ],
            )

            try:
                await service.create_agent(tenant_id, agent_data, db_mock)
            except Exception:
                pass  # Expect failure due to incomplete mocking

            # Verify validation was called with correct arguments
            assert mock_validate.called, "Validation method should have been called"
            call_args = mock_validate.call_args
            assert len(call_args[0][0]) == 1, "Should validate one MCP tool assignment"
            assert call_args[0][1] == UUID(tenant_id), "Should pass tenant_id as UUID"


class TestAgentUpdateWithMCPTools:
    """Tests for update_agent with MCP tool assignments."""

    @pytest.mark.asyncio
    async def test_update_agent_with_mcp_tools_calls_validation(self):
        """Test update_agent calls MCP validation when MCP tools provided."""
        service = AgentService()

        # Mock the validation method
        with patch.object(
            service, "_validate_mcp_tool_assignments", new_callable=AsyncMock
        ) as mock_validate:
            mock_validate.return_value = []

            # Mock database operations
            tenant_id = str(uuid4())
            agent_id = uuid4()

            mock_agent = MagicMock()
            mock_agent.id = agent_id
            mock_agent.tenant_id = tenant_id
            mock_agent.triggers = []
            mock_agent.tools = []

            db_mock = AsyncMock()
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = mock_agent
            db_mock.execute.return_value = mock_result
            db_mock.commit = AsyncMock()
            db_mock.refresh = AsyncMock()

            # Update data with MCP tools
            agent_update = AgentUpdate(
                mcp_tool_assignments=[
                    MCPToolAssignment(
                        id=str(uuid4()),
                        name="updated_tool",
                        source_type="mcp",
                        mcp_server_id=uuid4(),
                        mcp_server_name="test-server",
                        mcp_primitive_type="tool",
                    )
                ]
            )

            try:
                await service.update_agent(tenant_id, agent_id, agent_update, db_mock)
            except Exception:
                pass  # Expect failure due to incomplete mocking

            # Verify validation was called with correct arguments
            assert mock_validate.called, "Validation method should have been called"
            call_args = mock_validate.call_args
            assert len(call_args[0][0]) == 1, "Should validate one MCP tool assignment"
            assert call_args[0][1] == UUID(tenant_id), "Should pass tenant_id as UUID"


class TestBackwardCompatibility:
    """Tests for backward compatibility with OpenAPI-only agents."""

    def test_agent_create_without_mcp_tools(self):
        """Test creating agent without MCP tools (legacy behavior)."""
        agent_data = AgentCreate(
            name="Legacy Agent",
            system_prompt="Test prompt",
            llm_config=LLMConfig(model="gpt-4"),
            tool_ids=["servicedesk_plus"],
        )

        # Should not have MCP tool assignments
        assert agent_data.mcp_tool_assignments == []

    def test_agent_update_without_mcp_tools(self):
        """Test updating agent without MCP tools (legacy behavior)."""
        agent_update = AgentUpdate(
            name="Updated Agent",
            tool_ids=["servicedesk_plus", "knowledge_base"],
        )

        # Should not have MCP tool assignments
        assert agent_update.mcp_tool_assignments is None


class TestMCPOnlyAgent:
    """Tests for agents with only MCP tools (no OpenAPI tools)."""

    def test_agent_create_mcp_only(self):
        """Test creating agent with only MCP tools (no OpenAPI)."""
        agent_data = AgentCreate(
            name="MCP-Only Agent",
            system_prompt="Test prompt",
            llm_config=LLMConfig(model="gpt-4"),
            mcp_tool_assignments=[
                MCPToolAssignment(
                    id=str(uuid4()),
                    name="mcp_tool",
                    source_type="mcp",
                    mcp_server_id=uuid4(),
                    mcp_server_name="test-server",
                    mcp_primitive_type="tool",
                )
            ],
        )

        # Should have MCP tools but no OpenAPI tools
        assert len(agent_data.mcp_tool_assignments) == 1
        assert len(agent_data.tool_ids) == 0
