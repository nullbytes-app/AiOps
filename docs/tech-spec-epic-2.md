# Epic Technical Specification: Core Enhancement Agent

**Date:** 2025-11-02
**Author:** Ravi (via Winston - BMM Architect)
**Epic ID:** 2
**Status:** Draft
**Stories Covered:** 2.5, 2.5A, 2.5B, 2.6, 2.7, 2.8, 2.9, 2.10, 2.11, 2.12
**Prerequisites:** Epic 1 Complete (Foundation & Infrastructure)

---

## Overview

Epic 2 implements the core enhancement agent workflow that delivers the platform's primary value proposition: automated ticket enhancement with AI-synthesized context from multiple sources. This epic builds upon the foundation established in Epic 1 (FastAPI, PostgreSQL, Redis, Celery, Kubernetes) and delivers an end-to-end system capable of:

1. **Context Gathering** (Stories 2.5-2.7): Search historical tickets, knowledge base articles, and system inventory for relevant information
2. **Workflow Orchestration** (Story 2.8): Use LangGraph to execute context gathering nodes in parallel
3. **AI Synthesis** (Story 2.9): Leverage OpenRouter API Gateway and GPT-4o-mini to analyze context and generate actionable insights
4. **Ticket Updates** (Story 2.10): Post enhancements back to ServiceDesk Plus via REST API
5. **Integration & Testing** (Stories 2.11-2.12): Validate end-to-end workflow and achieve comprehensive test coverage

By the end of this epic, a technician creating a ticket in ServiceDesk Plus will automatically receive an enhancement within 60 seconds (p95) containing similar ticket resolutions, relevant documentation, system information, and recommended next steps.

---

## Objectives and Scope

### In Scope

**Context Gathering & Data Ingestion:**
- PostgreSQL full-text search for ticket_history table (Story 2.5)
- Bulk import of historical tickets from ServiceDesk Plus API (Story 2.5A)
- Automatic storage of resolved tickets via webhook (Story 2.5B)
- Knowledge base API integration with Redis caching (Story 2.6)
- IP address extraction and system inventory lookup (Story 2.7)

**AI Workflow & Synthesis:**
- LangGraph workflow orchestration with parallel execution (Story 2.8)
- OpenRouter API Gateway integration (Story 2.9)
- GPT-4o-mini for context synthesis (Story 2.9)
- System prompts and output formatting (Story 2.9)
- 500-word limit enforcement (Story 2.9)

**Integration & Quality:**
- ServiceDesk Plus API client for ticket updates (Story 2.10)
- End-to-end workflow validation (Story 2.11)
- Comprehensive unit and integration testing (Story 2.12)

### Out of Scope

- Multi-tenant security implementation (Epic 3)
- Row-level security policies (Epic 3 Story 3.1)
- Prometheus metrics instrumentation (Epic 4 Story 4.1)
- Production deployment (Epic 5)
- Admin UI (Epic 6)
- Plugin architecture (Epic 7)

---

## System Architecture Alignment

This epic implements the core enhancement workflow defined in architecture.md:

```
┌─────────────────────────────────────────────────────────────────┐
│                    EPIC 2 ARCHITECTURE                          │
└─────────────────────────────────────────────────────────────────┘

ServiceDesk Plus                                    ServiceDesk Plus
     │                                                      ▲
     │ 1. Webhook: Ticket Created                         │ 9. POST /api/v3/requests/{id}/notes
     │    (Story 2.1-2.4 DONE)                            │    (Story 2.10)
     ▼                                                     │
┌────────────────────┐                                    │
│   FastAPI API      │                                    │
│   /webhook/        │                                    │
│   servicedesk      │                                    │
└────────┬───────────┘                                    │
         │ 2. Queue job                                   │
         │    (Story 2.3 DONE)                           │
         ▼                                                │
┌────────────────────┐                                    │
│   Redis Queue      │◄───────────────┐                  │
│   enhancement:     │                │                  │
│   queue            │                │                  │
└────────┬───────────┘                │                  │
         │ 3. Celery worker pulls    │                  │
         │    (Story 2.4 DONE)        │                  │
         ▼                             │                  │
┌─────────────────────────────────────────────────────────┐
│              CELERY WORKER (enhance_ticket task)        │
│                                                         │
│  ┌──────────────────────────────────────────────────┐  │
│  │   4. Context Gathering (Stories 2.5-2.7)         │  │
│  │                                                   │  │
│  │   ┌─────────────────┐                            │  │
│  │   │ Ticket History  │ ← Story 2.5: PostgreSQL    │  │
│  │   │ Search          │   FTS, ticket_history      │  │
│  │   └────────┬────────┘                            │  │
│  │            │ TOP 5 similar tickets                │  │
│  │            │                                      │  │
│  │   ┌────────▼────────┐                            │  │
│  │   │ Knowledge Base  │ ← Story 2.6: KB API,       │  │
│  │   │ Search          │   Redis cache (1hr)        │  │
│  │   └────────┬────────┘                            │  │
│  │            │ TOP 3 KB articles                   │  │
│  │            │                                      │  │
│  │   ┌────────▼────────┐                            │  │
│  │   │ IP Address      │ ← Story 2.7: Regex         │  │
│  │   │ Cross-Reference │   extraction, inventory    │  │
│  │   └────────┬────────┘   lookup                   │  │
│  │            │ System info (hostname, role)        │  │
│  └────────────┼──────────────────────────────────────┘  │
│               │                                         │
│  ┌────────────▼──────────────────────────────────────┐  │
│  │   5. LangGraph Orchestration (Story 2.8)          │  │
│  │                                                    │  │
│  │   ┌──────────┐  ┌──────────┐  ┌──────────┐       │  │
│  │   │ ticket_  │  │   kb_    │  │   ip_    │       │  │
│  │   │ search   │  │  search  │  │  lookup  │       │  │
│  │   │  node    │  │   node   │  │   node   │       │  │
│  │   └────┬─────┘  └────┬─────┘  └────┬─────┘       │  │
│  │        │             │             │              │  │
│  │        └─────────────┼─────────────┘              │  │
│  │                      │ Parallel execution         │  │
│  │                      │ (reduce latency)           │  │
│  │                      ▼                            │  │
│  │            ┌──────────────────┐                   │  │
│  │            │ aggregate_results│                   │  │
│  │            │      node        │                   │  │
│  │            └─────────┬────────┘                   │  │
│  └──────────────────────┼──────────────────────────┘  │
│                         │ WorkflowState              │
│                         │                            │
│  ┌──────────────────────▼──────────────────────────┐  │
│  │   6. LLM Synthesis (Story 2.9)                   │  │
│  │                                                   │  │
│  │   OpenRouter API Gateway                         │  │
│  │   ┌───────────────────────────────────────┐      │  │
│  │   │ POST /api/v1/chat/completions         │      │  │
│  │   │                                        │      │  │
│  │   │ Model: openai/gpt-4o-mini             │      │  │
│  │   │ System Prompt: enhancement agent role │      │  │
│  │   │ User Prompt: ticket + context         │      │  │
│  │   │ Max Tokens: 1000 (≈500 words)         │      │  │
│  │   │ Temperature: 0.3 (consistent output)  │      │  │
│  │   └───────────────┬───────────────────────┘      │  │
│  │                   │ Enhancement text (markdown)  │  │
│  └───────────────────┼──────────────────────────────┘  │
│                      │                                 │
│  ┌───────────────────▼──────────────────────────────┐  │
│  │   7. Format & Truncate (Story 2.9)               │  │
│  │   - Enforce 500-word limit                       │  │
│  │   - Add source citations                         │  │
│  │   - Format as HTML/Markdown                      │  │
│  └───────────────────┬──────────────────────────────┘  │
│                      │ Final enhancement              │
└──────────────────────┼──────────────────────────────────┘
                       │
         ┌─────────────▼─────────────┐
         │ 8. ServiceDesk Plus API   │
         │    Client (Story 2.10)    │
         │                           │
         │ POST /api/v3/requests/    │
         │      {id}/notes           │
         │                           │
         │ - Retry: 3 attempts       │
         │ - Backoff: exponential    │
         │ - Timeout: 30s            │
         └───────────────────────────┘
```

