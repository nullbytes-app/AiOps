# Brainstorming Session Results

**Session Date:** 2025-11-05
**Facilitator:** BMad Master (Workflow Orchestrator)
**Participant:** Ravi

## Executive Summary

**Topic:** AI Agent Orchestration Platform - Multi-Tenant Agent Management UI

**Session Goals:**
- Design comprehensive UI for creating, configuring, and managing AI agents
- Enable self-service agent creation without code changes
- Support multi-tenant cost control and monitoring
- Integrate LiteLLM gateway for multi-provider LLM management
- Define OpenAPI-first tool integration approach

**Techniques Used:**
- Mind Mapping (Agents, Tools, LLM Providers, UI, Tenants, Monitoring branches)
- Research-Enhanced Discovery (Web search for industry patterns)
- Progressive Flow (systematic exploration)

**Total Ideas Generated:** 24 features across 3 priority tiers

### Key Themes Identified:

1. **Self-Service Agent Management** - Users can create and deploy agents entirely through UI without developer bottleneck
2. **Dynamic Tool Integration** - OpenAPI upload enables rapid tool onboarding via MCP standard
3. **Multi-Tenant Cost Control** - Virtual keys, budget enforcement with grace period (80% warn, 110% block)
4. **Enterprise-Grade Reliability** - Fallback chains, retry logic, provider-agnostic through LiteLLM gateway
5. **Visibility & Observability** - Real-time cost tracking, performance metrics, testing before deployment

## Technique Sessions

### Mind Mapping Session - Complete System Architecture

**Branch 1: AGENTS**
Explored comprehensive agent properties:

**Core Identity:**
- Name, ID, Description, Version

**Behavioral Configuration:**
- System Prompt (defines agent personality/role)
- Instructions (high-level guidance)
- Reasoning Settings (chain-of-thought)
- Delegation Settings (can agent delegate)

**LLM Configuration:**
- Model Selection (GPT-4, Claude, etc.)
- Temperature (0.0-2.0)
- Max Tokens, Top-P, Timeout

**Tools & Integrations:**
- Assigned MCP Tools (ServiceDesk, CMDB, AD, etc.)
- MCP Servers (Model Context Protocol standard)
- Built-in Tools
- Tool Schemas

**Memory & State:**
- Short-term Memory (conversation context)
- Long-term Memory (persistent across sessions)
- Agentic Memory (structured note-taking)
- Context Window Size
- State Schema (Pydantic models)

**Triggers & Execution:**
- Webhook Triggers (unique URL per agent)
- Scheduled Triggers (cron)
- Event-based Triggers
- Thread/Session Management

**Error Handling & Reliability:**
- Retry Logic (3 attempts, exponential backoff)
- Error Handlers (rate_limit, timeout, api_down)
- Fallback Mechanisms

**Output & Validation:**
- Output Schema (Pydantic)
- Response Format (JSON, text, structured)

**Lifecycle & Governance:**
- Status (draft → active → suspended → inactive)
- Created By, Dates, Tenant Assignment

**Monitoring:**
- Event Stream Handler
- Logging Level
- Metrics Collection (tokens, latency, success rate)

**Key Decision:** Agent-centric design where webhook triggers are properties OF the agent, not separate entities.

---

**Branch 2: TOOLS (MCP TOOLS)**

Explored two distinct concepts:

**Trigger Sources (Inbound - How agents get activated):**
- External systems that CALL agents via webhooks
- Properties: Webhook URL, HMAC signature, payload schema, IP whitelist
- Examples: ServiceDesk Plus webhook, Jira webhook

**MCP Tools (Outbound - What agents USE):**
- Systems agents QUERY for context/information
- Properties: OpenAPI spec, auth, rate limits, retry logic
- Examples: AD, CMDB, Monitoring, Knowledge Base MCP servers

