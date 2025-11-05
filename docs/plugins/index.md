# Plugin Architecture Documentation

**Version:** 2.0
**Last Updated:** 2025-11-05
**Status:** Modular

---

## Welcome

This documentation covers the AI Agents Platform plugin architecture, enabling support for multiple ticketing tools (ITSM systems) without modifying core enhancement logic.

**Quick Links:**
- 🚀 **New to plugins?** Start with [Development Guide](../plugin-development-guide.md)
- 📖 **Need reference?** Check [Interface Reference](plugin-interface-reference.md)
- 🔧 **Troubleshooting?** See [Troubleshooting Guide](plugin-troubleshooting.md)
- 📝 **Examples?** Browse [ServiceDesk Plus](plugin-examples-servicedesk.md) or [Jira](plugin-examples-jira.md)

---

## Documentation by Type (Diátaxis Framework)

### 📚 Tutorials (Learning-Oriented)

**Start here if you want to build your first plugin:**

- [Plugin Development Guide](../plugin-development-guide.md) - Step-by-step Zendesk plugin tutorial (15 steps)

### 🛠 How-To Guides (Problem-Oriented)

**Solve specific problems:**

- [Plugin Manager Guide](plugin-manager-guide.md) - Dynamic loading, routing, registration
- [Type Safety Guide](plugin-type-safety.md) - Type hints, mypy validation, resolving errors
- [Error Handling Guide](plugin-error-handling.md) - Exception hierarchy, retry patterns, graceful degradation
- [Performance Guide](plugin-performance.md) - Connection pooling, caching, latency optimization

### 📖 Reference (Information-Oriented)

**Look up technical details:**

- [Plugin Interface Reference](plugin-interface-reference.md) - TicketingToolPlugin ABC, TicketMetadata, abstract methods
- [ServiceDesk Plus Example](plugin-examples-servicedesk.md) - Complete implementation reference
- [Jira Service Management Example](plugin-examples-jira.md) - Complete implementation reference

### 💡 Explanation (Understanding-Oriented)

**Understand the architecture:**

- [Plugin Architecture Overview](plugin-architecture-overview.md) - Why plugin architecture, benefits, patterns

### 🔍 Support (Problem-Solving)

**Get help:**

- [Troubleshooting Guide](plugin-troubleshooting.md) - Common errors, debugging techniques
- [Testing Guide](plugin-testing-guide.md) - Test strategy, coverage requirements, mock plugins

### 📋 Planning (Future-Oriented)

**Plan and contribute:**

- [Plugin Roadmap](plugin-roadmap.md) - Planned plugins, features, versioning strategy
- [Submission Guidelines](plugin-submission-guidelines.md) - Code review checklist, PR process, deprecation policy

---

## Quick Start Paths

### Path 1: "I want to build my first plugin"

1. Read [Plugin Architecture Overview](plugin-architecture-overview.md) (15 min)
2. Follow [Development Guide](../plugin-development-guide.md) (2-3 hours)
3. Reference [Interface Documentation](plugin-interface-reference.md) as needed
4. Check [Troubleshooting Guide](plugin-troubleshooting.md) if stuck

### Path 2: "I need to understand existing plugins"

1. Review [Plugin Interface Reference](plugin-interface-reference.md) (20 min)
2. Study [ServiceDesk Plus Example](plugin-examples-servicedesk.md) (30 min)
3. Compare with [Jira Example](plugin-examples-jira.md) (30 min)
4. Read [Plugin Manager Guide](plugin-manager-guide.md) (20 min)

### Path 3: "I'm fixing bugs or improving performance"

1. Check [Troubleshooting Guide](plugin-troubleshooting.md) first
2. Review [Error Handling Guide](plugin-error-handling.md)
3. Optimize using [Performance Guide](plugin-performance.md)
4. Validate with [Testing Guide](plugin-testing-guide.md)

### Path 4: "I want to contribute a new plugin"

1. Review [Roadmap](plugin-roadmap.md) - Check if plugin already planned
2. Follow [Development Guide](../plugin-development-guide.md)
3. Meet requirements in [Submission Guidelines](plugin-submission-guidelines.md)
4. Submit PR following checklist

---

## Supported Tools

| Tool | Status | Version | Documentation |
|------|--------|---------|---------------|
| ServiceDesk Plus | ✅ Production | 1.0 | [Example](plugin-examples-servicedesk.md) |
| Jira Service Management | ✅ Production | 1.0 | [Example](plugin-examples-jira.md) |
| Zendesk | 🔄 Planned Q1 2026 | - | [Roadmap](plugin-roadmap.md) |
| ServiceNow | 🔄 Planned Q1 2026 | - | [Roadmap](plugin-roadmap.md) |
| Freshservice | 📋 Backlog Q2 2026 | - | [Roadmap](plugin-roadmap.md) |
| Freshdesk | 📋 Backlog Q2 2026 | - | [Roadmap](plugin-roadmap.md) |

---

## Core Concepts

### TicketingToolPlugin Interface

All plugins implement 4 abstract methods:
- `validate_webhook()` - Authenticate webhook requests
- `get_ticket()` - Retrieve ticket from API
- `update_ticket()` - Post enhancement content
- `extract_metadata()` - Normalize ticket data

See [Interface Reference](plugin-interface-reference.md) for details.

### Plugin Manager

Routes requests to correct plugin based on tenant configuration. See [Plugin Manager Guide](plugin-manager-guide.md).

### TicketMetadata

Standardized data structure for enhancement workflow:
- tenant_id, ticket_id, description, priority, created_at

---

## Development Standards

### Code Quality

- **Type Safety:** mypy --strict with 0 errors
- **Testing:** 15+ unit tests, 5+ integration tests, 80%+ coverage
- **Performance:** validate_webhook <100ms, get_ticket <2s
- **Security:** secrets.compare_digest(), no hardcoded credentials
- **File Size:** ≤500 lines per file

### Documentation Standards

- Google-style docstrings
- README.md in plugin directory
- Implementation examples
- API endpoint documentation

---

## Resources

### Internal Documentation

- Epic 7 Stories: `/docs/stories/7-*.md`
- Architecture Decisions: `/docs/architecture.md`
- Test Framework: `/tests/README-plugins.md`

### External Resources

- [Python ABC Module](https://docs.python.org/3/library/abc.html)
- [mypy Documentation](https://mypy.readthedocs.io/)
- [httpx Async Client](https://www.python-httpx.org/)

---

## Getting Help

1. **Search Documentation:** Use sidebar or Ctrl+F
2. **Check Troubleshooting:** [Common issues and solutions](plugin-troubleshooting.md)
3. **GitHub Issues:** Search existing issues
4. **GitHub Discussions:** Ask questions
5. **Code Examples:** Review [ServiceDesk Plus](plugin-examples-servicedesk.md) or [Jira](plugin-examples-jira.md)

---

## Contributing

We welcome plugin contributions! See [Submission Guidelines](plugin-submission-guidelines.md) for:
- Code review checklist
- PR process
- Documentation requirements
- Performance standards

---

**Need Help?** Check [Troubleshooting Guide](plugin-troubleshooting.md) or open a GitHub Discussion.