**Key Architectural Patterns:**

1. **Parallel Context Gathering**: Stories 2.5-2.7 execute concurrently via LangGraph (Story 2.8), reducing latency from ~30s sequential to ~10-15s parallel
2. **Graceful Degradation**: Failed context nodes don't block enhancement (partial context acceptable per NFR003)
3. **Caching Strategy**: Knowledge base results cached in Redis (1hr TTL), tenant configs cached (5min TTL)
4. **Error Handling**: Retry logic at multiple layers (Celery task, OpenRouter API, ServiceDesk Plus API)
5. **Data Provenance**: ticket_history rows tagged with `source` (bulk_import, webhook_resolved, api_fallback) and `ingested_at` timestamp

---

## Detailed Design

### 1. Context Gathering: Ticket History Search (Story 2.5)

**Objective:** Implement PostgreSQL full-text search to find similar historical tickets.

**Database Schema (ticket_history table):**

```sql
CREATE TABLE ticket_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id VARCHAR(100) NOT NULL,
    ticket_id VARCHAR(100) NOT NULL,
    description TEXT NOT NULL,
    resolution TEXT,
    resolved_date TIMESTAMP WITH TIME ZONE,
    tags TEXT[],
    source VARCHAR(50) NOT NULL,  -- 'bulk_import', 'webhook_resolved', 'api_fallback'
    ingested_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Indexes
    CONSTRAINT ticket_history_unique UNIQUE (tenant_id, ticket_id)
);

CREATE INDEX idx_ticket_history_tenant ON ticket_history(tenant_id);
CREATE INDEX idx_ticket_history_description_fts ON ticket_history USING gin(to_tsvector('english', description));
CREATE INDEX idx_ticket_history_resolved_date ON ticket_history(resolved_date DESC);
```

**Full-Text Search Implementation:**

```python
# src/services/ticket_history_search.py
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from src.database.models import TicketHistory
from typing import List, Dict

async def search_similar_tickets(
    session: AsyncSession,
    tenant_id: str,
    description: str,
    limit: int = 5
) -> List[Dict]:
    """
    Search ticket_history for similar tickets using PostgreSQL full-text search.

    Args:
        session: Async database session
        tenant_id: Tenant identifier for data isolation
        description: Ticket description to search for
        limit: Maximum number of results (default 5)

    Returns:
        List of dictionaries containing similar ticket info
    """
    # Create tsvector from description
    ts_query = func.plainto_tsquery('english', description)
    ts_vector = func.to_tsvector('english', TicketHistory.description)

    # Query with FTS ranking
    stmt = (
        select(
            TicketHistory.ticket_id,
            TicketHistory.description,
            TicketHistory.resolution,
            TicketHistory.resolved_date,
            TicketHistory.tags,
            func.ts_rank(ts_vector, ts_query).label('rank')
        )
        .where(TicketHistory.tenant_id == tenant_id)
        .where(TicketHistory.resolution.isnot(None))  # Only resolved tickets
        .where(func.ts_rank(ts_vector, ts_query) > 0.01)  # Minimum relevance threshold
        .order_by(func.ts_rank(ts_vector, ts_query).desc())
        .limit(limit)
    )

    result = await session.execute(stmt)
    rows = result.all()

    return [
        {
            "ticket_id": row.ticket_id,
            "description": row.description[:200],  # Truncate for context
            "resolution": row.resolution[:500],
            "resolved_date": row.resolved_date.isoformat(),
            "tags": row.tags or [],
            "relevance_score": float(row.rank)
        }
        for row in rows
    ]
```

**Performance Targets:**
- Search completes in <2 seconds for 10,000 ticket database (per AC)
- Full-text search index significantly faster than LIKE queries
- Rank threshold (0.01) filters out irrelevant results

---

### 2. Context Gathering: Bulk Ticket Import (Story 2.5A)

**Objective:** Implement script to bulk import historical tickets from ServiceDesk Plus API during tenant onboarding.

**Script Implementation:**