**Tool Configuration Properties:**
- Tool Name/ID, Type (MCP Server)
- OpenAPI Spec Upload (auto-generate MCP from Swagger!)
- Target URL, Operation Whitelist/Blacklist
- Authentication (API Key, OAuth 2.0/2.1, SAML, Certificates, JIT auth)
- Rate Limiting (sliding window, leaky bucket, different limits per agent/tenant)
- Retry Logic (max attempts, exponential backoff, retry on 429/500/503)
- Custom Headers, Request Timeout
- Response Schema Validation
- Least Privilege Scope
- Tenant Assignment, Health Check Endpoint

**Key Decisions:**
- OpenAPI-first approach: Upload Swagger spec → instant MCP tool
- Hybrid for existing: Keep ServiceDesk/Jira plugins, refactor to OpenAPI + handlers
- MCP standard validated as 2025 industry pattern (OpenAI, Google, Microsoft adopted)

---

**Branch 3: LLM PROVIDERS**

**Major Discovery:** LiteLLM as industry-standard gateway solution

**Provider Configuration Properties:**
- Provider Name, API Endpoint URL
- Authentication (API Key, Org ID, Project ID)
- Virtual API Keys (per tenant/user tracking)
- Available Models (ID, display name, context window, cost per token)
- Fallback Chain (primary → fallback1 → fallback2)
- Retry Logic (3 attempts, exponential backoff)
- Load Balancing (round-robin, least-latency, usage-based)
- Circuit Breaker (auto-disable failing provider)
- Budget Limits (per tenant, user, key)
- Rate Limits (RPM, TPM)
- Cost Tracking (real-time, per tenant/agent)
- Virtual API Keys (platform-generated, maps to real keys)
- Audit Logging (SOC 2 / ISO 27001 compliance)
- Secret Management (AWS Secrets Manager / Vault)
- Tenant Assignment, Model Restrictions, User-Level Permissions

**Key Decisions:**
- **Integrate LiteLLM proxy** as Docker service
- **Hybrid provider config:** Platform admin sets defaults, tenants can override (BYOK)
- **Grace period enforcement:** Warn at 80%, block at 110% of budget
- **LiteLLM benefits:** Unified interface, automatic fallbacks, load balancing, cost tracking, 100+ providers, MCP integration

---

**Branch 4: CONFIGURATION UI**

**UI Pages Needed:**

**Agent Management:**
- Agent List (view all, status, last run)
- Create/Edit Agent (tabs: Basic Info, Triggers, MCP Tools, LLM Config, System Prompt)
- Agent Dashboard (performance metrics)

**Tool Management:**
- MCP Tools Library (upload OpenAPI, configure)
- Tool Configuration (credentials, rate limits, health)
- Tool Assignment (which agents access which tools)

**LLM Provider:**
- Provider Configuration (add keys)
- Model Selection (enable/disable)
- Budget Management (limits, usage, alerts)
- Usage Analytics (cost per tenant/agent)

**Tenant Management:**
- Tenant List (existing from Epic 6)
- Tenant Settings (add BYOK, budgets)
- Tenant Agents (view/manage)

**Monitoring:**
- System Dashboard (health)
- Agent Execution Logs (traces)
- Cost Dashboard (spending trends)

**Key Decision:** Separate top-level nav items (Agents | Tools | Providers | Tenants | Monitoring) for clear organization

---

**Branch 5: TENANTS**

**Tenant Hierarchy:**
```
PLATFORM
  └─ TENANT (Organization)
      ├─ Users (admins, operators, viewers)
      ├─ Agents (their AI agents)
      ├─ Tools (assigned MCP tools)
      ├─ LLM Config (budget, BYOK)
      └─ Webhooks (trigger endpoints)
```

**Key Decisions:**
- Flat structure (each org = tenant)
- User Roles: Admin (configure), Operator (run), Viewer (read-only)
- Resource Isolation: Separate webhook URLs, virtual LLM keys, tenant_id filtering

---

**Branch 6: MONITORING**

**What to Monitor:**

**Agent Level:**
- Execution count, avg time, token usage, error rate

**Tenant Level:**
- Total runs, LLM cost, budget utilization, active agents

**Platform Level:**
- Total requests/day, LiteLLM health, DB connections, queue depth, P50/P95/P99

