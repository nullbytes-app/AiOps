# Sprint Change Proposal: Admin UI & Plugin Architecture

**Project:** AI Agents
**Date:** 2025-11-02
**Author:** Bob (Scrum Master) with Ravi
**Change Scope:** MAJOR - Architectural Enhancement
**Status:** ✅ APPROVED

---

## Executive Summary

During Epic 2 implementation (Story 2-5), we identified two strategic capabilities missing from the original architecture that significantly impact operational effectiveness and market applicability:

1. **No Admin/Operations UI** - Operators lack visibility and must use SQL/kubectl for configuration
2. **Hardcoded Tool Integration** - System limited to ServiceDesk Plus, cannot support other ticketing tools

**Recommended Approach:** Phased delivery across 3 releases

- **Phase 1 (MVP v1.0):** Complete Epic 1-5 as planned - proves core enhancement agent value
- **Phase 2 (MVP v1.5):** Add Streamlit admin UI - improves operations and self-service
- **Phase 3 (MVP v2.0):** Add plugin architecture - enables multi-tool support for market expansion

**Timeline Impact:** MVP v1.0 unchanged, +2-3 weeks for Phase 2, +3-4 weeks for Phase 3

**Business Value:**
- Phase 1: Core AI enhancement (HIGH value)
- Phase 2: Operational efficiency (MEDIUM value, reduces friction)
- Phase 3: Market expansion (HIGH value, supports Jira/Zendesk users)

---

## Issue Summary

### Problem Statement

> The AI Agents platform lacks a user interface for configuration management and system observability. Without a UI, operators cannot:
> - Configure system settings (model selection, agent prompts, enhancement preferences)
> - View database information and trigger sync operations
> - Monitor system operations beyond Grafana metrics
> - Switch between different ticketing tools (currently hardcoded to ServiceDesk Plus)

### Discovery Context

**When:** During implementation of Story 2-5 (Ticket History Search)

**How Discovered:** Realized that operators would need to:
- Onboard new tenants (configure URLs, API keys, webhook secrets)
- View enhancement history for debugging failed jobs
- Trigger bulk imports of historical tickets
- Monitor queue depth and worker status in real-time
- Switch between ServiceDesk Plus, Jira, Zendesk based on client needs

**Evidence:**
- Codebase analysis identified 18+ configuration points requiring UI exposure
- Current approach requires SQL queries to view `tenant_configs`, `enhancement_history`
- Manual database operations to trigger bulk imports
- ServiceDesk Plus integration hardcoded in 4+ files (webhooks, validators, API clients)

---

## Impact Analysis

### Epic Impact

| Epic | Status | Impact | Changes Needed |
|------|--------|--------|----------------|
| **Epic 1: Foundation** | ✅ Complete | None | No changes |
| **Epic 2: Core Enhancement** | ⚙️ In Progress | Minor | Can complete as-is, note in Story 2.10 that ServiceDesk Plus will become plugin in Phase 3 |
| **Epic 3: Multi-Tenancy** | 📋 Backlog | Minor | Story 3.2 should note UI coming in Epic 6 |
| **Epic 4: Monitoring** | 📋 Backlog | Minor | Grafana remains for SRE view, UI adds operator view (complementary) |
| **Epic 5: Production** | 📋 Backlog | Minor | Sequencing decision needed: deploy before or after UI |
| **🆕 Epic 6: Admin UI** | 🆕 New | NEW EPIC | 6-8 stories, 2-3 weeks, Streamlit-based admin interface |
| **🆕 Epic 7: Plugin Architecture** | 🆕 New | NEW EPIC | 5-7 stories, 3-4 weeks, abstract plugin pattern for tools |

**Total Story Addition:** 11-15 new stories
**Timeline Addition:** 5-7 weeks spread across Phases 2-3

### Artifact Changes Summary

**PRD (docs/PRD.md):**
- ✅ Add FR026-FR033 (Admin UI functional requirements)
- ✅ Add FR034-FR039 (Plugin architecture requirements)
- ✅ Add User Journey 4 (Operator onboards tenant via UI)
- ✅ Add Epic 6 & 7 to epic list
- ✅ Move multi-tool support from "Out of Scope" to Phase 3

**Architecture (docs/architecture.md):**
- ✅ Add Streamlit to technology stack
- ✅ Add admin-ui/ project structure
- ✅ Add Admin UI Architecture section (deployment, API endpoints, authentication)
- ✅ Add Plugin Architecture section (interface, manager, routing)
- ✅ Add tool_type, tool_specific_config columns to tenant_configs schema
- ✅ Add ADR-009 (Streamlit decision rationale)
- ✅ Add ADR-010 (Plugin architecture pattern)

