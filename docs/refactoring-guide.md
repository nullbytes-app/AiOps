# Python File Refactoring Guide

**Purpose**: Guide for refactoring oversized Python files to comply with 2025 best practices
**Target Audience**: Developers maintaining AI Agents codebase
**Last Updated**: 2025-11-11 (Story 12.7)

---

## Table of Contents

1. [Why Refactor: The 150-500 Line Sweet Spot](#why-refactor)
2. [When to Refactor: File Size Thresholds](#when-to-refactor)
3. [How to Refactor: Step-by-Step Process](#how-to-refactor)
4. [Refactoring Patterns and Examples](#refactoring-patterns)
5. [Testing and Validation](#testing-and-validation)
6. [Common Pitfalls and Solutions](#common-pitfalls)

---

## Why Refactor: The 150-500 Line Sweet Spot {#why-refactor}

### Research Findings (2025 Python Best Practices)

Based on September 2025 industry research and AI code editor optimization studies:

**Optimal Range**: 150-500 lines per file
- **150-300 lines**: Ideal for AI code editors (Claude Code, Cursor, GitHub Copilot)
- **300-500 lines**: Acceptable for complex service layers and API endpoints
- **500+ lines**: Significantly degrades AI assistance quality

### Why File Size Matters

1. **AI Code Editor Performance**
   - AI models have limited context windows (typically 100k-200k tokens)
   - Large files consume context budget, leaving less room for analysis
   - Refactored code gets better suggestions and fewer hallucinations

2. **Human Readability**
   - Developers can understand a 200-line module in 5-10 minutes
   - A 1000-line file takes 30-60 minutes to comprehend
   - Code reviews are faster and more thorough with smaller files

3. **Maintenance Velocity**
   - Smaller files = faster edits (AI can see entire file at once)
   - Easier to identify single responsibility violations
   - Less merge conflict surface area

4. **Testing Coverage**
   - Focused modules are easier to test in isolation
   - Mocking becomes simpler with clear boundaries
   - Integration test complexity reduces

### References

- Medium Article (Sep 2025): "How File Size Impacts AI Code Editor Effectiveness"
- Context7 MCP Server Research: Python packaging best practices
- WebSearch: Stack Overflow trends on Python module organization

---

## When to Refactor: File Size Thresholds {#when-to-refactor}

### File Size Zones

| Zone | Lines | Action | Priority | Example Files |
|------|-------|--------|----------|---------------|
| 🟢 GREEN | 0-500 | ✅ Compliant | None | Most project files |
| 🟡 YELLOW | 500-700 | 🟨 Monitor | Low | Budget service (529 lines) |
| 🔴 RED | 700+ | 🔴 **Refactor ASAP** | **HIGH** | models.py (1922 lines), tasks.py (1717 lines) |

### Triggers for Refactoring

**Immediate Triggers** (RED zone):
1. File exceeds 700 lines
2. More than 5 classes or 20 functions in one file
3. Git blame shows 50+ different change authors
4. Merge conflicts occur regularly in same file
5. AI code editors time out or provide poor suggestions

**Proactive Triggers** (YELLOW zone):
1. File approaching 500 lines
2. New feature would add 100+ lines
3. Module has multiple unrelated responsibilities
4. Team plans major feature work in that area

### Current Status (2025-11-11)

**Files Refactored (Story 12.7)**:
- `agent_execution_service.py`: 564 → 379 lines (32% reduction) ✅
- `12_MCP_Servers.py`: 558 → 59 lines (89% reduction) ✅

**Files Needing Attention** (detected by `check-file-size.py`):
- 🔴 `models.py` (1922 lines, 284% over)
- 🔴 `tasks.py` (1717 lines, 243% over)
- 🔴 `agent_service.py` (955 lines, 91% over)
- 🔴 `mcp_servers.py` (941 lines, 88% over)
- 🟡 65 total files exceeding threshold

---

## How to Refactor: Step-by-Step Process {#how-to-refactor}

### Phase 1: Analysis (15-30 minutes)

**Step 1: Understand Current Structure**
```bash
# Count lines
wc -l path/to/oversized_file.py

# Identify functions/classes
grep -E "^(def |class )" path/to/oversized_file.py | wc -l

# Find imports
head -50 path/to/oversized_file.py | grep "^import\|^from"
```

**Step 2: Identify Natural Split Points**

Look for cohesive groups of functions/classes with:
- **Common purpose** (e.g., all HTTP client logic)
- **Shared dependencies** (imports used together)
- **Similar abstraction level** (low-level utils vs. high-level orchestration)
- **Clear naming patterns** (functions starting with `_validate_`, `_parse_`, etc.)

**Example** (agent_execution_service.py):
```
Original 564 lines split into:
1. MCP bridge pooling (165 lines) - connection lifecycle
2. Tool conversion (128 lines) - format transformation
3. Message building (80 lines) - prompt construction
4. Result extraction (134 lines) - response parsing
5. Main service (379 lines) - orchestration
```

**Step 3: Draw Module Boundaries**
```
Before:                          After:
┌─────────────────────┐         ┌──────────────────┐
│ BigService          │         │ Main Service     │
│   - function_a()    │         │   - orchestrate()│
│   - function_b()    │    →    ├──────────────────┤
│   - function_c()    │         │ Module A         │
│   - function_d()    │         │   - function_a() │
│   - function_e()    │         │   - function_b() │
└─────────────────────┘         ├──────────────────┤
                                │ Module B         │
                                │   - function_c() │
                                │   - function_d() │
                                │   - function_e() │
                                └──────────────────┘
```

### Phase 2: Extraction (1-2 hours)

**Step 4: Create Directory Structure**
```bash
# For service refactoring
mkdir -p src/services/service_name/

# For UI component refactoring
mkdir -p src/admin/utils/component_name/
```

**Step 5: Extract First Module** (start with smallest/simplest)
```python
# src/services/agent_execution/message_builder.py
"""
Message Construction for Agent Execution

Builds LangChain message lists with system prompt + user message.
Extracted from agent_execution_service.py (Story 12.7).
"""

from typing import Any, Dict, List, Optional
from langchain_core.messages import HumanMessage, SystemMessage


def build_messages(
    system_prompt: str,
    user_message: str,
    context: Optional[Dict[str, Any]] = None,
) -> List[Any]:
    """
    Build LangChain messages list with system prompt + user message.

    Args:
        system_prompt: Agent's system prompt (may contain {variables})
        user_message: User's input message
        context: Optional context dict for variable substitution

    Returns:
        List of LangChain Message objects [SystemMessage, HumanMessage]
    """
    # Implementation...
```

**Step 6: Update Original File**
```python
# src/services/agent_execution_service.py
from src.services.agent_execution.message_builder import build_messages

# Replace old implementation with call to extracted function
messages = build_messages(
    system_prompt=agent.system_prompt,
    user_message=user_message,
    context=context,
)
```

**Step 7: Create Public API**
```python
# src/services/agent_execution/__init__.py
"""
Agent Execution Submodule

Modular components for agent execution workflow.
"""

from .message_builder import build_messages
from .result_extractor import extract_response, extract_tool_calls
from .tool_converter import convert_tools_to_langchain
from .mcp_bridge_pooler import get_or_create_mcp_bridge, cleanup_mcp_bridge

__all__ = [
    "build_messages",
    "extract_response",
    "extract_tool_calls",
    "convert_tools_to_langchain",
    "get_or_create_mcp_bridge",
    "cleanup_mcp_bridge",
]
```

### Phase 3: Validation (30-60 minutes)

**Step 8: Run Tests**
```bash
# Unit tests for module
pytest tests/unit/test_agent_execution_service.py -v

# Full test suite
pytest tests/ --cov=src --cov-report=term

# Expect: All tests passing, 0 regressions
```

**Step 9: Code Quality Checks**
```bash
# Format code
black src/services/agent_execution/

# Lint
ruff check src/services/agent_execution/

# Type check
mypy src/services/agent_execution/ --strict

# Security scan
bandit -r src/services/agent_execution/ -ll
```

**Step 10: Verify File Sizes**
```bash
# Check all files comply
python scripts/check-file-size.py

# Expected: Main file ≤500 lines, new modules ≤300 lines each
```

---

## Refactoring Patterns and Examples {#refactoring-patterns}

### Pattern 1: Extract Utility Functions

**When**: Many small helper functions with shared purpose

**Example**: Message builders, validators, formatters

```python
# Before (300 lines in one file)
class AgentService:
    def _validate_prompt(self, prompt): ...
    def _validate_config(self, config): ...
    def _validate_tools(self, tools): ...
    # ... 20 more methods

# After
# validators.py (150 lines)
def validate_prompt(prompt: str) -> tuple[bool, str]: ...
def validate_config(config: dict) -> tuple[bool, str]: ...
def validate_tools(tools: list) -> tuple[bool, str]: ...

# agent_service.py (150 lines)
from .validators import validate_prompt, validate_config, validate_tools

class AgentService:
    def create_agent(self, ...):
        valid, error = validate_prompt(prompt)
        if not valid:
            raise ValueError(error)
```

**Benefits**:
- Validators can be tested independently
- Reusable across multiple services
- Clear separation of concerns

### Pattern 2: Extract Stateless Operations

**When**: Pure functions that don't depend on class state

**Example**: Data transformations, format conversions

```python
# Before (500 lines)
class AgentExecutionService:
    def _convert_mcp_tool_to_langchain(self, tool): ...
    def _convert_openapi_tool_to_langchain(self, tool): ...
    def _build_tool_schema(self, tool): ...

# After
# tool_converter.py (200 lines)
def convert_mcp_tool_to_langchain(tool: MCPTool) -> LangChainTool: ...
def convert_openapi_tool_to_langchain(tool: OpenAPITool) -> LangChainTool: ...
def build_tool_schema(tool: UnifiedTool) -> dict: ...

# agent_execution_service.py (300 lines)
from .tool_converter import convert_tools_to_langchain

class AgentExecutionService:
    async def execute_agent(self, ...):
        langchain_tools = await convert_tools_to_langchain(unified_tools, ...)
```

**Benefits**:
- Easier to test (no mocking required)
- Can be used in other contexts
- Functional programming style

### Pattern 3: Extract UI Renderers

**When**: Streamlit page with multiple view functions

**Example**: Form rendering, table display, detail views

```python
# Before (558 lines in one file)
def render_server_list(): ...  # 150 lines
def render_server_form(): ...  # 200 lines
def render_server_details(): ... # 150 lines

# After
# mcp_admin_ui/list_display.py (216 lines)
def render_server_list(): ...

# mcp_admin_ui/form_renderers.py (303 lines)
def render_server_form(edit_mode: bool = False): ...

# mcp_admin_ui/detail_view.py (248 lines)
def render_server_details(): ...

# 12_MCP_Servers.py (59 lines)
from src.admin.utils.mcp_admin_ui import (
    render_server_list,
    render_server_form,
    render_server_details,
)

# Main routing
if st.session_state.mcp_view == "list":
    render_server_list()
elif st.session_state.mcp_view == "add":
    render_server_form(edit_mode=False)
```

**Benefits**:
- Each view can be tested independently
- Session state management isolated
- Page file becomes pure routing logic

### Pattern 4: Extract Data Models

**When**: Large models.py with many unrelated models

```python
# Before (1922 lines)
# models.py
class Tenant(Base): ...
class Agent(Base): ...
class MCPServer(Base): ...
class Tool(Base): ...
class Execution(Base): ...
# ... 30 more models

# After
# models/__init__.py
from .tenant import Tenant
from .agent import Agent, AgentConfig
from .mcp import MCPServer, MCPTool
from .tool import Tool, ToolConfig
from .execution import Execution, ExecutionResult

# models/tenant.py (150 lines)
class Tenant(Base): ...

# models/agent.py (250 lines)
class Agent(Base): ...
class AgentConfig(BaseModel): ...

# models/mcp.py (200 lines)
class MCPServer(Base): ...
class MCPTool(BaseModel): ...
```

**Benefits**:
- Related models grouped together
- Easier to find specific model
- Reduced import time for specific models

---

## Testing and Validation {#testing-and-validation}

### Unit Test Strategy

**Rule**: Existing tests should pass without modification (except mocks)

```python
# tests/unit/test_agent_execution_service.py

# ✅ Good: Tests unchanged, only imports updated
from src.services.agent_execution_service import AgentExecutionService

def test_execute_agent_success():
    service = AgentExecutionService(mock_db)
    result = await service.execute_agent(...)
    assert result["success"] is True  # Same assertion as before

# ❌ Bad: Tests rewritten for refactored structure
# This indicates behavior changed - refactoring should be behavior-preserving!
```

### Integration Test Validation

**Critical Flows to Test**:
1. **Agent Execution** (Story 11.1.7)
   - Full ReAct workflow with MCP tools
   - Budget enforcement triggers correctly
   - Tool call history captured

2. **MCP Admin UI** (Story 11.1.9)
   - Add server → server created
   - Edit server → changes persisted
   - Delete server → confirmation works
   - Session state preserved across views

**Test Commands**:
```bash
# Agent execution integration
pytest tests/integration/test_agent_execution.py -v

# MCP UI workflow
pytest tests/integration/test_mcp_ui_workflow.py -v

# Full suite (target: ≥89.6% pass rate)
pytest tests/ --cov=src --cov-report=term
```

### Manual Smoke Testing

**Agent Execution Service**:
1. Navigate to Agent Management UI
2. Create test agent with GPT-4o-mini
3. Assign MCP server with tools
4. Execute agent with test message
5. **Expected**: Response within 3-5 seconds, tool calls logged

**MCP Servers Admin Page**:
1. Navigate to MCP Servers page (localhost:8501)
2. Click "Add MCP Server"
3. Fill stdio form (command: npx, args: @modelcontextprotocol/server-everything)
4. Save server
5. **Expected**: Capabilities discovered, server shows "active" status

### Performance Benchmarks

**Acceptance Criteria** (Story 12.7 AC6):
- Agent execution latency: ±5% tolerance
- MCP Servers page load: ±10% tolerance
- Overall test suite: ≥89.6% pass rate

**Measurement**:
```python
# tests/performance/test_refactoring_impact.py
import time

def test_agent_execution_latency():
    start = time.time()
    result = await agent_service.execute_agent(...)
    latency = time.time() - start

    # Baseline: 3.2 seconds (before refactoring)
    # Target: 2.9-3.5 seconds (±5%)
    assert 2.9 <= latency <= 3.5, f"Latency {latency}s outside tolerance"
```

---

## Common Pitfalls and Solutions {#common-pitfalls}

### Pitfall 1: Circular Imports

**Problem**: Module A imports from module B, which imports from module A

```python
# ❌ CIRCULAR DEPENDENCY
# module_a.py
from .module_b import helper_b
def function_a(): helper_b()

# module_b.py
from .module_a import function_a
def helper_b(): function_a()
```

**Solution**: Extract shared logic to third module
```python
# ✅ RESOLVED WITH SHARED MODULE
# shared.py
def shared_logic(): ...

# module_a.py
from .shared import shared_logic
def function_a(): shared_logic()

# module_b.py
from .shared import shared_logic
def helper_b(): shared_logic()
```

### Pitfall 2: Breaking Existing Imports

**Problem**: Other modules import functions that were moved

```python
# ❌ BREAKING CHANGE
# Before refactoring
from src.services.agent_service import validate_prompt

# After refactoring (without compatibility)
# ModuleNotFoundError: No module named 'validate_prompt'
```

**Solution**: Re-export from original location
```python
# ✅ BACKWARD COMPATIBLE
# src/services/agent_service.py
from .validators import validate_prompt  # Import from new location

# Existing imports still work
from src.services.agent_service import validate_prompt
```

### Pitfall 3: Splitting Mid-Function

**Problem**: Trying to split a 500-line function into pieces

```python
# ❌ WRONG APPROACH
def giant_function():
    # Step 1 (100 lines)
    # Step 2 (100 lines)
    # Step 3 (100 lines)
    # Step 4 (100 lines)
    # Step 5 (100 lines)
```

**Solution**: Refactor function first, then extract modules
```python
# ✅ REFACTOR FUNCTION FIRST
def giant_function():
    step_1_result = _process_step_1()
    step_2_result = _process_step_2(step_1_result)
    step_3_result = _process_step_3(step_2_result)
    return _finalize(step_3_result)

# THEN extract helper functions to separate module
# processors.py
def process_step_1(): ...
def process_step_2(input_data): ...
```

### Pitfall 4: Over-Refactoring

**Problem**: Creating too many tiny modules (10 lines each)

**Rule of Thumb**: Aim for 150-300 lines per extracted module

```python
# ❌ TOO GRANULAR (overhead > benefit)
validators/
├── email_validator.py (15 lines)
├── phone_validator.py (18 lines)
├── url_validator.py (12 lines)
└── ip_validator.py (20 lines)

# ✅ APPROPRIATELY GROUPED (200 lines)
validators.py
- validate_email()
- validate_phone()
- validate_url()
- validate_ip()
```

### Pitfall 5: Forgetting Type Hints

**Problem**: Extracted functions lose type information

```python
# ❌ NO TYPE HINTS
def build_messages(system_prompt, user_message, context=None):
    return [SystemMessage(...), HumanMessage(...)]

# ✅ FULLY TYPED
def build_messages(
    system_prompt: str,
    user_message: str,
    context: Optional[Dict[str, Any]] = None,
) -> List[Any]:
    return [SystemMessage(...), HumanMessage(...)]
```

---

## File Size Enforcement Automation

### CI/CD Integration

**Step Added to `.github/workflows/ci.yml`** (Story 12.7 AC3):
```yaml
- name: Check file sizes (Story 12.7)
  run: |
    pip install pyyaml
    python scripts/check-file-size.py
  continue-on-error: false
```

**Configuration**: `scripts/file-size-config.yaml`
```yaml
max_lines: 500
exclude_patterns:
  - "alembic/versions/"  # Database migrations
  - "tests/fixtures/"    # Test data
  - "__pycache__"        # Python cache
exclude_dirs:
  - "data"
  - ".bmad-ephemeral"
```

### Running Checks Locally

```bash
# Basic check (fails on violations)
python scripts/check-file-size.py

# Verbose output (shows all files checked)
python scripts/check-file-size.py --verbose

# Custom threshold
python scripts/check-file-size.py --max-lines 600

# Help
python scripts/check-file-size.py --help
```

**Exit Codes**:
- `0`: All files comply
- `1`: One or more violations found
- `2`: Configuration error

---

## Success Metrics

### Story 12.7 Achievements

**File Size Reductions**:
- agent_execution_service.py: 564 → 379 lines (32% reduction)
- 12_MCP_Servers.py: 558 → 59 lines (89% reduction)

**New Modules Created**:
- 7 focused modules (40-303 lines each)
- All under 350-line threshold
- 100% test pass rate maintained

**CI/CD Enforcement**:
- Automated file size checks integrated
- 65 existing violations documented
- Clear refactoring guidance provided

### Future Goals

**Short Term** (Next Quarter):
- Refactor RED zone files (>700 lines): models.py, tasks.py
- Reduce YELLOW zone count by 50%
- Maintain 100% GREEN zone compliance

**Long Term** (2025 H2):
- All files under 500 lines
- Average file size: 150-250 lines
- 90%+ AI code editor satisfaction scores

---

## Additional Resources

- **CI/CD Guide**: See `docs/ci-cd-pipeline-guide.md` for automated enforcement details
- **Architecture Guide**: See `docs/architecture.md` for module organization patterns
- **Test Guide**: See `tests/README.md` for testing strategies
- **Story 12.7**: See `.bmad-ephemeral/stories/12-7-file-size-refactoring-and-code-quality.md`

---

**Document Version**: 1.0
**Last Reviewed**: 2025-11-11
**Next Review**: 2025-12-11
