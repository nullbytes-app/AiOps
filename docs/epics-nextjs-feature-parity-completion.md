# AI Agents Platform - Next.js UI Feature Parity & Completion

**Author:** Ravi (with Bob - Scrum Master, Team Analysis)
**Date:** 2025-01-20
**Project Type:** Brownfield - Feature Completion
**Context:** Post-migration gap analysis and feature parity completion

---

## Overview

This epic breakdown addresses the **feature gaps identified during Next.js UI migration**. The initial migration created the foundation, but left significant functionality incomplete or missing entirely. This document provides the roadmap to achieve **complete feature parity** with the Streamlit UI and deliver a production-ready Next.js dashboard.

**Situation:**
- Next.js UI exists but is incomplete
- 3 critical pages completely missing (Workers, LLM Costs, Agent Performance)
- Several pages partially implemented (Prompts, Tools, Tenants)
- No User/Role management UI (RBAC backend exists, no frontend)
- UI/UX inconsistencies across pages
- Missing backend APIs for worker monitoring

**Goal:** Deliver a fully functional Next.js UI that matches or exceeds Streamlit capabilities.

---

## Epic Structure

| Epic | Goal | Priority | API Status |
|------|------|----------|------------|
| **Epic 1** | Analytics & Monitoring Dashboards | P0 (Must Have) | ✅ APIs Ready |
| **Epic 2** | Worker Monitoring System | P0 (Must Have) | ❌ Backend Required |
| **Epic 3** | User & Role Management | P0 (Must Have) | ⚠️ Partial APIs |
| **Epic 4** | Feature Completion & Enhancement | P1 (Should Have) | ✅ APIs Ready |
| **Epic 5** | UI/UX Consistency & Cleanup | P2 (Nice to Have) | ✅ No Backend |

---

## Functional Requirements (Gap Analysis)

**Missing Critical Pages:**
- FR1: Workers monitoring page with health metrics
- FR2: LLM cost tracking and budget dashboard
- FR3: Agent performance analytics

**Missing Management:**
- FR4: User management CRUD interface
- FR5: Role assignment and permissions UI

**Incomplete Features:**
- FR6: Prompts page missing editor, versioning, testing
- FR7: Tools page missing OAuth2 config, tenant selection
- FR8: Tenants form missing multiple required fields

**Quality Issues:**
- FR9: UI/UX inconsistencies across pages
- FR10: Unnecessary pages (tickets, health, unclear purpose)

---

## FR Coverage Map

| FR | Description | Epic | Stories |
|----|-------------|------|---------|
| FR1 | Workers monitoring | Epic 2 | 2.1-2.5 |
| FR2 | LLM cost dashboard | Epic 1 | 1.1-1.4 |
| FR3 | Agent performance | Epic 1 | 1.5-1.8 |
| FR4 | User management | Epic 3 | 3.1-3.3 |
| FR5 | Role management | Epic 3 | 3.4-3.5 |
| FR6 | Prompts enhancement | Epic 4 | 4.1-4.3 |
| FR7 | Tools enhancement | Epic 4 | 4.4-4.5 |
| FR8 | Tenants fix | Epic 4 | 4.6 |
| FR9 | UI/UX consistency | Epic 5 | 5.1-5.3 |
| FR10 | Page cleanup | Epic 5 | 5.4 |

---

# Epic 1: Analytics & Monitoring Dashboards

**Goal:** Deliver LLM cost tracking and agent performance analytics to operations and admin users

**Value:** Enables cost control, performance optimization, and operational visibility - critical for production use

**Priority:** P0 (Must Have)

**API Status:** ✅ All APIs exist and ready (`/api/costs/*`, `/api/agents/*/metrics`)

**RBAC:**
- LLM Costs: admin + operator only
- Agent Performance: admin + developer

**Estimated Stories:** 8 stories

---

## Story 1.1: LLM Cost Dashboard - Overview Metrics

**As an** operations manager,
**I want** to see real-time cost summary metrics,
**So that** I can track spend and stay within budget.

**Acceptance Criteria:**

**Given** I have admin or operator role
**When** I navigate to `/dashboard/llm-costs`
**Then** I see a dashboard with:
- Today's spend (USD, formatted)
- This week's spend (USD, 7-day rolling)
- This month's spend (USD, month-to-date)
- Top spending tenant (name + amount)
- Top spending agent (name + amount)
- All metrics update every 60 seconds (auto-refresh)
- Loading states during fetch
- Error states if API fails

**And** metrics display with proper formatting:
- Currency: $1,234.56 (2 decimal places)
- Large numbers: 1.2K, 1.2M notation
- Percentage change indicators (↑ 15% vs yesterday)

**Prerequisites:** None (first story in epic)

**Technical Notes:**
- API: GET `/api/costs/summary` (returns CostSummaryDTO)
- Use React Query for data fetching with 60s refetch interval
- Implement loading skeletons for metrics cards
- Error boundary for graceful degradation
- Responsive: 4 cols desktop, 2 cols tablet, 1 col mobile

**Tasks:**
1. Create `nextjs-ui/app/dashboard/llm-costs/page.tsx`
2. Create custom hook `useLLMCostSummary()` with React Query
3. Create `CostMetricsCards` component with loading states
4. Add proper TypeScript types for CostSummaryDTO
5. Implement auto-refresh (60s interval)
6. Add error handling and retry logic
7. Write unit tests for metrics display
8. Test RBAC (admin/operator only, redirect others)

---

## Story 1.2: LLM Cost Dashboard - Daily Spend Trend Chart

**As an** operations manager,
**I want** to see a 30-day daily spend trend chart,
**So that** I can identify spending patterns and anomalies.

**Acceptance Criteria:**

**Given** I am on the LLM Costs dashboard
**When** the page loads
**Then** I see an interactive line chart showing:
- 30 days of daily spend data
- X-axis: dates (MM/DD format)
- Y-axis: USD amount (auto-scaled)
- Hover tooltip: date, exact amount, delta vs previous day
- Smooth line with gradient fill
- Responsive sizing (full width on mobile)

**And** chart interactions work:
- Zoom in/out on specific date ranges
- Export as PNG button
- Legend toggle for multiple series (if future enhancement)

**Prerequisites:** Story 1.1 (page structure exists)

**Technical Notes:**
- API: GET `/api/costs/trend?days=30` (returns DailySpendDTO[])
- Use Recharts or Chart.js for visualization
- Implement date formatting with date-fns
- Responsive container with min-height 300px
- Gradient fill under line (accent-blue with alpha)

**Tasks:**
1. Create `DailySpendChart` component
2. Create `useLLMCostTrend()` hook with React Query
3. Configure Recharts Line component with proper styling
4. Add hover tooltip with custom formatter
5. Implement export-to-PNG functionality
6. Add loading skeleton for chart area
7. Handle empty state (no data available)
8. Write tests for date formatting and data transformations

---

## Story 1.3: LLM Cost Dashboard - Token Breakdown Pie Chart

**As an** operations manager,
**I want** to see token usage breakdown by type,
**So that** I understand where tokens are being consumed.

