# Plugin Roadmap

[Plugin Docs](index.md) > Planning > Roadmap

**Last Updated:** 2025-11-05

---

## Overview

This roadmap outlines planned plugin implementations, features, and improvements for the AI Agents Platform plugin architecture.

---

## Completed (2025 Q4)

### Epic 7: Plugin Architecture Foundation

**Status:** ✅ Complete

- [x] Story 7.1: Plugin Base Interface (TicketingToolPlugin ABC)
- [x] Story 7.2: Plugin Manager and Registry
- [x] Story 7.3: ServiceDesk Plus Plugin Migration
- [x] Story 7.4: Jira Service Management Plugin
- [x] Story 7.5: Database Schema Multi-Tool Support
- [x] Story 7.6: Plugin Testing Framework
- [x] Story 7.7: Plugin Architecture Documentation

---

## Q1 2026: Priority 1 Plugins

### Zendesk Plugin (2 weeks)

**Priority:** High
**Effort:** 2 weeks
**Status:** 🔄 Planned

**Requirements:**
- Zendesk Support API integration
- JWT-based webhook validation
- Rich text formatting support
- Custom fields mapping
- SLA tracking integration

**Implementation:**
```
src/plugins/zendesk/
├── __init__.py
├── plugin.py
├── api_client.py
├── webhook_validator.py
└── README.md
```

**Deliverables:**
- Zendesk plugin implementation
- 20+ unit tests, 5+ integration tests
- API documentation
- Migration guide from ServiceDesk Plus

### ServiceNow Plugin (2 weeks)

**Priority:** High
**Effort:** 2 weeks
**Status:** 🔄 Planned

**Requirements:**
- ServiceNow REST API v2 integration
- OAuth 2.0 authentication
- Incident/Change Request support
- CMDB integration for device context
- Attachment handling

**Implementation:**
```
src/plugins/servicenow/
├── __init__.py
├── plugin.py
├── api_client.py
├── webhook_validator.py
├── cmdb_client.py
└── README.md
```

**Deliverables:**
- ServiceNow plugin implementation
- CMDB context enrichment
- 25+ unit tests, 7+ integration tests
- OAuth flow documentation

---

## Q2 2026: Priority 2 Plugins

### Freshservice Plugin (1.5 weeks)

**Priority:** Medium
**Effort:** 1.5 weeks
**Status:** 📋 Backlog

**Requirements:**
- Freshservice API v2 integration
- API key authentication
- Ticket + Problem + Change support
- Asset management integration

### Freshdesk Plugin (1.5 weeks)

**Priority:** Medium
**Effort:** 1.5 weeks
**Status:** 📋 Backlog

**Requirements:**
- Freshdesk API v2 integration
- Multi-brand support
- Forum post integration
- Customer portal sync

---

## Q3 2026: Priority 3 Plugins

### TOPdesk Plugin (1 week)

**Priority:** Low
**Effort:** 1 week
**Status:** 📋 Backlog

**Requirements:**
- TOPdesk API integration
- Dutch/English localization
- Operator change tracking

### SysAid Plugin (1 week)

**Priority:** Low
**Effort:** 1 week
**Status:** 📋 Backlog

**Requirements:**
- SysAid REST API integration
- LDAP/AD integration support
- Asset lifecycle tracking

### Cherwell Plugin (1 week)

**Priority:** Low
**Effort:** 1 week
**Status:** 📋 Backlog

**Requirements:**
- Cherwell REST API integration
- Custom object type support
- Business process workflow integration

---

## Future Features

### Plugin Hot-Reloading (Q4 2026)

**Description:** Reload plugins without service restart

**Features:**
- Dynamic plugin loading
- Version management
- A/B testing for plugin implementations
- Rollback capability

**Implementation:**
```python
class PluginManager:
    async def reload_plugin(self, tool_type: str) -> bool:
        """Hot-reload plugin without downtime."""
        ...

    async def enable_ab_test(self, tool_type: str, versions: List[str]) -> None:
        """A/B test multiple plugin versions."""
        ...
```

### Custom Plugin Development (Q4 2026)

**Description:** Generic webhook handler for custom integrations

**Features:**
- YAML-based plugin configuration
- No-code webhook mapping
- Field transformation rules
- Custom authentication methods

**Example:**
```yaml
# plugins/custom/my-itsm.yaml
name: "My Custom ITSM"
tool_type: "custom_itsm"
webhook:
  signature_header: "X-Custom-Signature"
  algorithm: "hmac-sha256"
field_mappings:
  tenant_id: "$.organization.id"
  ticket_id: "$.ticket.number"
  priority: "$.ticket.urgency"
api:
  base_url: "https://api.my-itsm.com"
  auth_type: "bearer"
  endpoints:
    get_ticket: "/api/v1/tickets/{ticket_id}"
    update_ticket: "/api/v1/tickets/{ticket_id}/notes"
```

