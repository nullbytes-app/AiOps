"""
Integration tests for MCP primitives (Story 11.2.6 - AC#2 Workflow 2).

Tests all three MCP primitives comprehensively:
1. Tools - Discovery, schema validation, invocation
2. Resources - Discovery, schema validation, reading
3. Prompts - Discovery, schema validation, getting

Uses real @modelcontextprotocol/server-everything for testing.
"""

import pytest
from typing import Any


@pytest.mark.integration
@pytest.mark.usefixtures("skip_if_no_mcp_server")
@pytest.mark.asyncio
async def test_tools_list_returns_valid_schema(mcp_stdio_client):
    """
    Test tools/list returns valid OpenAPI-style schema.

    Validates:
    - Each tool has required fields: name, inputSchema
    - inputSchema is valid JSON Schema
    - Optional fields (description) are strings if present
    """
    tools = await mcp_stdio_client.list_tools()

    assert isinstance(tools, list)
    assert len(tools) > 0

    for tool in tools:
        # Required fields
        assert "name" in tool
        assert isinstance(tool["name"], str)
        assert len(tool["name"]) > 0

        assert "inputSchema" in tool
        assert isinstance(tool["inputSchema"], dict)

        # Input schema structure
        schema = tool["inputSchema"]
        assert schema.get("type") == "object"

        # Optional description
        if "description" in tool:
            assert isinstance(tool["description"], str)


@pytest.mark.integration
@pytest.mark.usefixtures("skip_if_no_mcp_server")
@pytest.mark.asyncio
async def test_tools_invocation_with_string_argument(mcp_stdio_client):
    """
    Test tool invocation with string argument (echo tool).

    Validates:
    - Tool accepts string argument
    - Result contains input string
    - Result format is correct (content array, is_error flag)
    """
    test_message = "Test string argument 123"
    result = await mcp_stdio_client.call_tool("echo", {"message": test_message})

    # Validate result structure
    assert "content" in result
    assert "is_error" in result
    assert isinstance(result["content"], list)
    assert result["is_error"] is False

    # Validate content
    content_str = str(result["content"])
    assert test_message in content_str


@pytest.mark.integration
@pytest.mark.usefixtures("skip_if_no_mcp_server")
@pytest.mark.asyncio
async def test_tools_invocation_with_numeric_arguments(mcp_stdio_client):
    """
    Test tool invocation with numeric arguments (add tool).

    Validates:
    - Tool accepts multiple numeric arguments
    - Computation is correct
    - Result format is correct
    """
    result = await mcp_stdio_client.call_tool("add", {"a": 42, "b": 58})

    assert result["is_error"] is False
    assert "content" in result

    # Validate computation (42 + 58 = 100)
    content_str = str(result["content"])
    assert "100" in content_str


@pytest.mark.integration
@pytest.mark.usefixtures("skip_if_no_mcp_server")
@pytest.mark.asyncio
async def test_tools_invocation_with_negative_numbers(mcp_stdio_client):
    """
    Test tool invocation with negative numbers.

    Validates:
    - Tool handles negative numbers correctly
    - Computation is correct
    """
    result = await mcp_stdio_client.call_tool("add", {"a": -10, "b": 5})

    assert result["is_error"] is False

    # Validate computation (-10 + 5 = -5)
    content_str = str(result["content"])
    assert "-5" in content_str


@pytest.mark.integration
@pytest.mark.usefixtures("skip_if_no_mcp_server")
@pytest.mark.asyncio
async def test_tools_invocation_with_floats(mcp_stdio_client):
    """
    Test tool invocation with floating point numbers.

    Validates:
    - Tool handles floating point numbers
    - Computation is correct
    """
    result = await mcp_stdio_client.call_tool("add", {"a": 3.14, "b": 2.86})

    assert result["is_error"] is False

    # Validate computation (3.14 + 2.86 = 6.0)
    content_str = str(result["content"])
    assert "6" in content_str


