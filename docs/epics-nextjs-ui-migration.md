# AI Agents Platform - Next.js UI Migration Epic Breakdown

**Author:** Ravi (with Bob - Scrum Master)
**Date:** 2025-01-17
**Project Type:** Brownfield - UI Migration
**Target Scale:** Platform feature - Next.js UI replacing Streamlit

---

## Overview

This document provides the complete epic and story breakdown for migrating the AI Agents Platform from Streamlit to Next.js 14 with Apple Liquid Glass design and role-based access control (RBAC). This epic decomposes the technical specification into implementable, vertically-sliced stories.

**Living Document Notice:** This is the initial version based on tech-spec v2.0. It incorporates all team feedback and provides detailed acceptance criteria for each story.

**Epic Structure:**
- **Epic 1:** Pre-Implementation Preparation (Story 0)
- **Epic 2:** Authentication & Authorization Foundation (Stories 1A, 1B, 1C)
- **Epic 3:** Next.js UI Core (Stories 2-6)
- **Epic 4:** Documentation, Testing & Launch (Stories 7, 8, 8.5)

---

## Functional Requirements Inventory

Based on the tech-spec v2.0, the following functional requirements drive this migration:

**FR1:** Modern, performant UI that replaces Streamlit
- Sub-requirements: SSR, RSC, < 2s page load, mobile-responsive

**FR2:** Authentication system with JWT
- Sub-requirements: Login, register, password reset, JWT tokens

**FR3:** Role-based access control (RBAC) with 5 roles
- Roles: super_admin, tenant_admin, operator, developer, viewer
- Sub-requirements: Permission matrix, role assignment per tenant

**FR4:** Multi-tenant context switching
- Sub-requirements: Tenant switcher, tenant-scoped data, RLS

**FR5:** Apple Liquid Glass design system
- Sub-requirements: Glassmorphism, neural network bg, dark mode, responsive

**FR6:** Feature parity with 14 existing Streamlit pages
- Sub-requirements: All monitoring, configuration, operations, tools pages

**FR7:** Enhanced user experience
- Sub-requirements: Real-time polling, keyboard shortcuts, feedback widget

**FR8:** Security and compliance
- Sub-requirements: Rate limiting, password policy, audit logs, account lockout

**FR9:** Performance and accessibility
- Sub-requirements: Performance budget, WCAG 2.1 AA, reduced motion

**FR10:** Phased rollout with user training
- Sub-requirements: Alpha/Beta/GA phases, documentation, videos

---

## FR Coverage Map

| FR | Epic | Stories | Description |
|----|------|---------|-------------|
| FR1 | Epic 3 | Story 2 | Next.js project setup with SSR/RSC |
| FR2 | Epic 2 | Stories 1A, 1B, 1C | Complete auth system with JWT |
| FR3 | Epic 2 | Stories 1A, 1B, 1C | RBAC with 5 roles and permissions |
| FR4 | Epic 3 | Story 2 | Tenant switcher and context management |
| FR5 | Epic 1, Epic 3 | Story 0, Story 2, Story 6 | Design system and implementation |
| FR6 | Epic 3 | Stories 3, 4, 5 | All 14 pages migrated with feature parity |
| FR7 | Epic 3 | Story 6 | UX polish with feedback, shortcuts, notifications |
| FR8 | Epic 2, Epic 4 | Stories 1B, 1C, 8.5 | Security: rate limiting, policies, testing |
| FR9 | Epic 3, Epic 4 | Stories 2, 6, 8 | Performance budget, accessibility, load testing |
| FR10 | Epic 4 | Stories 7, 8 | Documentation, training, phased rollout |

---

## Epic 1: Pre-Implementation Preparation

**Goal:** Validate user needs and establish design foundation before any code is written

**Value:** Reduces rework by ensuring we build what users actually need and have a consistent design system to reference throughout implementation.

**Duration:** 1 week (5 days)

**Covers FRs:** FR5 (Design System)

**Sequencing:** Must be completed before Epic 2 begins

---

### Story 0: User Research & Design Preparation

**As a** product team member,
**I want** validated user personas and a complete design system,
**So that** we build features users need with a consistent, professional design.

**Acceptance Criteria:**

**Given** we are about to replace the primary UI of the platform
**When** we conduct user research and create design specifications
**Then** we should have:

1. ✅ **User Research Complete:**
   - 5-8 operations team members interviewed (1 hour each)
   - Interview notes documented with pain points, desired features, usage patterns
   - 5 user personas defined with: Name, Role, Goals, Pain Points, Usage scenarios
   - User research findings documented in `docs/user-research-findings.md`
   - Feature prioritization based on user feedback (most-used to least-used)

2. ✅ **Design System Created:**
   - Figma project created with all screens and components
   - SuperDesign Mockup #3 imported as reference (users preferred light theme)
   - 20+ components defined: Buttons, Inputs, Cards, Modals, Tables, Forms, etc.
   - Component variants documented (Primary, Secondary, Danger, Ghost, Disabled, Loading)
   - Spacing scale defined (4, 8, 16, 24, 32, 48, 64px)
   - Typography scale defined (H1-H6, body, caption, code) with sizes, weights, line heights
   - Color palette defined for light and dark modes
   - Responsive layouts for 4 breakpoints: mobile (< 768px), tablet (768-1024px), desktop (1024-1440px), wide (> 1440px)

3. ✅ **Design Tokens Exported:**
   - `docs/design-system/design-tokens.json` created with all tokens (colors, spacing, typography, animation)
   - Tokens organized by category (colors.glass, colors.text, colors.accent, etc.)
   - Animation timings and easing functions defined (fast: 150ms, base: 300ms, slow: 500ms)

4. ✅ **Empty State Patterns Defined:**
   - Welcome state template: "Get started by creating your first [entity]"
   - Zero state template: "No [items] yet. [Action] will appear here after [trigger]."
   - Error state template: "Failed to load. [Error details]. [Retry action]"

5. ✅ **Architecture Decision Records (ADRs) Created:**
   - `docs/adr/001-nextjs-over-remix.md` - Why Next.js 14 App Router
   - `docs/adr/002-authjs-over-clerk.md` - Why Auth.js for internal tool
   - `docs/adr/003-jwt-roles-on-demand.md` - Why roles fetched, not in JWT (CRITICAL)
   - `docs/adr/004-api-versioning-strategy.md` - Why `/api/v1/*` versioning
   - `docs/adr/005-tanstack-query-over-swr.md` - Data fetching library choice
   - `docs/adr/006-tailwind-over-css-in-js.md` - Styling approach

**And** all ADRs follow the standard template with: Status, Date, Context, Decision, Rationale, Alternatives, Consequences, Implementation Notes

**Prerequisites:** None (first story)

**Technical Notes:**
- Use Figma for design system (collaborative, versioned, exportable)
- SuperDesign mockups available at `.superdesign/design_iterations/`
- Interview script should cover: pain points, most-used features, mobile usage, design preferences
- Personas should map to the 5 RBAC roles (super_admin, tenant_admin, operator, developer, viewer)
- ADR 003 is CRITICAL - must document the JWT roles-on-demand architecture to prevent token bloat

**Test Strategy:**
- Design review with 2 team members to validate usability
- Figma prototype walkthrough with 2 operations team members
- Verify all design tokens validate as JSON

---

## Epic 2: Authentication & Authorization Foundation

**Goal:** Implement secure authentication with JWT and role-based access control for multi-tenant platform

**Value:** Enables secure, tenant-scoped access with granular permissions, replacing insecure K8s basic auth.

**Duration:** 10 days (2 weeks)

**Covers FRs:** FR2 (Authentication), FR3 (RBAC), FR4 (Multi-tenant), FR8 (Security)

**Sequencing:** Must be completed after Epic 1 (Story 0)

---

### Story 1A: Database & Auth Foundation

**As a** platform architect,
**I want** database models and migrations for users, roles, and audit logs,
**So that** we can store authentication data with proper multi-tenant isolation.

**Acceptance Criteria:**

**Given** we need to store user authentication and authorization data
**When** we create database models and run migrations
**Then** we should have:

1. ✅ **Database Models Created:**
   - `User` model with fields: id (UUID), email (unique), password_hash, default_tenant_id, failed_login_attempts, locked_until, password_expires_at, password_history (JSON), created_at, updated_at
   - `UserTenantRole` model with fields: id (UUID), user_id (FK), tenant_id (FK), role (enum: super_admin, tenant_admin, operator, developer, viewer), created_at, updated_at
   - `AuthAuditLog` model with fields: id (UUID), user_id (FK, nullable), event_type, success (bool), ip_address, user_agent, created_at
   - `AuditLog` model with fields: id (UUID), user_id (FK), tenant_id, action, entity_type, entity_id, old_value (JSONB), new_value (JSONB), ip_address, user_agent, created_at
   - All models use UUID primary keys
   - All timestamps default to NOW()

2. ✅ **Database Indexes Created:**
   - Index on users.email (unique)
   - Index on user_tenant_roles (user_id, tenant_id) - composite unique
   - Index on auth_audit_log (user_id, created_at)
   - Index on audit_log (user_id, tenant_id, entity_type, created_at)

3. ✅ **Alembic Migration Created:**
   - Migration file: `alembic/versions/YYYYMMDD_add_auth_tables.py`
   - Upgrade creates all 4 tables with indexes
   - Downgrade drops all 4 tables
   - Migration runs successfully (tested with upgrade + rollback)

4. ✅ **Admin User Seed Script:**
   - Script: `scripts/create_admin_user.py`
   - Accepts environment variables: ADMIN_EMAIL, ADMIN_PASSWORD, DEFAULT_TENANT_ID
   - Creates super_admin user with default tenant role
   - Password hashed with bcrypt (10 rounds)
   - Idempotent (checks if user exists before creating)

5. ✅ **User Migration Script (Optional):**
   - Script: `scripts/migrate_streamlit_users.py`
   - Reads existing K8s Ingress basic auth users (if any)
   - Migrates to new User table with temporary passwords
   - Sends password reset emails to all migrated users
   - Logs all migrations to audit_log

**And** all models inherit from SQLAlchemy declarative_base
**And** all models use AsyncPG for async database operations
**And** models follow existing project conventions (see src/database/models.py)

**Prerequisites:** Story 0 (ADR 003 defines JWT architecture)

**Technical Notes:**
- Extend existing `src/database/models.py`
- Use Alembic for migrations (already configured in project)
- Password hashing: bcrypt with 10 rounds (balance security vs performance)
- JWT roles stored as enum: `Role = Enum('super_admin', 'tenant_admin', 'operator', 'developer', 'viewer')`
- Row-Level Security (RLS) handled in application layer via tenant_id filtering
- User model should NOT store all tenant roles (see ADR 003 - roles fetched on-demand)

**Test Strategy:**
- Unit tests for model validation: `tests/unit/test_user_model.py`
- Tests: create user, assign role, validate unique constraints
- Test migration forward + rollback
- Test admin user creation script with mock env vars
- Coverage target: 90%+ for models and scripts

---

### Story 1B: Auth Service & JWT Implementation

**As a** backend developer,
**I want** authentication services for password hashing, JWT generation, and validation,
**So that** users can securely log in and maintain authenticated sessions.

**Acceptance Criteria:**

**Given** we have database models for users and authentication
**When** we implement authentication business logic
**Then** we should have:

1. ✅ **AuthService Implemented:**
   - `src/services/auth_service.py` created
   - Methods:
     - `hash_password(password: str) -> str` - bcrypt with 10 rounds
     - `verify_password(plain: str, hashed: str) -> bool` - constant-time comparison
     - `create_access_token(user: User) -> str` - JWT with 7-day expiration
     - `create_refresh_token(user: User) -> str` - JWT with 30-day expiration
     - `verify_token(token: str) -> JWTPayload` - validates signature + expiration
     - `revoke_token(token: str)` - adds token to Redis blacklist

2. ✅ **JWT Payload Structure (CRITICAL):**
   - Payload contains ONLY: sub (user_id), email, default_tenant_id, iat, exp
   - Payload does NOT contain roles (prevents token bloat, see ADR 003)
   - Access token expires in 7 days
   - Refresh token expires in 30 days
   - Tokens signed with HS256 algorithm
   - JWT secret loaded from environment variable: JWT_SECRET

