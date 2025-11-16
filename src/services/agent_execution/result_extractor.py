"""
Result Extraction for Agent Execution

Parses LangGraph execution results to extract final response and tool call history.
Handles LangGraph's message-based result structure.

Pattern: Two pure extraction functions with clear separation of concerns.
- extract_response: Parse final AI response from message list
- extract_tool_calls: Parse tool invocation history from message list

References:
- LangGraph message structure (AIMessage, ToolMessage)
- Story 11.1.7: MCP Tool Invocation in Agent Execution
- Story 12.7: File Size Refactoring (extracted from agent_execution_service.py)

Usage:
    result = await agent_executor.ainvoke({"messages": messages})
    response = extract_response(result)
    tool_calls = extract_tool_calls(result)
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


def extract_response(result: Dict[str, Any]) -> str:
    """
    Extract final response from LangGraph execution result.

    LangGraph returns dict with "messages" key containing conversation history.
    Final AI response is in last message's content field.

    Args:
        result: LangGraph agent execution result dict

    Returns:
        str: Final agent response text (empty string if not found)

    Example result structure:
    {
        "messages": [
            SystemMessage(...),
            HumanMessage(...),
            AIMessage(content="I'll help you...", tool_calls=[...]),
            ToolMessage(...),
            AIMessage(content="Based on the results...")  # <- Extract this
        ]
    }

    Example:
        >>> result = {"messages": [..., AIMessage(content="Done!")]}
        >>> response = extract_response(result)
        >>> print(response)  # "Done!"
    """
    # DEBUG: Print to stdout (will show in docker logs)
    print(f"\n{'='*80}")
    print(f"EXTRACT_RESPONSE DEBUG")
    print(f"Result keys: {result.keys()}")
    print(f"{'='*80}\n")

    messages = result.get("messages", [])

    print(f"Found {len(messages)} messages in result")

    if not messages:
        print("WARNING: No messages in execution result!")
        logger.warning("No messages in execution result")
        return ""

    # DEBUG: Print all message types
    for i, msg in enumerate(messages):
        content_preview = getattr(msg, 'content', 'N/A')
        if content_preview != 'N/A' and len(str(content_preview)) > 200:
            content_preview = str(content_preview)[:200] + "..."
        print(f"Message {i}: type={type(msg).__name__}, content={content_preview}")

    # Get last message (should be AIMessage with final response)
    last_message = messages[-1]

    print(f"\nLast message type: {type(last_message).__name__}")
    print(f"Last message has content attr: {hasattr(last_message, 'content')}")

    # Extract content from message
    if hasattr(last_message, "content"):
        content = str(last_message.content)
        print(f"Extracted content length: {len(content)} chars")
        print(f"Content preview: {content[:500]}")
        print(f"{'='*80}\n")
        return content
    else:
        print(f"ERROR: Last message has no content attribute!")
        logger.warning(f"Last message has no content attribute: {type(last_message)}")
        print(f"{'='*80}\n")
        return str(last_message)


def extract_tool_calls(result: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract tool call history from LangGraph execution result.

    Parses messages list to find all AIMessages with tool_calls and
    corresponding ToolMessages with results. Matches tool calls with
    their results sequentially (assumes synchronous execution).

    Args:
        result: LangGraph agent execution result dict

    Returns:
        List of tool call dicts:
        [
            {
                "tool_name": str,
                "tool_input": dict,
                "tool_output": str,
                "timestamp": str (ISO 8601)
            },
            ...
        ]

    Example:
        >>> result = {
        >>>     "messages": [
        >>>         AIMessage(tool_calls=[{"name": "search", "args": {...}}]),
        >>>         ToolMessage(content="Results: ..."),
        >>>         AIMessage(content="Based on search...")
        >>>     ]
        >>> }
        >>> calls = extract_tool_calls(result)
        >>> print(calls)
        >>> # [{"tool_name": "search", "tool_input": {...}, "tool_output": "Results: ..."}]
    """
    messages = result.get("messages", [])
    tool_calls: List[Dict[str, Any]] = []

    for message in messages:
        # Check if message has tool_calls attribute (AIMessage with function calls)
        if hasattr(message, "tool_calls") and message.tool_calls:
            for tool_call in message.tool_calls:
                tool_calls.append(
                    {
                        "tool_name": tool_call.get("name", "unknown"),
                        "tool_input": tool_call.get("args", {}),
                        "tool_output": "",  # Will be filled from ToolMessage
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                )

        # Check if message is ToolMessage (contains tool execution result)
        if hasattr(message, "__class__") and message.__class__.__name__ == "ToolMessage":
            # Match with last tool call (assumes sequential execution)
            if tool_calls:
                tool_calls[-1]["tool_output"] = str(message.content)

    logger.debug(f"Extracted {len(tool_calls)} tool calls from execution result")

    return tool_calls