### Plugin Marketplace (Q1 2027)

**Description:** Community-contributed plugin repository

**Features:**
- Plugin submission process
- Certification/verification
- Plugin discovery
- Installation via CLI
- Ratings and reviews

**Installation:**
```bash
# Install from marketplace
ai-agents plugin install zendesk --version 1.2.0

# List available plugins
ai-agents plugin list --marketplace

# Update plugin
ai-agents plugin update zendesk
```

---

## Versioning Strategy

### Semantic Versioning

**Format:** MAJOR.MINOR.PATCH

**Rules:**
- **MAJOR:** Breaking changes (e.g., remove method, change signature)
- **MINOR:** New features (backward compatible)
- **PATCH:** Bug fixes (backward compatible)

**Example:**
- v1.0.0 → v1.1.0: Add batch_update_tickets() method
- v1.1.0 → v1.1.1: Fix webhook validation bug
- v1.1.1 → v2.0.0: Remove deprecated method

### Breaking Changes

**Deprecation Policy:**
- 6-month notice before removal
- Migration guide provided
- Deprecated methods marked with `@deprecated` decorator

**Example:**
```python
from deprecated import deprecated


@deprecated(version='2.0.0', reason="Use get_ticket_batch() instead")
async def get_ticket(self, ticket_id: str) -> Dict:
    ...
```

---

## Deprecation Schedule

### v1.0.0 → v2.0.0 (Q2 2026)

**Deprecated:**
- `TicketingToolPlugin.get_custom_headers()` → Removed (use middleware)
- `extract_metadata()` return `dict` → Changed to `TicketMetadata` dataclass

**Migration:**
```python
# v1.0.0 (deprecated)
metadata = plugin.extract_metadata(payload)
tenant_id = metadata["tenant_id"]

# v2.0.0 (new)
metadata = plugin.extract_metadata(payload)
tenant_id = metadata.tenant_id  # Dataclass attribute
```

---

## Community Contributions

### Contribution Process

1. **Propose Plugin:** Open GitHub Discussion with use case
2. **Review:** Team reviews feasibility + demand
3. **Approval:** If approved, plugin added to roadmap
4. **Development:** Follow [Submission Guidelines](plugin-submission-guidelines.md)
5. **Code Review:** Minimum 2 approvals required
6. **Testing:** 15+ unit tests, 5+ integration tests, 80%+ coverage
7. **Documentation:** Complete plugin documentation
8. **Merge:** Merged to `main`, released in next version

### Recognition

**Contributors receive:**
- Credit in CHANGELOG.md
- GitHub contributor badge
- Listed in plugin AUTHORS file
- Priority support for their contributions

### Plugin Ownership

**Responsibilities:**
- Maintain compatibility with new platform versions
- Fix bugs within 2 weeks of report
- Respond to issues within 1 week
- Update documentation as needed

**If unmaintained:**
- Plugin marked as "Community Maintained"
- Open for new maintainer adoption
- May be archived if no maintainer found

---

## Performance Targets

### Current (Baseline)

| Metric | Target | Actual |
|--------|--------|--------|
| webhook_validation | <100ms | 45-52ms |
| get_ticket | <2s | 850-920ms |
| update_ticket | <5s | 1.2-1.4s |
| Plugin load time | <500ms | 120ms |

### Future (Q2 2026)

| Metric | Target | Notes |
|--------|--------|-------|
| webhook_validation | <50ms | Improved caching |
| get_ticket | <1s | Connection pooling |
| update_ticket | <3s | Batch operations |
| Plugin load time | <200ms | Lazy loading |

---

## Research & Exploration

### Multi-Tool Routing (Q3 2026)

**Description:** Route to different plugins per tenant based on rules

**Use Case:**
- Tenant uses Jira for incidents, ServiceNow for changes
- Route based on ticket priority (Jira for P1, ServiceDesk for P2-P4)
- Failover to backup tool if primary unavailable

**Implementation:**
```python
class RoutingRule:
    def should_route_to(self, metadata: TicketMetadata) -> str:
        if metadata.priority == "high":
            return "jira"
        return "servicedesk_plus"
```

### Plugin Analytics (Q4 2026)

**Description:** Built-in analytics for plugin usage

**Metrics:**
- Most used methods
- Average latency by method
- Error rates by plugin
- API call costs

---

## See Also

- [Plugin Submission Guidelines](plugin-submission-guidelines.md)
- [Plugin Development Guide](../plugin-development-guide.md)
- [Epic 7 Documentation](../stories/7-1-design-and-implement-plugin-base-interface.md)