```python
# scripts/import_tickets.py
import asyncio
import argparse
import httpx
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from src.database.models import TicketHistory
from src.config import settings
import logging

logger = logging.getLogger(__name__)

async def fetch_tickets_from_servicedesk(
    client: httpx.AsyncClient,
    base_url: str,
    api_key: str,
    start_date: datetime,
    end_date: datetime,
    page: int = 1,
    per_page: int = 100
) -> List[Dict]:
    """
    Fetch tickets from ServiceDesk Plus API with pagination.

    API Endpoint: GET /api/v3/requests
    Query Params:
        - list_info: {"start_index": 0, "row_count": 100}
        - input_data: {"status": "Closed", "resolved_time": {"from": ..., "to": ...}}
    """
    start_index = (page - 1) * per_page

    params = {
        "list_info": {
            "start_index": start_index,
            "row_count": per_page
        },
        "input_data": {
            "status": {"name": ["Closed", "Resolved"]},
            "resolved_time": {
                "from": int(start_date.timestamp() * 1000),
                "to": int(end_date.timestamp() * 1000)
            }
        }
    }

    response = await client.get(
        f"{base_url}/api/v3/requests",
        params=params,
        headers={"authtoken": api_key},
        timeout=30.0
    )

    response.raise_for_status()
    data = response.json()

    return data.get("requests", [])

async def import_tickets(
    tenant_id: str,
    base_url: str,
    api_key: str,
    days: int = 90
):
    """
    Bulk import historical tickets from ServiceDesk Plus.

    Usage:
        python scripts/import_tickets.py --tenant-id=acme-corp --days=90
    """
    engine = create_async_engine(settings.database_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    logger.info(f"Starting ticket import for tenant {tenant_id}")
    logger.info(f"Date range: {start_date.date()} to {end_date.date()}")

    total_imported = 0
    total_skipped = 0
    page = 1

    async with httpx.AsyncClient() as client:
        async with async_session() as session:
            while True:
                try:
                    tickets = await fetch_tickets_from_servicedesk(
                        client, base_url, api_key, start_date, end_date, page
                    )

                    if not tickets:
                        break  # No more pages

                    for ticket in tickets:
                        try:
                            # Extract fields
                            ticket_obj = TicketHistory(
                                tenant_id=tenant_id,
                                ticket_id=str(ticket["id"]),
                                description=ticket["subject"] + "\n\n" + ticket.get("description", ""),
                                resolution=ticket.get("resolution", {}).get("content", ""),
                                resolved_date=datetime.fromtimestamp(ticket["resolved_time"]["value"] / 1000),
                                tags=[tag["name"] for tag in ticket.get("tags", [])],
                                source="bulk_import",
                                ingested_at=datetime.now()
                            )

                            # Upsert (insert or ignore duplicate)
                            session.add(ticket_obj)
                            await session.commit()
                            total_imported += 1

                        except Exception as e:
                            logger.warning(f"Skipped ticket {ticket.get('id')}: {str(e)}")
                            total_skipped += 1
                            await session.rollback()
                            continue

                    # Progress logging
                    logger.info(f"Imported {total_imported} tickets (page {page}, skipped {total_skipped})")

                    # Rate limiting: 100 requests per minute
                    await asyncio.sleep(0.6)  # 60s / 100 = 0.6s per request

                    page += 1

                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 429:
                        # Rate limit exceeded, backoff
                        logger.warning("Rate limit hit, waiting 60s")
                        await asyncio.sleep(60)
                        continue
                    else:
                        logger.error(f"HTTP error: {e}")
                        raise

    logger.info(f"Import complete: {total_imported} tickets imported, {total_skipped} skipped")
    return total_imported, total_skipped

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Import historical tickets from ServiceDesk Plus")
    parser.add_argument("--tenant-id", required=True, help="Tenant identifier")
    parser.add_argument("--days", type=int, default=90, help="Number of days to import (default: 90)")

    args = parser.parse_args()

    # Load tenant config from database
    # (Implementation omitted for brevity - fetch base_url, api_key from tenant_configs table)

    asyncio.run(import_tickets(args.tenant_id, base_url, api_key, args.days))
```

**Performance Characteristics:**
- **Target:** 100 tickets/minute = 10,000 tickets in <2 hours (per AC)
- **Rate Limiting:** 0.6s delay between requests (respects ServiceDesk Plus 100 req/min limit)
- **Error Handling:** Skip invalid tickets, log errors, continue processing
- **Idempotency:** UNIQUE constraint on (tenant_id, ticket_id) prevents duplicates

---

### 3. Context Gathering: Resolved Ticket Storage (Story 2.5B)

**Objective:** Automatically store resolved tickets via webhook to keep ticket_history fresh.

**Webhook Endpoint:**

```python
# src/api/webhooks.py (add new endpoint)
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel, Field
from datetime import datetime
from src.database.session import get_session
from src.database.models import TicketHistory
from src.services.webhook_validator import validate_signature
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

class ResolvedTicketWebhook(BaseModel):
    tenant_id: str
    ticket_id: str
    subject: str
    description: str
    resolution: str
    resolved_date: datetime
    tags: List[str] = Field(default_factory=list)

@router.post("/webhook/servicedesk/resolved")
async def store_resolved_ticket(
    payload: ResolvedTicketWebhook,
    x_servicedesk_signature: str = Header(...),
    session: AsyncSession = Depends(get_session)
):
    """
    Store resolved ticket in ticket_history for future context gathering.

    This webhook is triggered when a ticket status changes to "Resolved" or "Closed"
    in ServiceDesk Plus. It stores the ticket data with provenance tracking.

    Authentication: HMAC-SHA256 signature validation (reuses Story 2.2 logic)
    """
    # Validate webhook signature (Story 2.2)
    await validate_signature(payload.tenant_id, payload.dict(), x_servicedesk_signature)

    # UPSERT: Insert or update if ticket already exists
    stmt = (
        insert(TicketHistory)
        .values(
            tenant_id=payload.tenant_id,
            ticket_id=payload.ticket_id,
            description=f"{payload.subject}\n\n{payload.description}",
            resolution=payload.resolution,
            resolved_date=payload.resolved_date,
            tags=payload.tags,
            source="webhook_resolved",
            ingested_at=datetime.now()
        )
        .on_conflict_do_update(
            index_elements=["tenant_id", "ticket_id"],
            set_={
                "resolution": payload.resolution,
                "resolved_date": payload.resolved_date,
                "source": "webhook_resolved",
                "ingested_at": datetime.now()
            }
        )
    )

    await session.execute(stmt)
    await session.commit()

    logger.info(f"Stored resolved ticket: {payload.ticket_id} (tenant: {payload.tenant_id})")

    # Prometheus metric (Epic 4)
    # ticket_history_stored_total.labels(tenant_id=payload.tenant_id, source="webhook_resolved").inc()

    return {"status": "accepted", "ticket_id": payload.ticket_id}
```

**Data Provenance:**
- `source='webhook_resolved'`: Distinguishes from bulk_import or api_fallback
- `ingested_at=NOW()`: Tracks when data entered system
- UPSERT logic: Updates resolution if ticket re-resolved or updated

---

### 4. Context Gathering: Knowledge Base Search (Story 2.6)

**Objective:** Integrate with knowledge base API to retrieve relevant articles, with Redis caching.

**Implementation:**

```python
# src/services/kb_search.py
import httpx
from typing import List, Dict, Optional
from src.cache.redis_client import redis_client
from src.config import settings
import json
import logging

logger = logging.getLogger(__name__)

async def search_knowledge_base(
    tenant_id: str,
    description: str,
    kb_base_url: str,
    kb_api_key: str,
    limit: int = 3
) -> List[Dict]:
    """
    Search knowledge base for relevant articles.

    Args:
        tenant_id: Tenant identifier (for cache key)
        description: Ticket description to search for
        kb_base_url: Knowledge base API base URL (tenant-specific)
        kb_api_key: API key for authentication
        limit: Maximum articles to return (default 3)

    Returns:
        List of articles with title, summary, URL
    """
    # Check Redis cache first (1 hour TTL per AC)
    cache_key = f"kb_search:{tenant_id}:{hash(description)}"
    cached = await redis_client.get(cache_key)

    if cached:
        logger.info(f"KB search cache hit: {cache_key}")
        return json.loads(cached)

    # Call KB API
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:  # 10s timeout per AC
            response = await client.get(
                f"{kb_base_url}/api/search",
                params={"query": description, "limit": limit},
                headers={"Authorization": f"Bearer {kb_api_key}"}
            )

            response.raise_for_status()
            data = response.json()

            articles = [
                {
                    "title": article["title"],
                    "summary": article["summary"][:200],  # Truncate
                    "url": article["url"]
                }
                for article in data.get("results", [])
            ]

            # Cache for 1 hour
            await redis_client.setex(cache_key, 3600, json.dumps(articles))

            logger.info(f"KB search returned {len(articles)} articles")
            return articles

    except httpx.TimeoutException:
        logger.warning("KB API timeout, returning empty")
        return []  # Graceful degradation (per NFR003)

    except httpx.HTTPStatusError as e:
        logger.error(f"KB API error: {e.response.status_code}")
        return []  # Graceful degradation
```

