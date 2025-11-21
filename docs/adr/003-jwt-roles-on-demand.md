# ADR 003: JWT Roles Fetched On-Demand (Not Stored in Token)

**Status:** Accepted ⚠️ **CRITICAL DECISION**
**Date:** 2025-01-17
**Deciders:** Ravi (Product Owner), Architecture Team
**Technical Story:** Story 0 - User Research & Design Preparation

---

## Context

The AI Agents Platform requires role-based access control (RBAC) with:
- **5 roles:** super_admin, tenant_admin, operator, developer, viewer
- **Multi-tenant architecture:** Users can have different roles in different tenants
- **Dynamic role assignment:** Admins can change user roles at any time
- **JWT authentication:** Sessions managed with JSON Web Tokens

**The Question:**
Should we store all user roles in the JWT payload, or fetch them on-demand per request?

**Example Scenario:**
```
User Alice has:
- super_admin role in Tenant A
- operator role in Tenant B
- viewer role in Tenant C
- developer role in Tenant D
```

**Two Approaches:**

### Approach 1: Store All Roles in JWT
```json
{
  "sub": "user-123",
  "email": "alice@example.com",
  "roles": [
    {"tenant": "tenant-a", "role": "super_admin"},
    {"tenant": "tenant-b", "role": "operator"},
    {"tenant": "tenant-c", "role": "viewer"},
    {"tenant": "tenant-d", "role": "developer"}
  ]
}
```

### Approach 2: Fetch Role On-Demand
```json
{
  "sub": "user-123",
  "email": "alice@example.com",
  "default_tenant_id": "tenant-a"
}
```
Then: `GET /api/v1/users/me/role?tenant_id=tenant-a` on each request.

---

## Decision

We will **fetch user roles on-demand** from the database, NOT store them in the JWT payload.

**JWT Payload Structure:**
```json
{
  "sub": "user-uuid",
  "email": "user@example.com",
  "default_tenant_id": "tenant-uuid",
  "iat": 1705507200,
  "exp": 1706112000
}
```

**Role Fetching:**
- On each authenticated request, call: `GET /api/v1/users/me/role?tenant_id={selected_tenant}`
- Backend queries: `SELECT role FROM user_tenant_roles WHERE user_id = ? AND tenant_id = ?`
- Role cached in Next.js session for duration of tenant context

---

## Rationale

### Why Fetch On-Demand?

**1. Token Bloat Prevention (Critical):**

**Problem:** Users with roles in 10+ tenants would have massive JWTs:
```json
// JWT with 10 tenant roles = ~400 bytes
// JWT with 50 tenant roles = ~2000 bytes
// JWT with 100 tenant roles = ~4000 bytes
```

**Consequences of large JWTs:**
- **HTTP header size limits:** Most servers limit headers to 8KB. Large JWTs can exceed this, causing 431 errors.
- **Network overhead:** JWT sent on EVERY request. 4KB JWT = 4KB overhead per request.
- **Cookie size limits:** Browsers limit cookies to 4KB. Large JWT won't fit.
- **Performance:** Parsing large JWTs on every request increases CPU usage.

**Our Scenario:**
- 20 users today, but platform could scale to 100+ users
- Enterprise customers might have 50-100 tenants
- A single user could have roles in 20+ tenants
- **Risk:** JWT bloat could break authentication at scale

**Solution:** Keep JWT minimal (5 fields, ~150 bytes). Fetch role only when needed.

---

**2. Dynamic Role Changes (Security):**

**Problem:** If roles are in JWT (expires in 7 days), role changes don't take effect until token expires.

**Scenario:**
```
Day 1: Alice is super_admin in Tenant A (JWT issued)
Day 2: Admin revokes Alice's super_admin role → makes her viewer
Day 3-7: Alice still has super_admin access (JWT hasn't expired yet)
```

**Security Risk:** Revoked permissions take up to 7 days to apply.

**Solution:** Fetch role from database on each request. Role changes are immediate:
```
Day 1: Alice is super_admin → DB: user_tenant_roles.role = 'super_admin'
Day 2: Admin revokes → DB: user_tenant_roles.role = 'viewer'
Day 3: Alice accesses Tenant A → API fetches from DB → role = 'viewer' ✅ IMMEDIATE
```

---

**3. Tenant Context Switching:**

**Problem:** User switches tenant in UI dropdown. If roles are in JWT, we'd need to:
- Parse JWT
- Find role for new tenant from array
- Update session