@pytest.mark.integration
@pytest.mark.usefixtures("skip_if_no_mcp_server")
@pytest.mark.asyncio
async def test_tools_result_content_types(mcp_stdio_client):
    """
    Test that tool results have proper content types.

    Validates:
    - Content is a list of content blocks
    - Each content block has expected structure
    """
    result = await mcp_stdio_client.call_tool("echo", {"message": "content test"})

    assert isinstance(result["content"], list)
    assert len(result["content"]) > 0

    # Validate at least one content block exists
    content_block = result["content"][0]
    assert isinstance(content_block, dict)


@pytest.mark.integration
@pytest.mark.usefixtures("skip_if_no_mcp_server")
@pytest.mark.asyncio
async def test_tools_available_in_test_server(mcp_stdio_client):
    """
    Test that expected tools are available from test server.

    Validates:
    - Test server provides expected tools
    - Tool names match specification
    """
    tools = await mcp_stdio_client.list_tools()
    tool_names = {tool["name"] for tool in tools}

    # Verify expected tools from @modelcontextprotocol/server-everything
    expected_tools = {"echo", "add"}
    assert expected_tools.issubset(tool_names), \
        f"Expected tools {expected_tools} not found. Available: {tool_names}"


@pytest.mark.integration
@pytest.mark.usefixtures("skip_if_no_mcp_server")
@pytest.mark.asyncio
async def test_resources_list_returns_valid_schema(mcp_stdio_client):
    """
    Test resources/list returns valid schema.

    Validates:
    - Result is a list
    - Each resource has required fields: uri, name
    - Optional fields have correct types
    """
    resources = await mcp_stdio_client.list_resources()

    assert isinstance(resources, list)

    # If resources are available, validate their schema
    for resource in resources:
        # Required fields
        assert "uri" in resource
        assert isinstance(resource["uri"], str)
        assert len(resource["uri"]) > 0

        assert "name" in resource
        assert isinstance(resource["name"], str)

        # Optional fields
        if "description" in resource:
            assert isinstance(resource["description"], str)

        if "mimeType" in resource:
            assert isinstance(resource["mimeType"], str)


@pytest.mark.integration
@pytest.mark.usefixtures("skip_if_no_mcp_server")
@pytest.mark.asyncio
async def test_resources_read_if_available(mcp_stdio_client):
    """
    Test reading a resource if any are available.

    Validates:
    - resources/read returns valid content structure
    - Content is a list of content blocks

    Note: Skips if no resources are available from test server.
    """
    resources = await mcp_stdio_client.list_resources()

    if len(resources) == 0:
        pytest.skip("No resources available from test server")

    # Read first available resource
    resource_uri = resources[0]["uri"]
    result = await mcp_stdio_client.read_resource(resource_uri)

    # Validate result structure
    assert "contents" in result
    assert isinstance(result["contents"], list)


@pytest.mark.integration
@pytest.mark.usefixtures("skip_if_no_mcp_server")
@pytest.mark.asyncio
async def test_prompts_list_returns_valid_schema(mcp_stdio_client):
    """
    Test prompts/list returns valid schema.

    Validates:
    - Result is a list
    - Each prompt has required fields: name
    - Optional fields have correct types
    """
    prompts = await mcp_stdio_client.list_prompts()

    assert isinstance(prompts, list)

    # If prompts are available, validate their schema
    for prompt in prompts:
        # Required fields
        assert "name" in prompt
        assert isinstance(prompt["name"], str)
        assert len(prompt["name"]) > 0

        # Optional fields
        if "description" in prompt:
            assert isinstance(prompt["description"], str)

        if "arguments" in prompt:
            assert isinstance(prompt["arguments"], list)


@pytest.mark.integration
@pytest.mark.usefixtures("skip_if_no_mcp_server")
@pytest.mark.asyncio
async def test_prompts_get_if_available(mcp_stdio_client):
    """
    Test getting a prompt if any are available.

    Validates:
    - prompts/get returns valid message structure
    - Messages is a list

    Note: Skips if no prompts are available from test server.
    """
    prompts = await mcp_stdio_client.list_prompts()

    if len(prompts) == 0:
        pytest.skip("No prompts available from test server")

    # Get first available prompt
    prompt_name = prompts[0]["name"]
    result = await mcp_stdio_client.get_prompt(prompt_name)

    # Validate result structure
    assert "messages" in result
    assert isinstance(result["messages"], list)