**Acceptance Criteria:**

**Given** I am on the LLM Costs dashboard
**When** the token breakdown section loads
**Then** I see a pie/donut chart showing:
- Input tokens (percentage + count)
- Output tokens (percentage + count)
- Total tokens (center of donut)
- Color-coded slices (consistent with design system)
- Hover tooltip: token type, count, percentage

**And** data table below chart shows:
- Token type | Count | Cost | Percentage
- Sortable columns
- Formatted numbers (1.2M notation)

**Prerequisites:** Story 1.1 (page exists)

**Technical Notes:**
- API: GET `/api/costs/token-breakdown?start_date=&end_date=` (returns TokenBreakdownDTO[])
- Use Recharts PieChart with responsive container
- Date range selector: Last 7 days, Last 30 days, Custom
- Table component from shadcn/ui
- Calculate percentages client-side

**Tasks:**
1. Create `TokenBreakdownChart` component (pie/donut)
2. Create `TokenBreakdownTable` component with sorting
3. Create `useTokenBreakdown()` hook with date range params
4. Implement date range selector component
5. Add color palette for token types
6. Format large numbers (1.2M, 1.2K)
7. Add loading states for chart + table
8. Write tests for percentage calculations

---

## Story 1.4: LLM Cost Dashboard - Budget Utilization Progress Bars

**As an** operations manager,
**I want** to see budget utilization for each tenant,
**So that** I can prevent overspend and take action before budgets are exceeded.

**Acceptance Criteria:**

**Given** I am on the LLM Costs dashboard
**When** the budget section loads
**Then** I see a list of tenants with:
- Tenant name
- Budget amount (USD)
- Spent amount (USD)
- Progress bar (percentage filled)
- Color coding: green (< 75%), yellow (75-90%), red (> 90%)
- Alert icon if > 100%

**And** for each tenant entry:
- Click to expand details (agent-level breakdown)
- Filter by: All tenants, Over budget only, High utilization (> 75%)

**Prerequisites:** Story 1.1 (page exists)

**Technical Notes:**
- API: GET `/api/costs/budget-utilization` (returns BudgetUtilizationDTO[])
- Progress bar component from shadcn/ui
- Color thresholds: < 75% = green-500, 75-90% = yellow-500, > 90% = red-500
- Expandable rows show agent-level spend
- Sort by: highest utilization, alphabetical

**Tasks:**
1. Create `BudgetUtilizationList` component with expandable rows
2. Create `useBudgetUtilization()` hook
3. Implement color-coded progress bars with thresholds
4. Add filter dropdown (All, Over budget, High utilization)
5. Create agent-level breakdown expand section
6. Add sort functionality
7. Handle edge cases (no budget set, $0 budget)
8. Write tests for threshold logic

---

## Story 1.5: Agent Performance Dashboard - Metrics Overview

**As a** developer or admin,
**I want** to see performance metrics for a selected agent,
**So that** I can identify slow or failing agents.

**Acceptance Criteria:**

**Given** I have developer or admin role
**When** I navigate to `/dashboard/agent-performance`
**Then** I see:
- Agent selector dropdown (all active agents)
- Date range selector (Last 7 days, Last 30 days, Custom)
- Metrics cards showing:
  - Total executions
  - Success rate (percentage)
  - Average execution time (seconds)
  - P95 execution time (seconds)
  - Total errors
  - Error rate (percentage)

**And** metrics update when:
- Different agent selected
- Date range changed
- Auto-refresh every 60 seconds

**Prerequisites:** None (first story for agent performance)

**Technical Notes:**
- API: GET `/api/agents/{id}/metrics?start_date=&end_date=` (returns AgentMetricsDTO)
- Fetch agent list: GET `/api/agents` (for dropdown)
- Use React Query with invalidation on agent/date change
- Format time values: < 1s show ms, >= 1s show seconds with 2 decimals
- Success rate = (total - errors) / total * 100

**Tasks:**
1. Create `nextjs-ui/app/dashboard/agent-performance/page.tsx`
2. Create `AgentSelector` dropdown component
3. Create `DateRangeSelector` component (reusable)
4. Create `useAgentMetrics()` hook with agent_id + date params
5. Create `AgentMetricsCards` component
6. Add loading skeletons for metrics
7. Implement auto-refresh (60s)
8. Write tests for metric calculations and formatting

---

## Story 1.6: Agent Performance Dashboard - Execution Trend Chart

**As a** developer,
**I want** to see execution count and duration trends over time,
**So that** I can spot performance degradation.

**Acceptance Criteria:**

**Given** I am viewing an agent's performance
**When** the trends section loads
**Then** I see a dual-axis chart showing:
- Left Y-axis: Execution count (bar chart)
- Right Y-axis: Average execution time in seconds (line chart)
- X-axis: Date (hourly or daily based on range)
- Hover tooltip: timestamp, count, avg time
- Responsive layout

**And** chart has controls:
- Toggle between hourly/daily granularity
- Show/hide execution count bars
- Show/hide execution time line

**Prerequisites:** Story 1.5 (page exists)

**Technical Notes:**
- API: GET `/api/agents/{id}/trends?start_date=&end_date=&granularity=hourly|daily`
- Use Recharts ComposedChart (bar + line)
- Granularity: < 7 days = hourly, >= 7 days = daily
- Auto-select granularity based on date range
- Format time axis with date-fns

**Tasks:**
1. Create `ExecutionTrendChart` component
2. Create `useAgentTrends()` hook with granularity param
3. Configure Recharts ComposedChart (dual Y-axis)
4. Implement granularity toggle (hourly/daily)
5. Add legend with show/hide toggles
6. Format hover tooltips
7. Add loading state
8. Write tests for granularity logic

---

## Story 1.7: Agent Performance Dashboard - Error Analysis Table

**As a** developer,
**I want** to see a breakdown of errors by type and frequency,
**So that** I can prioritize bug fixes.

**Acceptance Criteria:**

**Given** I am viewing agent performance
**When** the error analysis section loads
**Then** I see a table with:
- Error type/message (truncated, expandable)
- Occurrences (count)
- First seen (timestamp)
- Last seen (timestamp)
- Affected executions (count)
- Severity indicator (based on frequency)

**And** table features:
- Sort by any column
- Search/filter by error message
- Click row to see full error details + stack trace
- Pagination (20 per page)
- Export to CSV

**Prerequisites:** Story 1.5 (page exists)

**Technical Notes:**
- API: GET `/api/agents/{id}/error-analysis?start_date=&end_date=` (returns ErrorAnalysisDTO[])
- Use shadcn/ui Table with sorting + pagination
- Severity: < 5 occurrences = low, 5-20 = medium, > 20 = high
- Truncate error messages to 80 chars, expand on click
- Modal for full error details

**Tasks:**
1. Create `ErrorAnalysisTable` component with sorting
2. Create `useAgentErrorAnalysis()` hook
3. Implement search/filter input
4. Add severity badges (low/medium/high)
5. Create error detail modal component
6. Implement CSV export function
7. Add pagination controls
8. Write tests for sorting and filtering