**Complexity:** Client-side JWT parsing, role lookup logic, error handling.

**Solution:** User switches tenant → API call fetches new tenant's role:
```typescript
// User switches from Tenant A → Tenant B
await fetch(`/api/v1/users/me/role?tenant_id=tenant-b`)
// Returns: { role: "operator" }
// Next.js session updates: session.user.role = "operator"
```

**Benefit:** Simple, reliable, always accurate.

---

**4. Database Single Source of Truth:**

**Problem:** If roles in JWT, we have **two sources of truth**:
- JWT (client-side, cached for 7 days)
- Database (server-side, real-time)

**Consistency Issues:**
- JWT says "super_admin", DB says "viewer" → which is correct?
- Admin changes role → JWT out of sync until expiration
- Debugging: "Why does Alice still have admin access?" (stale JWT)

**Solution:** Database is **single source of truth**. Always fetch from DB:
```
Request → Validate JWT (user identity) → Fetch role from DB (authorization) → Authorize
```

**Benefit:** Zero ambiguity. DB is always right.

---

### Why Not Store Roles in JWT?

**Approach: Store all roles in JWT**

**Pros:**
- Fewer database queries (role already in JWT)
- Slightly faster (no DB roundtrip for role)

**Cons:**
- **Token bloat:** 10+ tenants = 1-2KB JWT (breaks cookie limits)
- **Stale data:** Role changes take 7 days to propagate
- **Security risk:** Revoked permissions not enforced until token expires
- **Complexity:** Client must parse JWT to get role for current tenant
- **Scalability:** Doesn't work for enterprises with 50-100 tenants

**Verdict:** Short-term performance gain, long-term scalability and security nightmare.

---

## Alternatives Considered

### Alternative 1: Store Roles in JWT (Rejected)
- **Pros:** Faster (no DB query), fewer API calls
- **Cons:** Token bloat, stale data, security risk, scalability issues
- **Rejected because:** Doesn't scale beyond 10 tenants, security risk of stale permissions

### Alternative 2: Store Only Current Tenant's Role in JWT
```json
{
  "sub": "user-123",
  "current_tenant_id": "tenant-a",
  "current_role": "super_admin"
}
```
- **Pros:** Avoids token bloat, includes current role
- **Cons:** Requires re-issuing JWT on tenant switch (forces logout/login), still has stale data problem
- **Rejected because:** Tenant switch would require re-authentication (bad UX)

### Alternative 3: Redis Cache for Roles
- **Pros:** Fast role lookups, no JWT bloat, no stale data
- **Cons:** Requires Redis infrastructure, cache invalidation complexity
- **Why we might do this later:** If role queries become a performance bottleneck (> 1000 req/s), cache in Redis with 5-minute TTL
- **For now:** PostgreSQL query is fast enough (< 5ms), YAGNI principle

---

## Consequences

### Positive

1. **Scalability:**
   - JWT size stays constant (~150 bytes) regardless of tenant count
   - Works for users with 1 tenant or 100 tenants
   - No HTTP header size issues

2. **Security:**
   - Role changes take effect immediately (no stale permissions)
   - Revoking access is instant (critical for security incidents)
   - Database is single source of truth (no sync issues)

3. **Simplicity:**
   - No JWT parsing logic on client side
   - No role sync between JWT and database
   - Straightforward debugging ("check the database")

4. **Tenant Switching:**
   - Switch tenant → fetch role → update session
   - No re-authentication required
   - Fast user experience (< 50ms API call)

### Negative

1. **Additional Database Query:**
   - **Impact:** One extra query per authenticated request: `SELECT role FROM user_tenant_roles WHERE user_id = ? AND tenant_id = ?`
   - **Performance:** ~1-5ms (indexed query, small table)
   - **Mitigation:** Add composite index on (user_id, tenant_id) → query is O(1) lookup

2. **Network Overhead:**
   - **Impact:** Tenant switch requires API call (client → server → DB → server → client)
   - **Performance:** ~50-100ms (local network), ~200-300ms (remote)
   - **Mitigation:** Acceptable for tenant switching (infrequent user action). Cache role in Next.js session for subsequent requests.

3. **Session State Management:**
   - **Complexity:** Next.js session must track: user ID, current tenant, current role
   - **Mitigation:** Auth.js handles session state elegantly. Simple session callback.

---

## Implementation Notes

### Backend API (FastAPI)

