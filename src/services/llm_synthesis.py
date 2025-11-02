"""
LLM-based synthesis service for generating contextual enhancements.

This module provides the core functionality for synthesizing enhancement recommendations
using OpenRouter API with OpenAI SDK. It handles context formatting, LLM API calls,
output validation, and graceful error handling.

Key Functions:
- synthesize_enhancement(): Main entry point for synthesis
- format_tickets(), format_kb_articles(), format_ip_info(): Context formatters
- truncate_to_words(): Word limit enforcement
"""

import asyncio
import json
from typing import Optional, List, Dict, Any
from http import HTTPStatus

from loguru import logger
from openai import AsyncOpenAI, APIError, APIConnectionError, APITimeoutError

from src.config import settings
from src.workflows.state import WorkflowState


# =============================================================================
# PROMPTS AND TEMPLATES
# =============================================================================

ENHANCEMENT_SYSTEM_PROMPT = """You are an AI assistant helping MSP technicians resolve IT incidents faster.

Your task: Analyze the gathered context (similar tickets, documentation, system information) and synthesize actionable insights that the technician can immediately apply.

Guidelines:
- Provide concise, actionable recommendations (maximum 500 words)
- Focus on fact-based insights derived from the context provided
- Organize output into clear sections with markdown headers
- Be professional and avoid speculation beyond the provided context
- Do not make recommendations outside the scope of incident resolution

Output Format:
Provide your analysis in these sections (use ## headers):
- Similar Tickets: Key similarities and how previous resolutions apply
- Relevant Documentation: Links and summaries of applicable KB articles
- System Information: Relevant system/network context that impacts resolution
- Recommended Next Steps: Specific actions the technician should take

Remember: Prioritize accuracy over comprehensiveness. It's better to cite sources than to speculate."""

ENHANCEMENT_USER_TEMPLATE = """Incident Details:
- Ticket ID: {ticket_id}
- Description: {description}
- Priority: {priority}

Context Gathered:

{similar_tickets_section}

{kb_articles_section}

{system_info_section}

Based on this context, provide your analysis and recommendations to help resolve this incident."""


# =============================================================================
# OPENROUTER CLIENT INITIALIZATION
# =============================================================================

def _initialize_llm_client() -> AsyncOpenAI:
    """
    Initialize OpenRouter API client using AsyncOpenAI SDK.

    The OpenRouter API is compatible with OpenAI SDK and provides multi-model
    access while being cost-optimized. The client requires:
    - API key: Loaded from OPENROUTER_API_KEY environment variable
    - Base URL: https://openrouter.ai/api/v1
    - Headers: HTTP-Referer and X-Title for OpenRouter analytics/rankings

    Returns:
        AsyncOpenAI: Configured async OpenAI client for OpenRouter

    Raises:
        ValueError: If API key is missing or invalid format
    """
    if not settings.openrouter_api_key or not settings.openrouter_api_key.strip():
        raise ValueError("OPENROUTER_API_KEY environment variable is required")

    return AsyncOpenAI(
        api_key=settings.openrouter_api_key,
        base_url=settings.openrouter_base_url,
        default_headers={
            "HTTP-Referer": settings.openrouter_site_url,
            "X-Title": settings.openrouter_app_name,
        },
    )


# Initialize client at module level
# Note: May be None in test environments or when config is unavailable
try:
    if settings is not None:
        _llm_client = _initialize_llm_client()
    else:
        _llm_client = None
except (ValueError, AttributeError) as e:
    logger.warning(f"LLM client initialization failed: {e}. Synthesis will return fallback.")
    _llm_client = None


# =============================================================================
# CONTEXT FORMATTING HELPERS
# =============================================================================

def format_tickets(tickets: Optional[List[Dict[str, Any]]]) -> str:
    """
    Format similar tickets into markdown list for LLM consumption.

    Args:
        tickets: List of similar tickets with ticket_id, description, resolution,
                resolved_date, relevance_score fields

    Returns:
        str: Markdown-formatted ticket list (up to 5 tickets) or fallback message
    """
    if not tickets:
        return "No similar tickets found."

    formatted = []
    for ticket in tickets[:5]:  # Limit to top 5 for brevity
        ticket_id = ticket.get("ticket_id", "UNKNOWN")
        description = ticket.get("description", "")[:100]  # Truncate description
        resolution = ticket.get("resolution", "")[:150]
        score = ticket.get("relevance_score", 0)
        date = ticket.get("resolved_date", "")

        entry = (
            f"- **Ticket {ticket_id}** (relevance: {score:.1%})\n"
            f"  - Issue: {description}...\n"
            f"  - Resolution: {resolution}...\n"
            f"  - Resolved: {date}"
        )
        formatted.append(entry)

    return "\n".join(formatted)


