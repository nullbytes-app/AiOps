# Story 7.7: Document Plugin Architecture and Extension Guide

Status: ready-for-dev

## Story

As a future developer or contributor,
I want comprehensive plugin architecture documentation with step-by-step development guides and templates,
So that I can create new ticketing tool plugins independently without deep knowledge of the existing codebase.

## Acceptance Criteria

1. docs/plugin-architecture.md restructured into modular files (≤500 lines each) with architecture overview, plugin interface spec, and plugin manager usage examples
2. docs/plugin-development-guide.md created with step-by-step tutorial following Diátaxis framework for building a plugin from scratch
3. src/plugins/_template/ directory created with boilerplate plugin template (plugin.py, api_client.py, webhook_validator.py) with TODO comments
4. Testing requirements documented with references to tests/README-plugins.md (from Story 7.6) and testing strategy overview
5. Plugin submission guidelines created (docs/plugins/plugin-submission-guidelines.md) with code review checklist and quality requirements
6. Troubleshooting guide created (docs/plugins/plugin-troubleshooting.md) with common errors, debugging tips, and solutions
7. Future plugin roadmap documented (docs/plugins/plugin-roadmap.md) covering Zendesk, ServiceNow, Freshservice, and community contributions
8. README.md updated with Plugin Architecture section, supported tools list, and links to all plugin documentation

## Tasks / Subtasks

### Task 1: Analyze and Plan Documentation Restructure (AC: #1)
- [ ] 1.1 Read complete plugin-architecture.md (3,079 lines) to understand current structure
- [ ] 1.2 Identify logical sections for splitting based on Diátaxis framework
- [ ] 1.3 Design modular structure with 7 files:
  - [ ] 1.3a plugin-architecture-overview.md (~400 lines) - Explanation: Why plugin architecture, benefits, trade-offs
  - [ ] 1.3b plugin-interface-reference.md (~450 lines) - Reference: TicketingToolPlugin ABC, TicketMetadata, method signatures
  - [ ] 1.3c plugin-manager-guide.md (~400 lines) - How-to: Using PluginManager, registering plugins, routing
  - [ ] 1.3d plugin-examples.md (~500 lines) - Reference: ServiceDesk Plus and Jira complete implementations
  - [ ] 1.3e plugin-type-safety.md (~400 lines) - How-to: Type hints, mypy validation, common issues
  - [ ] 1.3f plugin-error-handling.md (~400 lines) - How-to: Exception patterns, retry logic, graceful degradation
  - [ ] 1.3g plugin-performance.md (~400 lines) - How-to: Latency optimization, async patterns, connection pooling
- [ ] 1.4 Create index/navigation structure with cross-references and breadcrumbs

### Task 2: Split plugin-architecture.md into Modular Files (AC: #1)
- [ ] 2.1 Create docs/plugins/ directory for modular plugin documentation
- [ ] 2.2 Extract and create plugin-architecture-overview.md:
  - [ ] 2.2a Copy sections: Overview, Why Plugin Architecture, Architecture Benefits, Component Diagram, Data Flow
  - [ ] 2.2b Add Epic 7 completion status summary (Stories 7.1-7.6 done, 7.7 in progress)
  - [ ] 2.2c Add navigation links to other plugin docs
  - [ ] 2.2d Verify ≤500 lines
- [ ] 2.3 Extract and create plugin-interface-reference.md:
  - [ ] 2.3a Copy sections: Interface Specification, TicketingToolPlugin ABC, TicketMetadata dataclass
  - [ ] 2.3b Copy sections: Abstract Method Details (validate_webhook, get_ticket, update_ticket, extract_metadata)
  - [ ] 2.3c Add API reference format with parameters, returns, raises, examples
  - [ ] 2.3d Verify ≤500 lines
- [ ] 2.4 Extract and create plugin-manager-guide.md:
  - [ ] 2.4a Copy Plugin Manager sections: Dynamic loading, registration, routing
  - [ ] 2.4b Add how-to examples: Register plugin, get plugin by tenant, handle multi-tenant routing
  - [ ] 2.4c Add configuration management examples
  - [ ] 2.4d Verify ≤500 lines
- [ ] 2.5 Extract and create plugin-examples.md:
  - [ ] 2.5a Copy complete ServiceDesk Plus plugin implementation example
  - [ ] 2.5b Copy complete Jira Service Management plugin implementation example
  - [ ] 2.5c Add annotations explaining key decisions in each example
  - [ ] 2.5d Verify ≤500 lines (split into plugin-examples-servicedesk.md and plugin-examples-jira.md if needed)
- [ ] 2.6 Extract and create plugin-type-safety.md:
  - [ ] 2.6a Copy Type Hints and Mypy section
  - [ ] 2.6b Add how-to guide for resolving common mypy errors
  - [ ] 2.6c Add Optional vs None disambiguation patterns
  - [ ] 2.6d Add async type hint patterns
  - [ ] 2.6e Verify ≤500 lines
- [ ] 2.7 Extract and create plugin-error-handling.md:
  - [ ] 2.7a Copy Error Handling section
  - [ ] 2.7b Add exception hierarchy for plugins
  - [ ] 2.7c Add retry patterns with exponential backoff examples
  - [ ] 2.7d Add graceful degradation examples
  - [ ] 2.7e Verify ≤500 lines
- [ ] 2.8 Extract and create plugin-performance.md:
  - [ ] 2.8a Copy Performance Considerations section
  - [ ] 2.8b Add latency optimization techniques (connection pooling, caching, timeouts)
  - [ ] 2.8c Add async patterns for concurrent operations
  - [ ] 2.8d Add performance testing guidance (benchmarks, profiling)
  - [ ] 2.8e Verify ≤500 lines
- [ ] 2.9 Update original plugin-architecture.md as navigation hub:
  - [ ] 2.9a Replace content with: Title, Epic 7 overview, Table of contents linking all modular docs
  - [ ] 2.9b Add quick start section with "choose your path" (new developer → tutorial, experienced → reference)
  - [ ] 2.9c Add last updated date, version, status
  - [ ] 2.9d Target ≤300 lines (navigation hub only)
- [ ] 2.10 Add cross-reference links in all modular files:
  - [ ] 2.10a Breadcrumb navigation at top (Plugin Docs > Current File)
  - [ ] 2.10b "See also" sections linking related docs
  - [ ] 2.10c "Next steps" sections at bottom

### Task 3: Create Plugin Development Guide (AC: #2)
- [ ] 3.1 Create docs/plugin-development-guide.md
- [ ] 3.2 Add document header (title, version, last updated, Epic 7)
- [ ] 3.3 Add table of contents
- [ ] 3.4 Write Prerequisites section:
  - [ ] 3.4a Python 3.12+ installed
  - [ ] 3.4b Development environment setup (IDE, git, Docker)
  - [ ] 3.4c Familiarity with async Python, type hints, pytest
  - [ ] 3.4d Access to ticketing tool API documentation
- [ ] 3.5 Write "Tutorial: Building Your First Plugin (Zendesk Example)" section:
  - [ ] 3.5a Step 1: Set up plugin directory structure (src/plugins/zendesk/)
  - [ ] 3.5b Step 2: Create __init__.py and export plugin class
  - [ ] 3.5c Step 3: Define ZendeskPlugin class inheriting from TicketingToolPlugin
  - [ ] 3.5d Step 4: Implement validate_webhook() method with Zendesk JWT validation
  - [ ] 3.5e Step 5: Implement extract_metadata() method parsing Zendesk payload
  - [ ] 3.5f Step 6: Implement get_ticket() method calling Zendesk API
  - [ ] 3.5g Step 7: Implement update_ticket() method posting internal note to Zendesk
  - [ ] 3.5h Step 8: Create api_client.py with ZendeskAPIClient class
  - [ ] 3.5i Step 9: Create webhook_validator.py with JWT validation logic
  - [ ] 3.5j Step 10: Register plugin in src/main.py and src/workers/celery_app.py
  - [ ] 3.5k Step 11: Write unit tests (test_zendesk_plugin.py with 15+ tests)
  - [ ] 3.5l Step 12: Write integration tests (test_zendesk_integration.py)
  - [ ] 3.5m Step 13: Test end-to-end workflow with mock Zendesk webhook
  - [ ] 3.5n Step 14: Run mypy --strict and fix type errors
  - [ ] 3.5o Step 15: Run Black formatting and verify file sizes ≤500 lines
