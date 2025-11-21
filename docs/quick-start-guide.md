# Quick Start Guide - AI Agents Platform (Next.js UI)

**Version:** 1.0 | **Date:** January 2025 | **Goal:** Get started in 5 minutes ⏱️

---

## 1. Login (30 seconds)

**URL:** `https://your-domain.com/auth/login`

1. Enter your email and password
2. Click **Log in**
3. ✅ You're in! Welcome screen appears

**First time?** Contact your admin for login credentials.

**Forgot password?** Click "Forgot password?" → Check email → Reset

---

## 2. Navigation Overview (1 minute)

### Main Menu (Left Sidebar)
```
📊 Monitoring
   └─ Dashboard, Workers, LLM Costs, Agent Performance

⚙️ Configuration
   └─ Tenants, Agents, LLM Providers, Plugins, MCP Servers

🔧 Operations
   └─ Queue Management, Execution History

🛠️ Tools
   └─ System Prompts, Add Tool
```

### Quick Navigation
- **Desktop:** Click sidebar items
- **Mobile:** Bottom navigation (4 icons: Monitoring, Configuration, Operations, Tools)

---

## 3. Tenant Switcher (30 seconds)

**Location:** Top-right dropdown (next to your avatar)

**To switch tenants:**
1. Click tenant dropdown
2. Type to search (if you have 10+ tenants)
3. Select tenant → UI updates instantly

**Current tenant** is shown in the header (e.g., "tenant-abc")

---

## 4. Keyboard Shortcuts (1 minute)

| Shortcut | Action |
|----------|--------|
| `Cmd+K` (Mac) or `Ctrl+K` (Windows) | Open command palette (search pages, recent items) |
| `Cmd+D` (Mac) or `Ctrl+D` (Windows) | Toggle dark mode |
| `?` | Show all keyboard shortcuts |
| `Esc` | Close modals/dialogs |
| `/` | Focus search input (on pages with search) |
| Arrow keys | Navigate tables, dropdowns |

**Pro tip:** Press `Cmd+K` → Type "agents" → Jump directly to Agent Management page

---

## 5. Common Tasks (2 minutes)

### Task 1: View Dashboard Metrics
1. Click **Monitoring → Dashboard** (or just `/dashboard`)
2. See real-time metrics: Active Agents, Pending Tasks, Avg Response Time, Success Rate
3. **Auto-refreshes every 5 seconds** (no manual refresh needed)

### Task 2: Create a New Agent
1. Click **Configuration → Agents** → **+ New Agent** button
2. Fill in:
   - **Name:** My Test Agent
   - **System Prompt:** "You are a helpful assistant"
   - **LLM Provider:** Select from dropdown (e.g., OpenAI GPT-4)
   - **Tenant:** (Auto-filled with current tenant)
3. Click **Save**
4. ✅ Agent appears in list

### Task 3: Test an Agent
1. Go to **Configuration → Agents**
2. Click on an agent → Click **Test** button (or go to `/agents/[id]/test`)
3. Enter test input: "Hello, how are you?"
4. Click **Run Test**
5. See output in real-time

### Task 4: View Execution History
1. Click **Operations → Execution History**
2. Use filters:
   - **Status:** All / Success / Failed / Running
   - **Date Range:** Last 7/30/90 days or Custom
   - **Agent:** Filter by specific agent
3. Click **Export CSV** to download results

### Task 5: Check LLM Costs
1. Click **Monitoring → LLM Costs**
2. Select date range (Last 7/30/90 days)
3. See area chart + token breakdown table
4. Click **Export CSV** for detailed cost analysis

---

## 6. Where to Get Help

### In-App Help
- **Feedback Widget:** Click "💬 Feedback" button (bottom-right)
- **Keyboard Shortcuts:** Press `?` to see all shortcuts