---

## Story 1.8: Agent Performance Dashboard - Slowest Executions List

**As a** developer,
**I want** to see the slowest agent executions,
**So that** I can optimize performance bottlenecks.

**Acceptance Criteria:**

**Given** I am viewing agent performance
**When** the slowest executions section loads
**Then** I see a list showing:
- Top 20 slowest executions
- Execution ID (clickable to details)
- Duration (seconds, 2 decimals)
- Timestamp
- Input size (if applicable)
- Status (success/error)
- Agent name

**And** list features:
- Filter by status (all, success only, errors only)
- Click execution ID to view full details
- Show duration as bar chart (visual comparison)

**Prerequisites:** Story 1.5 (page exists)

**Technical Notes:**
- API: GET `/api/agents/slowest?limit=20&start_date=&end_date=` (returns SlowAgentMetricsDTO[])
- Link to execution history page for details
- Bar chart: max width = slowest execution, others scaled proportionally
- Color code bars: green (< 5s), yellow (5-15s), red (> 15s)

**Tasks:**
1. Create `SlowestExecutionsList` component
2. Create `useSlowestExecutions()` hook
3. Implement mini bar chart for duration visualization
4. Add status filter dropdown
5. Create link to execution details page
6. Add color coding based on duration thresholds
7. Handle empty state (no slow executions)
8. Write tests for duration formatting

---

# Epic 2: Worker Monitoring System

**Goal:** Provide operational visibility into Celery worker health and enable worker management

**Value:** Critical for production operations - monitors infrastructure health, enables troubleshooting, prevents downtime

**Priority:** P0 (Must Have)

**API Status:** ❌ **BACKEND REQUIRED** - No REST API exists, Streamlit uses direct Celery/K8s access

**RBAC:** admin only

**Blockers:** Must create backend API endpoints first before frontend work can begin

**Estimated Stories:** 5 stories (1 backend, 4 frontend)

---

## Story 2.1: Workers API - Backend Endpoints (BACKEND)

**As a** backend developer,
**I want** REST API endpoints for worker monitoring,
**So that** the frontend can display worker health without direct Celery access.

**Acceptance Criteria:**

**Given** Celery workers are running
**When** I call the workers API
**Then** I get worker data via REST

**Endpoints Required:**

1. **GET `/api/workers`** - List all workers
   - Returns: worker hostname, status (active/idle/unresponsive), uptime, active tasks, completed tasks, CPU%, memory%, throughput
   - Auth: admin only
   - Response: Array of WorkerStatusDTO

2. **GET `/api/workers/{hostname}/logs`** - Get worker logs
   - Query params: `lines` (default 100), `since` (timestamp)
   - Returns: log entries with timestamps
   - Auth: admin only
   - Fetches from Kubernetes pod logs

3. **POST `/api/workers/{hostname}/restart`** - Restart worker
   - Triggers Kubernetes deployment rollout restart
   - Returns: success/failure status
   - Auth: admin only
   - Logs action to audit log

4. **GET `/api/workers/{hostname}/metrics`** - Get detailed metrics
   - Returns: CPU%, memory%, network I/O, disk I/O, throughput history (7 days)
   - Auth: admin only
   - Fetches from Prometheus

**And** API implements:
- Tenant isolation (X-Tenant-ID header)
- Rate limiting (100 req/min per user)
- Error handling with proper status codes
- Request/response logging

**Prerequisites:** None (first backend story)

**Technical Notes:**
- File: `src/api/workers.py`
- Service: `src/services/worker_service.py` (wrap Celery inspect, K8s API, Prometheus)
- DTOs: `src/schemas/worker.py`
- Reuse logic from `src/admin/utils/worker_helper.py` but wrap in REST API
- Use `kubernetes` Python library for pod operations
- Use `celery.control.inspect()` for worker discovery
- Use `httpx` for Prometheus queries

**Tasks:**
1. Create `src/api/workers.py` with FastAPI router
2. Create `src/services/worker_service.py` with business logic
3. Define DTOs in `src/schemas/worker.py`
4. Implement GET `/api/workers` endpoint (list workers)
5. Implement GET `/api/workers/{hostname}/logs` (fetch K8s logs)
6. Implement POST `/api/workers/{hostname}/restart` (trigger rollout)
7. Implement GET `/api/workers/{hostname}/metrics` (Prometheus data)
8. Add RBAC decorator (@require_role("admin"))
9. Add request validation with Pydantic
10. Write unit tests for service layer
11. Write integration tests for endpoints
12. Update OpenAPI schema
13. Test with actual Celery workers and K8s cluster

---

## Story 2.2: Workers Page - Overview & List (FRONTEND)

**As an** admin,
**I want** to see all Celery workers and their health status,
**So that** I can monitor infrastructure health.

**Acceptance Criteria:**

**Given** I have admin role
**When** I navigate to `/dashboard/workers`
**Then** I see:
- Summary metrics cards:
  - Active workers count
  - Total active tasks
  - Total completed tasks (all time)
  - Average throughput (tasks/min)
- Workers table with columns:
  - Hostname
  - Status badge (active/idle/unresponsive)
  - Uptime (formatted: 2d 5h 30m)
  - Active tasks
  - CPU% (color-coded: green < 70%, yellow 70-85%, red > 85%)
  - Memory% (same color coding)
  - Throughput (tasks/min)
  - Actions: View Logs, Restart

**And** page features:
- Auto-refresh every 30 seconds
- Last refreshed timestamp
- Filter by status (all, active, idle, unresponsive)
- Sort by any column

**Prerequisites:** Story 2.1 (backend API exists)

**Technical Notes:**
- API: GET `/api/workers`
- Use React Query with 30s refetch interval
- Color coding thresholds: < 70% green, 70-85% yellow, > 85% red
- Format uptime with custom formatter
- RBAC: Redirect non-admins to dashboard
- Show warning if no workers found

**Tasks:**
1. Create `nextjs-ui/app/dashboard/workers/page.tsx`
2. Create `useWorkers()` hook with React Query
3. Create `WorkerMetricsCards` component
4. Create `WorkersTable` component with sorting
5. Add status badges component
6. Implement uptime formatter
7. Add CPU/memory color coding
8. Implement filter dropdown
9. Add auto-refresh with timestamp display
10. Write tests for formatting and color logic

---

## Story 2.3: Workers Page - Logs Viewer Modal

**As an** admin,
**I want** to view worker logs in a modal,
**So that** I can troubleshoot issues without leaving the page.

**Acceptance Criteria:**

**Given** I am viewing the workers list
**When** I click "View Logs" for a worker
**Then** a modal opens showing:
- Worker hostname in header
- Last 100 log lines (newest first)
- Timestamp for each line
- Log level color coding (ERROR = red, WARN = yellow, INFO = blue, DEBUG = gray)
- Auto-scroll to bottom option (toggle)
- Refresh button (fetch latest logs)
- Download logs as .txt button