**Caching Strategy:**
- **Cache Key:** `kb_search:{tenant_id}:{hash(description)}`
- **TTL:** 1 hour (3600 seconds)
- **Rationale:** KB articles change infrequently, caching reduces API calls

**Error Handling:**
- **Timeout:** 10 seconds (per AC), fallback to empty list
- **API Failure:** Return empty list, log warning (graceful degradation)

---

### 5. Context Gathering: IP Address Cross-Reference (Story 2.7)

**Objective:** Extract IP addresses from ticket description and lookup system information.

**Implementation:**

```python
# src/services/ip_lookup.py
import re
from typing import List, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.database.models import SystemInventory

# IPv4 and IPv6 regex patterns
IPV4_PATTERN = r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'
IPV6_PATTERN = r'\b(?:[A-Fa-f0-9]{1,4}:){7}[A-Fa-f0-9]{1,4}\b'

async def extract_and_lookup_ips(
    session: AsyncSession,
    tenant_id: str,
    description: str
) -> List[Dict]:
    """
    Extract IP addresses from ticket description and lookup system info.

    Args:
        session: Async database session
        tenant_id: Tenant identifier for inventory lookup
        description: Ticket description containing IP addresses

    Returns:
        List of system information dictionaries
    """
    # Extract IP addresses using regex
    ipv4_matches = re.findall(IPV4_PATTERN, description)
    ipv6_matches = re.findall(IPV6_PATTERN, description)
    all_ips = set(ipv4_matches + ipv6_matches)

    if not all_ips:
        return []  # No IPs found, not an error

    # Query system_inventory table
    stmt = (
        select(SystemInventory)
        .where(SystemInventory.tenant_id == tenant_id)
        .where(SystemInventory.ip_address.in_(all_ips))
    )

    result = await session.execute(stmt)
    systems = result.scalars().all()

    return [
        {
            "ip_address": system.ip_address,
            "hostname": system.hostname,
            "role": system.role,
            "client": system.client,
            "location": system.location
        }
        for system in systems
    ]
```

**Schema (system_inventory table):**

```sql
CREATE TABLE system_inventory (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id VARCHAR(100) NOT NULL,
    ip_address INET NOT NULL,
    hostname VARCHAR(255),
    role VARCHAR(100),
    client VARCHAR(255),
    location VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT system_inventory_unique UNIQUE (tenant_id, ip_address)
);

CREATE INDEX idx_system_inventory_tenant ON system_inventory(tenant_id);
CREATE INDEX idx_system_inventory_ip ON system_inventory(ip_address);
```

---

### 6. Workflow Orchestration: LangGraph Integration (Story 2.8)

**Objective:** Use LangGraph to orchestrate context gathering nodes in parallel.

**LangGraph Workflow Implementation:**

```python
# src/workflows/enhancement_workflow.py
from langgraph.graph import StateGraph, END
from typing import TypedDict, List, Dict, Optional
from src.services.ticket_history_search import search_similar_tickets
from src.services.kb_search import search_knowledge_base
from src.services.ip_lookup import extract_and_lookup_ips
import logging

logger = logging.getLogger(__name__)

class WorkflowState(TypedDict):
    """State passed between LangGraph nodes."""
    tenant_id: str
    ticket_id: str
    description: str
    priority: str

    # Context gathered
    similar_tickets: Optional[List[Dict]]
    kb_articles: Optional[List[Dict]]
    ip_info: Optional[List[Dict]]

    # Final enhancement
    enhancement: Optional[str]

    # Error tracking
    errors: List[str]

async def ticket_search_node(state: WorkflowState, session) -> WorkflowState:
    """Node: Search similar tickets in ticket_history."""
    try:
        results = await search_similar_tickets(
            session,
            state["tenant_id"],
            state["description"],
            limit=5
        )
        state["similar_tickets"] = results
        logger.info(f"Ticket search: {len(results)} results")
    except Exception as e:
        logger.error(f"Ticket search failed: {e}")
        state["errors"].append(f"Ticket search error: {str(e)}")
        state["similar_tickets"] = []
    return state

async def kb_search_node(state: WorkflowState, kb_config) -> WorkflowState:
    """Node: Search knowledge base for articles."""
    try:
        results = await search_knowledge_base(
            state["tenant_id"],
            state["description"],
            kb_config["base_url"],
            kb_config["api_key"],
            limit=3
        )
        state["kb_articles"] = results
        logger.info(f"KB search: {len(results)} results")
    except Exception as e:
        logger.error(f"KB search failed: {e}")
        state["errors"].append(f"KB search error: {str(e)}")
        state["kb_articles"] = []
    return state

async def ip_lookup_node(state: WorkflowState, session) -> WorkflowState:
    """Node: Extract and lookup IP addresses."""
    try:
        results = await extract_and_lookup_ips(
            session,
            state["tenant_id"],
            state["description"]
        )
        state["ip_info"] = results
        logger.info(f"IP lookup: {len(results)} systems")
    except Exception as e:
        logger.error(f"IP lookup failed: {e}")
        state["errors"].append(f"IP lookup error: {str(e)}")
        state["ip_info"] = []
    return state

def build_enhancement_workflow():
    """
    Build LangGraph workflow for context gathering.

    Nodes execute in parallel, then aggregate results.
    """
    workflow = StateGraph(WorkflowState)

    # Add nodes
    workflow.add_node("ticket_search", ticket_search_node)
    workflow.add_node("kb_search", kb_search_node)
    workflow.add_node("ip_lookup", ip_lookup_node)

    # Set entry point (all nodes execute in parallel from start)
    workflow.set_entry_point("ticket_search")
    workflow.add_edge("ticket_search", END)

    workflow.set_entry_point("kb_search")
    workflow.add_edge("kb_search", END)

    workflow.set_entry_point("ip_lookup")
    workflow.add_edge("ip_lookup", END)

    return workflow.compile()

async def execute_context_gathering(
    tenant_id: str,
    ticket_id: str,
    description: str,
    priority: str,
    session,
    kb_config: Dict
) -> WorkflowState:
    """
    Execute LangGraph workflow to gather context.

    Returns WorkflowState with all gathered context.
    """
    workflow = build_enhancement_workflow()

    initial_state = WorkflowState(
        tenant_id=tenant_id,
        ticket_id=ticket_id,
        description=description,
        priority=priority,
        similar_tickets=None,
        kb_articles=None,
        ip_info=None,
        enhancement=None,
        errors=[]
    )

    # Execute workflow (parallel execution)
    result = await workflow.ainvoke(initial_state, {"session": session, "kb_config": kb_config})

    logger.info(f"Context gathering complete: {len(result['errors'])} errors")
    return result
```

