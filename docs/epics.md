# AI Agents - Epic Breakdown

**Author:** Ravi
**Date:** 2025-10-31
**Project Level:** 3
**Target Scale:** Complex integration - platform features, major integrations, architectural changes

---

## Overview

This document provides the detailed epic breakdown for AI Agents, expanding on the high-level epic list in the [PRD](./PRD.md).

Each epic includes:

- Expanded goal and value proposition
- Complete story breakdown with user stories
- Acceptance criteria for each story
- Story sequencing and dependencies

**Epic Sequencing Principles:**

- Epic 1 establishes foundational infrastructure and initial functionality
- Subsequent epics build progressively, each delivering significant end-to-end value
- Stories within epics are vertically sliced and sequentially ordered
- No forward dependencies - each story builds only on previous work

---

## Epic 1: Foundation & Infrastructure Setup

**Expanded Goal:**

Establish the foundational infrastructure for the AI enhancement platform, including project structure, containerization, data storage, message queuing, and deployment automation. This epic delivers a working local development environment and production-ready infrastructure that subsequent epics will build upon. By the end of this epic, the system can receive and store basic data, even though the enhancement logic isn't yet implemented.

---

**Story 1.1: Initialize Project Structure and Development Environment**

As a developer,
I want a well-organized project structure with Python dependencies managed,
So that I can start building features with a solid foundation.

**Acceptance Criteria:**
1. Project directory structure created following Python best practices (src/, tests/, docs/, docker/, k8s/)
2. Python 3.11+ virtual environment configured
3. Core dependencies installed (FastAPI, LangGraph, SQLAlchemy, Redis client, pytest)
4. requirements.txt and/or pyproject.toml file created
5. .gitignore configured for Python projects
6. README.md with initial setup instructions
7. All dependencies install successfully with `pip install -r requirements.txt`

**Prerequisites:** None (first story)

---

**Story 1.2: Create Docker Configuration for Local Development**

As a developer,
I want Docker containers for all infrastructure components,
So that I can run the entire stack locally without manual service installation.

**Acceptance Criteria:**
1. Dockerfile created for FastAPI application with multi-stage build
2. docker-compose.yml includes PostgreSQL, Redis, and FastAPI services
3. Environment variables configured via .env file (database credentials, Redis connection)
4. Volume mounts configured for local development hot-reload
5. All services start successfully with `docker-compose up`
6. Health checks configured for each service
7. Documentation updated with Docker setup instructions

**Prerequisites:** Story 1.1 (project structure exists)

---

**Story 1.3: Set Up PostgreSQL Database with Schema**

As a developer,
I want a PostgreSQL database with initial schema for tenant configuration and enhancement history,
So that I can store multi-tenant data with proper isolation.

**Acceptance Criteria:**
1. PostgreSQL database initialized in Docker container
2. Database migration tool configured (Alembic or similar)
3. Initial schema created with tables: `tenant_configs`, `enhancement_history`
4. Row-level security (RLS) policies defined for tenant isolation
5. Database connection pooling configured in application
6. Database health check endpoint returns 200 OK
7. Sample data can be inserted and queried successfully
8. Migration can be rolled back and re-applied

**Prerequisites:** Story 1.2 (Docker environment running)

---

**Story 1.4: Configure Redis Queue for Message Processing**

As a developer,
I want a Redis instance configured for job queuing,
So that webhook requests can be buffered and processed asynchronously.

**Acceptance Criteria:**
1. Redis container running in docker-compose
2. Redis connection configured in FastAPI application
3. Basic queue operations tested (push, pop, peek)
4. Redis persistence configured (AOF or RDB)
5. Redis health check endpoint returns connection status
6. Queue depth can be monitored via Redis CLI
7. Test demonstrates message durability across container restarts

**Prerequisites:** Story 1.2 (Docker environment running)

---

**Story 1.5: Implement Celery Worker Setup**

As a developer,
I want Celery workers configured to process jobs from Redis queue,
So that enhancement jobs can be processed asynchronously with proper concurrency.

**Acceptance Criteria:**
1. Celery installed and configured with Redis as broker
2. Worker process starts successfully (`celery -A app worker`)
3. Basic test task executes successfully and returns result
4. Worker configuration includes concurrency settings (4-8 workers)
5. Worker container added to docker-compose
6. Worker logs visible and structured
7. Task retry logic configured with exponential backoff
8. Worker health monitoring endpoint available

**Prerequisites:** Story 1.4 (Redis queue configured)

---

**Story 1.6: Create Kubernetes Deployment Manifests**

As a DevOps engineer,
I want Kubernetes manifests for all components,
So that the platform can be deployed to production clusters.

**Acceptance Criteria:**
1. Kubernetes namespace manifest created (`ai-agents`)
2. Deployment manifests for FastAPI, Celery workers, PostgreSQL, Redis
3. Service manifests for inter-pod communication
4. ConfigMap manifest for non-sensitive configuration
5. Secret manifest template for sensitive credentials
6. Resource limits and requests defined for each deployment
7. All manifests apply successfully to local Kubernetes cluster (minikube or kind)
8. Pods start and pass readiness checks

**Prerequisites:** Stories 1.3, 1.4, 1.5 (all components containerized and tested)

---

**Story 1.7: Set Up CI/CD Pipeline with GitHub Actions**

As a developer,
I want automated testing and deployment pipeline,
So that code changes are validated and can be deployed consistently.

**Acceptance Criteria:**
1. GitHub Actions workflow file created (`.github/workflows/ci.yml`)
2. Workflow runs on pull requests and main branch commits
3. Automated steps: linting (black, flake8), unit tests (pytest), Docker build
4. Test coverage report generated and displayed
5. Docker images pushed to container registry on main branch
6. Workflow status badge added to README
7. Pipeline completes successfully for test commit

**Prerequisites:** Stories 1.1, 1.2 (project structure and Docker configuration exist)

---

**Story 1.8: Create Local Development and Deployment Documentation**

As a new developer,
I want comprehensive documentation for setting up and deploying the platform,
So that I can get the environment running without extensive troubleshooting.

**Acceptance Criteria:**
1. README.md includes: prerequisites, local setup steps, running tests, Docker commands
2. docs/deployment.md created with Kubernetes deployment instructions
3. docs/architecture.md created with system overview diagram
4. Environment variable documentation with examples
5. Troubleshooting section for common issues
6. Contributing guidelines documented
7. New developer can follow docs and get system running in <30 minutes

**Prerequisites:** Stories 1.1-1.7 (all infrastructure components complete)

---

## Epic 2: Core Enhancement Agent

**Expanded Goal:**

Build the complete end-to-end enhancement workflow, from receiving ServiceDesk Plus webhooks to updating tickets with AI-generated context. This epic delivers the core value proposition of the platform: automated ticket enhancement with relevant historical, documentation, and system context. By the end of this epic, a single enhancement agent can process real tickets and provide valuable context to technicians.