**Epics (docs/epics.md):**
- ✅ Add Epic 6 complete story breakdown (Stories 6.1-6.8)
- ✅ Add Epic 7 complete story breakdown (Stories 7.1-7.7)

**Deployment:**
- ✅ Add docker/admin-ui.dockerfile
- ✅ Update docker-compose.yml (add admin-ui service)
- ✅ Add k8s/deployment-admin-ui.yaml + service
- ✅ Update k8s/ingress.yaml (admin subdomain)

**Testing:**
- ✅ Add tests/admin_ui/ test suite (Streamlit testing)
- ✅ Add tests/unit/test_plugins.py (plugin interface tests)

**Documentation:**
- ✅ Update README.md (admin UI quick start)
- ✅ Add docs/admin-ui-guide.md (operator user guide)
- ✅ Add docs/plugin-development-guide.md (Phase 3)

**CI/CD:**
- ✅ Update .github/workflows/ci.yml (admin UI tests + Docker build)

---

## Path Forward Evaluation

### Options Considered

**Option 1: Phased Delivery (Recommended)**
- Phase 1: Complete Epic 1-5 as-is
- Phase 2: Add Admin UI (Epic 6)
- Phase 3: Add Plugin Architecture (Epic 7)
- **Effort:** Low Phase 1, Medium Phase 2 (2-3 weeks), Medium Phase 3 (3-4 weeks)
- **Risk:** Low - incremental validation
- **Status:** ✅ **SELECTED**

**Option 2: Potential Rollback**
- Revert Stories 2.1-2.4 and redesign with plugins from start
- **Effort:** High (redo 4 weeks of work)
- **Risk:** High (waste validated code)
- **Status:** ❌ **REJECTED** - No benefit, wastes good work

**Option 3: MVP Scope Reduction**
- Remove Epic 5 (Production) from MVP
- Add UI + Plugins before production
- **Effort:** Medium (better architecture before production)
- **Risk:** Medium (delays real-world validation)
- **Status:** ❌ **REJECTED** - Delays market feedback

### Selected Approach: Option 1 (Phased Delivery)

**Rationale:**

**Implementation Effort:**
- Phase 1: Already in progress, no added work
- Phase 2: 2-3 weeks (Streamlit is rapid development)
- Phase 3: 3-4 weeks (refactoring + new plugin)

**Technical Risk:** Low
- Each phase is independent and testable
- Streamlit is beginner-friendly (matches user skill level: beginner)
- Plugin architecture is well-established pattern
- No breaking changes to existing code

**Team Momentum:**
- ✅ Continuous value delivery (finish what we started)
- ✅ Phase 1 success validates core concept
- ✅ Phase 2 immediate operational improvement
- ✅ Phase 3 market expansion when core proven

**Long-term Sustainability:**
- ✅ Admin UI reduces operational friction
- ✅ Plugin architecture enables scalability
- ✅ Learning between phases informs better design
- ✅ User feedback after Phase 1 improves Phase 2 UI design

**Business Value:**
- Phase 1: Prove AI enhancement value (HIGH)
- Phase 2: Self-service operations (MEDIUM)
- Phase 3: Multi-tool market expansion (HIGH)

---

## Phased Implementation Plan

### Phase 1: MVP v1.0 (Weeks 1-10) - IN PROGRESS

**Goal:** Deliver working AI enhancement agent, prove core value

**Epics:**
- Epic 1: Foundation ✅ COMPLETE
- Epic 2: Core Enhancement Agent (Stories 2.5-2.12 remaining)
- Epic 3: Multi-Tenancy & Security
- Epic 4: Monitoring & Operations
- Epic 5: Production Deployment

**Deliverables:**
- ✅ Working end-to-end enhancement workflow
- ✅ ServiceDesk Plus integration (webhook + API)
- ✅ Multi-tenant isolation with RLS
- ✅ Grafana monitoring dashboards
- ✅ Production deployment on Kubernetes

**Success Criteria:**
- ✅ Process 10+ tickets/day successfully
- ✅ p95 latency <60 seconds
- ✅ 95%+ success rate
- ✅ First client onboarded and validated

**Configuration:** Manual (SQL for tenant_configs, YAML for app settings)

**Tools:** ServiceDesk Plus only

---

### Phase 2: MVP v1.5 (Weeks 11-13) - Admin UI

**Goal:** Add operational visibility and self-service configuration

**Epic:**
- Epic 6: Admin & Operations UI (Stories 6.1-6.8)

**Stories:**
1. **Story 6.1:** Streamlit Setup + Authentication (2 days)
   - Set up admin-ui/ project structure
   - Configure Streamlit with theme and settings
   - Implement basic authentication with streamlit-authenticator
   - Deploy to port 8501 locally

