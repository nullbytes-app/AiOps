# Streamlit to Next.js UI Migration Guide

**Version:** 1.0
**Date:** January 2025
**For:** AI Agents Platform Operations Team

---

## Overview

This guide helps you transition from the Streamlit admin interface to the new Next.js UI. All functionality remains the same or improved, with a modern interface, better performance, and enhanced security.

---

## Page Mapping: Streamlit → Next.js

| # | Streamlit Page | Next.js Location | URL Path | Notes |
|---|----------------|------------------|----------|-------|
| 1 | Dashboard | Monitoring → Dashboard | `/dashboard` | Same metrics, faster refresh (5s vs 30s polling) |
| 2 | Tenants | Configuration → Tenants | `/tenants` | Now has search/filter, pagination |
| 3 | Plugin Management | Configuration → Plugins | `/plugins` | Renamed from "Plugin Management" to "Plugins" |
| 4 | History | Operations → Execution History | `/execution-history` | Enhanced filters (date range, status, agent) |
| 5 | Agent Management | Configuration → Agents | `/agents` | Now includes test sandbox (`/agents/[id]/test`) |
| 6 | LLM Providers | Configuration → LLM Providers | `/llm-providers` | Same functionality, glassmorphic cards |
| 7 | Operations | Operations → Queue Management | `/operations` | Pause/resume queue, live queue depth chart |
| 8 | Workers | Monitoring → Workers | `/workers` | Real-time worker status (3s polling) |
| 9 | System Prompt Editor | Tools → System Prompts | `/prompts` | CodeMirror editor, live preview with variables |
| 10 | Add Tool | Tools → Add Tool | `/tools` | OpenAPI spec upload with validation |
| 11 | Execution History | Operations → Execution History | `/execution-history` | Merged with #4 (same page) |
| 12 | MCP Servers | Configuration → MCP Servers | `/mcp-servers` | Test connection, tool discovery |
| 13 | LLM Costs | Monitoring → LLM Costs | `/costs` | Date range picker, CSV export |
| 14 | Agent Performance | Monitoring → Agent Performance | `/performance` | Sortable columns, trend charts |

---

## New Features in Next.js UI

### 1. **Tenant Switcher** (Top-Right Dropdown)
- **What:** Switch between tenants without logging out
- **Where:** Header, next to user menu
- **How:** Click dropdown → Select tenant → UI updates instantly
- **Search:** Type to filter tenants (useful with 10+ tenants)

### 2. **Dark Mode** (Theme Toggle)
- **What:** Toggle between light and dark themes
- **Where:** Header, moon/sun icon OR press `Cmd+D` (Ctrl+D on Windows)
- **How:** Persists across sessions in browser localStorage

### 3. **Command Palette** (Keyboard Shortcuts)
- **What:** Quick navigation and search
- **Trigger:** Press `Cmd+K` (Ctrl+K on Windows)
- **Features:**
  - Search all pages (fuzzy search)
  - Recent items (last 10 visited pages)
  - Quick actions (create agent, pause queue)
- **Exit:** Press `Esc`

### 4. **Keyboard Shortcuts**
| Shortcut | Action |
|----------|--------|
| `Cmd+K` or `Ctrl+K` | Open command palette |
| `Cmd+D` or `Ctrl+D` | Toggle dark mode |
| `?` | Show all keyboard shortcuts |
| `Esc` | Close modals/dialogs |
| `/` | Focus search input (on pages with search) |
| Arrow keys | Navigate tables, dropdowns |

### 5. **Mobile Support**
- **What:** Fully responsive design for phones and tablets
- **Features:**
  - Bottom navigation (4 category icons)
  - Swipe gestures for navigation
  - Touch-optimized buttons and forms
  - Horizontal scroll for tables
- **Tested on:** iPhone 13 (iOS 16), Samsung Galaxy S21 (Android 12)

### 6. **Real-Time Polling**
- Dashboard metrics refresh every 5 seconds (vs 30s in Streamlit)
- Queue status refreshes every 3 seconds
- Workers status refreshes every 3 seconds
- Execution history supports manual refresh