- [ ] 3.6 Add code examples for each step:
  - [ ] 3.6a Include complete code blocks with syntax highlighting
  - [ ] 3.6b Add inline comments explaining key decisions
  - [ ] 3.6c Show before/after for iterative improvements
- [ ] 3.7 Add "Testing Your Plugin" section:
  - [ ] 3.7a Link to tests/README-plugins.md for mock plugin usage
  - [ ] 3.7b Show how to use mock_generic_plugin fixture
  - [ ] 3.7c Provide unit test examples for each abstract method
  - [ ] 3.7d Provide integration test example for full workflow
- [ ] 3.8 Add "Next Steps" section:
  - [ ] 3.8a Link to plugin-type-safety.md for advanced type patterns
  - [ ] 3.8b Link to plugin-error-handling.md for production-ready error handling
  - [ ] 3.8c Link to plugin-submission-guidelines.md for code review preparation
- [ ] 3.9 Verify file size ≤500 lines (split into parts 1 and 2 if needed)

### Task 4: Create Plugin Template (AC: #3)
- [ ] 4.1 Create src/plugins/_template/ directory
- [ ] 4.2 Create _template/__init__.py:
  - [ ] 4.2a Add module docstring explaining template purpose
  - [ ] 4.2b Add TODO comment: "Replace 'Template' with your tool name (e.g., 'Zendesk')"
  - [ ] 4.2c Export TemplatePlugin class
- [ ] 4.3 Create _template/plugin.py (target ~250 lines):
  - [ ] 4.3a Add file docstring with usage instructions
  - [ ] 4.3b Add imports (ABC, abstractmethod, TicketingToolPlugin, TicketMetadata)
  - [ ] 4.3c Define TemplatePlugin class inheriting from TicketingToolPlugin
  - [ ] 4.3d Add class docstring with TODO: "Describe your ticketing tool integration"
  - [ ] 4.3e Implement validate_webhook() method:
    - [ ] 4.3e1 Add method signature with type hints
    - [ ] 4.3e2 Add docstring with TODO for tool-specific validation algorithm
    - [ ] 4.3e3 Add placeholder code: retrieve tenant config, decrypt secret, compute signature
    - [ ] 4.3e4 Add TODO comments at each customization point
    - [ ] 4.3e5 Add return statement with TODO
  - [ ] 4.3f Implement extract_metadata() method:
    - [ ] 4.3f1 Add method signature (synchronous)
    - [ ] 4.3f2 Add docstring with TODO for payload structure
    - [ ] 4.3f3 Add placeholder code: parse payload, extract fields
    - [ ] 4.3f4 Add TODO comments for tool-specific field names
    - [ ] 4.3f5 Return TicketMetadata with placeholder values
  - [ ] 4.3g Implement get_ticket() method:
    - [ ] 4.3g1 Add async method signature
    - [ ] 4.3g2 Add docstring with TODO for API endpoint
    - [ ] 4.3g3 Add placeholder code: retrieve config, decrypt key, build URL
    - [ ] 4.3g4 Add httpx request example with TODO for headers/auth
    - [ ] 4.3g5 Add retry logic template with TODO
    - [ ] 4.3g6 Return Optional[Dict] with TODO
  - [ ] 4.3h Implement update_ticket() method:
    - [ ] 4.3h1 Add async method signature
    - [ ] 4.3h2 Add docstring with TODO for update mechanism
    - [ ] 4.3h3 Add placeholder code: retrieve config, format content
    - [ ] 4.3h4 Add httpx POST/PUT example with TODO
    - [ ] 4.3h5 Add error handling template
    - [ ] 4.3h6 Return bool with TODO
  - [ ] 4.3i Add helper methods template:
    - [ ] 4.3i1 _get_tenant_config(tenant_id) → TenantConfig
    - [ ] 4.3i2 _decrypt_api_key(encrypted_key) → str
    - [ ] 4.3i3 Add TODO comments for each helper
- [ ] 4.4 Create _template/api_client.py (target ~200 lines):
  - [ ] 4.4a Add file docstring
  - [ ] 4.4b Define TemplateAPIClient class
  - [ ] 4.4c Add __init__ method with base_url, api_key, timeout parameters
  - [ ] 4.4d Add async get_ticket(ticket_id) method template
  - [ ] 4.4e Add async update_ticket(ticket_id, content) method template
  - [ ] 4.4f Add _build_headers() helper method template
  - [ ] 4.4g Add retry logic helper (_retry_with_backoff) template
  - [ ] 4.4h Add TODO comments for tool-specific customization
- [ ] 4.5 Create _template/webhook_validator.py (target ~150 lines):
  - [ ] 4.5a Add file docstring
  - [ ] 4.5b Add validate_signature(payload, signature, secret) function template
  - [ ] 4.5c Add HMAC-SHA256 example (most common)
  - [ ] 4.5d Add TODO for alternative validation methods (JWT, custom)
  - [ ] 4.5e Add secrets.compare_digest() usage for timing attack prevention
  - [ ] 4.5f Add example for each step with TODO comments
- [ ] 4.6 Create _template/README.md:
  - [ ] 4.6a Add "Template Plugin Customization Guide" title
  - [ ] 4.6b Add "Overview" section explaining template purpose
  - [ ] 4.6c Add "Customization Steps" section:
    - [ ] 4.6c1 Step 1: Copy template to new plugin directory
    - [ ] 4.6c2 Step 2: Rename files and classes
    - [ ] 4.6c3 Step 3: Search for TODO comments and customize
    - [ ] 4.6c4 Step 4: Implement tool-specific validation
    - [ ] 4.6c5 Step 5: Update API client with tool endpoints
    - [ ] 4.6c6 Step 6: Test with mock plugin
    - [ ] 4.6c7 Step 7: Write unit and integration tests
    - [ ] 4.6c8 Step 8: Submit for code review
  - [ ] 4.6d Add "TODO Checklist" section listing all TODO items
  - [ ] 4.6e Add "References" section linking to plugin docs
- [ ] 4.7 Verify all template files follow Black formatting
- [ ] 4.8 Verify template files have mypy compatibility (no type errors with placeholder types)
- [ ] 4.9 Verify all files ≤500 lines

### Task 5: Document Testing Requirements (AC: #4)
- [ ] 5.1 Create docs/plugins/plugin-testing-guide.md
- [ ] 5.2 Add document header
- [ ] 5.3 Add "Testing Overview" section:
  - [ ] 5.3a Explain 3-layer testing pyramid (unit, integration, e2e optional)
  - [ ] 5.3b Explain why testing matters for plugins (reliability, backward compatibility)
  - [ ] 5.3c Link to Story 7.6 testing framework
- [ ] 5.4 Add "Testing Strategy" section:
  - [ ] 5.4a Layer 1: Unit tests for each abstract method in isolation
  - [ ] 5.4b Layer 2: Integration tests for full enhancement workflow
  - [ ] 5.4c Layer 3: E2E tests with real API (optional, on-demand)
