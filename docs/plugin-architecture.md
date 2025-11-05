# Plugin Architecture Guide

**Version:** 2.0
**Last Updated:** 2025-11-05
**Status:** Modular Documentation

---

## Overview

This document serves as the entry point to the AI Agents Platform plugin architecture documentation. The architecture enables support for multiple ticketing tools without modifying core enhancement logic.

**🎯 Epic 7 Objective:** Implement plugin architecture for multi-tool support (ServiceDesk Plus, Jira, future tools)

---

## Quick Start

**Choose your path:**

- 🆕 **New to plugins?** → [Plugin Development Guide](plugin-development-guide.md)
- 🔍 **Need technical reference?** → [Plugin Interface Reference](plugins/plugin-interface-reference.md)
- 🐛 **Troubleshooting?** → [Plugin Troubleshooting Guide](plugins/plugin-troubleshooting.md)
- 📚 **Browse all docs** → [Plugin Documentation Index](plugins/index.md)

---

## Documentation Structure

All plugin documentation has been modularized for better maintainability. Use the links below to navigate to specific topics:

### Core Documentation

| Document | Description | Audience |
|----------|-------------|----------|
| [Plugin Architecture Overview](plugins/plugin-architecture-overview.md) | Architecture patterns, benefits, component diagram | Architects, Developers |
| [Plugin Interface Reference](plugins/plugin-interface-reference.md) | TicketingToolPlugin ABC, TicketMetadata, abstract methods | Developers |
| [Plugin Manager Guide](plugins/plugin-manager-guide.md) | Dynamic loading, routing, registration | Developers |

### How-To Guides

| Document | Description | Topic |
|----------|-------------|-------|
| [Plugin Development Guide](plugin-development-guide.md) | Step-by-step Zendesk plugin tutorial (15 steps) | Building Plugins |
| [Plugin Type Safety Guide](plugins/plugin-type-safety.md) | Type hints, mypy validation, resolving errors | Type Safety |
| [Plugin Error Handling Guide](plugins/plugin-error-handling.md) | Exception hierarchy, retry patterns, graceful degradation | Error Handling |
| [Plugin Performance Guide](plugins/plugin-performance.md) | Connection pooling, caching, latency optimization | Performance |

### Examples & Reference

| Document | Description | Tool |
|----------|-------------|------|
| [ServiceDesk Plus Plugin Example](plugins/plugin-examples-servicedesk.md) | Complete implementation with code examples | ServiceDesk Plus |
| [Jira Service Management Plugin Example](plugins/plugin-examples-jira.md) | Complete implementation with code examples | Jira |

### Support & Planning

| Document | Description | Purpose |
|----------|-------------|---------|
| [Plugin Testing Guide](plugins/plugin-testing-guide.md) | Test strategy, coverage requirements, mock plugins | Testing |
| [Plugin Troubleshooting Guide](plugins/plugin-troubleshooting.md) | Common errors, debugging techniques | Support |
| [Plugin Submission Guidelines](plugins/plugin-submission-guidelines.md) | Code review checklist, PR process, deprecation policy | Contributing |
| [Plugin Roadmap](plugins/plugin-roadmap.md) | Planned plugins, features, versioning strategy | Planning |

---

## Architecture Summary

### Plugin Pattern

```
┌─────────────────────────────────────┐
│    FastAPI Application               │
│                                       │
│  ┌───────────────────────────────┐  │
│  │  Enhancement Workflow         │  │
│  │  (LangGraph)                  │  │
│  └──────────┬────────────────────┘  │
│             │                         │
│             ▼                         │
│  ┌───────────────────────────────┐  │
│  │  Plugin Manager               │  │
│  │  - Route by tenant tool_type  │  │
│  └──────────┬────────────────────┘  │
│             │                         │
│       ┌─────┴────┬─────────┐        │
│       ▼          ▼         ▼        │
│  ┌────────┐ ┌────────┐ ┌────────┐  │
│  │ServiceD│ │  Jira  │ │Zendesk │  │
│  │  Plus  │ │  SM    │ │(Future)│  │
│  └────────┘ └────────┘ └────────┘  │
└─────────────────────────────────────┘
```

### Key Benefits

- **Extensibility:** Add new tools by implementing interface
- **Isolation:** Tool-specific logic separated from core workflow
- **Testability:** Independent plugin testing with mocks
- **Flexibility:** Switch tools without code changes

---

## Interface Contract

All plugins implement `TicketingToolPlugin` ABC with 4 methods:

```python
class TicketingToolPlugin(ABC):
    @abstractmethod
    async def validate_webhook(self, payload: Dict, signature: str) -> bool:
        """Authenticate webhook requests"""

    @abstractmethod
    async def get_ticket(self, tenant_id: str, ticket_id: str) -> Optional[Dict]:
        """Retrieve ticket from API"""

    @abstractmethod
    async def update_ticket(self, tenant_id: str, ticket_id: str, content: str) -> bool:
        """Post enhancement content"""

    @abstractmethod
    def extract_metadata(self, payload: Dict) -> TicketMetadata:
        """Normalize ticket data"""
```

See [Plugin Interface Reference](plugins/plugin-interface-reference.md) for full details.

---

## Supported Tools

| Tool | Status | Docs |
|------|--------|------|
| ServiceDesk Plus | ✅ Production | [Example](plugins/plugin-examples-servicedesk.md) |
| Jira Service Management | ✅ Production | [Example](plugins/plugin-examples-jira.md) |
| Zendesk | 🔄 Planned Q1 2026 | [Roadmap](plugins/plugin-roadmap.md) |
| ServiceNow | 🔄 Planned Q1 2026 | [Roadmap](plugins/plugin-roadmap.md) |

---

## Development Standards

**Code Quality:**
- mypy --strict with 0 errors
- 15+ unit tests, 5+ integration tests
- 80%+ code coverage
- Files ≤500 lines

**Performance (NFR001):**
- validate_webhook: <100ms
- get_ticket: <2s
- update_ticket: <3s

See [Submission Guidelines](plugins/plugin-submission-guidelines.md) for full requirements.

---

## Getting Started

### 1. Understand the Architecture

Read [Plugin Architecture Overview](plugins/plugin-architecture-overview.md) (15 min)

### 2. Study Examples

- [ServiceDesk Plus Implementation](plugins/plugin-examples-servicedesk.md)
- [Jira Implementation](plugins/plugin-examples-jira.md)

### 3. Build Your Plugin

Follow [Plugin Development Guide](plugin-development-guide.md) (2-3 hours)

### 4. Submit for Review

See [Submission Guidelines](plugins/plugin-submission-guidelines.md)

---

## Need Help?

- 🔍 **Search:** [Documentation Index](plugins/index.md)
- 🐛 **Troubleshoot:** [Common Issues](plugins/plugin-troubleshooting.md)
- 💬 **Ask:** GitHub Discussions
- 📝 **Report:** GitHub Issues

---

## Related Documentation

- **Epic 7 Stories:** `/docs/stories/7-*.md`
- **Architecture Decisions:** `/docs/architecture.md`
- **Test Framework:** `/tests/README-plugins.md`
- **PRD:** `/docs/PRD.md` (FR034-FR039)

---

**Last Updated:** 2025-11-05 | **Version:** 2.0 | **Status:** Modular
