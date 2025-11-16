# Agent Testing Sandbox Guide (Story 8.14)

## Overview

The Agent Testing Sandbox provides a secure dry-run environment for testing agents before activation. It simulates agent execution without side effects, captures detailed execution traces, tracks token usage, and provides tools for debugging and comparison.

## Features

### 1. Sandbox Execution (AC #3)
- **Dry-run mode**: Tests agents without making real API calls or database writes
- **Mock tools**: Simulates tool responses for ticketing systems (ServiceDesk Plus, Jira)
- **Read-only database**: Prevents accidental data modifications during testing
- **No side effects**: Webhooks and external calls are intercepted

### 2. Execution Tracing (AC #4)
- **Step-by-step logging**: Records each tool call and LLM request
- **Timestamps**: Captures exact timing with nanosecond precision
- **Input/Output capture**: Stores parameters and responses for analysis
- **Execution flow**: Shows the complete agent decision path

### 3. Token Usage Tracking (AC #5)
- **Token counting**: Tracks input/output tokens from LLM calls
- **Cost calculation**: Estimates API costs based on model pricing
- **Per-step breakdown**: Shows token usage for each execution step
- **Cost trends**: Compare token usage across multiple test runs

### 4. Execution Timing (AC #6)
- **Total duration**: Complete test execution time
- **Per-step breakdown**: Latency for each tool call and LLM request
- **Performance analysis**: Identify bottlenecks in agent execution

### 5. Error Handling (AC #8)
- **Detailed error capture**: Full stack traces for debugging
- **Error type classification**: Distinguishes between tool, LLM, and system errors
- **Graceful degradation**: Returns partial results when failures occur

### 6. Result Comparison (AC #7)
- **Test history**: Store unlimited test execution results
- **Diff analysis**: Compare two test runs side-by-side
- **Regression detection**: Identify changes in token usage, timing, or behavior

## API Endpoints

### POST /api/agents/{agent_id}/test
Execute an agent test in sandbox mode.

**Request:**
```json
{
  "payload": {
    "ticket_id": "TICKET-123",
    "issue": "Network connectivity problem"
  },
  "simulate_webhook": true
}
```

**Response:**
```json
{
  "test_id": "550e8400-e29b-41d4-a716-446655440000",
  "agent_id": "...agent-id...",
  "status": "success",
  "execution_trace": {
    "steps": [
      {
        "step_number": 1,
        "step_type": "tool_call",
        "tool_name": "fetch_ticket",
        "input": {"ticket_id": "TICKET-123"},
        "output": {"ticket_id": "TICKET-123", "status": "Open"},
        "timestamp": "2025-11-07T12:34:56.123456Z",
        "duration_ms": 45.5
      },
      {
        "step_number": 2,
        "step_type": "llm_request",
        "model": "gpt-4o-mini",
        "input": {"prompt": "Analyze this ticket..."},
        "output": {"response": "The issue appears to be..."},
        "timestamp": "2025-11-07T12:34:56.180000Z",
        "duration_ms": 520.0
      }
    ],
    "total_duration_ms": 565.5,
    "status": "success"
  },
  "token_usage": {
    "input_tokens": 150,
    "output_tokens": 75,
    "total_tokens": 225,
    "estimated_cost_usd": 0.00034
  },
  "execution_time": {
    "total_duration_ms": 565.5,
    "steps": [
      {"name": "Load tools", "duration_ms": 45.5},
      {"name": "LLM analysis", "duration_ms": 520.0}
    ]
  },
  "errors": null,
  "created_at": "2025-11-07T12:34:56Z"
}
```

### GET /api/agents/{agent_id}/test-history
Retrieve paginated test execution history for an agent.

**Query Parameters:**
- `limit` (int, default=50): Maximum results (1-500)
- `offset` (int, default=0): Number of results to skip

**Response:**
```json
{
  "tests": [...test summaries...],
  "total": 125,
  "limit": 50,
  "offset": 0
}
```

### GET /api/agents/{agent_id}/test/{test_id}
Retrieve a single test execution result with full details.

**Response:** Complete test result (see POST /test response format)

### POST /api/agents/{agent_id}/test/compare
Compare two test executions to identify differences.

**Request:**
```json
{
  "test_id_1": "550e8400-e29b-41d4-a716-446655440000",
  "test_id_2": "660e8400-e29b-41d4-a716-446655440001"
}
```

**Response:**
```json
{
  "test_id_1": "550e8400-e29b-41d4-a716-446655440000",
  "test_id_2": "660e8400-e29b-41d4-a716-446655440001",
  "status_changed": false,
  "token_delta": 15,
  "cost_delta": 0.00005,
  "timing_delta": 120.5,
  "trace_differences": ["Step count changed: 4 → 5"]
}
```

## Usage Examples