**Parallel Execution Benefits:**
- **Sequential:** ticket_search (2s) + kb_search (5s) + ip_lookup (1s) = 8s
- **Parallel:** max(2s, 5s, 1s) = 5s
- **Latency Reduction:** ~40% faster

**Graceful Degradation:**
- Failed nodes don't block workflow (errors tracked in `state["errors"]`)
- Partial context acceptable (empty lists for failed nodes)

---

### 7. LLM Synthesis: OpenRouter Integration (Story 2.9)

**Objective:** Use OpenRouter API Gateway and GPT-4o-mini to synthesize enhancement from gathered context.

**OpenRouter Configuration:**

```python
# src/config.py (add to Settings)
class Settings(BaseSettings):
    # ... existing settings ...

    # OpenRouter API
    openrouter_api_key: str
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_site_url: str = "https://ai-agents.yourcompany.com"
    openrouter_app_name: str = "AI Agents Enhancement Platform"

    # LLM Configuration
    llm_model: str = "openai/gpt-4o-mini"
    llm_max_tokens: int = 1000  # Approximately 500 words
    llm_temperature: float = 0.3  # Consistent, focused output
    llm_timeout: int = 30  # 30 seconds

settings = Settings()
```

**System Prompt:**

```python
# src/prompts/enhancement_prompts.py

ENHANCEMENT_SYSTEM_PROMPT = """You are an AI assistant helping MSP technicians resolve IT incidents faster by analyzing gathered context and synthesizing actionable insights.

Your role:
- Analyze context from similar tickets, documentation, and system information
- Synthesize actionable insights and recommendations
- Provide clear next steps for troubleshooting

Guidelines:
- MAXIMUM 500 words (be concise!)
- Structure output with clear sections (see format below)
- Cite sources (e.g., "Similar ticket TKT-12345 resolved by...")
- Professional, helpful tone
- Focus on ACTIONABLE information, not theory
- If no context available for a section, briefly state "No information available" and move on

Output Format:
## Similar Tickets
[If found, summarize relevant past resolutions with ticket IDs]

## Relevant Documentation
[If found, key points from knowledge base with article titles/URLs]

## System Information
[If found, relevant server/IP details affecting this issue]

## Recommended Next Steps
[Actionable troubleshooting steps based on gathered context]

Constraints:
- DO NOT speculate beyond provided context
- DO NOT recommend actions outside technician's capability
- DO NOT include ticket metadata in output (ticket ID, priority already visible to technician)
"""

ENHANCEMENT_USER_TEMPLATE = """Ticket Description:
{description}

Priority: {priority}

---

Context Gathered:

### Similar Tickets Found:
{similar_tickets_summary}

### Knowledge Base Articles:
{kb_articles_summary}

### System Information:
{ip_info_summary}

---

Based on this context, provide your analysis and recommendations following the output format specified in your system prompt.
"""
```

**LLM Synthesis Function:**

```python
# src/services/llm_synthesis.py
from openai import AsyncOpenAI
from src.config import settings
from src.prompts.enhancement_prompts import ENHANCEMENT_SYSTEM_PROMPT, ENHANCEMENT_USER_TEMPLATE
from src.workflows.enhancement_workflow import WorkflowState
import logging

logger = logging.getLogger(__name__)

# Initialize OpenRouter client
client = AsyncOpenAI(
    base_url=settings.openrouter_base_url,
    api_key=settings.openrouter_api_key,
    default_headers={
        "HTTP-Referer": settings.openrouter_site_url,
        "X-Title": settings.openrouter_app_name
    }
)

def format_tickets(tickets: Optional[List[Dict]]) -> str:
    """Format similar tickets for prompt."""
    if not tickets:
        return "No similar tickets found."

    lines = []
    for ticket in tickets[:5]:
        lines.append(
            f"- Ticket {ticket['ticket_id']} (relevance: {ticket['relevance_score']:.2f}): "
            f"{ticket['description'][:100]}...\n"
            f"  Resolution: {ticket['resolution'][:200]}...\n"
            f"  Resolved: {ticket['resolved_date']}"
        )
    return "\n".join(lines)

def format_kb_articles(articles: Optional[List[Dict]]) -> str:
    """Format KB articles for prompt."""
    if not articles:
        return "No relevant documentation found."

    lines = []
    for article in articles[:3]:
        lines.append(
            f"- [{article['title']}]({article['url']}): {article['summary'][:200]}..."
        )
    return "\n".join(lines)

def format_ip_info(ip_info: Optional[List[Dict]]) -> str:
    """Format system information for prompt."""
    if not ip_info:
        return "No system information found."

    lines = []
    for system in ip_info:
        lines.append(
            f"- System: {system.get('hostname', 'Unknown')} ({system.get('ip_address', 'N/A')})\n"
            f"  Role: {system.get('role', 'Unknown')}, Client: {system.get('client', 'Unknown')}, "
            f"Location: {system.get('location', 'Unknown')}"
        )
    return "\n".join(lines)

def truncate_to_words(text: str, max_words: int) -> str:
    """Truncate text to maximum word count."""
    words = text.split()
    if len(words) <= max_words:
        return text
    return " ".join(words[:max_words]) + "...\n\n[Output truncated to 500-word limit]"

async def synthesize_enhancement(context: WorkflowState) -> str:
    """
    Use LLM to synthesize gathered context into enhancement.

    Args:
        context: WorkflowState containing all gathered context

    Returns:
        Enhancement text (markdown, max 500 words)
    """
    # Format context summaries
    user_prompt = ENHANCEMENT_USER_TEMPLATE.format(
        description=context["description"],
        priority=context["priority"],
        similar_tickets_summary=format_tickets(context.get("similar_tickets")),
        kb_articles_summary=format_kb_articles(context.get("kb_articles")),
        ip_info_summary=format_ip_info(context.get("ip_info"))
    )

    try:
        response = await client.chat.completions.create(
            model=settings.llm_model,
            messages=[
                {"role": "system", "content": ENHANCEMENT_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=settings.llm_max_tokens,
            temperature=settings.llm_temperature,
            timeout=settings.llm_timeout
        )

        enhancement = response.choices[0].message.content

        # Enforce 500-word limit (per FR013)
        word_count = len(enhancement.split())
        if word_count > 500:
            logger.warning(f"Enhancement exceeded 500 words ({word_count}), truncating")
            enhancement = truncate_to_words(enhancement, 500)

        # Log token usage for cost tracking
        logger.info(
            f"LLM synthesis complete: {response.usage.total_tokens} tokens, "
            f"{word_count} words"
        )

        return enhancement

    except Exception as e:
        logger.error(f"LLM synthesis failed: {e}")

        # Fallback: Return formatted context without synthesis (graceful degradation)
        fallback = "## Context Gathered\n\n"
        fallback += "### Similar Tickets\n" + format_tickets(context.get("similar_tickets")) + "\n\n"
        fallback += "### Knowledge Base\n" + format_kb_articles(context.get("kb_articles")) + "\n\n"
        fallback += "### System Information\n" + format_ip_info(context.get("ip_info")) + "\n\n"
        fallback += "_Note: AI synthesis unavailable, showing raw context._"

        return fallback
```

