# Admin UI Guide

**AI Agents Enhancement Platform - Streamlit Admin Interface**

**Version:** 1.0.0
**Last Updated:** 2025-11-04
**Story:** 6.8 - Create Admin UI Documentation and Deployment Guide
**Supersedes:** `admin-ui-setup.md` (Story 6.1 foundation guide)

---

## Table of Contents

- [Overview](#overview)
  - [Purpose](#purpose)
  - [Target Audience](#target-audience)
  - [Features Summary](#features-summary)
  - [Architecture](#architecture)
- [Quick Start](#quick-start)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [First Login](#first-login)
  - [Verify Connection](#verify-connection)
- [Access & Authentication](#access--authentication)
  - [Local Development Authentication](#local-development-authentication)
  - [Production Authentication (Kubernetes)](#production-authentication-kubernetes)
  - [Security Best Practices](#security-best-practices)
- [Features](#features)
  - [Dashboard Page](#dashboard-page)
  - [Tenant Management](#tenant-management)
  - [Enhancement History](#enhancement-history)
  - [System Operations](#system-operations)
  - [Real-Time Metrics](#real-time-metrics)
  - [Worker Monitoring](#worker-monitoring)
- [Local Development Setup](#local-development-setup)
  - [Detailed Prerequisites](#detailed-prerequisites)
  - [Step-by-Step Installation](#step-by-step-installation)
  - [Running the Application](#running-the-application)
  - [Local Troubleshooting](#local-troubleshooting)
- [Kubernetes Deployment](#kubernetes-deployment)
  - [Deployment Prerequisites](#deployment-prerequisites)
  - [Build Docker Image](#build-docker-image)
  - [Setup Authentication](#setup-authentication)
  - [Deploy Manifests](#deploy-manifests)
  - [Verify Deployment](#verify-deployment)
  - [Configure Local Access](#configure-local-access)
- [Configuration Reference](#configuration-reference)
  - [Environment Variables](#environment-variables)
  - [Streamlit Configuration](#streamlit-configuration)
  - [Resource Limits](#resource-limits)
  - [RBAC Permissions](#rbac-permissions)
- [Troubleshooting](#troubleshooting)
  - [Database Connection Failures](#database-connection-failures)
  - [Authentication Issues](#authentication-issues)
  - [Worker Monitoring Not Loading](#worker-monitoring-not-loading)
  - [Pod Crashes or Restarts](#pod-crashes-or-restarts)
  - [WebSocket Connection Lost](#websocket-connection-lost)
  - [Port Conflicts (Local)](#port-conflicts-local)
- [Security Considerations](#security-considerations)
  - [Authentication Methods](#authentication-methods)
  - [Secrets Management](#secrets-management)
  - [Network Security](#network-security)
  - [Database Access](#database-access)
  - [Audit Logging](#audit-logging)
  - [Production Hardening Checklist](#production-hardening-checklist)
- [Future Enhancements](#future-enhancements)
- [Quick Reference](#quick-reference)
  - [Common Commands](#common-commands)
  - [Useful URLs](#useful-urls)
  - [Troubleshooting Quick Checks](#troubleshooting-quick-checks)
  - [Configuration Files](#configuration-files)
- [Screenshots](#screenshots)
- [Related Documentation](#related-documentation)
- [References](#references)

---

## Overview

### Purpose

The AI Agents Admin UI provides operations teams and developers with a powerful web-based interface for managing and monitoring the multi-tenant ticket enhancement platform. Built with Streamlit 1.44+, it eliminates the need for kubectl access while providing comprehensive system visibility and control.

**Key Benefits:**
- **No kubectl Required:** Web-based access to all operations
- **Real-Time Monitoring:** Live metrics, health status, and performance data
- **Multi-Tenant Management:** Centralized tenant configuration and monitoring
- **Enhanced Troubleshooting:** Direct access to logs, history, and diagnostics
- **Production-Ready:** Secure authentication, resource controls, and audit logging

### Target Audience

This guide serves two primary audiences:

**1. Developers:**
- Local development setup and configuration
- Architecture understanding and code integration
- Feature usage and API integration
- Testing and validation procedures

**2. Operations Engineers:**
- Kubernetes deployment and management
- Production configuration and scaling
- Security hardening and compliance
- Troubleshooting and incident response
- Performance tuning and monitoring

### Features Summary

The Admin UI consists of six primary pages, each addressing specific operational needs:

| Page | Purpose | Key Features |
|------|---------|--------------|
| **Dashboard** | System status overview | Real-time metrics cards, database health, system indicators |
| **Tenant Management** | Configure tenants | CRUD operations, API config, encrypted secrets, validation |
| **Enhancement History** | Track processing | Filters (tenant/status/date/search), pagination, detail viewer, CSV export |
| **System Operations** | Control operations | Pause/resume processing, queue management, tenant sync, restart |
| **Real-Time Metrics** | Performance monitoring | Prometheus charts (queue depth, success rate, latency), time range selector |
| **Worker Monitoring** | Worker health tracking | Worker table, resource metrics (CPU/memory), logs viewer, restart operations |

### Architecture

The Admin UI operates as an independent Streamlit application with the following architecture:

```
┌─────────────────────────────────────────────────────────────┐
│                    AI Agents Admin UI                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐  │
│  │  Streamlit   │   │   Session    │   │  Multi-Page  │  │
│  │  App (3.12)  │──▶│    Auth      │──▶│  Navigation  │  │
│  └──────────────┘   └──────────────┘   └──────────────┘  │
│         │                                      │           │
│         ▼                                      ▼           │
│  ┌─────────────────────────────────────────────────────┐  │
│  │              Page Components                         │  │
│  │  • Dashboard (6.2)    • Operations (6.5)            │  │
│  │  • Tenants (6.3)      • Metrics (6.6)               │  │
│  │  • History (6.4)      • Workers (6.7)               │  │
│  └─────────────────────────────────────────────────────┘  │
│         │                   │                │             │
└─────────┼───────────────────┼────────────────┼─────────────┘
          │                   │                │
          ▼                   ▼                ▼
   ┌─────────────┐    ┌─────────────┐  ┌────────────┐
   │ PostgreSQL  │    │ Prometheus  │  │ Kubernetes │
   │  Database   │    │   Metrics   │  │    API     │
   └─────────────┘    └─────────────┘  └────────────┘
```

**Component Details:**

- **Streamlit Application:** Python 3.12-based web framework
- **Authentication:** Session-based (dev) or NGINX basic auth (prod)
- **Database Access:** Synchronous SQLAlchemy session (shared models)
- **Kubernetes Integration:** ServiceAccount with RBAC for worker operations
- **Resource Allocation:** 256Mi/100m CPU requests, 512Mi/500m CPU limits

**Deployment Options:**

1. **Local Development:** Direct execution via `streamlit run` command
2. **Kubernetes Production:** Containerized deployment with Ingress routing

---

## Quick Start

Get the Admin UI running in minutes with this streamlined setup.

### Prerequisites

**Minimum Requirements:**
- Python 3.12 or higher
- PostgreSQL 16+ (running and accessible)
- Docker (optional, for Kubernetes deployment)
- Kubernetes cluster 1.28+ (for production deployment)

### Installation

```bash
# 1. Navigate to project root
cd /path/to/ai-agents

# 2. Create and activate virtual environment
python3.12 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -e ".[dev]"

# 4. Configure database connection
export AI_AGENTS_DATABASE_URL="postgresql://aiagents:password@localhost:5432/ai_agents"
```

### First Login

```bash
# Start the application
streamlit run src/admin/app.py

# Access in browser
# Open: http://localhost:8501
```

**Default Credentials:**
- Username: `admin`
- Password: `admin`

⚠️ **Security Note:** Change default credentials for any non-development environment.

### Verify Connection

After logging in:

1. Navigate to **Dashboard** page (should load automatically)
2. Check **Database Connection Status** section
3. Verify indicators show:
   - ✅ Connected to PostgreSQL
   - Database version displayed (e.g., PostgreSQL 16.x)
   - Number of configured tenants

**If connection fails:** See [Troubleshooting → Database Connection Failures](#database-connection-failures)

---

## Access & Authentication

The Admin UI supports two authentication modes optimized for different deployment environments.

### Local Development Authentication

**Method:** Session-based authentication with local secrets file

**Setup:**

1. Create secrets file (if it doesn't exist):

```bash
mkdir -p .streamlit
cp .streamlit/secrets.toml.template .streamlit/secrets.toml
```

2. Edit `.streamlit/secrets.toml`:

```toml
[credentials]
[credentials.usernames]
[credentials.usernames.admin]
password = "your-secure-password-here"
name = "Administrator"
email = "admin@example.com"
```

**Default Behavior:**
If `secrets.toml` is not configured, the application uses default credentials (`admin`/`admin`).

**Security for Local Dev:**
- `.streamlit/secrets.toml` is git-ignored (never commit)
- Session expires after browser closure
- Suitable for single-developer environments only

### Production Authentication (Kubernetes)

**Method:** NGINX Ingress basic authentication with htpasswd

**How It Works:**

1. htpasswd file is created with encrypted credentials
2. Kubernetes Secret stores the htpasswd data
3. NGINX Ingress Controller enforces authentication before routing
4. Streamlit application receives authenticated requests

**Setup Script:**

```bash
# Create authentication secret
./scripts/setup-streamlit-auth.sh admin "YourSecurePassword123!"
```

This script:
- Generates htpasswd file with bcrypt encryption
- Creates Kubernetes Secret `streamlit-basic-auth`
- Configures proper namespace and annotations

**Manual Setup (Alternative):**

```bash
# Generate htpasswd file
htpasswd -c /tmp/auth admin

# Create Kubernetes Secret
kubectl create secret generic streamlit-basic-auth \
  --from-file=auth=/tmp/auth \
  --namespace=ai-agents

# Cleanup
rm /tmp/auth
```

**Verify Authentication Setup:**

```bash
# Check secret exists
kubectl get secret streamlit-basic-auth -n ai-agents

# View secret structure (not decrypted values)
kubectl get secret streamlit-basic-auth -n ai-agents -o yaml
```

### Security Best Practices

**Password Requirements:**
- ✅ Minimum 20 characters for production
- ✅ Mix of uppercase, lowercase, numbers, special characters
- ✅ No dictionary words or common patterns
- ❌ Avoid reusing passwords from other systems

**Secret Rotation:**
- **Development:** Every 180 days
- **Production:** Every 90 days
- **After Incident:** Immediately

**Access Control:**
- Restrict admin UI to internal networks only
- Use VPN or IP whitelisting for remote access
- Enable audit logging (see [Audit Logging](#audit-logging))
- Monitor failed authentication attempts

**Future Enhancement Path:**

Current basic authentication is MVP-appropriate. Planned upgrades:

| Phase | Method | Timeline |
|-------|--------|----------|
| MVP (Current) | NGINX Basic Auth | Implemented |
| Phase 2 | OAuth2-Proxy + Azure AD | Epic 7 |
| Phase 3 | RBAC (Admin/Operator/Viewer) | Epic 8 |

---

## Features

Detailed documentation for each page of the Admin UI.

### Dashboard Page

**Story:** 6.2 - Implement System Status Dashboard Page
**Route:** `/` (default landing page)
**Purpose:** Real-time system status overview and health monitoring

#### What It Does

The Dashboard provides at-a-glance visibility into system health with four key metrics cards and detailed database connection information.

#### Key Features

**1. Metrics Cards (Auto-Refresh Every 30 Seconds)**

| Metric | Description | Alert Thresholds |
|--------|-------------|------------------|
| **Database Status** | PostgreSQL connection health | 🟢 Connected / 🔴 Disconnected |
| **Active Tenants** | Number of enabled tenant configurations | Count display |
| **Queue Depth** | Pending jobs in Redis queue | 🟢 <100 / 🟡 100-500 / 🔴 >500 |
| **Success Rate** | Enhancement processing success percentage (24h) | 🟢 >95% / 🟡 90-95% / 🔴 <90% |

**2. Database Connection Details**

- PostgreSQL version information
- Connection string format (credentials masked)
- Connection pool status
- Last connection timestamp

**3. System Health Indicators**

Visual status indicators across all system components:
- 🟢 Healthy: All systems operational
- 🟡 Warning: Performance degradation detected
- 🔴 Critical: Component failure or threshold breach

#### Usage

**View Real-Time Status:**
1. Navigate to Dashboard (automatic on login)
2. Metrics auto-refresh every 30 seconds
3. Click refresh icon (↻) for manual update

**Interpret Metrics:**
- **Queue Depth Growing:** Potential worker capacity issue
- **Low Success Rate:** Check Enhancement History for error patterns
- **Database Disconnected:** Verify connectivity (see [Troubleshooting](#database-connection-failures))

#### Technical Details

- **Implementation:** `src/admin/pages/1_Dashboard.py`
- **Auto-Refresh:** Uses `@st.fragment` for partial updates (Story 6.2 pattern)
- **Database Queries:** Cached for 30 seconds (performance optimization)
- **Dependencies:** SQLAlchemy, Redis client

**[Screenshot Placeholder: Dashboard Page - System Status Overview]**

*Figure 1: Dashboard page showing metrics cards (top row), database connection details (left panel), and system health indicators with color-coded status. Navigation sidebar visible on left with all six pages listed.*

---

### Tenant Management

**Story:** 6.3 - Create Tenant Management Interface
**Route:** `/Tenants`
**Purpose:** CRUD operations for tenant configurations and ServiceDesk Plus API settings

#### What It Does

The Tenant Management page allows administrators to configure multi-tenant settings, including API credentials and webhook secrets, with automatic encryption for sensitive data.

#### Key Features

**1. Tenant List Table**

Displays all configured tenants with columns:
- **Name:** Tenant identifier (unique)
- **API URL:** ServiceDesk Plus endpoint
- **API Key:** Encrypted (shows "●●●●●●●●" + encryption status indicator 🔒)
- **Webhook Secret:** Encrypted
- **Active Status:** ✅ Active / ❌ Inactive toggle
- **Actions:** Edit / Delete buttons

**2. Add/Edit Tenant Form**

**Required Fields:**
- Tenant Name (alphanumeric, underscore, hyphen only)
- ServiceDesk Plus API URL (validated HTTPS format)
- API Key (encrypted with Fernet before storage)
- Webhook Secret (encrypted with Fernet before storage)

**Optional Fields:**
- Active Status (default: enabled)
- Metadata JSON (custom configuration)

**3. Validation Rules**

- Tenant name must be unique
- API URL must be valid HTTPS endpoint
- API Key and Webhook Secret cannot be empty
- Test connection button validates credentials against ServiceDesk Plus API

**4. Encryption**

- **Algorithm:** Fernet (symmetric encryption)
- **Key Source:** Environment variable `FERNET_KEY`
- **Fields Encrypted:** API Key, Webhook Secret
- **Indicator:** 🔒 icon shows field is encrypted
- **Rotation:** Supports key rotation (decrypt with old key, encrypt with new key)

#### Usage

**Add New Tenant:**
1. Click **Add Tenant** button
2. Fill required fields (Name, API URL, API Key, Webhook Secret)
3. Optional: Test connection to verify credentials
4. Click **Save**
5. Confirmation message appears

**Edit Existing Tenant:**
1. Click **Edit** button in tenant row
2. Modify fields (encrypted fields show as "●●●●●●●●", input new value to update)
3. Click **Save**
4. Changes applied immediately

**Delete Tenant:**
1. Click **Delete** button in tenant row
2. Confirmation dialog appears: "Are you sure? This will orphan enhancement history records."
3. Click **Confirm Delete**
4. Tenant removed from database

⚠️ **Warning:** Deleting a tenant does not delete its enhancement history records. Historical data remains for compliance.

**Test API Connection:**
1. In Add/Edit form, fill API URL and API Key
2. Click **Test Connection** button
3. System attempts API call to ServiceDesk Plus
4. Result displays:
   - ✅ Success: "Connection successful (HTTP 200)"
   - ❌ Failure: "Connection failed (Error message)"

#### Technical Details

- **Implementation:** `src/admin/pages/2_Tenants.py`
- **Database Model:** `TenantConfig` (src/database/models.py)
- **Encryption:** Cryptography library Fernet module
- **API Integration:** ServiceDesk Plus REST API v3
- **Test Suite:** 127 tests passing (see Story 6.3)

**Security Notes:**
- API keys never stored in plaintext
- Webhook secrets encrypted at rest
- Decryption only occurs at request processing time
- RBAC future enhancement will restrict tenant management to admin role

**[Screenshot Placeholder: Tenant Management - List View]**

*Figure 2: Tenant list table showing three configured tenants (ClientA, ClientB, Demo). Each row displays tenant name, masked API credentials with encryption indicator (🔒), active status toggle, and action buttons (Edit/Delete). "Add Tenant" button visible at top.*

**[Screenshot Placeholder: Tenant Management - Edit Form]**

*Figure 3: Edit tenant modal dialog showing form fields: Tenant Name (read-only), API URL (editable), API Key (masked with option to update), Webhook Secret (masked), Active Status (checkbox), Test Connection button, and Save/Cancel buttons. Validation feedback shown for invalid inputs.*

---

### Enhancement History

**Story:** 6.4 - Implement Enhancement History Viewer
**Route:** `/History`
**Purpose:** View and search ticket enhancement processing history with filtering and export

#### What It Does

The Enhancement History page provides comprehensive access to all processed enhancement requests, enabling troubleshooting, auditing, and performance analysis.

#### Key Features

**1. Advanced Filtering**

**Filter Bar Components:**

| Filter | Type | Options |
|--------|------|---------|
| **Tenant** | Dropdown | All tenants, or select specific tenant |
| **Status** | Multi-select | Success, Error, Pending, Processing |
| **Date Range** | Date pickers | From Date, To Date (defaults to last 30 days) |
| **Search** | Text input | Search by ticket ID, customer name, or keywords |

**2. Pagination**

- **Page Size:** Configurable (25, 50, 100, 250 records per page)
- **Navigation:** Previous / Next buttons with page number display
- **Total Count:** Shows "Showing X-Y of Z records"
- **Performance:** Composite index `ix_history_tenant_status_created` optimizes queries

**3. Results Table**

**Columns:**
- Ticket ID (clickable to expand details)
- Tenant Name
- Status (color-coded: 🟢 Success / 🔴 Error / 🟡 Pending / 🔵 Processing)
- Created Timestamp
- Processing Duration (seconds)
- Actions (Expand Details icon)

**4. Detail Viewer (Expandable)**

Click on any record to expand detail panel with three tabs:

**Tab 1: JSON Data**
- Original webhook payload (pretty-printed JSON)
- Enhanced ticket data (structured JSON)
- Request metadata (headers, timestamps)

**Tab 2: Text Enhancement**
- Original ticket description
- AI-generated enhanced description
- Context sources used (tickets, documentation, IP lookup)
- Confidence scores

**Tab 3: Error Details** (if status = Error)
- Error message
- Stack trace
- Retry count
- Last retry timestamp

**5. CSV Export**

- **Button:** "Export to CSV" (top-right of page)
- **Scope:** Exports current filtered results (respects all active filters)
- **Filename Format:** `enhancement_history_YYYY-MM-DD_HHMMSS.csv`
- **Columns:** All table columns plus expanded details (JSON flattened)
- **Limit:** Maximum 10,000 records per export (performance protection)

#### Usage

**Basic Search:**
1. Navigate to **Enhancement History** page
2. Select tenant from dropdown (or leave as "All")
3. Select status filters (or leave all checked)
4. Click **Apply Filters**

**Advanced Search:**
1. Enter ticket ID in search box (e.g., "REQ-12345")
2. Set date range (e.g., last 7 days)
3. Select specific tenant and status
4. Click **Apply Filters**

**View Details:**
1. Locate record in results table
2. Click **Expand** icon (▼) in Actions column
3. Detail panel appears below record with three tabs
4. Navigate tabs to view JSON, enhanced text, or error details
5. Click **Collapse** icon (▲) to hide details

**Export Data:**
1. Apply desired filters
2. Click **Export to CSV** button
3. Browser downloads CSV file
4. Open in Excel, Google Sheets, or analysis tools

#### Technical Details

- **Implementation:** `src/admin/pages/3_History.py`
- **Database Model:** `EnhancementHistory` (src/database/models.py)
- **Query Optimization:** Composite index on `(tenant_id, status, created_at)`
- **Pagination Pattern:** Custom Streamlit pagination (Story 6.4 best practice)
- **Test Suite:** 22 tests passing

**Performance Considerations:**
- **Query Limit:** Pagination prevents loading entire dataset
- **Index Usage:** Composite index reduces query time from ~2s to ~50ms (1000 records)
- **CSV Export Limit:** 10,000 records maximum (configurable in code)
- **Cache:** Filter results cached for 60 seconds (same filters = instant load)

**[Screenshot Placeholder: Enhancement History - Filter and Search]**

*Figure 4: Enhancement History page showing filter bar at top (Tenant dropdown, Status checkboxes, Date pickers, Search box), results table with 10 visible records, and pagination controls at bottom (Page 1 of 15, showing 1-25 of 372 records). One record is expanded showing the three-tab detail panel.*

**[Screenshot Placeholder: Enhancement History - Detail Expander]**

*Figure 5: Close-up of expanded detail panel for a single enhancement record. Three tabs visible: "JSON Data" (active, showing pretty-printed webhook payload), "Text Enhancement" (enhanced description with highlighting), "Error Details" (disabled for successful record). Panel shows collapse button (▲) in top-right.*

---

### System Operations

**Story:** 6.5 - Add System Operations Controls
**Route:** `/Operations`
**Purpose:** Control system operations without kubectl access

#### What It Does

The System Operations page provides web-based controls for common administrative tasks, enabling operations teams to manage the system without direct Kubernetes access.

#### Key Features

**1. Processing Controls**

**Pause/Resume Processing:**
- **Pause Button:** Stops workers from processing new enhancement jobs
  - Existing jobs complete
  - New webhook requests are queued but not processed
  - Status indicator changes to 🟡 PAUSED
- **Resume Button:** Restarts job processing
  - Workers begin processing queued jobs
  - Status indicator changes to 🟢 PROCESSING

**Use Cases:**
- Maintenance windows
- Database migrations
- Emergency response (high error rate)
- Capacity management during peak loads

**2. Queue Management**

**Clear Queues Button:**
- Removes all pending jobs from Redis queue
- **Warning:** Destructive operation requiring confirmation
- Confirmation dialog: "Clear all queued jobs? This cannot be undone. X jobs will be lost."
- Use case: Clear backlog after incident resolution

**Inspect Queues Button:**
- Displays queue statistics without modifications:
  - Total pending jobs
  - Jobs by status (pending, processing, failed)
  - Oldest job timestamp
  - Newest job timestamp
  - Average job age

**3. Tenant Configuration Sync**

**Sync Tenant Configs Button:**
- Forces reload of tenant configurations from database
- Workers cache tenant config in memory for performance
- Sync operation updates worker cache without restart
- Use case: Apply tenant changes immediately without worker restart

**4. Worker Restart**

**Restart Workers Button:**
- Performs graceful rolling restart of Celery worker deployment
- Uses Kubernetes API to patch deployment with restart annotation
- Workers complete current jobs before terminating
- New workers start automatically (ReplicaSet ensures desired count)
- Confirmation required: "Restart all workers? Current jobs will complete first. Brief service interruption expected."

**5. Operation Logs**

**Logs Viewer:**
- Displays recent operation logs from admin UI and workers
- **Log Levels:** INFO, WARNING, ERROR, CRITICAL (filter dropdown)
- **Auto-Refresh:** 30-second interval (manual refresh button available)
- **Line Limit:** Last 100 lines (configurable up to 1000)
- **Download Logs:** Button to save logs as text file

#### Usage

**Pause Processing for Maintenance:**
1. Navigate to **System Operations** page
2. Check current status indicator (should be 🟢 PROCESSING)
3. Click **Pause Processing** button
4. Confirmation dialog: "Pause all processing? Existing jobs will complete."
5. Click **Confirm**
6. Status changes to 🟡 PAUSED
7. Perform maintenance tasks
8. Click **Resume Processing** when ready
9. Status returns to 🟢 PROCESSING

**Clear Queue After Incident:**
1. Check **Inspect Queues** to see backlog size
2. If queue contains invalid jobs (e.g., from misconfigured webhook), click **Clear Queues**
3. Confirmation dialog shows number of jobs to be deleted
4. Verify number is expected, click **Confirm Delete**
5. Queue cleared, processing can resume with clean slate

**Apply Tenant Configuration Changes:**
1. After editing tenant via **Tenant Management** page
2. Navigate to **System Operations**
3. Click **Sync Tenant Configs**
4. Workers reload configurations from database
5. Confirmation: "Tenant configurations synced successfully"
6. No worker restart required

**Restart Workers (Troubleshooting):**
1. If workers are unresponsive or exhibiting errors
2. Navigate to **System Operations**
3. Click **Restart Workers** button
4. Confirmation dialog: "Restart all workers? Brief interruption expected."
5. Click **Confirm**
6. Kubernetes performs rolling restart
7. Monitor **Worker Monitoring** page to verify workers are healthy

#### Technical Details

- **Implementation:** `src/admin/pages/4_Operations.py`
- **Helper Modules:** `src/admin/utils/operations_helper.py` (5 focused modules, Story 6.5 refactored)
- **Kubernetes API:** Uses `kubernetes` Python client with RBAC permissions
- **Redis Operations:** Direct Redis client for queue management
- **Celery Control:** Celery inspect API for worker communication
- **Test Suite:** 204 tests passing (100% coverage)

**Security Considerations:**
- All destructive operations require confirmation
- Operations logged to audit trail
- RBAC permissions required (deployment patch, pod delete)
- Future enhancement: Role-based access (admin-only operations)

**[Screenshot Placeholder: System Operations - Control Panel]**

*Figure 6: System Operations page showing control panel with six main sections: Processing Controls (Pause/Resume buttons with status indicator 🟢 PROCESSING), Queue Management (Clear/Inspect buttons with current queue depth 42), Tenant Sync button, Worker Restart button (with warning icon ⚠️), and Logs viewer at bottom showing last 100 lines with log level filter.*

---

### Real-Time Metrics

**Story:** 6.6 - Integrate Real-Time Metrics Display
**Route:** `/Metrics`
**Purpose:** Visualize Prometheus metrics with interactive charts

#### What It Does

The Real-Time Metrics page displays performance and health metrics collected by Prometheus, providing insights into system behavior and capacity planning.

#### Key Features

**1. Interactive Plotly Charts**

**Chart 1: Queue Depth Over Time**
- **Metric:** `redis_queue_depth`
- **Y-Axis:** Number of pending jobs
- **X-Axis:** Time
- **Interaction:** Hover tooltips show exact values, zoom/pan enabled
- **Alert Thresholds:** Horizontal lines at 100 (warning) and 500 (critical)

**Chart 2: Success Rate**
- **Metric:** `enhancement_success_rate`
- **Y-Axis:** Percentage (0-100%)
- **X-Axis:** Time
- **Visualization:** Area chart with green fill above 95%, yellow 90-95%, red below 90%
- **Interaction:** Hover shows exact percentage and timestamp

**Chart 3: Latency Percentiles**
- **Metrics:** `enhancement_processing_duration_p50`, `p95`, `p99`
- **Y-Axis:** Duration in milliseconds
- **X-Axis:** Time
- **Lines:** Three traces (P50 blue, P95 orange, P99 red)
- **Interaction:** Toggle traces on/off, zoom to specific time ranges

**2. Time Range Selector**

**Button Group:**
- **1h:** Last hour (60 data points, 1-minute resolution)
- **6h:** Last 6 hours (72 data points, 5-minute resolution)
- **24h:** Last 24 hours (96 data points, 15-minute resolution)
- **7d:** Last 7 days (168 data points, 1-hour resolution)

**Active Selection:** Highlighted button with blue background

**3. Auto-Refresh**

- **Interval:** 60 seconds
- **Method:** `@st.fragment` for partial page updates (Story 6.6 best practice)
- **Indicator:** Timestamp shows "Last updated: 2025-11-04 14:32:15" with countdown timer
- **Manual Refresh:** Button (↻) to refresh immediately

**4. Error Resilience**

- **Cached Data Fallback:** If Prometheus is unavailable, displays last successful query results
- **Error Message:** "⚠️ Prometheus unavailable. Showing cached data from [timestamp]."
- **Retry Logic:** Auto-retries every 60 seconds in background

**5. Performance Optimization**

- **Query Limit:** Maximum 1000 data points per query (prevents browser slowdown)
- **Downsampling:** Larger time ranges use lower resolution (see Time Range Selector)
- **Render Time:** <2 seconds for 1000 points (tested in Story 6.6)

#### Usage

**View Recent Performance:**
1. Navigate to **Real-Time Metrics** page
2. Charts load with default 24h time range
3. Observe queue depth trends, success rate patterns, latency distribution

**Analyze Specific Time Window:**
1. Click time range button (e.g., **1h** for detailed recent view)
2. Charts update to show selected range
3. Use Plotly zoom/pan to focus on specific events

**Identify Performance Issues:**
1. **High Queue Depth:** Indicates worker capacity insufficient for load
   - Solution: Scale workers or optimize processing
2. **Declining Success Rate:** Check Enhancement History for error patterns
   - Solution: Investigate common errors, fix root cause
3. **Increasing Latency:** System slowdown or resource contention
   - Solution: Check Worker Monitoring for resource usage, database performance

**Export Chart Data:**
1. Hover over chart
2. Plotly menu appears in top-right of chart
3. Click camera icon to save as PNG
4. Click download icon to export data as CSV

#### Technical Details

- **Implementation:** `src/admin/pages/6_Metrics.py`
- **Metrics Helper:** `src/admin/utils/metrics_helper.py`
- **Prometheus API:** HTTP API (`/api/v1/query_range`)
- **Chart Library:** Plotly 5.x (interactive JavaScript-based charts)
- **Cache:** Query results cached for 60 seconds (reduces Prometheus load)
- **Test Suite:** 22 tests passing

**Prometheus Configuration:**
- **Endpoint:** `http://prometheus:9090` (Kubernetes service)
- **Scrape Interval:** 15 seconds
- **Retention:** 30 days (configurable in Prometheus config)

**Dependencies:**
- Prometheus server must be deployed and accessible
- Metrics instrumentation in worker and API code (Story 4.1-4.3)
- ServiceMonitor configured for scraping (Story 4.2)

**[Screenshot Placeholder: Real-Time Metrics - Charts and Time Selector]**

*Figure 7: Real-Time Metrics page showing three Plotly charts stacked vertically: (1) Queue Depth line chart with alert threshold lines, (2) Success Rate area chart with color-coded zones, (3) Latency Percentiles with three traces (P50, P95, P99). Time range selector buttons visible at top (1h, 6h, 24h active, 7d). Auto-refresh indicator shows "Last updated: 2025-11-04 14:32:15 (next in 45s)" with manual refresh button.*

---

### Worker Monitoring

**Story:** 6.7 - Add Worker Health and Resource Monitoring
**Route:** `/Workers`
**Purpose:** Monitor Celery worker health, resource utilization, and logs

#### What It Does

The Worker Monitoring page provides comprehensive visibility into Celery worker status, enabling proactive capacity management and rapid troubleshooting.

#### Key Features

**1. Worker Health Table**

**Columns:**

| Column | Description | Alert Thresholds |
|--------|-------------|------------------|
| **Hostname** | Worker pod name (e.g., `celery-worker-0`) | N/A |
| **Status** | 🟢 Active / 🟡 Idle / 🔴 Unresponsive | Ping test every 30s |
| **Uptime** | Duration since worker started | Display only |
| **Active Tasks** | Currently processing jobs | N/A |
| **CPU %** | Current CPU utilization | 🟢 <80% / 🟡 80-95% / 🔴 >95% |
| **Memory %** | Current memory utilization | 🟢 <80% / 🟡 80-95% / 🔴 >95% |
| **Throughput** | Tasks completed per minute (last 5 min) | Display only |
| **Actions** | Restart button, Logs button | N/A |

**Status Determination:**
- **🟢 Active:** Ping successful, processing tasks
- **🟡 Idle:** Ping successful, no active tasks
- **🔴 Unresponsive:** Ping failed (worker may be crashed or network issue)

**2. Resource Metrics**

**Data Sources:**
- **CPU/Memory:** Prometheus metrics (`celery_worker_cpu_percent`, `celery_worker_memory_percent`)
- **Throughput:** Calculated from Celery events (tasks completed in time window)
- **Active Tasks:** Celery inspect API (`app.control.inspect().active()`)

**Alert Indicators:**
- Cells with thresholds breached highlighted in color:
  - 🟢 Green: Healthy (<80%)
  - 🟡 Yellow: Warning (80-95%)
  - 🔴 Red: Critical (>95%)

**3. Worker Operations**

**Restart Button (Per Worker):**
- **Method:** Kubernetes API pod delete
- **Behavior:** Pod deleted, ReplicaSet creates replacement automatically
- **Confirmation Required:** "Restart worker [hostname]? Current tasks will be interrupted."
- **Use Case:** Unresponsive worker, memory leak mitigation

**Restart All Button (Top of Page):**
- **Method:** Deployment annotation patch (triggers rolling restart)
- **Behavior:** Graceful rolling update, one pod at a time
- **Confirmation Required:** "Restart all workers? Brief service interruption expected."
- **Use Case:** Apply configuration changes, clear memory leaks across fleet

**4. Logs Viewer**

**Per-Worker Logs:**
1. Click **Logs** button in worker row
2. Modal opens showing last 100 lines of worker logs
3. **Log Level Filter:** Dropdown to filter (ALL, DEBUG, INFO, WARNING, ERROR, CRITICAL)
4. **Download Logs:** Button to save as `.log` file
5. **Refresh:** Manual refresh button (logs auto-update every 30s)

**Log Viewer Features:**
- **Syntax Highlighting:** Color-coded by log level
- **Timestamps:** Preserved from original logs
- **Scrollable:** Fixed height with scrollbar (prevents page overflow)
- **Search:** Browser find (Ctrl+F) works within log text

**5. Historical Performance Charts**

**Throughput Chart (7-Day View):**
- **Metric:** Tasks completed per minute (aggregated per worker)
- **Visualization:** Line chart with one trace per worker
- **Tabbed Interface:** Tab for each worker hostname
- **Average Line:** Horizontal line showing 7-day average throughput
- **Interaction:** Hover tooltips, zoom, pan, toggle traces

**Use Cases:**
- Identify workers with consistently lower throughput (capacity issue)
- Detect performance degradation over time (memory leak, resource contention)
- Capacity planning (predict when to scale based on trends)

**6. Auto-Refresh**

- **Interval:** 30 seconds (worker health table and metrics)
- **Method:** `@st.fragment` for partial updates
- **Indicator:** "Last updated: [timestamp] (next in Xs)"
- **Manual Refresh:** Button at top of page

#### Usage

**Monitor Worker Health:**
1. Navigate to **Worker Monitoring** page
2. Worker health table loads with current status
3. Check Status column for any 🟡 Idle or 🔴 Unresponsive workers
4. Check CPU % and Memory % for any 🟡 or 🔴 indicators

**Restart Unresponsive Worker:**
1. Identify worker with 🔴 Unresponsive status
2. Click **Restart** button in worker row
3. Confirmation dialog: "Restart worker-0? Current tasks will be interrupted."
4. Click **Confirm**
5. Pod deletes, new pod starts (ReplicaSet maintains desired count)
6. New worker appears in table after ~30 seconds

**View Worker Logs:**
1. Click **Logs** button for specific worker
2. Logs modal opens showing last 100 lines
3. Use Log Level Filter to focus on errors: Select "ERROR"
4. Logs refresh automatically every 30s
5. Click **Download Logs** if needed for offline analysis
6. Close modal when done

**Analyze Historical Throughput:**
1. Scroll to **Historical Performance** section
2. Tabs show one per worker (e.g., "worker-0", "worker-1", "worker-2")
3. Click tab to view specific worker's 7-day throughput chart
4. Observe trends:
   - **Declining Throughput:** Memory leak or resource degradation
   - **Spiky Throughput:** Inconsistent workload (normal) or GC pauses
   - **Flat Zero:** Worker not processing (investigate)

**Capacity Planning:**
1. Check **Throughput** column in worker table
2. Calculate total system throughput: Sum of all workers' throughput
3. Compare to incoming job rate (visible in Real-Time Metrics → Queue Depth)
4. If queue depth consistently growing, scale workers:
   - Kubernetes: `kubectl scale deployment celery-worker --replicas=5`

#### Technical Details

- **Implementation:** `src/admin/pages/5_Workers.py`
- **Worker Helper:** `src/admin/utils/worker_helper.py` (619 lines)
- **Kubernetes API:** Uses `kubernetes` Python client for pod operations
- **Celery API:** `app.control.inspect()` for worker discovery and status
- **RBAC Required:** ServiceAccount `streamlit-admin` with permissions:
  - `pods` (get, list, watch, delete)
  - `pods/log` (get, list)
  - `deployments` (get, list, patch)
- **Test Suite:** 32 tests passing

**CRITICAL Deployment Note:**

Worker Monitoring page will NOT function without proper RBAC setup. The following manifest MUST be applied before deploying the admin UI:

```bash
kubectl apply -f k8s/streamlit-rbac.yaml
```

This creates:
- ServiceAccount: `streamlit-admin`
- Role: `streamlit-admin-role` (permissions listed above)
- RoleBinding: `streamlit-admin-rolebinding` (binds ServiceAccount to Role)

The Streamlit admin deployment manifest references this ServiceAccount:

```yaml
# k8s/streamlit-admin-deployment.yaml
spec:
  template:
    spec:
      serviceAccountName: streamlit-admin  # <-- CRITICAL
```

**Troubleshooting RBAC Issues:**

If Worker Monitoring page shows errors or empty table:

```bash
# 1. Verify ServiceAccount exists
kubectl get serviceaccount streamlit-admin -n ai-agents

# 2. Verify Role exists
kubectl get role streamlit-admin-role -n ai-agents

# 3. Verify RoleBinding exists
kubectl get rolebinding streamlit-admin-rolebinding -n ai-agents

# 4. Verify deployment uses ServiceAccount
kubectl get deployment streamlit-admin -n ai-agents -o yaml | grep serviceAccountName

# 5. Check pod logs for permission errors
kubectl logs -n ai-agents -l app=streamlit-admin | grep -i "forbidden\|unauthorized"
```

**[Screenshot Placeholder: Worker Monitoring - Health Table and Logs]**

*Figure 8: Worker Monitoring page showing worker health table with 3 workers. Columns: Hostname (worker-0, worker-1, worker-2), Status (🟢 Active for all), Uptime, Active Tasks (2, 0, 1), CPU% (45%, 32%, 78% with color coding), Memory% (56%, 48%, 82%), Throughput (12.5, 11.8, 10.2), Actions (Restart/Logs buttons). One worker (worker-2) has 🟡 yellow highlighting on Memory% column. Logs modal is open for worker-0 showing last 100 lines with ERROR level filter applied.*

**[Screenshot Placeholder: Worker Monitoring - Performance Charts]**

*Figure 9: Historical performance section showing tabbed interface with three tabs (worker-0 active, worker-1, worker-2). Line chart displays 7-day throughput (tasks/min) with blue line trace and horizontal dashed line showing average (11.5 tasks/min). X-axis shows dates (Nov 1-7), Y-axis shows throughput (0-20). Hover tooltip displays exact value at point (Nov 4 14:00, 13.2 tasks/min).*

---

## Local Development Setup

Comprehensive guide for setting up the Admin UI in a local development environment.

### Detailed Prerequisites

**1. Python 3.12 or Higher**

Verify installation:
```bash
python3.12 --version
# Expected output: Python 3.12.0 or higher
```

If not installed:
- **macOS:** `brew install python@3.12`
- **Ubuntu:** `sudo apt install python3.12 python3.12-venv`
- **Windows:** Download from [python.org](https://www.python.org/downloads/)

**2. PostgreSQL 16+ Running and Accessible**

Verify PostgreSQL is running:
```bash
# Check PostgreSQL status
pg_isready -h localhost -p 5432
# Expected output: localhost:5432 - accepting connections
```

Verify you can connect:
```bash
psql postgresql://aiagents:password@localhost:5432/ai_agents -c "SELECT 1"
# Expected output:
#  ?column?
# ----------
#         1
```

If PostgreSQL is not running:
```bash
# Docker Compose (recommended for local dev)
docker-compose up -d postgres

# Or system service
sudo systemctl start postgresql  # Linux
brew services start postgresql@16  # macOS
```

**3. Virtual Environment Tool**

Python 3.12 includes `venv` module by default. No separate installation needed.

**4. Git (Optional, for Repository Cloning)**

If not already cloned:
```bash
git clone https://github.com/your-org/ai-agents.git
cd ai-agents
```

### Step-by-Step Installation

**Step 1: Navigate to Project Root**

```bash
cd /path/to/ai-agents
# Verify you're in correct directory
ls -la  # Should see: README.md, pyproject.toml, src/, k8s/, etc.
```

**Step 2: Create Virtual Environment**

```bash
# Create venv in project directory
python3.12 -m venv venv

# Activate venv
source venv/bin/activate  # macOS/Linux
# OR
venv\Scripts\activate  # Windows

# Verify activation (prompt should show "(venv)")
which python
# Expected output: /path/to/ai-agents/venv/bin/python
```

**Step 3: Upgrade pip (Recommended)**

```bash
pip install --upgrade pip
# Ensures latest package manager for smooth installation
```

**Step 4: Install Dependencies**

```bash
# Install project in editable mode with dev dependencies
pip install -e ".[dev]"
```

**What This Installs:**

Core dependencies for Admin UI:
- `streamlit>=1.44.0` - Web UI framework
- `sqlalchemy>=2.0.0` - Database ORM
- `psycopg2-binary>=2.9.9` - PostgreSQL driver (synchronous)
- `pandas>=2.1.0` - Data manipulation for tables
- `plotly>=5.18.0` - Interactive charts (Real-Time Metrics page)
- `kubernetes>=29.0.0` - K8s API client (Worker Monitoring page)
- `psutil>=5.9.0` - Process monitoring
- `cryptography>=42.0.0` - Fernet encryption (Tenant Management page)
- `loguru>=0.7.0` - Structured logging

Dev dependencies (testing and linting):
- `pytest>=7.4.0` - Testing framework
- `pytest-asyncio>=0.21.0` - Async test support
- `pytest-mock>=3.12.0` - Mocking utilities
- `black>=23.12.0` - Code formatter
- `ruff>=0.1.0` - Fast Python linter

**Verify Installation:**

```bash
# Check Streamlit installed correctly
streamlit --version
# Expected output: Streamlit, version 1.44.0 (or higher)

# Check key imports work
python -c "import streamlit, sqlalchemy, pandas, plotly, kubernetes"
# No output = success
```

**Step 5: Configure Database Connection**

**Option A: Environment Variable (Recommended)**

```bash
export AI_AGENTS_DATABASE_URL="postgresql://aiagents:password@localhost:5432/ai_agents"
```

To persist across terminal sessions, add to shell profile:
```bash
# Add to ~/.bashrc (Linux) or ~/.zshrc (macOS)
echo 'export AI_AGENTS_DATABASE_URL="postgresql://aiagents:password@localhost:5432/ai_agents"' >> ~/.bashrc
source ~/.bashrc
```

**Option B: .env File**

```bash
# Create .env file in project root
cat > .env << 'EOF'
AI_AGENTS_DATABASE_URL=postgresql://aiagents:password@localhost:5432/ai_agents
EOF
```

**Note:** `.env` file is git-ignored (already in `.gitignore`). Safe to store credentials locally.

**Verify Configuration:**

```bash
echo $AI_AGENTS_DATABASE_URL
# Should output: postgresql://aiagents:password@localhost:5432/ai_agents

# Test database connection
python -c "from sqlalchemy import create_engine; import os; engine = create_engine(os.environ['AI_AGENTS_DATABASE_URL']); conn = engine.connect(); print('✅ Connected'); conn.close()"
# Expected output: ✅ Connected
```

**Step 6: Configure Authentication (Optional for Local Dev)**

The Admin UI works with default credentials (`admin`/`admin`) if no secrets file is provided. To customize:

```bash
# Create Streamlit config directory
mkdir -p .streamlit

# Copy template (if available)
cp .streamlit/secrets.toml.template .streamlit/secrets.toml

# OR create from scratch
cat > .streamlit/secrets.toml << 'EOF'
[credentials]
[credentials.usernames]
[credentials.usernames.admin]
password = "my-secure-dev-password"
name = "Developer Admin"
email = "dev@example.com"
EOF
```

**Security Note:** `.streamlit/secrets.toml` is git-ignored. Never commit this file.

**Step 7: Run Database Migrations (If Not Already Done)**

```bash
# Apply latest schema migrations
alembic upgrade head
```

Expected output:
```
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade -> 168c9b67e6ca, add_row_level_security_policies
```

### Running the Application

```bash
# From project root, with venv activated
streamlit run src/admin/app.py
```

**Expected Output:**

```
  You can now view your Streamlit app in your browser.

  Local URL: http://localhost:8501
  Network URL: http://192.168.1.100:8501

  For better performance, install the Watchdog module:

  $ pip install watchdog
```

**Access the Application:**

1. Open browser
2. Navigate to http://localhost:8501
3. Login page appears
4. Enter credentials:
   - Username: `admin`
   - Password: `admin` (or custom password from `secrets.toml`)
5. Dashboard page loads

**Stopping the Application:**

Press `Ctrl+C` in terminal where `streamlit run` is executing.

### Local Troubleshooting

**Issue 1: "Module not found" Errors**

**Symptom:**
```
ModuleNotFoundError: No module named 'streamlit'
```

**Solution:**
```bash
# Verify venv is activated
which python
# Should show venv path, not system Python

# If not activated
source venv/bin/activate

# Reinstall dependencies
pip install -e ".[dev]"
```

**Issue 2: "Port 8501 Already in Use"**

**Symptom:**
```
OSError: [Errno 48] Address already in use
```

**Solution:**
```bash
# Find process using port 8501
lsof -i :8501
# Output shows: python 12345 user ...

# Kill process
kill -9 12345

# Or use different port
streamlit run src/admin/app.py --server.port=8502
```

**Issue 3: Database Connection Failed on Dashboard**

**Symptom:**
Dashboard shows "❌ Database connection failed"

**Diagnostics:**
```bash
# 1. Check environment variable is set
echo $AI_AGENTS_DATABASE_URL
# Should output connection string

# 2. Test PostgreSQL is accessible
psql $AI_AGENTS_DATABASE_URL -c "SELECT 1"
# Should output: 1

# 3. Check database exists
psql $AI_AGENTS_DATABASE_URL -c "\dt"
# Should list tables: tenant_config, enhancement_history, etc.
```

**Solutions:**
- **Variable Not Set:** Re-export `AI_AGENTS_DATABASE_URL` or add to shell profile
- **PostgreSQL Not Running:** Start PostgreSQL service or Docker container
- **Database Doesn't Exist:** Create database: `createdb ai_agents`
- **Wrong Credentials:** Verify username/password in connection string

**Issue 4: Import Errors After Code Changes**

**Symptom:**
```
ImportError: cannot import name 'something' from 'src.admin.utils'
```

**Solution:**
```bash
# Reinstall package in editable mode
pip install -e .
# This updates Python's package cache for src/ imports
```

**Issue 5: Slow Page Loads or Timeouts**

**Symptoms:**
- Pages take >10 seconds to load
- Spinner shows indefinitely
- "Connection lost" messages

**Solutions:**
- **Large Database Tables:** Add pagination limits in code
- **Slow Queries:** Check database indexes (see Story 6.4 composite index)
- **Network Issues:** Check PostgreSQL is on localhost (not remote server with high latency)
- **Browser Cache:** Clear browser cache and hard reload (Ctrl+Shift+R)

---

## Kubernetes Deployment

Comprehensive production deployment guide for Kubernetes environments.

### Deployment Prerequisites

**1. Kubernetes Cluster (1.28+)**

Verify cluster access:
```bash
kubectl version --short
# Client Version: v1.28.0
# Server Version: v1.28.3
```

Check cluster health:
```bash
kubectl get nodes
# Expected: All nodes in Ready status
```

**2. kubectl Configured**

```bash
# Test kubectl context
kubectl config current-context
# Should show your cluster name

# Verify access to target namespace
kubectl get ns ai-agents
# If doesn't exist, create it:
kubectl create namespace ai-agents
```

**3. NGINX Ingress Controller Installed**

```bash
# Check Ingress Controller is deployed
kubectl get pods -n ingress-nginx -l app.kubernetes.io/name=ingress-nginx
# Should show running ingress-nginx-controller pods

# If not installed
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.9.4/deploy/static/provider/cloud/deploy.yaml
```

**4. Database Deployed and Accessible**

```bash
# Verify PostgreSQL service exists in cluster
kubectl get svc -n ai-agents postgres
# Should show service with ClusterIP

# Test connectivity from a pod
kubectl run test-db --rm -it --image=postgres:16 -- psql postgresql://aiagents:password@postgres.ai-agents.svc.cluster.local:5432/ai_agents -c "SELECT 1"
# Expected output: 1
```

**5. Docker Installed (for Building Image)**

```bash
docker --version
# Docker version 24.0.0 or higher
```

### Build Docker Image

**Build Command:**

```bash
# From project root
docker build -f docker/streamlit.dockerfile -t ai-agents-streamlit:1.0.0 .
```

**Dockerfile Overview:**

The `docker/streamlit.dockerfile` includes:
- Base image: `python:3.12-slim`
- Dependencies: Copies `pyproject.toml` and installs via pip
- Application code: Copies `src/` directory
- Config: Copies `.streamlit/config.toml`
- Entrypoint: `streamlit run src/admin/app.py --server.port=8501 --server.headless=true`

**Tag and Push to Registry (If Using Private Registry):**

```bash
# Tag for registry
docker tag ai-agents-streamlit:1.0.0 your-registry.com/ai-agents-streamlit:1.0.0

# Push to registry
docker push your-registry.com/ai-agents-streamlit:1.0.0
```

**Note:** If using local cluster (Minikube, Kind, Docker Desktop), no push required. Use local image directly.

**For Minikube:**
```bash
# Load image into Minikube
minikube image load ai-agents-streamlit:1.0.0
```

**For Kind:**
```bash
# Load image into Kind
kind load docker-image ai-agents-streamlit:1.0.0
```

### Setup Authentication

**Using Provided Script (Recommended):**

```bash
# Make script executable (if not already)
chmod +x scripts/setup-streamlit-auth.sh

# Run script with desired username and password
./scripts/setup-streamlit-auth.sh admin "YourSecurePassword123!"
```

**Script Output:**
```
Creating htpasswd file...
Password:
Re-type password:
Adding password for user admin

Creating Kubernetes secret...
secret/streamlit-basic-auth created

✅ Authentication configured successfully!

Next steps:
1. Deploy Streamlit admin manifests
2. Access UI at http://admin.ai-agents.local (after Ingress is applied)
3. Login with username: admin
```

**Manual Setup (Alternative):**

```bash
# 1. Install htpasswd (if not available)
# macOS: brew install apache2-utils
# Ubuntu: sudo apt install apache2-utils

# 2. Generate htpasswd file
htpasswd -c /tmp/auth admin
# Prompts for password (enter your secure password)

# 3. Create Kubernetes Secret
kubectl create secret generic streamlit-basic-auth \
  --from-file=auth=/tmp/auth \
  --namespace=ai-agents

# 4. Cleanup
rm /tmp/auth
```

**Verify Secret Created:**

```bash
# Check secret exists
kubectl get secret streamlit-basic-auth -n ai-agents

# View secret structure (not decrypted values)
kubectl get secret streamlit-basic-auth -n ai-agents -o yaml
```

Expected output:
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: streamlit-basic-auth
  namespace: ai-agents
type: Opaque
data:
  auth: YWRtaW46JGFwcjEkLi4uLi4=  # Base64-encoded htpasswd content
```

### Deploy Manifests

**CRITICAL: Apply in This Order**

Manifests must be applied in specific order due to dependencies:

**1. RBAC (ServiceAccount, Role, RoleBinding) - MUST BE FIRST**

```bash
kubectl apply -f k8s/streamlit-rbac.yaml
```

**Why First:** Worker Monitoring page requires ServiceAccount `streamlit-admin` to exist before deployment references it.

**Verify RBAC:**
```bash
# Check ServiceAccount
kubectl get serviceaccount streamlit-admin -n ai-agents

# Check Role
kubectl get role streamlit-admin-role -n ai-agents

# Check RoleBinding
kubectl get rolebinding streamlit-admin-rolebinding -n ai-agents
```

**2. ConfigMap (Streamlit Configuration)**

```bash
kubectl apply -f k8s/streamlit-admin-configmap.yaml
```

**Contents:** Streamlit `config.toml` settings (server port, headless mode, theme colors)

**Verify ConfigMap:**
```bash
kubectl get configmap streamlit-config -n ai-agents

# View contents
kubectl get configmap streamlit-config -n ai-agents -o yaml
```

**3. Deployment (Streamlit Application Pods)**

```bash
kubectl apply -f k8s/streamlit-admin-deployment.yaml
```

**Key Fields:**
- `spec.replicas: 1` (single replica for admin workload)
- `spec.template.spec.serviceAccountName: streamlit-admin` (references RBAC from step 1)
- `spec.template.spec.containers[0].env` (includes `AI_AGENTS_DATABASE_URL` from secret)
- `spec.template.spec.containers[0].resources` (requests: 256Mi/100m, limits: 512Mi/500m)

**Verify Deployment:**
```bash
# Check deployment created
kubectl get deployment streamlit-admin -n ai-agents

# Check pod is running
kubectl get pods -n ai-agents -l app=streamlit-admin

# Check pod logs
kubectl logs -n ai-agents -l app=streamlit-admin -f
```

Expected log output:
```
  You can now view your Streamlit app in your browser.

  URL: http://0.0.0.0:8501
```

**4. Service (LoadBalancer for Pod Access)**

```bash
kubectl apply -f k8s/streamlit-admin-service.yaml
```

**Service Type:** LoadBalancer (exposes port 80, routes to targetPort 8501)

**Verify Service:**
```bash
kubectl get svc streamlit-admin -n ai-agents

# Expected output:
# NAME              TYPE           CLUSTER-IP      EXTERNAL-IP   PORT(S)        AGE
# streamlit-admin   LoadBalancer   10.96.123.45    <pending>     80:30123/TCP   1m
```

**Note:** `EXTERNAL-IP` may show `<pending>` on local clusters. This is expected for Minikube/Kind (use Ingress instead).

**5. Ingress (NGINX Routing with Authentication)**

```bash
kubectl apply -f k8s/streamlit-admin-ingress.yaml
```

**Key Annotations:**
- `nginx.ingress.kubernetes.io/auth-type: basic`
- `nginx.ingress.kubernetes.io/auth-secret: streamlit-basic-auth`
- `nginx.ingress.kubernetes.io/proxy-read-timeout: "3600"` (WebSocket support)
- `nginx.ingress.kubernetes.io/proxy-send-timeout: "3600"` (WebSocket support)
- `nginx.ingress.kubernetes.io/websocket-services: streamlit-admin` (WebSocket support)

**TLS Configuration (Optional, Commented by Default):**
```yaml
# Uncomment for production with cert-manager
# tls:
# - hosts:
#   - admin.ai-agents.local
#   secretName: streamlit-admin-tls
```

**Verify Ingress:**
```bash
kubectl get ingress streamlit-admin -n ai-agents

# Expected output:
# NAME              CLASS   HOSTS                      ADDRESS        PORTS   AGE
# streamlit-admin   nginx   admin.ai-agents.local      192.168.49.2   80      1m
```

### Verify Deployment

**Full Verification Checklist:**

```bash
# 1. Check all pods are running
kubectl get pods -n ai-agents
# Expected: streamlit-admin-xxx pod in Running status (1/1 ready)

# 2. Check pod logs for errors
kubectl logs -n ai-agents -l app=streamlit-admin --tail=50
# Should show: "You can now view your Streamlit app in your browser."

# 3. Check service endpoints
kubectl get endpoints streamlit-admin -n ai-agents
# Should show pod IP and port 8501

# 4. Check ingress configuration
kubectl describe ingress streamlit-admin -n ai-agents
# Verify annotations present: auth-type, auth-secret, proxy timeouts

# 5. Test service directly (port-forward)
kubectl port-forward -n ai-agents svc/streamlit-admin 8501:80
# Open browser: http://localhost:8501
# Should show Streamlit login page
# Ctrl+C to stop port-forward

# 6. Test database connectivity from pod
kubectl exec -n ai-agents deployment/streamlit-admin -- \
  env | grep DATABASE_URL
# Should output: AI_AGENTS_DATABASE_URL=postgresql://...

# 7. Test RBAC permissions
kubectl auth can-i get pods \
  --as=system:serviceaccount:ai-agents:streamlit-admin \
  -n ai-agents
# Expected output: yes
```

### Configure Local Access

**Add Hostname to /etc/hosts:**

```bash
# For local clusters (Minikube, Kind, Docker Desktop)
echo "127.0.0.1  admin.ai-agents.local" | sudo tee -a /etc/hosts

# For Minikube specifically
echo "$(minikube ip)  admin.ai-agents.local" | sudo tee -a /etc/hosts

# For cloud clusters with LoadBalancer
# Replace <EXTERNAL-IP> with actual Ingress address
echo "<EXTERNAL-IP>  admin.ai-agents.local" | sudo tee -a /etc/hosts
```

**Verify Hostname Resolution:**

```bash
# Test DNS resolution
nslookup admin.ai-agents.local
# Should resolve to 127.0.0.1 or cluster IP

# Test HTTP access
curl -v http://admin.ai-agents.local
# Expected: HTTP 401 Unauthorized (authentication required)

# Test with credentials
curl -u admin:YourPassword http://admin.ai-agents.local
# Expected: HTTP 200 OK with HTML content
```

**Access UI in Browser:**

1. Open browser (Chrome, Firefox, Safari)
2. Navigate to: http://admin.ai-agents.local
3. Basic authentication prompt appears
4. Enter credentials:
   - Username: `admin`
   - Password: (password you set in setup-streamlit-auth.sh)
5. Dashboard page loads

**Troubleshooting Access Issues:**

| Symptom | Diagnosis | Solution |
|---------|-----------|----------|
| "Site can't be reached" | DNS resolution failed | Verify /etc/hosts entry |
| No auth prompt | Ingress not configured | Check Ingress annotations |
| 401 Unauthorized | Wrong credentials | Verify secret: `kubectl get secret streamlit-basic-auth -n ai-agents` |
| 502 Bad Gateway | Pod not running | Check pod status: `kubectl get pods -n ai-agents` |
| 503 Service Unavailable | Service not routing | Check service endpoints: `kubectl get endpoints -n ai-agents` |

---

## Configuration Reference

Comprehensive reference for all configuration options.

### Environment Variables

| Variable | Default | Description | Required | Used By |
|----------|---------|-------------|----------|---------|
| `AI_AGENTS_DATABASE_URL` | (none) | PostgreSQL connection string (format: `postgresql://user:pass@host:port/db`) | **Yes** | All pages |
| `KUBERNETES_NAMESPACE` | `ai-agents` | K8s namespace for worker operations | No | Worker Monitoring |
| `KUBERNETES_IN_CLUSTER` | `true` | Use in-cluster K8s config (vs local kubeconfig) | No | Worker Monitoring |
| `WORKER_LOG_LINES` | `100` | Default number of log lines to fetch | No | Worker Monitoring |
| `CELERY_APP_NAME` | `src.workers.celery_app` | Celery application import path | No | Worker Monitoring |
| `FERNET_KEY` | (generated) | Encryption key for tenant secrets (32-byte URL-safe base64) | **Yes** (production) | Tenant Management |
| `PROMETHEUS_URL` | `http://prometheus:9090` | Prometheus server endpoint | No (degrades gracefully) | Real-Time Metrics |
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL) | No | All pages |

**Configuration in Kubernetes:**

Environment variables are set in deployment manifest via:

```yaml
# k8s/streamlit-admin-deployment.yaml
spec:
  template:
    spec:
      containers:
      - name: streamlit-admin
        env:
        - name: AI_AGENTS_DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: database-credentials
              key: url
        - name: KUBERNETES_NAMESPACE
          value: "ai-agents"
        - name: FERNET_KEY
          valueFrom:
            secretKeyRef:
              name: encryption-key
              key: fernet_key
```

**Generating Fernet Key:**

```bash
# Generate new Fernet key
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Create secret
kubectl create secret generic encryption-key \
  --from-literal=fernet_key='<generated-key-here>' \
  --namespace=ai-agents
```

### Streamlit Configuration

**File Location:**
- **Local:** `.streamlit/config.toml`
- **Kubernetes:** ConfigMap `streamlit-config` mounted at `/app/.streamlit/config.toml`

**Configuration Options:**

```toml
[server]
port = 8501                    # Default port (do not change for K8s)
headless = true                # Required for production (no browser auto-open)
enableXsrfProtection = true    # CSRF protection (security)
maxUploadSize = 200            # Max file upload size in MB

[browser]
gatherUsageStats = false       # Disable telemetry (privacy)
serverAddress = "0.0.0.0"      # Listen on all interfaces (K8s requirement)

[theme]
primaryColor = "#0066CC"       # Brand blue color
backgroundColor = "#FFFFFF"    # White background
secondaryBackgroundColor = "#F0F2F6"  # Light gray
textColor = "#262730"          # Dark gray text
font = "sans serif"            # Font family

[logger]
level = "info"                 # Streamlit internal logging (debug, info, warning, error)
messageFormat = "%(asctime)s %(message)s"

[client]
showErrorDetails = false       # Hide error stack traces (production)
toolbarMode = "minimal"        # Minimal toolbar (cleaner UI)
```

**Updating Configuration (Kubernetes):**

1. Edit ConfigMap manifest: `k8s/streamlit-admin-configmap.yaml`
2. Apply changes: `kubectl apply -f k8s/streamlit-admin-configmap.yaml`
3. Restart pods to pick up new config: `kubectl rollout restart deployment/streamlit-admin -n ai-agents`

### Resource Limits

**Current Allocation:**

| Resource | Request | Limit | Rationale |
|----------|---------|-------|-----------|
| **Memory** | 256Mi | 512Mi | Streamlit baseline ~150Mi, buffer for pandas/plotly |
| **CPU** | 100m | 500m | Low CPU usage (mostly I/O), burst capacity for charts |

**Deployment Manifest Configuration:**

```yaml
# k8s/streamlit-admin-deployment.yaml
spec:
  template:
    spec:
      containers:
      - name: streamlit-admin
        resources:
          requests:
            memory: "256Mi"
            cpu: "100m"
          limits:
            memory: "512Mi"
            cpu: "500m"
```

**Adjusting Limits:**

**Increase Memory** (if experiencing OOMKilled):
```bash
# Edit deployment
kubectl edit deployment streamlit-admin -n ai-agents

# Change limits.memory from 512Mi to 1Gi
# Save and exit

# Pod will restart automatically with new limits
```

**Increase CPU** (if experiencing slow page loads):
```bash
# Edit deployment
kubectl edit deployment streamlit-admin -n ai-agents

# Change limits.cpu from 500m to 1000m (1 CPU core)
# Save and exit
```

**Monitoring Resource Usage:**

```bash
# Check current resource usage
kubectl top pod -n ai-agents -l app=streamlit-admin

# Example output:
# NAME                               CPU(cores)   MEMORY(bytes)
# streamlit-admin-6b7c8d9f5-abcde    45m          312Mi
```

### RBAC Permissions

**ServiceAccount:** `streamlit-admin`
**Namespace:** `ai-agents` (scoped to namespace only, not cluster-wide)

**Permissions (Role: `streamlit-admin-role`):**

| Resource | Verbs | Purpose |
|----------|-------|---------|
| `pods` | `get`, `list`, `watch` | Worker discovery and health checks |
| `pods` | `delete` | Restart individual workers (Worker Monitoring) |
| `pods/log` | `get`, `list` | Fetch worker logs (Worker Monitoring) |
| `deployments` | `get`, `list` | View deployment status |
| `deployments` | `patch` | Trigger rolling restart via annotation update |

**RBAC Manifest:**

```yaml
# k8s/streamlit-rbac.yaml
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: streamlit-admin
  namespace: ai-agents

---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: streamlit-admin-role
  namespace: ai-agents
rules:
- apiGroups: [""]
  resources: ["pods"]
  verbs: ["get", "list", "watch", "delete"]
- apiGroups: [""]
  resources: ["pods/log"]
  verbs: ["get", "list"]
- apiGroups: ["apps"]
  resources: ["deployments"]
  verbs: ["get", "list", "patch"]

---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: streamlit-admin-rolebinding
  namespace: ai-agents
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: streamlit-admin-role
subjects:
- kind: ServiceAccount
  name: streamlit-admin
  namespace: ai-agents
```

**Security Principle:** Least privilege - only permissions required for Worker Monitoring functionality, scoped to namespace only.

**Testing RBAC Permissions:**

```bash
# Test pod list permission
kubectl auth can-i list pods \
  --as=system:serviceaccount:ai-agents:streamlit-admin \
  -n ai-agents
# Expected: yes

# Test pod delete permission
kubectl auth can-i delete pods \
  --as=system:serviceaccount:ai-agents:streamlit-admin \
  -n ai-agents
# Expected: yes

# Test unauthorized action (should fail)
kubectl auth can-i delete namespace \
  --as=system:serviceaccount:ai-agents:streamlit-admin
# Expected: no
```

---

## Troubleshooting

Common issues and their solutions organized by symptom.

### Database Connection Failures

**Symptom:** Dashboard shows "❌ Database connection failed"

**Diagnostics:**

```bash
# 1. Verify environment variable is set
echo $AI_AGENTS_DATABASE_URL
# Should output connection string

# 2. Test PostgreSQL connectivity
psql $AI_AGENTS_DATABASE_URL -c "SELECT 1"
# Expected: 1

# 3. In Kubernetes, check secret exists
kubectl get secret database-credentials -n ai-agents

# 4. Verify pod has environment variable
kubectl exec -n ai-agents deployment/streamlit-admin -- env | grep DATABASE_URL
```

**Solutions:**

| Cause | Solution |
|-------|----------|
| **Environment variable not set** | Export variable: `export AI_AGENTS_DATABASE_URL="postgresql://..."` |
| **PostgreSQL not running** | Start service: `docker-compose up -d postgres` or `systemctl start postgresql` |
| **Wrong credentials** | Verify username/password in connection string |
| **Database doesn't exist** | Create database: `createdb ai_agents` |
| **Firewall blocking connection** | Check PostgreSQL allows connections from app IP (pg_hba.conf) |
| **Secret missing (K8s)** | Create secret: `kubectl create secret generic database-credentials --from-literal=url='...' -n ai-agents` |

**Verify Fix:**

Navigate to Dashboard page → Database Connection Status section should show:
- ✅ Connected to PostgreSQL
- Version information displayed
- Tenant count shown

---

### Authentication Issues

**Symptom (Local Dev):** Cannot login with `admin`/`admin`

**Solutions:**

1. **Check secrets.toml exists:**
   ```bash
   ls -la .streamlit/secrets.toml
   # If doesn't exist, app uses default credentials (admin/admin)
   ```

2. **Verify secrets.toml format:**
   ```bash
   cat .streamlit/secrets.toml
   # Should have [credentials.usernames.admin] section with password
   ```

3. **Try default credentials:** `admin` / `admin` (if secrets.toml doesn't exist)

4. **Restart Streamlit app** after changing secrets.toml:
   ```bash
   # Stop app (Ctrl+C)
   streamlit run src/admin/app.py
   ```

**Symptom (Kubernetes):** No basic auth prompt appears

**Diagnostics:**

```bash
# 1. Check Ingress secret exists
kubectl get secret streamlit-basic-auth -n ai-agents

# 2. Check Ingress has authentication annotations
kubectl describe ingress streamlit-admin -n ai-agents | grep -i auth
# Should show:
#   nginx.ingress.kubernetes.io/auth-type: basic
#   nginx.ingress.kubernetes.io/auth-secret: streamlit-basic-auth
```

**Solutions:**

| Cause | Solution |
|-------|----------|
| **Secret missing** | Run: `./scripts/setup-streamlit-auth.sh admin yourpassword` |
| **Ingress annotations missing** | Verify `k8s/streamlit-admin-ingress.yaml` has auth annotations, reapply manifest |
| **NGINX Ingress not installed** | Install: `kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.9.4/deploy/static/provider/cloud/deploy.yaml` |
| **Wrong secret reference** | Ingress annotation must reference `streamlit-basic-auth` (check spelling) |

**Symptom:** 401 Unauthorized after entering credentials

**Solutions:**

1. **Verify credentials are correct:** Username and password must match what was set in `setup-streamlit-auth.sh`

2. **Recreate secret with new password:**
   ```bash
   # Delete old secret
   kubectl delete secret streamlit-basic-auth -n ai-agents

   # Create new secret
   ./scripts/setup-streamlit-auth.sh admin NewPassword123!

   # Restart Ingress Controller to pick up changes
   kubectl rollout restart deployment ingress-nginx-controller -n ingress-nginx
   ```

---

### Worker Monitoring Not Loading

**Symptom:** Worker Monitoring page shows empty table or error: "Forbidden (403)"

**Root Cause:** Missing or incorrect RBAC permissions

**Diagnostics:**

```bash
# 1. Check ServiceAccount exists
kubectl get serviceaccount streamlit-admin -n ai-agents

# 2. Check Role exists
kubectl get role streamlit-admin-role -n ai-agents

# 3. Check RoleBinding exists
kubectl get rolebinding streamlit-admin-rolebinding -n ai-agents

# 4. Verify deployment uses ServiceAccount
kubectl get deployment streamlit-admin -n ai-agents -o yaml | grep serviceAccountName
# Should output: serviceAccountName: streamlit-admin

# 5. Test RBAC permissions
kubectl auth can-i list pods \
  --as=system:serviceaccount:ai-agents:streamlit-admin \
  -n ai-agents
# Expected: yes
```

**Solutions:**

1. **Apply RBAC manifest:**
   ```bash
   kubectl apply -f k8s/streamlit-rbac.yaml
   ```

2. **Verify deployment references ServiceAccount:**
   ```bash
   # Edit deployment if serviceAccountName is missing
   kubectl edit deployment streamlit-admin -n ai-agents

   # Add under spec.template.spec:
   #   serviceAccountName: streamlit-admin
   ```

3. **Restart pods to pick up new ServiceAccount:**
   ```bash
   kubectl rollout restart deployment/streamlit-admin -n ai-agents
   ```

4. **Check pod logs for permission errors:**
   ```bash
   kubectl logs -n ai-agents -l app=streamlit-admin | grep -i "forbidden\|unauthorized"
   ```

---

### Pod Crashes or Restarts

**Symptom:** Pod status shows `CrashLoopBackOff` or frequent restarts

**Diagnostics:**

```bash
# 1. Check pod status
kubectl get pods -n ai-agents -l app=streamlit-admin

# 2. Check pod events
kubectl describe pod -n ai-agents -l app=streamlit-admin

# 3. Check logs
kubectl logs -n ai-agents -l app=streamlit-admin --tail=100

# 4. Check previous container logs (if restarted)
kubectl logs -n ai-agents -l app=streamlit-admin --previous --tail=100
```

**Common Causes and Solutions:**

| Cause | Log Indicator | Solution |
|-------|---------------|----------|
| **OOMKilled (Out of Memory)** | Events show: "OOMKilled" | Increase memory limits in deployment: `resources.limits.memory: 1Gi` |
| **Import errors** | `ModuleNotFoundError: No module named 'X'` | Rebuild Docker image with missing dependency in pyproject.toml |
| **Database connection failed** | `sqlalchemy.exc.OperationalError` | Verify `AI_AGENTS_DATABASE_URL` secret exists and is correct |
| **Missing secrets** | `KeyError: 'FERNET_KEY'` | Create missing secret: `kubectl create secret generic encryption-key...` |
| **Port conflict** | `OSError: Address already in use` | Should not occur in K8s (each pod has own network) |
| **Python crash** | Traceback ending in `Segmentation fault` | Check resource limits, may need more memory |

**Solution Steps:**

1. **If OOMKilled, increase memory:**
   ```bash
   kubectl edit deployment streamlit-admin -n ai-agents
   # Change: limits.memory from 512Mi to 1Gi
   ```

2. **If import errors, rebuild image:**
   ```bash
   # Add missing package to pyproject.toml
   # Rebuild and redeploy
   docker build -f docker/streamlit.dockerfile -t ai-agents-streamlit:1.0.1 .
   kubectl set image deployment/streamlit-admin streamlit-admin=ai-agents-streamlit:1.0.1 -n ai-agents
   ```

3. **If database errors, check connection:**
   ```bash
   # Test from pod
   kubectl exec -n ai-agents deployment/streamlit-admin -- \
     python -c "from sqlalchemy import create_engine; import os; engine = create_engine(os.environ['AI_AGENTS_DATABASE_URL']); conn = engine.connect(); print('Connected'); conn.close()"
   ```

---

### WebSocket Connection Lost

**Symptom:** Frequent "Connection lost" messages in browser, page disconnects/reconnects repeatedly

**Cause:** WebSocket timeout too short for long-running operations or slow networks

**Diagnostics:**

```bash
# Check Ingress WebSocket timeout annotations
kubectl describe ingress streamlit-admin -n ai-agents | grep timeout
# Should show:
#   nginx.ingress.kubernetes.io/proxy-read-timeout: 3600
#   nginx.ingress.kubernetes.io/proxy-send-timeout: 3600
```

**Solutions:**

1. **Increase Ingress timeout annotations:**

Edit `k8s/streamlit-admin-ingress.yaml`:

```yaml
annotations:
  nginx.ingress.kubernetes.io/proxy-read-timeout: "7200"  # 2 hours
  nginx.ingress.kubernetes.io/proxy-send-timeout: "7200"
  nginx.ingress.kubernetes.io/websocket-services: streamlit-admin
```

Apply changes:
```bash
kubectl apply -f k8s/streamlit-admin-ingress.yaml
```

2. **Verify WebSocket service annotation:**

Ensure `websocket-services` annotation includes `streamlit-admin`:
```yaml
nginx.ingress.kubernetes.io/websocket-services: "streamlit-admin"
```

3. **Check NGINX Ingress Controller logs:**
```bash
kubectl logs -n ingress-nginx -l app.kubernetes.io/name=ingress-nginx | grep websocket
```

4. **Browser-side issues:**
- Try different browser (Chrome vs Firefox)
- Disable browser extensions (ad blockers may interfere with WebSockets)
- Check browser console for WebSocket errors (F12 → Console tab)

---

### Port Conflicts (Local)

**Symptom:** `OSError: [Errno 48] Address already in use` (port 8501)

**Diagnostics:**

```bash
# Find process using port 8501
lsof -i :8501
# Output shows:
# COMMAND   PID   USER   FD   TYPE DEVICE SIZE/OFF NODE NAME
# python    12345 user   3u   IPv4 ...     0t0      TCP *:8501 (LISTEN)
```

**Solutions:**

1. **Kill existing process:**
   ```bash
   # Get PID from lsof output above
   kill -9 12345

   # Or kill all Python processes on port 8501
   lsof -ti :8501 | xargs kill -9
   ```

2. **Use different port:**
   ```bash
   streamlit run src/admin/app.py --server.port=8502
   # Access at: http://localhost:8502
   ```

3. **Check for zombie processes:**
   ```bash
   # List all Streamlit processes
   ps aux | grep streamlit

   # Kill all Streamlit processes
   pkill -f streamlit
   ```

---

## Security Considerations

Comprehensive security guidance for production deployments.

### Authentication Methods

**Current Implementation (MVP):**

| Environment | Method | Encryption | Pros | Cons |
|-------------|--------|------------|------|------|
| **Local Dev** | Session-based with secrets.toml | Password in plaintext file (git-ignored) | Simple setup, fast iteration | Not suitable for multi-user, plaintext storage |
| **Production** | NGINX Ingress basic auth | htpasswd bcrypt hashing | Industry standard, widely supported | Single shared credential, no user audit trail |

**Planned Upgrades (Post-MVP):**

**Phase 2: OAuth2-Proxy (Epic 7)**

- **Provider Support:** Azure AD, Google Workspace, GitHub Enterprise, Okta
- **Benefits:**
  - Single Sign-On (SSO) with enterprise identity providers
  - Individual user authentication (audit trail)
  - No password management (provider handles it)
  - Multi-factor authentication (MFA) support
- **Implementation:** OAuth2-Proxy sidecar container in admin pod

**Phase 3: RBAC (Epic 8)**

- **Roles:**
  - **Admin:** Full access (all pages, all operations)
  - **Operator:** Limited access (view metrics, restart workers, no tenant management)
  - **Viewer:** Read-only access (dashboards, history, metrics only)
- **Benefits:**
  - Granular permission control
  - Principle of least privilege
  - Reduced security risk from compromised accounts

### Secrets Management

**Local Development:**

| Secret Type | Storage | Protection | Rotation |
|-------------|---------|------------|----------|
| `.streamlit/secrets.toml` | Local file | Git-ignored, file permissions (chmod 600) | Manual (every 180 days) |
| `.env` file | Local file | Git-ignored | Manual (every 180 days) |
| Database password | Environment variable or `.env` | Not encrypted (developer machine assumed secure) | Every 180 days |

**Kubernetes Production:**

| Secret Type | Storage | Protection | Rotation |
|-------------|---------|------------|----------|
| `streamlit-basic-auth` | Kubernetes Secret | Base64-encoded (K8s default), bcrypt hashed password | Every 90 days |
| `database-credentials` | Kubernetes Secret | Base64-encoded, in-transit encryption (etcd) | Every 90 days |
| `encryption-key` (Fernet) | Kubernetes Secret | Base64-encoded | Every 180 days (with key migration) |

**Best Practices:**

1. **Never commit secrets to git:**
   - `.streamlit/secrets.toml` ✅ Git-ignored
   - `.env` ✅ Git-ignored
   - `k8s/*.yaml` manifests ⚠️ Do not hardcode secrets in YAML (use kubectl create secret)

2. **Use strong secrets:**
   - **Passwords:** 20+ characters, mix of uppercase, lowercase, numbers, symbols
   - **Fernet Keys:** 32-byte URL-safe base64 (generated via `Fernet.generate_key()`)
   - **Database Passwords:** 16+ characters, random generation

3. **Rotate secrets regularly:**
   ```bash
   # Rotate basic auth password (quarterly)
   ./scripts/setup-streamlit-auth.sh admin NewPassword$(date +%s)

   # Rotate Fernet key (semi-annually, requires code change for migration)
   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   kubectl create secret generic encryption-key-new --from-literal=fernet_key='...' -n ai-agents
   ```

4. **Audit secret access:**
   ```bash
   # Check who has accessed secrets (K8s audit logs)
   kubectl get events -n ai-agents --field-selector involvedObject.kind=Secret
   ```

### Network Security

**Local Development:**

- **No TLS Required:** localhost traffic is inherently secure
- **Firewall:** Ensure port 8501 is not exposed to external networks
- **VPN:** Use VPN if accessing development environment remotely

**Kubernetes Production:**

| Layer | Configuration | Purpose |
|-------|---------------|---------|
| **Ingress** | NGINX Ingress Controller | Entry point for external traffic |
| **TLS/HTTPS** | cert-manager + Let's Encrypt (commented in manifest) | Encrypt traffic in transit |
| **Network Policies** | Kubernetes NetworkPolicy (optional) | Restrict pod-to-pod traffic |
| **IP Whitelisting** | Ingress annotation: `nginx.ingress.kubernetes.io/whitelist-source-range` | Limit access to corporate networks |

**Enable TLS (Production Recommended):**

1. **Install cert-manager:**
   ```bash
   kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml
   ```

2. **Uncomment TLS section in Ingress manifest:**

Edit `k8s/streamlit-admin-ingress.yaml`:

```yaml
spec:
  tls:
  - hosts:
    - admin.ai-agents.local
    secretName: streamlit-admin-tls
  rules:
  - host: admin.ai-agents.local
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: streamlit-admin
            port:
              number: 80
```

3. **Create Certificate resource:**

```yaml
# k8s/streamlit-admin-certificate.yaml
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: streamlit-admin-tls
  namespace: ai-agents
spec:
  secretName: streamlit-admin-tls
  issuerRef:
    name: letsencrypt-prod
    kind: ClusterIssuer
  dnsNames:
  - admin.ai-agents.local
```

Apply: `kubectl apply -f k8s/streamlit-admin-certificate.yaml`

**IP Whitelisting (Corporate Networks Only):**

Add annotation to `k8s/streamlit-admin-ingress.yaml`:

```yaml
annotations:
  nginx.ingress.kubernetes.io/whitelist-source-range: "10.0.0.0/8,192.168.1.0/24"
  # Replace with your corporate IP ranges
```

### Database Access

**Connection Security:**

- **Encryption:** Use `sslmode=require` in connection string for production:
  ```
  postgresql://user:pass@host:5432/db?sslmode=require
  ```
- **Connection Pooling:** SQLAlchemy pools connections (default: 5 max, configurable)
- **Credentials:** Stored in Kubernetes Secret `database-credentials`, mounted as environment variable

**Row-Level Security (RLS):**

- **Epic 3 Implementation:** Tenant isolation enforced at database level
- **Admin UI Impact:** Admin UI has full read-write access to all tenants (necessary for management)
- **Future Enhancement:** RLS policies could restrict viewer role to specific tenants

**Database Permissions:**

Admin UI requires:
- **SELECT:** All tables (tenant_config, enhancement_history, etc.)
- **INSERT/UPDATE/DELETE:** tenant_config (Tenant Management page)
- **SELECT:** enhancement_history (Enhancement History page)

**Recommended Database User Setup:**

```sql
-- Create dedicated user for admin UI
CREATE USER streamlit_admin WITH PASSWORD 'secure-password';

-- Grant necessary permissions
GRANT SELECT, INSERT, UPDATE, DELETE ON tenant_config TO streamlit_admin;
GRANT SELECT ON enhancement_history TO streamlit_admin;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO streamlit_admin;

-- Test connection
-- postgresql://streamlit_admin:secure-password@postgres:5432/ai_agents
```

### Audit Logging

**What to Log:**

| Event | Log Location | Details Captured |
|-------|--------------|------------------|
| **Login Attempts** | NGINX Ingress access logs | Username, IP, timestamp, success/failure |
| **Page Access** | Streamlit app logs (loguru) | User, page, timestamp |
| **Tenant Changes** | Application logs | User, operation (create/update/delete), tenant name, changes |
| **System Operations** | Application logs | User, operation (pause/resume/restart), timestamp, outcome |
| **RBAC Actions** | Kubernetes audit logs | ServiceAccount, operation (get/delete pods), timestamp |

**Access NGINX Ingress Logs:**

```bash
# View access logs (includes auth attempts)
kubectl logs -n ingress-nginx -l app.kubernetes.io/name=ingress-nginx | grep admin.ai-agents.local

# Failed auth attempts
kubectl logs -n ingress-nginx -l app.kubernetes.io/name=ingress-nginx | grep "401\|403"
```

**Access Streamlit Application Logs:**

```bash
# View app logs
kubectl logs -n ai-agents -l app=streamlit-admin

# Filter for tenant operations
kubectl logs -n ai-agents -l app=streamlit-admin | grep -i tenant

# Filter for errors
kubectl logs -n ai-agents -l app=streamlit-admin | grep -i error
```

**Enable Kubernetes Audit Logging (Cluster-Level):**

Requires cluster admin privileges. Add to kube-apiserver configuration:

```yaml
# /etc/kubernetes/audit-policy.yaml
apiVersion: audit.k8s.io/v1
kind: Policy
rules:
- level: RequestResponse
  users: ["system:serviceaccount:ai-agents:streamlit-admin"]
  verbs: ["delete", "patch"]
  resources:
  - group: ""
    resources: ["pods"]
  - group: "apps"
    resources: ["deployments"]
```

**Centralized Logging (Recommended for Production):**

- **Stack:** ELK (Elasticsearch, Logstash, Kibana) or EFK (Fluentd instead of Logstash)
- **Benefits:**
  - Searchable logs across all components
  - Long-term retention (30+ days)
  - Alerting on suspicious patterns
- **Implementation:** Deploy Fluentd DaemonSet to collect logs, ship to Elasticsearch

### Production Hardening Checklist

Complete checklist before production deployment:

```markdown
## Authentication & Authorization
- [ ] Strong basic auth password set (20+ characters)
- [ ] Default credentials (`admin`/`admin`) changed
- [ ] Authentication secret stored in Kubernetes Secret (not hardcoded)
- [ ] OAuth2-Proxy planned for Phase 2 (if enterprise SSO required)

## Network Security
- [ ] TLS/HTTPS enabled (cert-manager + Let's Encrypt configured)
- [ ] IP whitelisting configured (corporate networks only)
- [ ] Network policies applied (if required by security team)
- [ ] Ingress WebSocket timeouts configured (3600+ seconds)
- [ ] Firewall rules allow only necessary ports (443 for HTTPS)

## Secrets Management
- [ ] All secrets stored in Kubernetes Secrets (no hardcoded values)
- [ ] Fernet encryption key generated and stored
- [ ] Database credentials rotated (not default dev passwords)
- [ ] Secret rotation schedule documented (90 days for production)
- [ ] Secrets have proper RBAC permissions (only admin UI pod can access)

## Database Security
- [ ] Database connection uses SSL (`sslmode=require`)
- [ ] Database user has minimal necessary permissions
- [ ] Row-Level Security (RLS) policies applied (Epic 3)
- [ ] Database credentials different from dev environment

## Monitoring & Logging
- [ ] Audit logging enabled (NGINX + Streamlit app logs)
- [ ] Centralized logging configured (ELK/EFK stack)
- [ ] Log retention policy defined (30+ days)
- [ ] Alerting configured for failed auth attempts (>5 in 1 hour)
- [ ] Prometheus scraping metrics from admin UI (if available)

## Resource Management
- [ ] Resource requests/limits appropriate for workload
- [ ] Memory limits prevent OOMKilled (512Mi minimum, 1Gi recommended)
- [ ] CPU limits allow responsive UI (<500ms page load)
- [ ] Pod anti-affinity configured (if multi-replica)

## RBAC & Permissions
- [ ] ServiceAccount `streamlit-admin` created
- [ ] Role has least-privilege permissions (only necessary verbs)
- [ ] RoleBinding applied correctly
- [ ] RBAC permissions tested (kubectl auth can-i commands)

## Backup & Disaster Recovery
- [ ] Database backup schedule configured
- [ ] Kubernetes manifests stored in version control (git)
- [ ] Secrets documented in password manager (not in git)
- [ ] Disaster recovery plan documented

## Compliance
- [ ] Security scan performed on Docker image (trivy/snyk)
- [ ] Vulnerability scan passed (no HIGH/CRITICAL vulnerabilities)
- [ ] Access control policy documented
- [ ] Data retention policy defined (enhancement history)
```

---

## Future Enhancements

Planned improvements for post-MVP releases.

### Phase 2: OAuth2-Proxy Integration (Epic 7)

**Target Release:** MVP v2.0 (Q3 2026)

**Objective:** Replace NGINX basic authentication with enterprise SSO

**Supported Identity Providers:**
- Azure AD (Active Directory)
- Google Workspace
- GitHub Enterprise
- Okta
- Generic OIDC providers

**Implementation Approach:**

1. **Deploy OAuth2-Proxy as sidecar container:**

```yaml
# k8s/streamlit-admin-deployment.yaml (updated)
spec:
  template:
    spec:
      containers:
      - name: streamlit-admin
        # ... existing config
      - name: oauth2-proxy
        image: quay.io/oauth2-proxy/oauth2-proxy:v7.4.0
        args:
        - --provider=azure
        - --client-id=$(AZURE_CLIENT_ID)
        - --client-secret=$(AZURE_CLIENT_SECRET)
        - --cookie-secret=$(COOKIE_SECRET)
        - --upstream=http://localhost:8501
        - --http-address=0.0.0.0:4180
        - --email-domain=example.com
        ports:
        - containerPort: 4180
```

2. **Update Ingress to route through OAuth2-Proxy:**

```yaml
# k8s/streamlit-admin-ingress.yaml (updated)
spec:
  rules:
  - host: admin.ai-agents.local
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: streamlit-admin
            port:
              number: 4180  # OAuth2-Proxy port (not 80)
```

3. **Register application in Azure AD (example):**
   - Create App Registration in Azure Portal
   - Configure redirect URI: `https://admin.ai-agents.local/oauth2/callback`
   - Generate client secret
   - Store client ID and secret in Kubernetes Secret

**Benefits:**
- Individual user authentication (audit trail)
- No password management (Azure AD handles it)
- Multi-factor authentication (MFA) enforced by provider
- Single Sign-On (SSO) with other corporate applications

**Estimated Effort:** 2-3 days (configuration + testing)

---

### Phase 3: Role-Based Access Control (Epic 8)

**Target Release:** MVP v2.5 (Q4 2026)

**Objective:** Implement granular permissions based on user roles

**Proposed Roles:**

| Role | Permissions | Use Case |
|------|-------------|----------|
| **Admin** | Full access to all pages and operations | DevOps leads, platform administrators |
| **Operator** | View metrics, restart workers, view history (no tenant management) | On-call engineers, support team |
| **Viewer** | Read-only access to dashboards, metrics, history | Stakeholders, managers, auditors |

**Implementation Approach:**

1. **Add role claim to OAuth2-Proxy:**
   - Extract role from Azure AD group membership
   - Pass role to Streamlit app via HTTP header (`X-Auth-Role`)

2. **Implement role-based page visibility in Streamlit app:**

```python
# src/admin/app.py (updated)
user_role = st.session_state.get("role", "viewer")

pages = {
    "Dashboard": [st.Page("pages/1_Dashboard.py", icon="📊")],
    "Metrics": [st.Page("pages/6_Metrics.py", icon="📈")],
}

# Admin-only pages
if user_role in ["admin"]:
    pages["Management"] = [
        st.Page("pages/2_Tenants.py", title="Tenant Management", icon="🏢"),
        st.Page("pages/4_Operations.py", title="System Operations", icon="⚙️"),
    ]

# Operator pages (no tenant management)
if user_role in ["admin", "operator"]:
    pages["Workers"] = [st.Page("pages/5_Workers.py", icon="👷")]
```

3. **Add role-based operation authorization:**

```python
# src/admin/pages/4_Operations.py (updated)
if st.button("Restart Workers"):
    if user_role not in ["admin", "operator"]:
        st.error("⛔ Insufficient permissions. Admin or Operator role required.")
    else:
        # Perform restart
        restart_workers()
        st.success("✅ Workers restarted successfully")
```

**Benefits:**
- Reduced security risk (principle of least privilege)
- Compliance with access control policies
- Clearer separation of duties

**Estimated Effort:** 5-7 days (implementation + testing)

---

### Phase 4: Audit Logs UI Page (Epic 9)

**Target Release:** MVP v3.0 (Q1 2027)

**Objective:** Display admin operation history within the UI

**Features:**

1. **Audit Log Table:**
   - Columns: Timestamp, User, Action, Resource, Outcome, IP Address
   - Filters: User, action type (login, tenant_create, worker_restart, etc.), date range
   - Pagination: 50 records per page
   - CSV Export

2. **Action Types:**
   - **Authentication:** Login success/failure
   - **Tenant Management:** Create, update, delete tenant
   - **System Operations:** Pause/resume processing, clear queues, restart workers
   - **Worker Operations:** Restart individual worker, fetch logs

3. **Data Source:**
   - New database table: `audit_log` (created in Epic 9 migration)
   - Columns: id, timestamp, user, action, resource_type, resource_id, ip_address, user_agent, outcome (success/failure), error_message

4. **Implementation:**
   - New page: `src/admin/pages/7_Audit.py`
   - Helper module: `src/admin/utils/audit_helper.py`
   - Log writes: Integrate into existing pages (decorators or middleware)

**Benefits:**
- Compliance with audit requirements (SOC 2, ISO 27001)
- Troubleshooting aid (who did what when)
- Security incident response (identify malicious actions)

**Estimated Effort:** 3-5 days (database schema + UI + integration)

---

### Phase 5: TLS Certificate Automation (Infrastructure)

**Target Release:** Ongoing (infrastructure improvement)

**Objective:** Automate TLS certificate issuance and renewal

**Implementation:**

1. **Install cert-manager in cluster:**
   ```bash
   kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml
   ```

2. **Create ClusterIssuer for Let's Encrypt:**

```yaml
# k8s/cert-manager-issuer.yaml
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: devops@example.com
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
    - http01:
        ingress:
          class: nginx
```

3. **Update Ingress to request certificate:**

```yaml
# k8s/streamlit-admin-ingress.yaml (updated)
metadata:
  annotations:
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
spec:
  tls:
  - hosts:
    - admin.ai-agents.example.com  # Use real domain
    secretName: streamlit-admin-tls
```

**Benefits:**
- Automatic certificate renewal (no manual intervention)
- Free certificates (Let's Encrypt)
- HTTPS enforcement

**Estimated Effort:** 1 day (infrastructure configuration)

---

### Phase 6: Custom Alerting from UI (Epic 10)

**Target Release:** MVP v3.5 (Q2 2027)

**Objective:** Configure Prometheus alerting rules via UI (no YAML editing)

**Features:**

1. **Alerting Rules Page:**
   - List existing Prometheus alerting rules
   - Create new alert: Select metric, threshold, duration, severity
   - Edit existing alert
   - Enable/disable alert (without deleting)

2. **Alert Configuration:**
   - Metric selection: Dropdown of available metrics (queue_depth, success_rate, latency, CPU, memory)
   - Condition: >, <, >=, <=, ==
   - Threshold: Numeric value
   - Duration: How long condition must be true (1m, 5m, 15m)
   - Severity: Critical, Warning, Info
   - Notification channels: Email, Slack, PagerDuty (configured via Alertmanager)

3. **Implementation:**
   - New page: `src/admin/pages/8_Alerts.py`
   - Backend: Generate Prometheus rule YAML dynamically, apply via Prometheus API
   - Helper module: `src/admin/utils/alerting_helper.py`

**Benefits:**
- No kubectl or YAML knowledge required
- Faster alert creation (ops team can self-serve)
- Visual alert management

**Estimated Effort:** 7-10 days (Prometheus API integration + UI + testing)

---

### Phase 7: Advanced Metrics Dashboards (Epic 11)

**Target Release:** MVP v4.0 (Q3 2027)

**Objective:** Customizable dashboard layouts with drag-and-drop

**Features:**

1. **Dashboard Customization:**
   - Drag-and-drop chart placement
   - Resize charts
   - Add/remove charts from library
   - Save dashboard presets (per user)

2. **Additional Chart Types:**
   - **Heatmaps:** Show latency distribution over time (P50/P75/P90/P95/P99)
   - **Histograms:** Task duration distribution
   - **Gauges:** Current queue depth, CPU usage (visual gauges)
   - **Tables:** Top 10 slowest tickets, most common errors

3. **Implementation:**
   - Library: Plotly Dash (more flexible than Streamlit for custom layouts)
   - Backend: Store dashboard configs in database (per user)
   - Migration: Refactor Real-Time Metrics page to new dashboard framework

**Benefits:**
- Tailored views for different teams (ops vs management)
- Better insights with advanced visualizations
- User preference persistence

**Estimated Effort:** 10-15 days (Plotly Dash integration + customization UI)

---

### Phase 8: Multi-Cluster Support (Epic 12)

**Target Release:** MVP v5.0 (Q4 2027)

**Objective:** Manage multiple Kubernetes clusters from single admin UI

**Features:**

1. **Cluster Switcher:**
   - Dropdown in header: Select cluster (Cluster A, Cluster B, etc.)
   - Worker Monitoring page operates on selected cluster
   - Metrics page shows per-cluster or aggregated view

2. **Cluster Configuration:**
   - Store cluster kubeconfigs in Kubernetes Secrets
   - Admin page to add/remove clusters
   - Test cluster connectivity

3. **Aggregated Views:**
   - Dashboard shows metrics across all clusters
   - Alert if any cluster has issues
   - Drill-down into specific cluster for details

**Implementation:**
- Kubernetes Python client: Support multiple kubeconfig contexts
- Database: Store cluster metadata (name, endpoint, kubeconfig secret name)
- UI: Add cluster selector component to navigation

**Benefits:**
- Centralized management for multi-region deployments
- Cost savings (one admin UI instead of N)
- Consistent operations across clusters

**Estimated Effort:** 15-20 days (multi-cluster architecture + testing)

---

## Quick Reference

Fast-access tables for common commands and configurations.

### Common Commands

| Task | Command | Notes |
|------|---------|-------|
| **Run locally** | `streamlit run src/admin/app.py` | From project root, venv activated |
| **Run on custom port** | `streamlit run src/admin/app.py --server.port=8502` | If port 8501 is in use |
| **Build Docker image** | `docker build -f docker/streamlit.dockerfile -t ai-agents-streamlit:1.0.0 .` | From project root |
| **Setup K8s auth** | `./scripts/setup-streamlit-auth.sh admin yourpassword` | Creates htpasswd secret |
| **Apply RBAC** | `kubectl apply -f k8s/streamlit-rbac.yaml` | **MUST be first** manifest |
| **Deploy to K8s** | `kubectl apply -f k8s/streamlit-admin-*.yaml` | Apply all manifests (after RBAC) |
| **Check pod status** | `kubectl get pods -n ai-agents -l app=streamlit-admin` | Verify pod is running |
| **View pod logs** | `kubectl logs -n ai-agents -l app=streamlit-admin -f` | Follow logs in real-time |
| **Port-forward for testing** | `kubectl port-forward -n ai-agents svc/streamlit-admin 8501:80` | Access at localhost:8501 |
| **Restart deployment** | `kubectl rollout restart deployment/streamlit-admin -n ai-agents` | Apply config changes |
| **Scale replicas** | `kubectl scale deployment streamlit-admin --replicas=2 -n ai-agents` | Horizontal scaling |

### Useful URLs

| Environment | URL | Authentication |
|-------------|-----|----------------|
| **Local Dev** | http://localhost:8501 | `admin` / `admin` (default) |
| **Local Dev (custom port)** | http://localhost:8502 | `admin` / `admin` |
| **Kubernetes (Ingress)** | http://admin.ai-agents.local | NGINX basic auth (htpasswd) |
| **Kubernetes (TLS)** | https://admin.ai-agents.local | NGINX basic auth + TLS |
| **Prometheus (if available)** | http://prometheus:9090 | N/A (cluster-internal) |
| **Grafana (if available)** | http://grafana:3000 | Admin credentials (separate) |

**Note:** For Kubernetes URLs to work locally, add hostname to `/etc/hosts`:
```bash
echo "127.0.0.1  admin.ai-agents.local" | sudo tee -a /etc/hosts
```

### Troubleshooting Quick Checks

| Symptom | Quick Diagnostic Command | Expected Output |
|---------|--------------------------|-----------------|
| **Database connection failed** | `echo $AI_AGENTS_DATABASE_URL` | Connection string displayed |
| **Auth not working (K8s)** | `kubectl get secret streamlit-basic-auth -n ai-agents` | Secret exists (not "NotFound") |
| **Pod not starting** | `kubectl describe pod -n ai-agents -l app=streamlit-admin` | Events show no "ImagePullBackOff" or "CrashLoopBackOff" |
| **Worker monitoring empty** | `kubectl get serviceaccount streamlit-admin -n ai-agents` | ServiceAccount exists |
| **Port conflict (local)** | `lsof -i :8501` | Shows process using port (kill it) |
| **Ingress not routing** | `kubectl get ingress streamlit-admin -n ai-agents` | ADDRESS column shows IP |
| **Slow page loads** | `kubectl top pod -n ai-agents -l app=streamlit-admin` | Memory < 400Mi, CPU < 300m |

### Configuration Files

| File | Purpose | Location (Local) | Location (K8s) |
|------|---------|------------------|----------------|
| **secrets.toml** | Local dev authentication | `.streamlit/secrets.toml` | N/A |
| **config.toml** | Streamlit configuration | `.streamlit/config.toml` | ConfigMap `streamlit-config` |
| **.env** | Environment variables (local) | `.env` (project root) | N/A |
| **database credentials** | PostgreSQL connection | Environment variable | Secret `database-credentials` |
| **htpasswd** | Production auth credentials | N/A | Secret `streamlit-basic-auth` |
| **Fernet key** | Tenant secret encryption | Environment variable | Secret `encryption-key` |

---

## Screenshots

Visual documentation for each page of the Admin UI.

**Note:** Screenshots below use annotated wireframes per Story 6.8 MVP scope. Actual screenshots will be added in future documentation update after production deployment.

### Figure 1: Dashboard Page - System Status Overview

**[Wireframe Placeholder]**

**Description:** Dashboard landing page showing four metrics cards in top row (Database Status ✅, Active Tenants: 3, Queue Depth: 42, Success Rate: 97.2%). Below metrics cards is the Database Connection Details panel (left side) showing PostgreSQL 16.2 connection info. Center area shows empty space reserved for future system health chart. Navigation sidebar visible on left with all six pages listed (Dashboard active with blue highlight). Header shows "Admin UI - AI Agents Enhancement Platform" title and logout button (top right).

**Key UI Elements Annotated:**
- 🔵 Metrics cards with color-coded status (green = healthy)
- 🔵 Database connection details panel (version, connection string masked)
- 🔵 Refresh button (↻) in top-right of metrics section
- 🔵 Last updated timestamp below metrics
- 🔵 Navigation sidebar with page icons

---

### Figure 2: Tenant Management - List View

**[Wireframe Placeholder]**

**Description:** Tenant Management page showing table with three configured tenants (ClientA, ClientB, Demo). Table columns: Tenant Name, API URL, API Key (shows "●●●●●●●●" with 🔒 encryption indicator), Webhook Secret (masked), Active Status (✅ checkboxes), Actions (Edit and Delete buttons). "Add Tenant" button visible at top-left above table in blue/primary color. Filter bar above table with search box and "Active Only" checkbox.

**Key UI Elements Annotated:**
- 🔵 "Add Tenant" button (primary action)
- 🔵 Table with encrypted field indicators (🔒)
- 🔵 Active status toggles (✅/❌)
- 🔵 Action buttons per row (Edit/Delete)
- 🔵 Search and filter controls

---

### Figure 3: Tenant Management - Edit Form

**[Wireframe Placeholder]**

**Description:** Edit tenant modal dialog overlaying the tenant list. Modal shows form with fields: Tenant Name (read-only, "ClientA"), API URL (editable text input with HTTPS validation, "https://clienta.servicedeskplus.com/api/v3"), API Key (password field showing "●●●●●●●●" with "Update" button to change), Webhook Secret (password field, similar masking), Active Status (checkbox checked). Bottom of modal has three buttons: "Test Connection" (secondary), "Save" (primary blue), "Cancel" (secondary gray). Validation message below API URL: "✅ Valid HTTPS URL format".

**Key UI Elements Annotated:**
- 🔵 Modal overlay with semi-transparent background
- 🔵 Form fields with validation indicators
- 🔵 Password fields with update capability
- 🔵 "Test Connection" button for API verification
- 🔵 Primary/secondary button styling

---

### Figure 4: Enhancement History - Filter and Search

**[Wireframe Placeholder]**

**Description:** Enhancement History page showing filter bar at top with four filter controls: (1) Tenant dropdown (shows "ClientA" selected), (2) Status multi-select checkboxes (Success ✓, Error ✓, Pending ✓, Processing ✓), (3) Date range pickers (From: 2025-10-28, To: 2025-11-04), (4) Search text box (placeholder: "Search ticket ID, customer..."). Blue "Apply Filters" button right of search box. Results table below shows 10 records with columns: Ticket ID (clickable), Tenant, Status (color-coded), Created, Duration, Actions (▼ Expand icon). One record expanded showing detail panel with three tabs (JSON Data active, Text Enhancement, Error Details disabled). Pagination controls at bottom: "< Previous | Page 1 of 15 | Next >" with page size dropdown "25 per page". Top-right has "Export to CSV" button.

**Key UI Elements Annotated:**
- 🔵 Comprehensive filter bar with multiple controls
- 🔵 Color-coded status indicators (🟢🔴🟡🔵)
- 🔵 Expandable detail panel with tabbed interface
- 🔵 Pagination controls with page size selector
- 🔵 CSV export button

---

### Figure 5: Enhancement History - Detail Expander

**[Wireframe Placeholder]**

**Description:** Close-up view of expanded detail panel for single enhancement record (Ticket ID: REQ-12345). Panel shows three tabs at top: "JSON Data" (active with blue underline), "Text Enhancement", "Error Details" (grayed out/disabled for successful record). Active tab displays pretty-printed JSON with syntax highlighting (keys in blue, strings in green, numbers in orange). JSON shows webhook payload structure with fields: ticket_id, customer_name, description, priority. Collapse button (▲) in top-right of panel. Copy button next to JSON for clipboard copy.

**Key UI Elements Annotated:**
- 🔵 Three-tab structure for different data views
- 🔵 Syntax-highlighted JSON (color-coded)
- 🔵 Collapse button (▲) to hide details
- 🔵 Copy to clipboard button
- 🔵 Disabled tab styling (Error Details grayed out)

---

### Figure 6: System Operations - Control Panel

**[Wireframe Placeholder]**

**Description:** System Operations page organized into four sections: (1) Processing Controls section shows status indicator "🟢 PROCESSING" and two large buttons ("Pause Processing", "Resume Processing" disabled), (2) Queue Management section shows queue depth "42 jobs" and two buttons ("Clear Queues" with ⚠️ warning icon, "Inspect Queues"), (3) Configuration section shows "Sync Tenant Configs" button, (4) Worker Operations section shows "Restart Workers" button with ⚠️ warning icon. Bottom half of page shows Logs Viewer with log level dropdown (set to "ERROR"), log text area showing 10 lines of recent logs with timestamps, and "Download Logs" button. Refresh button (↻) and auto-refresh indicator "Last updated: 14:32:15 (next in 23s)".

**Key UI Elements Annotated:**
- 🔵 Status indicator with color coding (🟢 PROCESSING)
- 🔵 Button states (enabled/disabled based on context)
- 🔵 Warning icons (⚠️) for destructive operations
- 🔵 Logs viewer with filtering
- 🔵 Auto-refresh countdown timer

---

### Figure 7: Real-Time Metrics - Charts and Time Selector

**[Wireframe Placeholder]**

**Description:** Real-Time Metrics page showing three Plotly charts stacked vertically occupying most of screen: (1) Top chart titled "Queue Depth Over Time" shows blue line graph with Y-axis 0-100 jobs, X-axis showing last 24 hours with hourly marks. Horizontal dashed lines at Y=100 (yellow/warning) and Y=500 (red/critical). Current value: 42 jobs. (2) Middle chart titled "Success Rate" shows green area chart with Y-axis 0-100%, X-axis same 24-hour range. Green fill above 95% threshold line. Current value: 97.2%. (3) Bottom chart titled "Latency Percentiles" shows three line traces (P50 blue, P95 orange, P99 red) with Y-axis 0-5000ms, X-axis 24-hour range. Legend shows trace names with clickable toggles.

Above charts is time range selector with four buttons: "1h", "6h", "24h" (active with blue background), "7d". Top-right shows auto-refresh indicator "Last updated: 2025-11-04 14:32:15 (next in 45s)" with manual refresh button (↻). Plotly interactive controls visible on hover (zoom, pan, reset, download PNG).

**Key UI Elements Annotated:**
- 🔵 Time range selector buttons (active state highlighted)
- 🔵 Three distinct chart types (line, area, multi-trace)
- 🔵 Alert threshold lines (horizontal dashed)
- 🔵 Plotly interactive controls (hover menu)
- 🔵 Auto-refresh status with countdown
- 🔵 Legend with trace toggles

---

### Figure 8: Worker Monitoring - Health Table and Logs

**[Wireframe Placeholder]**

**Description:** Worker Monitoring page split into two main sections. Top section shows worker health table with 3 rows (worker-0, worker-1, worker-2) and 8 columns: Hostname, Status (🟢🟢🟢 all Active), Uptime (2h 15m, 1h 48m, 2h 10m), Active Tasks (2, 0, 1), CPU% (45% 🟢, 32% 🟢, 78% 🟡 with yellow background), Memory% (56% 🟢, 48% 🟢, 82% 🟡), Throughput (12.5, 11.8, 10.2 tasks/min), Actions (Restart and Logs buttons per row). Worker-2 row has yellow highlighting on CPU% and Memory% cells indicating warning thresholds.

Bottom section shows logs modal overlaying page (for worker-0). Modal titled "Worker Logs: worker-0" with log level dropdown (set to "ERROR" showing 3 results). Log text area shows 3 error lines with timestamps and red text. Modal has "Download Logs" button, "Refresh" button (↻), and "Close" button (X in top-right).

**Key UI Elements Annotated:**
- 🔵 Health table with color-coded cells
- 🔵 Status indicators (🟢🟡🔴)
- 🔵 Alert threshold highlighting (yellow backgrounds)
- 🔵 Action buttons per worker row
- 🔵 Logs modal with level filtering
- 🔵 Scrollable log text area

---

### Figure 9: Worker Monitoring - Performance Charts

**[Wireframe Placeholder]**

**Description:** Historical performance section of Worker Monitoring page showing tabbed interface with three tabs: "worker-0" (active with blue underline), "worker-1", "worker-2". Active tab displays line chart titled "7-Day Throughput (worker-0)" with Y-axis 0-20 tasks/min, X-axis showing last 7 days (Nov 1-7) with daily marks. Blue line trace shows throughput varying between 8-15 tasks/min with slight downward trend toward end. Horizontal dashed gray line at Y=11.5 labeled "7-day average". Hover tooltip displays at point (Nov 4 14:00, 13.2 tasks/min) showing exact timestamp and value. Plotly controls visible on hover.

**Key UI Elements Annotated:**
- 🔵 Tabbed interface for per-worker views
- 🔵 7-day historical line chart
- 🔵 Average baseline indicator (dashed line)
- 🔵 Hover tooltip with exact values
- 🔵 Date-based X-axis with daily resolution

---

## Related Documentation

Cross-references to complementary documentation.

### Story Files (Epic 6)

| Story | Title | Focus |
|-------|-------|-------|
| [6.1](stories/6-1-set-up-streamlit-application-foundation.md) | Streamlit Foundation | Multi-page setup, authentication, database connectivity |
| [6.2](stories/6-2-implement-system-status-dashboard-page.md) | System Status Dashboard | Real-time metrics cards, auto-refresh patterns |
| [6.3](stories/6-3-create-tenant-management-interface.md) | Tenant Management | CRUD operations, Fernet encryption, API integration |
| [6.4](stories/6-4-implement-enhancement-history-viewer.md) | Enhancement History | Filtering, pagination, detail viewer, CSV export |
| [6.5](stories/6-5-add-system-operations-controls.md) | System Operations | Pause/resume, queue management, worker restart |
| [6.6](stories/6-6-integrate-real-time-metrics-display.md) | Real-Time Metrics | Prometheus integration, Plotly charts, time ranges |
| [6.7](stories/6-7-add-worker-health-and-resource-monitoring.md) | Worker Monitoring | Celery inspect API, K8s RBAC, logs viewer, performance charts |
| [6.8](stories/6-8-create-admin-ui-documentation-and-deployment-guide.md) | This Guide | Comprehensive documentation and deployment procedures |

### Project Documentation

| Document | Purpose | Audience |
|----------|---------|----------|
| [README.md](../README.md) | Project overview, quick start | All stakeholders |
| [PRD.md](PRD.md) | Product requirements (FR026-FR033) | Product team, developers |
| [architecture.md](architecture.md) | Architecture decisions (ADR-009) | Architects, developers |
| [deployment.md](deployment.md) | General deployment guide | Operations team |
| [admin-ui-setup.md](admin-ui-setup.md) | Story 6.1 foundation guide (superseded by this guide) | Historical reference |
| [admin-ui-deployment-checklist.md](admin-ui-deployment-checklist.md) | Deployment validation checklist | Operations team |

### Kubernetes Manifests

| Manifest | Purpose | Apply Order |
|----------|---------|-------------|
| [k8s/streamlit-rbac.yaml](../k8s/streamlit-rbac.yaml) | ServiceAccount, Role, RoleBinding for Worker Monitoring | **1st (CRITICAL)** |
| [k8s/streamlit-admin-configmap.yaml](../k8s/streamlit-admin-configmap.yaml) | Streamlit config.toml settings | 2nd |
| [k8s/streamlit-admin-deployment.yaml](../k8s/streamlit-admin-deployment.yaml) | Deployment with pod spec, resources, service account | 3rd |
| [k8s/streamlit-admin-service.yaml](../k8s/streamlit-admin-service.yaml) | LoadBalancer service (port 80 → 8501) | 4th |
| [k8s/streamlit-admin-ingress.yaml](../k8s/streamlit-admin-ingress.yaml) | NGINX Ingress with basic auth annotations | 5th |

### External Resources

| Resource | Description | URL |
|----------|-------------|-----|
| **Streamlit Documentation** | Official Streamlit framework docs | https://docs.streamlit.io |
| **Streamlit Multi-Page Apps** | Multi-page navigation guide | https://docs.streamlit.io/develop/concepts/multipage-apps/overview |
| **Streamlit Kubernetes Tutorial** | Official K8s deployment guide | https://docs.streamlit.io/deploy/tutorials/kubernetes |
| **NGINX Ingress Basic Auth** | Basic authentication setup guide | https://kubernetes.github.io/ingress-nginx/examples/auth/basic/ |
| **Kubernetes RBAC** | Role-Based Access Control documentation | https://kubernetes.io/docs/reference/access-authn-authz/rbac/ |
| **Prometheus Querying** | PromQL query language guide | https://prometheus.io/docs/prometheus/latest/querying/basics/ |
| **Plotly Python** | Interactive charting library | https://plotly.com/python/ |
| **Celery Documentation** | Distributed task queue framework | https://docs.celeryq.dev/en/stable/ |
| **SQLAlchemy Documentation** | Python SQL toolkit and ORM | https://docs.sqlalchemy.org/en/20/ |

---

## References

Complete attribution for sources used in creating this guide.

### Project Sources

1. **Epic 6 Story Definitions:** `docs/epics.md` - Epic 6: Admin UI & Configuration Management, Stories 6.1-6.8
2. **PRD Requirements:** `docs/PRD.md` - Functional Requirements FR026-FR033 (Admin UI features)
3. **Architecture Decisions:** `docs/architecture.md` - ADR-009: Streamlit for Admin UI, Epic 6 implementation details
4. **Story Files:** `docs/stories/6-1-set-up-streamlit-application-foundation.md` through `6-7-add-worker-health-and-resource-monitoring.md`
5. **Existing Setup Guide:** `docs/admin-ui-setup.md` - Story 6.1 foundation guide (422 lines, created 2025-11-04)

### Code References

1. **Main Application:** `src/admin/app.py` - Streamlit entry point, multi-page navigation
2. **Dashboard Page:** `src/admin/pages/1_Dashboard.py` - System status metrics (Story 6.2)
3. **Tenant Management:** `src/admin/pages/2_Tenants.py` - CRUD operations (Story 6.3)
4. **Enhancement History:** `src/admin/pages/3_History.py` - Filtering and export (Story 6.4)
5. **System Operations:** `src/admin/pages/4_Operations.py` - Control panel (Story 6.5)
6. **Real-Time Metrics:** `src/admin/pages/6_Metrics.py` - Prometheus charts (Story 6.6)
7. **Worker Monitoring:** `src/admin/pages/5_Workers.py` - Health and logs (Story 6.7)
8. **Database Models:** `src/database/models.py` - TenantConfig, EnhancementHistory models
9. **Helper Modules:** `src/admin/utils/*.py` - db_helper, metrics_helper, worker_helper, operations_helper

### Kubernetes Manifests

1. **RBAC:** `k8s/streamlit-rbac.yaml` - ServiceAccount, Role, RoleBinding (Story 6.7, 87 lines)
2. **ConfigMap:** `k8s/streamlit-admin-configmap.yaml` - Streamlit config.toml
3. **Deployment:** `k8s/streamlit-admin-deployment.yaml` - Pod spec with resources
4. **Service:** `k8s/streamlit-admin-service.yaml` - LoadBalancer service
5. **Ingress:** `k8s/streamlit-admin-ingress.yaml` - NGINX with basic auth annotations
6. **Authentication Script:** `scripts/setup-streamlit-auth.sh` - htpasswd secret creation

### Research Sources

1. **2025 Documentation Best Practices:** Web search - "technical documentation best practices 2025 admin dashboard"
   - Technical Writer HQ: "6 Good Documentation Practices in 2025"
   - GitBook: "How to structure technical documentation: best practices"
   - DEV Community: "How to Write Technical Documentation in 2025"
2. **Dashboard Documentation Patterns:** Web search - "dashboard documentation structure wireframes"
   - Chartio: "How to Create Documentation for Dashboards"
   - Nasten: "How to write Dashboard Documentation"
3. **Streamlit Kubernetes Deployment:** Official Streamlit documentation
   - https://docs.streamlit.io/deploy/tutorials/kubernetes
4. **NGINX Ingress Basic Auth:** Kubernetes Ingress-NGINX documentation
   - https://kubernetes.github.io/ingress-nginx/examples/auth/basic/

### Standards and Best Practices

1. **Progressive Disclosure Pattern:** 2025 UX research - hierarchical information delivery
2. **Role-Based Documentation:** Separate sections for developers vs operations engineers
3. **Visual Aids:** Screenshot/wireframe best practices for technical documentation
4. **Troubleshooting Structure:** Symptom → Diagnostics → Solutions pattern
5. **Security Hardening:** Production deployment checklist methodology
6. **RBAC Principle:** Least privilege security model

### Version Information

- **Streamlit:** 1.44.0+
- **Kubernetes:** 1.28+
- **Python:** 3.12+
- **PostgreSQL:** 16+
- **NGINX Ingress:** 1.9.4+
- **Prometheus:** 2.x
- **Document Version:** 1.0.0
- **Last Updated:** 2025-11-04
- **Story:** 6.8 - Create Admin UI Documentation and Deployment Guide

---

**End of Admin UI Guide**

For questions, issues, or contributions:
1. Check Troubleshooting section above
2. Review Related Documentation for specific topics
3. Consult story files (6.1-6.7) for implementation details
4. Contact: DevOps team (admin-ui-support@example.com)

---

*This guide supersedes `admin-ui-setup.md` (Story 6.1). For historical reference, the original setup guide is preserved at `docs/admin-ui-setup.md`.*