### Documentation
- **Migration Guide:** `docs/migration-guide.md` (if coming from Streamlit)
- **Changelog:** `docs/changelog.md` (what's new in v1.0)
- **Runbooks:** `docs/runbooks/` (troubleshooting common issues)
  - Login issues: `login-issues.md`
  - Performance issues: `performance-issues.md`
  - Data sync issues: `data-sync-issues.md`
- **API Docs:** `/api/v1/docs` (Swagger UI for developers)

### Support Channels
- **Email:** support@aiagents.example.com (placeholder)
- **Slack:** #ai-agents-support (if internal)

---

## 7. Role-Based Permissions

Your role determines what you can do:

| Role | Can View | Can Edit | Can Delete |
|------|----------|----------|------------|
| **Super Admin** | Everything | Everything | Everything |
| **Tenant Admin** | Tenant data | Agents, configs | Agents, tenants |
| **Operator** | Dashboards, history | Queue (pause/resume) | ❌ |
| **Developer** | Agents, configs | Agents, plugins | ❌ |
| **Viewer** | Everything | ❌ | ❌ |

**Check your role:** Click user menu (top-right) → Shows role for current tenant

---

## 8. Tips & Tricks

### Tip 1: Use Dark Mode for Long Sessions
- Press `Cmd+D` to toggle dark mode
- Reduces eye strain, saves battery on OLED screens

### Tip 2: Use Command Palette for Speed
- Press `Cmd+K` → Type what you want (fuzzy search)
- Faster than clicking through menus

### Tip 3: Export Data for Reporting
- Execution History and LLM Costs pages have **Export CSV** buttons
- Use for monthly reports, cost analysis

### Tip 4: Mobile Access
- Fully responsive design works on phones and tablets
- Bottom navigation (4 icons) for quick access
- Swipe gestures for navigation

### Tip 5: Real-Time Updates
- Dashboard auto-refreshes every 5 seconds
- Queue status auto-refreshes every 3 seconds
- Workers auto-refreshes every 3 seconds
- No need to manually refresh pages

---

## 9. Known Issues & Workarounds

### Issue 1: "Token expired. Please log in again"
**Cause:** Access token expires after 7 days
**Fix:** Log in again (automatic redirect)

### Issue 2: Data not updating immediately
**Cause:** Caching (Redis cache TTL = 30 seconds)
**Fix:** Wait 30 seconds OR hard refresh (`Cmd+Shift+R`)

### Issue 3: "You don't have permission to view this"
**Cause:** Your role doesn't allow this action (e.g., Viewer trying to edit)
**Fix:** Contact admin to upgrade your role OR switch to a tenant where you have higher permissions

---

## 10. Next Steps

After completing this quick start:
1. Watch the **5-minute video walkthrough** (`docs/video-walkthrough.md`)
2. Read the **migration guide** if coming from Streamlit (`docs/migration-guide.md`)
3. Explore the **API documentation** if you're a developer (`/api/v1/docs`)
4. Attend the **live demo** (scheduled 1 week before GA launch, check email)

---

**🚀 You're ready to go!** If you have questions, click the "💬 Feedback" button or contact support.

---

**Generated by:** Bob (Scrum Master)
**Date:** January 2025
**Version:** 1.0

---

## PDF Version

To generate a 1-page PDF from this Markdown:

**Option 1: Using Markdown to PDF Converter**
```bash
npx md-to-pdf docs/quick-start-guide.md --pdf-options '{"format": "A4", "margin": "10mm"}'
```

**Option 2: Using Pandoc**
```bash
pandoc docs/quick-start-guide.md -o docs/quick-start-guide.pdf \
  --pdf-engine=xelatex \
  --variable geometry:margin=0.5in \
  --variable fontsize=9pt
```

**Option 3: Using Print to PDF (Manual)**
1. Open this file in a Markdown viewer (Typora, VS Code Markdown Preview, GitHub)
2. Print to PDF (Cmd+P → Save as PDF)
3. Adjust margins/font size as needed to fit on 1 page

**Design Tips for 1-Page PDF:**
- Use 2-column layout for sections 5-10
- Reduce font size to 9pt for body text
- Use icons for section headers
- Remove the "PDF Version" section from the printed PDF