**Error Handling:**
- **Timeout:** 30 seconds (settings.llm_timeout)
- **API Failure:** Fallback to formatted context without synthesis
- **Token Tracking:** Log usage for cost monitoring

---

### 8. ServiceDesk Plus API Integration (Story 2.10)

**Objective:** Implement API client to post enhancement as note to ServiceDesk Plus ticket.

**Implementation:**

```python
# src/services/servicedesk_client.py
import httpx
from typing import Dict
from src.config import settings
import logging

logger = logging.getLogger(__name__)

async def update_ticket_with_enhancement(
    base_url: str,
    api_key: str,
    ticket_id: str,
    enhancement: str
) -> bool:
    """
    Post enhancement to ServiceDesk Plus ticket as note.

    API Endpoint: POST /api/v3/requests/{id}/notes

    Args:
        base_url: ServiceDesk Plus base URL (tenant-specific)
        api_key: API key for authentication
        ticket_id: Ticket ID to update
        enhancement: Enhancement text (HTML or Markdown)

    Returns:
        True if successful, False otherwise
    """
    url = f"{base_url}/api/v3/requests/{ticket_id}/notes"

    # Convert markdown to HTML (simple conversion for MVP)
    # TODO: Use proper markdown library (mistletoe, markdown2) in production
    enhancement_html = enhancement.replace("\n", "<br>")

    payload = {
        "note": {
            "description": enhancement_html,
            "show_to_requester": True,
            "mark_first_response": False,
            "add_to_linked_requests": False
        }
    }

    # Retry logic: 3 attempts with exponential backoff
    max_retries = 3
    retry_delays = [2, 4, 8]  # Exponential backoff in seconds

    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    url,
                    json=payload,
                    headers={"authtoken": api_key}
                )

                response.raise_for_status()

                logger.info(f"Ticket {ticket_id} updated successfully")
                return True

        except httpx.TimeoutException:
            logger.warning(f"Timeout updating ticket {ticket_id}, attempt {attempt + 1}/{max_retries}")
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delays[attempt])
                continue
            else:
                logger.error(f"Failed to update ticket {ticket_id} after {max_retries} attempts")
                return False

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                logger.error(f"Authentication failed for ticket {ticket_id} (invalid API key)")
                return False  # Don't retry on auth failure
            elif e.response.status_code == 404:
                logger.error(f"Ticket {ticket_id} not found")
                return False  # Don't retry on 404
            else:
                logger.warning(f"HTTP error {e.response.status_code} updating ticket {ticket_id}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delays[attempt])
                    continue
                else:
                    return False

        except Exception as e:
            logger.error(f"Unexpected error updating ticket {ticket_id}: {e}")
            return False

    return False
```

**Retry Strategy:**
- **Attempts:** 3 total
- **Backoff:** 2s, 4s, 8s (exponential)
- **No Retry:** 401 Unauthorized, 404 Not Found (permanent failures)

---

### 9. End-to-End Integration (Story 2.11)

**Objective:** Connect all components in complete enhancement workflow.

**Celery Task Integration:**

```python
# src/workers/tasks.py (update enhance_ticket task)
from src.workflows.enhancement_workflow import execute_context_gathering
from src.services.llm_synthesis import synthesize_enhancement
from src.services.servicedesk_client import update_ticket_with_enhancement
from src.database.session import async_session_maker
from src.database.models import EnhancementHistory
import logging

logger = logging.getLogger(__name__)

@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,  # 1 minute
    time_limit=120  # 2 minutes (per NFR001)
)
async def enhance_ticket(
    self,
    tenant_id: str,
    ticket_id: str,
    description: str,
    priority: str
):
    """
    Enhanced ticket processing task (Stories 2.5-2.11 integrated).

    Flow:
    1. Load tenant configuration
    2. Execute context gathering workflow (Stories 2.5-2.7, orchestrated by 2.8)
    3. Synthesize enhancement with LLM (Story 2.9)
    4. Update ServiceDesk Plus ticket (Story 2.10)
    5. Record result in enhancement_history
    """
    start_time = time.time()
    correlation_id = f"{tenant_id}:{ticket_id}:{int(start_time)}"

    logger.info(f"[{correlation_id}] Starting enhancement for ticket {ticket_id}")

    # Create enhancement_history record
    async with async_session_maker() as session:
        history = EnhancementHistory(
            tenant_id=tenant_id,
            ticket_id=ticket_id,
            status="pending",
            created_at=datetime.now()
        )
        session.add(history)
        await session.commit()
        history_id = history.id

    try:
        # 1. Load tenant configuration
        async with async_session_maker() as session:
            tenant = await get_tenant_config(session, tenant_id)
            if not tenant:
                raise ValueError(f"Tenant {tenant_id} not found")

        # 2. Execute context gathering (Stories 2.5-2.8)
        logger.info(f"[{correlation_id}] Starting context gathering")
        async with async_session_maker() as session:
            context = await execute_context_gathering(
                tenant_id=tenant_id,
                ticket_id=ticket_id,
                description=description,
                priority=priority,
                session=session,
                kb_config={
                    "base_url": tenant.kb_base_url,
                    "api_key": tenant.kb_api_key
                }
            )

        # Log gathered context summary
        logger.info(
            f"[{correlation_id}] Context gathered: "
            f"{len(context.get('similar_tickets', []))} tickets, "
            f"{len(context.get('kb_articles', []))} KB articles, "
            f"{len(context.get('ip_info', []))} systems"
        )

        # 3. Synthesize enhancement with LLM (Story 2.9)
        logger.info(f"[{correlation_id}] Starting LLM synthesis")
        enhancement = await synthesize_enhancement(context)

        # 4. Update ServiceDesk Plus ticket (Story 2.10)
        logger.info(f"[{correlation_id}] Updating ServiceDesk Plus ticket")
        success = await update_ticket_with_enhancement(
            base_url=tenant.servicedesk_url,
            api_key=tenant.servicedesk_api_key,
            ticket_id=ticket_id,
            enhancement=enhancement
        )

        if not success:
            raise Exception("Failed to update ServiceDesk Plus ticket")

        # 5. Record success in enhancement_history
        processing_time = int((time.time() - start_time) * 1000)  # milliseconds

        async with async_session_maker() as session:
            history = await session.get(EnhancementHistory, history_id)
            history.status = "completed"
            history.context_gathered = {
                "similar_tickets": context.get("similar_tickets"),
                "kb_articles": context.get("kb_articles"),
                "ip_info": context.get("ip_info"),
                "errors": context.get("errors", [])
            }
            history.llm_output = enhancement
            history.processing_time_ms = processing_time
            history.completed_at = datetime.now()
            await session.commit()

        logger.info(
            f"[{correlation_id}] Enhancement complete in {processing_time}ms"
        )

    except Exception as e:
        logger.error(f"[{correlation_id}] Enhancement failed: {e}")

        # Record failure in enhancement_history
        async with async_session_maker() as session:
            history = await session.get(EnhancementHistory, history_id)
            history.status = "failed"
            history.error_message = str(e)
            history.completed_at = datetime.now()
            await session.commit()

        # Retry task if retries remaining
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e)
        else:
            logger.error(f"[{correlation_id}] Max retries exceeded, giving up")
```

