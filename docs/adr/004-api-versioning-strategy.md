# ADR 004: URL-Based API Versioning (`/api/v1/*`)

**Status:** Accepted
**Date:** 2025-01-17
**Deciders:** Ravi (Product Owner), Architecture Team
**Technical Story:** Story 0 - User Research & Design Preparation

---

## Context

The AI Agents Platform has an existing FastAPI backend with **unversioned API endpoints**:
```
POST /auth/login
GET /agents
GET /executions
```

We're migrating the UI from Streamlit to Next.js, and will be adding **new endpoints** for authentication, user management, and RBAC:
```
POST /api/v1/auth/login
GET /api/v1/users/me/role
POST /api/v1/users/{user_id}/roles
```

**Key Questions:**
1. Should we version the new API endpoints?
2. What versioning strategy should we use?
3. How do we handle backward compatibility with existing Streamlit endpoints?

---

## Decision

We will use **URL-based API versioning** with the `/api/v1/*` prefix for all **new endpoints**.

**Versioning Strategy:**
- **New endpoints:** `/api/v1/*` (versioned)
- **Existing endpoints:** Remain unversioned (Streamlit compatibility)
- **Future major changes:** Introduce `/api/v2/*` when needed

**Examples:**
```
✅ NEW (Next.js UI):
POST /api/v1/auth/login
POST /api/v1/auth/register
GET /api/v1/users/me/role?tenant_id=xxx
POST /api/v1/users/{user_id}/roles

✅ EXISTING (Streamlit compatibility):
GET /agents
POST /executions
GET /metrics/summary
```

---

## Rationale

### Why URL-Based Versioning?

**1. Clarity and Explicitness:**
- Version is immediately visible in the URL
- Developers know which version they're calling: `fetch('/api/v1/users')`
- Easy to identify breaking changes vs. backward-compatible changes

**2. Browser-Friendly:**
- Works in browsers (no custom headers needed)
- Can test in browser address bar: `https://api.example.com/api/v1/users`
- Swagger/OpenAPI docs display version clearly

**3. Caching-Friendly:**
- CDNs and proxies cache based on URL
- Different versions can have different cache policies
- No header parsing required

**4. Client Simplicity:**
- No need to set custom headers on every request
- Works with simple `fetch()` calls
- No special HTTP client configuration

**5. Migration Path:**
- Gradual migration: v1 and v2 coexist
- Deprecate v1 after v2 adoption
- Clear sunset timeline: "v1 EOL: 2026-12-31"

### Why Keep Existing Endpoints Unversioned?

**Backward Compatibility:**
- Streamlit UI still runs in production (during migration)
- Changing URLs would require updating all Streamlit code
- Risk of breaking existing functionality

**Strategy:**
```
Phase 1 (Now): Next.js calls /api/v1/*, Streamlit calls unversioned endpoints
Phase 2 (Beta): Both UIs running, both endpoints active
Phase 3 (GA): Next.js default, Streamlit deprecated
Phase 4 (Decommission): Remove Streamlit, consider deprecating unversioned endpoints
```

**Trade-off:** Temporary inconsistency (some versioned, some not) for zero-risk migration.

### Why Not Header-Based Versioning?

**Alternative: Use `Accept: application/vnd.api.v1+json` header**

**Pros:**
- Cleaner URLs (no version in path)
- RESTful purist approach
- Single endpoint with multiple versions

**Cons:**
- **Not browser-friendly:** Can't test in address bar
- **Harder to debug:** Version not visible in network logs (must inspect headers)
- **Caching complexity:** CDNs must cache based on headers (more config)
- **Client complexity:** Must set headers on every request
- **Swagger/OpenAPI:** Harder to document multi-version endpoints

**Verdict:** Header-based versioning is elegant in theory, but URL-based is simpler in practice.

### Why Not Query Parameter Versioning?

**Alternative: `/api/users?version=1`**

**Pros:**
- Keeps base URL clean
- Easy to add

**Cons:**
- **Easy to forget:** Client forgets `?version=1` → defaults to latest (breaking changes)
- **Not RESTful:** Query params for versioning is unconventional
- **Routing complexity:** Framework must parse query param to route to correct handler

**Verdict:** Less conventional, more error-prone.

---

## Alternatives Considered

### Alternative 1: Header-Based Versioning
```
GET /api/users
Accept: application/vnd.api.v1+json
```
- **Pros:** Cleaner URLs, RESTful
- **Cons:** Not browser-friendly, harder to debug, client complexity
- **Rejected because:** URL-based is simpler and more visible

### Alternative 2: Query Parameter Versioning
```
GET /api/users?version=1
```
- **Pros:** Keeps base URL clean
- **Cons:** Easy to forget, not RESTful, routing complexity
- **Rejected because:** Less conventional, error-prone

### Alternative 3: Subdomain Versioning
```
https://v1.api.example.com/users
https://v2.api.example.com/users
```
- **Pros:** Clean separation, independent infrastructure per version
- **Cons:** Requires DNS setup, SSL certs per subdomain, infrastructure overhead
- **Rejected because:** Overkill for internal tool, unnecessary complexity

### Alternative 4: No Versioning (Breaking Changes in Place)
```
GET /api/users  // Changes over time, breaks clients
```
- **Pros:** Simplest approach, no version management
- **Cons:** **Breaking changes break all clients**, no migration path, production downtime
- **Rejected because:** Unacceptable for production system

---