### 1. Quick Test
```python
import httpx

client = httpx.AsyncClient()

# Execute test
response = await client.post(
    "http://localhost:8000/api/agents/{agent_id}/test",
    json={
        "payload": {"ticket_id": "TICKET-123"},
        "simulate_webhook": True
    }
)

result = response.json()
print(f"Test Status: {result['status']}")
print(f"Total Duration: {result['execution_time']['total_duration_ms']}ms")
print(f"Tokens Used: {result['token_usage']['total_tokens']}")
print(f"Estimated Cost: ${result['token_usage']['estimated_cost_usd']}")
```

### 2. Compare Two Tests
```python
# Get history
history_response = await client.get(
    f"http://localhost:8000/api/agents/{agent_id}/test-history?limit=2"
)
tests = history_response.json()["tests"]

# Compare recent tests
if len(tests) >= 2:
    comparison = await client.post(
        f"http://localhost:8000/api/agents/{agent_id}/test/compare",
        json={
            "test_id_1": tests[0]["test_id"],
            "test_id_2": tests[1]["test_id"]
        }
    )

    diff = comparison.json()
    print(f"Token Usage Changed by: {diff['token_delta']}")
    print(f"Cost Changed by: ${diff['cost_delta']}")
    print(f"Timing Changed by: {diff['timing_delta']}ms")
```

## Architecture

### Service Layer (`src/services/`)

**`agent_test_service.py`** - Main orchestration
- `execute_agent_test()` - Run test in sandbox mode
- `get_test_history()` - Retrieve paginated history
- `get_test_result()` - Get single test details
- `compare_tests()` - Compare two executions

**`execution_tracer.py`** - Step logging utility
- `ExecutionTracer` class captures steps with timing
- `add_tool_call()` - Record tool execution
- `add_llm_request()` - Record LLM call
- `to_dict()` - Export trace as JSON

**`sandbox_context.py`** - Dry-run execution environment
- `SandboxExecutionContext` - Manages test isolation
- `SandboxToolResponse` - Mock tool responses
- Prevents writes, API calls, webhooks

### API Layer (`src/api/agent_testing.py`)
- 4 REST endpoints with full tenant isolation
- Input validation via Pydantic schemas
- Error handling with appropriate HTTP status codes

### Data Models
- **AgentTestExecution** - Database model storing test results
- **ExecutionStep**, **ExecutionTrace** - Execution structure
- **TokenUsage**, **ExecutionTiming** - Metrics tracking
- **ErrorDetails** - Error information

## Constraints & Best Practices

1. **File Size**: All service files ≤500 lines (constraint C1)
2. **Testing**: 13+ unit tests covering all major paths (constraint C2)
3. **Async Patterns**: Full async/await throughout (constraint C3)
4. **Security**: No side effects in sandbox mode (constraint C4)
5. **2025 Best Practices**: LiteLLM patterns validated via Context7 (constraint C5)
6. **Reusability**: Builds on existing LiteLLM infrastructure (constraint C6)
7. **UI Consistency**: Ready for Streamlit integration (constraint C7)
8. **Database**: UUID primary keys, JSONB for flexible storage (constraint C8)
9. **Read-Only**: All test mode transactions are read-only (constraint C9)
10. **Error Handling**: Graceful degradation with full stack traces (constraint C10)

## Testing

### Unit Tests
```bash
pytest tests/unit/test_agent_test_service.py -v
# 13 tests: ExecutionTracer (5), SandboxExecutionContext (4), AgentTestService (4)
```

### Test Coverage
- Execution tracing and step recording
- Sandbox context and tool mocking
- Tenant isolation enforcement
- Error handling and validation
- Token usage calculation

## Future Enhancements

1. **Story 8.15**: Memory configuration UI integration
2. **Story 8.16**: LLM cost dashboard with test metrics
3. **Story 8.17**: Agent performance metrics dashboard
4. **Streamlit UI** (Task 4): Interactive test interface with visualization
5. **Advanced Comparison**: Diff visualization in UI
6. **Historical Analysis**: Trend analysis across test runs

## Troubleshooting

### Test Execution Fails
- Check agent exists and status is not INACTIVE
- Verify tenant_id matches authenticated user
- Review error details in response for specific issues

### Unexpected Token Usage
- Verify LLM model configuration in agent
- Check prompt template length
- Compare against baseline test

### Performance Issues
- Review per-step timing breakdown
- Identify slow tool calls (network latency)
- Consider agent complexity

## References

- **Migration**: `alembic/versions/005_add_agent_test_executions_table.py`
- **Models**: `src/database/models.py:AgentTestExecution`
- **Schemas**: `src/schemas/agent_test.py`
- **Services**: `src/services/{agent_test_service,sandbox_context,execution_tracer}.py`
- **API**: `src/api/agent_testing.py`
- **Tests**: `tests/unit/test_agent_test_service.py`