**End-to-End Flow Validation:**
- **Integration Test:** Webhook payload → enhancement posted to ServiceDesk Plus
- **Latency Target:** <60 seconds p95 (per NFR001)
- **Error Handling:** Failures logged with correlation ID, alertable

---

### 10. Comprehensive Testing (Story 2.12)

**Objective:** Achieve >80% code coverage with unit and integration tests.

**Test Structure:**

```
tests/
├── unit/
│   ├── test_ticket_history_search.py
│   ├── test_kb_search.py
│   ├── test_ip_lookup.py
│   ├── test_llm_synthesis.py
│   ├── test_servicedesk_client.py
│   └── test_enhancement_workflow.py
├── integration/
│   ├── test_end_to_end_enhancement.py
│   ├── test_bulk_ticket_import.py
│   └── test_resolved_ticket_webhook.py
└── fixtures/
    ├── mock_tickets.json
    ├── mock_kb_articles.json
    └── mock_llm_responses.json
```

**Example Unit Test (LLM Synthesis):**

```python
# tests/unit/test_llm_synthesis.py
import pytest
from unittest.mock import AsyncMock, patch
from src.services.llm_synthesis import synthesize_enhancement, format_tickets
from src.workflows.enhancement_workflow import WorkflowState

@pytest.fixture
def sample_context():
    return WorkflowState(
        tenant_id="test-tenant",
        ticket_id="TKT-12345",
        description="Server not responding at 192.168.1.100",
        priority="High",
        similar_tickets=[
            {
                "ticket_id": "TKT-11111",
                "description": "Server down",
                "resolution": "Restarted Apache service",
                "resolved_date": "2024-10-15T10:00:00",
                "relevance_score": 0.85
            }
        ],
        kb_articles=[
            {
                "title": "Troubleshooting Server Connectivity",
                "summary": "Check network, restart services",
                "url": "https://kb.example.com/article-123"
            }
        ],
        ip_info=[
            {
                "ip_address": "192.168.1.100",
                "hostname": "web-server-01",
                "role": "Web Server",
                "client": "Acme Corp",
                "location": "DC-1"
            }
        ],
        enhancement=None,
        errors=[]
    )

@pytest.mark.asyncio
async def test_format_tickets():
    """Test ticket formatting for prompt."""
    tickets = [
        {
            "ticket_id": "TKT-123",
            "description": "Test ticket description",
            "resolution": "Test resolution",
            "resolved_date": "2024-10-15T10:00:00",
            "relevance_score": 0.9
        }
    ]

    result = format_tickets(tickets)

    assert "TKT-123" in result
    assert "Test resolution" in result
    assert "0.90" in result  # Relevance score

@pytest.mark.asyncio
@patch("src.services.llm_synthesis.client")
async def test_synthesize_enhancement_success(mock_client, sample_context):
    """Test successful LLM synthesis."""
    # Mock OpenAI response
    mock_response = AsyncMock()
    mock_response.choices = [
        AsyncMock(message=AsyncMock(content="## Similar Tickets\n- TKT-11111: Restarted Apache\n\n## Recommended Next Steps\n1. Check network connectivity\n2. Restart services"))
    ]
    mock_response.usage = AsyncMock(total_tokens=350)
    mock_client.chat.completions.create.return_value = mock_response

    result = await synthesize_enhancement(sample_context)

    assert "Similar Tickets" in result
    assert "Recommended Next Steps" in result
    assert len(result.split()) <= 500  # Word limit

@pytest.mark.asyncio
@patch("src.services.llm_synthesis.client")
async def test_synthesize_enhancement_fallback(mock_client, sample_context):
    """Test fallback when LLM fails."""
    mock_client.chat.completions.create.side_effect = Exception("API error")

    result = await synthesize_enhancement(sample_context)

    # Should return formatted context without synthesis
    assert "Context Gathered" in result
    assert "TKT-11111" in result  # Ticket from context
    assert "AI synthesis unavailable" in result
```

**Integration Test (End-to-End):**

```python
# tests/integration/test_end_to_end_enhancement.py
import pytest
from httpx import AsyncClient
from src.main import app
from src.database.session import async_session_maker
from src.database.models import EnhancementHistory

@pytest.mark.asyncio
async def test_end_to_end_enhancement_workflow(test_db, mock_servicedesk_api):
    """
    Integration test: Webhook → Enhancement → ServiceDesk Plus update.

    This test validates the complete workflow from receiving a webhook
    to posting the enhancement back to ServiceDesk Plus.
    """
    # 1. Send webhook request
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/webhook/servicedesk",
            json={
                "tenant_id": "test-tenant",
                "ticket_id": "TKT-99999",
                "description": "Test issue description",
                "priority": "Medium"
            },
            headers={"X-ServiceDesk-Signature": "valid-signature"}
        )

    assert response.status_code == 202  # Accepted

    # 2. Wait for Celery task to complete (in test: run synchronously)
    await asyncio.sleep(5)  # Allow processing time

    # 3. Verify enhancement_history record
    async with async_session_maker() as session:
        history = await session.execute(
            select(EnhancementHistory).where(
                EnhancementHistory.ticket_id == "TKT-99999"
            )
        )
        record = history.scalar_one()

        assert record.status == "completed"
        assert record.llm_output is not None
        assert record.processing_time_ms < 60000  # <60s

    # 4. Verify ServiceDesk Plus API called
    assert mock_servicedesk_api.called
    assert mock_servicedesk_api.call_args[0][0] == "TKT-99999"
```