## Consequences

### Positive

1. **Clear Migration Path:**
   - Next.js uses `/api/v1/*`
   - Streamlit uses unversioned endpoints
   - Both coexist during migration (zero downtime)

2. **Future-Proof:**
   - When breaking changes needed: introduce `/api/v2/*`
   - Clients migrate at their own pace
   - No forced upgrades (until v1 sunset)

3. **Developer Experience:**
   - Version visible in code: `fetch('/api/v1/users')`
   - Easy to test in browser
   - Clear Swagger docs: `/api/v1/docs`

4. **Debugging:**
   - Network logs show version: `POST /api/v1/auth/login`
   - No need to inspect headers
   - Clear error messages: "v1 deprecated, use v2"

### Negative

1. **URL Length:**
   - Adds 4 characters (`/v1/`) to every new endpoint
   - **Impact:** Negligible (~0.02% increase in request size)

2. **Temporary Inconsistency:**
   - Some endpoints versioned (`/api/v1/*`), some not (`/agents`)
   - **Impact:** Confusing for developers unfamiliar with migration context
   - **Mitigation:** Document clearly in API docs

3. **Routing Complexity:**
   - FastAPI must route both `/api/v1/*` and unversioned endpoints
   - **Impact:** Slightly more complex router configuration
   - **Mitigation:** Use FastAPI `APIRouter` with prefix

4. **Multiple Versions Maintenance:**
   - If v2 is introduced, must maintain both v1 and v2
   - **Impact:** Code duplication, bug fixes in both versions
   - **Mitigation:** Deprecation policy (v1 sunset after 1 year)

---

## Implementation Notes

### FastAPI Backend

**Router Structure:**
```python
# src/api/v1/__init__.py
from fastapi import APIRouter
from .auth import router as auth_router
from .users import router as users_router

v1_router = APIRouter(prefix="/api/v1")
v1_router.include_router(auth_router, prefix="/auth", tags=["auth"])
v1_router.include_router(users_router, prefix="/users", tags=["users"])

# src/main.py
from fastapi import FastAPI
from src.api.v1 import v1_router
from src.api import legacy_router  # Unversioned endpoints

app = FastAPI()
app.include_router(v1_router)  # /api/v1/*
app.include_router(legacy_router)  # /agents, /executions, etc.
```

**Directory Structure:**
```
src/api/
├── v1/                  # Versioned endpoints
│   ├── __init__.py
│   ├── auth.py         # /api/v1/auth/*
│   ├── users.py        # /api/v1/users/*
│   └── agents.py       # /api/v1/agents/* (if needed)
├── agents.py           # Unversioned /agents (Streamlit)
├── executions.py       # Unversioned /executions
└── health.py           # Unversioned /health
```

### Next.js Frontend

**API Client:**
```typescript
// /lib/api-client.ts
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL
const API_VERSION = "v1"

export const apiClient = {
  async get(endpoint: string) {
    const res = await fetch(`${API_BASE_URL}/api/${API_VERSION}${endpoint}`)
    return res.json()
  },
  async post(endpoint: string, data: any) {
    const res = await fetch(`${API_BASE_URL}/api/${API_VERSION}${endpoint}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data)
    })
    return res.json()
  }
}

// Usage:
await apiClient.get("/users/me/role?tenant_id=xxx")  // → /api/v1/users/me/role?tenant_id=xxx
```

### OpenAPI Documentation

**Swagger UI:**
```python
# src/main.py
app = FastAPI(
    title="AI Agents Platform API",
    version="1.0.0",
    docs_url="/api/v1/docs",      # Swagger UI for v1
    redoc_url="/api/v1/redoc",    # ReDoc for v1
    openapi_url="/api/v1/openapi.json"
)
```

**Accessing Docs:**
- Swagger UI: `https://api.example.com/api/v1/docs`
- ReDoc: `https://api.example.com/api/v1/redoc`
- OpenAPI JSON: `https://api.example.com/api/v1/openapi.json`

### Deprecation Policy

**When to introduce v2:**
- Breaking changes that cannot be backward-compatible
- Major architectural refactoring
- Security vulnerabilities requiring redesign

**Example: v1 → v2 Migration**
```
2026-01-01: Announce v1 deprecation (1-year notice)
2026-06-01: v2 released, v1 still supported
2026-12-01: v1 sunset warning (6 months remaining)
2027-01-01: v1 removed (404 on all v1 endpoints)
```

**Deprecation Response:**
```json
// v1 endpoint after deprecation announcement
{
  "deprecated": true,
  "sunset_date": "2027-01-01",
  "migration_guide": "https://docs.example.com/api/v1-to-v2",
  "message": "v1 will be removed on 2027-01-01. Please migrate to v2."
}
```

---

## References

- [REST API Versioning Best Practices](https://restfulapi.net/versioning/)
- [FastAPI Versioning Guide](https://fastapi.tiangolo.com/advanced/sub-applications/)
- [Stripe API Versioning](https://stripe.com/docs/api/versioning) (URL-based example)
- [GitHub API Versioning](https://docs.github.com/en/rest/overview/api-versions) (Header-based example)

---

## Related Decisions

- **ADR 001:** Next.js framework selection
- **ADR 002:** Auth.js for authentication
- **Story 1C:** API endpoint implementation

---

**Decision Made By:** Ravi (Product Owner)
**Reviewed By:** Architecture Team
**Supersedes:** None
**Superseded By:** None