### 7. **Feedback Widget**
- **What:** Submit feedback directly from the UI
- **Where:** Floating "💬 Feedback" button (bottom-right)
- **How:** Click → Select sentiment (Love it / It's okay / Hate it) → Optional comment → Submit
- **Privacy:** Feedback includes page URL, sentiment, comment (anonymous)

### 8. **Glassmorphic Design**
- **What:** Apple-inspired "Liquid Glass" aesthetic
- **Features:**
  - Semi-transparent cards with backdrop blur
  - Animated neural network background (light mode)
  - Particle system background (dark mode)
  - Smooth animations and transitions
- **Performance:** Auto-disabled on low-end devices, respects `prefers-reduced-motion`

### 9. **Enhanced Data Tables**
- **Sortable Columns:** Click header to sort ascending/descending
- **Filters:** Search/filter by multiple criteria
- **Pagination:** 50 items per page (configurable)
- **Export:** CSV export on Execution History and LLM Costs pages

### 10. **Role-Based Access Control (RBAC)**
- **What:** User permissions based on assigned role
- **Roles:** Super Admin, Tenant Admin, Operator, Developer, Viewer
- **Impact:** Some buttons/pages hidden based on your role (e.g., Viewer cannot edit agents)

---

## Breaking Changes

### 1. **Authentication Required**
- **Old:** K8s Ingress basic auth (username/password pop-up)
- **New:** JWT-based authentication with login page
- **Impact:**
  - You must create an account (one-time)
  - Login at `/auth/login` with email + password
  - Tokens expire after 7 days (auto-logout)
  - Forgot password flow available

### 2. **URL Structure Changed**
- **Old:** `/admin` (Streamlit root)
- **New:** `/dashboard` (Next.js root)
- **Redirect:** `/admin` redirects to `/dashboard` during transition
- **Bookmarks:** Update your bookmarks to new URLs (see table above)

### 3. **Role-Based Permissions**
- **Old:** Everyone had full admin access
- **New:** Permissions based on assigned role
- **Impact:**
  - **Super Admin:** Full access (all CRUD operations)
  - **Tenant Admin:** Manage agents, tenants, configurations for assigned tenant
  - **Operator:** Pause queue, view dashboards, execution history (read-only configs)
  - **Developer:** Test agents, debug executions, configure plugins (no tenant/user management)
  - **Viewer:** Read-only access (dashboards, reports, history)
- **Check Your Role:** Click user menu (top-right) → Shows role for current tenant

---

## Side-by-Side Screenshots

### 1. Dashboard Comparison
**Streamlit (Old):**
- Single-column layout
- Static metrics cards
- Manual refresh button
- No real-time updates

**Next.js (New):**
- Responsive grid layout
- Glassmorphic metric cards with color coding
- Auto-refresh every 5 seconds
- Animated charts (Recharts LineChart)
- Activity feed with "time ago" format

### 2. Agent Management Comparison
**Streamlit (Old):**
- Simple form with text inputs
- No search/filter
- Full page reload on save

**Next.js (New):**
- Searchable agent table (TanStack Table)
- Filter by status (active/inactive)
- Modal-based forms (no page reload)
- Test sandbox: `/agents/[id]/test` with live execution

### 3. Execution History Comparison
**Streamlit (Old):**
- Basic table, no pagination
- Limited filters (status only)
- No export

**Next.js (New):**
- Sortable columns (click header)
- Advanced filters: date range, status, agent
- Pagination (50 per page)
- CSV export button
- Detail modal with JSON diff viewer

### 4. LLM Costs Comparison
**Streamlit (Old):**
- Simple chart
- Last 30 days only
- No export

**Next.js (New):**
- Date range picker (7/30/90 days, custom)
- Area chart + token breakdown table
- CSV export with full cost details
- Model-level breakdown

### 5. Mobile View Comparison
**Streamlit (Old):**
- Not mobile-optimized
- Requires horizontal scrolling
- Buttons too small for touch

**Next.js (New):**
- Fully responsive (mobile-first design)
- Bottom navigation (4 icons)
- Touch-optimized buttons (44x44px minimum)
- Forms stack vertically on mobile

---

## Frequently Asked Questions (FAQ)

### Q1: How do I get my login credentials?
**A:** Contact your system administrator. They will:
1. Create your user account with email
2. Assign you a role (super_admin, tenant_admin, operator, developer, or viewer)
3. Send you a password reset link
4. You set your own password (12+ characters, uppercase, number, special character)

### Q2: What if I forget my password?
**A:** Click "Forgot password?" on the login page → Enter your email → Check email for reset link → Set new password.

### Q3: Can I use both Streamlit and Next.js during the transition?
**A:** Yes, during the **2-week transition period**:
- **Next.js UI:** `/dashboard` (new, recommended)
- **Streamlit UI:** `/admin-legacy` (old, read-only)

After 2 weeks, Streamlit will be decommissioned and redirect to Next.js.

### Q4: Why can't I see the "Delete Tenant" button anymore?
**A:** Role-based access control (RBAC) is now enforced. Only **Super Admin** and **Tenant Admin** can delete tenants. Check your role in the user menu (top-right).

### Q5: Where did the "Operations" page go?
**A:** It was renamed to **"Queue Management"** and is now under **Operations → Queue Management** (`/operations`).

### Q6: How do I switch between tenants?
**A:** Click the **Tenant Switcher** dropdown in the top-right header (next to your user avatar) → Select tenant → UI updates instantly with new tenant's data.

### Q7: Can I still use keyboard shortcuts?
**A:** Yes! Next.js has **more** keyboard shortcuts. Press `?` to see the full list. Popular ones:
- `Cmd+K`: Command palette
- `Cmd+D`: Toggle dark mode
- `Esc`: Close modals

### Q8: Is my data still the same?
**A:** Yes, both UIs connect to the same PostgreSQL database and FastAPI backend. Your data is unchanged.

### Q9: What happens to my Streamlit bookmarks?
**A:** Update them to the new Next.js URLs (see "Page Mapping" table above). Old URLs may redirect during the transition but will eventually break.

### Q10: How do I report bugs or request features?
**A:** Click the **"💬 Feedback"** button (bottom-right) → Select sentiment → Describe the issue → Submit. Your feedback goes directly to the product team.

---

## Getting Help

### Support Resources
- **Quick Start Guide:** `docs/quick-start-guide.pdf` (1-page PDF)
- **Video Walkthrough:** `docs/video-walkthrough.mp4` (5-minute tour)
- **Runbooks:** `docs/runbooks/` (troubleshooting common issues)
- **API Docs:** `/api/v1/docs` (Swagger UI)

### Common Issues
- **Login Issues:** See `docs/runbooks/login-issues.md`
- **Performance Issues:** See `docs/runbooks/performance-issues.md`
- **Data Sync Issues:** See `docs/runbooks/data-sync-issues.md`

### Contact
- **Email:** support@aiagents.example.com (placeholder)
- **Slack:** #ai-agents-support (if internal Slack)
- **Feedback Widget:** Click "💬 Feedback" button in UI

---

## Training & Onboarding

### Live Demo Session
- **When:** 1 week before GA launch
- **Duration:** 30 minutes (20min walkthrough, 10min Q&A)
- **Format:** Zoom with screen sharing
- **Recording:** Available for those who cannot attend

### Self-Paced Learning
1. Read this migration guide (you are here!)
2. Watch the 5-minute video walkthrough
3. Review the quick start guide PDF
4. Log in and explore (use test tenant if available)
5. Ask questions via feedback widget or support channels

---

## Timeline

| Phase | Date | Status |
|-------|------|--------|
| **Alpha** (3 users) | Week 1 | ✅ Complete |
| **Beta** (10 users) | Week 2 | ✅ Complete |
| **GA** (All users) | Week 3 | 🚀 Launching |
| **Streamlit Decommission** | Week 5 (2 weeks after GA) | Planned |

---

**Generated by:** Bob (Scrum Master)
**Date:** January 2025
**Version:** 1.0