def format_kb_articles(articles: Optional[List[Dict[str, Any]]]) -> str:
    """
    Format KB articles into markdown links for LLM consumption.

    Args:
        articles: List of KB articles with title, summary, url fields

    Returns:
        str: Markdown-formatted article list (up to 3 articles) or fallback message
    """
    if not articles:
        return "No relevant documentation found."

    formatted = []
    for article in articles[:3]:  # Limit to top 3 for brevity
        title = article.get("title", "Untitled")
        url = article.get("url", "#")
        summary = article.get("summary", "")[:150]

        entry = f"- [{title}]({url}): {summary}..."
        formatted.append(entry)

    return "\n".join(formatted)


def format_ip_info(ip_info: Optional[List[Dict[str, Any]]]) -> str:
    """
    Format system/IP information into human-readable format for LLM.

    Args:
        ip_info: List of systems with ip_address, hostname, role, client, location fields

    Returns:
        str: Formatted system inventory or fallback message
    """
    if not ip_info:
        return "No system information found."

    formatted = []
    for system in ip_info[:5]:  # Limit to top 5 systems
        hostname = system.get("hostname", "UNKNOWN")
        ip = system.get("ip_address", "N/A")
        role = system.get("role", "Unknown")
        client = system.get("client", "N/A")
        location = system.get("location", "N/A")

        entry = (
            f"- **{hostname}** ({ip})\n"
            f"  - Role: {role}\n"
            f"  - Client: {client}\n"
            f"  - Location: {location}"
        )
        formatted.append(entry)

    return "\n".join(formatted)


# =============================================================================
# WORD LIMIT ENFORCEMENT
# =============================================================================

def truncate_to_words(text: str, max_words: int) -> str:
    """
    Truncate text to maximum word count, preserving complete sentences.

    Args:
        text: Text to truncate
        max_words: Maximum number of words

    Returns:
        str: Truncated text with indicator if truncation occurred
    """
    words = text.split()

    if len(words) <= max_words:
        return text

    # Truncate and find the last complete sentence
    truncated = " ".join(words[:max_words])

    # Try to end at sentence boundary
    for punct in [".", "!", "?"]:
        if punct in truncated:
            last_punct = truncated.rfind(punct)
            truncated = truncated[: last_punct + 1]
            break

    logger.warning(
        f"Enhancement output exceeded {max_words} words, truncating. "
        f"Original: {len(words)} words, Truncated: {len(truncated.split())} words"
    )

    return f"{truncated}\n\n[Output truncated to {max_words}-word limit]"


# =============================================================================
# MAIN SYNTHESIS FUNCTION
# =============================================================================