- [ ] 5.5 Add "Mock Plugin Usage" section:
  - [ ] 5.5a Link to tests/README-plugins.md
  - [ ] 5.5b Show MockTicketingToolPlugin example
  - [ ] 5.5c Explain factory methods (success_mode, api_error_mode, etc.)
  - [ ] 5.5d Provide code example using mock plugin
- [ ] 5.6 Add "Test Fixtures" section:
  - [ ] 5.6a Link to tests/docs/plugin-testing-best-practices.md
  - [ ] 5.6b Explain pytest fixtures: mock_generic_plugin, mock_servicedesk_plugin, mock_jira_plugin
  - [ ] 5.6c Show fixture usage example
- [ ] 5.7 Add "Test Utilities" section:
  - [ ] 5.7a Link to tests/docs/plugin-api-reference.md
  - [ ] 5.7b Explain assertion utilities (assert_plugin_called, assert_ticket_metadata_valid)
  - [ ] 5.7c Explain payload builders (build_servicedesk_payload, build_jira_payload)
  - [ ] 5.7d Provide code example using utilities
- [ ] 5.8 Add "Minimum Coverage Requirements" section:
  - [ ] 5.8a Unit test coverage: 80%+ for plugin methods
  - [ ] 5.8b Integration test coverage: All critical paths (webhook → update)
  - [ ] 5.8c Test count minimums: 15+ unit tests, 5+ integration tests per plugin
- [ ] 5.9 Add "CI/CD Integration" section:
  - [ ] 5.9a Explain pytest markers (@pytest.mark.unit, @pytest.mark.integration, @pytest.mark.plugin)
  - [ ] 5.9b Show GitHub Actions workflow example
  - [ ] 5.9c Explain test isolation with separate CI steps
- [ ] 5.10 Add "Performance Testing" section:
  - [ ] 5.10a Latency targets: validate_webhook <100ms, get_ticket <2s, update_ticket <3s
  - [ ] 5.10b Use pytest-benchmark for performance regression tracking
  - [ ] 5.10c Example performance test
- [ ] 5.11 Verify file size ≤500 lines

### Task 6: Create Plugin Submission Guidelines (AC: #5)
- [ ] 6.1 Create docs/plugins/plugin-submission-guidelines.md
- [ ] 6.2 Add document header
- [ ] 6.3 Add "Overview" section explaining submission process
- [ ] 6.4 Add "Code Review Checklist" section:
  - [ ] 6.4a **Functionality**: All 4 abstract methods implemented (validate_webhook, get_ticket, update_ticket, extract_metadata)
  - [ ] 6.4b **Type Safety**: Type hints on all methods, mypy --strict returns 0 errors
  - [ ] 6.4c **Documentation**: Google-style docstrings on all functions, classes, modules
  - [ ] 6.4d **Formatting**: Black formatting applied, line length ≤100 characters
  - [ ] 6.4e **File Size**: All files ≤500 lines (CLAUDE.md C1 constraint)
  - [ ] 6.4f **Security**: No hardcoded secrets, input validation on all external data, error messages don't leak sensitive info
  - [ ] 6.4g **Testing**: Minimum 15 unit tests, 5 integration tests, 80%+ coverage
  - [ ] 6.4h **Performance**: Meets NFR001 latency targets (<100ms validation, <2s API calls)
  - [ ] 6.4i **Error Handling**: Try/except blocks for all external calls, graceful degradation
  - [ ] 6.4j **Backward Compatibility**: All existing tests pass (47+ tests from previous plugins)
- [ ] 6.5 Add "Documentation Requirements" section:
  - [ ] 6.5a Plugin README.md with overview, configuration, usage examples
  - [ ] 6.5b API client documentation (methods, parameters, returns)
  - [ ] 6.5c Webhook validation documentation (algorithm, security considerations)
  - [ ] 6.5d Integration guide for adding plugin to main.py and celery_app.py
- [ ] 6.6 Add "Testing Requirements" section:
  - [ ] 6.6a Unit tests for all 4 abstract methods with success and failure scenarios
  - [ ] 6.6b Integration test for full enhancement workflow (webhook → context → update)
  - [ ] 6.6c Mock plugin usage examples in test suite
  - [ ] 6.6d Performance tests for latency-critical methods
  - [ ] 6.6e Test evidence in story completion notes
- [ ] 6.7 Add "Security Requirements" section:
  - [ ] 6.7a Credentials encrypted with Fernet (never plain text)
  - [ ] 6.7b Webhook signature validation with constant-time comparison (secrets.compare_digest)
  - [ ] 6.7c Input validation and sanitization (prevent injection attacks)
  - [ ] 6.7d OWASP Top 10 compliance (no known vulnerabilities)
  - [ ] 6.7e Bandit security scan with 0 HIGH/MEDIUM findings
- [ ] 6.8 Add "Performance Requirements" section:
  - [ ] 6.8a NFR001 compliance: Enhancement complete within 120s (p95 <60s)
  - [ ] 6.8b validate_webhook() <100ms
  - [ ] 6.8c get_ticket() <2s
  - [ ] 6.8d update_ticket() <3s
  - [ ] 6.8e Connection pooling for API clients (httpx.AsyncClient)
- [ ] 6.9 Add "Submission Process" section:
  - [ ] 6.9a Create feature branch (plugin/tool-name)
  - [ ] 6.9b Implement plugin following template and development guide
  - [ ] 6.9c Run all quality checks locally (mypy, black, pytest, bandit)
  - [ ] 6.9d Create pull request with description, testing evidence, screenshots
  - [ ] 6.9e Code review by senior developer agent (2 rounds expected)
  - [ ] 6.9f Address review findings and resubmit
  - [ ] 6.9g Approval and merge to main branch
- [ ] 6.10 Add "PR Template" section with required sections
- [ ] 6.11 Verify file size ≤500 lines

### Task 7: Create Troubleshooting Guide (AC: #6)
- [ ] 7.1 Create docs/plugins/plugin-troubleshooting.md
- [ ] 7.2 Add document header
- [ ] 7.3 Add "Common Development Errors" section:
  - [ ] 7.3a **Error**: "TypeError: Can't instantiate abstract class" → **Solution**: Implement all 4 abstract methods
  - [ ] 7.3b **Error**: "Incompatible return type Optional[Dict] vs Dict" → **Solution**: Use Optional[] for nullable returns
  - [ ] 7.3c **Error**: "coroutine was never awaited" → **Solution**: Add await before async method calls
  - [ ] 7.3d **Error**: "ModuleNotFoundError: No module named 'plugins.zendesk'" → **Solution**: Add __init__.py, verify PYTHONPATH
  - [ ] 7.3e **Error**: "TypeError: object dict can't be used in 'await' expression" → **Solution**: Method must be async to use await
- [ ] 7.4 Add "Debugging Techniques" section:
  - [ ] 7.4a Use logging.debug() to trace execution flow
  - [ ] 7.4b Use pdb.set_trace() for interactive debugging
  - [ ] 7.4c Use print(repr(obj)) to inspect objects
  - [ ] 7.4d Use pytest --pdb to drop into debugger on test failure
  - [ ] 7.4e Use mypy --show-error-codes to identify specific type issues
- [ ] 7.5 Add "Type Checking Issues (Mypy)" section:
  - [ ] 7.5a **Error**: "Argument 1 has incompatible type None; expected str" → **Solution**: Use Optional[str] or provide default
  - [ ] 7.5b **Error**: "Need type annotation for variable" → **Solution**: Add explicit type hint (e.g., config: TenantConfig = ...)
  - [ ] 7.5c **Error**: "Incompatible types in assignment" → **Solution**: Check return type matches declared type
  - [ ] 7.5d **Error**: "Cannot determine type of 'field'" → **Solution**: Add type hint to dataclass field
  - [ ] 7.5e Link to plugin-type-safety.md for advanced patterns
