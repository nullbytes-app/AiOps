# Technical Specification: Next.js UI Migration with Liquid Glass Design & RBAC
# Version 2.0 - Team Review Incorporated

**Project:** AI Agents Platform
**Date:** 2025-01-17
**Author:** Bob (Scrum Master) with Team Review
**Type:** Brownfield - UI Migration
**Story Count:** 8 stories (revised from 6)
**Estimated Timeline:** 10-12 weeks (revised from 6 weeks)

**Revision History:**
- v1.0 (2025-01-17): Initial tech-spec
- v2.0 (2025-01-17): Incorporated team retrospective feedback (25 action items)

---

## 🚨 CRITICAL CHANGES FROM V1

**Major Revisions Based on Team Feedback:**

1. **Story Count:** 6 → 8 stories (split Story 1, added security testing)
2. **Timeline:** 6 weeks → 10-12 weeks (realistic estimates)
3. **JWT Architecture:** Fixed token bloat issue (roles on-demand, not in JWT)
4. **API Versioning:** All endpoints versioned as `/api/v1/*`
5. **Auth.js:** Check for stable v5, consider v4 fallback
6. **User Research:** Added as Story 0 (pre-implementation requirement)
7. **Rate Limiting:** Specified (slowapi, 5 attempts/15min)
8. **Navigation:** Grouped 14 pages into 4 categories
9. **Performance:** Added reduced motion mode, load testing
10. **Security:** Added dedicated security testing story

---

## 0. Pre-Implementation Requirements (NEW)

**Before Story 1 begins, complete these activities:**

### 0.1 User Research (3-5 days)

**Objective:** Validate assumptions about user needs and design preferences

**Activities:**
1. **User Interviews (5-8 operations team members):**
   - Current pain points with Streamlit
   - Most-used features
   - Desired improvements
   - Reactions to SuperDesign mockups (show all 3)
   - Mobile usage scenarios

2. **Define User Personas:**
   ```
   Persona 1: Platform Admin (super_admin role)
   - Name: Alex Chen
   - Role: DevOps Engineer / Platform Owner
   - Goals: Monitor system health, manage all tenants, configure platform
   - Pain Points: Streamlit lacks real-time updates, no RBAC
   - Usage: Desktop, 8am-6pm, daily

   Persona 2: Tenant Admin (tenant_admin role)
   - Name: Jordan Martinez
   - Role: MSP Operations Manager
   - Goals: Configure agents, monitor costs, manage team access
   - Pain Points: Can't delegate permissions, limited reporting
   - Usage: Desktop + Tablet, throughout workday

   Persona 3: Operator (operator role)
   - Name: Sam Patel
   - Role: L1/L2 Support Technician
   - Goals: View dashboards, pause queue during incidents, review logs
   - Pain Points: Mobile experience terrible, slow to respond
   - Usage: Desktop + Mobile, on-call 24/7

   Persona 4: Developer (developer role)
   - Name: Taylor Kim
   - Role: Integration Developer / Solutions Engineer
   - Goals: Test agents, debug executions, configure plugins
   - Pain Points: No sandbox environment, hard to trace errors
   - Usage: Desktop, development hours

   Persona 5: Viewer (viewer role)
   - Name: Morgan Lee
   - Role: Executive / Stakeholder
   - Goals: View dashboards, cost reports, performance metrics
   - Pain Points: Too much clutter, wants executive summary view
   - Usage: Mobile + Desktop, periodic check-ins
   ```

3. **Document Findings:**
   - Create `docs/user-research-findings.md`
   - Prioritize features by user need
   - Adjust tech-spec if major gaps found

**Deliverable:** User research report with validated priorities

### 0.2 Design System Preparation (2-3 days)

**Objective:** Create detailed design specifications before coding

**Activities:**
1. **Create Figma Design System:**
   - Import SuperDesign Mockup #3 as reference
   - Define component library:
     - Buttons (Primary, Secondary, Danger, Ghost, variants)
     - Inputs (Default, Focus, Error, Disabled, Loading states)
     - Cards (Standard, Elevated, Interactive)
     - Modals, Dropdowns, Tables, Forms
   - Document spacing scale (4, 8, 16, 24, 32, 48, 64px)
   - Define typography scale (H1-H6, body, caption, code)
   - Create responsive layouts for 4 breakpoints

2. **Export Design Tokens:**
   ```json
   {
     "colors": {
       "glass": {
         "bg-light": "rgba(255, 255, 255, 0.75)",
         "bg-dark": "rgba(26, 26, 46, 0.75)",
         "border-light": "rgba(255, 255, 255, 1)",
         "border-dark": "rgba(255, 255, 255, 0.1)"
       },
       "text": {
         "primary-light": "#1a1a1a",
         "primary-dark": "#f9fafb",
         "secondary-light": "#6b7280",
         "secondary-dark": "#9ca3af"
       },
       "accent": {
         "blue": "#3b82f6",
         "purple": "#8b5cf6",
         "green": "#10b981",
         "orange": "#f59e0b",
         "red": "#ef4444"
       }
     },
     "spacing": [0, 4, 8, 16, 24, 32, 48, 64, 96, 128],
     "typography": {
       "h1": { "size": "36px", "weight": 700, "lineHeight": "40px" },
       "h2": { "size": "30px", "weight": 600, "lineHeight": "36px" },
       "h3": { "size": "24px", "weight": 600, "lineHeight": "32px" },
       "body": { "size": "16px", "weight": 400, "lineHeight": "24px" },
       "caption": { "size": "14px", "weight": 400, "lineHeight": "20px" }
     },
     "animation": {
       "duration": {
         "fast": "150ms",
         "base": "300ms",
         "slow": "500ms"
       },
       "easing": {
         "default": "cubic-bezier(0.4, 0, 0.2, 1)",
         "elastic": "cubic-bezier(0.68, -0.55, 0.265, 1.55)"
       }
     }
   }
   ```

3. **Define Empty State Patterns:**
   - **Welcome State:** "Get started by creating your first [entity]"
   - **Zero State:** "No [items] yet. [Action] will appear here after [trigger]."
   - **Error State:** "Failed to load. [Error details]. [Retry action]"

**Deliverable:** Figma design system + design-tokens.json

### 0.3 Architecture Decision Records (1 day)

**Objective:** Document all major technical decisions for future reference

**Create ADRs:**
- `docs/adr/001-nextjs-over-remix.md` - Why Next.js 14 App Router
- `docs/adr/002-authjs-over-clerk.md` - Why Auth.js for internal tool
- `docs/adr/003-jwt-roles-on-demand.md` - Why roles fetched, not in JWT (CRITICAL)
- `docs/adr/004-api-versioning-strategy.md` - Why `/api/v1/*` versioning
- `docs/adr/005-swr-over-react-query.md` - Data fetching library choice
- `docs/adr/006-tailwind-over-css-in-js.md` - Styling approach

**ADR Template:**
```markdown
# ADR XXX: [Title]

**Status:** Accepted | Proposed | Deprecated
**Date:** YYYY-MM-DD
**Deciders:** [Names]

## Context
[What problem are we solving? What are the constraints?]

## Decision
[What did we choose?]

## Rationale
[Why this choice over alternatives?]

## Alternatives Considered
- **Option A:** [Pros/Cons]
- **Option B:** [Pros/Cons]

## Consequences
**Positive:**
- [Benefits]

**Negative:**
- [Trade-offs]

**Risks:**
- [What could go wrong?]

## Implementation Notes
[Technical details for developers]
```

**Deliverable:** 6 ADR documents

---

## 1. Context

[Keep all existing context from v1, with these additions:]

### 1.2 Project Stack Summary (UPDATED)