@pytest.mark.integration
@pytest.mark.usefixtures("skip_if_no_mcp_server")
@pytest.mark.asyncio
async def test_prompts_get_with_arguments_if_available(mcp_stdio_client):
    """
    Test getting a prompt with arguments if supported.

    Validates:
    - Prompts accept arguments
    - Result contains messages

    Note: Skips if no prompts with arguments are available.
    """
    prompts = await mcp_stdio_client.list_prompts()

    # Find a prompt that accepts arguments
    prompt_with_args = None
    for prompt in prompts:
        if "arguments" in prompt and len(prompt["arguments"]) > 0:
            prompt_with_args = prompt
            break

    if prompt_with_args is None:
        pytest.skip("No prompts with arguments available from test server")

    # Get prompt with dummy arguments
    prompt_name = prompt_with_args["name"]
    result = await mcp_stdio_client.get_prompt(prompt_name, {"arg1": "test"})

    # Validate result structure
    assert "messages" in result
    assert isinstance(result["messages"], list)


@pytest.mark.integration
@pytest.mark.usefixtures("skip_if_no_mcp_server")
@pytest.mark.asyncio
async def test_all_primitives_available_simultaneously(mcp_stdio_client):
    """
    Test that all three primitives can be accessed in sequence.

    Validates:
    - Tools, resources, and prompts can be listed sequentially
    - No interference between primitive types
    - Client remains stable across all operations
    """
    # List tools
    tools = await mcp_stdio_client.list_tools()
    assert isinstance(tools, list)

    # List resources
    resources = await mcp_stdio_client.list_resources()
    assert isinstance(resources, list)

    # List prompts
    prompts = await mcp_stdio_client.list_prompts()
    assert isinstance(prompts, list)

    # Verify no cross-contamination
    # (e.g., tools list doesn't contain resource data)
    if len(tools) > 0:
        assert "uri" not in tools[0]  # URI is resource-specific
        assert "name" in tools[0]  # But name is present in tools


@pytest.mark.integration
@pytest.mark.usefixtures("skip_if_no_mcp_server")
@pytest.mark.asyncio
async def test_tools_invocation_preserves_state(mcp_stdio_client):
    """
    Test that multiple tool invocations don't interfere with each other.

    Validates:
    - Each tool call is independent
    - No state leakage between calls
    - Results are correctly isolated
    """
    # First call
    result1 = await mcp_stdio_client.call_tool("echo", {"message": "first"})
    assert "first" in str(result1["content"])

    # Second call with different argument
    result2 = await mcp_stdio_client.call_tool("echo", {"message": "second"})
    assert "second" in str(result2["content"])

    # Verify no cross-contamination
    assert "second" not in str(result1["content"])
    assert "first" not in str(result2["content"])


@pytest.mark.integration
@pytest.mark.usefixtures("skip_if_no_mcp_server")
@pytest.mark.asyncio
async def test_primitives_listing_is_idempotent(mcp_stdio_client):
    """
    Test that listing primitives multiple times returns consistent results.

    Validates:
    - Multiple list_tools() calls return same tools
    - Multiple list_resources() calls return same resources
    - Multiple list_prompts() calls return same prompts
    """
    # List tools twice
    tools1 = await mcp_stdio_client.list_tools()
    tools2 = await mcp_stdio_client.list_tools()

    # Should return same number of tools
    assert len(tools1) == len(tools2)

    # Should return same tool names
    tool_names1 = {tool["name"] for tool in tools1}
    tool_names2 = {tool["name"] for tool in tools2}
    assert tool_names1 == tool_names2

    # List resources twice
    resources1 = await mcp_stdio_client.list_resources()
    resources2 = await mcp_stdio_client.list_resources()
    assert len(resources1) == len(resources2)

    # List prompts twice
    prompts1 = await mcp_stdio_client.list_prompts()
    prompts2 = await mcp_stdio_client.list_prompts()
    assert len(prompts1) == len(prompts2)