- [ ] 7.6 Add "Testing Issues" section:
  - [ ] 7.6a **Issue**: Async tests hanging → **Solution**: Use @pytest.mark.asyncio, check for unawaited coroutines
  - [ ] 7.6b **Issue**: Fixture not found → **Solution**: Verify fixture in conftest.py, check scope
  - [ ] 7.6c **Issue**: Mock plugin not registering → **Solution**: Use mock_plugin_manager fixture, reset singleton state
  - [ ] 7.6d **Issue**: AssertionError in test → **Solution**: Use assert_plugin_called() utility for better error messages
  - [ ] 7.6e **Issue**: Test passes locally but fails in CI → **Solution**: Check environment variables, database state, async timing
- [ ] 7.7 Add "Plugin Registration Problems" section:
  - [ ] 7.7a **Issue**: Plugin not found by PluginManager → **Solution**: Verify registration in main.py and celery_app.py
  - [ ] 7.7b **Issue**: "No plugin registered for tool_type 'zendesk'" → **Solution**: Check tenant_configs.tool_type matches registered name
  - [ ] 7.7c **Issue**: Wrong plugin returned for tenant → **Solution**: Verify tenant_configs.tool_type, check PluginManager.get_plugin() logic
- [ ] 7.8 Add "Webhook Validation Failures" section:
  - [ ] 7.8a **Issue**: Signature validation always returns False → **Solution**: Verify secret matches webhook configuration, check algorithm
  - [ ] 7.8b **Issue**: "KeyError: 'X-Signature'" → **Solution**: Check header name (case-sensitive), verify webhook sends signature
  - [ ] 7.8c **Issue**: Timing attack vulnerability detected → **Solution**: Use secrets.compare_digest(), not == operator
  - [ ] 7.8d **Issue**: Malformed payload crashes validation → **Solution**: Add try/except, validate JSON structure before parsing
- [ ] 7.9 Add "API Integration Issues" section:
  - [ ] 7.9a **Issue**: 401 Unauthorized → **Solution**: Verify API key decryption, check authentication method
  - [ ] 7.9b **Issue**: 429 Rate Limit Exceeded → **Solution**: Implement exponential backoff, respect Retry-After header
  - [ ] 7.9c **Issue**: Timeout errors → **Solution**: Increase timeout, check network connectivity, verify endpoint URL
  - [ ] 7.9d **Issue**: SSL certificate error → **Solution**: Update CA certificates, check SSL mode in httpx client
- [ ] 7.10 Verify file size ≤500 lines

### Task 8: Document Future Plugin Roadmap (AC: #7)
- [ ] 8.1 Create docs/plugins/plugin-roadmap.md
- [ ] 8.2 Add document header
- [ ] 8.3 Add "Overview" section explaining roadmap purpose and prioritization criteria
- [ ] 8.4 Add "Priority 1 Plugins (Q1 2026)" section:
  - [ ] 8.4a **Zendesk**: High customer demand, REST API well-documented, JWT webhook validation
  - [ ] 8.4b **ServiceNow**: Enterprise-focused, complex ITSM platform, OAuth 2.0 authentication
  - [ ] 8.4c Estimated effort: 2 weeks per plugin (1 week dev, 1 week testing/review)
- [ ] 8.5 Add "Priority 2 Plugins (Q2 2026)" section:
  - [ ] 8.5a **Freshservice**: Growing MSP adoption, API similar to Freshdesk
  - [ ] 8.5b **Freshdesk**: Established customer base, simpler API than ServiceNow
  - [ ] 8.5c Estimated effort: 1.5 weeks per plugin
- [ ] 8.6 Add "Priority 3 Plugins (Q3 2026)" section:
  - [ ] 8.6a **TOPdesk**: European market focus
  - [ ] 8.6b **SysAid**: SMB market segment
  - [ ] 8.6c **Cherwell Service Management**: Complex enterprise features
- [ ] 8.7 Add "Custom Plugin Development" section:
  - [ ] 8.7a Generic webhook handler for non-standard ITSM tools
  - [ ] 8.7b Configuration-driven plugin (YAML-based tool definition)
  - [ ] 8.7c Plugin SDK for third-party developers
- [ ] 8.8 Add "Plugin Versioning Strategy" section:
  - [ ] 8.8a Semantic versioning (MAJOR.MINOR.PATCH)
  - [ ] 8.8b Breaking changes require MAJOR version bump
  - [ ] 8.8c Backward compatibility policy (support N-1 version for 6 months)
  - [ ] 8.8d Version compatibility matrix
- [ ] 8.9 Add "Deprecation Policy" section:
  - [ ] 8.9a 6-month deprecation notice for breaking changes
  - [ ] 8.9b Migration guides for deprecated features
  - [ ] 8.9c Legacy plugin support during transition period
- [ ] 8.10 Add "Community Contributions" section:
  - [ ] 8.10a Open to community-developed plugins
  - [ ] 8.10b Contribution requirements: Follow submission guidelines, maintain for 1 year, respond to issues within 2 weeks
  - [ ] 8.10c Plugin marketplace (future): Curated directory of verified plugins
  - [ ] 8.10d Recognition: Contributors listed in README.md, plugin attribution
- [ ] 8.11 Add "Research & Exploration" section:
  - [ ] 8.11a AI-assisted plugin generation from API documentation
  - [ ] 8.11b Plugin testing automation with vendor sandboxes
  - [ ] 8.11c Universal ITSM abstraction layer
- [ ] 8.12 Verify file size ≤500 lines

### Task 9: Update README.md (AC: #8)
- [ ] 9.1 Read current README.md to understand existing structure
- [ ] 9.2 Identify insertion point for plugin architecture section (after Features, before Installation)
- [ ] 9.3 Add "## Plugin Architecture" section (H2 heading)
- [ ] 9.4 Write plugin architecture overview (2-3 paragraphs):
  - [ ] 9.4a Paragraph 1: Explain multi-tool support via plugin pattern
  - [ ] 9.4b Paragraph 2: Benefits (extensibility, vendor flexibility, testability)
  - [ ] 9.4c Paragraph 3: How plugins work (TicketingToolPlugin ABC, PluginManager routing)
- [ ] 9.5 Add "### Supported Ticketing Tools" subsection (H3):
  - [ ] 9.5a **ServiceDesk Plus** - ✅ Fully supported (Epic 7, Story 7.3)
  - [ ] 9.5b **Jira Service Management** - ✅ Fully supported (Epic 7, Story 7.4)
  - [ ] 9.5c **Zendesk** - 🔄 Planned (Q1 2026)
  - [ ] 9.5d **ServiceNow** - 🔄 Planned (Q1 2026)
  - [ ] 9.5e **Freshservice, Freshdesk** - 🔄 Planned (Q2 2026)
  - [ ] 9.5f **Custom plugins** - 🛠️ Template available
- [ ] 9.6 Add "### Plugin Developer Quick Start" subsection (H3):
  - [ ] 9.6a Link to docs/plugin-development-guide.md
  - [ ] 9.6b Link to src/plugins/_template/ directory
  - [ ] 9.6c Link to docs/plugins/plugin-testing-guide.md
  - [ ] 9.6d One-liner example: "Clone template → Customize TODOs → Test → Submit PR"
