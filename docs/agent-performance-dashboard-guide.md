# Agent Performance Metrics Dashboard Guide

## Overview

The Agent Performance Metrics Dashboard (Story 8.17) provides real-time monitoring and analysis of AI agent execution performance across all agents in your tenant. Track execution metrics, identify performance bottlenecks, and receive optimization recommendations.

**Location**: Streamlit Admin UI → Agent Performance page (08_Agent_Performance.py)

## Key Features

### 1. Performance Metrics Summary
- **Success Rate**: Percentage of successful executions (0-100%)
- **Average Duration**: Mean execution time in seconds
- **P50 Latency**: Median execution latency
- **P95 Latency**: 95th percentile latency (identifies slow outliers)
- **P99 Latency**: 99th percentile latency (identifies worst-case latency)
- **Total Executions**: Cumulative execution count
- **Successful/Failed Counts**: Breakdown by status

### 2. Performance Trends Chart
Line chart showing performance trends over time (default: 7 days, configurable 1-90 days):
- Execution count per day
- Success rate percentage per day
- Average duration per day
- Helps identify performance degradation patterns

### 3. Error Distribution Analysis
Pie chart breaking down errors by category:
- **Timeout**: Request timeout or task timeout errors
- **Rate Limit**: API rate limit or quota exceeded errors
- **Validation Error**: Input validation or data format errors
- **Tool Failure**: Tool execution or integration errors
- **Other**: Uncategorized errors

### 4. Execution History Table
Detailed log of recent executions with:
- Timestamp (when execution occurred)
- Status (success/failed)
- Duration (in seconds)
- Token usage (input + output tokens)
- Cost (estimated USD)
- Error message (if failed)

Supports filtering by:
- Date range
- Status (success/failed)
- Pagination (50 records per page)

### 5. Slowest Agents Overview
Tenant-wide ranking of agents by P95 latency with:
- Agent name
- Execution count
- P95 latency in seconds
- Average duration
- Success rate
- **Optimization Recommendation**:
  - P95 ≥ 15s: "Review slow tool calls, consider async execution or parallel processing"
  - Avg Duration > 10s: "Optimize prompt length, reduce context size, consider caching"
  - Success Rate < 90%: "Investigate frequent failures, add error handling, review timeout settings"
  - Otherwise: "Performance OK"

## Using the Dashboard

### Step 1: Select an Agent
1. From the "Select Agent" dropdown, choose the agent to analyze
2. Available agents are populated from your tenant's agent list

### Step 2: Configure Date Range
1. Use the "Date Range" date picker to select analysis period
2. Default: Last 7 days
3. Max supported: From any date to today

### Step 3: Choose Trend Period
1. Select "Trend Period" (7, 14, or 30 days)
2. Determines the time window for trend chart aggregation
3. Longer periods show broader trends, shorter periods show recent patterns

### Step 4: View Metrics
The dashboard displays:
1. **Metrics Cards**: 8 key metrics summarizing agent performance
2. **Performance Trends**: Line chart of daily metrics
3. **Error Distribution**: Pie chart of error types
4. **Execution History**: Table of recent executions
5. **Slowest Agents**: Tenant-wide performance ranking

### Step 5: Interpret Results

#### Success Rate < 90%
**Action**: Investigate error patterns
- Check "Error Distribution" chart for error categories
- Review execution history for common error messages
- Consider implementing error handling or retry logic

#### P95 Latency > 15 seconds
**Action**: Optimize tool calls
- Review tool integration configuration
- Consider implementing parallel execution
- Check for slow external API calls
- Implement caching for repeated operations

#### Average Duration > 10 seconds
**Action**: Optimize prompt and context
- Reduce prompt length
- Decrease context window size
- Implement prompt caching
- Evaluate model choice

#### High Error Spike
**Action**: Debug specific errors
- Filter execution history by date range with high errors
- Look for patterns (specific error types, time of day, etc.)
- Check integration logs for tool failures
- Monitor rate limiting from external services

## API Integration

The dashboard uses REST API endpoints for data retrieval:

### Metrics Endpoint
```
GET /api/agents/{agent_id}/metrics
Query Parameters:
  - start_date: YYYY-MM-DD (optional, defaults to 7 days ago)
  - end_date: YYYY-MM-DD (optional, defaults to today)

Response:
{
  "metrics": {
    "agent_id": "uuid",
    "agent_name": "string",
    "total_executions": int,
    "successful_executions": int,
    "failed_executions": int,
    "success_rate": 0.0-100.0,
    "average_duration_seconds": float,
    "p50_latency_seconds": float,
    "p95_latency_seconds": float,
    "p99_latency_seconds": float,
    "start_date": "YYYY-MM-DD",
    "end_date": "YYYY-MM-DD"
  },
  "query_executed_at": "ISO8601 timestamp"
}
```

### Execution History Endpoint
```
GET /api/agents/{agent_id}/history
Query Parameters:
  - status: "success" or "failed" (optional)
  - start_date: YYYY-MM-DD (optional)
  - end_date: YYYY-MM-DD (optional)
  - limit: 1-500 (default 50)
  - offset: >= 0 (default 0)

Response:
{
  "records": [
    {
      "execution_id": "uuid",
      "timestamp": "ISO8601",
      "status": "success|failed",
      "duration_ms": int,
      "duration_seconds": float,
      "input_tokens": int,
      "output_tokens": int,
      "total_tokens": int,
      "estimated_cost_usd": float,
      "error_message": "string or null",
      "error_type": "string or null",
      "error_category": "timeout|rate_limit|validation_error|tool_failure|other|null"
    }
  ],
  "pagination": {
    "total_count": int,
    "limit": int,
    "offset": int,
    "has_more": bool
  }
}
```

