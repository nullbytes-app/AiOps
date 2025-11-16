"""
Unit tests for MCP stdio Transport Client.

Tests MCPStdioClient class with mocked subprocess operations.
Target coverage: ≥95%
"""

import asyncio
import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from uuid import uuid4

import pytest

from src.schemas.mcp_server import MCPServerResponse
from src.services.mcp_stdio_client import (
    InitializationError,
    InvalidJSONError,
    MCPError,
    MCPStdioClient,
    ProcessError,
    TimeoutError,
    ToolExecutionError,
)


# Test Fixtures


@pytest.fixture
def valid_stdio_config():
    """Valid stdio MCP server configuration."""
    return MCPServerResponse(
        id=uuid4(),
        tenant_id=uuid4(),
        name="test-server",
        transport_type="stdio",
        command="python",
        args=["-m", "mcp_server"],
        env={"API_KEY": "test-key"},
        discovered_tools=[],
        discovered_resources=[],
        discovered_prompts=[],
        status="active",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def mock_process():
    """Mock asyncio.subprocess.Process."""
    process = AsyncMock(spec=asyncio.subprocess.Process)
    process.pid = 12345
    process.returncode = None

    # Mock stdin/stdout/stderr as AsyncMock with StreamWriter/StreamReader-like behavior
    process.stdin = AsyncMock()
    process.stdin.write = Mock()
    process.stdin.drain = AsyncMock()
    process.stdin.close = Mock()

    process.stdout = AsyncMock()
    process.stdout.readline = AsyncMock()
    process.stdout.close = Mock()

    process.stderr = AsyncMock()
    process.stderr.readline = AsyncMock(return_value=b"")  # No stderr by default
    process.stderr.close = Mock()

    process.terminate = Mock()
    process.kill = Mock()
    process.wait = AsyncMock()

    return process


# Test Client Initialization


@pytest.mark.asyncio
async def test_client_initialization_valid_config(valid_stdio_config):
    """Test MCPStdioClient initialization with valid stdio config."""
    client = MCPStdioClient(valid_stdio_config)

    assert client.command == "python"
    assert client.args == ["-m", "mcp_server"]
    assert client.env == {"API_KEY": "test-key"}
    assert client.process is None
    assert client._closed is False


def test_client_initialization_non_stdio_transport():
    """Test initialization rejects non-stdio transport."""
    config = MCPServerResponse(
        id=uuid4(),
        tenant_id=uuid4(),
        name="test-server",
        transport_type="http_sse",  # Wrong transport type
        command=None,
        status="active",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    with pytest.raises(ValueError, match="Expected stdio transport"):
        MCPStdioClient(config)


def test_client_initialization_missing_command():
    """Test initialization rejects missing command."""
    config = MCPServerResponse(
        id=uuid4(),
        tenant_id=uuid4(),
        name="test-server",
        transport_type="stdio",
        command=None,  # Missing command
        status="active",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    with pytest.raises(ValueError, match="Command is required"):
        MCPStdioClient(config)


# Test JSON-RPC Message Handling


def test_create_request_basic(valid_stdio_config):
    """Test JSON-RPC request construction."""
    client = MCPStdioClient(valid_stdio_config)

    request = client._create_request("tools/list")

    assert request["jsonrpc"] == "2.0"
    assert request["id"] == 1
    assert request["method"] == "tools/list"
    assert "params" not in request


def test_create_request_with_params(valid_stdio_config):
    """Test JSON-RPC request construction with parameters."""
    client = MCPStdioClient(valid_stdio_config)

    params = {"name": "test_tool", "arguments": {"arg1": "value1"}}
    request = client._create_request("tools/call", params)

    assert request["jsonrpc"] == "2.0"
    assert request["id"] == 1
    assert request["method"] == "tools/call"
    assert request["params"] == params


def test_next_id_increments(valid_stdio_config):
    """Test request ID increments correctly."""
    client = MCPStdioClient(valid_stdio_config)

    assert client._next_id() == 1
    assert client._next_id() == 2
    assert client._next_id() == 3


@pytest.mark.asyncio
async def test_send_request_success(valid_stdio_config, mock_process):
    """Test sending JSON-RPC request via stdin."""
    client = MCPStdioClient(valid_stdio_config)
    client.process = mock_process

    request = {"jsonrpc": "2.0", "id": 1, "method": "initialize"}
    await client._send_request(request)

    # Verify write was called with JSON + newline
    expected_message = json.dumps(request) + "\n"
    mock_process.stdin.write.assert_called_once_with(expected_message.encode("utf-8"))
    mock_process.stdin.drain.assert_awaited_once()


@pytest.mark.asyncio
async def test_send_request_no_process(valid_stdio_config):
    """Test send_request raises error when process is not available."""
    client = MCPStdioClient(valid_stdio_config)

    request = {"jsonrpc": "2.0", "id": 1, "method": "initialize"}

    with pytest.raises(ProcessError, match="Process stdin is not available"):
        await client._send_request(request)


@pytest.mark.asyncio
async def test_read_response_success(valid_stdio_config, mock_process):
    """Test reading JSON-RPC response from stdout."""
    client = MCPStdioClient(valid_stdio_config)
    client.process = mock_process

    response_data = {"jsonrpc": "2.0", "id": 1, "result": {"tools": []}}
    mock_process.stdout.readline.return_value = (json.dumps(response_data) + "\n").encode("utf-8")

    response = await client._read_response()

    assert response == response_data


@pytest.mark.asyncio
async def test_read_response_malformed_json(valid_stdio_config, mock_process):
    """Test read_response handles malformed JSON."""
    client = MCPStdioClient(valid_stdio_config)
    client.process = mock_process

    mock_process.stdout.readline.return_value = b"not valid json\n"

    with pytest.raises(InvalidJSONError, match="Failed to parse JSON-RPC response"):
        await client._read_response()


@pytest.mark.asyncio
async def test_read_response_invalid_jsonrpc_version(valid_stdio_config, mock_process):
    """Test read_response validates JSON-RPC version."""
    client = MCPStdioClient(valid_stdio_config)
    client.process = mock_process

    response_data = {"jsonrpc": "1.0", "id": 1, "result": {}}  # Wrong version
    mock_process.stdout.readline.return_value = (json.dumps(response_data) + "\n").encode("utf-8")

    with pytest.raises(InvalidJSONError, match="Invalid JSON-RPC version"):
        await client._read_response()


@pytest.mark.asyncio
async def test_read_response_eof(valid_stdio_config, mock_process):
    """Test read_response handles EOF (stdout closed)."""
    client = MCPStdioClient(valid_stdio_config)
    client.process = mock_process

    mock_process.stdout.readline.return_value = b""  # EOF

    with pytest.raises(EOFError, match="MCP server closed stdout unexpectedly"):
        await client._read_response()


# Test Subprocess Management


@pytest.mark.asyncio
async def test_context_manager_spawns_subprocess(valid_stdio_config):
    """Test async context manager spawns subprocess."""
    with patch("asyncio.create_subprocess_exec") as mock_create:
        mock_process = AsyncMock()
        mock_process.pid = 12345
        mock_process.returncode = None
        mock_process.stdin = AsyncMock()
        mock_process.stdout = AsyncMock()
        mock_process.stderr = AsyncMock()
        mock_process.stderr.readline = AsyncMock(return_value=b"")
        mock_create.return_value = mock_process

        async with MCPStdioClient(valid_stdio_config) as client:
            assert client.process is not None
            assert client.process.pid == 12345

        # Verify subprocess was created with correct arguments
        mock_create.assert_called_once_with(
            "python",
            "-m",
            "mcp_server",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=unittest.mock.ANY,  # Contains merged env
        )


@pytest.mark.asyncio
async def test_context_manager_cleanup_on_exit(valid_stdio_config, mock_process):
    """Test async context manager calls close on exit."""
    with patch("asyncio.create_subprocess_exec", return_value=mock_process):
        async with MCPStdioClient(valid_stdio_config) as client:
            pass

        # Verify cleanup was called
        mock_process.terminate.assert_called_once()
        mock_process.wait.assert_awaited()


@pytest.mark.asyncio
async def test_close_graceful_shutdown(valid_stdio_config, mock_process):
    """Test close() performs graceful shutdown (SIGTERM → wait)."""
    client = MCPStdioClient(valid_stdio_config)
    client.process = mock_process
    client._stderr_task = AsyncMock()

    await client.close()

    # Verify SIGTERM was sent
    mock_process.terminate.assert_called_once()

    # Verify waited for process exit
    mock_process.wait.assert_awaited()

    # Verify pipes closed
    mock_process.stdin.close.assert_called_once()
    mock_process.stdout.close.assert_called_once()
    mock_process.stderr.close.assert_called_once()

    assert client._closed is True


@pytest.mark.asyncio
async def test_close_force_kill_on_timeout(valid_stdio_config, mock_process):
    """Test close() sends SIGKILL if graceful shutdown times out."""
    client = MCPStdioClient(valid_stdio_config)
    client.process = mock_process
    client._stderr_task = AsyncMock()

    # Simulate timeout on wait
    mock_process.wait.side_effect = [asyncio.TimeoutError(), None]

    await client.close()

    # Verify SIGTERM was sent first
    mock_process.terminate.assert_called_once()

    # Verify SIGKILL was sent after timeout
    mock_process.kill.assert_called_once()


@pytest.mark.asyncio
async def test_close_already_terminated(valid_stdio_config, mock_process):
    """Test close() handles already terminated process."""
    client = MCPStdioClient(valid_stdio_config)
    client.process = mock_process
    client.process.returncode = 0  # Already exited
    client._stderr_task = AsyncMock()

    await client.close()

    # Should not send signals
    mock_process.terminate.assert_not_called()
    mock_process.kill.assert_not_called()


# Test MCP Initialize Handshake


@pytest.mark.asyncio
async def test_initialize_success(valid_stdio_config, mock_process):
    """Test initialize handshake with successful response."""
    with patch("asyncio.create_subprocess_exec", return_value=mock_process):
        async with MCPStdioClient(valid_stdio_config) as client:
            # Mock successful initialize response
            init_response = {
                "jsonrpc": "2.0",
                "id": 1,
                "result": {
                    "protocolVersion": "2025-03-26",
                    "capabilities": {"tools": {}, "resources": {}, "prompts": {}},
                    "serverInfo": {"name": "test-server", "version": "1.0.0"},
                },
            }

            # Mock _send_and_wait to return successful result
            with patch.object(client, "_send_and_wait", return_value=init_response["result"]):
                capabilities = await client.initialize()

            assert client.server_capabilities == init_response["result"]["capabilities"]
            assert capabilities == init_response["result"]["capabilities"]


@pytest.mark.asyncio
async def test_initialize_incompatible_version(valid_stdio_config, mock_process):
    """Test initialize rejects incompatible protocol version."""
    with patch("asyncio.create_subprocess_exec", return_value=mock_process):
        async with MCPStdioClient(valid_stdio_config) as client:
            # Mock response with incompatible version
            init_response = {
                "protocolVersion": "1.0.0",  # Wrong version
                "capabilities": {},
                "serverInfo": {"name": "test-server", "version": "1.0.0"},
            }

            with patch.object(client, "_send_and_wait", return_value=init_response):
                with pytest.raises(InitializationError, match="Incompatible protocol version"):
                    await client.initialize()


@pytest.mark.asyncio
async def test_initialize_closed_client(valid_stdio_config):
    """Test initialize raises error when client is closed."""
    client = MCPStdioClient(valid_stdio_config)
    client._closed = True

    with pytest.raises(MCPError, match="Client is closed"):
        await client.initialize()


# Test List Methods


@pytest.mark.asyncio
async def test_list_tools_with_multiple_tools(valid_stdio_config, mock_process):
    """Test list_tools returns multiple tools."""
    with patch("asyncio.create_subprocess_exec", return_value=mock_process):
        async with MCPStdioClient(valid_stdio_config) as client:
            tools_response = {
                "tools": [
                    {
                        "name": "read_file",
                        "description": "Read a file",
                        "inputSchema": {"type": "object", "properties": {"path": {"type": "string"}}},
                    },
                    {"name": "write_file", "description": "Write to a file", "inputSchema": {"type": "object"}},
                ]
            }

            with patch.object(client, "_send_and_wait", return_value=tools_response):
                tools = await client.list_tools()

            assert len(tools) == 2
            assert tools[0]["name"] == "read_file"
            assert tools[1]["name"] == "write_file"


@pytest.mark.asyncio
async def test_list_tools_empty(valid_stdio_config, mock_process):
    """Test list_tools handles empty tools gracefully."""
    with patch("asyncio.create_subprocess_exec", return_value=mock_process):
        async with MCPStdioClient(valid_stdio_config) as client:
            tools_response = {"tools": []}

            with patch.object(client, "_send_and_wait", return_value=tools_response):
                tools = await client.list_tools()

            assert tools == []


@pytest.mark.asyncio
async def test_list_resources_success(valid_stdio_config, mock_process):
    """Test list_resources returns resources."""
    with patch("asyncio.create_subprocess_exec", return_value=mock_process):
        async with MCPStdioClient(valid_stdio_config) as client:
            resources_response = {
                "resources": [
                    {
                        "uri": "file:///config.json",
                        "name": "Config",
                        "description": "App config",
                        "mimeType": "application/json",
                    }
                ]
            }

            with patch.object(client, "_send_and_wait", return_value=resources_response):
                resources = await client.list_resources()

            assert len(resources) == 1
            assert resources[0]["uri"] == "file:///config.json"


@pytest.mark.asyncio
async def test_list_prompts_success(valid_stdio_config, mock_process):
    """Test list_prompts returns prompts."""
    with patch("asyncio.create_subprocess_exec", return_value=mock_process):
        async with MCPStdioClient(valid_stdio_config) as client:
            prompts_response = {
                "prompts": [
                    {
                        "name": "review_code",
                        "description": "Review code",
                        "arguments": [{"name": "language", "description": "Language", "required": True}],
                    }
                ]
            }

            with patch.object(client, "_send_and_wait", return_value=prompts_response):
                prompts = await client.list_prompts()

            assert len(prompts) == 1
            assert prompts[0]["name"] == "review_code"


# Test Execution Methods


@pytest.mark.asyncio
async def test_call_tool_success(valid_stdio_config, mock_process):
    """Test call_tool with successful execution."""
    with patch("asyncio.create_subprocess_exec", return_value=mock_process):
        async with MCPStdioClient(valid_stdio_config) as client:
            tool_response = {
                "content": [{"type": "text", "text": "File contents here"}],
                "isError": False,
            }

            with patch.object(client, "_send_and_wait", return_value=tool_response):
                result = await client.call_tool("read_file", {"path": "/etc/hosts"})

            assert result["content"] == tool_response["content"]
            assert result["is_error"] is False


@pytest.mark.asyncio
async def test_call_tool_with_error(valid_stdio_config, mock_process):
    """Test call_tool raises ToolExecutionError when isError is true."""
    with patch("asyncio.create_subprocess_exec", return_value=mock_process):
        async with MCPStdioClient(valid_stdio_config) as client:
            tool_response = {
                "content": [{"type": "text", "text": "Error: File not found"}],
                "isError": True,
            }

            with patch.object(client, "_send_and_wait", return_value=tool_response):
                with pytest.raises(ToolExecutionError, match="Tool 'read_file' execution failed"):
                    await client.call_tool("read_file", {"path": "/nonexistent"})


@pytest.mark.asyncio
async def test_read_resource_success(valid_stdio_config, mock_process):
    """Test read_resource returns contents."""
    with patch("asyncio.create_subprocess_exec", return_value=mock_process):
        async with MCPStdioClient(valid_stdio_config) as client:
            resource_response = {
                "contents": [{"uri": "file:///config.json", "mimeType": "application/json", "text": '{"key": "value"}'}]
            }

            with patch.object(client, "_send_and_wait", return_value=resource_response):
                result = await client.read_resource("file:///config.json")

            assert result["contents"] == resource_response["contents"]


@pytest.mark.asyncio
async def test_get_prompt_success(valid_stdio_config, mock_process):
    """Test get_prompt returns messages."""
    with patch("asyncio.create_subprocess_exec", return_value=mock_process):
        async with MCPStdioClient(valid_stdio_config) as client:
            prompt_response = {
                "messages": [{"role": "user", "content": {"type": "text", "text": "Review this Python code..."}}]
            }

            with patch.object(client, "_send_and_wait", return_value=prompt_response):
                result = await client.get_prompt("review_code", {"language": "python"})

            assert result["messages"] == prompt_response["messages"]


@pytest.mark.asyncio
async def test_get_prompt_without_arguments(valid_stdio_config, mock_process):
    """Test get_prompt with no arguments."""
    with patch("asyncio.create_subprocess_exec", return_value=mock_process):
        async with MCPStdioClient(valid_stdio_config) as client:
            prompt_response = {"messages": [{"role": "user", "content": {"type": "text", "text": "Default prompt"}}]}

            with patch.object(client, "_send_and_wait", return_value=prompt_response):
                result = await client.get_prompt("default_prompt")

            assert result["messages"] == prompt_response["messages"]


# Test Error Handling


@pytest.mark.asyncio
async def test_timeout_handling(valid_stdio_config, mock_process):
    """Test timeout raises TimeoutError."""
    with patch("asyncio.create_subprocess_exec", return_value=mock_process):
        async with MCPStdioClient(valid_stdio_config) as client:
            # Mock slow response (timeout)
            with patch.object(client, "_send_and_wait") as mock_send:
                mock_send.side_effect = TimeoutError("No response received for method 'tools/list' within 30.0s")

                with pytest.raises(TimeoutError, match="No response received"):
                    await client.list_tools()


@pytest.mark.asyncio
async def test_operations_after_close(valid_stdio_config, mock_process):
    """Test operations raise error after client is closed."""
    with patch("asyncio.create_subprocess_exec", return_value=mock_process):
        client = MCPStdioClient(valid_stdio_config)
        async with client:
            pass

        # After context exit, client is closed
        with pytest.raises(MCPError, match="Client is closed"):
            await client.list_tools()


# ============================================================================
# Test Additional Error Paths (Story 11.2.6 - Coverage >90%)
# ============================================================================


@pytest.mark.asyncio
async def test_read_response_process_stdout_not_available(valid_stdio_config):
    """Test _read_response raises ProcessError when process stdout is None."""
    client = MCPStdioClient(valid_stdio_config)
    client.process = AsyncMock()
    client.process.stdout = None  # Simulate stdout not available

    with pytest.raises(ProcessError, match="Process stdout is not available"):
        await client._read_response()


@pytest.mark.asyncio
async def test_context_manager_subprocess_spawn_failure(valid_stdio_config):
    """Test __aenter__ raises ProcessError on subprocess spawn failure."""
    with patch("asyncio.create_subprocess_exec", side_effect=OSError("Command not found")):
        client = MCPStdioClient(valid_stdio_config)

        with pytest.raises(ProcessError, match="Failed to spawn subprocess"):
            async with client:
                pass


@pytest.mark.asyncio
async def test_initialize_exception_handling(valid_stdio_config, mock_process):
    """Test initialize wraps exceptions in InitializationError."""
    with patch("asyncio.create_subprocess_exec", return_value=mock_process):
        async with MCPStdioClient(valid_stdio_config) as client:
            # Mock _send_and_wait to raise generic exception
            with patch.object(client, "_send_and_wait", side_effect=ValueError("Invalid response")):
                with pytest.raises(InitializationError, match="Initialize handshake failed"):
                    await client.initialize()


@pytest.mark.asyncio
async def test_list_resources_closed_client(valid_stdio_config, mock_process):
    """Test list_resources raises error when client is closed."""
    with patch("asyncio.create_subprocess_exec", return_value=mock_process):
        client = MCPStdioClient(valid_stdio_config)
        async with client:
            pass  # Close client

        with pytest.raises(MCPError, match="Client is closed"):
            await client.list_resources()


@pytest.mark.asyncio
async def test_list_prompts_closed_client(valid_stdio_config, mock_process):
    """Test list_prompts raises error when client is closed."""
    with patch("asyncio.create_subprocess_exec", return_value=mock_process):
        client = MCPStdioClient(valid_stdio_config)
        async with client:
            pass  # Close client

        with pytest.raises(MCPError, match="Client is closed"):
            await client.list_prompts()


@pytest.mark.asyncio
async def test_call_tool_closed_client(valid_stdio_config, mock_process):
    """Test call_tool raises error when client is closed."""
    with patch("asyncio.create_subprocess_exec", return_value=mock_process):
        client = MCPStdioClient(valid_stdio_config)
        async with client:
            pass  # Close client

        with pytest.raises(MCPError, match="Client is closed"):
            await client.call_tool("test_tool", {})


@pytest.mark.asyncio
async def test_read_resource_closed_client(valid_stdio_config, mock_process):
    """Test read_resource raises error when client is closed."""
    with patch("asyncio.create_subprocess_exec", return_value=mock_process):
        client = MCPStdioClient(valid_stdio_config)
        async with client:
            pass  # Close client

        with pytest.raises(MCPError, match="Client is closed"):
            await client.read_resource("file:///test.txt")


@pytest.mark.asyncio
async def test_get_prompt_closed_client(valid_stdio_config, mock_process):
    """Test get_prompt raises error when client is closed."""
    with patch("asyncio.create_subprocess_exec", return_value=mock_process):
        client = MCPStdioClient(valid_stdio_config)
        async with client:
            pass  # Close client

        with pytest.raises(MCPError, match="Client is closed"):
            await client.get_prompt("test_prompt")


@pytest.mark.asyncio
async def test_close_when_already_closed(valid_stdio_config, mock_process):
    """Test close() returns early when already closed (line 344)."""
    with patch("asyncio.create_subprocess_exec", return_value=mock_process):
        client = MCPStdioClient(valid_stdio_config)
        async with client:
            pass  # Close client

        # Call close again - should return early without error
        await client.close()
        assert client._closed is True


@pytest.mark.asyncio
async def test_monitor_stderr_logs_output(valid_stdio_config):
    """Test _monitor_stderr() logs stderr output from MCP server."""
    # Create mock process with stderr output
    mock_process = AsyncMock()
    mock_stderr = AsyncMock()
    mock_stderr.readline = AsyncMock(side_effect=[
        b"Warning: test message\n",
        b"Error: another message\n",
        b""  # EOF
    ])
    mock_process.stderr = mock_stderr
    mock_process.stdin = AsyncMock()
    mock_process.stdout = AsyncMock()
    mock_process.pid = 12345

    with patch("asyncio.create_subprocess_exec", return_value=mock_process):
        async with MCPStdioClient(valid_stdio_config) as client:
            # Wait a moment for stderr monitoring task to process messages
            await asyncio.sleep(0.1)

        # Verify stderr was read (3 calls: 2 messages + EOF)
        assert mock_stderr.readline.call_count == 3


@pytest.mark.asyncio
async def test_monitor_stderr_handles_no_stderr(valid_stdio_config):
    """Test _monitor_stderr() handles case when process.stderr is None."""
    # Create mock process without stderr
    mock_process = AsyncMock()
    mock_process.stderr = None
    mock_process.stdin = AsyncMock()
    mock_process.stdout = AsyncMock()
    mock_process.pid = 12345

    with patch("asyncio.create_subprocess_exec", return_value=mock_process):
        async with MCPStdioClient(valid_stdio_config) as client:
            # Should not raise error even without stderr
            await asyncio.sleep(0.05)


@pytest.mark.asyncio
async def test_send_and_wait_with_real_request_response(valid_stdio_config):
    """Test _send_and_wait() sends request and waits for matching response."""
    # Create mock process that returns a valid JSON-RPC response
    mock_process = AsyncMock()
    mock_stdin = AsyncMock()
    mock_stdout = AsyncMock()

    # Mock stdout to return a valid initialize response
    response_data = {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {
            "protocolVersion": "2025-03-26",
            "serverInfo": {"name": "test-server", "version": "1.0.0"}
        }
    }
    mock_stdout.readline = AsyncMock(return_value=(json.dumps(response_data) + "\n").encode())

    mock_process.stdin = mock_stdin
    mock_process.stdout = mock_stdout
    mock_process.stderr = None
    mock_process.pid = 12345

    with patch("asyncio.create_subprocess_exec", return_value=mock_process):
        client = MCPStdioClient(valid_stdio_config)
        async with client:
            # Call _send_and_wait directly
            result = await client._send_and_wait("initialize", {"protocolVersion": "2025-03-26"})

            # Verify result
            assert result["protocolVersion"] == "2025-03-26"
            assert result["serverInfo"]["name"] == "test-server"


@pytest.mark.asyncio
async def test_send_and_wait_timeout_error(valid_stdio_config):
    """Test _send_and_wait() raises TimeoutError when no response received."""
    # Create mock process that never responds
    mock_process = AsyncMock()
    mock_stdin = AsyncMock()
    mock_stdout = AsyncMock()

    # Mock stdout to never return data (simulates timeout)
    async def never_return():
        await asyncio.sleep(100)  # Sleep longer than timeout
        return b""

    mock_stdout.readline = never_return

    mock_process.stdin = mock_stdin
    mock_process.stdout = mock_stdout
    mock_process.stderr = None
    mock_process.pid = 12345

    with patch("asyncio.create_subprocess_exec", return_value=mock_process):
        client = MCPStdioClient(valid_stdio_config)
        async with client:
            # Call _send_and_wait with short timeout
            with pytest.raises(TimeoutError, match="No response received for method"):
                await client._send_and_wait("tools/list", {}, timeout=0.1)


@pytest.mark.asyncio
async def test_read_responses_dispatches_to_pending_request(valid_stdio_config):
    """Test _read_responses() matches responses to pending requests."""
    # This is tested indirectly through _send_and_wait test above
    # The _read_responses background task is created in _send_and_wait (line 245)
    # and processes the response to resolve the future

    mock_process = AsyncMock()
    mock_stdin = AsyncMock()
    mock_stdout = AsyncMock()

    response_data = {"jsonrpc": "2.0", "id": 1, "result": {"tools": []}}
    mock_stdout.readline = AsyncMock(return_value=(json.dumps(response_data) + "\n").encode())

    mock_process.stdin = mock_stdin
    mock_process.stdout = mock_stdout
    mock_process.stderr = None
    mock_process.pid = 12345

    with patch("asyncio.create_subprocess_exec", return_value=mock_process):
        client = MCPStdioClient(valid_stdio_config)
        async with client:
            # This internally uses _read_responses to dispatch the response
            result = await client._send_and_wait("tools/list", {})
            assert "tools" in result


import unittest.mock
