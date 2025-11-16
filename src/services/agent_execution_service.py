"""
Agent Execution Service with LangGraph Integration

Orchestrates agent execution workflow with MCP tool support, combining:
- LangGraph's create_react_agent for ReAct pattern execution
- LiteLLM virtual keys for tenant-isolated LLM calls
- MCP Tool Bridge for dynamic MCP primitive invocation
- MCP Bridge pooling for connection reuse (Story 11.2.3)
- Graceful error handling with structured responses

Implements:
- Multi-tenant agent execution with budget enforcement
- OpenAPI + MCP tool binding to LLM
- System prompt + user message construction
- Result extraction from LangGraph state
- MCP bridge connection pooling per execution context
- Error recovery with detailed diagnostics

Refactoring Note (Story 12.7):
This module was refactored to comply with 2025 Python best practices
(150-500 line sweet spot for AI code editors). Extracted modules:
- agent_execution.mcp_bridge_pooler: Connection pooling lifecycle
- agent_execution.tool_converter: Tool format conversion
- agent_execution.message_builder: Message construction
- agent_execution.result_extractor: Result parsing

References:
- Story 11.1.7: MCP Tool Invocation in Agent Execution
- Story 11.2.3: MCP Connection Pooling and Caching
- Story 12.7: File Size Refactoring and Code Quality
- LangGraph 0.6+ create_react_agent pattern
- langchain-mcp-adapters for MCP primitive conversion
"""

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import UUID

from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import MCPServer
from src.exceptions import BudgetExceededError
from src.services.agent_execution.mcp_bridge_pooler import cleanup_mcp_bridge
from src.services.agent_execution.message_builder import build_messages
from src.services.agent_execution.result_extractor import extract_response, extract_tool_calls
from src.services.agent_execution.tool_converter import convert_tools_to_langchain
from src.services.agent_service import AgentService
from src.services.llm_service import LLMService

logger = logging.getLogger(__name__)


class AgentExecutionError(Exception):
    """Base exception for agent execution errors."""

    pass


