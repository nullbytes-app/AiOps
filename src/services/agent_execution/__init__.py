"""
Agent Execution Submodule

Modular components for agent execution workflow:
- mcp_bridge_pooler: MCP bridge connection pooling and lifecycle management
- tool_converter: Tool conversion from unified format to LangChain tools
- message_builder: Message construction with variable substitution
- result_extractor: Result parsing from LangGraph execution output

This module was refactored from agent_execution_service.py in Story 12.7
to comply with 2025 Python best practices (150-500 line file size sweet spot).

References:
- Story 12.7: File Size Refactoring and Code Quality
- Context7 MCP: Ruff + Black best practices (Trust 9.4/7.3)
- WebSearch: "Right-Sizing Python Files for AI Code Editors" (Medium, Sep 2025)
"""

from .mcp_bridge_pooler import (
    cleanup_mcp_bridge,
    get_or_create_mcp_bridge,
    get_pool_size,
)
from .message_builder import build_messages
from .result_extractor import extract_response, extract_tool_calls
from .tool_converter import convert_tools_to_langchain

__all__ = [
    # MCP Bridge Pooling
    "get_or_create_mcp_bridge",
    "cleanup_mcp_bridge",
    "get_pool_size",
    # Tool Conversion
    "convert_tools_to_langchain",
    # Message Building
    "build_messages",
    # Result Extraction
    "extract_response",
    "extract_tool_calls",
]
