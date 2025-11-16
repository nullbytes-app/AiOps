"""
Pytest fixtures for integration tests.

Provides common fixtures like Redis mocks for integration testing.

Note: Old provider-related fixtures have been removed as part of Story 9.2
(Provider Management API refactor). LLMProvider and LLMModel models no longer exist.

MCP Test Server Setup (Story 11.2.6):
- Uses @modelcontextprotocol/server-everything for integration tests
- Provides fixtures for stdio and HTTP+SSE transport testing
"""

import asyncio
import os
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture
async def redis_client():
    """
    Provide mocked Redis client for integration tests.

    Returns:
        MagicMock: Async Redis client mock with standard methods

    Methods mocked:
        - get: Returns None (cache miss)
        - set: Returns True
        - delete: Returns 1 (success)
        - exists: Returns False
    """
    mock_redis = MagicMock()
    mock_redis.get = AsyncMock(return_value=None)
    mock_redis.set = AsyncMock(return_value=True)
    mock_redis.delete = AsyncMock(return_value=1)
    mock_redis.exists = AsyncMock(return_value=False)
    return mock_redis



# ==============================================================================
# MCP Test Server Fixtures (Story 11.2.6)
# ==============================================================================

@pytest.fixture(scope="session")
def mcp_test_server_command():
    """
    Get the command to run @modelcontextprotocol/server-everything.
    
    Returns:
        tuple: (command, args) for spawning MCP test server
    """
    # Use npx to run the test server
    project_root = Path(__file__).parent.parent.parent
    
    return (
        "npx",
        [
            "-y",  # Auto-install if not present
            "@modelcontextprotocol/server-everything",
        ],
    )


@pytest.fixture
def mcp_stdio_test_server_config(mcp_test_server_command):
    """
    Configuration for stdio MCP test server.
    
    Uses @modelcontextprotocol/server-everything which provides:
    - Tools: echo, add, longRunningOperation, sampleLLM, getTinyImage
    - Resources: test://static/resource, test://dynamic/{id}
    - Prompts: simple_prompt, complex_prompt
    
    Returns:
        MCPServerResponse: Config object for MCPStdioClient
    """
    from src.schemas.mcp_server import MCPServerResponse
    
    command, args = mcp_test_server_command
    
    return MCPServerResponse(
        id=uuid4(),
        tenant_id=uuid4(),
        name="test-mcp-stdio-server",
        description="MCP test server for integration testing (stdio)",
        transport_type="stdio",
        command=command,
        args=args,
        env={"LOG_LEVEL": "error"},  # Reduce noise in tests
        url=None,
        headers={},
        status="active",
        consecutive_failures=0,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


@pytest.fixture
async def mcp_stdio_client(mcp_stdio_test_server_config):
    """
    Provide initialized MCP stdio client for testing.
    
    Yields:
        MCPStdioClient: Initialized client with test server
    
    Usage:
        async def test_tool_invocation(mcp_stdio_client):
            tools = await mcp_stdio_client.list_tools()
            assert len(tools) > 0
    """
    from src.services.mcp_stdio_client import MCPStdioClient
    
    async with MCPStdioClient(mcp_stdio_test_server_config) as client:
        await client.initialize()
        yield client


@pytest.fixture
def skip_if_no_mcp_server():
    """
    Skip test if MCP test server (npx) is not available.
    
    Usage:
        @pytest.mark.usefixtures("skip_if_no_mcp_server")
        async def test_with_mcp(mcp_stdio_client):
            ...
    """
    import shutil
    
    if not shutil.which("npx"):
        pytest.skip("npx not available - cannot run MCP test server")



@pytest.fixture
def mock_db_session():
    """
    Mock database session for integration tests that need DB mocking.
    
    Returns:
        AsyncMock: Mocked async database session
    """
    session = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.refresh = AsyncMock()
    session.execute = AsyncMock()
    session.add = MagicMock()  # Synchronous
    return session