class AgentExecutionService:
    """
    Service for executing agents with LangGraph + MCP tool support.

    Orchestrates complete agent execution workflow:
    1. Load agent configuration with tenant isolation
    2. Retrieve OpenAPI + MCP tools via UnifiedToolService
    3. Initialize LLM client using tenant's virtual key (LiteLLM)
    4. Convert MCP primitives to LangChain tools via MCPToolBridge
    5. Create ReAct agent with create_react_agent(model, tools)
    6. Execute agent with system prompt + user message
    7. Extract response and tool call history
    8. Handle errors gracefully with structured diagnostics

    Example usage:
        service = AgentExecutionService(db)
        result = await service.execute_agent(
            agent_id=agent_uuid,
            tenant_id="acme-corp",
            user_message="Process ticket #123",
            context={"ticket_id": 123}
        )
        if result["success"]:
            print(result["response"])
    """

    def __init__(
        self,
        db: AsyncSession,
        litellm_proxy_url: Optional[str] = None,
        master_key: Optional[str] = None,
    ):
        """
        Initialize Agent Execution Service.

        Args:
            db: AsyncSession for database operations
            litellm_proxy_url: Optional LiteLLM proxy URL (defaults to settings)
            master_key: Optional LiteLLM master key (defaults to settings)
        """
        self.db = db
        self.agent_service = AgentService()
        self.llm_service = LLMService(db, litellm_proxy_url, master_key)

        # Get LiteLLM proxy URL for init_chat_model
        from src.config import settings

        self.litellm_proxy_url = litellm_proxy_url or settings.litellm_proxy_url

    async def execute_agent(
        self,
        agent_id: UUID,
        tenant_id: str,
        user_message: str,
        context: Optional[Dict[str, Any]] = None,
        timeout_seconds: int = 120,
    ) -> Dict[str, Any]:
        """
        Execute agent with LangGraph ReAct workflow and MCP tool support.

        Main execution flow implementing AC#4 (execute agent with create_react_agent):
        1. Load agent configuration with tenant isolation (CRITICAL)
        2. Get LLM client with budget check (Story 8.10)
        3. Load all assigned tools (OpenAPI + MCP)
        4. Convert MCP primitives to LangChain tools
        5. Create ReAct agent with tool bindings
        6. Execute with system prompt + user message
        7. Return structured result

        Args:
            agent_id: Agent UUID to execute
            tenant_id: Tenant identifier for isolation and budget tracking
            user_message: User's input message to the agent
            context: Optional context dict for prompt variable substitution
            timeout_seconds: Maximum execution time (default: 120s)

        Returns:
            Dict containing:
            {
                "success": bool,
                "response": str,  # Agent's final response
                "tool_calls": list[dict],  # History of tool invocations
                "execution_time_seconds": float,
                "model_used": str,
                "error": str | None  # Error message if success=False
            }

        Raises:
            AgentExecutionError: If agent execution fails
            BudgetExceededError: If tenant budget exceeded (re-raised from LLMService)
            ValueError: If agent not found or tenant mismatch

        Example:
            >>> service = AgentExecutionService(db)
            >>> result = await service.execute_agent(
            >>>     agent_id=UUID("..."),
            >>>     tenant_id="acme-corp",
            >>>     user_message="Analyze ticket #123 and suggest resolution"
            >>> )
            >>> if result["success"]:
            >>>     print(f"Agent response: {result['response']}")
            >>>     print(f"Tools called: {len(result['tool_calls'])}")
        """
        start_time = datetime.now(timezone.utc)

        # Generate execution context ID for MCP bridge pooling (Story 11.2.3)
        execution_context_id = str(uuid.uuid4())

        try:
            # Step 1: Load agent with tenant isolation (CRITICAL: AC#7)
            logger.info(
                "Loading agent for execution",
                extra={
                    "agent_id": str(agent_id),
                    "tenant_id": tenant_id,
                },
            )

            agent = await self.agent_service.get_agent_by_id(
                tenant_id=tenant_id,
                agent_id=agent_id,
                db=self.db,
            )

            # Verify agent is active
            if agent.status != "active":
                raise AgentExecutionError(
                    f"Agent is not active (status: {agent.status}). "
                    "Only active agents can be executed."
                )

            # Step 2: Get tenant's virtual key and check budget (Story 8.10)
            logger.info(
                "Initializing LLM client for tenant",
                extra={"tenant_id": tenant_id},
            )

            try:
                # Get AsyncOpenAI client to extract API key (virtual key)
                # This also performs budget check per Story 8.10
                async_openai_client = await self.llm_service.get_llm_client_for_tenant(tenant_id)
                # Extract virtual key from client for init_chat_model
                virtual_key = async_openai_client.api_key
            except BudgetExceededError as e:
                logger.warning(
                    f"Budget exceeded for tenant {tenant_id}",
                    extra={"error": str(e)},
                )
                # Re-raise budget error for caller to handle
                raise

            # Step 3: Load all tools (OpenAPI + MCP) via UnifiedToolService
            logger.info(
                "Loading tools for agent",
                extra={"agent_id": str(agent_id)},
            )

            unified_tools = await self.agent_service.get_agent_tools(
                agent_id=agent_id,
                tenant_id=tenant_id,
                db=self.db,
            )

            logger.info(
                f"Loaded {len(unified_tools)} unified tools",
                extra={
                    "agent_id": str(agent_id),
                    "tool_count": len(unified_tools),
                },
            )

            # Step 4: Get active MCP servers for tool conversion
            stmt = select(MCPServer).where(
                MCPServer.tenant_id == tenant_id,
                MCPServer.status == "active",
            )
            db_result = await self.db.execute(stmt)
            mcp_servers = list(db_result.scalars().all())

            # Convert tools to LangChain-compatible format
            # Uses extracted tool_converter module (Story 12.7)
            langchain_tools = await convert_tools_to_langchain(
                unified_tools=unified_tools,
                mcp_servers=mcp_servers,
                execution_context_id=execution_context_id,
            )

            logger.info(
                f"Converted {len(langchain_tools)} tools to LangChain format",
                extra={"tool_count": len(langchain_tools)},
            )

            # Step 5: Extract LLM model from agent.llm_config
            llm_provider = agent.llm_config.get("provider", "openai")
            llm_model = agent.llm_config.get("model", "gpt-4o-mini")
            temperature = agent.llm_config.get("temperature", 0.3)
            max_tokens = agent.llm_config.get("max_tokens", 1000)

            # Normalize model string for LiteLLM proxy
            # Handles various config formats: provider-prefixed models, bare names, etc.
            # Reason: Ensure compatibility with all current and future LLM model configurations
            if "/" in llm_model:
                # Model already has provider prefix (e.g., "xai/grok-4-fast-reasoning")
                model_string = llm_model
                logger.info(
                    f"Using provider-prefixed model: {model_string}",
                    extra={"model": model_string, "provider": llm_provider},
                )
            elif llm_provider == "litellm" or not llm_provider:
                # Provider is generic marker or empty - use model as-is
                # LiteLLM will infer the correct provider
                model_string = llm_model
                logger.info(
                    f"Using model without prefix (provider={llm_provider}): {model_string}",
                    extra={"model": model_string, "provider": llm_provider},
                )
            else:
                # Traditional format: concatenate provider/model
                model_string = f"{llm_provider}/{llm_model}"
                logger.info(
                    f"Constructed model string from provider+model: {model_string}",
                    extra={"model": llm_model, "provider": llm_provider},
                )

            logger.info(
                "Creating ReAct agent",
                extra={
                    "model": model_string,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "tool_count": len(langchain_tools),
                },
            )

            # Step 6: Initialize chat model with ChatOpenAI
            # Using ChatOpenAI with LiteLLM proxy ensures proper tool binding for all providers
            # LiteLLM handles provider-specific tool calling formats (OpenAI, Grok, Claude, etc.)
            llm = ChatOpenAI(
                model=model_string,  # e.g., "xai/grok-4-fast-reasoning", "openai/gpt-4o-mini"
                api_key=virtual_key,  # Tenant's virtual key from LiteLLM
                base_url=f"{self.litellm_proxy_url}/v1",  # LiteLLM proxy endpoint
                temperature=temperature,
                max_tokens=max_tokens,
            )

            # Step 7: Create ReAct agent with LangGraph
            # Using create_react_agent pattern from LangGraph 0.6+
            agent_executor = create_react_agent(
                model=llm,
                tools=langchain_tools,
            )

            # Step 8: Build messages with system prompt + user message
            # Uses extracted message_builder module (Story 12.7)
            messages = build_messages(
                system_prompt=agent.system_prompt,
                user_message=user_message,
                context=context,
            )

            logger.info(
                "Executing agent",
                extra={
                    "agent_id": str(agent_id),
                    "message_count": len(messages),
                },
            )

            # Step 9: Execute agent with timeout
            try:
                execution_result = await asyncio.wait_for(
                    agent_executor.ainvoke({"messages": messages}),
                    timeout=timeout_seconds,
                )
            except asyncio.TimeoutError:
                raise AgentExecutionError(
                    f"Agent execution timeout after {timeout_seconds} seconds"
                )

            # DEBUG: Print execution result
            print(f"\n{'='*80}")
            print(f"AGENT EXECUTION RESULT DEBUG")
            print(f"Result type: {type(execution_result)}")
            print(f"Result keys: {execution_result.keys() if isinstance(execution_result, dict) else 'N/A'}")
            if isinstance(execution_result, dict) and "messages" in execution_result:
                print(f"Message count: {len(execution_result['messages'])}")
                for i, msg in enumerate(execution_result["messages"]):
                    msg_type = type(msg).__name__
                    msg_content = getattr(msg, "content", "N/A")
                    if msg_content != "N/A" and len(str(msg_content)) > 150:
                        msg_content = str(msg_content)[:150] + "..."
                    print(f"  Message {i}: {msg_type} - {msg_content}")
            print(f"{'='*80}\n")

            # Step 10: Extract response and tool calls from result
            # Uses extracted result_extractor module (Story 12.7)
            final_response = extract_response(execution_result)
            tool_calls = extract_tool_calls(execution_result)

            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()

            logger.info(
                "Agent execution completed",
                extra={
                    "agent_id": str(agent_id),
                    "execution_time_seconds": execution_time,
                    "tool_calls_count": len(tool_calls),
                },
            )

            return {
                "success": True,
                "response": final_response,
                "tool_calls": tool_calls,
                "execution_time_seconds": execution_time,
                "model_used": model_string,
                "error": None,
            }

        except BudgetExceededError:
            # Re-raise budget errors for caller to handle
            raise

        except Exception as e:
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            error_msg = f"Agent execution failed: {str(e)}"

            logger.error(
                error_msg,
                extra={
                    "agent_id": str(agent_id),
                    "tenant_id": tenant_id,
                    "error_type": type(e).__name__,
                    "execution_time_seconds": execution_time,
                },
                exc_info=True,
            )

            # Return structured error response
            return {
                "success": False,
                "response": "",
                "tool_calls": [],
                "execution_time_seconds": execution_time,
                "model_used": "",
                "error": error_msg,
            }

        finally:
            # Cleanup MCP bridge for this execution context (Story 11.2.3)
            # Uses extracted mcp_bridge_pooler module (Story 12.7)
            await cleanup_mcp_bridge(execution_context_id)