**And** modal features:
- Search/filter logs by keyword
- Line numbers
- Monospace font
- Dark theme (readable)
- Close with X or ESC key

**Prerequisites:** Story 2.2 (page exists)

**Technical Notes:**
- API: GET `/api/workers/{hostname}/logs?lines=100`
- Use shadcn/ui Dialog component
- Log level detection: regex match ERROR, WARN, INFO, DEBUG
- Virtualized list for performance (react-window or similar)
- Download uses Blob + URL.createObjectURL

**Tasks:**
1. Create `WorkerLogsModal` component
2. Create `useWorkerLogs()` hook with hostname param
3. Implement log level color coding
4. Add search/filter input
5. Implement auto-scroll toggle
6. Add refresh button with loading state
7. Implement download functionality
8. Add keyboard shortcut (ESC to close)
9. Write tests for log parsing and filtering

---

## Story 2.4: Workers Page - Restart Worker Confirmation

**As an** admin,
**I want** to restart a worker with confirmation,
**So that** I can recover from worker issues safely.

**Acceptance Criteria:**

**Given** I am viewing the workers list
**When** I click "Restart" for a worker
**Then** a confirmation dialog opens showing:
- Warning message: "Restarting will terminate active tasks on this worker"
- Worker hostname
- Current active tasks count
- Confirmation checkbox: "I understand active tasks will be lost"
- Cancel button
- Confirm Restart button (disabled until checkbox checked)

**And** when I confirm restart:
- API call to restart worker
- Success toast: "Worker {hostname} restart initiated"
- Worker status updates to "restarting" in table
- Auto-refresh detects when worker comes back online
- If restart fails, error toast with retry option

**Prerequisites:** Story 2.2 (page exists)

**Technical Notes:**
- API: POST `/api/workers/{hostname}/restart`
- Use shadcn/ui AlertDialog
- Optimistic update: set status = "restarting" immediately
- Poll for worker status every 5s (max 12 attempts = 60s)
- If worker doesn't come back in 60s, show warning
- Log restart action to audit log (backend)

**Tasks:**
1. Create `RestartWorkerDialog` component
2. Create `useRestartWorker()` mutation hook
3. Implement confirmation checkbox logic
4. Add optimistic update for worker status
5. Implement polling for worker recovery
6. Add success/error toast notifications
7. Handle restart timeout (60s)
8. Write tests for confirmation flow

---

## Story 2.5: Workers Page - Performance Metrics Chart

**As an** admin,
**I want** to see CPU and memory trends for a worker,
**So that** I can identify resource issues over time.

**Acceptance Criteria:**

**Given** I am viewing the workers list
**When** I click a worker row to expand
**Then** I see an expanded section showing:
- Last 7 days of metrics
- Dual-axis line chart:
  - Left Y-axis: CPU% (blue line)
  - Right Y-axis: Memory% (green line)
  - X-axis: Date/time
- Hover tooltip: timestamp, CPU%, Memory%
- Throughput mini chart (tasks/min over 7 days)

**And** expanded section includes:
- Collapse button
- Detailed worker info:
  - OS version
  - Python version
  - Celery version
  - Connected queues
  - Worker config (max tasks per child, etc.)

**Prerequisites:** Story 2.2 (page exists)

**Technical Notes:**
- API: GET `/api/workers/{hostname}/metrics`
- Use Recharts ComposedChart
- Fetch metrics on expand (not pre-loaded)
- Cache metrics for 5 minutes (React Query)
- 7-day data with hourly granularity

**Tasks:**
1. Create `WorkerMetricsChart` component
2. Create `useWorkerMetrics()` hook with hostname param
3. Implement expandable row in table
4. Configure dual-axis Recharts chart
5. Add throughput mini chart
6. Display detailed worker info
7. Add collapse/expand animation
8. Write tests for metrics data transformation

---

# Epic 3: User & Role Management System

**Goal:** Provide complete RBAC management UI for admins to manage users, assign roles, and control access

**Value:** Enables proper access control and user administration - critical for enterprise deployment

**Priority:** P0 (Must Have)

**API Status:** ⚠️ **PARTIAL** - Some endpoints exist (`/api/users/me`), need full CRUD

**RBAC:** super_admin and tenant_admin only

**Estimated Stories:** 5 stories (2 backend, 3 frontend)

---

## Story 3.1: Users API - Full CRUD Endpoints (BACKEND)

**As a** backend developer,
**I want** complete user management API endpoints,
**So that** admins can manage users via the UI.

**Acceptance Criteria:**

**Given** I have super_admin or tenant_admin role
**When** I call user management endpoints
**Then** I can perform all user operations

**Endpoints Required:**

1. **GET `/api/users`** - List all users (tenant-scoped)
   - Query params: `tenant_id` (optional, super_admin can see all), `is_active`, `role`, `limit`, `offset`
   - Returns: PaginatedResponse<UserDetailDTO>
   - Auth: super_admin (all users) or tenant_admin (tenant users only)

2. **POST `/api/users`** - Create new user
   - Body: email, password, default_tenant_id, initial_role
   - Validates: email format, password strength, tenant exists
   - Returns: UserDetailDTO
   - Auth: super_admin or tenant_admin
   - Side effects: Sends welcome email, creates initial role assignment

3. **PUT `/api/users/{id}`** - Update user
   - Body: email (optional), is_active, default_tenant_id
   - Validates: cannot disable last super_admin
   - Returns: UserDetailDTO
   - Auth: super_admin or tenant_admin (own tenant users only)

4. **DELETE `/api/users/{id}`** - Soft delete user
   - Sets is_active = false
   - Validates: cannot delete self, cannot delete last super_admin
   - Returns: 204 No Content
   - Auth: super_admin or tenant_admin
   - Side effects: Revokes all tokens, logs to audit log

5. **POST `/api/users/{id}/reset-password`** - Admin password reset
   - Generates temporary password
   - Returns: temporary password (show once)
   - Auth: super_admin or tenant_admin
   - Side effects: Sends reset email, forces password change on next login