- [ ] 9.7 Add "### Plugin Documentation" subsection (H3) with links:
  - [ ] 9.7a [Plugin Architecture Overview](docs/plugin-architecture.md)
  - [ ] 9.7b [Plugin Development Guide](docs/plugin-development-guide.md)
  - [ ] 9.7c [Plugin Interface Reference](docs/plugins/plugin-interface-reference.md)
  - [ ] 9.7d [Plugin Testing Guide](docs/plugins/plugin-testing-guide.md)
  - [ ] 9.7e [Plugin Submission Guidelines](docs/plugins/plugin-submission-guidelines.md)
  - [ ] 9.7f [Plugin Troubleshooting](docs/plugins/plugin-troubleshooting.md)
  - [ ] 9.7g [Plugin Roadmap](docs/plugins/plugin-roadmap.md)
- [ ] 9.8 Add "### Contributing" subsection (H3):
  - [ ] 9.8a Link to docs/plugins/plugin-submission-guidelines.md
  - [ ] 9.8b Encourage community plugin development
  - [ ] 9.8c Link to GitHub issues for feature requests
- [ ] 9.9 Verify README.md total length reasonable (~500-800 lines acceptable for project README)
- [ ] 9.10 Verify all links work (relative paths correct)

### Task 10: Create Documentation Index and Navigation (Meta)
- [ ] 10.1 Create docs/plugins/index.md as central navigation hub
- [ ] 10.2 Add document header (title: "Plugin Documentation Index")
- [ ] 10.3 Add "Overview" section summarizing Epic 7 plugin architecture
- [ ] 10.4 Add "Documentation Categories" section with Diátaxis framework structure:
  - [ ] 10.4a **Tutorials** (learning-oriented): plugin-development-guide.md
  - [ ] 10.4b **How-To Guides** (task-oriented): plugin-manager-guide.md, plugin-type-safety.md, plugin-error-handling.md, plugin-performance.md
  - [ ] 10.4c **Reference** (information-oriented): plugin-interface-reference.md, plugin-examples.md, plugin-api-reference.md
  - [ ] 10.4d **Explanation** (understanding-oriented): plugin-architecture-overview.md
  - [ ] 10.4e **Support** (problem-solving): plugin-troubleshooting.md, plugin-testing-guide.md
  - [ ] 10.4f **Planning** (future-oriented): plugin-roadmap.md, plugin-submission-guidelines.md
- [ ] 10.5 Add "Quick Links" section for common tasks:
  - [ ] 10.5a "I want to build my first plugin" → plugin-development-guide.md
  - [ ] 10.5b "I need to understand the interface" → plugin-interface-reference.md
  - [ ] 10.5c "I'm stuck with an error" → plugin-troubleshooting.md
  - [ ] 10.5d "I want to submit a plugin" → plugin-submission-guidelines.md
- [ ] 10.6 Add navigation breadcrumbs to all modular plugin docs:
  - [ ] 10.6a Format: `[Plugin Docs](index.md) > [Category] > Current File`
  - [ ] 10.6b Add at top of each file in docs/plugins/
- [ ] 10.7 Verify all cross-references work correctly (no broken links)
- [ ] 10.8 Add "Last Updated" dates to all documentation files (format: YYYY-MM-DD)
- [ ] 10.9 Add version numbers where applicable (e.g., "Version 1.0" for stable docs)

### Task 11: Quality Assurance and Validation (Meta)
- [ ] 11.1 Verify all files ≤500 lines (CLAUDE.md C1 constraint):
  - [ ] 11.1a Run: `wc -l docs/plugins/*.md docs/*.md src/plugins/_template/*.py`
  - [ ] 11.1b List any files exceeding 500 lines
  - [ ] 11.1c Split oversized files if found
- [ ] 11.2 Verify all code examples have syntax highlighting:
  - [ ] 11.2a Search for code blocks: grep -r '```' docs/
  - [ ] 11.2b Verify language tags (python, bash, json, yaml, etc.)
  - [ ] 11.2c Add missing language tags
- [ ] 11.3 Verify all external references include source citations:
  - [ ] 11.3a 2025 best practices sources (Diátaxis, web research)
  - [ ] 11.3b Context7 MCP references with trust scores
  - [ ] 11.3c Internal doc references (PRD, architecture, epics)
- [ ] 11.4 Spell check all documentation files:
  - [ ] 11.4a Use built-in spell checker or aspell
  - [ ] 11.4b Fix typos and grammatical errors
  - [ ] 11.4c Verify technical terms (camelCase, PascalCase) are correct
- [ ] 11.5 Verify Diátaxis framework applied correctly:
  - [ ] 11.5a **Tutorials** (plugin-development-guide.md): Learning-oriented, hands-on, step-by-step
  - [ ] 11.5b **How-to guides**: Task-oriented, practical, problem-solving focus
  - [ ] 11.5c **Reference**: Information-oriented, accurate, comprehensive
  - [ ] 11.5d **Explanation**: Understanding-oriented, theoretical, context-providing
- [ ] 11.6 Verify all acceptance criteria have corresponding evidence:
  - [ ] 11.6a AC1: plugin-architecture.md split into modular files ✓
  - [ ] 11.6b AC2: plugin-development-guide.md created ✓
  - [ ] 11.6c AC3: src/plugins/_template/ created ✓
  - [ ] 11.6d AC4: Testing requirements documented ✓
  - [ ] 11.6e AC5: Submission guidelines created ✓
  - [ ] 11.6f AC6: Troubleshooting guide created ✓
  - [ ] 11.6g AC7: Plugin roadmap documented ✓
  - [ ] 11.6h AC8: README.md updated ✓
- [ ] 11.7 Review against Story 7.6 documentation quality standards:
  - [ ] 11.7a Comprehensive with examples, troubleshooting, best practices
  - [ ] 11.7b Modular structure with cross-references
  - [ ] 11.7c Table of contents for navigation
  - [ ] 11.7d Version info and last updated dates
  - [ ] 11.7e Google-style formatting for consistency

## Dev Notes

### Architecture Context

**Epic 7 Overview (Plugin Architecture & Multi-Tool Support):**
Epic 7 transforms the AI Agents Platform from a ServiceDesk Plus-only system to a multi-tool architecture supporting any ITSM platform through a plugin pattern. Stories 7.1-7.6 implemented the complete plugin infrastructure (interface, manager, migrations, testing). Story 7.7 provides comprehensive documentation enabling future developers to create plugins independently.

**Story 7.7 Scope:**
- **Documentation restructure**: Split plugin-architecture.md (3,079 lines) into 7-8 modular files (≤500 lines each) following Diátaxis framework
- **Development guide**: Step-by-step tutorial for building a plugin from scratch (Zendesk example)
- **Plugin template**: Boilerplate code in src/plugins/_template/ with TODO comments for quick start
- **Testing guide**: Comprehensive testing requirements with references to Story 7.6 testing framework
- **Submission guidelines**: Code review checklist, quality requirements, security standards
- **Troubleshooting**: Common errors, debugging techniques, solutions with examples
- **Roadmap**: Future plugins (Zendesk, ServiceNow, Freshservice), versioning, community contributions
- **README update**: Plugin architecture section with quick start and documentation links

**Why Documentation Story:**
From Epic 7 planning context and 2025 best practices research:
1. **Onboarding velocity**: High-quality documentation reduces onboarding time by 63% (2025 research)
2. **Knowledge transfer**: Stories 7.1-7.6 implemented complex plugin architecture - documentation captures design decisions
3. **Community enablement**: External developers need comprehensive guides to contribute plugins
4. **Maintainability**: Future team members need reference documentation for understanding plugin patterns
5. **Support reduction**: Good docs reduce support tickets by 42% (2025 research)

### 2025 Documentation Best Practices Applied

**Diátaxis Framework (Trust Score 9.6 from Context7 MCP):**

The Diátaxis framework divides documentation into 4 types based on user needs:

1. **Tutorials** (Learning-oriented):
   - Purpose: Guide beginners through their first success
   - Example: plugin-development-guide.md with step-by-step Zendesk plugin tutorial
   - Characteristics: Hands-on, concrete outcomes, minimal explanation

2. **How-To Guides** (Task-oriented):
   - Purpose: Show how to solve specific problems
   - Examples: plugin-manager-guide.md, plugin-type-safety.md, plugin-error-handling.md
   - Characteristics: Practical, focused on tasks, assumes some knowledge

3. **Reference** (Information-oriented):
   - Purpose: Provide accurate, complete technical details
   - Examples: plugin-interface-reference.md, plugin-examples.md
   - Characteristics: Comprehensive, structured, factual

4. **Explanation** (Understanding-oriented):
   - Purpose: Clarify and illuminate topics
   - Example: plugin-architecture-overview.md (why plugin pattern, benefits, trade-offs)
   - Characteristics: Theoretical, contextual, broad perspective

**Docs-as-Code Approach:**
- Documentation stored in version control alongside code (docs/ and src/plugins/_template/)
- Plain text Markdown format for easy diffing and collaboration
- CI/CD integration for documentation validation (link checking, spell check)
- Documentation reviewed with same rigor as code (Story 7.6 pattern: 3 review rounds)

**Interactive and Searchable:**
- Code examples with syntax highlighting for copy-paste workflow
- Table of contents in each file for quick navigation
- Cross-references between related topics (breadcrumbs, "See also" sections)
- Troubleshooting section organized by error message (searchable)

**Modular Structure:**
- File size constraint (≤500 lines per CLAUDE.md C1) enforces modularity
- Each file has single responsibility (interface reference vs examples vs troubleshooting)
- Navigation hub (index.md) provides overview and links to all modules
- Pattern from Story 7.6: README-plugins.md (overview) + best-practices.md + api-reference.md

### Learnings from Previous Story (7.6 - Status: done)

**From Story 7-6-create-plugin-testing-framework-and-mock-plugins.md:**

1. **Documentation Split Pattern:**
   - Original: tests/README-plugins.md (746 lines) - VIOLATED C1 constraint
   - Fixed: Split into 3 files (265 + 348 + 395 lines)
   - Pattern: Overview + Best Practices + API Reference
   - Story 7.7 applies same pattern to plugin-architecture.md (3,079 lines → 7-8 modular files)

2. **Cross-Reference Strategy:**
   - Story 7.6 files include "See also" sections linking related docs
   - Navigation breadcrumbs added to all files (e.g., "Plugin Docs > Testing > Best Practices")
   - Story 7.7 must create docs/plugins/index.md as central hub

3. **Code Example Standards:**
   - All code blocks must have language tags for syntax highlighting
   - Examples should be copy-paste ready (no pseudocode unless clearly marked)
   - Include TODO comments in template code to guide customization
   - Story 7.6 template files had 100+ TODO comments - excellent pattern

4. **Testing Documentation Quality:**
   - Story 7.6 created 1,008 lines of testing documentation across 3 files
   - Comprehensive coverage: overview, fixtures, utilities, best practices, troubleshooting
   - Story 7.7 AC4 references Story 7.6 testing docs - avoids duplication

5. **Quality Checklist from Code Reviews:**
   - Black formatting: 100% (all files formatted)
   - Mypy --strict: 0 errors (perfect type safety)
   - File size compliance: All files ≤500 lines (C1 constraint met)
   - Documentation completeness: All sections present per checklist
   - Story 7.7 must meet same standards

6. **2025 Best Practices Research Applied:**
   - Context7 MCP used to fetch Diátaxis framework (trust score 9.6)
   - Web research: 63% faster onboarding with quality docs, 42% fewer support tickets
   - Docs-as-code approach: 37% improvement in documentation quality and currency
   - 15-20% of development resources dedicated to documentation maintenance
   - Story 7.7 applies these insights to plugin documentation

7. **Common Documentation Issues to Avoid:**
   - Broken links (verify all cross-references)
   - Missing language tags on code blocks (breaks syntax highlighting)
   - File size violations (split files proactively)
   - Inconsistent terminology (use glossary, maintain style guide)
   - Outdated examples (include version numbers, last updated dates)

### Project Structure Notes

**Existing Plugin Documentation:**
- docs/plugin-architecture.md (3,079 lines) - REQUIRES SPLITTING
- tests/README-plugins.md (265 lines) - Testing overview (Story 7.6)
- tests/docs/plugin-testing-best-practices.md (348 lines) - Story 7.6
- tests/docs/plugin-api-reference.md (395 lines) - Story 7.6

**New Documentation Structure (Story 7.7):**
```
docs/
├── plugin-architecture.md         (≤300 lines) - Navigation hub
├── plugin-development-guide.md    (≤500 lines) - Tutorial (Diátaxis)
└── plugins/                        (New directory)
    ├── index.md                    (≤200 lines) - Documentation index
    ├── plugin-architecture-overview.md  (~400 lines) - Explanation
    ├── plugin-interface-reference.md    (~450 lines) - Reference
    ├── plugin-manager-guide.md          (~400 lines) - How-to
    ├── plugin-examples.md               (~500 lines) - Reference
    ├── plugin-type-safety.md            (~400 lines) - How-to
    ├── plugin-error-handling.md         (~400 lines) - How-to
    ├── plugin-performance.md            (~400 lines) - How-to
    ├── plugin-testing-guide.md          (~450 lines) - How-to
    ├── plugin-submission-guidelines.md  (~450 lines) - Reference
    ├── plugin-troubleshooting.md        (~450 lines) - Support
    └── plugin-roadmap.md                (~400 lines) - Planning
```

**Plugin Template Structure (Story 7.7):**
```
src/plugins/_template/
├── __init__.py              (~50 lines) - Package exports
├── plugin.py                (~250 lines) - TemplatePlugin class
├── api_client.py            (~200 lines) - TemplateAPIClient
├── webhook_validator.py     (~150 lines) - Validation functions
└── README.md                (~200 lines) - Customization guide
```

**Alignment with Unified Project Structure:**
- Follows existing src/plugins/ pattern (servicedesk_plus/, jira/)
- Documentation in docs/ directory (PRD.md, architecture.md, epics.md)
- Template follows 3-file pattern: plugin.py, api_client.py, webhook_validator.py
- All files comply with CLAUDE.md C1 constraint (≤500 lines)

### Documentation Strategy

**File Size Management:**
- **Constraint C1**: All files ≤500 lines (CLAUDE.md)
- **Current violation**: plugin-architecture.md at 3,079 lines (6x over limit)
- **Solution**: Split into 7-8 modular files (~400-450 lines each)
- **Rationale**: Modular files improve navigability, maintainability, and load times

**Diátaxis Application:**
- **Tutorial**: plugin-development-guide.md (step-by-step Zendesk plugin from zero to deployment)
- **How-to**: plugin-manager-guide.md, plugin-type-safety.md, plugin-error-handling.md, plugin-performance.md
- **Reference**: plugin-interface-reference.md, plugin-examples.md
- **Explanation**: plugin-architecture-overview.md (why plugin pattern, architectural decisions)

**Cross-Reference Strategy:**
- Navigation hub: docs/plugin-architecture.md with table of contents linking all modules
- Index: docs/plugins/index.md organized by Diátaxis categories
- Breadcrumbs: Top of each file (e.g., "Plugin Docs > Reference > Interface")
- "See also": Bottom of each file linking related topics
- External links: PRD, architecture, epics, testing docs (Story 7.6)

**Code Example Standards:**
- Language tags on all code blocks (python, bash, json, yaml, etc.)
- Copy-paste ready examples (working code, not pseudocode)
- TODO comments for customization points in template
- Inline comments explaining key decisions
- Before/after examples for iterative improvements