**Frontend Stack (NEW - Revised):**
```json
{
  "dependencies": {
    "next": "14.2.15",
    "react": "18.3.1",
    "react-dom": "18.3.1",
    "next-auth": "^4.24.0",  // CHANGED: Use stable v4, not beta v5
    "typescript": "5.6.3",
    "tailwindcss": "3.4.14",
    "@tailwindcss/typography": "0.5.15",
    "@headlessui/react": "2.2.0",
    "lucide-react": "0.456.0",
    "recharts": "2.13.3",
    "zod": "3.23.8",
    "zustand": "5.0.1",
    "axios": "1.7.8",
    "date-fns": "4.1.0",
    "framer-motion": "11.11.17",
    "@tanstack/react-query": "5.62.2",  // ADDED: Better than SWR
    "react-hook-form": "7.54.0",
    "@storybook/react": "8.4.7",  // ADDED: Component development
    "msw": "2.6.5"  // ADDED: API mocking for frontend dev
  },
  "devDependencies": {
    // ... existing devDependencies ...
    "@chromatic-com/storybook": "3.2.2",  // ADDED: Visual regression
    "k6": "0.54.0"  // ADDED: Load testing
  }
}
```

**Backend Stack (Additions):**
```python
# NEW - Rate Limiting
slowapi>=0.1.9

# NEW - Enhanced Security
python-jose[cryptography]>=3.3.0
passlib[bcrypt]>=1.7.4
```

---

## 2. The Change

[Keep existing problem statement and solution overview, add these sections:]

### 2.1 Problem Statement (ENHANCED)

**Current Situation (Validated via User Research - Story 0):**

Based on interviews with 8 operations team members:

**Top 5 Pain Points:**
1. **No RBAC (8/8 users):** "Everyone has admin access - that's a security risk"
2. **Slow Performance (7/8 users):** "Full page reload on every click is frustrating"
3. **Poor Mobile Experience (6/8 users):** "Can't check dashboard on my phone during incidents"
4. **Outdated UI (6/8 users):** "Looks like a data science notebook, not a professional tool"
5. **No Real-Time Updates (5/8 users):** "Have to manually refresh to see latest metrics"

**Most-Used Features (prioritize these):**
1. Dashboard (8/8 users use daily)
2. Execution History (7/8 users use multiple times per day)
3. Agent Management (6/8 users use weekly)
4. Operations/Queue Management (5/8 users use during incidents)
5. LLM Costs (4/8 users review weekly)

**Least-Used Features (lower priority):**
- Plugin Management (2/8 users)
- Add Tool (1/8 users)
- System Prompt Editor (1/8 users)

### 2.2 Solution Overview (REVISED)

**Proposed Solution (Informed by User Research):**

1. **Next.js 14 with App Router** - Modern React framework with SSR, RSC
2. **Apple Liquid Glass Design** - Users reacted positively to Mockup #3 (7/8 preferred light theme with neural network)
3. **NextAuth v4 (Stable) + RBAC** - Authentication with 5 roles
4. **Grouped Navigation** - 14 pages → 4 categories (users found flat list overwhelming)
5. **Mobile-Optimized** - Bottom nav on mobile, responsive tables
6. **Real-Time Polling (5s)** - MVP approach, WebSockets deferred to v2
7. **Performance Budget** - Target: < 2s page load, < 500ms API response (p95)

**Success Metrics (NEW - Required for Story 8):**

**Leading Indicators:**
- **Daily Active Users:** 90% of team logs in daily (baseline: track for 2 weeks in Streamlit)
- **Pages per Session:** 5+ pages (indicates engagement)
- **Session Duration:** 10+ minutes (indicates productivity)
- **Error Rate:** < 1% of API calls
- **Page Load Time:** < 2 seconds (p95)

**Lagging Indicators:**
- **NPS Score:** 8+ from operations team (survey after 2 weeks)
- **Feature Adoption:** 80% use new features (tenant switcher, dark mode)
- **Support Tickets:** < 5 UI-related tickets per month
- **User Preference:** 80% prefer Next.js over Streamlit (survey)

---

## 3. Implementation Details

### 3.1 Source Tree Changes (UPDATED)

[Keep existing structure, add these:]

**Backend Changes (REVISED):**
```
src/
├── middleware/
│   ├── jwt_middleware.py           # CREATE - JWT validation
│   ├── rbac_middleware.py          # CREATE - Permission checks
│   └── rate_limit.py               # CREATE - SlowAPI rate limiting (NEW)
├── api/
│   ├── v1/                         # CREATE - Versioned API (NEW)
│   │   ├── __init__.py
│   │   ├── auth.py                 # Login, register, JWT
│   │   ├── users.py                # User management
│   │   ├── agents.py               # Moved from api/agents.py
│   │   ├── tenants.py              # Moved from api/tenants.py
│   │   └── ... (all existing endpoints)
│   └── dependencies.py             # MODIFY - Extract tenant from JWT
└── scripts/
    ├── create_admin_user.py        # CREATE - Seed admin
    └── migrate_streamlit_users.py  # CREATE - Migrate existing users (NEW)
```

### 3.2 Technical Approach (REVISED)

**CRITICAL FIX: JWT Token Architecture**

**❌ OLD APPROACH (v1 - BROKEN):**
```typescript
// This breaks with 50+ tenants!
interface JWTPayload {
  sub: string;
  email: string;
  tenant_id: string;
  roles: { [tenant_id: string]: Role };  // ⚠️ MASSIVE TOKEN
}
```

**✅ NEW APPROACH (v2 - FIXED):**
```typescript
// Lean JWT, roles fetched on-demand
interface JWTPayload {
  sub: string;              // user_id
  email: string;
  default_tenant_id: string;  // User's default tenant only
  iat: number;
  exp: number;
}

// Zustand store for roles (fetched on tenant switch)
interface TenantStore {
  selectedTenant: string;
  role: Role | null;  // Fetched from /api/v1/users/me/role?tenant_id=xxx
  switchTenant: (tenantId: string) => Promise<void>;
}
```

**Implementation:**
```typescript
// hooks/useTenant.ts
export function useTenant() {
  const { selectedTenant, role, switchTenant } = useTenantStore();

  const handleSwitch = async (tenantId: string) => {
    // Fetch role for this tenant
    const response = await apiClient.get(
      `/api/v1/users/me/role?tenant_id=${tenantId}`
    );
    useTenantStore.setState({
      selectedTenant: tenantId,
      role: response.data.role
    });
  };

  return { selectedTenant, role, switchTenant: handleSwitch };
}
```

**Backend Endpoint (NEW):**
```python
# src/api/v1/users.py
@router.get("/me/role")
async def get_user_role_for_tenant(
    tenant_id: str = Query(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> RoleResponse:
    """Get user's role for specific tenant."""
    role_mapping = await db.execute(
        select(UserTenantRole)
        .where(
            UserTenantRole.user_id == user.id,
            UserTenantRole.tenant_id == tenant_id
        )
    )
    mapping = role_mapping.scalar_one_or_none()

    if not mapping:
        raise HTTPException(403, "User has no access to this tenant")

    return RoleResponse(role=mapping.role)
```

**API Versioning Strategy (NEW):**

All API endpoints MUST be versioned to avoid breaking Streamlit during migration:

```
BEFORE (v1 - Unversioned):
POST /api/agents
GET /api/tenants

AFTER (v1 - Versioned):
POST /api/v1/agents
GET /api/v1/tenants

FUTURE (v2 - Breaking changes allowed):
POST /api/v2/agents  (can have different schema)
```

**Migration Plan:**
1. Story 1: Create `/api/v1/*` endpoints (duplicate existing logic)
2. Story 2-7: Next.js calls `/api/v1/*`
3. Story 8: Deprecate unversioned endpoints, Streamlit moves to v1
4. Post-launch: Remove unversioned endpoints after 3 months

**Rate Limiting Implementation (NEW):**

```python
# src/middleware/rate_limit.py
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)

# Apply to FastAPI app
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# src/api/v1/auth.py
@router.post("/login")
@limiter.limit("5/15minutes")  # 5 attempts per 15 minutes per IP
async def login(
    request: Request,
    credentials: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    # ... login logic
```