---

**Story 2.1: Implement FastAPI Webhook Receiver Endpoint**

As a ServiceDesk Plus instance,
I want to send webhook notifications when tickets are created,
So that the enhancement agent can be triggered automatically.

**Acceptance Criteria:**
1. POST endpoint created at `/webhook/servicedesk` accepting JSON payload
2. Endpoint extracts ticket ID, description, priority, client identifier from payload
3. Basic input validation using Pydantic models
4. Endpoint returns 202 Accepted immediately (async processing)
5. Request logged with timestamp and payload summary
6. Unit tests cover valid payload, invalid payload, missing fields
7. Endpoint callable via curl/Postman with sample payload

**Prerequisites:** Epic 1 complete (FastAPI infrastructure running)

---

**Story 2.2: Implement Webhook Signature Validation**

As a security engineer,
I want webhook requests validated using HMAC signatures,
So that only authentic ServiceDesk Plus requests are processed.

**Acceptance Criteria:**
1. Signature validation middleware added to webhook endpoint
2. HMAC-SHA256 signature computed from payload + shared secret
3. Signature compared with header value (e.g., `X-ServiceDesk-Signature`)
4. Invalid signatures rejected with 401 Unauthorized
5. Shared secret loaded from environment variable/Kubernetes secret
6. Validation logic unit tested with valid and invalid signatures
7. Documentation explains signature generation for ServiceDesk Plus configuration

**Prerequisites:** Story 2.1 (webhook endpoint exists)

---

**Story 2.3: Queue Enhancement Jobs to Redis**

As a webhook receiver,
I want to push validated ticket enhancement requests to Redis queue,
So that work is buffered and processed asynchronously by workers.

**Acceptance Criteria:**
1. After validation, ticket data serialized and pushed to Redis queue
2. Queue key follows naming convention: `enhancement:queue`
3. Job payload includes: ticket_id, description, priority, tenant_id, timestamp
4. Job ID generated and returned in webhook response for tracking
5. Queue push failures logged and return 503 Service Unavailable
6. Redis connection pooling configured for performance
7. Unit tests verify job queuing with mock Redis

**Prerequisites:** Story 2.2 (webhook validation complete)

---

**Story 2.4: Create Celery Task for Enhancement Processing**

As a Celery worker,
I want a dedicated task to process enhancement jobs from the queue,
So that tickets can be enhanced asynchronously.

**Acceptance Criteria:**
1. Celery task `enhance_ticket` created accepting job payload
2. Task pulls job from Redis queue
3. Task logs start, completion, and any errors
4. Task timeout set to 120 seconds (per NFR001)
5. Failed tasks retry up to 3 times with exponential backoff
6. Task updates enhancement_history table with status (pending, completed, failed)
7. Unit tests verify task execution with mock data

**Prerequisites:** Story 2.3 (jobs queued to Redis)

---

**Story 2.5: Implement Ticket History Search (Context Gathering)**

As an enhancement agent,
I want to search past tickets for similar issues,
So that technicians can see how similar problems were resolved.

**Acceptance Criteria:**
1. Function created to search ticket_history table by keywords from description
2. Search uses PostgreSQL full-text search or similarity matching
3. Results filtered by tenant_id for data isolation
4. Returns top 5 most similar tickets with: ticket_id, description, resolution, resolved_date
5. Search respects row-level security policies
6. Empty results handled gracefully (returns empty list)
7. Unit tests verify search with sample ticket data
8. Performance: Search completes in <2 seconds for 10,000 ticket database

**Prerequisites:** Story 1.3 (database schema with ticket_history table)

---

**Story 2.5A: Populate Ticket History from ServiceDesk Plus**

As a platform operator,
I want to bulk import historical tickets from ServiceDesk Plus during tenant onboarding,
So that the enhancement agent has context data available from day one.

**Acceptance Criteria:**
1. Python script created: `scripts/import_tickets.py --tenant-id=X --days=90`
2. Script fetches closed/resolved tickets from ServiceDesk Plus API
3. Uses pagination (100 tickets per page) for large datasets
4. Stores required fields: tenant_id, ticket_id, description, resolution, resolved_date, tags, source='bulk_import', ingested_at
5. Progress tracking: Logs "Imported 1000/5000 tickets (20%)" every 100 tickets
6. Error handling: Skip invalid tickets, log errors, continue processing
7. Idempotent: UNIQUE constraint on (tenant_id, ticket_id) prevents duplicates
8. Performance: Processes ~100 tickets/minute (target: 10,000 tickets in <2 hours)
9. Accepts parameters: --start-date, --end-date, --days (default: 90)
10. Exit codes: 0 on success, non-zero on failure (for automation)

**Prerequisites:** Story 1.3 (ticket_history table with source, ingested_at columns)

---

**Story 2.5B: Store Resolved Tickets Automatically**

As an enhancement agent,
I want resolved tickets automatically stored in ticket_history with provenance tracking,
So that future enhancements can reference recent resolutions and operators can monitor data health.

**Acceptance Criteria:**
1. FastAPI endpoint: `POST /webhook/servicedesk/resolved`
2. Accepts webhook payload when ticket status → "Resolved" or "Closed"
3. Pydantic schema validates: ticket_id, description, resolution, resolved_date, tenant_id
4. Webhook signature validation (reuse Story 2.2 validation logic)
5. Inserts with provenance: source='webhook_resolved', ingested_at=NOW()
6. Returns 202 Accepted immediately (async storage via Celery)
7. UPSERT logic: ON CONFLICT (tenant_id, ticket_id) DO UPDATE SET resolution, source, ingested_at
8. Error logging includes: tenant_id, ticket_id, source, error message
9. Prometheus metric: `ticket_history_stored_total{tenant_id, source, status}`
10. Performance: <500ms p95 latency for webhook response

**Prerequisites:** Story 2.2 (webhook validation), Story 2.4 (Celery patterns)

---

**Story 2.6: Implement Documentation and Knowledge Base Search**

As an enhancement agent,
I want to search knowledge base articles and documentation,
So that technicians receive relevant troubleshooting guides.

**Acceptance Criteria:**
1. Function created to search documentation table/external KB API
2. Search uses keywords extracted from ticket description
3. Returns top 3 relevant articles with: title, summary, URL
4. Handles KB API unavailability gracefully (returns empty, logs warning)
5. Results cached in Redis for 1 hour to reduce API calls
6. Timeout set to 10 seconds with fallback to cached results
7. Unit tests with mocked KB API responses

**Prerequisites:** Story 2.5 (context gathering pattern established)

---

**Story 2.7: Implement IP Address Cross-Reference**

As an enhancement agent,
I want to identify and cross-reference IP addresses mentioned in tickets,
So that technicians know which systems are affected.

