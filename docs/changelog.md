# Changelog

## v1.0 - January 2025

### 🎉 New Features

1. **Next.js 14 Modern UI** - Complete rewrite with Server-Side Rendering (SSR), React Server Components (RSC), and Apple Liquid Glass design aesthetic
2. **JWT Authentication** - Secure authentication with email/password login, 7-day access tokens, 30-day refresh tokens
3. **Role-Based Access Control (RBAC)** - 5 roles with granular permissions: Super Admin, Tenant Admin, Operator, Developer, Viewer
4. **Tenant Switcher** - Switch between tenants without logging out (top-right dropdown with search)
5. **Dark Mode** - Toggle between light and dark themes (Cmd+D or moon/sun icon in header)
6. **Command Palette** - Quick navigation and search (Cmd+K for fuzzy search of pages and recent items)
7. **Keyboard Shortcuts** - Full keyboard navigation support (Cmd+K, Cmd+D, ?, Esc, /, arrow keys)
8. **Mobile-Responsive Design** - Bottom navigation, swipe gestures, touch-optimized buttons (tested on iPhone 13, Samsung Galaxy S21)
9. **Real-Time Polling** - Auto-refresh dashboards (5s), queue status (3s), workers (3s) without page reload
10. **Feedback Widget** - In-app feedback collection (💬 button, bottom-right) with sentiment analysis
11. **Glassmorphic UI** - Semi-transparent cards with backdrop blur, animated neural network background (light mode), particle system (dark mode)
12. **Enhanced Data Tables** - Sortable columns, advanced filters, pagination (50 per page), CSV export (TanStack Table v8)
13. **Test Sandbox for Agents** - Live agent testing at `/agents/[id]/test` with input/output display
14. **OpenAPI Tool Upload** - Upload OpenAPI specs with client-side validation (js-yaml parser)
15. **System Prompt Editor** - CodeMirror-based editor with live preview and variable substitution

### ✨ Improvements

1. **80% Bundle Size Reduction** - Next.js optimized build (< 300KB gzipped initial bundle vs 1.5MB Streamlit)
2. **Page Load Speed** - < 2s initial load, < 500ms p95 API response time (vs 5-8s Streamlit full-page reloads)
3. **Accessibility (WCAG 2.1 AA)** - Full keyboard navigation, ARIA labels, focus states, screen reader support
4. **Error Handling** - Graceful error states with retry buttons, 404/500 custom error pages
5. **Loading States** - Skeleton screens, spinners, progress bars (no blank pages during data fetch)
6. **Form Validation** - Zod schemas, React Hook Form integration, real-time error messages
7. **Optimistic UI Updates** - Instant UI updates on CRUD operations with automatic rollback on error
8. **Confirmation Dialogs** - "Are you sure?" prompts for all destructive actions (delete, pause queue)
9. **Toast Notifications** - Non-blocking success/error messages (Sonner library, max 3 toasts visible)
10. **Breadcrumb Navigation** - Auto-generated breadcrumbs (Home → Category → Page)
11. **Empty States** - User-friendly messages when no data (e.g., "No agents yet. Create your first agent.")
12. **API Versioning** - All endpoints versioned as `/api/v1/*` for backward compatibility

### 🔄 Changes

1. **Authentication Required** - K8s Ingress basic auth replaced with JWT login page (email + password)
2. **URL Structure** - `/admin` → `/dashboard` (Streamlit root changed to Next.js)
3. **RBAC Enforcement** - Some features now restricted based on role (e.g., Viewer cannot edit agents)
4. **Session Management** - Tokens expire after 7 days (auto-logout), refresh tokens valid for 30 days
5. **Rate Limiting** - Login attempts limited to 5 per 15 minutes per IP (account lockout after 5 failed attempts)
6. **Password Policy** - Minimum 12 characters, uppercase, number, special character, no common passwords (zxcvbn score >= 3)

### ⚠️ Known Issues