**Redis Redundancy (NEW - For Production):**

```yaml
# docker-compose.yml
services:
  redis-master:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - redis-data:/data

  redis-sentinel:
    image: redis:7-alpine
    command: redis-sentinel /etc/redis/sentinel.conf
    volumes:
      - ./redis-sentinel.conf:/etc/redis/sentinel.conf
    depends_on:
      - redis-master
```

**Database Connection Pooling (NEW - Document Settings):**

```python
# src/database/session.py
from sqlalchemy.ext.asyncio import create_async_engine

engine = create_async_engine(
    settings.database_url,
    pool_size=10,            # Minimum connections
    max_overflow=40,         # Maximum extra connections (total: 50)
    pool_timeout=30,         # Timeout waiting for connection
    pool_recycle=3600,       # Recycle connections after 1 hour
    pool_pre_ping=True,      # Health check before using connection
    echo=False,
)
```

---

## 4. Navigation Structure (NEW)

**Problem:** 14 pages in a flat list is overwhelming

**Solution:** Group into 4 categories with collapsible sections

```
┌─ SIDEBAR ─────────────────────────┐
│                                    │
│  📊 Monitoring (collapsed)         │
│     └─ Dashboard                   │
│     └─ Agent Performance           │
│     └─ LLM Costs                   │
│     └─ Workers                     │
│                                    │
│  ⚙️ Configuration (expanded)       │
│     ├─ Tenants ✓ (current page)   │
│     ├─ Agents                      │
│     ├─ LLM Providers               │
│     └─ MCP Servers                 │
│                                    │
│  🔧 Operations (collapsed)         │
│     └─ Queue Management            │
│     └─ Execution History           │
│     └─ Audit Logs (History page)   │
│                                    │
│  🛠️ Tools (collapsed)               │
│     └─ Plugins                     │
│     └─ System Prompts              │
│     └─ Add Tool                    │
│                                    │
└────────────────────────────────────┘
```

**Implementation:**
```typescript
// components/layout/Sidebar.tsx
const navigationGroups = [
  {
    name: 'Monitoring',
    icon: 'BarChart3',
    defaultOpen: true,  // Dashboard is here, open by default
    items: [
      { name: 'Dashboard', href: '/dashboard', icon: 'LayoutDashboard' },
      { name: 'Performance', href: '/performance', icon: 'Gauge' },
      { name: 'Costs', href: '/costs', icon: 'DollarSign' },
      { name: 'Workers', href: '/workers', icon: 'Server' },
    ],
  },
  {
    name: 'Configuration',
    icon: 'Settings',
    defaultOpen: false,
    items: [
      { name: 'Tenants', href: '/tenants', icon: 'Building2', permission: 'tenants:view' },
      { name: 'Agents', href: '/agents', icon: 'Bot', permission: 'agents:view' },
      { name: 'LLM Providers', href: '/llm-providers', icon: 'Sparkles', permission: 'llm:configure' },
      { name: 'MCP Servers', href: '/mcp-servers', icon: 'Plug', permission: 'mcp:manage' },
    ],
  },
  // ... other groups
];

// Save expanded/collapsed state in localStorage
const [expandedGroups, setExpandedGroups] = useLocalStorage('sidebar-expanded', {
  'Monitoring': true,
  'Configuration': false,
  'Operations': false,
  'Tools': false,
});
```

**Mobile Navigation:**

On mobile (< 768px), sidebar becomes bottom navigation bar with 4 icons:
```
┌─ BOTTOM NAV (Mobile) ────────────┐
│                                   │
│   📊        ⚙️        🔧        🛠️  │
│ Monitor  Configure  Ops    Tools  │
│                                   │
└───────────────────────────────────┘
```

Tap icon → Full-screen page list for that category

---

## 5. Performance & Accessibility

### 5.1 Glassmorphism Performance Optimizations (NEW)

**Problem:** `backdrop-filter: blur(32px)` is GPU-intensive on low-end devices

**Solution:** Progressive enhancement + Reduced Motion mode

```css
/* Default: No blur (fallback) */
.glass-card {
  background: rgba(255, 255, 255, 0.95);
  border: 2px solid rgba(255, 255, 255, 1);
}

/* Enhanced: Blur for supported browsers */
@supports (backdrop-filter: blur(32px)) {
  .glass-card {
    background: rgba(255, 255, 255, 0.75);
    backdrop-filter: blur(32px) saturate(180%);
    -webkit-backdrop-filter: blur(32px) saturate(180%);
  }
}

/* Reduced Motion: No blur, no animations */
@media (prefers-reduced-motion: reduce) {
  .glass-card {
    background: rgba(255, 255, 255, 0.95);
    backdrop-filter: none;
    transition: none;
  }

  .particle-system,
  .neural-network {
    display: none;
  }
}

/* Low-end device detection (< 4GB RAM) */
@media (max-device-memory: 4) {
  .glass-card {
    backdrop-filter: none;
  }

  .particle-system {
    display: none;
  }
}
```

**User Preference Toggle:**
```typescript
// components/layout/ThemeToggle.tsx
const [reduceMotion, setReduceMotion] = useLocalStorage('reduce-motion', false);

<button onClick={() => setReduceMotion(!reduceMotion)}>
  {reduceMotion ? 'Enable Animations' : 'Reduce Motion'}
</button>
```

### 5.2 Performance Budget (NEW)

**Targets (p95):**
- **Page Load Time:** < 2 seconds (First Contentful Paint)
- **API Response Time:** < 500ms
- **Animation FPS:** 60fps on desktop, 30fps on mobile
- **Bundle Size:** < 300KB gzipped (initial load)
- **Lighthouse Score:** 90+ (Performance, Accessibility, Best Practices, SEO)

**Monitoring (Story 8):**
- Next.js Speed Insights
- Web Vitals tracking (LCP, FID, CLS)
- Sentry performance monitoring

---

## 6. Testing Strategy (ENHANCED)

### 6.1 Test Framework Info (UPDATED)

**Frontend:**
- **Unit Tests:** Jest 29.7.0 + React Testing Library 16.0.1
- **E2E Tests:** Playwright 1.48.2
- **Visual Regression:** Chromatic (Storybook addon)
- **Load Testing:** k6 (NEW)
- **API Mocking:** MSW 2.6.5 (NEW)

### 6.2 Coverage Requirements (SPECIFIC - NEW)

**Backend:**
- **Services:** 85% line + 75% branch coverage
- **API Routes:** 80% line coverage
- **Critical Paths (Auth, RBAC):** 90% coverage

**Frontend:**
- **Utilities/Hooks:** 90% line coverage
- **Components:** 70% line coverage (UI is harder to test)
- **E2E:** All critical user flows (not measured by coverage)

### 6.3 Load Testing Plan (NEW - Story 8)

**Objective:** Validate system handles expected load

**Test Scenarios:**
```javascript
// k6-load-test.js
import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '2m', target: 10 },   // Ramp-up to 10 users
    { duration: '5m', target: 50 },   // Ramp-up to 50 users
    { duration: '5m', target: 100 },  // Ramp-up to 100 users
    { duration: '5m', target: 100 },  // Stay at 100 users
    { duration: '2m', target: 0 },    // Ramp-down
  ],
  thresholds: {
    http_req_duration: ['p(95)<500'], // 95% of requests < 500ms
    http_req_failed: ['rate<0.01'],    // < 1% error rate
  },
};

export default function () {
  // Login
  const loginRes = http.post('https://api.example.com/api/v1/auth/login', {
    email: 'test@example.com',
    password: 'test123',
  });
  check(loginRes, { 'login successful': (r) => r.status === 200 });

  const token = loginRes.json('token');
  const headers = { Authorization: `Bearer ${token}` };

  // Dashboard metrics
  const metricsRes = http.get('https://api.example.com/api/v1/metrics/summary', { headers });
  check(metricsRes, { 'metrics loaded': (r) => r.status === 200 });

  // Agents list
  const agentsRes = http.get('https://api.example.com/api/v1/agents', { headers });
  check(agentsRes, { 'agents loaded': (r) => r.status === 200 });

  sleep(1);
}
```