**Acceptance Criteria:**
1. Function extracts IP addresses from ticket description using regex
2. Queries system inventory table for matching IPs
3. Returns system details: hostname, role, client, location
4. Handles multiple IPs in single ticket
5. No match returns empty (not an error)
6. IPv4 and IPv6 patterns both supported
7. Unit tests verify IP extraction and lookup

**Prerequisites:** Story 2.5 (context gathering pattern established)

---

**Story 2.8: Integrate LangGraph Workflow Orchestration**

As an enhancement agent,
I want to orchestrate context gathering using LangGraph,
So that searches run concurrently and results are combined efficiently.

**Acceptance Criteria:**
1. LangGraph workflow defined with nodes: ticket_search, doc_search, ip_search
2. Nodes execute concurrently for performance
3. Workflow aggregates results from all nodes
4. Failed nodes don't block workflow (partial results acceptable)
5. Workflow state persisted for debugging
6. Workflow execution time logged
7. Unit tests verify concurrent execution and result aggregation

**Prerequisites:** Stories 2.5, 2.6, 2.7 (all context gathering functions implemented)

---

**Story 2.9: Implement LLM Synthesis with OpenRouter Agent Configuration**

As an enhancement agent,
I want to use LLM to analyze gathered context and generate actionable insights,
So that technicians receive synthesized recommendations, not just raw data.

**Acceptance Criteria:**
1. OpenRouter API client configured with API key from environment
2. System prompt defined: Agent role, behavior guidelines, output format, constraints
3. Prompt template created: ticket description + gathered context → structured enhancement
4. LLM output formatted with sections: Similar Tickets, Documentation, System Info, Recommendations
5. Output limited to 500 words maximum (per FR013)
6. API timeout set to 30 seconds with retry logic
7. Costs tracked per API call (token usage logged)
8. Unit tests with mocked OpenRouter responses
9. Error handling for API failures (fallback to basic context without LLM synthesis)

**Implementation Details:**

### Agent Configuration & System Prompt

**Context:** LangGraph (Story 2.8) is a **workflow orchestrator** (manages state, nodes, edges), not an **agent framework** (system prompts, tools). Agent configuration belongs in the **synthesis node** where the LLM is invoked.

**System Prompt:**
```python
ENHANCEMENT_SYSTEM_PROMPT = """
You are an AI assistant helping MSP technicians resolve IT incidents faster.

Your role:
- Analyze gathered context (similar tickets, documentation, system info)
- Synthesize actionable insights
- Provide clear next steps

Guidelines:
- Maximum 500 words (concise!)
- Structure output with clear sections
- Cite sources (e.g., "Similar ticket TKT-123 resolved by...")
- Professional, helpful tone
- Focus on ACTIONABLE information, not theory

Output Format:
## Similar Tickets
[If found, summarize relevant past resolutions]

## Relevant Documentation
[If found, key points from knowledge base]

## System Information
[If found, relevant server/IP details]

## Recommended Next Steps
[Actionable troubleshooting steps based on context]
"""
```

**Prompt Template:**
```python
ENHANCEMENT_TEMPLATE = """
Ticket ID: {ticket_id}
Description: {description}
Priority: {priority}

Context Gathered:

### Similar Tickets Found:
{similar_tickets_summary}

### Knowledge Base Articles:
{kb_articles_summary}

### System Information:
{ip_info_summary}

### Monitoring Data:
{monitoring_data_summary}

Based on this context, provide your analysis and recommendations.
"""
```

**OpenRouter Client:**
```python
from openai import AsyncOpenAI
from src.config import settings

client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=settings.openrouter_api_key,
    default_headers={
        "HTTP-Referer": settings.openrouter_site_url,
        "X-Title": settings.openrouter_app_name
    }
)
```

**Synthesis Function:**
```python
async def synthesize_enhancement(context: WorkflowState) -> str:
    """Use LLM to synthesize gathered context into enhancement."""

    # Format context summaries
    prompt = ENHANCEMENT_TEMPLATE.format(
        ticket_id=context["ticket_id"],
        description=context["description"],
        priority=context["priority"],
        similar_tickets_summary=format_tickets(context["similar_tickets"]),
        kb_articles_summary=format_docs(context["kb_articles"]),
        ip_info_summary=format_ip(context["ip_info"]),
        monitoring_data_summary=format_monitoring(context["monitoring_data"])
    )

    try:
        response = await client.chat.completions.create(
            model="openai/gpt-4o-mini",
            messages=[
                {"role": "system", "content": ENHANCEMENT_SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1000,
            temperature=0.3
        )

        enhancement = response.choices[0].message.content

        # Enforce 500-word limit
        if len(enhancement.split()) > 500:
            logger.warning(f"Enhancement exceeded 500 words, truncating")
            enhancement = truncate_to_words(enhancement, 500)

        return enhancement

    except Exception as e:
        logger.error(f"LLM synthesis failed: {e}")
        raise SynthesisError(f"Failed to generate enhancement: {str(e)}")
```

**Context Formatting Helpers:**
```python
def format_tickets(tickets: Optional[List[Dict]]) -> str:
    if not tickets:
        return "No similar tickets found."
    lines = []
    for ticket in tickets[:5]:
        lines.append(
            f"- Ticket {ticket['ticket_id']}: {ticket['description'][:100]}... "
            f"(Resolved: {ticket['resolved_date']})"
        )
    return "\n".join(lines)

def format_docs(docs: Optional[List[Dict]]) -> str:
    if not docs:
        return "No relevant documentation found."
    lines = []
    for doc in docs[:3]:
        lines.append(f"- {doc['title']}: {doc['summary'][:200]}...")
    return "\n".join(lines)

def format_ip(ip_info: Optional[Dict]) -> str:
    if not ip_info:
        return "No system information found."
    return f"System: {ip_info.get('hostname', 'Unknown')} ({ip_info.get('ip', 'N/A')})\n" \
           f"Role: {ip_info.get('role', 'Unknown')}\n" \
           f"Client: {ip_info.get('client', 'Unknown')}"

def format_monitoring(monitoring: Optional[Dict]) -> str:
    if not monitoring:
        return "No monitoring data available."
    return f"Status: {monitoring.get('status', 'Unknown')}\n" \
           f"Recent Alerts: {len(monitoring.get('alerts', []))}"
```

**Integration with Story 2.8:**
- Story 2.8 LangGraph workflow produces: `WorkflowState` (with gathered context)
- Story 2.9 `synthesize_enhancement(context: WorkflowState)` consumes it
- Returns: enhancement string → Story 2.10 posts to ServiceDesk Plus

**Prerequisites:** Story 2.8 (context gathered and aggregated)

---

**Story 2.10: Implement ServiceDesk Plus API Integration for Ticket Updates**

As an enhancement agent,
I want to update tickets in ServiceDesk Plus via API,
So that technicians see enhancements within their existing workflow.