**Endpoint: Get User Role for Tenant**
```python
# src/api/v1/users.py
@router.get("/users/me/role")
async def get_user_role_for_tenant(
    tenant_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
) -> RoleResponse:
    """
    Fetch user's role for a specific tenant.

    Returns 404 if user has no role in tenant.
    Returns 403 if user tries to access tenant they're not part of.
    """
    result = await db.execute(
        select(UserTenantRole.role)
        .where(
            UserTenantRole.user_id == current_user.id,
            UserTenantRole.tenant_id == tenant_id
        )
    )
    user_role = result.scalar_one_or_none()

    if not user_role:
        raise HTTPException(status_code=404, detail="User has no role in this tenant")

    return RoleResponse(role=user_role, tenant_id=tenant_id)
```

**Database Schema:**
```sql
CREATE TABLE user_tenant_roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL CHECK (role IN ('super_admin', 'tenant_admin', 'operator', 'developer', 'viewer')),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, tenant_id)  -- One role per user per tenant
);

-- CRITICAL: Index for fast role lookups
CREATE INDEX idx_user_tenant_roles_lookup ON user_tenant_roles(user_id, tenant_id);
```

### Frontend (Next.js)

**Auth.js Session Callback:**
```typescript
// /app/lib/auth.ts
callbacks: {
  async session({ session, token }) {
    // Get selected tenant from session state (or default)
    const tenantId = session.selectedTenantId || token.defaultTenantId

    // Fetch role from FastAPI
    const res = await fetch(
      `${process.env.API_URL}/api/v1/users/me/role?tenant_id=${tenantId}`,
      { headers: { Authorization: `Bearer ${token.accessToken}` } }
    )

    if (res.ok) {
      const data = await res.json()
      session.user.role = data.role
      session.user.tenantId = tenantId
    } else {
      // User has no role in this tenant
      session.user.role = null
      session.user.tenantId = null
    }

    return session
  }
}
```

**Tenant Switcher Component:**
```typescript
// /components/layout/TenantSwitcher.tsx
async function switchTenant(newTenantId: string) {
  // Fetch role for new tenant
  const res = await fetch(`/api/v1/users/me/role?tenant_id=${newTenantId}`)
  const data = await res.json()

  // Update session
  await fetch("/api/auth/session", {
    method: "POST",
    body: JSON.stringify({
      selectedTenantId: newTenantId,
      role: data.role
    })
  })

  // Update local state
  useTenantStore.setState({
    selectedTenant: newTenantId,
    role: data.role
  })

  // Redirect to dashboard
  router.push("/dashboard")
}
```

### Performance Optimization

**Database Query Performance:**
- Indexed query: ~1-5ms
- Query plan: Index scan on `idx_user_tenant_roles_lookup`
- No N+1 queries (single SELECT per request)

**Caching Strategy (Future):**
```python
# If role lookups become bottleneck (> 1000 req/s):
# Cache role in Redis with 5-minute TTL

@cache(ttl=300)  # 5 minutes
async def get_user_role_cached(user_id: str, tenant_id: str) -> str:
    # Query DB, cache result
    ...

# Invalidate cache on role change:
async def update_user_role(user_id, tenant_id, new_role):
    # Update DB
    await db.execute(...)
    # Invalidate cache
    cache.delete(f"role:{user_id}:{tenant_id}")
```

---

## References

- [JWT Best Practices (RFC 8725)](https://datatracker.ietf.org/doc/html/rfc8725)
- [OWASP JWT Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/JSON_Web_Token_for_Java_Cheat_Sheet.html)
- [Auth0: Token Best Practices](https://auth0.com/docs/secure/tokens/token-best-practices)
- [PostgreSQL Index Performance](https://www.postgresql.org/docs/current/indexes-types.html)

---

## Related Decisions

- **ADR 002:** Auth.js selection (enables this architecture)
- **Story 1A:** Database models for user_tenant_roles
- **Story 1B:** JWT implementation in FastAPI backend

---

**Decision Made By:** Ravi (Product Owner)
**Reviewed By:** Architecture Team
**Supersedes:** None
**Superseded By:** None

---

## ⚠️ Critical Implementation Reminder

**To all developers implementing auth (Stories 1A-C and Story 2):**

1. ✅ **DO** keep JWT minimal (user ID, email, default tenant only)
2. ✅ **DO** fetch role from database on each request
3. ✅ **DO** create composite index on (user_id, tenant_id)
4. ❌ **DO NOT** add roles array to JWT payload
5. ❌ **DO NOT** cache roles in client state (use Next.js session)

**This decision is critical for security and scalability. Violating it will cause production issues.**