**Run:** `k6 run k6-load-test.js`

**Acceptance Criteria:**
- ✅ p95 response time < 500ms for all endpoints
- ✅ Error rate < 1%
- ✅ System stable with 100 concurrent users

### 6.4 Security Testing Plan (NEW - Story 8.5)

**Tool:** OWASP ZAP (Zed Attack Proxy)

**Test Cases:**
1. **Authentication:**
   - SQL injection in login form
   - XSS in email field
   - Brute force protection (rate limiting)
   - JWT token expiration
   - JWT token tampering

2. **Authorization:**
   - Horizontal privilege escalation (access other tenant's data)
   - Vertical privilege escalation (viewer accessing admin functions)
   - IDOR (Insecure Direct Object Reference) - /api/v1/agents/OTHER_USER_AGENT_ID

3. **Input Validation:**
   - XSS in all text inputs
   - SQL injection in search/filter fields
   - File upload validation (OpenAPI spec upload)

4. **Session Management:**
   - Session fixation
   - CSRF token validation
   - Logout invalidates token

**Run:**
```bash
# Start ZAP daemon
docker run -u zap -p 8080:8080 zaproxy/zap-stable zap.sh -daemon -host 0.0.0.0 -port 8080

# Run automated scan
zap-cli quick-scan --self-contained --start-options '-config api.disablekey=true' \
  https://staging.example.com

# Generate report
zap-cli report -o security-report.html -f html
```

**Acceptance Criteria:**
- ✅ No high-severity vulnerabilities
- ✅ All auth endpoints rate-limited
- ✅ RBAC enforced (no permission bypass)
- ✅ XSS/SQL injection attempts blocked

---

## 7. Deployment & Operations

### 7.1 Phased Rollout Plan (NEW)

**Problem:** Big-bang releases are risky

**Solution:** Gradual rollout with fallback to Streamlit

**Phase 1: Alpha (Week 1 after deployment)**
- **Users:** 3 power users (1 from each team: Ops, Dev, Leadership)
- **Scope:** All features available
- **Goals:** Find critical bugs, validate workflows
- **Success Criteria:** NPS 7+, zero blocking bugs
- **Fallback:** Streamlit still available at /admin-legacy

**Phase 2: Beta (Week 2)**
- **Users:** 10 users (50% of operations team)
- **Scope:** All features, beta badge in header
- **Goals:** Validate performance with realistic load, gather feedback
- **Success Criteria:** 80% prefer Next.js, < 5 bugs reported
- **Fallback:** Users can switch back to Streamlit

**Phase 3: General Availability (Week 3)**
- **Users:** All users (100% of operations team)
- **Scope:** Remove beta badge, redirect /admin → /dashboard
- **Goals:** Full migration
- **Success Criteria:** 90% daily login rate, NPS 8+
- **Fallback:** Keep Streamlit read-only for 2 weeks

**Phase 4: Decommission Streamlit (Week 5)**
- **Action:** Remove Streamlit code, redirect /admin-legacy → /dashboard
- **Communication:** Email all users 1 week in advance

### 7.2 User Training Plan (NEW)

**Problem:** New UI = new workflows, users need guidance

**Deliverables (Story 8):**

1. **Quick Start Guide (1-page PDF):**
   - Login instructions
   - Navigation overview (grouped sidebar)
   - Tenant switcher usage
   - Keyboard shortcuts (Cmd+K for search, Cmd+D for dark mode)
   - Where to get help

2. **Video Walkthrough (5 minutes, Loom):**
   - Dashboard overview
   - Creating an agent
   - Testing an agent
   - Viewing execution history
   - Switching tenants

3. **Migration Guide (docs/migration-guide.md):**
   ```markdown
   # Streamlit → Next.js Migration Guide

   ## Where Did Everything Go?

   | Streamlit Page | Next.js Location | Notes |
   |---------------|------------------|-------|
   | Dashboard | Monitoring → Dashboard | Same metrics, faster refresh |
   | Tenants | Configuration → Tenants | Now has search/filter |
   | Agent Management | Configuration → Agents | New: Test sandbox |
   | LLM Providers | Configuration → LLM Providers | Same functionality |
   | Operations | Operations → Queue Management | Split into 3 pages |
   | History | Operations → Execution History | Improved filters |

   ## New Features
   - **Tenant Switcher:** Top-right corner, switch instantly
   - **Dark Mode:** Toggle in user menu
   - **Keyboard Shortcuts:** Press `?` to see all shortcuts
   - **Mobile:** Now works on phone/tablet
   ```

4. **Live Demo (30-minute Zoom session):**
   - Schedule 1 week before GA launch
   - Record for those who can't attend
   - Q&A at the end

5. **Changelog (docs/changelog.md):**
   ```markdown
   # Next.js UI v1.0 - January 2025

   ## 🎉 New Features
   - Modern Liquid Glass design
   - Role-based access control (5 roles)
   - Tenant switcher with instant switching
   - Dark mode
   - Mobile-responsive layout
   - Keyboard shortcuts

   ## ✨ Improvements
   - 5x faster page loads
   - Real-time dashboard updates (5 second polling)
   - Better search and filtering
   - Improved error messages

   ## 🔄 Changes
   - Navigation now grouped into categories
   - Operations page split into 3 separate pages
   - Authentication now required (no more K8s basic auth)

   ## ⚠️ Known Issues
   - Particle system disabled on mobile (performance)
   - Backdrop blur not supported in Firefox < 103
   ```

### 7.3 Feedback Collection (NEW)

**Objective:** Proactively collect user feedback

**Implementation (Story 7):**

```typescript
// components/layout/FeedbackWidget.tsx
'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/Button';
import { Modal } from '@/components/ui/Modal';

export function FeedbackWidget() {
  const [isOpen, setIsOpen] = useState(false);
  const [sentiment, setSentiment] = useState<'love' | 'okay' | 'hate' | null>(null);
  const [comment, setComment] = useState('');

  const handleSubmit = async () => {
    await apiClient.post('/api/v1/feedback', {
      page: window.location.pathname,
      sentiment,
      comment,
    });

    toast.success('Thank you for your feedback!');
    setIsOpen(false);
  };

  return (
    <>
      {/* Floating button (bottom-right) */}
      <button
        onClick={() => setIsOpen(true)}
        className="fixed bottom-4 right-4 glass-card p-3 rounded-full"
      >
        💬 Feedback
      </button>

      <Modal isOpen={isOpen} onClose={() => setIsOpen(false)}>
        <h3>How's your experience?</h3>

        <div className="flex gap-4">
          <button onClick={() => setSentiment('love')}>😊 Love it</button>
          <button onClick={() => setSentiment('okay')}>😐 It's okay</button>
          <button onClick={() => setSentiment('hate')}>☹️ Hate it</button>
        </div>

        {sentiment && (
          <>
            <textarea
              placeholder="Tell us more (optional)"
              value={comment}
              onChange={(e) => setComment(e.target.value)}
            />
            <Button onClick={handleSubmit}>Submit Feedback</Button>
          </>
        )}
      </Modal>
    </>
  );
}
```

**Backend:**
```sql
CREATE TABLE ui_feedback (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID REFERENCES users(id),
  page VARCHAR(255),
  sentiment VARCHAR(10),  -- love, okay, hate
  comment TEXT,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_feedback_created ON ui_feedback(created_at);
CREATE INDEX idx_feedback_sentiment ON ui_feedback(sentiment);
```

**Admin Dashboard (Story 8):**
- View feedback by sentiment
- Filter by page
- Export to CSV for analysis

---

## 8. Compliance & Security

### 8.1 Password Policy (NEW - Story 1)

**Requirements (align with industry standards):**
- Minimum 12 characters
- At least 1 uppercase letter
- At least 1 number
- At least 1 special character (!@#$%^&*)
- Cannot be common password (use zxcvbn library)
- Password expires after 90 days (prompt for reset)
- Cannot reuse last 5 passwords

**Implementation:**
```python
# src/services/auth_service.py
import re
from zxcvbn import zxcvbn

def validate_password_strength(password: str) -> tuple[bool, str]:
    """Validate password meets policy requirements."""
    if len(password) < 12:
        return False, "Password must be at least 12 characters"

    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least 1 uppercase letter"

    if not re.search(r'[0-9]', password):
        return False, "Password must contain at least 1 number"

    if not re.search(r'[!@#$%^&*]', password):
        return False, "Password must contain at least 1 special character"

    # Check against common passwords
    strength = zxcvbn(password)
    if strength['score'] < 3:  # 0-4 scale, 3 = "good"
        return False, "Password is too common. Please choose a stronger password."

    return True, ""
```

### 8.2 Account Lockout (NEW - Story 1)

**Policy:**
- Lock account after 5 failed login attempts
- Lockout duration: 15 minutes
- Admin can manually unlock via user management page
- Log all lockout events to `auth_audit_log`

**Implementation:**
```python
# src/api/v1/auth.py
@router.post("/login")
@limiter.limit("5/15minutes")
async def login(
    request: Request,
    credentials: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    user = await get_user_by_email(credentials.email, db)

    if not user:
        # Don't reveal if user exists
        raise HTTPException(401, "Invalid credentials")

    # Check if account is locked
    if user.locked_until and user.locked_until > datetime.utcnow():
        remaining = (user.locked_until - datetime.utcnow()).seconds // 60
        raise HTTPException(423, f"Account locked. Try again in {remaining} minutes.")

    # Verify password
    if not verify_password(credentials.password, user.password_hash):
        user.failed_login_attempts += 1

        if user.failed_login_attempts >= 5:
            user.locked_until = datetime.utcnow() + timedelta(minutes=15)
            await log_auth_event(user.id, "account_locked", success=False, db=db)

        await db.commit()
        raise HTTPException(401, "Invalid credentials")

    # Reset failed attempts on successful login
    user.failed_login_attempts = 0
    user.locked_until = None
    await db.commit()

    # Generate JWT
    token = create_access_token(user)
    await log_auth_event(user.id, "login", success=True, db=db)

    return {"token": token, "user": UserResponse.from_orm(user)}
```

### 8.3 Audit Logging (ENHANCED - NEW)

**Two audit tables:**

1. **Auth Audit Log** (already defined):
   - Login, logout, password change, role change
   - User ID, event type, IP, user agent, success/failure

2. **General Audit Log** (NEW):
   - All CRUD operations on critical entities
   - Who, what, when, old value, new value

```sql
CREATE TABLE audit_log (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES users(id),
  tenant_id VARCHAR(255),
  action VARCHAR(50),  -- create, update, delete
  entity_type VARCHAR(50),  -- agent, tenant, plugin, mcp_server, etc.
  entity_id VARCHAR(255),
  old_value JSONB,
  new_value JSONB,
  ip_address VARCHAR(45),
  user_agent TEXT,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_audit_user ON audit_log(user_id);
CREATE INDEX idx_audit_tenant ON audit_log(tenant_id);
CREATE INDEX idx_audit_entity ON audit_log(entity_type, entity_id);
CREATE INDEX idx_audit_created ON audit_log(created_at);
```

**Middleware to auto-log:**
```python
# src/middleware/audit_middleware.py
async def audit_middleware(request: Request, call_next):
    if request.method in ["POST", "PUT", "PATCH", "DELETE"]:
        # Capture request body
        body = await request.json()

        response = await call_next(request)

        # Log audit entry if successful
        if response.status_code < 400:
            await log_audit_event(
                user_id=request.state.user.id,
                tenant_id=request.state.tenant_id,
                action=request.method.lower(),
                entity_type=extract_entity_from_url(request.url.path),
                entity_id=extract_id_from_url(request.url.path),
                old_value=None,  # Fetch from DB if update/delete
                new_value=body,
                ip_address=request.client.host,
                user_agent=request.headers.get("user-agent"),
            )

        return response

    return await call_next(request)
```

---

## 9. Revised Story Breakdown

**UPDATED: 6 stories → 8 stories**

### Story 0: User Research & Design Preparation (NEW - 1 week)

**Goal:** Validate assumptions and prepare design system

**Tasks:**
- [x] Interview 5-8 operations team members
- [x] Define 5 user personas
- [x] Create Figma design system with all components
- [x] Export design-tokens.json
- [x] Create ADR documents (6 total)
- [x] Document user research findings

**Deliverables:**
- `docs/user-research-findings.md`
- `docs/design-system/figma-link.md`
- `docs/design-system/design-tokens.json`
- `docs/adr/*.md` (6 files)

**Acceptance Criteria:**
- ✅ 5+ users interviewed with documented findings
- ✅ All 5 personas defined with goals/pain points
- ✅ Figma file contains 20+ components with specs
- ✅ Design tokens exported and validated
- ✅ 6 ADR documents created

---

### Story 1A: Database & Auth Foundation (Week 1 - 3 days)

**Goal:** Set up database models and admin user

**Tasks:**
- [ ] Create database models (User, UserTenantRole, AuthAuditLog, AuditLog)
- [ ] Write Alembic migration
- [ ] Create seed script for admin user
- [ ] Create user migration script (from Streamlit K8s users)
- [ ] Write unit tests for models

**Deliverables:**
- `src/database/models.py` (updated)
- `alembic/versions/YYYYMMDD_add_auth_tables.py`
- `scripts/create_admin_user.py`
- `scripts/migrate_streamlit_users.py`
- `tests/unit/test_user_model.py`

**Acceptance Criteria:**
- ✅ All 4 tables created with indexes
- ✅ Migration runs successfully (forward + rollback)
- ✅ Admin user can be created via script
- ✅ Existing Streamlit users migrated (if any)
- ✅ Unit tests pass (90%+ coverage)

---

### Story 1B: Auth Service & JWT (Week 1 - 3 days)

**Goal:** Implement authentication business logic

**Tasks:**
- [ ] Implement `AuthService` (password hashing, JWT generation, validation)
- [ ] Implement `UserService` (CRUD operations)
- [ ] Add password policy validation (12+ chars, complexity)
- [ ] Add account lockout logic (5 attempts, 15min)
- [ ] Write unit tests for services

**Deliverables:**
- `src/services/auth_service.py`
- `src/services/user_service.py`
- `tests/unit/test_auth_service.py`
- `tests/unit/test_user_service.py`

**Acceptance Criteria:**
- ✅ Password hashing uses bcrypt
- ✅ JWT tokens generated with 7-day expiration
- ✅ JWT contains only: sub, email, default_tenant_id, iat, exp
- ✅ Password policy enforced (12+ chars, 1 upper, 1 number, 1 special)
- ✅ Account locks after 5 failed attempts
- ✅ Unit tests pass (90%+ coverage)

---

### Story 1C: API Endpoints & Middleware (Week 2 - 4 days)

**Goal:** Expose auth APIs and protect routes

**Tasks:**
- [ ] Create `/api/v1/auth/*` endpoints (login, register, refresh, logout, me)
- [ ] Create `/api/v1/users/*` endpoints (CRUD, role fetch)
- [ ] Implement JWT middleware (validate tokens, set request.state.user)
- [ ] Implement RBAC middleware (permission checks)
- [ ] Implement rate limiting (SlowAPI, 5 attempts/15min)
- [ ] Add API versioning (move all endpoints to `/api/v1/*`)
- [ ] Write integration tests for auth flow

**Deliverables:**
- `src/api/v1/auth.py`
- `src/api/v1/users.py`
- `src/middleware/jwt_middleware.py`
- `src/middleware/rbac_middleware.py`
- `src/middleware/rate_limit.py`
- `tests/integration/test_auth_api.py`
- `tests/integration/test_rbac.py`

**Acceptance Criteria:**
- ✅ Login endpoint returns JWT token
- ✅ All endpoints versioned under `/api/v1/*`
- ✅ JWT middleware validates tokens and sets user context
- ✅ RBAC middleware enforces permissions (403 if insufficient)
- ✅ Rate limiting active (5 login attempts per 15min per IP)
- ✅ Auth events logged to `auth_audit_log`
- ✅ Integration tests pass (80%+ coverage)

---

### Story 2: Next.js Project Setup & Layout (Week 3 - 1 week)

**Goal:** Set up Next.js app with auth and base layout

**Tasks:**
- [ ] Initialize Next.js 14 project with TypeScript
- [ ] Configure Tailwind CSS with Liquid Glass theme (from design-tokens.json)
- [ ] Set up NextAuth v4 (or v5 if stable)
- [ ] Create root layout with providers (Auth, ReactQuery, Theme, Toast)
- [ ] Build dashboard shell (Header, Sidebar with grouped nav, Footer)
- [ ] Implement TenantSwitcher component (glassmorphic dropdown with search)
- [ ] Build login page and auth flow
- [ ] Create UI primitives (GlassCard, Button, Input, Select, Modal, Toast)
- [ ] Add NeuralNetwork background component
- [ ] Set up Storybook for component development
- [ ] Set up MSW for API mocking
- [ ] Implement authentication middleware
- [ ] Write component tests

**Deliverables:**
- `nextjs-ui/` (complete project structure)
- `nextjs-ui/src/lib/auth.ts` (NextAuth config)
- `nextjs-ui/src/components/layout/*` (Header, Sidebar, TenantSwitcher)
- `nextjs-ui/src/components/ui/*` (10+ primitive components)
- `nextjs-ui/src/styles/liquid-glass.css`
- `nextjs-ui/.storybook/` (Storybook config)
- `nextjs-ui/src/mocks/` (MSW handlers)
- `nextjs-ui/src/components/**/*.stories.tsx` (Storybook stories)
- `nextjs-ui/src/components/**/*.test.tsx` (Component tests)

**Acceptance Criteria:**
- ✅ Next.js app runs locally (`npm run dev`)
- ✅ Login page uses NextAuth
- ✅ Dashboard layout renders with grouped navigation (4 categories)
- ✅ Tenant switcher works (fetches tenants, switches context)
- ✅ Liquid Glass design applied (backdrop-filter with fallbacks)
- ✅ Dark mode toggle switches theme
- ✅ All UI primitives have Storybook stories
- ✅ MSW mocks all API endpoints
- ✅ Component tests pass (70%+ coverage)
- ✅ Reduced motion mode works (respects prefers-reduced-motion)

---

### Story 3: Core Pages - Monitoring (Week 4 - 1 week)

**Goal:** Build dashboard and monitoring pages

**Tasks:**
- [ ] Build Dashboard page (metrics cards, performance chart, activity feed)
- [ ] Build Agent Performance page (metrics table, trend charts)
- [ ] Build LLM Costs page (cost summary, daily trend, token breakdown)
- [ ] Build Workers page (Celery worker status, task counts)
- [ ] Integrate Recharts for all charts
- [ ] Implement SWR/React Query for data fetching
- [ ] Add loading states (skeleton screens)
- [ ] Add error boundaries
- [ ] Implement role-based UI (hide charts if no permission)
- [ ] Write page tests

**Deliverables:**
- `nextjs-ui/src/app/(dashboard)/dashboard/page.tsx`
- `nextjs-ui/src/app/(dashboard)/performance/page.tsx`
- `nextjs-ui/src/app/(dashboard)/costs/page.tsx`
- `nextjs-ui/src/app/(dashboard)/workers/page.tsx`
- `nextjs-ui/src/components/dashboard/*` (MetricCard, Chart, ActivityFeed)
- `nextjs-ui/src/app/(dashboard)/*/loading.tsx` (Loading states)
- `nextjs-ui/src/app/(dashboard)/*/error.tsx` (Error boundaries)

**Acceptance Criteria:**
- ✅ Dashboard displays 4 metric cards with live data
- ✅ Charts render correctly (Recharts)
- ✅ Data refreshes every 5 seconds (polling)
- ✅ Loading skeletons show during fetch
- ✅ Error boundaries catch and display errors
- ✅ Role-based UI hides features based on permissions
- ✅ Mobile responsive (bottom nav on mobile)
- ✅ Empty states show when no data

---

### Story 4: Core Pages - Configuration (Week 5 - 1 week)

**Goal:** Build configuration management pages

**Tasks:**
- [ ] Build Tenants page (list, detail, CRUD forms)
- [ ] Build Agents page (list, detail, CRUD forms, tool assignment)
- [ ] Build LLM Providers page (model list, add/edit/delete)
- [ ] Build MCP Servers page (server list, config forms, test connection)
- [ ] Implement data tables with sorting/filtering (TanStack Table)
- [ ] Add form validation (React Hook Form + Zod)
- [ ] Implement optimistic UI updates
- [ ] Write page tests

**Deliverables:**
- `nextjs-ui/src/app/(dashboard)/tenants/page.tsx`
- `nextjs-ui/src/app/(dashboard)/tenants/[id]/page.tsx`
- `nextjs-ui/src/app/(dashboard)/agents/page.tsx`
- `nextjs-ui/src/app/(dashboard)/agents/[id]/page.tsx`
- `nextjs-ui/src/app/(dashboard)/llm-providers/page.tsx`
- `nextjs-ui/src/app/(dashboard)/mcp-servers/page.tsx`
- `nextjs-ui/src/components/tenants/*` (TenantForm, TenantTable)
- `nextjs-ui/src/components/agents/*` (AgentForm, ToolAssignmentUI)

**Acceptance Criteria:**
- ✅ All CRUD operations work (create, read, update, delete)
- ✅ Forms validate with Zod schemas
- ✅ Tables support sorting, filtering, pagination
- ✅ Optimistic updates (UI updates before API response)
- ✅ Error handling with toast notifications
- ✅ Role-based access (admins can edit, viewers read-only)
- ✅ Mobile responsive

---

### Story 5: Operations & Tools Pages (Week 6 - 1 week)

**Goal:** Build operations and tools pages

**Tasks:**
- [ ] Build Queue Management page (pause/resume, queue depth)
- [ ] Build Execution History page (list with filters, detail view)
- [ ] Build Audit Logs page (auth + general audit logs)
- [ ] Build Plugins page (plugin list, config forms, test connection)
- [ ] Build System Prompts page (template editor, variable substitution)
- [ ] Build Add Tool page (OpenAPI spec upload, validation)
- [ ] Implement agent testing sandbox UI
- [ ] Write page tests

**Deliverables:**
- `nextjs-ui/src/app/(dashboard)/operations/page.tsx`
- `nextjs-ui/src/app/(dashboard)/execution-history/page.tsx`
- `nextjs-ui/src/app/(dashboard)/audit-logs/page.tsx`
- `nextjs-ui/src/app/(dashboard)/plugins/page.tsx`
- `nextjs-ui/src/app/(dashboard)/prompts/page.tsx`
- `nextjs-ui/src/app/(dashboard)/tools/page.tsx`
- `nextjs-ui/src/app/(dashboard)/agents/[id]/test/page.tsx`

**Acceptance Criteria:**
- ✅ Queue can be paused/resumed
- ✅ Execution history displays with filters (date, status, agent)
- ✅ Audit logs show all CRUD operations
- ✅ Plugins can be configured and tested
- ✅ System prompts can be edited with preview
- ✅ Tools can be uploaded (OpenAPI spec validation)
- ✅ Agent testing sandbox executes tests and shows results
- ✅ Role-based access enforced

---

### Story 6: Polish & User Experience (Week 7 - 1 week)

**Goal:** Refine UX, add feedback widget, optimize performance

**Tasks:**
- [ ] Add feedback widget (floating button, sentiment + comment)
- [ ] Implement keyboard shortcuts (Cmd+K search, Cmd+D dark mode, ? for help)
- [ ] Add breadcrumbs navigation
- [ ] Improve loading states (progress bars, spinners)
- [ ] Add confirmation dialogs for destructive actions
- [ ] Implement toast notification system
- [ ] Optimize bundle size (code splitting, lazy loading)
- [ ] Add favicon, meta tags, Open Graph tags
- [ ] Implement 404 and 500 error pages
- [ ] Test mobile experience on real devices
- [ ] Write E2E tests (critical user flows)

**Deliverables:**
- `nextjs-ui/src/components/layout/FeedbackWidget.tsx`
- `nextjs-ui/src/components/layout/KeyboardShortcuts.tsx`
- `nextjs-ui/src/components/layout/Breadcrumbs.tsx`
- `nextjs-ui/src/components/ui/ConfirmDialog.tsx`
- `nextjs-ui/src/app/not-found.tsx`
- `nextjs-ui/src/app/error.tsx`
- `nextjs-ui/e2e/*.spec.ts` (Playwright tests)

**Acceptance Criteria:**
- ✅ Feedback widget works (submits to backend)
- ✅ Keyboard shortcuts functional (Cmd+K, Cmd+D, ?)
- ✅ Breadcrumbs show current location
- ✅ Confirmation dialogs prevent accidental deletions
- ✅ Toast notifications for all actions
- ✅ Bundle size < 300KB gzipped
- ✅ Lighthouse score 90+ (all categories)
- ✅ E2E tests pass (login, create agent, test agent, logout)
- ✅ Mobile experience tested on iPhone and Android

---

### Story 7: Documentation & Training (Week 8 - 3 days)

**Goal:** Create all user-facing documentation

**Tasks:**
- [ ] Write Quick Start Guide (1-page PDF)
- [ ] Create video walkthrough (5 minutes, Loom)
- [ ] Write migration guide (Streamlit → Next.js)
- [ ] Create changelog (features, improvements, breaking changes)
- [ ] Generate API documentation (Redocly from OpenAPI schema)
- [ ] Write runbooks (login issues, performance, data sync)
- [ ] Schedule live demo (30-minute Zoom session)
- [ ] Send pre-launch communication to users

**Deliverables:**
- `docs/quick-start-guide.pdf`
- `docs/video-walkthrough.mp4` (or Loom link)
- `docs/migration-guide.md`
- `docs/changelog.md`
- `docs/api-docs.html` (Redocly)
- `docs/runbooks/*.md` (3 runbooks)
- Email template for launch announcement

**Acceptance Criteria:**
- ✅ Quick start guide covers login, navigation, key features
- ✅ Video walkthrough demonstrates core workflows
- ✅ Migration guide maps all Streamlit pages to Next.js
- ✅ Changelog lists all new features and changes
- ✅ API docs generated and hosted
- ✅ Runbooks cover 3 common issues
- ✅ Live demo scheduled and announced

---

### Story 8: Testing, Deployment & Rollout (Week 9-10 - 2 weeks)

**Goal:** Comprehensive testing, staging deployment, phased rollout

**Tasks:**
- [ ] Run load testing (k6, 100 concurrent users)
- [ ] Fix performance bottlenecks identified
- [ ] Run accessibility audit (Lighthouse, axe DevTools)
- [ ] Fix accessibility issues (keyboard nav, ARIA labels, contrast)
- [ ] Test cross-browser (Chrome, Firefox, Safari, Edge)
- [ ] Build production Docker image
- [ ] Deploy to staging environment
- [ ] Run smoke tests on staging
- [ ] **Phase 1:** Alpha rollout (3 power users, 1 week)
- [ ] Collect alpha feedback, fix bugs
- [ ] **Phase 2:** Beta rollout (10 users, 1 week)
- [ ] Collect beta feedback, fix bugs
- [ ] **Phase 3:** General availability (all users)
- [ ] Monitor metrics (NPS, login rate, error rate)
- [ ] Collect post-launch feedback via widget
- [ ] **Phase 4:** Decommission Streamlit (2 weeks after GA)

**Deliverables:**
- `k6-load-test.js` (load test script)
- Load test results report
- Accessibility audit report
- Docker image for Next.js UI
- Deployment playbook
- Rollout metrics dashboard
- Post-launch feedback summary

**Acceptance Criteria:**
- ✅ Load test passes (p95 < 500ms, error rate < 1%)
- ✅ Lighthouse accessibility score 90+
- ✅ All cross-browser issues fixed
- ✅ Docker image builds successfully
- ✅ Staging deployment successful
- ✅ Alpha: 3 users test for 1 week, NPS 7+
- ✅ Beta: 10 users test for 1 week, 80% prefer Next.js
- ✅ GA: 90% daily login rate, NPS 8+
- ✅ Streamlit decommissioned after 2 weeks

---

### Story 8.5: Security Testing (NEW - Week 10 - 2 days)

**Goal:** Validate security posture before GA launch

**Tasks:**
- [ ] Run OWASP ZAP automated scan
- [ ] Manual penetration testing (auth bypass attempts)
- [ ] Test SQL injection in all inputs
- [ ] Test XSS in all text fields
- [ ] Test IDOR (access other tenant's data)
- [ ] Test JWT token tampering
- [ ] Test rate limiting effectiveness
- [ ] Test RBAC enforcement (permission bypass attempts)
- [ ] Document findings and fix critical vulnerabilities
- [ ] Re-test after fixes

**Deliverables:**
- `docs/security-test-report.html`
- `docs/security-findings.md`
- Fixed vulnerabilities (if any)

**Acceptance Criteria:**
- ✅ OWASP ZAP scan completes (no high-severity issues)
- ✅ All auth endpoints rate-limited
- ✅ RBAC enforced (no permission bypass possible)
- ✅ XSS/SQL injection attempts blocked
- ✅ JWT tokens cannot be tampered
- ✅ Users cannot access other tenants' data
- ✅ All critical findings resolved

---

## 10. Success Metrics & Monitoring (NEW)

**Defined in Story 8, tracked for 4 weeks post-launch:**

### Leading Indicators (Track Daily)

| Metric | Target | Current (Track) | Status |
|--------|--------|-----------------|--------|
| Daily Active Users | 90% of team | TBD | 🟡 Tracking |
| Pages per Session | 5+ pages | TBD | 🟡 Tracking |
| Session Duration | 10+ minutes | TBD | 🟡 Tracking |
| Error Rate | < 1% | TBD | 🟡 Tracking |
| Page Load Time (p95) | < 2 seconds | TBD | 🟡 Tracking |
| API Response Time (p95) | < 500ms | TBD | 🟡 Tracking |

### Lagging Indicators (Track Weekly)

| Metric | Target | Week 1 | Week 2 | Week 4 | Status |
|--------|--------|--------|--------|--------|--------|
| NPS Score | 8+ | TBD | TBD | TBD | 🟡 Tracking |
| Feature Adoption | 80% | TBD | TBD | TBD | 🟡 Tracking |
| Support Tickets | < 5/month | TBD | TBD | TBD | 🟡 Tracking |
| User Preference | 80% prefer Next.js | TBD | TBD | TBD | 🟡 Tracking |

### How to Track

**Daily Metrics (Next.js Analytics):**
```typescript
// lib/analytics.ts
import { useEffect } from 'react';
import { usePathname } from 'next/navigation';

export function usePageView() {
  const pathname = usePathname();

  useEffect(() => {
    // Track page view
    fetch('/api/v1/analytics/pageview', {
      method: 'POST',
      body: JSON.stringify({ page: pathname }),
    });
  }, [pathname]);
}
```

**Weekly Survey (In-App):**
```typescript
// Show NPS survey after 2 weeks of usage
useEffect(() => {
  const accountAge = user.created_at;
  const twoWeeksAgo = new Date(Date.now() - 14 * 24 * 60 * 60 * 1000);

  if (accountAge < twoWeeksAgo && !user.nps_survey_completed) {
    // Show NPS modal
    setShowNPSModal(true);
  }
}, [user]);
```

---

## 11. Timeline Summary

**Total Duration: 10-12 weeks**

| Week | Story | Duration | Deliverables |
|------|-------|----------|--------------|
| Pre-1 | Story 0: User Research & Design | 5 days | Research report, Figma, ADRs |
| 1 | Story 1A: Database & Auth Foundation | 3 days | DB models, migrations, seed scripts |
| 1 | Story 1B: Auth Service & JWT | 3 days | Auth/User services, tests |
| 2 | Story 1C: API Endpoints & Middleware | 4 days | Auth APIs, JWT/RBAC middleware |
| 3 | Story 2: Next.js Setup & Layout | 1 week | Project setup, layout, UI primitives |
| 4 | Story 3: Core Pages - Monitoring | 1 week | Dashboard, performance, costs, workers |
| 5 | Story 4: Core Pages - Configuration | 1 week | Tenants, agents, LLM, MCP pages |
| 6 | Story 5: Operations & Tools | 1 week | Queue, history, plugins, prompts, tools |
| 7 | Story 6: Polish & UX | 1 week | Feedback, shortcuts, optimization |
| 8 | Story 7: Documentation | 3 days | Guides, videos, runbooks |
| 9-10 | Story 8: Testing & Rollout | 2 weeks | Load/security tests, phased rollout |
| 10 | Story 8.5: Security Testing | 2 days | OWASP ZAP, penetration testing |

**Critical Path:**
Story 0 → Story 1A → Story 1B → Story 1C → Story 2 (must be sequential)

**Parallel Work Opportunities:**
- Stories 3, 4, 5 can be worked on in parallel (different pages)
- Frontend stories (2-6) can overlap with backend stories (1A-1C) if 2 developers
- Story 7 (docs) can be written during Story 6 (polish)

**Buffer Time:**
- 2 weeks built into estimate (6 weeks realistic → 10 weeks planned)
- Accounts for: bug fixes, team feedback, unexpected complexity

---

## 12. Risk Assessment & Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Users resist new UI | Medium | High | User research, phased rollout, fallback to Streamlit |
| Timeline slips to 14+ weeks | High | Medium | Buffer built in, parallel work, scope flexibility |
| Auth bugs in production | Low | Critical | Security testing, beta period, rollback plan |
| Performance issues (100+ users) | Medium | High | Load testing before GA, monitoring, optimization |
| NextAuth beta breaks | Medium | High | Check for stable v5, consider v4 or Lucia Auth |
| JWT token bloat | **FIXED** | N/A | Roles on-demand, lean JWT (v2 architecture) |
| Mobile experience poor | Medium | Medium | Test on real devices, user feedback in beta |
| Glassmorphism janky | Medium | Low | Reduced motion mode, performance budget |
| Integration with FastAPI breaks | Low | High | API versioning, integration tests, staging env |
| Users lose data during migration | Low | Critical | Backup/restore tested, rollback plan |

---

## 13. Open Questions for Ravi

**Please clarify these before starting Story 1:**

1. **User Base:**
   - How many total users will use this system?
   - Are MSP technicians also users, or only internal ops team?
   - If technicians are users, what role should they have?

2. **Existing Users:**
   - Are there existing users in K8s Ingress basic auth?
   - If yes, how many? Do we need to migrate them?

3. **Auth.js Version:**
   - Should we wait for NextAuth v5 stable, or use v4 stable?
   - Alternative: Use Lucia Auth (lightweight, fully stable)?

4. **Deployment Environment:**
   - Will Next.js be deployed on Render.com (same as FastAPI)?
   - Or different platform (Vercel, AWS, etc.)?

5. **Redis Redundancy:**
   - Is Redis currently a single instance or clustered?
   - Should we set up Redis Sentinel for HA?

6. **Success Metrics:**
   - What's the current Streamlit usage? (DAU, session duration)
   - This will be our baseline for comparison

7. **Budget & Resources:**
   - Is this a 1-person project or team?
   - If team, how many frontend vs backend developers?

8. **Launch Date:**
   - Hard deadline or flexible?
   - If hard deadline, we may need to descope (e.g., defer Story 5 tools pages)

---

## 14. Summary of Changes from v1 → v2

**Major Improvements:**

1. ✅ **Timeline Realistic:** 6 weeks → 10-12 weeks
2. ✅ **Story Split:** 6 stories → 8 stories (Story 1 split, security added)
3. ✅ **JWT Architecture Fixed:** Roles on-demand, not in token (prevents bloat)
4. ✅ **API Versioning:** All endpoints under `/api/v1/*`
5. ✅ **Auth.js Decision:** Use stable v4, check v5 status
6. ✅ **User Research:** Added as Story 0 (mandatory pre-work)
7. ✅ **Rate Limiting:** Specified (SlowAPI, 5 attempts/15min)
8. ✅ **Navigation:** Grouped 14 pages into 4 categories
9. ✅ **Performance:** Reduced motion mode, load testing (k6)
10. ✅ **Security:** Dedicated security testing story (OWASP ZAP)
11. ✅ **Phased Rollout:** Alpha → Beta → GA over 3 weeks
12. ✅ **User Training:** Videos, guides, live demo
13. ✅ **Feedback Collection:** In-app feedback widget
14. ✅ **Success Metrics:** Specific KPIs (NPS 8+, 90% DAU, etc.)
15. ✅ **Compliance:** Password policy, account lockout, audit logs

**Deferred to v2:**
- WebSocket real-time updates (polling for MVP)
- i18n (English only for MVP, but structured for future)
- White-labeling per tenant
- Advanced analytics/reporting
- Mobile native apps

---

## 15. Next Steps

**After tech-spec approval:**

1. **Generate Epic & Stories:**
   - Create `docs/epics-nextjs-ui-migration.md`
   - Create 8 story files in `docs/stories/`
   - Story template: Goal, Tasks, AC, Deliverables, Tests

2. **Set Up Project Tracking:**
   - Create GitHub project board (or Jira)
   - Add all 8 stories as issues
   - Assign to team members
   - Set milestones

3. **Kick Off Story 0:**
   - Schedule user interviews (5-8 users, 1 hour each)
   - Create Figma account and project
   - Start ADR documents

4. **Weekly Standups:**
   - Every Monday: Review progress, blockers
   - Every Friday: Demo completed stories
   - Ad-hoc: Pair programming, code reviews

**Let's build something amazing! 🚀**

---

**Tech-Spec v2.0 Complete!**

This document incorporates all 25 action items from the team retrospective and provides a comprehensive roadmap for the Next.js UI migration with Liquid Glass design and RBAC.

**Approved by:**
- ✅ Winston (Architect) - Architecture reviewed and approved
- ✅ Sally (UX Designer) - UX/design validated
- ✅ Amelia (Developer) - Implementation approach confirmed
- ✅ Murat (Test Architect) - Testing strategy validated
- ✅ John (Product Manager) - Product requirements approved
- ✅ Mary (Business Analyst) - Requirements and compliance validated
- ✅ Paige (Technical Writer) - Documentation plan approved
- ✅ Saif (Visual Design Expert) - Design system validated
- ✅ Bob (Scrum Master) - Story breakdown and timeline confirmed

**Pending:**
- ⏳ Ravi - Final approval and answer to open questions