**And** API implements:
- Tenant isolation (tenant_admin can only manage their tenant's users)
- Role-based authorization (@require_role("super_admin", "tenant_admin"))
- Input validation (Pydantic schemas)
- Audit logging for all user changes

**Prerequisites:** None (extends existing auth system)

**Technical Notes:**
- Extend existing `src/api/users.py`
- Reuse `src/services/user_service.py` and `src/services/auth_service.py`
- Add to existing DTOs in `src/schemas/user.py`
- Password validation: min 8 chars, 1 uppercase, 1 number, 1 special
- Use existing User model from `src/database/models.py`

**Tasks:**
1. Add GET `/api/users` endpoint with pagination
2. Add POST `/api/users` endpoint (create)
3. Add PUT `/api/users/{id}` endpoint (update)
4. Add DELETE `/api/users/{id}` endpoint (soft delete)
5. Add POST `/api/users/{id}/reset-password` endpoint
6. Implement tenant-scoped filtering logic
7. Add validation: cannot delete/disable last super_admin
8. Add audit logging for all operations
9. Write unit tests for service layer
10. Write integration tests for all endpoints
11. Update OpenAPI schema
12. Test with multiple tenants and roles

---

## Story 3.2: Users Management Page - List & CRUD

**As a** super_admin or tenant_admin,
**I want** to view and manage users,
**So that** I can control who has access to the system.

**Acceptance Criteria:**

**Given** I have super_admin or tenant_admin role
**When** I navigate to `/dashboard/users`
**Then** I see:
- Users table with columns:
  - Email
  - Default tenant (name, not ID)
  - Roles (comma-separated list: "Admin (Tenant A), Viewer (Tenant B)")
  - Status (active/inactive badge)
  - Last login (relative time: "2 hours ago")
  - Created date
  - Actions: Edit, Reset Password, Deactivate/Activate
- "Create User" button (top right)
- Search by email input
- Filter by: Active status, Role, Tenant
- Pagination (20 per page)

**And** table features:
- Sort by any column
- Click row to view full user details
- Bulk actions: Deactivate selected users

**And** RBAC enforcement:
- super_admin: sees all users from all tenants
- tenant_admin: sees only users with roles in their tenant

**Prerequisites:** Story 3.1 (backend API exists)

**Technical Notes:**
- API: GET `/api/users?limit=20&offset=0&tenant_id=&is_active=&role=`
- Use shadcn/ui Table with sorting + pagination
- Implement debounced search (300ms delay)
- Use React Query with pagination state
- Role badges: color-coded by role level
- Redirect non-admin users to dashboard

**Tasks:**
1. Create `nextjs-ui/app/dashboard/users/page.tsx`
2. Create `useUsers()` hook with pagination + filters
3. Create `UsersTable` component with sorting
4. Implement search input with debounce
5. Add filter dropdowns (status, role, tenant)
6. Create action buttons (Edit, Reset Password, Deactivate)
7. Add "Create User" button linking to `/dashboard/users/new`
8. Implement bulk selection and actions
9. Write tests for filtering and pagination

---

## Story 3.3: Users Management - Create/Edit User Form

**As a** super_admin or tenant_admin,
**I want** to create and edit users via a form,
**So that** I can onboard new users and update existing ones.

**Acceptance Criteria:**

**Given** I am on the users page
**When** I click "Create User" or "Edit" action
**Then** a form modal/page opens with fields:
- Email (required, validated)
- Password (required for create, optional for edit)
- Password confirmation (must match)
- Default tenant (dropdown, required)
- Initial role for default tenant (dropdown: super_admin, tenant_admin, developer, operator, viewer)
- Is active (checkbox, edit only)
- Send welcome email (checkbox, create only, default checked)

**And** form validation:
- Email: RFC 5322 format
- Password: min 8 chars, 1 uppercase, 1 number, 1 special char
- Real-time validation feedback
- Submit button disabled until valid

**And** on successful submit:
- Create: Success toast "User {email} created", navigate to user detail
- Edit: Success toast "User {email} updated", close modal
- Error: Show error message, keep form open

**And** special cases:
- Creating duplicate email: Show error "Email already exists"
- Editing own account: Disable "is_active" field (cannot deactivate self)

**Prerequisites:** Story 3.2 (page exists)

**Technical Notes:**
- API: POST `/api/users` (create), PUT `/api/users/{id}` (edit)
- Use React Hook Form with Zod validation
- Password strength meter (visual indicator)
- Use shadcn/ui Form components
- Tenant dropdown: fetch from GET `/api/tenants`

**Tasks:**
1. Create `UserForm` component (reusable for create/edit)
2. Create Zod schema for user validation
3. Implement password strength meter
4. Create `useCreateUser()` mutation hook
5. Create `useUpdateUser()` mutation hook
6. Fetch tenants for dropdown
7. Add real-time validation feedback
8. Handle form submission with error states
9. Add success/error toast notifications
10. Write tests for validation rules

---

## Story 3.4: Role Assignment API (BACKEND)

**As a** backend developer,
**I want** API endpoints to assign and revoke roles,
**So that** admins can manage user permissions.

**Acceptance Criteria:**

**Given** I have super_admin or tenant_admin role
**When** I call role assignment endpoints
**Then** I can manage user-tenant-role mappings

**Endpoints Required:**

1. **POST `/api/users/{user_id}/roles`** - Assign role to user
   - Body: tenant_id, role (enum: RoleEnum)
   - Validates: user exists, tenant exists, role is valid
   - Returns: RoleAssignment
   - Auth: super_admin or tenant_admin (own tenant only)
   - Side effects: Creates UserTenantRole record, logs to audit

2. **DELETE `/api/users/{user_id}/roles/{role_id}`** - Revoke role
   - Validates: cannot remove last super_admin role
   - Returns: 204 No Content
   - Auth: super_admin or tenant_admin
   - Side effects: Deletes UserTenantRole record, logs to audit

3. **GET `/api/users/{user_id}/roles`** - List user's roles
   - Returns: Array of RoleAssignment (tenant + role pairs)
   - Auth: super_admin, tenant_admin (own tenant), or user viewing own roles

4. **GET `/api/roles`** - List available roles
   - Returns: Array of {role_enum, display_name, description, level}
   - Auth: any authenticated user
   - Used to populate role dropdowns

**And** special validation:
- Cannot assign role for tenant user doesn't have access to (unless super_admin)
- Cannot create duplicate role assignments (user + tenant + role must be unique)
- tenant_admin can only assign roles for their own tenant

**Prerequisites:** Story 3.1 (user API exists)

**Technical Notes:**
- File: `src/api/roles.py` (new router)
- Reuse UserTenantRole model from `src/database/models.py`
- Add to existing `src/schemas/user.py` for DTOs
- Validation logic in service layer

**Tasks:**
1. Create `src/api/roles.py` with FastAPI router
2. Add POST `/api/users/{user_id}/roles` endpoint
3. Add DELETE `/api/users/{user_id}/roles/{role_id}` endpoint
4. Add GET `/api/users/{user_id}/roles` endpoint
5. Add GET `/api/roles` endpoint (list all available roles)
6. Implement validation: cannot remove last super_admin
7. Add tenant-scoped authorization
8. Add audit logging
9. Write unit tests
10. Write integration tests
11. Update OpenAPI schema

---

## Story 3.5: Role Assignment UI

**As a** super_admin or tenant_admin,
**I want** to assign and revoke user roles via the UI,
**So that** I can control user permissions across tenants.

**Acceptance Criteria:**

**Given** I am viewing a user detail page
**When** I navigate to the "Roles" tab
**Then** I see:
- Current role assignments table:
  - Tenant name
  - Role (badge with color coding)
  - Assigned date
  - Actions: Revoke button
- "Assign New Role" button
- Empty state if no roles assigned

**And** when I click "Assign New Role":
- Modal opens with:
  - Tenant selector dropdown
  - Role selector dropdown (filtered by available roles for that tenant)
  - Assign button
- On submit:
  - Success toast "Role {role} assigned to {user} for tenant {tenant}"
  - Table updates with new role
  - Modal closes

**And** when I click "Revoke":
- Confirmation dialog: "Are you sure you want to revoke {role} for {tenant}?"
- On confirm:
  - API call to revoke
  - Success toast "Role revoked"
  - Row removed from table
- Special case: If revoking last super_admin role, show error "Cannot remove last super_admin"

**And** RBAC enforcement:
- super_admin: can assign any role for any tenant
- tenant_admin: can only assign roles for own tenant

**Prerequisites:** Story 3.4 (backend API), Story 3.2 (user page exists)

**Technical Notes:**
- API: POST `/api/users/{id}/roles`, DELETE `/api/users/{id}/roles/{role_id}`, GET `/api/roles`
- Use shadcn/ui Table for roles list
- Modal with form for assignment
- AlertDialog for revoke confirmation
- Fetch available roles from GET `/api/roles`
- Filter tenants based on current user's role

**Tasks:**
1. Create `UserRolesTab` component
2. Create `AssignRoleModal` component
3. Create `useAssignRole()` mutation hook
4. Create `useRevokeRole()` mutation hook
5. Fetch available roles for dropdown
6. Implement tenant filtering (tenant_admin sees only own tenant)
7. Add revoke confirmation dialog
8. Handle special case: last super_admin
9. Add success/error toasts
10. Write tests for role assignment flow

---

# Epic 4: Feature Completion & Enhancement

**Goal:** Complete partial implementations and add missing functionality to existing pages

**Value:** Achieves feature parity with Streamlit UI, delivers complete user experience

**Priority:** P1 (Should Have)

**API Status:** ✅ APIs ready

**Estimated Stories:** 6 stories

---

## Story 4.1: Prompts Page - Rich Text Editor

**As a** developer or admin,
**I want** a rich text editor for system prompts,
**So that** I can easily compose and preview prompts with formatting.

**Acceptance Criteria:**

**Given** I am on the Prompts page
**When** I click "Create Prompt" or "Edit" on existing prompt
**Then** I see a rich editor with:
- Syntax highlighting for `{{variables}}`
- Line numbers
- Character count (live update)
- Warning at 8000+ characters (yellow)
- Error at 12000+ characters (red, blocks save)
- Markdown preview pane (split view toggle)
- Variable substitution preview (replaces {{var}} with sample values)

**And** editor features:
- Find/replace
- Undo/redo
- Keyboard shortcuts (Ctrl+S to save)
- Auto-save draft every 30 seconds (local storage)
- Restore draft on return

**And** variable handling:
- Detects all `{{variable}}` patterns
- Lists detected variables below editor
- Provides sample values for preview
- Warns about undefined variables

**Prerequisites:** None (enhances existing prompts page)

**Technical Notes:**
- Use CodeMirror or Monaco Editor (VS Code editor)
- Markdown preview: use react-markdown
- Variable detection: regex `/\{\{(\w+)\}\}/g`
- Auto-save: localStorage with prompt_id key
- Character count widget in editor gutter

**Tasks:**
1. Install and configure Monaco Editor or CodeMirror
2. Create `PromptEditor` component with syntax highlighting
3. Implement variable detection and listing
4. Add markdown preview pane
5. Implement variable substitution preview
6. Add character count warning/error
7. Implement auto-save to localStorage
8. Add keyboard shortcuts (Ctrl+S)
9. Write tests for variable detection

---

## Story 4.2: Prompts Page - Version History

**As a** developer,
**I want** to view and revert to previous prompt versions,
**So that** I can recover from mistakes and track changes.

**Acceptance Criteria:**

**Given** I am editing a prompt
**When** I click the "Version History" tab
**Then** I see a list of previous versions:
- Version number (auto-incrementing)
- Saved date/time (relative: "2 hours ago")
- Description (if provided)
- Character count
- Actions: View, Revert

**And** when I click "View" on a version:
- Modal opens with:
  - Full prompt text (read-only)
  - Version metadata
  - Diff view comparing to current version
  - Close button

**And** when I click "Revert":
- Confirmation dialog: "Revert to version {N}? Current prompt will be saved as new version."
- On confirm:
  - API call to revert (creates new version with old content)
  - Success toast "Reverted to version {N}"
  - Editor updates with old content
  - Version list refreshes

**And** version history includes:
- Pagination (20 versions per page)
- Search by description
- Filter by date range

**Prerequisites:** Story 4.1 (editor exists)

**Technical Notes:**
- API: GET `/api/prompts/{id}/versions`, POST `/api/prompts/{id}/versions/revert`
- Diff view: use react-diff-viewer
- Version storage handled by backend (already exists in Streamlit version)
- Revert creates new version (immutable history)

**Tasks:**
1. Create `VersionHistoryTab` component
2. Create `usePromptVersions()` hook
3. Create `VersionDiffModal` for viewing
4. Implement diff comparison view
5. Create `useRevertPromptVersion()` mutation
6. Add revert confirmation dialog
7. Implement pagination for versions
8. Add search and date filter
9. Write tests for revert logic

---

## Story 4.3: Prompts Page - LLM Test Feature

**As a** developer,
**I want** to test my prompt with a real LLM,
**So that** I can validate prompt quality before deploying.

**Acceptance Criteria:**

**Given** I am editing a prompt
**When** I click the "Test" tab
**Then** I see a test interface with:
- Model selector dropdown (all available LLM models)
- User message input (simulates agent input)
- Temperature slider (0.0 - 1.0, default 0.7)
- Max tokens input (default 500)
- "Run Test" button

**And** when I click "Run Test":
- Loading state (spinner + "Testing prompt...")
- Calls LLM with: system_prompt (from editor) + user_message + model + params
- Shows result panel:
  - LLM response (formatted, markdown)
  - Token usage (input tokens, output tokens, total)
  - Execution time (seconds)
  - Cost estimate (USD, based on token usage)
  - "Copy Response" button

**And** result history:
- Stores last 5 test runs (session only, not persisted)
- Can view previous runs
- Compare responses side-by-side

**Prerequisites:** Story 4.1 (editor exists)

**Technical Notes:**
- API: POST `/api/llm/test` (accepts system_prompt, user_message, model, temperature, max_tokens)
- Fetch models: GET `/api/llm/models` (or reuse from existing)
- Cost calculation: backend returns cost based on model pricing
- Response formatting: use react-markdown for LLM output
- Session storage for test history (not persisted to DB)

**Tasks:**
1. Create `PromptTestTab` component
2. Create `useLLMTest()` mutation hook
3. Fetch available models for dropdown
4. Implement temperature slider
5. Create result display component
6. Add token usage and cost display
7. Implement test history (session storage, last 5)
8. Add copy-to-clipboard for response
9. Write tests for cost calculation

---

## Story 4.4: Tools Page - OAuth2 Scope Selection

**As a** developer or admin,
**I want** to select OAuth2 scopes when configuring tools,
**So that** I can control API access permissions.

**Acceptance Criteria:**

**Given** I am importing an OpenAPI spec with OAuth2
**When** I reach the "Configure Import" step
**Then** I see OAuth2 configuration section with:
- Flow type selector (if multiple flows available)
- Client ID input
- Client Secret input (masked, show/hide toggle)
- Token URL (pre-filled from spec, editable)
- Scopes multi-select:
  - List all available scopes from spec
  - Each scope shows: name + description
  - "Select All" button
  - "Deselect All" button
  - Search/filter scopes input

**And** scope selection UI:
- Checkboxes for each scope
- Selected count indicator (e.g., "5 of 23 selected")
- Grouped by category (if spec provides scope groups)
- Selected scopes highlighted

**And** validation:
- At least one scope must be selected
- Client ID required
- Client Secret required
- Submit disabled until valid

**Prerequisites:** None (enhances existing tools page)

**Technical Notes:**
- Existing tools page parses OpenAPI spec
- OAuth2 flows from `spec.components.securitySchemes`
- Scopes from `flows.{flowType}.scopes`
- Use shadcn/ui Checkbox for multi-select
- Store selected scopes in form state

**Tasks:**
1. Enhance `ImportConfig` component with OAuth2 section
2. Parse OAuth2 flows and scopes from spec
3. Create multi-select scope UI with checkboxes
4. Implement "Select All" / "Deselect All"
5. Add search/filter for scopes
6. Add selected count indicator
7. Implement form validation
8. Update form submission to include scopes
9. Write tests for scope parsing and selection

---

## Story 4.5: Tools Page - Test Connection Feature

**As a** developer or admin,
**I want** to test API connection before importing,
**So that** I can validate credentials and connectivity.

**Acceptance Criteria:**

**Given** I have configured auth for an OpenAPI tool
**When** I click "Test Connection" button
**Then** the system:
- Makes a test API call to the first available endpoint (GET preferred)
- Shows loading state "Testing connection..."
- Displays result:
  - Success: ✅ "Connection successful! Status: 200 OK" + response preview
  - Failure: ❌ "Connection failed: {error message}" + details

**And** success result includes:
- HTTP status code
- Response time (ms)
- Response headers (collapsible)
- Response body preview (first 500 chars, formatted JSON if applicable)

**And** failure result includes:
- Error type (Network error, Auth error, Timeout, etc.)
- HTTP status code (if applicable)
- Error message
- Troubleshooting tips (based on error type)
- Retry button

**And** test behavior:
- Timeout after 10 seconds
- Uses configured auth (API key, Bearer, Basic, OAuth2)
- Does not save anything (read-only test)

**Prerequisites:** None (enhances existing tools page)

**Technical Notes:**
- API: POST `/api/openapi-tools/test-connection` (already exists in Streamlit version)
- Request body: spec, auth_config
- Backend makes actual HTTP call to target API
- Timeout: 10s on backend
- Error handling: network errors, auth errors, timeouts

**Tasks:**
1. Add "Test Connection" button to ImportConfig component
2. Create `useTestConnection()` mutation hook
3. Create `ConnectionTestResult` component for displaying results
4. Implement success state UI
5. Implement failure state UI with troubleshooting tips
6. Add response preview formatting (JSON pretty-print)
7. Add retry functionality
8. Handle timeout and network errors
9. Write tests for error handling

---

## Story 4.6: Tenants Form - Complete Field Coverage

**As an** admin,
**I want** to create/edit tenants with all required fields,
**So that** tenant configuration is complete and functional.

**Acceptance Criteria:**

**Given** I am creating or editing a tenant
**When** I fill out the tenant form
**Then** I see all fields from Streamlit version:
- Name (required, text input)
- Description (optional, textarea)
- Logo URL (optional, text input with preview)
- **Tool Type** (dropdown: "ServiceDesk Plus", "Jira", "None")
- **ServiceDesk URL** (text input, required if tool_type selected)
- **Is Active** (toggle switch, default ON)
- **Enhancement Preferences** (JSON editor or key-value pairs)

**And** field validation:
- Name: 3-100 chars, alphanumeric + spaces
- ServiceDesk URL: valid URL format, required if tool_type != None
- Enhancement Preferences: valid JSON format
- Logo URL: valid URL (http/https), optional

**And** enhancement preferences UI:
- Option 1: JSON editor (CodeMirror) with validation
- Option 2: Key-value form (add/remove pairs, converts to JSON)
- Default value: `{"auto_enhance": true, "priority_boost": false}`

**And** on submit:
- Validation errors shown inline
- Success: toast "Tenant {name} created/updated"
- Navigate to tenant detail page

**Prerequisites:** None (fixes existing tenants page)

**Technical Notes:**
- API: POST `/api/tenants` (create), PUT `/api/tenants/{id}` (update)
- Enhancement preferences stored as JSONB in database
- Use Zod for form validation
- Logo preview: load image on URL change (debounced)
- Tool type enum: matches backend enum

**Tasks:**
1. Update `TenantForm` component with all missing fields
2. Add tool_type dropdown with options
3. Add servicedesk_url input (conditional on tool_type)
4. Add is_active toggle switch
5. Add enhancement_preferences editor (JSON or key-value)
6. Implement logo preview
7. Update Zod schema with all field validations
8. Update form submission to include all fields
9. Test create and edit flows
10. Write tests for validation rules

---

# Epic 5: UI/UX Consistency & Cleanup

**Goal:** Ensure consistent design system usage and remove unnecessary pages

**Value:** Professional, cohesive user experience with no confusing or broken pages

**Priority:** P2 (Nice to Have)

**Estimated Stories:** 4 stories

---

## Story 5.1: Design System Audit & Fix

**As a** user,
**I want** consistent UI/UX across all pages,
**So that** the application feels professional and cohesive.

**Acceptance Criteria:**

**Given** all pages are implemented
**When** I navigate through the application
**Then** I see consistent:
- Color palette (matches design system)
- Typography (font sizes, weights, line heights)
- Spacing (margins, padding using 4px/8px grid)
- Border radius (consistent across cards, buttons, inputs)
- Shadow depths (consistent elevation levels)
- Button styles (primary, secondary, ghost variants)
- Input styles (focus states, error states)
- Loading states (skeleton screens, spinners)
- Empty states (consistent messaging and illustrations)
- Error states (consistent error message formatting)

**And** navigation is consistent:
- Sidebar menu styling
- Active page indicator
- Breadcrumbs (if applicable)
- Page headers (consistent layout)

**And** responsive behavior:
- All pages work on mobile (320px+)
- All pages work on tablet (768px+)
- All pages work on desktop (1024px+)
- No horizontal scroll on any breakpoint

**Prerequisites:** All pages implemented (Epics 1-4 complete)

**Technical Notes:**
- Use design tokens from tailwind.config.ts
- Audit against Apple Liquid Glass design system
- Use Figma/design spec as reference (if available)
- Test on multiple screen sizes
- Use browser dev tools + responsive design mode

**Tasks:**
1. Create audit checklist (colors, typography, spacing, etc.)
2. Audit all pages against checklist
3. Document inconsistencies in spreadsheet
4. Fix color inconsistencies (update tailwind classes)
5. Fix typography inconsistencies
6. Fix spacing inconsistencies
7. Fix component style inconsistencies (buttons, inputs, cards)
8. Test responsive behavior on all breakpoints
9. Fix any responsive issues
10. Create design system documentation page (optional)

---

## Story 5.2: Accessibility (A11y) Compliance - WCAG 2.1 AA

**As a** user with accessibility needs,
**I want** the application to meet WCAG 2.1 AA standards,
**So that** I can use it with assistive technologies.

**Acceptance Criteria:**

**Given** all pages are implemented
**When** I audit for accessibility
**Then** all pages pass WCAG 2.1 AA:
- Color contrast ratios: min 4.5:1 for normal text, 3:1 for large text
- All interactive elements keyboard accessible (Tab, Enter, Space, Esc)
- Focus indicators visible (outline or ring)
- Form labels properly associated with inputs
- ARIA labels for icon-only buttons
- Alt text for images
- Semantic HTML (proper heading hierarchy)
- Screen reader support (test with NVDA/JAWS)

**And** accessibility features:
- Skip to main content link
- Reduced motion support (prefers-reduced-motion CSS)
- High contrast mode support
- Keyboard shortcuts documented and accessible
- Error messages announced to screen readers

**Prerequisites:** Story 5.1 (design system consistent)

**Technical Notes:**
- Use axe DevTools for automated testing
- Manual testing with keyboard navigation
- Test with screen reader (NVDA on Windows, VoiceOver on Mac)
- Use next/image for optimized alt text
- Implement useReducedMotion hook for animations

**Tasks:**
1. Run axe DevTools audit on all pages
2. Fix color contrast issues
3. Add ARIA labels to icon-only buttons
4. Ensure all form labels properly associated
5. Add alt text to all images
6. Fix heading hierarchy (h1 → h2 → h3, no skips)
7. Test keyboard navigation on all pages
8. Add focus indicators (visible outlines/rings)
9. Implement skip-to-content link
10. Add prefers-reduced-motion CSS
11. Test with screen reader
12. Document accessibility features

---

## Story 5.3: Loading States & Error Handling Consistency

**As a** user,
**I want** consistent loading and error states,
**So that** I always understand what's happening.

**Acceptance Criteria:**

**Given** any page makes an API call
**When** data is loading
**Then** I see appropriate loading state:
- Skeleton screens for content areas (not just spinners)
- Disabled buttons during mutations
- Loading spinners for small actions
- Progress indicators for multi-step processes

**And** when an error occurs:
- Toast notification for mutations (create, update, delete)
- Inline error messages for forms
- Error boundary for React crashes
- Retry button for failed API calls
- Helpful error messages (not just "Error 500")

**And** empty states are consistent:
- Consistent illustration/icon
- Helpful message explaining why empty
- Clear call-to-action (e.g., "Create your first X")
- Consistent styling across all empty states

**Prerequisites:** Story 5.1 (design system)

**Technical Notes:**
- Create reusable `LoadingSkeleton` component
- Create reusable `EmptyState` component
- Create reusable `ErrorState` component
- Use React Error Boundary for crash handling
- Toast library: sonner or react-hot-toast

**Tasks:**
1. Create `LoadingSkeleton` component library
2. Create `EmptyState` component with variants
3. Create `ErrorState` component with retry
4. Create React Error Boundary component
5. Audit all pages for loading states
6. Replace spinners with skeletons where appropriate
7. Audit all pages for error handling
8. Add retry buttons to failed API calls
9. Improve error messages (user-friendly)
10. Test error scenarios (network offline, 500 errors, etc.)

---

## Story 5.4: Remove Unnecessary Pages & Cleanup

**As a** user,
**I want** only relevant pages in navigation,
**So that** I'm not confused by broken or unclear pages.

**Acceptance Criteria:**

**Given** all features are implemented
**When** I audit the page list
**Then** I identify and handle unnecessary pages:
- **tickets page** - unclear purpose, audit if needed or remove
- **health page** - may duplicate Operations page, consolidate or remove
- **agents-config page** - may overlap with agents page, consolidate or remove

**And** for each unnecessary page:
- Determine if it should be:
  1. Removed entirely (delete page + navigation link)
  2. Consolidated into another page (merge functionality)
  3. Renamed/repurposed (clarify purpose)
- Update navigation sidebar
- Add redirects if needed (old URL → new URL)
- Update any internal links
- Remove from RBAC config if deleted

**And** cleanup actions:
- Remove unused components
- Remove unused API routes (if any)
- Update documentation
- Remove from sitemap

**Prerequisites:** All features complete

**Technical Notes:**
- Audit criteria: page usage, functionality overlap, user value
- Create redirect in middleware.ts if needed
- Update navigation in sidebar component
- Use git to track deletions

**Tasks:**
1. Audit all Next.js pages and document purpose
2. Identify pages for removal: tickets, health, agents-config
3. For each page, decide: remove, consolidate, or keep
4. If consolidate: merge functionality into target page
5. If remove: delete page file + navigation link
6. Add redirects for removed pages (middleware.ts)
7. Update sidebar navigation component
8. Remove unused components
9. Update documentation
10. Test navigation and redirects

---

## Summary

**Total Epics:** 5
**Total Stories:** 28

**Breakdown:**
- Epic 1 (Analytics): 8 stories
- Epic 2 (Workers): 5 stories (1 backend + 4 frontend)
- Epic 3 (Users/RBAC): 5 stories (2 backend + 3 frontend)
- Epic 4 (Feature Completion): 6 stories
- Epic 5 (UI/UX): 4 stories

**Backend Work Required:** 3 stories
- Story 2.1: Workers API
- Story 3.1: Users API (extend existing)
- Story 3.4: Role Assignment API

**Frontend Work:** 25 stories

**Priority Distribution:**
- P0 (Must Have): Epics 1, 2, 3 (18 stories)
- P1 (Should Have): Epic 4 (6 stories)
- P2 (Nice to Have): Epic 5 (4 stories)

**API Readiness:**
- ✅ Ready: Epics 1, 4, 5 (APIs exist)
- ⚠️ Partial: Epic 3 (some APIs missing)
- ❌ Blocked: Epic 2 (no API, backend work required)

**Recommended Sequence:**
1. **Sprint 1**: Epic 1 (Analytics) - immediate value, APIs ready
2. **Sprint 2**: Epic 2 Backend (Story 2.1) + Epic 3 Backend (Stories 3.1, 3.4)
3. **Sprint 3**: Epic 2 Frontend (Workers UI) + Epic 3 Frontend (Users UI)
4. **Sprint 4**: Epic 4 (Feature Completion)
5. **Sprint 5**: Epic 5 (UI/UX Polish)

---

**Next Steps:**
1. Review and approve this epic breakdown
2. Prioritize which epic to start first
3. Run `/bmad:bmm:workflows:create-story` for first story to generate detailed implementation plan
4. Begin development

---

_This document provides the complete roadmap for achieving Next.js UI feature parity. Each story includes detailed acceptance criteria, technical notes, and task breakdowns for implementation._
