# Technical Specification: Next.js UI Migration with Liquid Glass Design & RBAC

**Project:** AI Agents Platform
**Date:** 2025-01-17
**Author:** Bob (Scrum Master) with Ravi
**Type:** Brownfield - UI Migration
**Story Count:** 6 stories

---

## 1. Context

### 1.1 Loaded Documents Summary

**Documents Available:**
- ✅ Technical Research: Queue & Workflow Orchestration (Redis + Celery validation)
- ✅ Project Structure: Brownfield FastAPI application with Streamlit UI
- ✅ SuperDesign Mockups: 3 Liquid Glass dashboard iterations created

**Project Type:**
Brownfield - Migrating existing Streamlit admin UI to production-ready Next.js application

**Existing Stack:**
- **Backend:** FastAPI 0.104+ with Python 3.12
- **Database:** PostgreSQL with AsyncPG + SQLAlchemy 2.0
- **Queue:** Redis 5.0 + Celery 5.3
- **Current UI:** Streamlit 1.44 (development/internal only)
- **Observability:** OpenTelemetry + Prometheus

### 1.2 Project Stack Summary

**Backend Stack (Existing - Python 3.12):**
```python
# Core Framework
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
pydantic>=2.5.0

# Database
sqlalchemy[asyncio]>=2.0.23
alembic>=1.12.1
asyncpg>=0.29.0

# Queue & Workers
redis>=5.0.1
celery[redis]>=5.3.4

# AI/LLM
langgraph>=0.6.0
langchain>=0.3.0
langchain-openai>=0.2.0
openai>=1.3.0

# Monitoring
prometheus-client>=0.19.0
opentelemetry-api>=1.20.0
opentelemetry-sdk>=1.20.0
```

**Frontend Stack (NEW - To Be Created):**
```json
{
  "dependencies": {
    "next": "14.2.15",
    "react": "18.3.1",
    "react-dom": "18.3.1",
    "next-auth": "5.0.0-beta.25",
    "@auth/core": "0.37.2",
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
    "framer-motion": "11.11.17"
  },
  "devDependencies": {
    "@types/node": "22.9.0",
    "@types/react": "18.3.12",
    "@types/react-dom": "18.3.1",
    "eslint": "9.14.0",
    "eslint-config-next": "14.2.15",
    "prettier": "3.3.3",
    "autoprefixer": "10.4.20",
    "postcss": "8.4.47"
  }
}
```

**Node.js Version:** 20.x LTS (detected from existing package.json engines requirement)

### 1.3 Existing Structure Summary

**Current Streamlit Application Structure:**
```
src/admin/
├── app.py                          # Main Streamlit entry point
├── pages/
│   ├── 1_Dashboard.py             # System metrics, performance trends
│   ├── 2_Tenants.py               # Tenant CRUD, detail views
│   ├── 3_Plugin_Management.py     # Plugin config, testing
│   ├── 4_History.py               # Enhancement history viewer
│   ├── 5_Agent_Management.py      # Agent CRUD + MCP tool discovery
│   ├── 6_LLM_Providers.py         # LiteLLM model management
│   ├── 7_Operations.py            # Queue ops, audit logs
│   ├── 8_Workers.py               # Celery worker monitoring
│   ├── 9_System_Prompt_Editor.py  # Template editor
│   ├── 10_Add_Tool.py             # Tool upload (OpenAPI)
│   ├── 11_Execution_History.py    # Execution logs
│   ├── 12_MCP_Servers.py          # MCP server configuration
│   ├── 07_LLM_Costs.py           # Cost dashboard
│   └── 08_Agent_Performance.py    # Performance metrics
├── utils/                          # 30+ helper modules
│   ├── agent_helpers.py
│   ├── tenant_helpers.py
│   ├── mcp_ui_helpers.py
│   └── ...
└── components/                     # Reusable Streamlit components
    ├── agent_forms.py
    └── plugin_config_form.py
```

**FastAPI Backend Structure:**
```
src/
├── main.py                        # FastAPI app entry
├── config.py                      # Settings (Pydantic Settings)
├── api/                           # REST API routes
│   ├── agents.py
│   ├── tenants.py
│   ├── plugins_routes.py
│   ├── mcp_servers.py
│   ├── webhooks.py
│   ├── dependencies.py           # Tenant extraction, RLS
│   └── admin/                    # Admin-only endpoints
│       └── tenants.py
├── database/                      # SQLAlchemy models
│   ├── models.py                 # All DB models
│   ├── session.py                # Async session management
│   └── tenant_context.py         # RLS context setting
├── services/                      # Business logic
│   ├── agent_service.py
│   ├── tenant_service.py
│   ├── mcp_server_service.py
│   └── ...
└── workers/                       # Celery tasks
    ├── celery_app.py
    └── tasks.py
```

**Key Patterns in Existing Code:**
1. **Async/Await:** All database operations use `async/await` with AsyncPG
2. **Dependency Injection:** FastAPI's `Depends()` for services, DB sessions, tenant extraction
3. **Row-Level Security (RLS):** PostgreSQL RLS already implemented, tenant context set per request
4. **Multi-tenant:** `tenant_id` extraction via `get_tenant_id()` dependency
5. **Error Handling:** Custom exceptions in `src/exceptions.py`, HTTPException for API errors
6. **Logging:** Loguru for structured logging
7. **Validation:** Pydantic v2 models for all API requests/responses

---

## 2. The Change

### 2.1 Problem Statement

**Current Situation:**
The AI Agents platform currently uses Streamlit for its admin UI, which was perfect for rapid development but has limitations for production use:

1. **Not Production-Ready:** Streamlit is designed for data apps/dashboards, not full-featured admin UIs
2. **Limited Customization:** Hard to implement custom UI/UX patterns and Liquid Glass design
3. **No Built-in Auth:** Current implementation relies on K8s Ingress basic auth (no RBAC)
4. **Performance:** Full page reloads on every interaction, not ideal for real-time dashboards
5. **Mobile Experience:** Not responsive, difficult to use on tablets/phones
6. **Developer Experience:** Hard to test, no component reusability

**Impact:**
- Internal operations teams find the UI "too basic" and want a "feature-rich, futuristic" experience
- No role-based access control means all users have full admin privileges (security risk)
- Difficult to onboard new clients due to unprofessional UI appearance
- Cannot support mobile field technicians who need dashboard access on the go

### 2.2 Solution Overview

**Proposed Solution:**
Migrate from Streamlit to a modern Next.js 14 application with:

1. **Next.js 14 with App Router:** Modern React framework with SSR, RSC, and excellent DX
2. **Apple Liquid Glass Design:** Sophisticated glassmorphic UI with translucent materials, backdrop blur, and depth
3. **Auth.js (NextAuth v5) + RBAC:** Proper authentication with role-based access control
4. **FastAPI Backend Integration:** Use existing FastAPI REST API (no backend changes required)
5. **Tailwind CSS + Framer Motion:** Utility-first styling with smooth animations
6. **Zustand for State:** Lightweight state management for tenant switching and user context
7. **Feature Parity:** All 14 existing Streamlit pages migrated to Next.js
8. **Enhanced UX:** Real-time updates, optimistic UI, responsive design, keyboard shortcuts

**Key Design Decisions:**
- **SuperDesign Mockup #3 (Light Neural Network) as Base:** Tenant switcher already integrated, professional look
- **Dark Mode Toggle:** Steal particle system sophistication from Mockup #4
- **Mobile-First:** Responsive breakpoints for tablet (768px), desktop (1024px), wide (1440px)
- **Accessibility:** WCAG 2.1 AA compliance (keyboard nav, screen reader support, color contrast)

### 2.3 Change Type

**Category:** Frontend Migration + Authentication Implementation

**Scope:**
- **IN SCOPE:** Complete UI replacement, authentication/authorization, all existing features
- **OUT OF SCOPE:** Backend API changes, database schema changes (except auth tables), business logic modifications

### 2.4 Scope - What's IN

**Feature Parity with Streamlit:**
1. ✅ All 14 existing pages (Dashboard, Tenants, Agents, Plugins, Operations, etc.)
2. ✅ Real-time metrics and dashboards
3. ✅ CRUD operations for all entities
4. ✅ Complex forms (agent config, plugin setup, MCP servers)
5. ✅ Data tables with sorting, filtering, pagination
6. ✅ File uploads (OpenAPI specs, tool definitions)
7. ✅ Testing tools (plugin connection tests, agent sandbox)
8. ✅ Audit logs and execution history viewers