**Tool Level:**
- Call count, latency, error rate, rate limit status

**Monitoring Stack (Epic 4):**
- Prometheus, Grafana, OpenTelemetry, AlertManager

**New Dashboards:**
- LLM Cost Dashboard
- Agent Performance Dashboard
- Tenant Usage Dashboard

---

## Idea Categorization

### Immediate Opportunities (Quick Wins)

_Ideas ready to implement now - High value, low complexity_

1. **Agent CRUD basics** - Create, list, edit, delete agents via UI
2. **System prompt editor** - Text area for prompt configuration
3. **LiteLLM Docker service** - Add to docker-compose.yml
4. **Basic provider config** - Platform admin configures OpenAI/Anthropic keys
5. **Agent webhook endpoint generation** - Auto-generate unique URLs per agent
6. **Tool assignment UI** - Checkboxes to assign existing tools to agents

### Future Innovations (Promising Concepts)

_Ideas requiring development/research - Important but more work_

7. **OpenAPI tool upload** - Auto-generate MCP tools from Swagger specs
8. **Virtual key management** - LiteLLM integration for per-tenant keys
9. **Budget enforcement with grace period** - Track usage, alert at 80%, block at 110%
10. **Agent testing sandbox** - Test agent with sample inputs before activation
11. **Memory configuration UI** - Configure short/long-term memory settings
12. **Fallback chain configuration** - UI to set primary → fallback1 → fallback2
13. **BYOK (Bring Your Own Key)** - Tenant-provided API keys
14. **LLM cost dashboard** - Real-time spending visualization
15. **Agent performance metrics** - Success rate, duration, token usage per agent

### Moonshots (Bold Long-term Vision)

_Ambitious, transformative concepts - Future exploration_

16. **Visual prompt builder** - Drag-and-drop prompt template system
17. **Agent marketplace** - Pre-built agent templates users can deploy
18. **Multi-level tenancy** - MSP → Clients hierarchy
19. **Agent collaboration** - Agents calling other agents
20. **Auto-optimization** - AI suggests prompt improvements based on performance
21. **Model A/B testing** - Test prompt variations, choose best performer
22. **Advanced RBAC** - Granular permissions (who can edit what)
23. **Plugin ecosystem** - Community-contributed MCP tools
24. **Agent versioning system** - Deploy multiple versions, rollback capability

### Insights and Learnings

_Key realizations from the session_

**Insight 1: Gateway Pattern is Critical**
LiteLLM isn't just nice-to-have—it's foundational for multi-tenant cost control, provider flexibility, and observability. Without it, building all that infrastructure manually would take months.

**Insight 2: Configuration Over Code**
The pattern emerging is "configure once, use everywhere." OpenAPI specs become tools, YAML configs become agents, virtual keys become tenants. This is the path to scalability and self-service.

**Insight 3: Agent-Centric Design Wins**
Making the agent the center (with triggers, tools, and LLM config as properties) creates a simpler mental model than having separate "trigger sources" and "tool assignments." Everything about an agent lives with the agent.

**Insight 4: Hybrid Approach Solves Real Problems**
Platform-provided defaults with tenant overrides (BYOK) addresses both ease-of-use (quick onboarding) and enterprise requirements (data sovereignty, cost control, compliance).

**Insight 5: Testing is Non-Negotiable**
Every major feature needs a "test" capability: test connection for tools, test webhook for triggers, sandbox mode for agents. This prevents "deploy and pray" scenarios and builds user confidence.

**Insight 6: Industry Patterns Validate Approach**
Research showed major platforms (Microsoft Copilot Studio, AWS Gateway, Portkey) all converging on similar patterns: OpenAPI-first, virtual keys, budget enforcement, MCP standard. Our approach aligns with 2025 best practices.

## Action Planning

### Top 3 Priority Ideas

#### #1 Priority: LiteLLM Proxy Integration & Foundation

**Rationale:**
Foundation for all LLM features. Without LiteLLM, we can't do multi-tenant cost control, provider fallbacks, or usage tracking. This unblocks all subsequent stories.