3. ✅ **Password Policy Validation:**
   - Method: `validate_password_strength(password: str) -> tuple[bool, str]`
   - Rules enforced:
     - Minimum 12 characters
     - At least 1 uppercase letter (A-Z)
     - At least 1 number (0-9)
     - At least 1 special character (!@#$%^&*)
     - Password not in common passwords list (using zxcvbn library, score >= 3)
   - Returns (True, "") if valid, (False, "error message") if invalid

4. ✅ **Account Lockout Logic:**
   - Method: `handle_failed_login(user: User) -> None`
   - Increments user.failed_login_attempts
   - If attempts >= 5: sets user.locked_until = now + 15 minutes
   - Logs lockout event to auth_audit_log
   - Method: `reset_failed_attempts(user: User) -> None` - called on successful login

5. ✅ **UserService Implemented:**
   - `src/services/user_service.py` created
   - Methods:
     - `create_user(email, password, default_tenant_id, db) -> User`
     - `get_user_by_email(email, db) -> User | None`
     - `get_user_by_id(user_id, db) -> User | None`
     - `update_user(user_id, updates, db) -> User`
     - `delete_user(user_id, db) -> None`
     - `get_user_role_for_tenant(user_id, tenant_id, db) -> Role | None`
     - `assign_role(user_id, tenant_id, role, db) -> None`

**And** all password operations use constant-time comparison to prevent timing attacks
**And** JWT tokens are stateless (no session store needed)
**And** revoked tokens stored in Redis with TTL = token expiration
**And** all services use async/await for database operations

**Prerequisites:** Story 1A (database models exist)

**Technical Notes:**
- Use `python-jose` library for JWT operations
- Use `passlib` with `bcrypt` for password hashing
- Use `zxcvbn` library for password strength estimation
- JWT_SECRET must be at least 32 characters (enforce in settings validation)
- Token blacklist stored in Redis: key = `revoked:{token_hash}`, value = 1, TTL = token expiration
- Constant-time comparison: use `secrets.compare_digest()` or passlib's verify

**Test Strategy:**
- Unit tests: `tests/unit/test_auth_service.py`, `tests/unit/test_user_service.py`
- Test password hashing (verify != original, verify works)
- Test JWT generation and validation (happy path + expired + invalid signature)
- Test password policy (all rules: length, uppercase, number, special, common password)
- Test account lockout (5 attempts, locked_until set, resets on success)
- Test user CRUD operations
- Coverage target: 90%+ for both services

---

### Story 1C: API Endpoints & Middleware

**As a** frontend developer,
**I want** REST API endpoints for authentication and user management,
**So that** the Next.js UI can authenticate users and enforce permissions.

**Acceptance Criteria:**

**Given** we have authentication services and database models
**When** we implement API endpoints and middleware
**Then** we should have:

1. ✅ **Auth API Endpoints:**
   - `src/api/v1/auth.py` created (note: versioned under /api/v1)
   - Endpoints:
     - `POST /api/v1/auth/register` - create new user, returns JWT token + user
     - `POST /api/v1/auth/login` - authenticate, returns JWT token + refresh token + user
     - `POST /api/v1/auth/refresh` - exchange refresh token for new access token
     - `POST /api/v1/auth/logout` - revoke access token (adds to blacklist)
     - `GET /api/v1/auth/me` - get current user info (requires JWT)
     - `POST /api/v1/auth/forgot-password` - send password reset email
     - `POST /api/v1/auth/reset-password` - reset password with token

2. ✅ **User Management API Endpoints:**
   - `src/api/v1/users.py` created
   - Endpoints:
     - `GET /api/v1/users` - list all users (super_admin only)
     - `GET /api/v1/users/{user_id}` - get user details (self or super_admin)
     - `PUT /api/v1/users/{user_id}` - update user (self or super_admin)
     - `DELETE /api/v1/users/{user_id}` - delete user (super_admin only)
     - `GET /api/v1/users/me/role?tenant_id=xxx` - get role for specific tenant (CRITICAL)
     - `POST /api/v1/users/{user_id}/roles` - assign role to user (super_admin only)
     - `DELETE /api/v1/users/{user_id}/roles/{tenant_id}` - remove role (super_admin only)

3. ✅ **JWT Middleware:**
   - `src/middleware/jwt_middleware.py` created
   - Extracts JWT token from Authorization header (Bearer token)
   - Validates token signature and expiration
   - Checks if token is revoked (Redis blacklist)
   - Sets `request.state.user` with authenticated user
   - Returns 401 if token missing, invalid, expired, or revoked
   - Returns 423 if user account is locked

4. ✅ **RBAC Middleware:**
   - `src/middleware/rbac_middleware.py` created
   - Decorator: `@require_permission("permission:action")` (e.g., `@require_permission("agents:edit")`)
   - Fetches user's role for current tenant from `request.state.tenant_id`
   - Checks permission matrix (see tech-spec for full matrix)
   - Returns 403 if user lacks permission
   - Returns 404 if tenant not found or user has no role in tenant

5. ✅ **Rate Limiting:**
   - `src/middleware/rate_limit.py` created using SlowAPI library
   - Applied to auth endpoints:
     - `/api/v1/auth/login` - 5 attempts per 15 minutes per IP
     - `/api/v1/auth/register` - 3 attempts per hour per IP
     - `/api/v1/auth/forgot-password` - 3 attempts per hour per IP
   - Uses Redis for rate limit storage (key = `ratelimit:{ip}:{endpoint}`)
   - Returns 429 with Retry-After header when rate limit exceeded

6. ✅ **API Versioning:**
   - All new endpoints under `/api/v1/*`
   - Existing unversioned endpoints remain unchanged (Streamlit compatibility)
   - Update `src/api/dependencies.py` to work with both versioned and unversioned
   - Document versioning strategy in `docs/adr/004-api-versioning-strategy.md`

7. ✅ **Audit Logging:**
   - All login attempts logged to `auth_audit_log` (success + failure)
   - All CRUD operations logged to `audit_log` via middleware
   - Audit middleware captures: user_id, tenant_id, action, entity, old/new values, IP, user agent

**And** all endpoints return consistent error format:
```json
{
  "detail": "Human-readable error message",
  "code": "ERROR_CODE",
  "timestamp": "2025-01-17T12:34:56Z"
}
```

**And** all endpoints follow OpenAPI 3.0 spec (auto-generated docs at /api/v1/docs)

**Prerequisites:** Story 1B (services implemented)

**Technical Notes:**
- Use FastAPI dependency injection for middleware
- JWT middleware: `Depends(get_current_user)` dependency
- RBAC middleware: `Depends(require_permission("perm"))` dependency
- SlowAPI integrates with FastAPI via state: `app.state.limiter = limiter`
- Permission matrix defined in `src/config/permissions.py` as dict
- Audit middleware: use FastAPI middleware stack, runs on all POST/PUT/PATCH/DELETE
- API versioning: prefix all routes with `/api/v1` in router

**Test Strategy:**
- Integration tests: `tests/integration/test_auth_api.py`, `tests/integration/test_rbac.py`
- Test complete auth flow: register → login → access protected endpoint → logout
- Test JWT validation: valid token, expired token, invalid signature, revoked token
- Test RBAC: super_admin can access all, viewer cannot edit, etc.
- Test rate limiting: exceed limit, verify 429 response with Retry-After
- Test audit logging: verify entries created for login, CRUD operations
- Test account lockout: 5 failed logins, account locked, cannot login until timeout
- Coverage target: 80%+ for API routes and middleware

---

## Epic 3: Next.js UI Core Implementation

**Goal:** Build complete Next.js 14 application with all 14 pages, Liquid Glass design, and full feature parity with Streamlit

**Value:** Delivers modern, performant, mobile-responsive UI that users prefer, enabling phased rollout and eventual Streamlit decommissioning.

**Duration:** 5 weeks

**Covers FRs:** FR1 (Modern UI), FR4 (Tenant Switcher), FR5 (Design System), FR6 (Feature Parity), FR7 (UX Enhancements), FR9 (Performance)

**Sequencing:** Must be completed after Epic 2 (authentication exists)

---

### Story 2: Next.js Project Setup & Layout

**As a** frontend developer,
**I want** a complete Next.js project with authentication, layout, and UI primitives,
**So that** I can build feature pages with consistent design and auth protection.

**Acceptance Criteria:**

**Given** we have backend authentication APIs and design system
**When** we set up the Next.js project and base layout
**Then** we should have:

1. ✅ **Next.js Project Initialized:**
   - Project directory: `nextjs-ui/`
   - Next.js 14.2.15 with App Router
   - TypeScript 5.6.3 with strict mode enabled
   - Dependencies from tech-spec installed (see section 1.2)
   - Scripts: `dev`, `build`, `start`, `lint`, `test`, `test:e2e`, `storybook`

2. ✅ **Tailwind CSS Configured:**
   - `tailwind.config.ts` with design tokens from `../docs/design-system/design-tokens.json`
   - Custom CSS in `src/styles/liquid-glass.css`:
     - `.glass-card` - glassmorphism with backdrop-filter
     - `.glass-button` - glass-styled buttons
     - Progressive enhancement: @supports (backdrop-filter)
     - Reduced motion: @media (prefers-reduced-motion: reduce)
     - Low-end device detection: @media (max-device-memory: 4)
   - Dark mode support via `next-themes` provider

3. ✅ **NextAuth Configured:**
   - `src/lib/auth.ts` with NextAuth v4 (or v5 if stable)
   - Providers: Credentials provider (email + password)
   - JWT strategy with custom callbacks
   - Session callback fetches default tenant
   - Login page: `src/app/auth/login/page.tsx`

4. ✅ **Root Layout with Providers:**
   - `src/app/layout.tsx` with nested providers:
     - SessionProvider (NextAuth)
     - ReactQueryProvider (@tanstack/react-query)
     - ThemeProvider (next-themes for dark mode)
     - ToastProvider (sonner for notifications)
   - Global error boundary
   - Loading.tsx with skeleton UI

5. ✅ **Dashboard Shell:**
   - Layout: `src/app/(dashboard)/layout.tsx`
   - Components:
     - Header: Logo, Tenant Switcher, User Menu (profile, settings, logout), Dark Mode Toggle
     - Sidebar: Grouped navigation (4 categories), collapsible sections, active state
     - Footer: Copyright, version, links
   - Mobile: Header + Bottom navigation (4 icons), sidebar hidden
   - Desktop: Header + Sidebar (left), content area, footer

6. ✅ **Tenant Switcher Component:**
   - `src/components/layout/TenantSwitcher.tsx`
   - Glassmorphic dropdown (Headless UI Listbox)
   - Displays current tenant name + icon
   - Lists all user's tenants (fetched from `/api/v1/users/me/tenants`)
   - Search filter for 10+ tenants
   - On switch: fetches role for new tenant (`/api/v1/users/me/role?tenant_id=xxx`)
   - Updates Zustand store: `useTenantStore.setState({ selectedTenant, role })`
   - All API calls use new tenant context

7. ✅ **Navigation Component:**
   - `src/components/layout/Sidebar.tsx`
   - 4 groups: Monitoring, Configuration, Operations, Tools
   - Each group: icon, title, collapsible section, items with icons + names + paths
   - Active state: highlight current page
   - Permission-based hiding: hide items user cannot access
   - Collapsed/expanded state stored in localStorage: `sidebar-expanded`
   - Mobile: Bottom nav with 4 group icons, tap opens full-screen item list

8. ✅ **UI Primitives (10+ components):**
   - `src/components/ui/` with all components:
     - GlassCard, Button (5 variants), Input, Select, Textarea
     - Modal, Toast, Dropdown, Checkbox, Radio, Switch
     - Skeleton, Spinner, ProgressBar, Badge, Avatar
   - All components have TypeScript types
   - All components support dark mode
   - All components support disabled state
   - Accessibility: ARIA labels, keyboard navigation, focus states

9. ✅ **Animated Background:**
   - `src/components/ui/NeuralNetwork.tsx`
   - Canvas-based neural network animation (light mode)
   - Particle system (dark mode)
   - Respects prefers-reduced-motion (displays static gradient)
   - Disabled on mobile/low-end devices (max-device-memory: 4)

10. ✅ **Storybook Setup:**
    - `.storybook/` config with all addons
    - All UI primitives have stories: `src/components/ui/*.stories.tsx`
    - Stories show all variants (default, disabled, loading, error)
    - Dark mode toggle in Storybook toolbar

11. ✅ **MSW Setup:**
    - `src/mocks/` with MSW handlers
    - Handlers for all `/api/v1/*` endpoints
    - Mock data fixtures: users, tenants, agents, etc.
    - MSW browser worker for dev mode
    - MSW server worker for tests

12. ✅ **Authentication Middleware:**
    - `src/middleware.ts` (Next.js middleware)
    - Redirects unauthenticated users to /auth/login
    - Protected routes: all `/dashboard/*` paths
    - Public routes: `/auth/*`, `/api/*`

**And** app runs locally: `npm run dev` starts on http://localhost:3000
**And** Storybook runs: `npm run storybook` starts on http://localhost:6006
**And** all components pass a11y checks in Storybook (addon-a11y)
**And** dark mode toggle switches theme instantly (no flash)
**And** glassmorphism has fallback for unsupported browsers

**Prerequisites:** Story 1C (auth APIs exist), Story 0 (design system)

**Technical Notes:**
- Use Headless UI for accessible components (Listbox, Dialog, Menu)
- Use Lucide React for icons (tree-shakable)
- Use Zustand for client state (tenant, theme, sidebar)
- Use React Query for server state (API calls, caching)
- Use Sonner for toast notifications (modern, performant)
- Animation: Framer Motion for micro-interactions
- NeuralNetwork component: use requestAnimationFrame for 60fps
- Design tokens: import from JSON, convert to Tailwind theme config

**Test Strategy:**
- Component tests: `src/components/**/*.test.tsx` using React Testing Library
- Test all UI primitives: render, click, keyboard nav, accessibility
- Test tenant switcher: switch tenant, verify API call, verify store update
- Test navigation: click item, verify active state, verify mobile bottom nav
- Test auth: redirect unauthenticated user, protected route access
- E2E test: login flow (Playwright): fill form, submit, verify dashboard redirect
- Visual regression: Chromatic with Storybook for UI primitives
- Coverage target: 70%+ for components

---

### Story 3: Core Pages - Monitoring

**As an** operations team member,
**I want** monitoring pages (dashboard, performance, costs, workers),
**So that** I can view real-time metrics and system health in a modern UI.

**Acceptance Criteria:**

**Given** we have the Next.js layout and UI primitives
**When** we build monitoring pages
**Then** we should have:

1. ✅ **Dashboard Page:**
   - Path: `/dashboard`
   - Components:
     - 4 metric cards (glass cards, color-coded): Total Executions (blue), Success Rate (green), Avg Duration (purple), Active Agents (orange)
     - Performance chart (Recharts LineChart): Last 24 hours, execution count + success rate
     - Activity feed: Last 10 executions with status, agent, duration, time ago
   - Data fetched from `/api/v1/metrics/summary`
   - Polling: refresh every 5 seconds (React Query refetchInterval)
   - Loading: skeleton cards during fetch
   - Error: error boundary with retry button

2. ✅ **Agent Performance Page:**
   - Path: `/performance`
   - Components:
     - Metrics table (TanStack Table): Agent name, executions, success rate, avg duration, last run
     - Sortable columns (click header to sort)
     - Trend chart (Recharts BarChart): Executions per agent (last 7 days)
   - Data fetched from `/api/v1/agents/performance`
   - Polling: refresh every 10 seconds

3. ✅ **LLM Costs Page:**
   - Path: `/costs`
   - Components:
     - Cost summary cards: Total cost (last 30 days), this month, last month
     - Daily trend chart (Recharts AreaChart): Cost per day (last 30 days)
     - Token breakdown table: Model, tokens used, cost, percentage
   - Data fetched from `/api/v1/metrics/llm-costs`
   - Date range picker: last 7 days, last 30 days, last 90 days, custom
   - Export CSV button (downloads cost report)

4. ✅ **Workers Page:**
   - Path: `/workers`
   - Components:
     - Worker status cards: Active workers, idle workers, failed workers
     - Worker table: Worker name, status, tasks completed, queue size, last heartbeat
     - Queue depth chart (Recharts LineChart): Queue size over last hour
   - Data fetched from `/api/v1/workers/status`
   - Polling: refresh every 3 seconds (real-time critical)

**And** all pages support dark mode
**And** all charts responsive (scale to container width)
**And** all tables support sorting and filtering
**And** empty states show when no data (e.g., "No executions yet")
**And** role-based UI: viewers see all, operators can pause queue (Story 5)
**And** mobile responsive: tables scroll horizontally, charts adapt

**Prerequisites:** Story 2 (layout and UI primitives exist)

**Technical Notes:**
- Use Recharts for all charts (responsive, accessible)
- Use TanStack Table for data tables (sorting, filtering, pagination)
- Use React Query for data fetching (caching, polling, background refetch)
- Use date-fns for date formatting (lighter than Moment.js)
- Loading skeletons: use Skeleton component from Story 2
- Error boundaries: use ErrorBoundary component from Story 2
- Polling: React Query refetchInterval option
- Empty states: use EmptyState component with icon + message

**Test Strategy:**
- Component tests for each page: render, data fetch, loading, error
- Test charts render with mock data
- Test tables: sort column, filter rows, pagination
- Test polling: mock API, verify refetch every N seconds
- Test role-based UI: hide elements based on role
- E2E test: login → navigate to dashboard → verify metrics display
- Coverage target: 70%+ for page components

---

### Story 4: Core Pages - Configuration

**As a** tenant admin,
**I want** configuration pages (tenants, agents, LLM providers, MCP servers),
**So that** I can manage platform configuration in a modern UI.

**Acceptance Criteria:**

**Given** we have monitoring pages and UI primitives
**When** we build configuration pages
**Then** we should have:

1. ✅ **Tenants Page:**
   - List: `/tenants` - table with tenant name, ID, agent count, created date, actions
   - Detail: `/tenants/[id]` - tenant details, edit form, delete button
   - Create: `/tenants/new` - create tenant form
   - Components:
     - TenantTable: sortable, filterable (search by name), pagination
     - TenantForm: name (required), description, logo upload
   - Data: GET `/api/v1/tenants`, POST/PUT/DELETE
   - Optimistic updates: UI updates before API response, rollback on error
   - Permissions: super_admin + tenant_admin can edit, viewer read-only

2. ✅ **Agents Page:**
   - List: `/agents` - table with agent name, type, status, tools count, last run
   - Detail: `/agents/[id]` - agent config, tools assignment, test button
   - Create: `/agents/new` - create agent form
   - Test: `/agents/[id]/test` - sandbox UI (input message, execute, view output)
   - Components:
     - AgentTable: filter by status (active, inactive), search
     - AgentForm: name, type (dropdown), system prompt (textarea), tools (multi-select)
     - ToolAssignmentUI: drag-and-drop tools from available to assigned
     - TestSandbox: input field, execute button, output display (JSON + formatted)
   - Data: GET `/api/v1/agents`, POST/PUT/DELETE
   - Permissions: tenant_admin + developer can edit, operator read-only

3. ✅ **LLM Providers Page:**
   - List: `/llm-providers` - cards with provider logo, name, models count, status
   - Detail: `/llm-providers/[id]` - provider config, model list, test connection
   - Create: `/llm-providers/new` - add provider form (API key, base URL)
   - Components:
     - ProviderCard: logo, name, status badge, edit/delete actions
     - ProviderForm: name, type (OpenAI, Anthropic, Custom), API key, base URL, models (list)
     - TestConnection: button that sends test request, displays response time + model list
   - Data: GET `/api/v1/llm-providers`, POST/PUT/DELETE
   - Permissions: tenant_admin can edit, operator + developer read-only

4. ✅ **MCP Servers Page:**
   - List: `/mcp-servers` - table with server name, type, status, tools count, health
   - Detail: `/mcp-servers/[id]` - server config, test connection, tool list
   - Create: `/mcp-servers/new` - add server form
   - Components:
     - McpServerTable: filter by status (healthy, unhealthy), search
     - McpServerForm: name, type (HTTP, SSE, stdio), connection config (URL, env vars)
     - TestConnection: button that pings server, displays health status + tools discovered
     - ToolList: list of tools exposed by server with descriptions
   - Data: GET `/api/v1/mcp-servers`, POST/PUT/DELETE
   - Permissions: tenant_admin + developer can edit, operator read-only

**And** all forms validate with Zod schemas (required fields, format validation)
**And** all forms use React Hook Form (error handling, field state)
**And** optimistic UI updates for all CRUD operations
**And** toast notifications for all actions (success/error)
**And** confirmation dialogs for delete operations ("Are you sure?")
**And** role-based access: hide edit/delete buttons based on permissions
**And** mobile responsive: forms stack vertically, tables scroll

**Prerequisites:** Story 3 (monitoring pages exist)

**Technical Notes:**
- Use Zod for form validation (type-safe, composable)
- Use React Hook Form for form state (performance, error handling)
- Use React Query mutations for POST/PUT/DELETE (optimistic updates, rollback)
- Use Headless UI Dialog for modals (accessible, keyboard nav)
- Use Sonner toast for notifications (modern, stackable)
- Optimistic updates: update cache before API response, revert on error
- File upload (tenant logo): use pre-signed S3 URL or base64 encode
- Tool assignment: use react-beautiful-dnd or dnd-kit for drag-and-drop

**Test Strategy:**
- Component tests for each page: render, CRUD operations, validation
- Test forms: fill fields, submit, verify API call, verify toast
- Test optimistic updates: update UI, verify rollback on error
- Test role-based access: hide/show buttons based on role
- Test confirmation dialogs: delete → confirm → verify API call
- E2E test: create agent → assign tools → test agent → verify execution
- Coverage target: 70%+ for page components

---

### Story 5: Operations & Tools Pages

**Status:** ✅ COMPLETED 2025-11-19 (All 6 ACs + comprehensive testing complete)

**As an** operator,
**I want** operations and tools pages (queue, history, audit, plugins, prompts, tools),
**So that** I can manage daily operations and configure advanced features.

**Acceptance Criteria:**

**Given** we have configuration pages and UI primitives
**When** we build operations and tools pages
**Then** we should have:

1. ✅ **Queue Management Page:** ✅ **COMPLETED 2025-11-19**
   - Path: `/operations`
   - Components:
     - Queue status cards: Queue depth, processing rate, avg wait time
     - Pause/Resume button (glassmorphic toggle, only tenant_admin + operator)
     - Queue chart (Recharts LineChart): Queue depth over last hour
     - Task list table: Task ID, agent, status, queued at, actions (cancel)
   - Data: GET `/api/v1/queue/status`, POST `/api/v1/queue/pause`, POST `/api/v1/queue/resume`
   - Polling: refresh every 3 seconds
   - Permissions: operator + tenant_admin can pause/resume, developer read-only
   - **Implementation:** 7 files created (lib/api/queue.ts, lib/hooks/useQueue.ts, 5 components)
   - **Build:** PASSING (297 kB bundle, 0 TypeScript errors, 0 ESLint errors)
   - **Details:** See `docs/sprint-artifacts/5-operations-and-tools-pages.md` AC-1 section

2. ✅ **Execution History Page:** ✅ **COMPLETED 2025-11-19**
   - Path: `/execution-history`
   - Components:
     - Filters: Date range, status (all, success, failed, pending), agent (dropdown)
     - Execution table: Execution ID, agent, status, duration, started at, actions (view details)
     - Detail modal: Full execution details (input, output, error, logs, metadata)
   - Data: GET `/api/v1/executions?status=xxx&agent=xxx&date_from=xxx&date_to=xxx`
   - Pagination: 50 executions per page
   - Export: button to download filtered results as CSV
   - **Implementation:** 6 files created (lib/api/executions.ts, lib/hooks/useExecutions.ts, 3 components, page)
   - **Features:** TanStack Table v8 sortable columns, @uiw/react-json-view for JSON display, PapaParse CSV export, debounced search (500ms)
   - **Build:** PASSING (25.7 kB bundle, 208 kB First Load JS, 0 TypeScript errors, 0 ESLint errors)
   - **Details:** See `docs/sprint-artifacts/5-operations-and-tools-pages.md` AC-2 section

3. ✅ **Audit Logs Page:** ✅ **COMPLETED 2025-11-19**
   - Path: `/audit-logs`
   - Tabs: Auth Events, General Audit
   - Components:
     - Auth Audit table: User, event type (login, logout, password_change), success, IP, user agent, timestamp
     - General Audit table: User, tenant, action (create, update, delete), entity type, entity ID, timestamp
     - Detail modal: Shows old_value vs new_value (JSON diff)
     - Filters: User, tenant, event type, date range
   - Data: GET `/api/v1/audit/auth`, GET `/api/v1/audit/general`
   - Pagination: 100 logs per page
   - Permissions: super_admin + tenant_admin only
   - **Implementation:** 6 files created (lib/api/audit.ts, lib/hooks/useAudit.ts, 3 components, page), 1 file modified (Table.tsx for colSpan)
   - **Features:** Dual-tab interface, jsondiffpatch side-by-side JSON diff, Badge color coding (success/default/warning/error)
   - **Build:** PASSING (0 TypeScript errors, 0 ESLint errors)
   - **Details:** See `docs/sprint-artifacts/5-operations-and-tools-pages.md` AC-3 section

4. ✅ **Plugins Page:** ✅ **COMPLETED 2025-11-19**
   - Path: `/plugins`
   - Components:
     - Plugin table: Name, type (webhook, polling), status, last sync, actions
     - Detail: `/plugins/[id]` - config form, test connection, logs (3 tabs: Configuration, Test Connection, Logs)
     - Create: `/plugins/new` - add plugin form
     - TestConnection: button that triggers test webhook/poll, displays result
   - Data: GET `/api/v1/plugins`, POST/PUT/DELETE
   - Permissions: tenant_admin + developer can edit
   - **Implementation:** 8 files created (lib/api/plugins.ts, lib/hooks/usePlugins.ts, 4 components, 3 pages)
   - **Build:** PASSING (6.97 kB list page, 9.49 kB detail page, 0 TypeScript errors)

5. ✅ **System Prompts Page:** ✅ **COMPLETED 2025-11-19**
   - Path: `/prompts`
   - Components:
     - Prompt list: cards with prompt name, variables, last updated
     - Detail: `/prompts/[id]` - editor (CodeMirror), preview, save
     - Editor features: syntax highlighting, variable autocomplete ({{variable}}), preview with test data
     - Preview pane: shows prompt with substituted variables (60/40 split-pane layout)
   - Data: GET `/api/v1/prompts`, PUT `/api/v1/prompts/[id]`
   - Permissions: tenant_admin + developer can edit
   - **Implementation:** 7 files created (lib/api/prompts.ts with extractVariables(), lib/hooks/usePrompts.ts, 2 components, 3 pages)
   - **Features:** CodeMirror @uiw/react-codemirror v4.25.3, real-time variable extraction, live preview with test data substitution
   - **Build:** PASSING (3.19 kB list, 3.04 kB detail, 1.45 kB new, 0 TypeScript errors)

6. ✅ **Add Tool Page:** ✅ **COMPLETED 2025-11-19**
   - Path: `/tools`
   - Components:
     - OpenAPI spec upload: drag-and-drop or file picker (accepts .json, .yaml, .yml, max 5MB)
     - Validation: parses spec with js-yaml, validates against OpenAPI 3.0 schema
     - Tool preview: expandable table lists all operations (paths + methods) with HTTP method badges, selection checkboxes, parameter details
     - Import configuration: name prefix, base URL, authentication (none/API key/bearer/basic)
     - Import button: saves tools to database, assigns to tenant
   - Data: POST `/api/v1/tools/import` (multipart/form-data with file)
   - Permissions: tenant_admin + developer only
   - **Implementation:** 8 files created (lib/api/tools.ts, lib/hooks/useTools.ts, 3 components, page)
   - **Features:** Client-side OpenAPI parsing, operation selection with preview, auth configuration form, 4-step wizard
   - **Build:** PASSING (19.7 kB bundle, 0 TypeScript errors, js-yaml and ajv dependencies installed)
   - **Test Coverage:** 99.76% (5 component test files: PromptCards, PromptEditor, OpenAPIUpload, ToolPreview, ImportConfig - 128 tests passing)

**And** all tables support sorting, filtering, pagination
**And** execution detail modal shows full input/output (syntax-highlighted JSON)
**And** audit log diff shows old vs new values side-by-side (JSON diff library)
**And** role-based access enforced on all pages
**And** mobile responsive: tables scroll, forms stack

**Prerequisites:** Story 4 (configuration pages exist)

**Technical Notes:**
- Use TanStack Table for all tables (consistent API)
- Use CodeMirror or Monaco Editor for prompt editor (syntax highlighting)
- Use react-json-view for JSON display in execution details
- Use jsondiffpatch for audit log diffs
- Use react-dropzone for file uploads
- Use js-yaml to parse YAML OpenAPI specs
- Queue polling: React Query refetchInterval = 3s
- CSV export: use papaparse library to convert JSON to CSV

**Test Strategy:**
- Component tests for each page: render, filters, pagination
- Test queue management: pause/resume, verify API call
- Test execution history: filter by status, date range, agent
- Test audit logs: view details, JSON diff display
- Test plugins: create, test connection, view logs
- Test prompts: edit, preview with variables, save
- Test tools: upload spec, validate, preview operations, import
- E2E test: view execution history → filter by failed → view details
- Coverage target: 70%+ for page components

---

### Story 6: Polish & User Experience

**As a** user of the platform,
**I want** polished UX with feedback widget, keyboard shortcuts, and optimized performance,
**So that** the UI feels professional, fast, and delightful to use.

**Acceptance Criteria:**

**Given** we have all core pages built
**When** we polish the UX and optimize performance
**Then** we should have:

1. ✅ **Feedback Widget:**
   - Floating button (bottom-right): "💬 Feedback" (glassmorphic button)
   - Modal: "How's your experience?" → 3 sentiment buttons (😊 Love it, 😐 It's okay, ☹️ Hate it)
   - After sentiment selection: textarea for comment (optional), submit button
   - Data: POST `/api/v1/feedback` with { page, sentiment, comment }
   - Toast: "Thank you for your feedback!" on submit
   - Permissions: all authenticated users

2. ✅ **Keyboard Shortcuts:**
   - `Cmd+K` (Ctrl+K): Open command palette (search pages, recent items)
   - `Cmd+D` (Ctrl+D): Toggle dark mode
   - `?`: Show keyboard shortcuts modal
   - `Esc`: Close modals, command palette
   - `/`: Focus search input (on pages with search)
   - Arrow keys: Navigate tables, dropdowns
   - Component: `src/components/layout/KeyboardShortcuts.tsx` (modal with all shortcuts)
   - Implementation: use `useHotkeys` hook (react-hotkeys-hook)

3. ✅ **Breadcrumbs Navigation:**
   - Component: `src/components/layout/Breadcrumbs.tsx`
   - Displays: Home → Category → Page (e.g., Home → Configuration → Agents)
   - Auto-generated from route path
   - Clickable links to parent pages
   - Displayed in header on all dashboard pages

4. ✅ **Loading States:**
   - Skeleton screens for all pages (gray boxes mimicking content layout)
   - Spinners for button actions (loading state during API call)
   - Progress bars for long operations (file upload, CSV export)
   - Component: `src/components/ui/Skeleton.tsx`, `src/components/ui/Spinner.tsx`, `src/components/ui/ProgressBar.tsx`

5. ✅ **Confirmation Dialogs:**
   - Component: `src/components/ui/ConfirmDialog.tsx`
   - Used for all destructive actions: delete agent, delete tenant, pause queue
   - Modal: "Are you sure?" + description + Cancel/Confirm buttons
   - Confirm button: red, labeled "Delete" or "Pause"
   - Prevents accidental deletions

6. ✅ **Toast Notification System:**
   - Uses Sonner library (modern, stackable, dismissable)
   - Toast types: success (green), error (red), info (blue), warning (orange)
   - Auto-dismiss after 5 seconds (error stays until dismissed)
   - Max 3 toasts visible at once (stacks vertically)
   - Position: top-right on desktop, top-center on mobile

7. ✅ **Bundle Optimization:**
   - Code splitting: dynamic imports for heavy pages (e.g., execution history)
   - Lazy loading: images use Next.js Image component (lazy, optimized)
   - Tree shaking: remove unused exports, verify with bundle analyzer
   - Target: < 300KB gzipped for initial bundle
   - Analysis: run `npm run build && npm run analyze`

8. ✅ **Error Pages:**
   - 404 page: `src/app/not-found.tsx` - "Page not found" with glassmorphic card + link to dashboard
   - 500 page: `src/app/error.tsx` - "Something went wrong" with retry button + error details (dev mode only)

9. ✅ **Mobile Testing:**
   - Test on real devices: iPhone 13 (iOS 16), Samsung Galaxy S21 (Android 12)
   - Test all pages: dashboard, agents, execution history
   - Test interactions: tenant switcher, navigation, forms, modals
   - Test performance: page load < 3s on 4G, animations 30fps

10. ✅ **E2E Tests:**
    - Playwright tests for critical user flows:
      - `e2e/auth.spec.ts`: Login → verify dashboard → logout
      - `e2e/agents.spec.ts`: Create agent → assign tools → test agent → verify success
      - `e2e/execution-history.spec.ts`: View history → filter by failed → view details
    - Run: `npm run test:e2e`

**And** all keyboard shortcuts documented in modal (press `?`)
**And** command palette searches pages + recent items (fuzzy search)
**And** breadcrumbs auto-generate from URL path
**And** bundle size < 300KB gzipped (verified with webpack-bundle-analyzer)
**And** Lighthouse score 90+ (Performance, Accessibility, Best Practices, SEO)
**And** mobile experience tested on 2 real devices (iPhone, Android)
**And** all E2E tests pass on Chrome, Firefox, Safari

**Prerequisites:** Story 5 (all pages exist)

**Technical Notes:**
- Use Sonner for toasts (modern, performant, stackable)
- Use react-hotkeys-hook for keyboard shortcuts (lightweight)
- Use kbar for command palette (searchable, keyboard nav)
- Use Next.js dynamic imports for code splitting: `const Page = dynamic(() => import('./Page'))`
- Use Next.js Image component for all images (lazy, optimized, WebP)
- Use webpack-bundle-analyzer to identify large dependencies
- Use Playwright for E2E tests (cross-browser, reliable)
- Lighthouse: run `npx lighthouse http://localhost:3000 --view`

**Test Strategy:**
- Component tests for new components: FeedbackWidget, KeyboardShortcuts, Breadcrumbs, ConfirmDialog
- Test keyboard shortcuts: press Cmd+K, verify command palette opens
- Test feedback widget: click button, select sentiment, submit, verify API call
- Test confirmation dialog: delete agent, verify confirmation modal, confirm, verify deletion
- E2E tests (Playwright): 3 critical flows (auth, agents, history)
- Bundle analysis: verify < 300KB gzipped
- Lighthouse audit: verify 90+ score
- Mobile testing: manual testing on 2 real devices
- Coverage target: 70%+ for new components

---

## Epic 4: Documentation, Testing & Launch

**Goal:** Comprehensive testing, user documentation, and phased rollout to production

**Value:** Ensures quality, security, and user readiness before replacing Streamlit, minimizing risks and maximizing adoption.

**Duration:** 2.5 weeks

**Covers FRs:** FR8 (Security), FR9 (Performance, Accessibility), FR10 (Training, Rollout)

**Sequencing:** Must be completed after Epic 3 (all pages exist)

---

### Story 7: Documentation & Training

**As a** user of the new Next.js UI,
**I want** comprehensive documentation and training materials,
**So that** I can quickly learn the new UI and find help when needed.

**Acceptance Criteria:**

**Given** we have completed all pages and features
**When** we create documentation and training materials
**Then** we should have:

1. ✅ **Quick Start Guide (1-page PDF):**
   - `docs/quick-start-guide.pdf` created
   - Sections:
     - Login instructions (URL, credentials, first-time setup)
     - Navigation overview (grouped sidebar, 4 categories, search)
     - Tenant switcher usage (top-right dropdown, search, switching)
     - Keyboard shortcuts table (Cmd+K, Cmd+D, ?, Esc, /)
     - Where to get help (feedback widget, support email)
   - Designed: clean layout, screenshots, 1 page (front/back)

2. ✅ **Video Walkthrough (5 minutes, Loom):**
   - `docs/video-walkthrough.mp4` or Loom link
   - Content:
     - Intro (0:00-0:30): What's new in Next.js UI
     - Dashboard overview (0:30-1:30): Metrics, charts, activity feed
     - Creating an agent (1:30-2:30): Navigate to agents, fill form, assign tools
     - Testing an agent (2:30-3:30): Open test sandbox, execute test, view output
     - Viewing execution history (3:30-4:30): Navigate to history, filter by failed, view details
     - Switching tenants (4:30-5:00): Use tenant switcher, verify context change
   - Recorded: screen recording with voiceover, no background music

3. ✅ **Migration Guide (Streamlit → Next.js):**
   - `docs/migration-guide.md` created
   - Table: Streamlit page → Next.js location → Notes
   - Example rows:
     - Dashboard → Monitoring → Dashboard (same metrics, faster refresh)
     - Tenants → Configuration → Tenants (now has search/filter)
     - Operations → Operations → Queue Management (split into 3 pages)
   - Section: New Features (tenant switcher, dark mode, keyboard shortcuts, mobile)
   - Section: Breaking Changes (authentication required, no K8s basic auth)

4. ✅ **Changelog:**
   - `docs/changelog.md` created
   - Sections:
     - 🎉 New Features (10+ items)
     - ✨ Improvements (5+ items)
     - 🔄 Changes (3+ items)
     - ⚠️ Known Issues (2-3 items)
   - Format: Markdown with emoji, bulleted lists
   - Version: v1.0 - January 2025

5. ✅ **API Documentation:**
   - `docs/api-docs.html` generated with Redocly
   - Source: OpenAPI 3.0 spec auto-generated by FastAPI
   - Includes: All `/api/v1/*` endpoints with request/response schemas, examples, auth requirements
   - Hosted: accessible at `/api/v1/docs` (FastAPI auto-docs)

6. ✅ **Runbooks (3 common issues):**
   - `docs/runbooks/login-issues.md` - troubleshooting login failures (wrong password, account locked, expired token)
   - `docs/runbooks/performance-issues.md` - troubleshooting slow page loads (network, API latency, browser extensions)
   - `docs/runbooks/data-sync-issues.md` - troubleshooting missing data (tenant context, permissions, cache)

7. ✅ **Live Demo Scheduled:**
   - 30-minute Zoom session scheduled 1 week before GA launch
   - Invite sent to all operations team members
   - Agenda: Walkthrough (20 min), Q&A (10 min)
   - Recording: recorded for those who cannot attend

8. ✅ **Pre-Launch Communication:**
   - Email template: `docs/email-launch-announcement.md`
   - Subject: "🎉 New UI Launching Next Week - Here's What You Need to Know"
   - Content: What's changing, why, when, how to prepare, where to get help
   - Sent: 1 week before GA launch

**And** all documentation uses consistent formatting (Markdown, headings, lists)
**And** all screenshots show real data (not Lorem ipsum)
**And** video is < 50MB (compressed, 1080p, 30fps)
**And** migration guide covers all 14 Streamlit pages
**And** API docs generated from OpenAPI spec (auto-updated on API changes)
**And** runbooks tested (reproduces issue, follows steps, resolves issue)

**Prerequisites:** Story 6 (all pages polished)

**Technical Notes:**
- Use Loom for video recording (browser-based, shareable link)
- Use Figma or Canva for quick start guide design
- Use Redocly CLI to generate API docs from OpenAPI spec: `redocly build-docs openapi.yaml --output api-docs.html`
- Quick start guide: export as PDF from Figma/Canva
- Video: record in 1080p, compress with HandBrake to < 50MB

**Test Strategy:**
- Review all documentation with 1 team member (clarity, completeness)
- Test runbooks: follow steps on clean environment, verify resolution
- Verify API docs include all endpoints (compare to `GET /api/v1/openapi.json`)
- Test video playback on different devices (desktop, mobile, tablet)
- Verify links in documentation (no broken links)

---

### Story 8: Testing, Deployment & Rollout

**As a** product owner,
**I want** comprehensive testing and phased rollout,
**So that** we launch with confidence and minimize risks.

**Acceptance Criteria:**

**Given** we have completed all features and documentation
**When** we perform testing and deploy to production
**Then** we should have:

1. ✅ **Load Testing:**
   - Script: `k6-load-test.js` created (see tech-spec section 6.3 for full script)
   - Test scenarios: ramp-up from 10 → 50 → 100 concurrent users over 14 minutes
   - Endpoints tested: login, dashboard metrics, agents list, execution history
   - Thresholds: p95 < 500ms, error rate < 1%
   - Run: `k6 run k6-load-test.js` against staging environment
   - Report: `docs/load-test-results.html` with charts, pass/fail status
   - Result: ✅ All thresholds pass, system stable with 100 users

2. ✅ **Performance Bottlenecks Fixed:**
   - Identify slow endpoints from load test (> 500ms p95)
   - Add database indexes if needed (e.g., on execution_history.created_at)
   - Add Redis caching for expensive queries (e.g., dashboard metrics)
   - Optimize React Query cache settings (staleTime, cacheTime)
   - Re-run load test, verify improvements

3. ✅ **Accessibility Audit:**
   - Run Lighthouse audit on all pages (Performance, Accessibility, Best Practices, SEO)
   - Run axe DevTools on all pages (WCAG 2.1 AA compliance)
   - Report: `docs/accessibility-audit-report.html`
   - Issues: color contrast, missing ARIA labels, keyboard nav
   - Fixed: all critical and high-priority issues (score 90+)

4. ✅ **Cross-Browser Testing:**
   - Test on: Chrome 120+, Firefox 120+, Safari 17+, Edge 120+
   - Test pages: dashboard, agents, execution history, login
   - Test features: glassmorphism fallback, dark mode, forms, modals
   - Document issues: `docs/cross-browser-issues.md`
   - Fixed: all blocking issues (layout breaks, JS errors)

5. ✅ **Production Docker Image:**
   - Dockerfile: `nextjs-ui/Dockerfile` with multi-stage build (build → prod)
   - Base image: node:20-alpine
   - Build: `npm run build` → standalone output
   - Image size: < 200MB (optimized with .dockerignore)
   - Test: `docker build -t nextjs-ui . && docker run -p 3000:3000 nextjs-ui`

6. ✅ **Staging Deployment:**
   - Deploy to staging environment (same infrastructure as prod)
   - Environment: Render.com (or AWS/Vercel)
   - URL: https://staging-ai-agents.example.com
   - Configuration: staging env vars (.env.staging)
   - Smoke tests: login, view dashboard, create agent, view history

7. ✅ **Phase 1: Alpha Rollout (1 week):**
   - Users: 3 power users (1 from each team: Ops, Dev, Leadership)
   - Access: alpha.ai-agents.example.com or staging URL
   - Communication: Email with login instructions + feedback form
   - Feedback: daily check-ins, feedback widget, direct messages
   - Success criteria: NPS 7+, zero blocking bugs
   - Fallback: Streamlit still available at /admin-legacy

8. ✅ **Alpha Feedback Collection & Bug Fixes:**
   - Review feedback widget submissions
   - Triage bugs by severity (blocking, high, medium, low)
   - Fix all blocking bugs (cannot complete critical workflows)
   - Fix high-priority bugs (workarounds exist)
   - Re-test after fixes

9. ✅ **Phase 2: Beta Rollout (1 week):**
   - Users: 10 users (50% of operations team)
   - Communication: Email announcement + live demo session
   - Beta badge: displayed in header ("Beta" badge, link to feedback)
   - Feedback: feedback widget, NPS survey (after 3 days)
   - Success criteria: 80% prefer Next.js over Streamlit, < 5 bugs reported
   - Fallback: users can switch back to Streamlit

10. ✅ **Beta Feedback Collection & Bug Fixes:**
    - Review NPS survey results (target: 80%+ prefer Next.js)
    - Review bug reports (target: < 5 new bugs)
    - Fix all critical bugs
    - Improve UX based on feedback (e.g., adjust polling interval, improve loading states)

11. ✅ **Phase 3: General Availability (All Users):**
    - Users: all operations team members (20 users)
    - Communication: email announcement 2 days before, Slack notification
    - Launch: redirect /admin → /dashboard (Next.js becomes default)
    - Beta badge: removed from header
    - Fallback: Streamlit available at /admin-legacy (read-only for 2 weeks)

12. ✅ **GA Monitoring (First 2 Weeks):**
    - Monitor metrics: daily active users, pages per session, error rate, page load time
    - Track success metrics: NPS 8+, 90% daily login rate, < 5 support tickets
    - Weekly review: team standup to discuss issues, feedback, wins
    - Adjust: fix bugs, improve UX based on feedback

13. ✅ **Phase 4: Decommission Streamlit (2 Weeks After GA):**
    - Communication: email 1 week before decommissioning
    - Action: redirect /admin-legacy → /dashboard
    - Action: remove Streamlit code from codebase
    - Action: update documentation (remove Streamlit references)

**And** load test report shows p95 < 500ms, error rate < 1%
**And** accessibility audit shows Lighthouse score 90+
**And** cross-browser testing passes on Chrome, Firefox, Safari, Edge
**And** Docker image builds successfully and runs locally
**And** staging deployment successful and smoke tests pass
**And** alpha users: 3 users test for 1 week, NPS 7+
**And** beta users: 10 users test for 1 week, 80% prefer Next.js
**And** GA: 90% daily login rate, NPS 8+
**And** Streamlit decommissioned 2 weeks after GA

**Prerequisites:** Story 7 (documentation complete)

**Technical Notes:**
- k6 for load testing (lightweight, scriptable, grafana integration)
- Lighthouse CLI: `npx lighthouse https://example.com --view`
- axe DevTools: browser extension for accessibility testing
- Docker: multi-stage build to reduce image size
- Render.com: deploy Next.js with `render.yaml` config
- NPS survey: in-app modal after 3 days of usage (track in database)
- Success metrics: track in Next.js Analytics or custom analytics table

**Test Strategy:**
- Load test: run against staging with 100 concurrent users
- Accessibility: run Lighthouse + axe on all pages, fix critical issues
- Cross-browser: manual testing on 4 browsers, document issues
- Smoke tests: automated Playwright tests for critical flows
- Rollout: track metrics daily, review weekly
- Bug fixes: prioritize by severity, test after fixes

---

### Story 8.5: Security Testing

**As a** security engineer,
**I want** comprehensive security testing before GA launch,
**So that** we validate the security posture and fix vulnerabilities.

**Acceptance Criteria:**

**Given** we are about to launch to all users
**When** we perform security testing
**Then** we should have:

1. ✅ **OWASP ZAP Automated Scan:**
   - Tool: OWASP ZAP (Zed Attack Proxy)
   - Scan: full scan of staging environment (https://staging-ai-agents.example.com)
   - Duration: 2-4 hours (automated)
   - Report: `docs/security-test-report.html` with findings by severity
   - Result: no high-severity vulnerabilities

2. ✅ **Manual Penetration Testing:**
   - Authentication bypass attempts:
     - Try accessing /dashboard without token → expect 401
     - Try invalid JWT token → expect 401
     - Try expired JWT token → expect 401
     - Try tampered JWT token (change user_id) → expect 401
     - Try accessing other tenant's data → expect 403 or 404
   - Authorization bypass attempts:
     - Login as viewer → try to edit agent → expect 403
     - Login as operator → try to delete tenant → expect 403
     - Login as developer → try to assign roles → expect 403
   - Brute force testing:
     - Try 10 failed logins → expect rate limit 429 after 5 attempts
     - Wait 15 minutes → try again → expect login to work

3. ✅ **SQL Injection Testing:**
   - Test all text inputs with SQL injection payloads:
     - Login email: `' OR '1'='1`
     - Search agents: `'; DROP TABLE agents; --`
     - Filter execution history: `1' UNION SELECT * FROM users --`
   - Result: all payloads blocked (parameterized queries used)

4. ✅ **XSS Testing:**
   - Test all text inputs with XSS payloads:
     - Agent name: `<script>alert('XSS')</script>`
     - Tenant description: `<img src=x onerror=alert('XSS')>`
     - System prompt: `<svg onload=alert('XSS')>`
   - Result: all payloads sanitized (HTML escaped on display)

5. ✅ **IDOR Testing (Insecure Direct Object Reference):**
   - Test accessing other tenant's resources:
     - Login as tenant A → try `GET /api/v1/agents/{tenant_B_agent_id}` → expect 403 or 404
     - Try changing tenant_id in request body → expect validation error
   - Result: all requests filtered by tenant_id, no cross-tenant access

6. ✅ **JWT Token Tampering:**
   - Test modifying JWT payload:
     - Change user_id in payload → sign with incorrect secret → expect 401
     - Change default_tenant_id → sign with correct secret → expect backend re-validates from DB
     - Replay old token after logout → expect 401 (token in blacklist)
   - Result: all tampering attempts blocked

7. ✅ **Rate Limiting Effectiveness:**
   - Test login endpoint: 10 requests in 1 minute → expect 429 after 5 attempts
   - Test register endpoint: 5 requests in 1 hour → expect 429 after 3 attempts
   - Test forgot-password: 5 requests in 1 hour → expect 429 after 3 attempts
   - Result: all rate limits enforced (SlowAPI working)

8. ✅ **RBAC Enforcement:**
   - Test permission matrix (see tech-spec for full matrix):
     - Viewer: cannot edit agents → expect 403
     - Operator: can pause queue → expect 200
     - Developer: can test agents → expect 200
     - Tenant Admin: can assign roles → expect 200
     - Super Admin: can delete tenants → expect 200
   - Result: all permissions enforced (RBAC middleware working)

9. ✅ **Document Findings:**
   - `docs/security-findings.md` created with:
     - Summary of tests performed
     - List of vulnerabilities found (if any)
     - Severity (critical, high, medium, low)
     - Remediation steps
     - Verification (re-test after fix)

10. ✅ **Fix Critical Vulnerabilities:**
    - All critical findings fixed before GA launch
    - High-priority findings fixed or accepted risk documented
    - Medium/low findings triaged for future sprints

11. ✅ **Re-Test After Fixes:**
    - Run OWASP ZAP scan again
    - Re-test manual penetration tests
    - Verify all critical findings resolved

**And** OWASP ZAP scan shows no high-severity vulnerabilities
**And** all authentication endpoints rate-limited
**And** RBAC enforced (no permission bypass possible)
**And** XSS/SQL injection attempts blocked
**And** JWT tokens cannot be tampered
**And** users cannot access other tenants' data
**And** all critical findings resolved before GA

**Prerequisites:** Story 8 (staging deployed, alpha/beta tested)

**Technical Notes:**
- OWASP ZAP: run in Docker: `docker run -u zap -p 8080:8080 zaproxy/zap-stable zap.sh -daemon`
- Manual testing: use Postman or curl for API testing
- SQL injection: use parameterized queries (SQLAlchemy default)
- XSS: HTML escape all user input on display (React does this by default, but verify)
- IDOR: enforce tenant filtering in all queries (e.g., `.where(Agent.tenant_id == request.state.tenant_id)`)
- JWT tampering: verify signature with secret, re-fetch user from DB to validate tenant access
- Rate limiting: SlowAPI configured in Story 1C

**Test Strategy:**
- Automated: OWASP ZAP full scan (2-4 hours)
- Manual: penetration testing (auth bypass, IDOR, XSS, SQL injection)
- Documentation: record all findings in security-findings.md
- Fixes: prioritize critical/high, fix before GA
- Re-test: run OWASP ZAP + manual tests after fixes
- Sign-off: security engineer approves before GA launch

---

## Summary

**Total Stories:** 8 (Story 0, 1A, 1B, 1C, 2, 3, 4, 5, 6, 7, 8, 8.5)
**Total Duration:** 10-12 weeks
**Total Deliverables:** 50+ files (code, docs, tests, configs)

**Epic Breakdown:**
- **Epic 1:** Pre-Implementation (1 week) - Story 0
- **Epic 2:** Auth Foundation (2 weeks) - Stories 1A, 1B, 1C
- **Epic 3:** UI Core (5 weeks) - Stories 2, 3, 4, 5, 6
- **Epic 4:** Testing & Launch (2.5 weeks) - Stories 7, 8, 8.5

**Critical Path:**
Story 0 → 1A → 1B → 1C → 2 (must be sequential)

**Parallel Work:**
- Stories 3, 4, 5 can be parallel (different pages)
- Frontend (Stories 2-6) can overlap with backend (1A-1C) if 2 developers

**Success Criteria:**
- ✅ All 10 FRs covered by stories
- ✅ All stories have clear acceptance criteria
- ✅ All stories have test strategy
- ✅ Epic structure enables incremental value delivery
- ✅ Phased rollout minimizes risk
- ✅ User training ensures smooth adoption

**Next Steps:**
1. Ravi approves this epic breakdown
2. Ravi answers open questions (see tech-spec section 13)
3. Create GitHub project board with all 8 stories as issues
4. Kick off Story 0: User Research & Design Preparation

---

**Epic Breakdown Complete! 🚀**

This document provides the complete, implementable story breakdown for the Next.js UI migration. Each story is vertically sliced, has clear acceptance criteria, and can be completed by a single developer in one focused session (or one week for larger stories).

**Ready for Phase 4 Implementation!**