**Performance Benchmarks (Story 2.12 AC #5):**

```python
# tests/performance/test_benchmarks.py
import pytest
import time

@pytest.mark.benchmark
async def test_ticket_search_performance(test_db):
    """Benchmark: Ticket search <2 seconds for 10K database."""
    # Populate database with 10,000 tickets
    await populate_ticket_history(test_db, count=10000)

    start = time.time()
    results = await search_similar_tickets(
        test_db,
        tenant_id="test-tenant",
        description="Server connectivity issue",
        limit=5
    )
    duration = time.time() - start

    assert duration < 2.0  # <2 seconds (per AC)
    assert len(results) > 0

@pytest.mark.benchmark
async def test_end_to_end_latency(test_system):
    """Benchmark: End-to-end enhancement <60s p95."""
    latencies = []

    for _ in range(100):
        start = time.time()
        await trigger_enhancement(test_system, ticket_id=f"TKT-{_}")
        duration = time.time() - start
        latencies.append(duration)

    p95 = sorted(latencies)[94]  # 95th percentile

    assert p95 < 60.0  # <60s p95 (per NFR001)
```

---

## Technology Stack

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| **Database** | PostgreSQL | 17 | Ticket history, full-text search |
| **ORM** | SQLAlchemy | 2.0+ | Async database access |
| **Cache** | Redis | 7.x | KB results caching (1hr TTL) |
| **Task Queue** | Celery | 5.x | Async enhancement processing |
| **Workflow** | LangGraph | 1.0+ | Context gathering orchestration |
| **LLM Gateway** | OpenRouter | - | Multi-model API gateway |
| **LLM Model** | GPT-4o-mini | - | Cost-effective synthesis |
| **HTTP Client** | HTTPX | 0.25+ | Async ServiceDesk Plus, KB APIs |
| **Testing** | Pytest | 7.4+ | Unit, integration, performance tests |

---

## Performance Targets (from NFRs)

| Metric | Target | Validation Story |
|--------|--------|------------------|
| **End-to-end latency** | <120s max, <60s p95 | Story 2.11 |
| **Ticket search** | <2s for 10K database | Story 2.5 |
| **KB API timeout** | 10s | Story 2.6 |
| **LLM synthesis timeout** | 30s | Story 2.9 |
| **ServiceDesk Plus API timeout** | 30s | Story 2.10 |
| **Bulk import throughput** | 100 tickets/min | Story 2.5A |
| **Context gathering latency** | <30s (parallel execution) | Story 2.8 |

---

## Security Considerations

**Authentication & Authorization:**
- Webhook signature validation (Story 2.2, reused in 2.5B)
- ServiceDesk Plus API keys encrypted at rest (Epic 3 Story 3.3)
- Row-level security on all database queries (Epic 3 Story 3.1)

**Input Validation:**
- Pydantic models for all webhook payloads
- Maximum description length: 10,000 characters (Epic 3 Story 3.4)
- SQL injection prevention via SQLAlchemy parameterized queries
- IP address regex validation (Story 2.7)

**Data Privacy:**
- Tenant isolation via tenant_id filtering
- No cross-tenant data leakage in searches (validated in Epic 3 Story 3.8)
- LLM prompts contain only necessary context (no PII logging)

---

## Error Handling & Resilience

**Retry Strategies:**
- **Celery Task:** 3 retries, 60s backoff, 120s timeout
- **OpenRouter API:** 2 retries, exponential backoff (2s, 4s), 30s timeout
- **ServiceDesk Plus API:** 3 retries, exponential backoff (2s, 4s, 8s), 30s timeout
- **KB API:** No retry (10s timeout, fallback to empty)

**Graceful Degradation:**
- Failed context nodes → Continue with partial context
- LLM synthesis failure → Return formatted context without synthesis
- ServiceDesk Plus API failure → Log, retry, alert (Epic 4)

**Logging & Monitoring:**
- Structured logging (JSON) with correlation IDs
- Prometheus metrics (Epic 4): enhancement_duration_seconds, enhancement_success_rate
- Error tracking in enhancement_history table

---

## Implementation Sequence

**Week 1-2:** Context Gathering Foundation
1. Story 2.5: Ticket history search (3-5 days)
2. Story 2.5A: Bulk ticket import script (3-5 days)
3. Story 2.5B: Resolved ticket webhook (2-3 days)

**Week 3-4:** Context Gathering Expansion
4. Story 2.6: Knowledge base search (1 week)
5. Story 2.7: IP address lookup (1 week)

**Week 5-6:** Orchestration & Synthesis
6. Story 2.8: LangGraph orchestration (1-2 weeks)
7. Story 2.9A: OpenRouter client setup (3-5 days)
8. Story 2.9B: Prompt design (3-5 days)

**Week 7:** Synthesis & Integration
9. Story 2.9C: Context formatting (2-3 days)
10. Story 2.9D: LLM synthesis integration (3-5 days)
11. Story 2.10: ServiceDesk Plus API client (1 week)

**Week 8:** End-to-End & Testing
12. Story 2.11: End-to-end integration (1 week)
13. Story 2.12: Comprehensive testing (1 week)

**Total Estimated Duration:** 6-8 weeks

---

## Risks & Mitigations

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| OpenRouter API downtime | High | Low | Fallback to formatted context, retry logic |
| LLM synthesis exceeds 500 words | Medium | Medium | Enforce truncation, adjust temperature |
| Ticket history cold start (no data) | High | High | Story 2.5A bulk import addresses this |
| KB API slow/unavailable | Medium | Medium | 10s timeout, Redis caching, graceful degradation |
| ServiceDesk Plus API rate limits | Medium | Low | Rate limiting in bulk import (0.6s/request) |
| Full-text search performance | Medium | Low | Indexed FTS, rank threshold filtering |

---

## Testing Strategy

**Unit Tests (>80% coverage):**
- All context gathering functions (2.5-2.7)
- LangGraph workflow nodes (2.8)
- LLM synthesis with mocked responses (2.9)
- ServiceDesk Plus API client (2.10)

**Integration Tests:**
- End-to-end webhook → enhancement → ticket update
- Bulk ticket import with ServiceDesk Plus API
- Resolved ticket webhook storage

**Performance Tests:**
- Ticket search <2s benchmark (10K database)
- End-to-end latency <60s p95 (100 requests)
- Bulk import throughput 100 tickets/min

**Mock Data:**
- Fixtures for tickets, KB articles, LLM responses
- Reduces external API dependencies during testing
- Consistent test data for reproducibility

---

## Future Enhancements (Out of Scope for Epic 2)

- **Story 2.9 Sub-Story Split:** Break Story 2.9 into 2.9A-D for better tracking (recommended in gate check)
- **Monitoring Integration:** FR008 monitoring data retrieval (clarify in Story 2.8 or add Story 2.7B)
- **Advanced Caching:** Tenant config caching (5min TTL) from Epic 3 Story 3.2
- **Distributed Tracing:** OpenTelemetry spans for debugging (Epic 4 Story 4.6)
- **Admin UI:** Streamlit interface for enhancement history viewing (Epic 6 Story 6.4)
- **Plugin Architecture:** Jira support, multi-tool enhancement (Epic 7)

---

_This technical specification is a living document and will be updated as Stories 2.5-2.12 are implemented. Last updated: 2025-11-02_

**Generated by:** Winston (BMM Architect Agent)
**Workflow:** solutioning-gate-check → tech-spec generation
**References:**
- architecture.md (ADR-003, ADR-020)
- epics.md (Epic 2 stories 2.5-2.12)
- PRD.md (FR001-FR017, NFR001-NFR005)
