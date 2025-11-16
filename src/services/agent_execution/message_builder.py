"""
Message Construction for Agent Execution

Builds LangChain message lists with system prompt + user message.
Performs variable substitution in system prompts using context dictionaries.

Pattern: Simple utility function with clear single responsibility.
No state management, pure functional approach.

References:
- LangChain Message types (SystemMessage, HumanMessage)
- Story 12.7: File Size Refactoring (extracted from agent_execution_service.py)

Usage:
    messages = build_messages(
        system_prompt="You are a {role} assistant",
        user_message="Help me with...",
        context={"role": "technical support"}
    )
    # Returns: [SystemMessage(...), HumanMessage(...)]
"""

import logging
from typing import Any, Dict, List, Optional

from langchain_core.messages import HumanMessage, SystemMessage

logger = logging.getLogger(__name__)


def build_messages(
    system_prompt: str,
    user_message: str,
    context: Optional[Dict[str, Any]] = None,
) -> List[Any]:
    """
    Build LangChain messages list with system prompt + user message.

    Performs variable substitution in system_prompt using context dict.
    If substitution fails due to missing keys, logs warning and uses
    original prompt without substitution (graceful degradation).

    Args:
        system_prompt: Agent's system prompt (may contain {variables})
        user_message: User's input message
        context: Optional context dict for variable substitution

    Returns:
        List of LangChain Message objects [SystemMessage, HumanMessage]

    Example:
        >>> messages = build_messages(
        >>>     system_prompt="You are {role} assistant for {company}",
        >>>     user_message="Help me debug this code",
        >>>     context={"role": "technical support", "company": "ACME Corp"}
        >>> )
        >>> # SystemMessage: "You are technical support assistant for ACME Corp"
        >>> # HumanMessage: "Help me debug this code"
    """
    # Perform variable substitution in system prompt
    if context:
        try:
            formatted_prompt = system_prompt.format(**context)
        except KeyError as e:
            logger.warning(
                f"Missing context variable in system prompt: {e}",
                extra={"missing_key": str(e)},
            )
            # Graceful degradation: use original prompt
            formatted_prompt = system_prompt
    else:
        formatted_prompt = system_prompt

    # Build messages list
    messages = [
        SystemMessage(content=formatted_prompt),
        HumanMessage(content=user_message),
    ]

    return messages
