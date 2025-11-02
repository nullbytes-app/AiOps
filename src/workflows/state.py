"""
Workflow state definitions for LangGraph orchestration.

Defines the WorkflowState TypedDict that represents the complete state of
the enhancement context gathering workflow. Passed between all workflow nodes
and consumed by Story 2.9 LLM synthesis.

Story: 2.8 - Integrate LangGraph Workflow Orchestration
"""

from typing import Any, List, Optional, TypedDict


class WorkflowState(TypedDict):
    """
    Complete state for enhancement context gathering workflow.

    Represents the shared state passed between LangGraph workflow nodes.
    Each node reads and updates this state with additional context data.

    Fields:
        tenant_id: Tenant identifier for data isolation and logging
        ticket_id: Unique identifier for the support ticket being enhanced
        description: Ticket description text (source for all searches)
        priority: Ticket priority level (e.g., "high", "medium", "low")
        timestamp: ISO 8601 timestamp of ticket creation
        correlation_id: Request correlation ID for distributed tracing

        similar_tickets: Results from ticket history search (Story 2.5)
            List[dict] with fields: ticket_id, description, resolution, resolved_date
            Default: empty list if no matches or search fails

        kb_articles: Results from knowledge base search (Story 2.6)
            List[dict] with fields: title, summary, url
            Default: empty list if API unavailable or no matches

        ip_info: Results from IP address lookup (Story 2.7)
            List[dict] with fields: ip_address, hostname, role, client, location
            Default: empty list if no IPs extracted or no system matches

        errors: Accumulated errors from workflow nodes
            List[dict] with fields: node_name, error_message, timestamp, severity
            Tracks failures for debugging without blocking workflow

    Usage:
        >>> from src.workflows.state import WorkflowState
        >>> from src.workflows.enhancement_workflow import enhancement_graph
        >>>
        >>> state: WorkflowState = {
        ...     "tenant_id": "acme-corp",
        ...     "ticket_id": "TICKET-123",
        ...     "description": "Server down, IP 192.168.1.5",
        ...     "priority": "high",
        ...     "timestamp": "2025-11-02T10:30:00Z",
        ...     "correlation_id": "req-456",
        ...     "similar_tickets": [],
        ...     "kb_articles": [],
        ...     "ip_info": [],
        ...     "errors": [],
        ... }
        >>> result = enhancement_graph.invoke(state)
        >>> print(f"Found {len(result['similar_tickets'])} similar tickets")
    """

    tenant_id: str
    ticket_id: str
    description: str
    priority: Optional[str]
    timestamp: str
    correlation_id: str
    similar_tickets: List[dict]
    kb_articles: List[dict]
    ip_info: List[dict]
    errors: List[dict]