**New Features:**
1. ✅ Authentication (Auth.js with email/password + OAuth providers)
2. ✅ Role-Based Access Control (5 roles: super_admin, tenant_admin, operator, developer, viewer)
3. ✅ Tenant switcher in header (glassmorphic dropdown with active state)
4. ✅ Dark mode toggle
5. ✅ Responsive mobile layout
6. ✅ Keyboard shortcuts for common actions
7. ✅ Toast notifications for user feedback
8. ✅ Loading states with skeleton screens
9. ✅ Optimistic UI updates for better UX

**Design System:**
1. ✅ Liquid Glass components (cards, modals, dropdowns)
2. ✅ Neural network animated background (from Mockup #3)
3. ✅ Particle system for dark mode (from Mockup #4)
4. ✅ Color-coded metrics (purple, cyan, green, orange)
5. ✅ Smooth transitions (300ms cubic-bezier)
6. ✅ Glassmorphic effects (backdrop-filter: blur(32px) saturate(180%))

### 2.5 Scope - What's OUT

**Explicitly NOT Included:**
1. ❌ Changes to FastAPI backend routes (use existing APIs as-is)
2. ❌ Database schema changes beyond auth tables (existing models stay)
3. ❌ Celery worker modifications
4. ❌ LangGraph workflow changes
5. ❌ Plugin system refactoring
6. ❌ Multi-language support (English only for MVP)
7. ❌ Advanced analytics/reporting (beyond existing dashboards)
8. ❌ White-labeling/theming per tenant (single global design)
9. ❌ Mobile native apps (responsive web only)
10. ❌ WebSocket real-time updates (poll-based for MVP, can add later)

---

## 3. Implementation Details

### 3.1 Source Tree Changes

**NEW Next.js Application Structure:**
```
nextjs-ui/                          # NEW - Root directory for Next.js app
├── package.json                    # CREATE - Dependencies defined above
├── tsconfig.json                   # CREATE - TypeScript config (strict mode)
├── next.config.js                  # CREATE - Next.js configuration
├── tailwind.config.ts              # CREATE - Tailwind + Liquid Glass theme
├── postcss.config.js               # CREATE - PostCSS for Tailwind
├── .env.local                      # CREATE - Environment variables
├── .eslintrc.json                  # CREATE - ESLint config (Next.js defaults)
├── .prettierrc                     # CREATE - Code formatting rules
├── public/                         # CREATE - Static assets
│   ├── logo.svg
│   ├── favicon.ico
│   └── robots.txt
├── src/                            # CREATE - Source code
│   ├── app/                        # CREATE - Next.js App Router
│   │   ├── layout.tsx              # Root layout with providers
│   │   ├── page.tsx                # Redirect to /dashboard
│   │   ├── (auth)/                 # Auth route group
│   │   │   ├── login/page.tsx      # Login page
│   │   │   └── register/page.tsx   # Registration (admin-only)
│   │   ├── (dashboard)/            # Protected dashboard group
│   │   │   ├── layout.tsx          # Dashboard shell (sidebar, header, tenant switcher)
│   │   │   ├── dashboard/page.tsx  # Main dashboard
│   │   │   ├── tenants/
│   │   │   │   ├── page.tsx        # Tenant list
│   │   │   │   └── [id]/page.tsx   # Tenant detail
│   │   │   ├── agents/
│   │   │   │   ├── page.tsx        # Agent list
│   │   │   │   ├── [id]/page.tsx   # Agent detail
│   │   │   │   └── [id]/test/page.tsx # Agent testing sandbox
│   │   │   ├── plugins/page.tsx    # Plugin management
│   │   │   ├── operations/page.tsx # Operations dashboard
│   │   │   ├── llm-providers/page.tsx
│   │   │   ├── costs/page.tsx
│   │   │   ├── performance/page.tsx
│   │   │   ├── mcp-servers/page.tsx
│   │   │   ├── execution-history/page.tsx
│   │   │   ├── workers/page.tsx
│   │   │   ├── prompts/page.tsx    # System prompt editor
│   │   │   └── tools/page.tsx      # Add tool (OpenAPI upload)
│   │   └── api/                    # Next.js API routes
│   │       └── auth/[...nextauth]/route.ts # Auth.js handler
│   ├── components/                 # CREATE - React components
│   │   ├── ui/                     # Reusable UI primitives
│   │   │   ├── GlassCard.tsx       # Glassmorphic card component
│   │   │   ├── Button.tsx          # Liquid Glass button
│   │   │   ├── Input.tsx           # Form inputs
│   │   │   ├── Select.tsx          # Dropdowns
│   │   │   ├── Modal.tsx           # Glass modal
│   │   │   ├── Table.tsx           # Data table with sorting/filtering
│   │   │   ├── Toast.tsx           # Notification system
│   │   │   └── ...
│   │   ├── layout/                 # Layout components
│   │   │   ├── Header.tsx          # Top bar with tenant switcher
│   │   │   ├── Sidebar.tsx         # Navigation sidebar
│   │   │   ├── TenantSwitcher.tsx  # Glassmorphic tenant dropdown
│   │   │   ├── ThemeToggle.tsx     # Dark/light mode toggle
│   │   │   └── UserMenu.tsx        # User profile dropdown
│   │   ├── dashboard/              # Dashboard-specific components
│   │   │   ├── MetricCard.tsx      # Color-coded metric display
│   │   │   ├── PerformanceChart.tsx # Recharts wrapper
│   │   │   ├── ActivityFeed.tsx    # Recent activity list
│   │   │   └── NeuralNetwork.tsx   # Animated background
│   │   ├── agents/                 # Agent management components
│   │   │   ├── AgentForm.tsx
│   │   │   ├── AgentTestPanel.tsx
│   │   │   └── ToolAssignmentUI.tsx
│   │   ├── tenants/                # Tenant components
│   │   │   ├── TenantForm.tsx
│   │   │   └── TenantDetailView.tsx
│   │   └── ...                     # Other domain components
│   ├── lib/                        # CREATE - Utilities and config
│   │   ├── auth.ts                 # Auth.js configuration
│   │   ├── api-client.ts           # Axios wrapper for FastAPI calls
│   │   ├── permissions.ts          # RBAC permission checks
│   │   ├── utils.ts                # Helper functions
│   │   └── constants.ts            # App constants
│   ├── hooks/                      # CREATE - Custom React hooks
│   │   ├── useAuth.ts              # Authentication state
│   │   ├── useTenant.ts            # Tenant context
│   │   ├── usePermissions.ts       # RBAC checks
│   │   ├── useApi.ts               # API fetching with SWR
│   │   └── useToast.ts             # Toast notifications
│   ├── store/                      # CREATE - Zustand stores
│   │   ├── auth-store.ts           # User session state
│   │   ├── tenant-store.ts         # Selected tenant state
│   │   └── ui-store.ts             # UI state (theme, sidebar)
│   ├── types/                      # CREATE - TypeScript types
│   │   ├── api.ts                  # API request/response types
│   │   ├── models.ts               # Domain models (User, Agent, Tenant, etc.)
│   │   └── auth.ts                 # Auth-related types
│   └── styles/                     # CREATE - Global styles
│       ├── globals.css             # Tailwind imports + custom CSS
│       └── liquid-glass.css        # Liquid Glass design tokens
└── middleware.ts                   # CREATE - Auth middleware for route protection
```

**Backend Changes (FastAPI):**
```
src/
├── database/
│   └── models.py                   # MODIFY - Add User, UserTenantRole, AuthAuditLog models
├── api/
│   ├── auth.py                     # CREATE - Login, register, JWT validation endpoints
│   ├── users.py                    # CREATE - User CRUD (admin-only)
│   └── dependencies.py             # MODIFY - Update get_tenant_id() to extract from JWT
├── services/
│   ├── auth_service.py             # CREATE - Password hashing, JWT generation
│   └── user_service.py             # CREATE - User management business logic
└── middleware/
    ├── jwt_middleware.py           # CREATE - Validate JWT tokens, set request.state.user
    └── rbac_middleware.py          # CREATE - Check permissions based on user role
```

**Database Migrations:**
```
alembic/versions/
└── YYYYMMDD_HHMM_add_auth_tables.py  # CREATE - Add users, user_tenant_roles, auth_audit_log tables
```

### 3.2 Technical Approach

**Architecture Pattern: Backend-for-Frontend (BFF) Variant**

The Next.js app will act as a pure frontend client that communicates directly with the existing FastAPI backend via REST APIs. No Next.js API routes will be used except for Auth.js authentication callbacks.

**Authentication Flow:**

```
1. User visits /login
2. Next.js displays login form
3. User submits credentials
4. Auth.js calls /api/auth/callback/credentials
5. Next.js API route calls FastAPI POST /api/auth/login
6. FastAPI validates credentials, returns JWT token + user data
7. Auth.js stores JWT in session cookie (httpOnly, secure)
8. User redirected to /dashboard
9. All subsequent API calls include JWT in Authorization header
10. FastAPI jwt_middleware validates JWT, extracts user_id, tenant_id, roles
11. FastAPI rbac_middleware checks permissions before route handler
12. Response returned to Next.js, rendered to user
```

**JWT Structure:**
```typescript
interface JWTPayload {
  sub: string;              // user_id (UUID)
  email: string;            // user email
  tenant_id: string;        // default tenant for user
  roles: {                  // Roles per tenant
    [tenant_id: string]: Role;
  };
  iat: number;              // Issued at (Unix timestamp)
  exp: number;              // Expiration (Unix timestamp, 7 days)
}
```

**RBAC Implementation:**

**Frontend (Next.js):**
```typescript
// hooks/usePermissions.ts
export function usePermissions() {
  const { user } = useAuth();
  const { selectedTenant } = useTenant();

  const can = (permission: Permission): boolean => {
    const role = user?.roles[selectedTenant];
    return PERMISSIONS[permission].includes(role);
  };

  return { can };
}

// Usage in components:
const { can } = usePermissions();
{can('agents:delete') && <DeleteButton />}
```

**Backend (FastAPI):**
```python
# middleware/rbac_middleware.py
def require_permission(permission: str):
    async def dependency(request: Request):
        user = request.state.user  # Set by jwt_middleware
        tenant_id = await get_tenant_id(request)

        role = await get_user_role(user.id, tenant_id)

        if not has_permission(role, permission):
            raise HTTPException(403, "Insufficient permissions")

        return user
    return Depends(dependency)

# Usage in routes:
@router.delete("/agents/{agent_id}")
async def delete_agent(
    agent_id: str,
    user: User = require_permission("agents:delete")
):
    ...
```

**State Management Strategy:**

1. **Server State (API data):** SWR for data fetching, caching, revalidation
2. **Client State (UI):** Zustand for tenant selection, theme, sidebar state
3. **Auth State:** Auth.js session (server-side), Zustand for client-side access
4. **Form State:** React Hook Form with Zod validation

**Styling Approach:**

1. **Tailwind CSS:** Utility-first for rapid development
2. **Custom Liquid Glass Theme:**
   ```ts
   // tailwind.config.ts
   theme: {
     extend: {
       colors: {
         'glass-bg': 'rgba(255, 255, 255, 0.75)',
         'glass-border': 'rgba(255, 255, 255, 1)',
         'accent-blue': '#3b82f6',
         'accent-purple': '#8b5cf6',
         'accent-green': '#10b981',
         'accent-orange': '#f59e0b',
       },
       backdropBlur: {
         'glass': '32px',
       },
     }
   }
   ```
3. **Framer Motion:** For glassmorphic card animations, page transitions
4. **CSS Modules:** For complex component-specific styles

### 3.3 Existing Patterns to Follow

**Backend Patterns (FastAPI - MUST CONFORM):**

1. **Async/Await Everywhere:**
   ```python
   # All DB operations use async
   async def get_agents(tenant_id: str, db: AsyncSession):
       result = await db.execute(select(Agent).where(Agent.tenant_id == tenant_id))
       return result.scalars().all()
   ```

2. **Dependency Injection:**
   ```python
   # Use Depends() for services, DB, tenant
   @router.get("/agents")
   async def list_agents(
       tenant_id: str = Depends(get_tenant_id),
       db: AsyncSession = Depends(get_tenant_db),
       agent_service: AgentService = Depends(get_agent_service)
   ):
       ...
   ```

3. **Pydantic Models for Validation:**
   ```python
   # Request/response models
   class AgentCreateRequest(BaseModel):
       name: str = Field(..., min_length=1, max_length=255)
       description: Optional[str] = None
       ...
   ```

4. **Error Handling:**
   ```python
   # Custom exceptions
   from src.exceptions import TenantNotFoundError

   if not tenant:
       raise TenantNotFoundError(tenant_id)

   # HTTPException for API errors
   raise HTTPException(status_code=404, detail="Agent not found")
   ```

5. **Logging with Loguru:**
   ```python
   from loguru import logger

   logger.info(f"Creating agent for tenant {tenant_id}")
   logger.error(f"Failed to create agent: {e}", exc_info=True)
   ```

**Frontend Patterns (Next.js - ESTABLISH NEW):**

1. **Server Components by Default:**
   ```typescript
   // app/dashboard/page.tsx
   export default async function DashboardPage() {
     // Fetch data in Server Component
     const metrics = await getMetrics();
     return <DashboardView metrics={metrics} />;
   }
   ```

2. **Client Components Only When Needed:**
   ```typescript
   'use client';  // Only for interactivity, useState, useEffect

   export function InteractiveChart({ data }: Props) {
     const [filter, setFilter] = useState('all');
     ...
   }
   ```

3. **Error Boundaries:**
   ```typescript
   // app/dashboard/error.tsx
   'use client';
   export default function Error({ error, reset }: ErrorPageProps) {
     return <ErrorDisplay error={error} onReset={reset} />;
   }
   ```

4. **Loading States:**
   ```typescript
   // app/dashboard/loading.tsx
   export default function Loading() {
     return <DashboardSkeleton />;
   }
   ```

5. **TypeScript Strict Mode:**
   ```typescript
   // Always type props, state, functions
   interface Props {
     agent: Agent;
     onUpdate: (agent: Agent) => Promise<void>;
   }
   ```

### 3.4 Integration Points

**FastAPI REST API Endpoints (Existing):**

All endpoints follow pattern: `https://api.example.com/api/{resource}`

**Authentication:**
- `POST /api/auth/login` - NEW - Login with email/password
- `POST /api/auth/refresh` - NEW - Refresh JWT token
- `POST /api/auth/logout` - NEW - Invalidate session
- `GET /api/auth/me` - NEW - Get current user info

**Tenants:**
- `GET /api/admin/tenants` - List all tenants (admin only)
- `POST /api/admin/tenants` - Create tenant
- `GET /api/admin/tenants/{id}` - Get tenant details
- `PUT /api/admin/tenants/{id}` - Update tenant
- `DELETE /api/admin/tenants/{id}` - Delete tenant

**Agents:**
- `GET /api/agents` - List agents for current tenant
- `POST /api/agents` - Create agent
- `GET /api/agents/{id}` - Get agent details
- `PUT /api/agents/{id}` - Update agent
- `DELETE /api/agents/{id}` - Delete agent
- `POST /api/agents/{id}/test` - Test agent in sandbox

**Dashboard Metrics:**
- `GET /api/metrics/summary` - Overall system metrics
- `GET /api/metrics/performance-trends` - Performance over time
- `GET /api/llm-costs/summary` - Cost summary
- `GET /api/llm-costs/daily-trend` - Daily cost trends

**(30+ more endpoints across plugins, operations, MCP servers, etc.)**

**External Dependencies:**
- **FastAPI Backend:** All API calls via HTTPS
- **PostgreSQL Database:** Accessed only via FastAPI (Next.js never touches DB directly)
- **Auth.js Providers:** Email/password (credentials provider) + OAuth (Google, GitHub) optional

### 3.5 Existing Code References

**Key Files to Reference:**

**For Understanding API Contracts:**
- `src/api/agents.py:20-150` - Agent CRUD endpoints, request/response models
- `src/api/admin/tenants.py:71-340` - Tenant management patterns
- `src/api/dependencies.py:23-86` - Tenant extraction logic (will adapt for JWT)
- `src/database/models.py:1-500` - All Pydantic models and table schemas

**For Understanding Business Logic:**
- `src/services/agent_service.py:1-300` - Agent operations
- `src/services/tenant_service.py:1-200` - Tenant operations
- `src/services/mcp_server_service.py:1-400` - MCP server management

**For Understanding Current UI Features:**
- `src/admin/pages/1_Dashboard.py:1-100` - Dashboard layout and metrics
- `src/admin/pages/5_Agent_Management.py:1-200` - Agent CRUD forms
- `src/admin/utils/agent_helpers.py:1-150` - Helper functions for UI
- `src/admin/utils/tenant_helpers.py:1-100` - Tenant dropdown logic

**For Understanding Data Models:**
- `src/database/models.py:Agent` - Agent model (name, tenant_id, config, tools)
- `src/database/models.py:Tenant` - Tenant model (name, api_keys, budget)
- `src/database/models.py:MCPServer` - MCP server model

### 3.6 Framework Dependencies

**Next.js & React Ecosystem:**
- `next@14.2.15` - React framework with App Router, SSR, RSC
- `react@18.3.1` - UI library
- `react-dom@18.3.1` - React DOM renderer
- `typescript@5.6.3` - Type safety

**Authentication:**
- `next-auth@5.0.0-beta.25` - Auth.js for authentication
- `@auth/core@0.37.2` - Core authentication logic
- `jose@5.9.6` - JWT signing/verification (included with next-auth)
- `bcryptjs@2.4.3` - Password hashing (backend)

**UI & Styling:**
- `tailwindcss@3.4.14` - Utility-first CSS framework
- `@tailwindcss/typography@0.5.15` - Typography plugin
- `@headlessui/react@2.2.0` - Unstyled accessible components
- `lucide-react@0.456.0` - Icon library (matches Streamlit lucide icons)
- `framer-motion@11.11.17` - Animation library for transitions
- `class-variance-authority@0.7.1` - Component variant management
- `clsx@2.1.1` - Conditional classNames utility
- `tailwind-merge@2.5.5` - Merge Tailwind classes

**Data Fetching & State:**
- `swr@2.2.5` - Data fetching, caching, revalidation
- `zustand@5.0.1` - Lightweight state management
- `axios@1.7.8` - HTTP client for FastAPI calls
- `react-hook-form@7.54.0` - Form state management
- `zod@3.23.8` - Schema validation

**Data Visualization:**
- `recharts@2.13.3` - Chart library (similar to Plotly in Streamlit)
- `@tanstack/react-table@8.20.5` - Headless table library

**Utilities:**
- `date-fns@4.1.0` - Date manipulation
- `lodash-es@4.17.21` - Utility functions
- `nanoid@5.0.9` - Unique ID generation

### 3.7 Internal Dependencies

**Internal Modules (Next.js):**
```typescript
// Authentication
import { auth, signIn, signOut } from '@/lib/auth';
import { useAuth } from '@/hooks/useAuth';
import { usePermissions } from '@/hooks/usePermissions';

// API Client
import { apiClient } from '@/lib/api-client';
import { useApi } from '@/hooks/useApi';

// Tenant Context
import { useTenant } from '@/hooks/useTenant';
import { TenantSwitcher } from '@/components/layout/TenantSwitcher';

// UI Components
import { GlassCard } from '@/components/ui/GlassCard';
import { Button } from '@/components/ui/Button';
import { Toast } from '@/components/ui/Toast';

// Stores
import { useAuthStore } from '@/store/auth-store';
import { useTenantStore } from '@/store/tenant-store';
import { useUIStore } from '@/store/ui-store';

// Types
import type { Agent, Tenant, User } from '@/types/models';
import type { APIResponse } from '@/types/api';
```

### 3.8 Configuration Changes

**Environment Variables (Next.js `.env.local`):**
```bash
# FastAPI Backend
NEXT_PUBLIC_API_URL=https://api.example.com
NEXT_PUBLIC_API_TIMEOUT=30000

# Auth.js
NEXTAUTH_URL=https://app.example.com
NEXTAUTH_SECRET=<generated-secret-32-chars>
AUTH_TRUST_HOST=true

# OAuth Providers (Optional)
GOOGLE_CLIENT_ID=<google-oauth-client-id>
GOOGLE_CLIENT_SECRET=<google-oauth-secret>
GITHUB_CLIENT_ID=<github-oauth-client-id>
GITHUB_CLIENT_SECRET=<github-oauth-secret>

# Feature Flags
NEXT_PUBLIC_ENABLE_OAUTH=false
NEXT_PUBLIC_ENABLE_DARK_MODE=true
NEXT_PUBLIC_ENABLE_MOBILE=true
```

**Environment Variables (FastAPI `.env` - ADD):**
```bash
# JWT Configuration
JWT_SECRET_KEY=<same-as-NEXTAUTH_SECRET>
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=10080  # 7 days

# CORS for Next.js
CORS_ORIGINS=https://app.example.com,http://localhost:3000

# Admin User (for initial setup)
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=<secure-password>
```

**Update FastAPI `src/config.py`:**
```python
class Settings(BaseSettings):
    # Existing settings...

    # JWT Configuration (NEW)
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 10080

    # CORS (NEW)
    cors_origins: list[str] = ["http://localhost:3000"]

    # Admin User (NEW)
    admin_email: str
    admin_password: str
```

**Update FastAPI `src/main.py` - Add CORS:**
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## 4. Development Context

### 4.1 Existing Conventions (Backend - MUST CONFORM)

**Code Style (Python):**
- **Formatter:** Black (line length: 100)
- **Linter:** Ruff (E, F, I, N, W rules)
- **Type Checker:** Mypy (strict mode)
- **Quotes:** Double quotes preferred
- **Indentation:** 4 spaces
- **Imports:** Sorted by Ruff (isort rules)

**Example:**
```python
# Good - Conforms to existing style
from typing import Optional

from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import Agent
from src.services.agent_service import AgentService


async def get_agent_by_id(
    agent_id: str,
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_tenant_db),
) -> Agent:
    """Get agent by ID with tenant validation."""
    agent = await db.get(Agent, agent_id)
    if not agent or agent.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent
```

**Testing Patterns (Pytest):**
- **Test Files:** `test_*.py` in `tests/` directory
- **Test Classes:** `TestClassName` (optional, prefer functions)
- **Test Functions:** `test_function_name_scenario()`
- **Markers:** `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.asyncio`
- **Fixtures:** Use fixtures for DB sessions, mock services
- **Coverage:** Aim for 80%+ on new code

**Example:**
```python
# tests/unit/test_agent_service.py
import pytest
from unittest.mock import AsyncMock

@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_agent_success(mock_db_session):
    """Test agent creation with valid data."""
    service = AgentService(mock_db_session)
    agent = await service.create_agent(
        tenant_id="test-tenant",
        name="Test Agent",
        config={"model": "gpt-4"}
    )
    assert agent.name == "Test Agent"
    assert agent.tenant_id == "test-tenant"
```

### 4.2 New Conventions (Frontend - ESTABLISH)

**Code Style (TypeScript):**
- **Formatter:** Prettier (semi: true, singleQuote: true, trailingComma: 'es5')
- **Linter:** ESLint (Next.js recommended + TypeScript strict)
- **Type Checker:** TypeScript (strict mode)
- **Quotes:** Single quotes
- **Indentation:** 2 spaces
- **File Naming:** kebab-case for files, PascalCase for components

**Example:**
```typescript
// Good - New frontend style
import { useState } from 'react';
import type { Agent } from '@/types/models';
import { Button } from '@/components/ui/Button';

interface Props {
  agent: Agent;
  onUpdate: (agent: Agent) => Promise<void>;
}

export function AgentCard({ agent, onUpdate }: Props) {
  const [isLoading, setIsLoading] = useState(false);

  const handleClick = async () => {
    setIsLoading(true);
    try {
      await onUpdate(agent);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="glass-card">
      <h3>{agent.name}</h3>
      <Button onClick={handleClick} disabled={isLoading}>
        Update
      </Button>
    </div>
  );
}
```

**Component Structure:**
```typescript
// 1. Imports (external, then internal)
// 2. Types/Interfaces
// 3. Component function
// 4. Exports (default export at bottom)
```

**Testing Patterns (Jest + React Testing Library):**
- **Test Files:** `*.test.tsx` next to component files
- **Test Functions:** `test('should do something', () => {...})`
- **Assertions:** `expect(element).toBeInTheDocument()`
- **User Events:** `await user.click(button)`
- **Mocks:** Mock API calls with MSW (Mock Service Worker)

---

## 5. Implementation Stack

**Complete Technology Stack:**

**Frontend:**
- Runtime: Node.js 20.x LTS
- Framework: Next.js 14.2.15 (App Router)
- Language: TypeScript 5.6.3 (strict mode)
- UI Library: React 18.3.1
- Styling: Tailwind CSS 3.4.14 + Framer Motion 11.11.17
- Components: Headless UI 2.2.0 + Lucide React 0.456.0
- State: Zustand 5.0.1 + SWR 2.2.5
- Forms: React Hook Form 7.54.0 + Zod 3.23.8
- Auth: Auth.js (NextAuth) 5.0.0-beta.25
- HTTP: Axios 1.7.8
- Charts: Recharts 2.13.3
- Testing: Jest 29.7.0 + React Testing Library 16.0.1
- E2E Testing: Playwright 1.48.2

**Backend (Existing + Additions):**
- Runtime: Python 3.12
- Framework: FastAPI 0.104+
- Database: PostgreSQL 15+ with AsyncPG 0.29
- ORM: SQLAlchemy 2.0 (async)
- Queue: Redis 5.0 + Celery 5.3
- Auth (NEW): python-jose 3.3.0 + passlib 1.7.4
- Validation: Pydantic 2.5+
- Testing: Pytest 7.4.3 + pytest-asyncio 0.21.1

**Infrastructure:**
- Deployment: Render.com (existing)
- Container: Docker (both Next.js and FastAPI)
- Orchestration: Kubernetes (existing for FastAPI)
- Monitoring: Prometheus + OpenTelemetry (existing)
- Logging: Loguru (backend) + Console (frontend dev)

---

## 6. Technical Details

### 6.1 Liquid Glass Design Implementation

**Core CSS Variables:**
```css
/* styles/liquid-glass.css */
:root {
  /* Light Mode */
  --glass-bg-light: rgba(255, 255, 255, 0.75);
  --glass-border-light: rgba(255, 255, 255, 1);
  --shadow-color-light: rgba(0, 0, 0, 0.1);

  /* Dark Mode */
  --glass-bg-dark: rgba(26, 26, 46, 0.75);
  --glass-border-dark: rgba(255, 255, 255, 0.1);
  --shadow-color-dark: rgba(0, 0, 0, 0.5);

  /* Accents */
  --accent-blue: #3b82f6;
  --accent-purple: #8b5cf6;
  --accent-green: #10b981;
  --accent-orange: #f59e0b;
}

.glass-card {
  background: var(--glass-bg-light);
  backdrop-filter: blur(32px) saturate(180%) brightness(1.1);
  -webkit-backdrop-filter: blur(32px) saturate(180%) brightness(1.1);
  border: 2px solid var(--glass-border-light);
  box-shadow:
    0 8px 32px var(--shadow-color-light),
    inset 0 1px 0 rgba(255, 255, 255, 1);
  border-radius: 24px;
  transition: all 300ms cubic-bezier(0.4, 0, 0.2, 1);
}

.glass-card:hover {
  transform: translateY(-2px);
  box-shadow:
    0 12px 48px var(--shadow-color-light),
    inset 0 1px 0 rgba(255, 255, 255, 1);
}

.dark .glass-card {
  background: var(--glass-bg-dark);
  border-color: var(--glass-border-dark);
  box-shadow:
    0 8px 32px var(--shadow-color-dark),
    inset 0 1px 0 rgba(255, 255, 255, 0.1);
}
```

**Neural Network Background (Light Mode):**
```typescript
// components/dashboard/NeuralNetwork.tsx
'use client';

import { useEffect, useRef } from 'react';

export function NeuralNetwork() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Create nodes and connections
    const nodes = Array.from({ length: 20 }, () => ({
      x: Math.random() * canvas.width,
      y: Math.random() * canvas.height,
      vx: (Math.random() - 0.5) * 0.5,
      vy: (Math.random() - 0.5) * 0.5,
    }));

    function animate() {
      if (!ctx || !canvas) return;

      ctx.clearRect(0, 0, canvas.width, canvas.height);

      // Update and draw nodes
      nodes.forEach(node => {
        node.x += node.vx;
        node.y += node.vy;

        // Bounce off edges
        if (node.x < 0 || node.x > canvas.width) node.vx *= -1;
        if (node.y < 0 || node.y > canvas.height) node.vy *= -1;

        // Draw node
        ctx.beginPath();
        ctx.arc(node.x, node.y, 4, 0, Math.PI * 2);
        ctx.fillStyle = 'rgba(139, 127, 255, 0.8)';
        ctx.fill();
      });

      // Draw connections
      nodes.forEach((node, i) => {
        nodes.slice(i + 1).forEach(other => {
          const dist = Math.hypot(node.x - other.x, node.y - other.y);
          if (dist < 150) {
            ctx.beginPath();
            ctx.moveTo(node.x, node.y);
            ctx.lineTo(other.x, other.y);
            ctx.strokeStyle = `rgba(139, 127, 255, ${0.2 * (1 - dist / 150)})`;
            ctx.lineWidth = 1;
            ctx.stroke();
          }
        });
      });

      requestAnimationFrame(animate);
    }

    animate();
  }, []);

  return (
    <canvas
      ref={canvasRef}
      className="fixed inset-0 opacity-40 pointer-events-none"
      width={1920}
      height={1080}
    />
  );
}
```

**Particle System (Dark Mode):**
Similar implementation with 40 particles, slower movement, glow effects

### 6.2 Authentication Implementation Details

**Password Hashing (Backend):**
```python
# services/auth_service.py
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)
```

**JWT Generation (Backend):**
```python
# services/auth_service.py
from jose import jwt
from datetime import datetime, timedelta

def create_access_token(user: User, roles: dict[str, str]) -> str:
    expire = datetime.utcnow() + timedelta(minutes=settings.jwt_access_token_expire_minutes)
    payload = {
        "sub": str(user.id),
        "email": user.email,
        "tenant_id": roles[next(iter(roles))],  # Default tenant
        "roles": roles,
        "iat": datetime.utcnow().timestamp(),
        "exp": expire.timestamp(),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
```

**JWT Validation (Backend Middleware):**
```python
# middleware/jwt_middleware.py
from fastapi import Request, HTTPException
from jose import jwt, JWTError

async def jwt_middleware(request: Request, call_next):
    # Skip auth routes
    if request.url.path.startswith("/api/auth/login"):
        return await call_next(request)

    # Extract token from Authorization header
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(401, "Missing or invalid Authorization header")

    token = auth_header.split(" ")[1]

    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm]
        )

        # Set user in request state
        request.state.user = {
            "id": payload["sub"],
            "email": payload["email"],
            "tenant_id": payload["tenant_id"],
            "roles": payload["roles"],
        }
    except JWTError:
        raise HTTPException(401, "Invalid or expired token")

    return await call_next(request)
```

**Auth.js Configuration (Frontend):**
```typescript
// lib/auth.ts
import NextAuth from 'next-auth';
import CredentialsProvider from 'next-auth/providers/credentials';
import axios from 'axios';

export const { handlers, signIn, signOut, auth } = NextAuth({
  providers: [
    CredentialsProvider({
      name: 'Credentials',
      credentials: {
        email: { label: 'Email', type: 'email' },
        password: { label: 'Password', type: 'password' },
      },
      async authorize(credentials) {
        try {
          const response = await axios.post(
            `${process.env.NEXT_PUBLIC_API_URL}/api/auth/login`,
            {
              email: credentials.email,
              password: credentials.password,
            }
          );

          if (response.data.token) {
            return {
              id: response.data.user.id,
              email: response.data.user.email,
              name: response.data.user.full_name,
              token: response.data.token,
              roles: response.data.user.roles,
            };
          }
        } catch (error) {
          return null;
        }
      },
    }),
  ],
  callbacks: {
    async jwt({ token, user }) {
      if (user) {
        token.id = user.id;
        token.token = user.token;
        token.roles = user.roles;
      }
      return token;
    },
    async session({ session, token }) {
      session.user.id = token.id;
      session.user.token = token.token;
      session.user.roles = token.roles;
      return session;
    },
  },
  pages: {
    signIn: '/login',
  },
  session: {
    strategy: 'jwt',
  },
});
```

### 6.3 Performance Optimization

**Server Components for Data Fetching:**
```typescript
// app/dashboard/page.tsx (Server Component)
import { auth } from '@/lib/auth';
import { getMetrics } from '@/lib/api-server';

export default async function DashboardPage() {
  const session = await auth();
  const metrics = await getMetrics(session.user.token);

  return <DashboardView metrics={metrics} />;
}
```

**Client Components for Interactivity:**
```typescript
// components/dashboard/MetricCard.tsx (Client Component)
'use client';

import { motion } from 'framer-motion';

export function MetricCard({ title, value, change }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="glass-card"
    >
      <h3>{title}</h3>
      <p className="text-4xl font-bold">{value}</p>
      <span className={change > 0 ? 'text-green-500' : 'text-red-500'}>
        {change > 0 ? '+' : ''}{change}%
      </span>
    </motion.div>
  );
}
```

**SWR for Data Caching:**
```typescript
// hooks/useAgents.ts
import useSWR from 'swr';
import { apiClient } from '@/lib/api-client';

export function useAgents(tenantId: string) {
  const { data, error, mutate } = useSWR(
    `/api/agents?tenant_id=${tenantId}`,
    apiClient.get,
    {
      revalidateOnFocus: false,
      revalidateOnReconnect: true,
      dedupingInterval: 5000,
    }
  );

  return {
    agents: data?.data || [],
    isLoading: !error && !data,
    isError: error,
    mutate,
  };
}
```

### 6.4 Security Considerations

**CSRF Protection:**
- Auth.js handles CSRF tokens automatically
- All POST/PUT/DELETE requests include CSRF token

**XSS Prevention:**
- React automatically escapes content
- Use `dangerouslySetInnerHTML` only for sanitized content
- Content Security Policy (CSP) headers in Next.js config

**Input Validation:**
- Zod schemas for all form inputs
- FastAPI Pydantic models validate API requests
- SQL injection prevented by SQLAlchemy (parameterized queries)

**Rate Limiting:**
- Implement rate limiting on FastAPI auth endpoints
- Use Redis for distributed rate limiting

**Audit Logging:**
- Log all authentication events (login, logout, password changes)
- Log all permission-denied attempts
- Store in `auth_audit_log` table

---

## 7. Development Setup

### 7.1 Prerequisites

**Required Software:**
- Node.js 20.x LTS
- Python 3.12
- PostgreSQL 15+
- Redis 7+
- Docker & Docker Compose (for local development)

### 7.2 Local Development Setup

**1. Clone Repository (if not already):**
```bash
cd /Users/ravi/Documents/nullBytes_Apps/Ai_Agents/AI\ Ops
```

**2. Backend Setup (FastAPI):**
```bash
# Create virtual environment
python3.12 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"

# Copy environment variables
cp .env.example .env
# Edit .env with your configuration

# Run database migrations
alembic upgrade head

# Start backend
uvicorn src.main:app --reload --port 8000
```

**3. Frontend Setup (Next.js):**
```bash
# Create Next.js app directory
mkdir nextjs-ui
cd nextjs-ui

# Initialize Next.js project
npx create-next-app@14.2.15 . --typescript --tailwind --app --import-alias "@/*"

# Install dependencies
npm install next-auth@beta @auth/core zustand swr axios recharts framer-motion @headlessui/react lucide-react zod react-hook-form

# Install dev dependencies
npm install -D @types/node @types/react @types/react-dom eslint eslint-config-next prettier

# Copy environment variables
cp .env.example .env.local
# Edit .env.local with your configuration

# Start development server
npm run dev
```

**4. Run Services (Docker Compose):**
```bash
# From project root
docker-compose up -d postgres redis

# Check services
docker-compose ps
```

**5. Verify Setup:**
```bash
# Backend health check
curl http://localhost:8000/health

# Frontend
# Open browser to http://localhost:3000
```

### 7.3 Running Tests

**Backend Tests:**
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/unit/test_auth_service.py

# Run with coverage
pytest --cov=src --cov-report=html

# Run integration tests only
pytest -m integration
```

**Frontend Tests:**
```bash
cd nextjs-ui

# Run unit tests
npm test

# Run tests in watch mode
npm test -- --watch

# Run with coverage
npm test -- --coverage

# Run E2E tests
npm run test:e2e
```

---

## 8. Implementation Guide

### 8.1 Setup Steps

**Before Starting Implementation:**

1. ✅ **Create feature branch:**
   ```bash
   git checkout -b feature/nextjs-ui-migration
   ```

2. ✅ **Verify development environment:**
   - Node.js 20.x installed: `node --version`
   - Python 3.12 installed: `python --version`
   - Docker running: `docker ps`
   - PostgreSQL accessible: `psql -h localhost -U postgres`
   - Redis accessible: `redis-cli ping`

3. ✅ **Review SuperDesign mockups:**
   - `/Users/ravi/Documents/nullBytes_Apps/Ai_Agents/.superdesign/design_iterations/ai_ops_dashboard_1_3.html`
   - Extract color schemes, component patterns, animations

4. ✅ **Set up project tracking:**
   - Create GitHub project board (or similar)
   - Add all 6 stories as issues
   - Set milestones for each sprint

### 8.2 Implementation Steps

**Story 1: Authentication Setup + RBAC (Week 1)**
1. Add database migrations for auth tables
2. Implement FastAPI auth endpoints (login, register, JWT validation)
3. Add JWT middleware and RBAC middleware
4. Create initial admin user via seed script
5. Write unit tests for auth service
6. Document API endpoints

**Story 2: Project Setup + Layout + Tenant Switcher (Week 1-2)**
1. Initialize Next.js project with TypeScript
2. Configure Tailwind CSS with Liquid Glass theme
3. Set up Auth.js with credentials provider
4. Create root layout with providers (Auth, Theme, Toast)
5. Build dashboard shell (Header, Sidebar, TenantSwitcher)
6. Implement authentication flow (login page, middleware)
7. Create UI primitives (GlassCard, Button, Input, etc.)
8. Add neural network background component
9. Test authentication and navigation

**Story 3: Core Pages (Dashboard, Tenants, Agents) (Week 2-3)**
1. Build Dashboard page with metrics cards
2. Integrate Recharts for performance charts
3. Create Tenants list and detail pages
4. Implement Agents CRUD with forms
5. Add agent testing sandbox UI
6. Implement role-based UI (hide/show based on permissions)
7. Write component tests

**Story 4: Management Pages (Plugins, LLM, Operations) (Week 3-4)**
1. Create Plugins management page
2. Build LLM Providers configuration UI
3. Implement Operations dashboard (queue controls, audit logs)
4. Add MCP Servers management
5. Create System Prompt Editor
6. Build Add Tool page (OpenAPI upload)
7. Test all CRUD operations

**Story 5: Monitoring & History + Role-Based UI (Week 4-5)**
1. Build Execution History viewer with filters
2. Create Workers monitoring dashboard
3. Implement LLM Costs dashboard with charts
4. Add Agent Performance metrics page
5. Refine role-based access throughout app
6. Add loading states and error boundaries
7. Implement optimistic UI updates

**Story 6: Testing, Polish, Deployment (Week 5-6)**
1. Add E2E tests with Playwright
2. Implement dark mode toggle
3. Add responsive mobile layouts
4. Performance optimization (code splitting, image optimization)
5. Accessibility audit (keyboard nav, ARIA labels)
6. Create deployment Dockerfile for Next.js
7. Update docker-compose.yml
8. Deploy to staging environment
9. User acceptance testing with operations team
10. Production deployment

### 8.3 Testing Strategy

**Unit Tests:**
- **Frontend:** Test individual components with Jest + React Testing Library
  - Component rendering
  - User interactions
  - State management
  - Hooks logic
- **Backend:** Test services and utilities with Pytest
  - Auth service (password hashing, JWT generation)
  - User service (CRUD operations)
  - Permission checks

**Integration Tests:**
- **API Integration:** Test Next.js → FastAPI communication
  - Login flow end-to-end
  - Data fetching with real API responses
  - Error handling
- **Database Integration:** Test auth database operations
  - User creation and authentication
  - Role assignment
  - RLS enforcement

**E2E Tests (Playwright):**
- User login flow
- Tenant switching
- Create/edit/delete agent
- Navigation between pages
- Permission-based feature visibility

**Manual Testing Checklist:**
- [ ] All pages load correctly
- [ ] Forms submit and validate properly
- [ ] Tables sort and filter correctly
- [ ] Dark mode works on all pages
- [ ] Mobile responsive layout works
- [ ] Keyboard navigation works
- [ ] Screen reader compatibility
- [ ] Cross-browser testing (Chrome, Firefox, Safari)

### 8.4 Acceptance Criteria

**Story 1 - Authentication + RBAC:**
- [ ] Admin can register new users with roles
- [ ] Users can log in with email/password
- [ ] JWT tokens are generated and validated
- [ ] Protected routes require authentication
- [ ] RBAC middleware enforces permissions
- [ ] All auth events are logged

**Story 2 - Project Setup + Layout:**
- [ ] Next.js app runs locally
- [ ] Login page uses Auth.js
- [ ] Dashboard layout has header, sidebar, tenant switcher
- [ ] Liquid Glass design applied to all UI elements
- [ ] Theme toggle switches light/dark mode
- [ ] Navigation works between all pages

**Story 3 - Core Pages:**
- [ ] Dashboard displays real-time metrics
- [ ] Charts render correctly
- [ ] Tenant CRUD operations work
- [ ] Agent CRUD operations work
- [ ] Agent testing sandbox executes tests
- [ ] Role-based UI hides features based on permissions

**Story 4 - Management Pages:**
- [ ] All 7 management pages render
- [ ] Plugin configuration saves correctly
- [ ] LLM provider models are listed
- [ ] Operations queue controls work
- [ ] MCP servers can be added/edited/deleted
- [ ] System prompts can be edited
- [ ] OpenAPI tools can be uploaded

**Story 5 - Monitoring & History:**
- [ ] Execution history displays with filters
- [ ] Workers dashboard shows real-time stats
- [ ] Cost dashboard displays accurate data
- [ ] Performance metrics load quickly
- [ ] Role-based access works on all pages
- [ ] Loading states display during fetches
- [ ] Errors are handled gracefully

**Story 6 - Testing & Deployment:**
- [ ] All E2E tests pass
- [ ] Dark mode works perfectly
- [ ] Mobile layout is fully responsive
- [ ] Performance Lighthouse score > 90
- [ ] Accessibility Lighthouse score > 90
- [ ] Docker image builds successfully
- [ ] App deploys to staging
- [ ] User acceptance testing passes
- [ ] Production deployment successful

---

## 9. Developer Resources

### 9.1 File Paths Complete

**Backend Files to Modify:**
- `src/database/models.py` - Add User, UserTenantRole, AuthAuditLog models
- `src/api/dependencies.py` - Update get_tenant_id() to extract from JWT
- `src/config.py` - Add JWT configuration
- `src/main.py` - Add CORS middleware
- `alembic/versions/YYYYMMDD_HHMM_add_auth_tables.py` - Create migration

**Backend Files to Create:**
- `src/api/auth.py` - Authentication endpoints
- `src/api/users.py` - User management endpoints
- `src/services/auth_service.py` - Auth business logic
- `src/services/user_service.py` - User business logic
- `src/middleware/jwt_middleware.py` - JWT validation
- `src/middleware/rbac_middleware.py` - Permission checks
- `tests/unit/test_auth_service.py` - Auth service tests
- `tests/integration/test_auth_api.py` - Auth API integration tests

**Frontend Files to Create (100+ files):**
- See Section 3.1 Source Tree Changes for complete structure
- Key entry points:
  - `nextjs-ui/src/app/layout.tsx`
  - `nextjs-ui/src/app/(dashboard)/layout.tsx`
  - `nextjs-ui/src/lib/auth.ts`
  - `nextjs-ui/src/lib/api-client.ts`
  - `nextjs-ui/middleware.ts`

### 9.2 Key Code Locations

**Authentication:**
- Backend login endpoint: `src/api/auth.py:create_login_endpoint()`
- JWT generation: `src/services/auth_service.py:create_access_token()`
- JWT middleware: `src/middleware/jwt_middleware.py:jwt_middleware()`
- Frontend Auth.js config: `nextjs-ui/src/lib/auth.ts:NextAuth()`
- Login page: `nextjs-ui/src/app/(auth)/login/page.tsx`

**Authorization:**
- Permission definitions: `nextjs-ui/src/lib/permissions.ts:PERMISSIONS`
- RBAC middleware: `src/middleware/rbac_middleware.py:require_permission()`
- Frontend permission hook: `nextjs-ui/src/hooks/usePermissions.ts:usePermissions()`

**Tenant Switching:**
- Tenant switcher UI: `nextjs-ui/src/components/layout/TenantSwitcher.tsx`
- Tenant store: `nextjs-ui/src/store/tenant-store.ts`
- Tenant extraction: `src/api/dependencies.py:get_tenant_id()`

**Liquid Glass Design:**
- CSS variables: `nextjs-ui/src/styles/liquid-glass.css`
- GlassCard component: `nextjs-ui/src/components/ui/GlassCard.tsx`
- Neural network: `nextjs-ui/src/components/dashboard/NeuralNetwork.tsx`

### 9.3 Testing Locations

**Backend Tests:**
- Unit tests: `tests/unit/`
  - `test_auth_service.py`
  - `test_user_service.py`
- Integration tests: `tests/integration/`
  - `test_auth_api.py`
  - `test_rbac_middleware.py`

**Frontend Tests:**
- Component tests: `nextjs-ui/src/components/**/*.test.tsx`
- Hook tests: `nextjs-ui/src/hooks/**/*.test.ts`
- E2E tests: `nextjs-ui/e2e/`
  - `auth.spec.ts`
  - `dashboard.spec.ts`
  - `agents.spec.ts`

### 9.4 Documentation to Update

**README Files:**
- `README.md` - Add Next.js setup instructions
- `nextjs-ui/README.md` - Create frontend-specific README

**API Documentation:**
- `docs/api/authentication.md` - CREATE - Document auth endpoints
- `docs/api/authorization.md` - CREATE - Document RBAC system

**Development Guides:**
- `docs/development/frontend-setup.md` - CREATE - Next.js development guide
- `docs/development/component-guide.md` - CREATE - Component usage examples
- `docs/development/testing-guide.md` - UPDATE - Add frontend testing

**Deployment Documentation:**
- `docs/deployment/nextjs.md` - CREATE - Next.js deployment guide
- `docker-compose.yml` - UPDATE - Add Next.js service

**CHANGELOG:**
- `CHANGELOG.md` - UPDATE - Add UI migration entry

---

## 10. UX/UI Considerations

### 10.1 UI Components Affected

**New Components to Create:**
- GlassCard - Glassmorphic card with hover effects
- Button - Liquid Glass button with variants
- Input - Form input with glass styling
- Select - Dropdown with glass styling
- Modal - Glass modal with backdrop
- Toast - Notification system
- Table - Data table with sorting/filtering
- Tabs - Tabbed interface
- Badge - Status badges (active, inactive, etc.)
- Avatar - User avatar
- Skeleton - Loading placeholder
- EmptyState - No data placeholder
- ErrorBoundary - Error display component

**Components per Page:**
- Dashboard: MetricCard, PerformanceChart, ActivityFeed, NeuralNetwork
- Tenants: TenantForm, TenantTable, TenantDetailView
- Agents: AgentForm, AgentCard, AgentTestPanel, ToolAssignmentUI
- Plugins: PluginCard, PluginConfigForm, ConnectionTestPanel
- Operations: QueueControls, AuditLogTable, SyncStatusPanel
- And more for each of the 14 pages...

### 10.2 UX Flow Changes

**Current Flow (Streamlit):**
1. User visits app.example.com
2. K8s Ingress prompts for basic auth (username/password)
3. User authenticated by Ingress, forwarded to Streamlit
4. Full page reload on every interaction
5. No tenant switching (session-based, set once)

**New Flow (Next.js):**
1. User visits app.example.com
2. Redirected to /login page
3. User enters email/password
4. Auth.js validates via FastAPI, stores JWT in session cookie
5. Redirected to /dashboard
6. Tenant switcher in header allows instant switching (no page reload)
7. Optimistic UI updates on interactions
8. Real-time updates (polling every 5 seconds for dashboard metrics)

### 10.3 Visual/Interaction Patterns

**Design System Components:**
1. **Glassmorphic Cards:**
   - Translucent background (75% opacity)
   - Backdrop blur (32px)
   - Subtle border (white with transparency)
   - Elevation shadow
   - Smooth hover lift effect

2. **Color-Coded Metrics:**
   - Blue (#3b82f6) - Active models, requests
   - Purple (#8b5cf6) - Success rates
   - Green (#10b981) - Positive metrics, success states
   - Orange (#f59e0b) - Warnings, pending states
   - Red (#ef4444) - Errors, failures

3. **Animations:**
   - Page transitions: 300ms fade + slide
   - Card hover: 200ms lift + shadow expand
   - Button press: 150ms scale down
   - Loading: Skeleton shimmer effect
   - Toast: Slide in from top-right

4. **Typography:**
   - Headings: Inter font, bold weights
   - Body: Inter font, regular weight
   - Code: Fira Code, monospace

### 10.4 Responsive Design

**Breakpoints:**
- Mobile: < 768px (single column, hamburger menu)
- Tablet: 768px - 1024px (sidebar collapses to icons)
- Desktop: 1024px - 1440px (full sidebar with labels)
- Wide: > 1440px (additional spacing, larger charts)

**Mobile Adaptations:**
- Sidebar becomes bottom navigation bar
- Tables become card lists
- Multi-column layouts stack vertically
- Touch-friendly targets (min 44x44px)
- Swipe gestures for navigation

### 10.5 Accessibility

**Keyboard Navigation:**
- Tab order follows visual hierarchy
- Skip links for main content
- Escape closes modals/dropdowns
- Arrow keys navigate lists/menus
- Enter/Space activate buttons

**Screen Reader Support:**
- Semantic HTML elements
- ARIA labels for all interactive elements
- ARIA live regions for dynamic content
- Focus indicators (blue outline)
- Alt text for all images

**Color Contrast:**
- Text: WCAG AA minimum (4.5:1)
- Interactive elements: WCAG AA minimum (3:1)
- Test with dark mode enabled

---

## 11. Testing Approach

### 11.1 Test Framework Info

**Backend (Python):**
- **Framework:** Pytest 7.4.3
- **Async:** pytest-asyncio 0.21.1
- **Mocking:** pytest-mock 3.12.0, fakeredis 2.20.0
- **HTTP:** pytest-httpx 0.22.0
- **Coverage:** pytest-cov 7.0.0

**Frontend (TypeScript):**
- **Framework:** Jest 29.7.0
- **React Testing:** @testing-library/react 16.0.1
- **E2E:** Playwright 1.48.2
- **Mocking:** MSW (Mock Service Worker) 2.6.5

### 11.2 Testing Approach

**Backend Unit Tests:**
```python
# tests/unit/test_auth_service.py
import pytest
from src.services.auth_service import AuthService

@pytest.mark.unit
def test_hash_password():
    """Test password hashing."""
    service = AuthService()
    hashed = service.hash_password("test123")
    assert hashed != "test123"
    assert service.verify_password("test123", hashed)

@pytest.mark.unit
def test_create_jwt_token():
    """Test JWT token generation."""
    service = AuthService()
    user = User(id="123", email="test@example.com")
    roles = {"tenant1": "admin"}

    token = service.create_access_token(user, roles)
    payload = service.decode_token(token)

    assert payload["sub"] == "123"
    assert payload["email"] == "test@example.com"
    assert payload["roles"]["tenant1"] == "admin"
```

**Backend Integration Tests:**
```python
# tests/integration/test_auth_api.py
import pytest
from httpx import AsyncClient

@pytest.mark.integration
@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, test_user):
    """Test successful login."""
    response = await client.post(
        "/api/auth/login",
        json={"email": test_user.email, "password": "test123"}
    )
    assert response.status_code == 200
    assert "token" in response.json()
    assert "user" in response.json()

@pytest.mark.integration
@pytest.mark.asyncio
async def test_protected_route_requires_auth(client: AsyncClient):
    """Test protected route without auth."""
    response = await client.get("/api/agents")
    assert response.status_code == 401
```

**Frontend Component Tests:**
```typescript
// components/ui/GlassCard.test.tsx
import { render, screen } from '@testing-library/react';
import { GlassCard } from './GlassCard';

describe('GlassCard', () => {
  it('renders children correctly', () => {
    render(
      <GlassCard>
        <p>Test content</p>
      </GlassCard>
    );
    expect(screen.getByText('Test content')).toBeInTheDocument();
  });

  it('applies hover effect', async () => {
    const { container } = render(<GlassCard>Content</GlassCard>);
    const card = container.firstChild;

    // Check for glass-card class
    expect(card).toHaveClass('glass-card');
  });
});
```

**Frontend E2E Tests:**
```typescript
// e2e/auth.spec.ts
import { test, expect } from '@playwright/test';

test.describe('Authentication', () => {
  test('user can log in', async ({ page }) => {
    await page.goto('http://localhost:3000/login');

    await page.fill('input[name="email"]', 'admin@example.com');
    await page.fill('input[name="password"]', 'admin123');
    await page.click('button[type="submit"]');

    await expect(page).toHaveURL('http://localhost:3000/dashboard');
    await expect(page.locator('text=Dashboard')).toBeVisible();
  });

  test('invalid credentials show error', async ({ page }) => {
    await page.goto('http://localhost:3000/login');

    await page.fill('input[name="email"]', 'wrong@example.com');
    await page.fill('input[name="password"]', 'wrong');
    await page.click('button[type="submit"]');

    await expect(page.locator('text=Invalid credentials')).toBeVisible();
  });
});
```

### 11.3 Coverage Requirements

**Backend:**
- Unit tests: 80%+ coverage on services, utilities
- Integration tests: 70%+ coverage on API routes
- Critical paths (auth, RBAC): 90%+ coverage

**Frontend:**
- Component tests: 70%+ coverage
- Utility functions: 80%+ coverage
- E2E tests: Cover all critical user flows

---

## 12. Deployment Strategy

### 12.1 Deployment Steps

**1. Build Docker Images:**
```bash
# Backend (already exists, no changes)
docker build -t ai-agents-api:latest .

# Frontend (NEW)
cd nextjs-ui
docker build -t ai-agents-ui:latest .
```

**2. Update docker-compose.yml:**
```yaml
services:
  # Existing services...

  nextjs-ui:
    build:
      context: ./nextjs-ui
      dockerfile: Dockerfile
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://api:8000
      - NEXTAUTH_URL=http://localhost:3000
      - NEXTAUTH_SECRET=${NEXTAUTH_SECRET}
    depends_on:
      - api
    networks:
      - ai-agents-network
```

**3. Deploy to Staging:**
```bash
# Push images to registry
docker tag ai-agents-ui:latest registry.example.com/ai-agents-ui:staging
docker push registry.example.com/ai-agents-ui:staging

# Deploy via Render.com (or similar)
# Update render.yaml with Next.js service
```

**4. Run Database Migrations:**
```bash
# SSH into backend container
docker exec -it ai-agents-api bash

# Run migrations
alembic upgrade head

# Create admin user
python scripts/create_admin_user.py
```

**5. Smoke Test:**
- [ ] Login works
- [ ] Dashboard loads
- [ ] Tenant switching works
- [ ] API calls succeed
- [ ] Metrics display correctly

**6. Deploy to Production:**
```bash
# Tag as production
docker tag ai-agents-ui:latest registry.example.com/ai-agents-ui:production
docker push registry.example.com/ai-agents-ui:production

# Deploy via Render.com
# Monitor logs for errors
```

### 12.2 Rollback Plan

**If Issues Detected:**

1. **Immediate Rollback:**
   ```bash
   # Revert to previous Docker image
   docker tag registry.example.com/ai-agents-ui:previous registry.example.com/ai-agents-ui:production
   docker push registry.example.com/ai-agents-ui:production

   # Restart service
   docker-compose restart nextjs-ui
   ```

2. **Database Rollback (if migrations were run):**
   ```bash
   # Rollback last migration
   alembic downgrade -1
   ```

3. **Verify Rollback:**
   - [ ] Previous version loads
   - [ ] All features work
   - [ ] No data loss

### 12.3 Monitoring Approach

**Post-Deployment Monitoring:**

**Application Metrics:**
- Response times (p50, p95, p99)
- Error rates (HTTP 4xx, 5xx)
- Authentication success/failure rates
- API call volumes per endpoint

**Infrastructure Metrics:**
- CPU usage
- Memory usage
- Network bandwidth
- Container health

**User Metrics:**
- Active users per day
- Page views per session
- Most used features
- User flow drop-offs

**Logging:**
- Frontend: Console errors sent to logging service
- Backend: Loguru logs (INFO, WARNING, ERROR levels)
- Auth: All login attempts logged to audit table

**Alerts:**
- Error rate > 5% → Slack notification
- Response time p95 > 2s → Email alert
- Login failures > 10/min → Security alert
- Container restart → PagerDuty alert

---

## 13. Technical Debt & Future Enhancements

**Known Limitations (Accept for MVP):**
1. Polling for real-time updates (no WebSockets) - Add WebSockets in v2
2. Single-language support (English only) - Add i18n later
3. No offline support (requires internet) - Add PWA later
4. Basic error pages (no custom 404/500 designs) - Enhance in v2

**Future Enhancements:**
1. **WebSocket Real-Time Updates:** Replace polling with WebSockets for dashboard metrics
2. **Advanced Analytics:** Custom reports, data exports, scheduled emails
3. **Multi-Language Support:** i18n with next-intl
4. **Mobile Native Apps:** React Native version for iOS/Android
5. **Advanced RBAC:** Custom permissions, permission groups, delegated admin
6. **White-Labeling:** Tenant-specific themes, logos, domains
7. **API Rate Limiting:** Per-user and per-tenant rate limits
8. **Audit Dashboard:** Visualize all audit logs, detect anomalies
9. **Two-Factor Authentication:** TOTP, SMS, email 2FA
10. **SSO Integration:** SAML, Azure AD, Okta

---

## 14. Summary

**What We're Building:**
A production-ready Next.js admin UI to replace the Streamlit prototype, featuring:
- Modern Liquid Glass design (SuperDesign Mockup #3 as base)
- Proper authentication (Auth.js) and RBAC (5 roles)
- All 14 existing Streamlit pages migrated to React
- Dark mode, responsive design, accessibility
- Integration with existing FastAPI backend (minimal backend changes)

**Why This Approach:**
- **Auth.js over Clerk/Auth0:** Free, self-hosted, no vendor lock-in for internal tool
- **Next.js 14 App Router:** Modern React patterns, SSR, best-in-class DX
- **Minimal Backend Changes:** Only add auth endpoints and JWT middleware, keep existing API
- **Liquid Glass Design:** Matches user's request for "futuristic but not too basic"
- **6 Stories:** Structured approach ensures systematic migration with proper testing

**Success Criteria:**
- All Streamlit features migrated to Next.js
- Authentication and RBAC working correctly
- Users prefer new UI over Streamlit
- No degradation in performance
- 80%+ test coverage
- Successful production deployment

**Estimated Timeline:**
- 6 weeks for full implementation
- 1 story per week
- Overlapping stories for parallel development

---

**Tech-Spec Complete! ✅**

This document serves as the single source of truth for the Next.js UI Migration project. All developers should reference this document before starting implementation.

**Next Step:** Generate epic and 6 user stories based on this tech-spec.