async def synthesize_enhancement(context: WorkflowState) -> str:
    """
    Synthesize LLM-based enhancement recommendations from gathered context.

    This is the main entry point for LLM synthesis. It takes the WorkflowState from
    Story 2.8 (LangGraph context gathering) and returns markdown-formatted synthesis.

    The function:
    1. Formats context (tickets, KB articles, IP info) into readable sections
    2. Fills user prompt template with formatted context
    3. Calls OpenRouter API with 30-second timeout
    4. Enforces 500-word limit on output
    5. Logs token usage for cost tracking
    6. Returns graceful fallback on any error

    Args:
        context: WorkflowState from Story 2.8 containing:
                - tenant_id: Tenant identifier
                - ticket_id: Ticket being enhanced
                - description: Ticket description
                - priority: Ticket priority
                - similar_tickets: List of similar tickets
                - kb_articles: List of relevant KB articles
                - ip_info: List of systems/IP information
                - errors: Any errors encountered during context gathering (not blocking)

    Returns:
        str: Markdown-formatted enhancement recommendation (max 500 words)

    Raises:
        No exceptions raised - all errors caught and fallback returned
    """
    tenant_id = context.get("tenant_id", "unknown")
    ticket_id = context.get("ticket_id", "unknown")
    description = context.get("description", "")
    priority = context.get("priority", "normal")

    correlation_id = context.get("correlation_id", ticket_id)

    logger.info(
        f"Starting LLM synthesis | ticket_id={ticket_id} | tenant_id={tenant_id} | "
        f"correlation_id={correlation_id}"
    )

    # Check if client is initialized
    if _llm_client is None:
        logger.error(
            f"LLM client not initialized | ticket_id={ticket_id} | "
            f"correlation_id={correlation_id}"
        )
        return _build_fallback_output(
            context,
            "LLM synthesis service is unavailable. Please try again or contact support.",
        )

    try:
        # Step 1: Format context summaries
        similar_tickets_section = "## Similar Tickets\n" + format_tickets(
            context.get("similar_tickets")
        )
        kb_articles_section = "## Relevant Documentation\n" + format_kb_articles(
            context.get("kb_articles")
        )
        system_info_section = "## System Information\n" + format_ip_info(
            context.get("ip_info")
        )

        # Step 2: Fill user prompt template
        user_message = ENHANCEMENT_USER_TEMPLATE.format(
            ticket_id=ticket_id,
            description=description,
            priority=priority,
            similar_tickets_section=similar_tickets_section,
            kb_articles_section=kb_articles_section,
            system_info_section=system_info_section,
        )

        # Step 3: Call OpenRouter API with timeout
        if settings is None:
            logger.error("Settings not initialized | ticket_id={ticket_id}")
            return _build_fallback_output(context, "Configuration unavailable")

        logger.debug(f"Calling OpenRouter API | model={settings.llm_model}")

        try:
            response = await asyncio.wait_for(
                _llm_client.chat.completions.create(
                    model=settings.llm_model,
                    messages=[
                        {"role": "system", "content": ENHANCEMENT_SYSTEM_PROMPT},
                        {"role": "user", "content": user_message},
                    ],
                    max_tokens=settings.llm_max_tokens,
                    temperature=settings.llm_temperature,
                ),
                timeout=settings.llm_timeout_seconds,
            )
        except asyncio.TimeoutError:
            logger.warning(
                f"LLM API timeout after {settings.llm_timeout_seconds}s | "
                f"ticket_id={ticket_id} | correlation_id={correlation_id}"
            )
            return _build_fallback_output(context, "AI synthesis timed out. Showing context.")

        # Step 4: Extract response content
        synthesis_text = response.choices[0].message.content or ""

        # Step 5: Enforce word limit
        synthesis_text = truncate_to_words(synthesis_text, max_words=500)

        # Step 6: Log token usage for cost tracking
        if response.usage:
            usage_log = {
                "event": "llm_synthesis_token_usage",
                "correlation_id": correlation_id,
                "tenant_id": tenant_id,
                "ticket_id": ticket_id,
                "model": settings.llm_model,
                "input_tokens": response.usage.prompt_tokens,
                "output_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }
            logger.info(json.dumps(usage_log))

        logger.info(
            f"LLM synthesis completed | ticket_id={ticket_id} | "
            f"output_length={len(synthesis_text.split())} words | "
            f"correlation_id={correlation_id}"
        )

        return synthesis_text

    except APIConnectionError as e:
        logger.error(
            f"LLM API connection error | ticket_id={ticket_id} | "
            f"error={str(e)} | correlation_id={correlation_id}"
        )
        return _build_fallback_output(context, "Connection to AI service failed.")

    except APITimeoutError as e:
        logger.warning(
            f"LLM API timeout error | ticket_id={ticket_id} | "
            f"error={str(e)} | correlation_id={correlation_id}"
        )
        return _build_fallback_output(context, "AI service request timed out.")

    except APIError as e:
        # Handle authentication errors (401) specially
        if hasattr(e, "status_code") and e.status_code == HTTPStatus.UNAUTHORIZED:
            logger.critical(
                f"LLM API authentication failed (401) | ticket_id={ticket_id} | "
                f"correlation_id={correlation_id}"
            )
        elif hasattr(e, "status_code") and e.status_code >= 500:
            logger.error(
                f"LLM API server error ({e.status_code}) | ticket_id={ticket_id} | "
                f"correlation_id={correlation_id}"
            )
        else:
            logger.error(
                f"LLM API error | ticket_id={ticket_id} | "
                f"error={str(e)} | correlation_id={correlation_id}"
            )

        return _build_fallback_output(context, "AI synthesis service error occurred.")

    except Exception as e:
        logger.exception(
            f"Unexpected error during LLM synthesis | ticket_id={ticket_id} | "
            f"error={str(e)} | correlation_id={correlation_id}"
        )
        return _build_fallback_output(context, "An unexpected error occurred.")


# =============================================================================
# FALLBACK OUTPUT BUILDER
# =============================================================================


def _build_fallback_output(context: WorkflowState, error_note: str) -> str:
    """
    Build fallback output when LLM synthesis fails (graceful degradation).

    Args:
        context: WorkflowState with gathered context
        error_note: Brief note about why synthesis failed

    Returns:
        str: Formatted context without synthesis, with disclaimer
    """
    ticket_id = context.get("ticket_id", "unknown")

    fallback = f"""## Context Gathered

{format_tickets(context.get("similar_tickets"))}

## Relevant Documentation

{format_kb_articles(context.get("kb_articles"))}

## System Information

{format_ip_info(context.get("ip_info"))}

---

**Note:** AI synthesis was unavailable ({error_note}). The above context has been gathered from your knowledge base and similar tickets. Please review and determine next steps manually."""

    return fallback