1. **Lighthouse Audit Pending** - Final performance audit to be run before GA launch (target: 90+ score)
2. **Mobile E2E Tests Limited** - Playwright E2E tests run on desktop only (manual mobile testing completed on 2 real devices)
3. **Streamlit Decommissioning Pending** - `/admin-legacy` remains available (read-only) for 2 weeks after GA launch

---

## Deprecated

- **Streamlit Admin UI** - Will be decommissioned 2 weeks after GA launch (accessible at `/admin-legacy` during transition)
- **K8s Ingress Basic Auth** - Replaced with JWT authentication

---

## Security

- **JWT Secret Rotation** - Ensure `JWT_SECRET` environment variable is at least 32 characters (enforced in settings validation)
- **Password Hashing** - Bcrypt with 10 rounds (balance security vs performance)
- **Account Lockout** - 15-minute lockout after 5 failed login attempts (prevents brute force)
- **Token Blacklist** - Revoked tokens stored in Redis with TTL = token expiration
- **Audit Logging** - All login attempts and CRUD operations logged to `auth_audit_log` and `audit_log` tables
- **RBAC Middleware** - All API endpoints protected with role-based permission checks

---

## Dependencies

### Frontend (New)
- **Next.js** 14.2.15 (App Router, SSR, RSC)
- **React** 18.3.1 (latest stable)
- **TypeScript** 5.6.3 (strict mode)
- **TailwindCSS** 3.4.14 (utility-first styling)
- **NextAuth** 4.24.13 (stable v4, not beta v5)
- **TanStack Query** 5.62.2 (data fetching, caching, polling)
- **TanStack Table** 8.21.3 (sortable, filterable tables)
- **Recharts** 3.3.0 (responsive charts)
- **Zod** 4.1.12 (schema validation)
- **React Hook Form** 7.66.1 (form state management)
- **Framer Motion** 11.11.17 (animations)
- **HeadlessUI** 2.2.9 (accessible components)
- **Lucide React** 0.462.0 (icon library)
- **CodeMirror** (@uiw/react-codemirror 4.25.3) (prompt editor)
- **Sonner** 2.0.7 (toast notifications)
- **Storybook** 10.0.8 (component development)
- **MSW** 2.6.5 (API mocking for tests)
- **Playwright** 1.56.1 (E2E testing)

### Backend (Added)
- **slowapi** >= 0.1.9 (rate limiting for FastAPI)
- **python-jose[cryptography]** >= 3.3.0 (JWT operations)
- **passlib[bcrypt]** >= 1.7.4 (password hashing)
- **zxcvbn** (password strength validation)

---

## Breaking Changes for Developers

### API Changes
- All endpoints now require JWT token in `Authorization: Bearer <token>` header (except `/auth/*` endpoints)
- New `/api/v1/auth/*` endpoints for login, register, refresh, logout
- New `/api/v1/users/*` endpoints for user management
- Rate limiting applied to authentication endpoints (5 attempts/15min for login)

### Database Changes
- New tables: `users`, `user_tenant_roles`, `auth_audit_log`, `audit_log`
- New indexes: `users.email` (unique), `user_tenant_roles (user_id, tenant_id)` (composite unique)
- New migrations: `alembic/versions/015_add_auth_tables.py`

### Environment Variables (New)
- `JWT_SECRET` - Secret key for signing JWT tokens (min 32 characters, **REQUIRED**)
- `ACCESS_TOKEN_EXPIRE_MINUTES` - Access token expiration (default: 10080 = 7 days)
- `REFRESH_TOKEN_EXPIRE_MINUTES` - Refresh token expiration (default: 43200 = 30 days)

---

## Migration Guide

See [`docs/migration-guide.md`](./migration-guide.md) for complete Streamlit → Next.js migration instructions.

---

## Contributors

- **Bob** (Scrum Master) - Epic planning, story breakdown, workflow facilitation
- **Ravi** (Product Owner) - Requirements, user research, acceptance criteria validation
- **Dev Team** - Implementation (Stories 0-8.5)

---

**Generated:** January 2025
**Version:** 1.0 (GA Release)