2. **Story 6.2:** Tenant Management CRUD (3 days)
   - Implement Tenants page with list view
   - Create tenant form (name, tool URL, API key, webhook secret)
   - Add form validation and "Test Connection" button
   - Implement create, read, update, delete operations via FastAPI endpoints

3. **Story 6.3:** Operations Dashboard (3 days)
   - Create Dashboard page with 2x2 metric card grid
   - Display: queue depth, active workers, success rate, p95 latency
   - Implement auto-refresh every 5 seconds
   - Add recent enhancements table (last 50 records)

4. **Story 6.4:** Enhancement History Viewer (2 days)
   - Implement Enhancement History page
   - Add filters: tenant, status, date range, ticket ID search
   - Create expandable detail view (context, LLM output, errors)
   - Add pagination for large result sets

5. **Story 6.5:** Bulk Import UI (2 days)
   - Implement Sync Operations page
   - Create bulk import form (tenant selector, date range)
   - Add progress tracking with real-time updates
   - Display import history table

6. **Story 6.6:** FastAPI Admin Endpoints (2 days)
   - Implement /api/admin/tenants/* endpoints (CRUD)
   - Implement /api/admin/enhancements* endpoints (list, detail)
   - Implement /api/admin/metrics endpoint (real-time data)
   - Implement /api/admin/sync/* endpoints (trigger, status)

7. **Story 6.7:** Deploy Admin UI (1 day)
   - Create docker/admin-ui.dockerfile
   - Update docker-compose.yml
   - Create k8s/deployment-admin-ui.yaml + service
   - Update k8s/ingress.yaml for admin subdomain
   - Test deployment locally and on staging

8. **Story 6.8:** Documentation (1 day)
   - Update README.md with admin UI quick start
   - Create docs/admin-ui-guide.md (user guide)
   - Document admin API endpoints
   - Create operator training materials

**Deliverables:**
- ✅ Web-based admin interface at admin.ai-agents.example.com
- ✅ Self-service tenant onboarding (no SQL required)
- ✅ Real-time system health dashboard
- ✅ Enhancement history debugging interface
- ✅ Bulk import trigger with progress tracking

**Success Criteria:**
- ✅ Non-technical operator can onboard tenant in <5 minutes (vs 30 minutes manual)
- ✅ Dashboard metrics update every 5 seconds
- ✅ Enhancement history searchable in <2 seconds
- ✅ Bulk import processes 100 tickets/minute

**Technology:** Streamlit (Python-native, beginner-friendly)

**Timeline:** 2-3 weeks

---

### Phase 3: MVP v2.0 (Weeks 14-18) - Plugin Architecture

**Goal:** Enable multi-tool support for market expansion

**Epic:**
- Epic 7: Multi-Tool Plugin Architecture (Stories 7.1-7.7)

**Stories:**
1. **Story 7.1:** Plugin Base Interface + Manager (3 days)
   - Create src/plugins/base.py (TicketingToolPlugin ABC)
   - Define interface methods: validate_webhook, parse_webhook_payload, update_ticket, fetch_ticket_history
   - Implement src/plugins/plugin_manager.py (registry pattern)
   - Add tool_type, tool_specific_config to database schema (Alembic migration)

2. **Story 7.2:** Refactor ServiceDesk Plus into Plugin (4 days)
   - Create src/plugins/servicedesk_plus/ directory
   - Move existing webhook validation to plugin
   - Move existing API client to plugin
   - Implement TicketingToolPlugin interface
   - Register ServiceDeskPlusPlugin in manager
   - Update Stories 2.1, 2.2, 2.10 code to use plugin
   - Ensure backward compatibility (no functional changes)

3. **Story 7.3:** Implement Jira Plugin (5 days)
   - Create src/plugins/jira/ directory
   - Implement JiraPlugin.validate_webhook (Jira webhook signature)
   - Implement JiraPlugin.parse_webhook_payload (Jira webhook format)
   - Implement JiraPlugin.update_ticket (Jira REST API)
   - Implement JiraPlugin.fetch_ticket_history (Jira JQL queries)
   - Register JiraPlugin in manager
   - Test with Jira sandbox instance

4. **Story 7.4:** UI Plugin Selector (2 days)
   - Update tenant form in Admin UI (add tool dropdown)
   - Display available plugins from plugin_manager.plugins
   - Add tool-specific configuration fields (conditional based on tool_type)
   - Update tenant create/edit endpoints to handle tool_type

5. **Story 7.5:** Update Webhook Routing (3 days)
   - Refactor src/api/webhooks.py to use plugin_manager
   - Implement dynamic plugin selection based on tenant_config.tool_type
   - Update webhook endpoint to route to plugin.validate_webhook
   - Update payload parsing to use plugin.parse_webhook_payload
   - Ensure error handling for unknown tool types

6. **Story 7.6:** Plugin Tests + Documentation (2 days)
   - Create tests/unit/test_plugins.py (interface contract tests)
   - Create tests/unit/test_servicedesk_plus_plugin.py
   - Create tests/unit/test_jira_plugin.py
   - Create docs/plugin-development-guide.md
   - Document plugin registration process

7. **Story 7.7:** Deploy + Multi-Tool Validation (2 days)
   - Deploy to staging with both plugins
   - Create test tenants: one ServiceDesk Plus, one Jira
   - Validate webhook routing to correct plugin
   - Validate ticket updates for both tools
   - Production deployment with monitoring

**Deliverables:**
- ✅ Abstract TicketingToolPlugin base class
- ✅ Plugin manager with registry
- ✅ ServiceDesk Plus refactored as plugin (backward compatible)
- ✅ Jira plugin implementation (second tool)
- ✅ UI plugin selector in tenant form
- ✅ Dynamic webhook routing
- ✅ Plugin development guide

**Success Criteria:**
- ✅ 2+ ticketing tools supported (ServiceDesk Plus, Jira)
- ✅ Tenant can switch tools via UI dropdown
- ✅ Webhooks route to correct plugin based on tenant
- ✅ Third-party developer can add plugin using guide

**Technology:** Python ABC (Abstract Base Class), plugin registry pattern

**Timeline:** 3-4 weeks

---

## Technology Decisions

### Admin UI: Streamlit

**Decision:** Use Streamlit for admin and operations interface

**Rationale:**
- ✅ Python-native (zero JavaScript knowledge required, matches team skill set)
- ✅ Rapid development (built-in components reduce code by 80%)
- ✅ Real-time updates (auto-refresh with st.rerun())
- ✅ Beginner-friendly (matches user skill level from config: beginner)
- ✅ Separate deployment (port 8501, doesn't complicate FastAPI)
- ✅ Perfect for internal tools (admin dashboards don't need SPA complexity)

**Alternatives Considered:**
- React + FastAPI: ❌ Requires JavaScript expertise, slower development, overkill
- Vue + FastAPI: ❌ Similar to React, still requires JS
- FastAPI Admin: ❌ Auto-generated but inflexible, hard to customize
- HTMX + Alpine.js: ✅ Good alternative (minimal JS) but slower than Streamlit for MVP

**Tradeoffs:**
- ✅ 5-10x faster development than SPA
- ✅ No build pipeline, no webpack, no npm
- ⚠️ Less customizable UI (Streamlit's opinionated design) - acceptable for internal tool
- ⚠️ Not suitable for public-facing UIs - fine for admin interface

**References:**
- Reflex.dev comparison (2025)
- Medium: Streamlit vs Gradio (2024)
- Reddit r/htmx: FastAPI + HTMX boilerplate
- Streamlit documentation

---

### Plugin Architecture: Abstract Base Class + Registry

**Decision:** Implement abstract plugin pattern for ticketing tool integrations

**Rationale:**
- ✅ Extensibility (add new tools without core code changes)
- ✅ Market fit (different MSPs use different tools - Jira, Zendesk, Freshservice)
- ✅ Maintainability (tool-specific code isolated in plugins)
- ✅ Testability (mock plugins for testing, interface contract tests)
- ✅ Competitive (multi-tool support is table stakes for B2B SaaS)

**Alternatives Considered:**
- Hardcode all tools: ❌ Unmaintainable, explosion of if/else logic
- Single adapter pattern: ❌ Less flexible than plugin pattern
- Microservices per tool: ❌ Operational overhead for MVP

**Implementation:**
- Abstract base class: `TicketingToolPlugin` (Python ABC)
- Plugin manager with registry pattern
- Discovery via manual registration (entry points as future enhancement)
- Backward compatible: ServiceDesk Plus becomes first plugin

**References:**
- Stack Overflow: Building plugin architecture in Python
- Python docs: Abstract Base Classes
- re-ws.pl: Plugin architecture demo (2024)

---

## Database Schema Changes

### Phase 2 (Admin UI)
No schema changes - uses existing tables.

### Phase 3 (Plugin Architecture)

**Alembic Migration:** `add_tool_type_to_tenant_configs`

```sql
-- Add tool_type column
ALTER TABLE tenant_configs
ADD COLUMN tool_type VARCHAR(50) NOT NULL DEFAULT 'servicedesk_plus';

-- Add tool-specific config
ADD COLUMN tool_specific_config JSONB DEFAULT '{}';

-- Add index for tool_type queries
CREATE INDEX idx_tenant_configs_tool_type ON tenant_configs(tool_type);

-- Update column comments
COMMENT ON COLUMN tenant_configs.tool_type IS
  'Ticketing tool plugin identifier (servicedesk_plus, jira, zendesk, etc.)';

COMMENT ON COLUMN tenant_configs.tool_specific_config IS
  'Plugin-specific configuration (e.g., Jira project key, Zendesk subdomain)';
```

**Backward Compatibility:** Default value 'servicedesk_plus' ensures existing tenants continue working.

---

## Testing Strategy

### Phase 2: Admin UI Tests

**Location:** tests/admin_ui/

**Approach:** Streamlit testing framework (streamlit.testing.v1.AppTest)

**Coverage:**
- Form validation (required fields, valid URLs, min length)
- Tenant CRUD operations (create, read, update, delete)
- Dashboard metric display (mock API responses)
- History viewer search/filter (pagination, date ranges)
- Bulk import trigger (progress tracking, error handling)

**Example:**
```python
def test_create_tenant_form_validation():
    at = AppTest.from_file("admin-ui/pages/2_👥_Tenants.py")
    at.run()
    at.button[0].click()  # Submit empty form
    assert "Tenant Name is required" in at.error[0].value
```

### Phase 3: Plugin Tests

**Location:** tests/unit/test_plugins.py

**Approach:** Interface contract testing + plugin-specific tests

**Coverage:**
- Plugin interface compliance (all plugins implement required methods)
- ServiceDesk Plus plugin (webhook validation, API calls)
- Jira plugin (webhook validation, JQL queries, REST API)
- Plugin manager (registration, routing, error handling)

**Example:**
```python
def test_all_plugins_implement_interface():
    from src.plugins.plugin_manager import plugin_manager
    for name, plugin in plugin_manager.plugins.items():
        assert hasattr(plugin, 'validate_webhook')
        assert hasattr(plugin, 'parse_webhook_payload')
        assert hasattr(plugin, 'update_ticket')
        assert hasattr(plugin, 'fetch_ticket_history')
```

---

## Deployment Changes

### Phase 2: Admin UI Deployment

**Docker Compose (Local Development):**
```yaml
services:
  admin-ui:
    build:
      context: .
      dockerfile: docker/admin-ui.dockerfile
    ports:
      - "8501:8501"
    environment:
      - API_URL=http://api:8000
    depends_on:
      - api
```

**Kubernetes (Production):**
```yaml
# k8s/deployment-admin-ui.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: admin-ui
  namespace: ai-agents-prod
spec:
  replicas: 1  # Admin UI doesn't need horizontal scaling
  selector:
    matchLabels:
      app: admin-ui
  template:
    spec:
      containers:
      - name: admin-ui
        image: ai-agents-admin:latest
        ports:
        - containerPort: 8501
        resources:
          requests:
            cpu: 100m
            memory: 256Mi
          limits:
            cpu: 500m
            memory: 512Mi
```

**Ingress Update:**
```yaml
# k8s/ingress.yaml (add admin subdomain)
spec:
  rules:
  - host: admin.ai-agents.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: admin-ui-service
            port:
              number: 8501
```

### Phase 3: Plugin Architecture
No deployment changes - plugins are part of API codebase.

---

## Risks and Mitigation

### Phase 2 Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|-----------|
| Streamlit learning curve | Delays Phase 2 | Low | Streamlit documentation excellent, beginner-friendly |
| Admin UI performance with large datasets | Slow page loads | Medium | Implement pagination, limit results to 1000 records, add indexes |
| Authentication bypass | Security vulnerability | Low | Use streamlit-authenticator, basic auth for MVP, OAuth2 for production |
| Admin UI adds operational overhead | More services to manage | Low | Single container, minimal resources, health checks |

### Phase 3 Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|-----------|
| Plugin abstraction too complex | Hard to add new tools | Medium | Keep interface simple (4 methods), provide good documentation |
| ServiceDesk Plus refactoring breaks existing code | Service disruption | Medium | Comprehensive tests, backward compatibility, staged rollout |
| Jira plugin implementation takes longer | Phase 3 delays | Medium | Timebox to 5 days, reduce scope to basic functionality if needed |
| Plugin routing errors | Webhooks fail | Low | Extensive error handling, fallback to default, monitoring alerts |

---

## Success Metrics

### Phase 1 (MVP v1.0) - Core Enhancement Agent

- **Performance:** p95 latency <60 seconds
- **Reliability:** 95%+ success rate
- **Throughput:** Process 10+ tickets/day per tenant
- **Client Validation:** 1+ production tenant live for 2+ weeks

### Phase 2 (MVP v1.5) - Admin UI

- **Efficiency:** Tenant onboarding time reduced from 30 minutes (manual) to 5 minutes (UI)
- **Adoption:** 100% of tenant onboarding done via UI (no SQL queries)
- **Usability:** Non-technical operators can manage system without developer help
- **Visibility:** Operators check dashboard 5+ times/day for system health

### Phase 3 (MVP v2.0) - Plugin Architecture

- **Tools Supported:** 2+ ticketing tools (ServiceDesk Plus + Jira minimum)
- **Market Expansion:** Can onboard Jira-using MSPs (previously blocked)
- **Extensibility:** Third-party developer can add plugin in <3 days using guide
- **Reliability:** Plugin routing 100% accurate (no webhooks to wrong tool)

---

## Handoff Plan

### Immediate Actions (This Week - Scrum Master)

1. ✅ **Approve Sprint Change Proposal** (You - Done)
2. 📝 **Update docs/PRD.md** - Add FR026-FR039, User Journey 4, Epic 6 & 7
3. 📝 **Update docs/architecture.md** - Add Streamlit, Plugin sections, ADR-009, ADR-010
4. 📝 **Update docs/epics.md** - Add Epic 6 & 7 story breakdowns
5. 💾 **Git Commit:** "Add Admin UI and Plugin Architecture to roadmap"
   ```bash
   git add docs/PRD.md docs/architecture.md docs/epics.md docs/sprint-change-proposal-2025-11-02.md
   git commit -m "Add Epic 6 (Admin UI) and Epic 7 (Plugin Architecture) to roadmap

   - Phase 1 (MVP v1.0): Epic 1-5 unchanged
   - Phase 2 (MVP v1.5): Add Streamlit admin UI for operations
   - Phase 3 (MVP v2.0): Add plugin architecture for multi-tool support

   Closes correct-course analysis for 2025-11-02 mid-sprint enhancement"

   git push origin main
   ```

### After Phase 1 Complete (Epic 1-5 Done)

6. **PM Review:** Product Manager reviews FR026-FR039, approves UI scope
7. **Architect Review:** Solution Architect reviews Admin UI architecture section
8. **SM: Create Epic 6 Tech Spec:** `/bmad:bmm:workflows:tech-spec` for Epic 6
9. **SM: Draft Stories 6.1-6.8:** `/bmad:bmm:workflows:create-story` for each story
10. **Dev: Implement Epic 6:** Developer Agent implements stories sequentially
11. **TEA: Design Tests:** Test Architect designs Streamlit test strategy

### After Phase 2 Complete (Epic 6 Done)

12. **PM Review:** Validate plugin architecture requirements FR034-FR039
13. **Architect Review:** Review plugin architecture section, validate abstraction design
14. **SM: Create Epic 7 Tech Spec:** `/bmad:bmm:workflows:tech-spec` for Epic 7
15. **SM: Draft Stories 7.1-7.7:** `/bmad:bmm:workflows:create-story` for each story
16. **Dev: Implement Epic 7:** Developer Agent implements stories (includes refactoring)
17. **TEA: Design Plugin Tests:** Interface contract tests, mock plugins

---

## Approval Record

**Scrum Master (Bob):** ✅ Recommended - Phased approach balances risk and value
**Product Owner (Ravi):** ✅ Approved - 2025-11-02
**Status:** APPROVED FOR IMPLEMENTATION

---

## Appendix A: UI Wireframes

### Dashboard Page

```
┌─────────────────────────────────────────────────────────────┐
│ 🤖 AI Agents Administration          👤 Ravi    [Logout]    │
├─────────────────────────────────────────────────────────────┤
│ 📊 Dashboard │ 👥 Tenants │ 📝 History │ 🔄 Sync │ ⚙️ Settings│
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  System Health                    🔄 Auto-refresh: 5s        │
│  ──────────────────────────────────────────────────────────  │
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │ Queue Depth  │  │ Active       │  │ Success Rate │       │
│  │              │  │ Workers      │  │ (24h)        │       │
│  │    🔢 42     │  │   👷 6/10    │  │   📊 97.3%   │       │
│  │ ⚠️ High      │  │   ✅ Healthy │  │   ✅ Good    │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
│                                                               │
│  ┌──────────────┐                                            │
│  │ p95 Latency  │                                            │
│  │              │                                            │
│  │   ⏱️ 42s     │                                            │
│  │   ✅ Target  │                                            │
│  └──────────────┘                                            │
│                                                               │
│  Recent Enhancements                                         │
│  ──────────────────────────────────────────────────────────  │
│                                                               │
│  ┌─────┬─────────┬────────┬────────┬──────┬──────────────┐  │
│  │Tenant│Ticket  │Status  │Time    │Dur   │Actions       │  │
│  ├─────┼─────────┼────────┼────────┼──────┼──────────────┤  │
│  │Acme │TKT-123  │✅ Done  │2m ago  │38s   │[View Details]│  │
│  │Beta │TKT-456  │⏳ Pend  │5m ago  │-     │[View Details]│  │
│  │Acme │TKT-789  │❌ Fail  │10m ago │120s  │[View][Retry] │  │
│  └─────┴─────────┴────────┴────────┴──────┴──────────────┘  │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

### Tenant Form

```
┌───────────────────────────────────────────────────────────┐
│ Add New Tenant                                   [✕ Close] │
├───────────────────────────────────────────────────────────┤
│                                                             │
│ Tenant Information                                          │
│ ───────────────                                             │
│ * Tenant Name:    [Acme Corporation________________]        │
│ * Tenant ID:      [acme-corp___________________]            │
│                   (auto-generated from name)                │
│                                                             │
│ Tool Configuration                                          │
│ ───────────────────                                         │
│ * Ticketing Tool: [ServiceDesk Plus ▼]                      │
│                   (Phase 3: Jira, Zendesk available)        │
│                                                             │
│ * Tool URL:       [https://acme.servicedeskplus.com___]     │
│ * API Key:        [••••••••••••••••••••••••] [👁 Show]     │
│ * Webhook Secret: [sk_3e4f8a9b2c1d5e6f7g8h] [📋 Copy]      │
│                   [🔄 Generate New]                         │
│                                                             │
│                   [🔗 Test Connection]                      │
│                                                             │
│ Enhancement Preferences                                     │
│ ────────────────────────                                    │
│ * LLM Model:      [GPT-4o-mini ▼]                          │
│                   (GPT-4o-mini, GPT-4o, Claude-3.5)         │
│                                                             │
│ Max Output Words: [500_____]                                │
│ Temperature:      [0.3] ━━━●─────────── 1.0                │
│                                                             │
│ Context Gatherers:                                          │
│ ☑ Ticket History Search        Timeout: [10]s              │
│ ☑ Documentation Search          Timeout: [10]s              │
│ ☑ IP Address Lookup             Timeout: [5]s               │
│ ☐ Monitoring Data (optional)    Timeout: [15]s              │
│                                                             │
│                          [Cancel] [💾 Save Tenant]          │
└───────────────────────────────────────────────────────────┘
```

---

## Appendix B: Epic 6 Story Breakdown

### Epic 6: Admin & Operations UI

**Goal:** Provide web-based admin interface for tenant configuration and operational visibility

**Estimated Duration:** 2-3 weeks
**Stories:** 6.1-6.8

#### Story 6.1: Streamlit Setup + Authentication
**Estimate:** 2 days
**Tasks:**
- Create admin-ui/ directory structure
- Install Streamlit and dependencies
- Configure .streamlit/config.toml (theme, server settings)
- Implement basic authentication (streamlit-authenticator)
- Create multi-page navigation
- Test local deployment on port 8501

#### Story 6.2: Tenant Management CRUD
**Estimate:** 3 days
**Tasks:**
- Create Tenants page with list view
- Implement tenant form component (reusable)
- Add form validation (required fields, URL format, min lengths)
- Implement "Test Connection" button (API validation)
- Connect to FastAPI endpoints (create, read, update, delete)
- Add delete confirmation dialog
- Test full CRUD cycle

#### Story 6.3: Operations Dashboard
**Estimate:** 3 days
**Tasks:**
- Create Dashboard page with metric cards
- Fetch real-time metrics from /api/admin/metrics
- Display: queue depth, workers, success rate, p95 latency
- Add color coding (green/yellow/red based on thresholds)
- Implement auto-refresh (5 second interval)
- Add recent enhancements table
- Test with live data

#### Story 6.4: Enhancement History Viewer
**Estimate:** 2 days
**Tasks:**
- Create Enhancement History page
- Implement filters (tenant, status, date range, search)
- Display results table with pagination
- Implement expandable detail view
- Show context gathered, LLM output, error details
- Add "Download JSON" button
- Test with 1000+ records

#### Story 6.5: Bulk Import UI
**Estimate:** 2 days
**Tasks:**
- Create Sync Operations page
- Implement bulk import form (tenant, date range)
- Add "Start Import" button (triggers /api/admin/sync/ticket-history)
- Implement progress tracking (poll /api/admin/sync/status)
- Display progress bar with estimates
- Show import history table
- Test with 5000+ ticket import

#### Story 6.6: FastAPI Admin Endpoints
**Estimate:** 2 days
**Tasks:**
- Create src/api/admin.py router
- Implement /api/admin/tenants/* (CRUD)
- Implement /api/admin/enhancements (list, detail)
- Implement /api/admin/metrics (real-time)
- Implement /api/admin/sync/* (trigger, status)
- Add authentication middleware (API key or JWT)
- Write unit tests for all endpoints

#### Story 6.7: Deploy Admin UI
**Estimate:** 1 day
**Tasks:**
- Create docker/admin-ui.dockerfile
- Update docker-compose.yml (add admin-ui service)
- Create k8s/deployment-admin-ui.yaml
- Create k8s/service-admin-ui.yaml
- Update k8s/ingress.yaml (admin subdomain)
- Test deployment locally
- Deploy to staging environment
- Verify health checks

#### Story 6.8: Documentation
**Estimate:** 1 day
**Tasks:**
- Update README.md (admin UI quick start)
- Create docs/admin-ui-guide.md (operator user guide)
- Document admin API endpoints (OpenAPI)
- Create screenshots for documentation
- Write operator training guide
- Update deployment documentation

---

## Appendix C: Epic 7 Story Breakdown

### Epic 7: Multi-Tool Plugin Architecture

**Goal:** Refactor ticketing tool integration into extensible plugin architecture supporting multiple tools

**Estimated Duration:** 3-4 weeks
**Stories:** 7.1-7.7

#### Story 7.1: Plugin Base Interface + Manager
**Estimate:** 3 days
**Tasks:**
- Create src/plugins/base.py (TicketingToolPlugin ABC)
- Define interface methods (4 methods)
- Create src/plugins/plugin_manager.py (registry)
- Add tool_type column to tenant_configs (Alembic migration)
- Add tool_specific_config column (JSONB)
- Create indexes
- Write interface documentation
- Test migration rollback

#### Story 7.2: Refactor ServiceDesk Plus into Plugin
**Estimate:** 4 days
**Tasks:**
- Create src/plugins/servicedesk_plus/ directory
- Move webhook validation to plugin
- Move API client to plugin
- Implement TicketingToolPlugin interface
- Register plugin in plugin_manager
- Update src/api/webhooks.py to use plugin
- Ensure backward compatibility
- Run full regression test suite

#### Story 7.3: Implement Jira Plugin
**Estimate:** 5 days
**Tasks:**
- Create src/plugins/jira/ directory
- Implement validate_webhook (Jira webhook HMAC)
- Implement parse_webhook_payload (Jira JSON format)
- Implement update_ticket (Jira REST API)
- Implement fetch_ticket_history (JQL queries)
- Register JiraPlugin in manager
- Set up Jira sandbox for testing
- Test full workflow with Jira

#### Story 7.4: UI Plugin Selector
**Estimate:** 2 days
**Tasks:**
- Update tenant form (add tool_type dropdown)
- Populate dropdown from plugin_manager.plugins
- Add conditional fields (tool-specific config)
- Update create/edit endpoints (handle tool_type)
- Test switching tools via UI
- Validate tool-specific config

#### Story 7.5: Update Webhook Routing
**Estimate:** 3 days
**Tasks:**
- Refactor src/api/webhooks.py (use plugin_manager)
- Implement dynamic plugin selection (tenant.tool_type)
- Route validation to plugin.validate_webhook
- Route parsing to plugin.parse_webhook_payload
- Add error handling (unknown tool_type)
- Update webhook tests
- Test with both ServiceDesk Plus and Jira

#### Story 7.6: Plugin Tests + Documentation
**Estimate:** 2 days
**Tasks:**
- Create tests/unit/test_plugins.py (interface tests)
- Create tests/unit/test_servicedesk_plus_plugin.py
- Create tests/unit/test_jira_plugin.py
- Create docs/plugin-development-guide.md
- Document plugin registration
- Add plugin architecture diagram
- Write "Adding a New Tool" tutorial

#### Story 7.7: Deploy + Multi-Tool Validation
**Estimate:** 2 days
**Tasks:**
- Deploy to staging with both plugins
- Create test tenant (ServiceDesk Plus)
- Create test tenant (Jira)
- Validate webhook routing
- Validate ticket updates for both tools
- Validate bulk imports for both tools
- Production deployment
- Monitor for 24 hours

---

## Appendix D: Change Log

| Date | Author | Change | Reason |
|------|--------|--------|--------|
| 2025-11-02 | Bob (SM) + Ravi | Initial proposal created | Mid-sprint discovery of UI and multi-tool needs |
| 2025-11-02 | Ravi | Approved for implementation | Phased approach balances risk and value |

---

**End of Sprint Change Proposal**

**Next Steps:**
1. SM updates PRD, Architecture, Epics docs
2. SM commits changes to git
3. Continue Epic 2-5 implementation
4. After Phase 1: Draft Epic 6 stories
5. After Phase 2: Draft Epic 7 stories

**Questions?** Contact: Bob (Scrum Master) or Ravi (Product Owner)