**Next steps:**
1. Add LiteLLM service to docker-compose.yml with PostgreSQL backend
2. Create config/litellm-config.yaml with default providers (OpenAI, Anthropic)
3. Update agent code to point to LiteLLM proxy instead of direct provider APIs
4. Create agent database schema (agents, agent_tools, agent_triggers tables)
5. Test with existing ServiceDesk Plus agent

**Resources needed:**
- LiteLLM Docker image (ghcr.io/berriai/litellm-database:main-stable)
- PostgreSQL for virtual key storage (already have)
- OpenAI + Anthropic API keys (already have)
- 1 developer week

**Timeline:** Week 1-2 of Epic 8

---

#### #2 Priority: Core Agent Management UI

**Rationale:**
Users need to create and configure agents through UI. This is the core value proposition—eliminating the developer bottleneck for agent creation.

**Next steps:**
1. Build Agent CRUD API endpoints (POST/GET/PUT/DELETE /api/agents)
2. Create Agent Management Streamlit page (05_Agent_Management.py)
3. Build agent creation wizard with tabs (Basic Info, LLM Config, System Prompt, Triggers, Tools)
4. Implement system prompt editor with templates
5. Generate unique webhook URLs per agent
6. Tool assignment checkboxes (assign ServiceDesk, Jira, future MCP tools)

**Resources needed:**
- FastAPI for backend APIs
- Streamlit for admin UI
- Pydantic schemas for validation
- 2-3 developer weeks

**Timeline:** Week 3-5 of Epic 8

---

#### #3 Priority: OpenAPI Tool Upload & Dynamic MCP Generation

**Rationale:**
This transforms the platform from "pre-built integrations only" to "integrate any API in minutes." Critical differentiator and enables rapid expansion of tool ecosystem without custom code.

**Next steps:**
1. Build OpenAPI/Swagger upload interface
2. Parse OpenAPI spec to extract operations, parameters, auth requirements
3. Generate MCP server wrapper code dynamically
4. Create tool configuration form based on parsed auth schemes
5. Implement "Test Connection" validation
6. Store tool metadata in database (tools table)

**Resources needed:**
- OpenAPI parser library (prance, openapi-spec-validator)
- MCP server generation templates
- 2 developer weeks (complex feature)

**Timeline:** Week 6-8 of Epic 8

---

## Reflection and Follow-up

### What Worked Well

1. **Research-Enhanced Discovery** - Using web search to validate architectural patterns (LiteLLM, MCP standard, OpenAPI-first) saved us from reinventing the wheel and aligned us with industry best practices

2. **Agent-Centric Mental Model** - Early clarity on making agents the center (not separate trigger/tool entities) simplified the entire architecture

3. **Progressive Mind Mapping** - Systematically exploring each branch (Agents → Tools → Providers → UI → Tenants → Monitoring) ensured comprehensive coverage

4. **Hybrid Decisions** - Recognizing when "both/and" beats "either/or" (platform defaults + BYOK, plugins + MCP, quick wins + promising concepts)

5. **Party Mode Collaboration** - Having multiple agent personas (John, Mary, Winston, Sally, Amelia, Murat, Bob, Paige) provided diverse perspectives and caught gaps early

### Areas for Further Exploration