**Acceptance Criteria:**
1. ServiceDesk Plus API client configured (base URL, API key from tenant config)
2. Function created to add work note/comment to ticket
3. Enhancement content formatted as HTML or Markdown (configurable)
4. API retry logic: 3 attempts with exponential backoff
5. API failures logged with ticket_id and error details
6. Success updates enhancement_history table with "completed" status
7. Unit tests with mocked API responses (success, timeout, 401, 500)

**Prerequisites:** Story 2.9 (enhancement content generated)

---

**Story 2.11: End-to-End Enhancement Workflow Integration**

As a system integrator,
I want all components connected in working end-to-end flow,
So that a webhook triggers complete ticket enhancement.

**Acceptance Criteria:**
1. Webhook → Queue → Worker → Context Gathering → LLM → API Update pipeline functional
2. Integration test with sample webhook payload completes successfully
3. Test ticket updated in ServiceDesk Plus (or mock) with enhancement
4. All intermediate steps logged with correlation ID
5. Performance: End-to-end latency <60 seconds (p95 per NFR001)
6. Failed enhancements logged and alertable
7. Smoke test can be run on-demand for validation

**Prerequisites:** Stories 2.1-2.10 (all enhancement components implemented)

---

**Story 2.12: Create Unit and Integration Tests for Enhancement Pipeline**

As a QA engineer,
I want comprehensive test coverage for the enhancement pipeline,
So that changes don't break core functionality.

**Acceptance Criteria:**
1. Unit tests for each component achieve >80% code coverage
2. Integration tests cover happy path and error scenarios
3. Mock data fixtures created for tickets, context, LLM responses
4. Tests run in CI pipeline and block merges on failure
5. Performance benchmarks established (baseline latency, throughput)
6. Test documentation explains how to run and add new tests
7. All tests pass successfully

**Prerequisites:** Story 2.11 (end-to-end flow complete)

---

## Epic 3: Multi-Tenancy & Security

**Expanded Goal:**

Implement robust tenant isolation, security controls, and configuration management to make the platform production-ready for multiple MSP clients. This epic ensures that client data never leaks across tenant boundaries, credentials are securely managed, and malicious input is prevented. By the end of this epic, the platform can safely serve multiple clients simultaneously with complete data isolation.

---

**Story 3.1: Implement Row-Level Security in PostgreSQL**

As a database administrator,
I want row-level security policies enforced on all tenant data tables,
So that queries automatically filter by tenant_id without application-level checks.

**Acceptance Criteria:**
1. RLS policies created for tables: tenant_configs, enhancement_history, ticket_history
2. Policies enforce: users only see rows matching their tenant_id
3. Database roles configured: app_user (limited access), admin (full access)
4. Application connects with app_user role
5. Integration tests verify tenant isolation (queries from tenant A never return tenant B data)
6. RLS migration script created and tested
7. Documentation explains RLS configuration and testing

**Prerequisites:** Story 1.3 (database schema exists)

---

**Story 3.2: Create Tenant Configuration Management System**

As an operations engineer,
I want tenant-specific configuration stored and loaded per request,
So that each client can have unique ServiceDesk Plus credentials and preferences.

**Acceptance Criteria:**
1. tenant_configs table includes: tenant_id, servicedesk_url, api_key, enhancement_prefs (JSON)
2. Configuration loader retrieves tenant config by tenant_id
3. Tenant ID extracted from webhook payload or authentication token
4. Config cached in Redis with TTL (5 minutes) for performance
5. Missing tenant config returns 404 with clear error message
6. Configuration CRUD API endpoints created (admin only)
7. Unit tests verify config loading and caching

**Prerequisites:** Story 3.1 (RLS policies ensure tenant isolation)

---

**Story 3.3: Implement Secrets Management with Kubernetes Secrets**

As a security engineer,
I want sensitive credentials encrypted at rest and injected at runtime,
So that API keys and passwords are never stored in plain text.

**Acceptance Criteria:**
1. Kubernetes Secret manifests created for: database credentials, Redis password, OpenAI API key
2. Secrets mounted as environment variables or volume files in pods
3. Application reads secrets from environment at startup
4. Secret rotation procedure documented
5. No secrets committed to git repository (.gitignore verification)
6. Local development uses .env file (git-ignored), production uses K8s secrets
7. Secrets validator ensures required values present at startup

**Prerequisites:** Story 1.6 (Kubernetes manifests exist)

---

**Story 3.4: Implement Input Validation and Sanitization**

As a security engineer,
I want all webhook and API inputs validated and sanitized,
So that injection attacks and malformed data are prevented.

**Acceptance Criteria:**
1. Pydantic models enforce strict typing for all input fields
2. String inputs sanitized to prevent SQL injection, XSS
3. Input length limits enforced (max 10,000 chars for ticket description)
4. Invalid input returns 400 Bad Request with validation errors
5. Special characters in ticket descriptions handled safely
6. Unit tests cover: valid input, invalid types, oversized input, injection attempts
7. Security scanning tool (e.g., bandit) integrated into CI pipeline

**Prerequisites:** Story 2.1 (webhook endpoint receives input)

---

**Story 3.5: Implement Webhook Signature Validation with Multiple Tenants**

As a platform operator,
I want each tenant to have unique webhook signing secrets,
So that tenant A cannot spoof webhooks for tenant B.

**Acceptance Criteria:**
1. Webhook signing secret stored per tenant in tenant_configs
2. Signature validation uses tenant-specific secret
3. Tenant identified from webhook payload before signature check
4. Invalid signatures return 401 with logged security event
5. Signature replay attack prevented (timestamp validation)
6. Rate limiting added (max 100 webhooks/min per tenant)
7. Security tests verify cross-tenant spoofing prevention

**Prerequisites:** Stories 2.2 (signature validation), 3.2 (tenant configuration)

---

**Story 3.6: Create Kubernetes Namespaces for Tenant Isolation**

As a DevOps engineer,
I want each tenant deployed in separate Kubernetes namespace,
So that compute resources are isolated and failures don't cascade.

**Acceptance Criteria:**
1. Namespace creation script accepts tenant_id parameter
2. Each namespace includes: deployments, services, network policies
3. Network policies prevent cross-namespace communication (except shared DB/Redis)
4. Resource quotas set per namespace (CPU, memory limits)
5. RBAC policies restrict tenant namespaces to authorized operators
6. Namespace provisioning documented and automated
7. Test environment created with 2 tenant namespaces

**Prerequisites:** Story 1.6 (base Kubernetes manifests exist)

---

**Story 3.7: Implement Audit Logging for All Operations**

As a compliance officer,
I want all enhancement operations logged with tenant, user, timestamp,
So that we can audit access and troubleshoot issues.

**Acceptance Criteria:**
1. Structured logging configured (JSON format) with fields: timestamp, tenant_id, ticket_id, operation, user, status
2. All critical operations logged: webhook received, enhancement started, completed, failed, API calls
3. Logs include correlation IDs for tracing requests
4. Logs shipped to centralized logging (stdout for container log aggregation)
5. Log retention set to 90 days (per NFR005)
6. Sensitive data (API keys, PII) redacted from logs
7. Log query examples documented for common troubleshooting scenarios