### Performance Trends Endpoint
```
GET /api/agents/{agent_id}/trends
Query Parameters:
  - days: 1-90 (default 7)

Response:
{
  "trends": [
    {
      "trend_date": "YYYY-MM-DD",
      "execution_count": int,
      "successful": int,
      "failed": int,
      "success_rate": 0.0-100.0,
      "average_duration_seconds": float
    }
  ],
  "days_requested": int
}
```

### Error Analysis Endpoint
```
GET /api/agents/{agent_id}/error-analysis
Query Parameters:
  - start_date: YYYY-MM-DD (optional, defaults to 7 days ago)
  - end_date: YYYY-MM-DD (optional, defaults to today)

Response:
{
  "error_breakdown": [
    {
      "error_type": "timeout|rate_limit|validation_error|tool_failure|other",
      "count": int
    }
  ],
  "total_errors": int
}
```

### Slowest Agents Endpoint
```
GET /api/agents/slowest
Query Parameters:
  - limit: 1-100 (default 10)

Response:
{
  "slowest_agents": [
    {
      "agent_id": "uuid",
      "agent_name": "string",
      "execution_count": int,
      "p95_latency_seconds": float,
      "average_duration_seconds": float,
      "success_rate": 0.0-100.0,
      "optimization_recommendation": "string"
    }
  ],
  "count": int
}
```

## Architecture

### Service Layer (src/services/)

**AgentPerformanceService** (facade)
- Orchestrates query building and result aggregation
- Async methods for all data retrieval
- Error handling and logging

**AgentPerformanceQueryBuilder** (queries)
- SQL query execution for metrics retrieval
- Percentile calculations using PostgreSQL `func.percentile_cont()`
- Tenant isolation via joins with agents table

**AgentPerformanceAggregator** (aggregations)
- Pure functions for metrics calculation
- Error categorization logic
- Data normalization and DTO conversion
- Optimization recommendation generation

### Schemas (src/schemas/agent_performance.py)

**Pydantic v2 DTOs**:
- `AgentMetricsDTO`: Summary metrics for one agent
- `ExecutionRecordDTO`: Single execution log entry
- `TrendDataDTO`: Daily aggregated metrics
- `ErrorAnalysisDTO`: Error type breakdown
- `SlowAgentMetricsDTO`: Agent ranking by latency
- `ExecutionFiltersDTO`: Query parameter filters

### API Endpoints (src/api/agent_performance.py)

FastAPI routes with:
- Tenant isolation checks via `get_tenant_id()` dependency
- Proper HTTP status codes (200, 400, 403, 500)
- Comprehensive error handling
- Caching headers for performance

### Dashboard UI (src/admin/pages/08_Agent_Performance.py)

Streamlit page with:
- `@st.cache_data(ttl=60)` for efficient API caching
- `@st.fragment(run_every=60)` for auto-refresh without full reload
- Agent selection and date range filtering
- Interactive Plotly charts
- Responsive multi-column layouts

## Performance Optimization

### Database Query Optimization
- Percentile calculations use PostgreSQL native `PERCENTILE_CONT()` for efficiency
- Queries are indexed on (agent_id, timestamp) for fast filtering
- Date range filtering reduces query scope significantly

### Caching Strategy
- Dashboard caches data for 60 seconds (configurable)
- Manual refresh button clears cache on demand
- Auto-refresh every 60 seconds for near real-time updates

### Pagination
- Execution history limited to 50 records per page
- Reduces payload size and improves UI responsiveness
- Total count returned for pagination controls

## Troubleshooting

### No Data Appears
**Possible causes:**
- Agent has no recent executions
- Selected date range has no data
- Agent is from different tenant

**Solution**: Select different date range or different agent

### Charts Show "No data available"
**Cause**: No trend or error data for selected period

**Solution**: Extend date range to include more history

### Error Analysis Pie Chart is Empty
**Cause**: No failed executions in date range

**Solution**: Select date range with execution failures or check "Success rate < 100%"

### "Please select an agent" message
**Cause**: No agent selected from dropdown

**Solution**: Click "Select Agent" dropdown and choose an agent

### "Agent not found or access denied" (403)
**Cause**: Agent doesn't belong to authenticated tenant

**Solution**:
- Verify agent exists in your tenant
- Check authentication credentials
- Contact admin if tenant access issue

## Best Practices

### Monitoring Performance
1. **Daily Review**: Check slowest agents list daily
2. **Weekly Analysis**: Review trends over 7-day periods
3. **Threshold Alerts**: Set internal alerts for P95 > 10s or Success Rate < 95%
4. **Error Patterns**: Look for recurring error categories

### Optimization Priorities
1. **Quick Wins**: Fix validation errors (often simple data format issues)
2. **High Impact**: Reduce P95 latency > 15s (direct user impact)
3. **Cost Optimization**: Reduce token usage for high-volume agents
4. **Reliability**: Improve success rate < 90%

### Capacity Planning
- Monitor total execution count trends
- Track average duration for cost estimation
- Plan for peak usage periods
- Consider token quota for high-volume agents

## Related Stories

- **Story 8.16**: LLM Cost Dashboard (cost tracking)
- **Story 8.14**: Agent Testing Sandbox (testing framework)
- **Story 8.15**: Memory Configuration UI (agent memory management)
- **Story 8.13**: BYOK Configuration (API key management)

## Support

For issues or feature requests:
1. Check this guide's troubleshooting section
2. Review API endpoint documentation
3. Check server logs at `/var/log/ai-agents/app.log`
4. Contact the development team with:
   - Agent ID (UUID)
   - Date/time of issue
   - Screenshot of dashboard state
   - Error messages from browser console