1. **Agent Collaboration Patterns** - How agents call other agents, delegate tasks, share context (Moonshot #19)

2. **Security Hardening** - Prompt injection defense, tool permission boundaries, tenant isolation validation

3. **Performance Optimization** - Caching strategies, connection pooling, query optimization for high-scale deployments

4. **Plugin Marketplace Mechanics** - How community-contributed MCP tools get validated, versioned, and distributed

5. **Agent Versioning & Rollback** - Blue/green deployment for agents, A/B testing framework, safe rollback mechanisms

### Recommended Follow-up Techniques

For deep dives on specific components:

1. **SCAMPER Method** - For optimizing the agent creation UX (Substitute, Combine, Adapt, Modify, Put to other use, Eliminate, Reverse)

2. **Assumption Reversal** - For challenging constraints on tool integration ("What if tools could install themselves?")

3. **Five Whys** - For understanding root causes of configuration complexity

4. **Six Thinking Hats** - For evaluating trade-offs in BYOK vs. platform-managed keys

### Questions That Emerged

1. **How do we handle agent versioning?** If a user updates an agent's prompt, should old in-flight executions use the old version?

2. **What's the approval workflow for agents?** Should Draft → Review → Approved flow exist for enterprise compliance?

3. **How do agents share learnings?** If Agent A discovers a good solution pattern, can Agent B learn from it?

4. **What's the migration path?** How do we migrate existing hardcoded Ticket Enhancement agent to new agent management system?

5. **How do we prevent agent sprawl?** Should there be limits on agents per tenant? Cleanup of unused agents?

6. **What's the tool discovery UX?** How do users find and select the right MCP tool from a library of 50+ tools?

### Next Session Planning

**Suggested topics:**
1. Deep dive: Agent testing & validation frameworks
2. Deep dive: Tool marketplace & discovery UX
3. Deep dive: Multi-level tenancy (MSP → Clients)
4. Security review: Threat modeling for agent orchestration
5. Performance planning: Scaling to 1000+ tenants, 10,000+ agents

**Recommended timeframe:** 2-3 weeks (after Epic 8 foundation stories are implemented)

**Preparation needed:**
- Implement Stories 8.1-8.4 to have working foundation
- Gather user feedback on agent creation UX
- Research competitive agent platforms (n8n, Zapier, Make) for UX inspiration

---

## Epic 8: AI Agent Orchestration Platform

**Goal:** Enable users to create, configure, and manage AI agents through UI without code changes

**Value:** Transforms platform from single-purpose (ticket enhancement) to general-purpose agent orchestration

**Target Milestone:** MVP v2.5 (12-14 weeks)

**Story Breakdown:** 17 stories across 5 phases

### Phase 1: Foundation (Weeks 1-2)
- Story 8.1: LiteLLM Proxy Integration (1 week)
- Story 8.2: Agent Database Schema & Models (3-4 days)

### Phase 2: Core Agent Management (Weeks 3-5)
- Story 8.3: Agent CRUD API Endpoints (3-4 days)
- Story 8.4: Agent Management UI (1 week)
- Story 8.5: System Prompt Editor (4-5 days)
- Story 8.6: Agent Webhook Endpoint Generation (3 days)

### Phase 3: Tool Integration (Weeks 6-8)
- Story 8.7: Tool Assignment UI (2-3 days)
- Story 8.8: OpenAPI Tool Upload & Auto-Generation (2 weeks)

### Phase 4: LLM Provider Features (Weeks 9-11)
- Story 8.9: Virtual Key Management (3-4 days)
- Story 8.10: Budget Enforcement with Grace Period (1 week)
- Story 8.11: Provider Configuration UI (4-5 days)
- Story 8.12: Fallback Chain Configuration (3-4 days)
- Story 8.13: BYOK (Bring Your Own Key) (1 week)

### Phase 5: Advanced Features (Weeks 12-14)
- Story 8.14: Agent Testing Sandbox (1 week)
- Story 8.15: Memory Configuration UI (1-2 weeks)
- Story 8.16: LLM Cost Dashboard (1 week)
- Story 8.17: Agent Performance Metrics Dashboard (1 week)

### Success Metrics

**Adoption:**
- Time to create new agent: < 10 minutes (vs. weeks of coding)
- % of agents created via UI: Target 95%
- Number of tenants using BYOK: Track adoption

**Cost:**
- Budget overruns: < 5% (grace period working)
- Cost per agent execution: Trend downward (fallbacks optimize)
- Alert response time: < 1 hour (automated alerts)

**Performance:**
- Agent creation success rate: > 98%
- Tool connection test success: > 95%
- Provider fallback triggers: Track frequency

---

_Session facilitated using the BMAD CIS brainstorming framework with Party Mode multi-agent collaboration_