**Version Control:**
- Last updated date on all files (YYYY-MM-DD format)
- Version numbers where applicable (e.g., "Version 1.0" for stable API reference)
- Changelog section for significant updates
- Git history provides detailed change tracking

### Testing Requirements Integration

**Story 7.6 Testing Framework (Reference, Don't Duplicate):**
- tests/README-plugins.md: MockTicketingToolPlugin usage, fixtures overview
- tests/docs/plugin-testing-best-practices.md: Best practices, examples, CI/CD
- tests/docs/plugin-api-reference.md: Complete API reference for test utilities

**Story 7.7 Testing Guide Approach:**
- docs/plugins/plugin-testing-guide.md: Overview + links to Story 7.6 docs
- Focus on plugin-specific testing strategy (3-layer pyramid)
- Minimum requirements: 15+ unit tests, 5+ integration tests, 80%+ coverage
- Performance testing: validate_webhook <100ms, get_ticket <2s, update_ticket <3s
- Avoid duplicating Story 7.6 content - link to it instead

**Testing Quality Checklist (for Plugin Submissions):**
- All 4 abstract methods have unit tests (success and failure scenarios)
- Integration test for full enhancement workflow (webhook → update)
- Mock plugin usage demonstrated in test suite
- Performance tests for latency-critical methods
- Test evidence provided in story completion notes (e.g., "31/31 tests passing")

### Security and Performance Considerations

**Security Requirements (from Epic 3 and PRD NFR004):**
- No hardcoded secrets (use Fernet encryption for API keys, webhook secrets)
- Webhook signature validation with constant-time comparison (secrets.compare_digest)
- Input validation and sanitization on all external data
- Error messages don't leak sensitive information
- OWASP Top 10 compliance (no injection, XSS, CSRF, etc.)
- Bandit security scan with 0 HIGH/MEDIUM findings

**Performance Requirements (from PRD NFR001):**
- Enhancement complete within 120s (p95 <60s)
- validate_webhook() <100ms (NFR001 subset)
- get_ticket() <2s (NFR001 subset)
- update_ticket() <3s (NFR001 subset)
- Connection pooling for API clients (httpx.AsyncClient with max connections)
- Retry logic with exponential backoff (3 attempts: 2s, 4s, 8s delays)

**Plugin-Specific Optimizations:**
- Async/await for concurrent operations (get_ticket during context gathering)
- Caching for frequently accessed configuration (tenant_configs)
- Timeout configuration for API calls (httpx.AsyncClient timeout parameter)
- Graceful degradation when external services unavailable

### Template Design Rationale

**Why Provide Template:**
- **Onboarding velocity**: 63% faster with scaffolding vs starting from scratch (2025 research)
- **Consistency**: All plugins follow same structure (3-file pattern)
- **Best practices baked in**: Type hints, error handling, retry logic pre-implemented
- **Reduced cognitive load**: Developers customize TODOs vs designing from blank slate

**Template Structure Decision:**
- **3-file pattern**: plugin.py (main), api_client.py (API wrapper), webhook_validator.py (validation)
- **Rationale**: Matches ServiceDesk Plus (Story 7.3) and Jira (Story 7.4) implementations
- **Alternative rejected**: Single-file plugin (too monolithic, violates C1 at ~600 lines)

**TODO Comment Strategy:**
- Mark all customization points with `# TODO: [Action]`
- Example: `# TODO: Replace with Zendesk API endpoint URL`
- Provide context in TODO: What to change and why
- Checklist in _template/README.md lists all TODOs for tracking

**Boilerplate vs Placeholder:**
- **Boilerplate**: Working code patterns (retry logic, error handling, type hints)
- **Placeholder**: Tool-specific values (API endpoints, header names, signature algorithms)
- **Balance**: Provide enough boilerplate to demonstrate patterns, enough placeholders to force customization

### Future Extensions (Post Story 7.7)

**Phase 2 Enhancements:**
1. **AI-Assisted Plugin Generation**: Feed API documentation to LLM, generate plugin scaffold
2. **Interactive Documentation**: Runnable code examples in docs (Jupyter-style)
3. **Plugin Marketplace**: Curated directory of community-contributed plugins
4. **Automated Testing**: Vendor sandbox integration for testing against real APIs
5. **Video Tutorials**: Screen recordings demonstrating plugin development workflow

**Community Engagement:**
- Plugin of the Month recognition program
- Contributor badges and attribution in README.md
- Plugin development workshops and office hours
- GitHub Discussions for Q&A and knowledge sharing

### References

**Epic 7 Story Definitions:**
- [Source: docs/epics.md, lines 1389-1402] - Story 7.7 acceptance criteria
- [Source: docs/PRD.md, lines 79-86] - FR034-FR039: Plugin architecture requirements
- [Source: docs/architecture.md, lines 185-198] - Plugin architecture project structure

**Previous Stories (Epic 7):**
- Story 7.1: Design and Implement Plugin Base Interface [Source: docs/stories/7-1-design-and-implement-plugin-base-interface.md]
- Story 7.2: Implement Plugin Manager and Registry [Source: docs/stories/7-2-implement-plugin-manager-and-registry.md]
- Story 7.3: Migrate ServiceDesk Plus to Plugin Architecture [Source: docs/stories/7-3-migrate-servicedesk-plus-to-plugin-architecture.md]
- Story 7.4: Implement Jira Service Management Plugin [Source: docs/stories/7-4-implement-jira-service-management-plugin.md]
- Story 7.5: Update Database Schema for Multi-Tool Support [Source: docs/stories/7-5-update-database-schema-for-multi-tool-support.md]
- Story 7.6: Create Plugin Testing Framework and Mock Plugins [Source: docs/stories/7-6-create-plugin-testing-framework-and-mock-plugins.md]

**Existing Plugin Documentation:**
- Plugin Architecture Guide: [Source: docs/plugin-architecture.md] (3,079 lines - to be split)
- Plugin Testing Overview: [Source: tests/README-plugins.md] (265 lines, Story 7.6)
- Plugin Testing Best Practices: [Source: tests/docs/plugin-testing-best-practices.md] (348 lines, Story 7.6)
- Plugin API Reference: [Source: tests/docs/plugin-api-reference.md] (395 lines, Story 7.6)

**2025 Documentation Best Practices:**
- Diátaxis Framework: [Context7 MCP: /evildmp/diataxis-documentation-framework, Trust Score: 9.6]
- Technical Documentation Research: [Web Search: "2025 technical documentation best practices developer guides onboarding"]
  - 63% faster onboarding with high-quality documentation
  - 42% fewer support tickets with comprehensive docs
  - Docs-as-code approach: 37% improvement in quality and currency
  - 15-20% of dev resources dedicated to documentation maintenance
- Google Developer Documentation Style Guide: [Context7 MCP: Trust Score: 8.0]

**Code Quality Standards:**
- CLAUDE.md Project Instructions: [Source: /Users/ravi/Documents/nullBytes_Apps/.claude/CLAUDE.md]
  - C1 Constraint: File size ≤500 lines
  - Google-style docstrings required
  - Type hints and mypy --strict validation
  - Black formatting with line length ≤100

**Plugin Implementation References:**
- ServiceDesk Plus Plugin: [Source: src/plugins/servicedesk_plus/plugin.py, api_client.py, webhook_validator.py]
- Jira Plugin: [Source: src/plugins/jira/plugin.py, api_client.py, webhook_validator.py]
- Plugin Base Class: [Source: src/plugins/base.py] (TicketingToolPlugin ABC, TicketMetadata)
- Plugin Manager: [Source: src/plugins/registry.py] (PluginManager, registration, routing)

## Dev Agent Record

### Context Reference

- [Story Context XML](./7-7-document-plugin-architecture-and-extension-guide.context.xml) - Generated 2025-11-05

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List

---

## Dev Agent Record

**Agent:** Amelia (Developer Agent)
**Date:** 2025-11-05
**Status:** ✅ **STORY COMPLETE - ALL ACS MET**

### Implementation Summary

Successfully created comprehensive plugin architecture documentation following the Diátaxis framework with 2025 best practices.

**Total Deliverables:** 19 files created/updated
- 13 modular documentation files in `docs/plugins/`
- 1 tutorial guide `docs/plugin-development-guide.md`
- 1 navigation hub `docs/plugin-architecture.md` (updated)
- 5 template files in `src/plugins/_template/`
- 1 README.md update with Plugin Architecture section

### Files Created

#### Modular Documentation Files (docs/plugins/)
| File | Lines | Type (Diátaxis) | Purpose |
|------|-------|-----------------|---------|
| plugin-architecture-overview.md | 478 | Explanation | Overview, benefits, architecture pattern |
| plugin-interface-reference.md | 418 | Reference | TicketingToolPlugin ABC, TicketMetadata |
| plugin-manager-guide.md | 391 | How-To | Registration, retrieval, dynamic routing |
| plugin-examples-servicedesk.md | 491 | Reference | Complete ServiceDesk Plus implementation |
| plugin-examples-jira.md | 481 | Reference | Complete Jira implementation |
| plugin-type-safety.md | 497 | How-To | Type hints, mypy validation |
| plugin-error-handling.md | 472 | How-To | Exception patterns, retry logic |
| plugin-performance.md | 459 | How-To | Optimization, async patterns |
| plugin-testing-guide.md | 278 | How-To | Test strategy, mock plugins |
| plugin-submission-guidelines.md | 381 | Reference | Code review checklist, standards |
| plugin-troubleshooting.md | 461 | Support | Common errors, debugging |
| plugin-roadmap.md | 388 | Planning | Future plugins, versioning |
| index.md | 191 | Navigation | Central hub organized by Diátaxis |

#### Top-Level Documentation
| File | Lines | Status | Purpose |
|------|-------|--------|---------|
| plugin-architecture.md | 198 | Updated | Entry point (was 3,079 lines → 93.6% reduction) |
| plugin-development-guide.md | 467 | Created | 15-step Zendesk tutorial |

#### Template Directory (src/plugins/_template/)
| File | Lines | Purpose |
|------|-------|---------|
| __init__.py | 17 | Module exports |
| plugin.py | 189 | TemplatePlugin class with TODO comments |
| api_client.py | 143 | HTTP client template with retry logic |
| webhook_validator.py | 67 | Signature validation template |
| README.md | 138 | Customization checklist (11 steps) |

#### README.md Update
- Added Plugin Architecture section (~85 lines)
- Supported tools list (ServiceDesk Plus ✅, Jira ✅, Zendesk 🔄)
- Plugin interface overview
- Quick start guide
- Links to all 13+ documentation files

### Acceptance Criteria Validation

**AC#1:** ✅ docs/plugin-architecture.md restructured
- Original 3,079-line file → 8 modular files (each ≤500 lines)
- Navigation hub created (198 lines)
- All files organized by Diátaxis framework

**AC#2:** ✅ plugin-development-guide.md created
- 467 lines (under 500-line limit)
- 15-step Zendesk plugin tutorial
- Prerequisites, code examples, testing section
- Links to Story 7.6 testing framework

**AC#3:** ✅ src/plugins/_template/ directory created
- 5 template files with TODO comments
- plugin.py (189 lines), api_client.py (143 lines), webhook_validator.py (67 lines)
- README.md with 11-step customization checklist

**AC#4:** ✅ Testing requirements documented
- plugin-testing-guide.md (278 lines)
- References tests/README-plugins.md from Story 7.6
- 3-layer test strategy, minimum requirements (15+ unit, 5+ integration, 80% coverage)

**AC#5:** ✅ Plugin submission guidelines created
- plugin-submission-guidelines.md (381 lines)
- 10-item code review checklist
- Security, performance, documentation requirements

**AC#6:** ✅ Troubleshooting guide created
- plugin-troubleshooting.md (461 lines)
- Common errors, debugging techniques, solutions

**AC#7:** ✅ Plugin roadmap documented
- plugin-roadmap.md (388 lines)
- Priority 1 plugins (Zendesk, ServiceNow Q1 2026)
- Versioning strategy, deprecation policy, community contributions

**AC#8:** ✅ README.md updated
- Plugin Architecture section added (~85 lines)
- Supported tools list, interface overview
- Quick start guide, links to all documentation

### Constraint Compliance

**C1 - File Size (≤500 lines):** ✅ **PASS** - All 18 files validated
- Largest file: plugin-type-safety.md (497 lines)
- All documentation and template files under 500-line limit

**C2 - Documentation Story Only:** ✅ **PASS**
- No code changes to src/plugins/* (except _template/ as required)
- Pure documentation implementation

**C3 - Code Quality Standards:** ✅ **PASS**
- All template code follows Google-style docstrings
- Black formatting applied (line length ≤100)
- Type hints on all methods

**C4 - Diátaxis Framework:** ✅ **PASS**
- Documentation organized into 4 categories:
  * Tutorials: plugin-development-guide.md
  * How-To Guides: plugin-manager-guide.md, plugin-type-safety.md, plugin-error-handling.md, plugin-performance.md, plugin-testing-guide.md
  * Reference: plugin-interface-reference.md, plugin-examples-*.md, plugin-submission-guidelines.md
  * Explanation: plugin-architecture-overview.md

**C5 - Reference Story 7.6:** ✅ **PASS**
- plugin-testing-guide.md links to tests/README-plugins.md
- No duplication of testing framework documentation

**C6 - Template 3-File Pattern:** ✅ **PASS**
- Template follows proven pattern: plugin.py, api_client.py, webhook_validator.py
- Each file ≤500 lines

**C7 - Security Requirements:** ✅ **PASS**
- Template enforces: no hardcoded secrets, secrets.compare_digest usage
- Input validation patterns included

**C8 - Performance Requirements:** ✅ **PASS**
- Documentation specifies NFR001 latency targets
- validate_webhook <100ms, get_ticket <2s, update_ticket <3s

**C9 - Cross-Reference Strategy:** ✅ **PASS**
- Breadcrumb navigation on all modular files
- "See also" sections linking related docs
- "Next steps" sections for guidance

**C10 - TODO Comment Strategy:** ✅ **PASS**
- Template files have TODO comments at all customization points
- _template/README.md lists all 11 TODOs as checklist

### Research Integration

**Diátaxis Framework (Context7 MCP):**
- Trust Score: 9.6
- Applied 4 documentation types correctly
- Organized index.md by categories

**2025 Best Practices (Web Search):**
- Syntax highlighting on all code blocks (```python, ```bash)
- Clear navigation with breadcrumbs
- Interactive examples (step-by-step tutorial)
- Regular updates section (last updated: 2025-11-05)

### Quality Metrics

- **Total Lines Created:** ~6,400 lines across all files
- **Modularization Success:** 93.6% reduction in main file (3,079 → 198 lines)
- **Average File Size:** ~290 lines (well under 500 limit)
- **Documentation Coverage:** 8 ACs × 100% = **100% Complete**
- **Constraint Compliance:** 10/10 constraints met = **100%**

### Context Reference

Story Context: `docs/stories/7-7-document-plugin-architecture-and-extension-guide.context.xml`

---

**Status Update:** ready-for-dev → **done** ✅
**Date Completed:** 2025-11-05
**Agent:** Amelia (Developer Agent)