**Prerequisites:** Story 2.11 (end-to-end flow exists to log)

---

**Story 3.8: Create Security Testing and Penetration Test Suite**

As a security engineer,
I want automated security tests validating isolation and input handling,
So that security regressions are caught before production.

**Acceptance Criteria:**
1. Security test suite created with scenarios: SQL injection, XSS, tenant isolation bypass, signature spoofing
2. Tests run in CI pipeline as part of PR checks
3. OWASP Top 10 vulnerabilities checked
4. Dependency scanning for known CVEs (e.g., using safety, snyk)
5. Security test results documented and tracked
6. Failed security tests block deployment
7. Quarterly penetration test procedure documented

**Prerequisites:** Stories 3.1-3.7 (all security features implemented)

---

## Epic 4: Monitoring & Operations

**Expanded Goal:**

Deploy a comprehensive observability stack that provides real-time visibility into agent performance, enables proactive alerting for failures, and supports debugging through distributed tracing. This epic ensures operators can answer "is it working?" at a glance and quickly diagnose issues when they occur. By the end of this epic, the platform has production-grade monitoring that meets NFR005 requirements.

---

**Story 4.1: Implement Prometheus Metrics Instrumentation**

As an SRE,
I want application metrics exposed in Prometheus format,
So that performance and health can be monitored in real-time.

**Acceptance Criteria:**
1. Prometheus client library integrated (prometheus_client for Python)
2. Metrics endpoint exposed at `/metrics` returning Prometheus format
3. Key metrics implemented: enhancement_requests_total, enhancement_duration_seconds, enhancement_success_rate, queue_depth, worker_active_count
4. Metrics labeled by: tenant_id, status (success/failure), operation_type
5. Metrics scraped successfully by Prometheus server (configured in docker-compose)
6. Metrics documented with descriptions and use cases
7. Unit tests verify metric incrementation

**Prerequisites:** Story 2.11 (enhancement pipeline operational)

---

**Story 4.2: Deploy Prometheus Server and Configure Scraping**

As a DevOps engineer,
I want Prometheus server deployed and scraping all application instances,
So that metrics are collected and stored for querying.

**Acceptance Criteria:**
1. Prometheus server deployed in Kubernetes (or docker-compose for local)
2. Scrape configs target all FastAPI and Celery worker pods
3. Scrape interval set to 15 seconds
4. Metrics retention configured for 30 days
5. Prometheus UI accessible and showing active targets
6. Sample PromQL queries documented (e.g., p95 latency, error rate)
7. Prometheus health check endpoint returns 200 OK

**Prerequisites:** Story 4.1 (metrics exposed)

---

**Story 4.3: Create Grafana Dashboards for Real-Time Monitoring**

As an operations engineer,
I want visual dashboards showing system health and performance,
So that I can monitor the platform without running queries manually.

**Acceptance Criteria:**
1. Grafana deployed and connected to Prometheus data source
2. Main dashboard created with panels: Success Rate (gauge), Queue Depth (graph), p95 Latency (graph), Error Rate by Tenant (table), Active Workers (stat)
3. Dashboard auto-refreshes every 30 seconds
4. Time range selector allows viewing last 1h, 6h, 24h, 7d
5. Dashboard exported as JSON and version-controlled
6. Dashboard accessible via browser with authentication
7. Screenshots and usage guide added to documentation

**Prerequisites:** Story 4.2 (Prometheus collecting metrics)

---

**Story 4.4: Configure Alerting Rules in Prometheus**

As an SRE,
I want automated alerts for critical failures,
So that I'm notified when the system degrades or fails.

**Acceptance Criteria:**
1. Alert rules configured for: EnhancementSuccessRateLow (<95% for 10 min), QueueDepthHigh (>100 jobs for 5 min), WorkerDown (0 active workers), HighLatency (p95 >120s for 5 min)
2. Alerts include labels: severity (warning/critical), tenant_id (if applicable)
3. Alert annotations provide context and troubleshooting links
4. Alerts tested by triggering conditions in test environment
5. Alert history viewable in Prometheus UI
6. Alert silencing procedure documented
7. Runbooks linked from alert annotations

**Prerequisites:** Story 4.2 (Prometheus server running)

---

**Story 4.5: Integrate Alertmanager for Alert Routing**

As an on-call engineer,
I want alerts delivered to Slack/PagerDuty/Email,
So that I'm notified immediately when action is needed.

**Acceptance Criteria:**
1. Alertmanager deployed and configured with Prometheus
2. Alerting channels configured: Slack (primary), email (secondary)
3. Alert routing rules: critical → Slack + PagerDuty, warning → Slack only
4. Alert grouping prevents notification spam (group by tenant, 5 min window)
5. Test alert successfully delivered to all channels
6. Alert resolution notifications sent when alerts clear
7. Alerting configuration documented and version-controlled

**Prerequisites:** Story 4.4 (alert rules configured)

---

**Story 4.6: Implement Distributed Tracing with OpenTelemetry**

As a developer,
I want request traces showing end-to-end flow through components,
So that I can debug performance bottlenecks and failed enhancements.

**Acceptance Criteria:**
1. OpenTelemetry instrumentation added to FastAPI and Celery
2. Traces include spans: webhook_received, job_queued, context_gathering, llm_call, ticket_update
3. Trace context propagated across service boundaries
4. Traces exported to Jaeger or similar backend
5. Sample trace viewable in Jaeger UI showing complete enhancement flow
6. Slow traces (>60s) automatically flagged
7. Tracing overhead <5% performance impact

**Prerequisites:** Story 2.11 (end-to-end flow to trace)

---

**Story 4.7: Create Operational Runbooks and Dashboards**

As an on-call engineer,
I want documented procedures for common operational tasks,
So that I can respond to issues quickly and consistently.

**Acceptance Criteria:**
1. Runbooks created for: High Queue Depth, Worker Failures, Database Connection Issues, API Timeout, Tenant Onboarding
2. Each runbook includes: symptoms, diagnosis steps, resolution steps, escalation path
3. Runbooks linked from Grafana dashboard and alert annotations
4. Operational dashboard created with quick actions: restart workers, clear queue, view recent errors
5. Runbooks tested by new team member during drill
6. Runbook repository maintained in docs/runbooks/
7. Quarterly runbook review process established

**Prerequisites:** Stories 4.1-4.6 (monitoring stack operational)

---

## Epic 5: Production Deployment & Validation

**Expanded Goal:**

Deploy the platform to production infrastructure, onboard the first real client, and validate system behavior with actual ticket data. This epic transitions from development to live operations, establishing baseline metrics, validating assumptions, and documenting lessons learned. By the end of this epic, the platform is serving real MSP clients with measurable improvements in ticket quality.

---

**Story 5.1: Provision Production Kubernetes Cluster**

As a DevOps engineer,
I want a production Kubernetes cluster configured for high availability,
So that the platform runs reliably for real clients.

**Acceptance Criteria:**
1. Production cluster provisioned on cloud provider (AWS EKS, GCP GKE, or Azure AKS)
2. Cluster configured with: 3+ nodes, auto-scaling enabled, network policies, RBAC
3. Managed database (RDS/Cloud SQL) configured with backups, encryption
4. Managed Redis (ElastiCache/MemoryStore) configured with persistence
5. Ingress controller deployed with TLS certificates (Let's Encrypt)
6. Cluster monitoring integrated with cloud provider observability
7. Infrastructure-as-code (Terraform/Pulumi) for reproducible deployment

**Prerequisites:** Epic 1 (infrastructure manifests created)

---

**Story 5.2: Deploy Application to Production Environment**

As a DevOps engineer,
I want all application components deployed to production cluster,
So that the platform is accessible to clients.

**Acceptance Criteria:**
1. All Kubernetes manifests applied to production cluster
2. Docker images pulled from container registry
3. Secrets configured with production credentials
4. All pods running and passing health checks
5. Database migrations applied successfully
6. Production webhook endpoint accessible via HTTPS
7. Smoke test confirms end-to-end functionality

**Prerequisites:** Story 5.1 (production cluster ready)

---

**Story 5.3: Onboard First Production Client**

As an account manager,
I want to onboard the first MSP client to the platform,
So that we can validate value proposition with real data.

**Acceptance Criteria:**
1. Client tenant created in tenant_configs table
2. ServiceDesk Plus webhook configured to call production endpoint
3. Client-specific configuration: API credentials, enhancement preferences, signing secret
4. Kubernetes namespace created for client isolation
5. Test webhook from client's ServiceDesk Plus successfully processed
6. Client's first real ticket enhanced and visible in their system
7. Client onboarding checklist documented for future clients

**Prerequisites:** Story 5.2 (production deployment complete)

---

**Story 5.4: Conduct Production Validation Testing**

As a QA engineer,
I want to validate system behavior with real client ticket data,
So that we confirm the platform works as designed in production conditions.

**Acceptance Criteria:**
1. Validation test plan executed: 10 real tickets processed successfully
2. Enhancement quality reviewed by client technicians (feedback collected)
3. Performance metrics measured: p50, p95, p99 latency, success rate
4. Error scenarios tested: KB timeout, API failure, partial context
5. Multi-tenant isolation validated (if multiple clients onboarded)
6. Monitoring alerts verified (trigger test alert, confirm notification)
7. Validation report documenting results, issues, recommendations

**Prerequisites:** Story 5.3 (client onboarded and processing tickets)

---

**Story 5.5: Establish Baseline Metrics and Success Criteria**

As a product manager,
I want baseline performance metrics documented,
So that we can measure improvement over time and justify ROI.

**Acceptance Criteria:**
1. Baseline metrics collected over 7-day period: average resolution time (before/after enhancement), ticket quality score, technician satisfaction
2. Success criteria defined: >20% reduction in research time, >4/5 technician satisfaction, >95% enhancement success rate
3. Metrics dashboard created for stakeholder visibility
4. Weekly metric review process established
5. Client feedback mechanism implemented (thumbs up/down on enhancements)
6. Improvement roadmap prioritized based on baseline findings
7. Metrics report shared with stakeholders

**Prerequisites:** Story 5.4 (validation testing complete)

---

**Story 5.6: Create Production Support Documentation and Handoff**

As a support engineer,
I want comprehensive documentation for operating the production system,
So that I can support clients and respond to incidents.

**Acceptance Criteria:**
1. Production support guide created: architecture overview, common issues, troubleshooting steps, escalation paths
2. Client support procedures documented: ticket investigation, configuration changes, performance tuning
3. Incident response playbook created: severity definitions, response SLAs, communication templates
4. On-call rotation schedule established
5. Support team trained on platform (knowledge transfer session conducted)
6. Support knowledge base seeded with FAQs and known issues
7. 24x7 support readiness validated with mock incident drill

**Prerequisites:** Story 5.5 (system stabilized and metrics established)

---

**Story 5.7: Conduct Post-MVP Retrospective and Plan Next Phase**

As a product team,
I want to reflect on MVP learnings and plan future iterations,
So that we build the right features based on real-world feedback.

**Acceptance Criteria:**
1. Retrospective session conducted with: what worked well, what didn't, what to improve
2. Client feedback synthesized and prioritized
3. Technical debt identified and prioritized for paydown
4. Future epic candidates evaluated: RCA agent, triage agent, admin portal, advanced monitoring
5. Roadmap for next 3-6 months drafted and socialized
6. Go/no-go decision for next phase documented with rationale
7. Retrospective findings shared with stakeholders

**Prerequisites:** Stories 5.1-5.6 (production system operational and validated)

---

## Epic 6: Admin UI & Configuration Management _(Added 2025-11-02 for MVP v1.5)_

**Goal:** Provide web-based admin interface for system visibility and configuration management

**Value:** Enable operations teams to manage tenant configurations, monitor system health, and view enhancement history without requiring kubectl access or manual YAML editing

**Estimated Complexity:** 6-8 stories, 2-3 weeks

**Target Milestone:** MVP v1.5 (after MVP v1.0 production validation)

**Technologies:** Streamlit 1.30+, Pandas, Plotly, SQLAlchemy (shared with FastAPI)

**Prerequisites:** Epic 1-5 complete (MVP v1.0 validated in production)

---

**Story 6.1: Set Up Streamlit Application Foundation**

As an operations engineer,
I want a basic Streamlit admin application deployed,
So that I can access a web-based interface for system management.

**Acceptance Criteria:**
1. Streamlit app created at src/admin/app.py with basic structure
2. Shared database connection established (reusing SQLAlchemy models from src/database/)
3. Multi-page navigation configured (Dashboard, Tenants, History pages)
4. Basic authentication implemented (Streamlit auth or Kubernetes Ingress basic auth)
5. Kubernetes deployment manifest created for Streamlit service (port 8501)
6. Streamlit service accessible via http://admin.ai-agents.local in local dev
7. README documentation updated with admin UI access instructions

**Prerequisites:** Epic 1 complete (database models and infrastructure in place)

---

**Story 6.2: Implement System Status Dashboard Page**

As an operations manager,
I want to see real-time system status and key metrics,
So that I can quickly assess system health at a glance.

**Acceptance Criteria:**
1. Dashboard page displays system status indicator (Healthy/Degraded/Down)
2. Key metrics displayed with st.metric: Queue depth, Success rate (24h), P95 latency, Active workers
3. Recent failures shown in expandable section (last 10 failed enhancements with error messages)
4. Redis connection status displayed
5. PostgreSQL connection status displayed
6. Auto-refresh implemented (configurable interval, default 30s)
7. Visual indicators use color coding (green=healthy, yellow=warning, red=critical)
8. Load time < 2 seconds for dashboard

**Prerequisites:** Story 6.1 (Streamlit foundation), Story 4.1 (Prometheus metrics available)

---

**Story 6.3: Create Tenant Management Interface**

As an operations engineer,
I want to view, add, edit, and delete tenant configurations,
So that I can onboard new clients without editing YAML files.

**Acceptance Criteria:**
1. Tenants page displays table of all tenants (name, tool_type, ServiceDesk URL, status, created_at)
2. Search/filter functionality for tenant list
3. "Add New Tenant" form with fields: name, tool_type (dropdown), servicedesk_url, api_key, webhook_secret (auto-generated), enhancement_preferences (checkboxes)
4. Form validation: required fields, URL format, duplicate tenant_id check
5. "Test Connection" button validates credentials against ServiceDesk Plus API before saving
6. Edit tenant form pre-populated with existing values (sensitive fields masked)
7. Delete tenant with confirmation dialog (soft delete, marks inactive)
8. Success/error messages displayed after each operation
9. Webhook URL displayed after tenant creation (for copying to ServiceDesk Plus config)

**Prerequisites:** Story 6.1 (Streamlit foundation), Story 3.2 (tenant_configs table)

---

**Story 6.4: Implement Enhancement History Viewer**

As an operations analyst,
I want to search and view enhancement history,
So that I can audit processing results and debug failures.

**Acceptance Criteria:**
1. History page displays enhancement_history table with pagination (50 rows per page)
2. Filters available: tenant_id (dropdown), status (pending/completed/failed), date range picker
3. Search box for ticket_id or description keyword search
4. Table columns: ticket_id, tenant, status, processing_time_ms, created_at, completed_at
5. Expandable row details show: context_gathered (formatted JSON), llm_output, error_message
6. Export to CSV button for filtered results
7. Performance: query returns < 5 seconds for 10K rows
8. Color-coded status badges (green=completed, red=failed, blue=pending)

**Prerequisites:** Story 6.1 (Streamlit foundation), Story 2.4 (enhancement_history table populated)

---

**Story 6.5: Add System Operations Controls**

As an operations engineer,
I want manual controls for system operations,
So that I can pause processing, clear queues, and perform maintenance tasks.

**Acceptance Criteria:**
1. Operations page with warning banner ("Caution: Manual operations can affect system behavior")
2. "Pause Processing" button stops Celery workers from picking up new jobs (sets Redis flag)
3. "Resume Processing" button clears pause flag
4. "Clear Queue" button with confirmation dialog removes all pending jobs from Redis
5. "Sync Tenant Configs" button reloads tenant configurations from database to Redis cache
6. "View Worker Health" section displays active workers with uptime and task counts
7. Operation logs displayed (last 20 operations with timestamp, user, action)
8. All operations require confirmation dialog with typed confirmation ("YES")
9. Audit log entry created for each operation

**Prerequisites:** Story 6.1 (Streamlit foundation), Story 1.5 (Celery workers operational)

---

**Story 6.6: Integrate Real-Time Metrics Display**

As an operations manager,
I want live charts showing system performance trends,
So that I can identify patterns and anomalies over time.

**Acceptance Criteria:**
1. Dashboard page includes time-series charts for: Queue depth, Success rate, Latency (P50/P95/P99)
2. Charts display last 24 hours by default with time range selector (1h, 6h, 24h, 7d)
3. Data fetched from Prometheus via HTTP API
4. Charts use Plotly for interactivity (hover tooltips, zoom, pan)
5. Chart refresh interval configurable (default 60s)
6. Loading spinner displayed while fetching data
7. Error handling for Prometheus unavailability (show cached data + warning)
8. Chart performance: renders < 2 seconds for 1000 data points

**Prerequisites:** Story 6.2 (Dashboard page), Story 4.2 (Prometheus deployed)

---

**Story 6.7: Add Worker Health and Resource Monitoring**

As an operations engineer,
I want to view worker health and resource utilization,
So that I can identify performance bottlenecks and scale appropriately.

**Acceptance Criteria:**
1. Workers page displays list of active Celery workers (hostname, uptime, active tasks, completed tasks)
2. Resource utilization metrics per worker: CPU%, Memory%, Task throughput (tasks/min)
3. Worker status indicator (active/idle/unresponsive)
4. "Restart Worker" button for individual worker (sends TERM signal via K8s API)
5. Worker logs viewer (last 100 lines, filterable by log level)
6. Alert threshold indicators (CPU >80% = yellow, >95% = red)
7. Historical worker performance chart (last 7 days average throughput)
8. Data refreshed every 30 seconds

**Prerequisites:** Story 6.1 (Streamlit foundation), Story 4.1 (worker metrics instrumented)

---

**Story 6.8: Create Admin UI Documentation and Deployment Guide**

As a developer or operations engineer,
I want comprehensive documentation for the admin UI,
So that I can deploy, configure, and use it effectively.

**Acceptance Criteria:**
1. docs/admin-ui-guide.md created with sections: Overview, Access, Features, Configuration
2. Local development setup documented (Streamlit dev server, database connection)
3. Kubernetes deployment instructions (manifests, ingress, authentication)
4. Screenshots/wireframes for each page (Dashboard, Tenants, History, Operations)
5. Troubleshooting section (common issues, logs locations, health checks)
6. Security considerations documented (authentication, authorization, secrets management)
7. Future enhancements section (OAuth, role-based access, audit logs UI)
8. README.md updated with link to admin UI guide

**Prerequisites:** Stories 6.1-6.7 (all admin UI features implemented)

---

## Epic 7: Plugin Architecture & Multi-Tool Support _(Added 2025-11-02 for MVP v2.0)_

**Goal:** Refactor to plugin-based architecture supporting multiple ticketing tools

**Value:** Enable market expansion by supporting Jira Service Management, Zendesk, and other ITSM tools without rewriting core enhancement logic

**Estimated Complexity:** 5-7 stories, 3-4 weeks

**Target Milestone:** MVP v2.0 (after MVP v1.5 validation)

**Technologies:** Python ABC, Plugin registry pattern

**Prerequisites:** Epic 1-6 complete (MVP v1.5 validated with Streamlit UI)

---

**Story 7.1: Design and Implement Plugin Base Interface**

As a platform engineer,
I want a standardized plugin interface for ticketing tools,
So that new tools can be integrated without modifying core enhancement logic.

**Acceptance Criteria:**
1. Abstract base class TicketingToolPlugin created at src/plugins/base.py
2. Four abstract methods defined: validate_webhook(), get_ticket(), update_ticket(), extract_metadata()
3. Type hints and docstrings for all methods (Google style)
4. TicketMetadata dataclass defined (tenant_id, ticket_id, description, priority, created_at)
5. Plugin interface documented with usage examples in docs/plugin-architecture.md
6. Unit tests for base class structure and method signatures
7. Mypy validation passes (all types correctly defined)

**Prerequisites:** Epic 6 complete (MVP v1.5 validated)

---

**Story 7.2: Implement Plugin Manager and Registry**

As a platform engineer,
I want a plugin manager that loads and routes requests to appropriate plugins,
So that the system can dynamically support multiple ticketing tools.

**Acceptance Criteria:**
1. PluginManager class created at src/plugins/registry.py
2. Plugin registration method: register_plugin(tool_type: str, plugin: TicketingToolPlugin)
3. Plugin retrieval method: get_plugin(tool_type: str) -> TicketingToolPlugin
4. Plugin discovery on startup (auto-load from src/plugins/*/ directories)
5. Error handling for missing plugins (raise PluginNotFoundError with clear message)
6. Plugin validation on registration (ensures implements all required methods)
7. Unit tests with mock plugins for registration and retrieval
8. Integration test: register 2 plugins, retrieve by tool_type

**Prerequisites:** Story 7.1 (plugin base interface defined)

---

**Story 7.3: Migrate ServiceDesk Plus to Plugin Architecture**

As a platform engineer,
I want existing ServiceDesk Plus integration extracted into a plugin,
So that it follows the same pattern as future tool integrations.

**Acceptance Criteria:**
1. ServiceDesk Plus plugin created at src/plugins/servicedesk_plus/plugin.py
2. Plugin implements all four required methods from TicketingToolPlugin
3. Existing code from src/services/webhook_validator.py and src/enhancement/ticket_updater.py migrated to plugin
4. Plugin registered in PluginManager on application startup
5. Webhook endpoint updated to use plugin manager: plugin = manager.get_plugin(tenant.tool_type)
6. All existing ServiceDesk Plus unit tests pass without modification (API compatibility maintained)
7. Integration test: Send webhook through plugin → enhacement → ticket update (end-to-end)
8. No breaking changes to existing tenant configurations (tool_type defaults to 'servicedesk_plus')

**Prerequisites:** Story 7.2 (plugin manager ready), Epic 2 complete (ServiceDesk Plus integration working)

---

**Story 7.4: Implement Jira Service Management Plugin**

As a platform engineer,
I want a Jira Service Management plugin,
So that MSPs using Jira can benefit from ticket enhancement.

**Acceptance Criteria:**
1. Jira plugin created at src/plugins/jira/plugin.py implementing TicketingToolPlugin
2. Jira webhook signature validation implemented (HMAC-SHA256 with Jira secret)
3. Jira API client implemented for: Get issue (GET /rest/api/3/issue/{issueKey}), Update issue (PUT /rest/api/3/issue/{issueKey})
4. Metadata extraction from Jira webhook payload (project, issue key, summary, description, priority)
5. Enhancement comment posted to Jira issue using API
6. Jira-specific configuration fields added to tenant_configs: jira_url, jira_api_token, jira_project_key
7. Unit tests for Jira webhook validation, API calls, metadata extraction
8. Integration test with Jira Cloud test instance (using test account)
9. Documentation: docs/jira-plugin-setup.md with onboarding instructions

**Prerequisites:** Story 7.3 (ServiceDesk Plus migrated, plugin pattern proven)

---

**Story 7.5: Update Database Schema for Multi-Tool Support**

As a platform engineer,
I want the database schema to support multiple ticketing tools per tenant,
So that tool-specific configurations are properly stored and retrieved.

**Acceptance Criteria:**
1. Alembic migration created: add tool_type column to tenant_configs (VARCHAR(50), default 'servicedesk_plus')
2. Index created on tool_type column for fast plugin lookup
3. Tool-specific config fields added to enhancement_preferences JSONB: jira_project_key, jira_issue_type, zendesk_subdomain
4. Migration tested: upgrade applies cleanly, downgrade rolls back correctly
5. Existing tenant records updated with tool_type='servicedesk_plus'
6. Data validation: tenant_configs.tool_type must match registered plugin (constraint or application logic)
7. Unit tests for new schema fields and constraints
8. Documentation updated: docs/database-schema.md reflects multi-tool support

**Prerequisites:** Story 7.2 (plugin manager supports multiple tool types)

---

**Story 7.6: Create Plugin Testing Framework and Mock Plugins**

As a developer,
I want a testing framework for plugins,
So that I can test enhancement workflows without real ticketing tool dependencies.

**Acceptance Criteria:**
1. MockTicketingToolPlugin created at tests/mocks/mock_plugin.py
2. Mock plugin implements all four methods with configurable responses (success, failure, timeout)
3. Plugin test fixtures created in tests/conftest.py (mock_servicedesk_plugin, mock_jira_plugin)
4. Test utilities for: asserting plugin method calls, capturing plugin responses, simulating tool failures
5. Integration test: Full enhancement workflow with mock plugin (webhook → enhancement → ticket update)
6. Documentation: tests/README-plugins.md with testing guidelines
7. CI pipeline updated to run plugin tests in isolation

**Prerequisites:** Story 7.2 (plugin manager), Story 7.3 (at least one real plugin to test against)

---

**Story 7.7: Document Plugin Architecture and Extension Guide**

As a future developer or contributor,
I want comprehensive plugin architecture documentation,
So that I can create new ticketing tool plugins independently.

**Acceptance Criteria:**
1. docs/plugin-architecture.md updated with: Architecture overview, Plugin interface spec, Plugin manager usage
2. Plugin development guide created: docs/plugin-development-guide.md with step-by-step instructions
3. Example plugin template provided: src/plugins/_template/ with TODO comments
4. Testing requirements documented (unit tests, integration tests, mock strategies)
5. Plugin submission guidelines (code review checklist, documentation requirements)
6. Troubleshooting section (common plugin errors, debugging tips)
7. Future plugin roadmap documented (Zendesk, Freshservice, custom tool plugins)
8. README.md updated with plugin architecture overview and links

**Prerequisites:** Stories 7.1-7.6 (plugin architecture fully implemented)

---

## Story Guidelines Reference

**Story Format:**

```
**Story [EPIC.N]: [Story Title]**

As a [user type],
I want [goal/desire],
So that [benefit/value].

**Acceptance Criteria:**
1. [Specific testable criterion]
2. [Another specific criterion]
3. [etc.]

**Prerequisites:** [Dependencies on previous stories, if any]
```

**Story Requirements:**

- **Vertical slices** - Complete, testable functionality delivery
- **Sequential ordering** - Logical progression within epic
- **No forward dependencies** - Only depend on previous work
- **AI-agent sized** - Completable in 2-4 hour focused session
- **Value-focused** - Integrate technical enablers into value-delivering stories

---

**For implementation:** Use the `create-story` workflow to generate individual story implementation plans from this epic breakdown.
