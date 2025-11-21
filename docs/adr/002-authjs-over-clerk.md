# ADR 002: Auth.js (NextAuth v5) Over Clerk for Internal Tool Authentication

**Status:** Accepted
**Date:** 2025-01-17
**Deciders:** Ravi (Product Owner), Architecture Team
**Technical Story:** Story 0 - User Research & Design Preparation

---

## Context

The Next.js UI requires user authentication and authorization with:
- JWT-based session management
- Role-based access control (RBAC) with 5 roles
- Multi-tenant support (tenant switcher)
- Password reset and account lockout
- Integration with existing FastAPI backend (PostgreSQL user database)

**Candidates Evaluated:**
1. **Auth.js (NextAuth v5)** - Open source, self-hosted
2. **Clerk** - Managed authentication SaaS
3. **Auth0** - Enterprise authentication SaaS
4. **Custom Auth** - Build from scratch

**Key Consideration:** This is an **internal operations tool** (20 users), not a public-facing product.

---

## Decision

We will use **Auth.js (NextAuth v5)** for authentication in the Next.js UI.

---

## Rationale

### Why Auth.js?

**1. Zero Cost for Internal Tool:**
- Auth.js is **100% open source and free**
- Clerk pricing: $25/month for 20 users ($300/year minimum)
- Auth0 pricing: ~$240/year for 20 users
- **Savings:** $240-300/year for a 20-user internal tool

**2. Self-Hosted = Full Control:**
- User data stays in our PostgreSQL database (existing backend)
- No third-party service dependency
- Complete control over authentication flow
- Custom password policies, lockout logic, audit logs

**3. Integration with Existing Backend:**
- Auth.js can authenticate against **our existing FastAPI `/api/v1/auth/*` endpoints**
- Reuses existing user database (users, roles, tenants)
- No data migration or dual user management needed

**4. Flexibility for Custom Requirements:**
- Multi-tenant context switching (tenant switcher in header)
- Roles fetched on-demand from database (not stored in JWT)
- Custom session callbacks for tenant-specific data
- Easy to implement account lockout, password expiry

**5. NextAuth v5 Modern Features:**
- Built for Next.js 14 App Router
- Edge runtime support
- TypeScript-first with excellent type inference
- Middleware-based route protection

**6. No Vendor Lock-in:**
- Open source means we own the implementation
- Can customize or replace without breaking changes
- Source code is auditable for security

### Why Not Clerk?

**Clerk Strengths:**
- Beautiful pre-built UI components
- Excellent developer experience
- Built-in user management dashboard
- Social auth providers out of the box

**Clerk Limitations (for our use case):**
- **Cost:** $25/month minimum ($300/year) for internal tool with 20 users
- **External dependency:** Requires internet connectivity to Clerk servers
- **Data location:** User data stored on Clerk servers (compliance risk for internal tool)
- **Overkill:** Pre-built UI and social auth not needed for internal ops tool
- **Integration complexity:** Would require syncing users between Clerk and our PostgreSQL database

**Verdict:** Clerk is excellent for customer-facing products but unnecessary cost and complexity for internal tool.

### Why Not Auth0?

**Auth0 Strengths:**
- Enterprise-grade features (SSO, MFA, SAML)
- Mature product with extensive docs
- Strong security track record

**Auth0 Limitations:**
- **Cost:** $240+/year for 20 users (B2B pricing)
- **Complexity:** Enterprise features not needed for internal tool
- **Integration:** Similar sync issues as Clerk
- **Overhead:** Requires Auth0 account management

**Verdict:** Enterprise solution for enterprise problems. We don't have those problems.

### Why Not Custom Auth?

**Custom Auth Strengths:**
- Complete control
- Zero external dependencies

**Custom Auth Limitations:**
- **Time investment:** 2-3 weeks to build securely
- **Security risk:** Easy to introduce vulnerabilities (password storage, session management, CSRF)
- **Maintenance burden:** Ongoing updates for security patches
- **Reinventing wheel:** Auth.js already solves this well

**Verdict:** Not worth the time and risk when Auth.js exists.

---

## Alternatives Considered

### Alternative 1: Clerk
- **Pros:** Beautiful UI, great DX, managed service
- **Cons:** $300/year cost, vendor lock-in, data externalization
- **Rejected because:** Cost and complexity unjustified for 20-user internal tool

### Alternative 2: Auth0
- **Pros:** Enterprise features, battle-tested, SSO support
- **Cons:** $240/year cost, overkill for internal tool
- **Rejected because:** Don't need enterprise features (no SSO, SAML required)

### Alternative 3: Supabase Auth
- **Pros:** Open source, includes database
- **Cons:** Requires migrating from PostgreSQL to Supabase, changes backend architecture
- **Rejected because:** Don't want to change existing backend infrastructure

### Alternative 4: Custom Implementation
- **Pros:** Maximum flexibility, zero dependencies
- **Cons:** 2-3 weeks development time, security risk, maintenance burden
- **Rejected because:** Auth.js provides same benefits with proven security

---

## Consequences

### Positive

1. **Cost Savings:**
   - $0 authentication cost vs. $240-300/year for SaaS
   - No per-user pricing concerns as team scales to 30-40 users

2. **Data Privacy:**
   - All user data remains in our PostgreSQL database
   - No PII sent to third-party services
   - Simplified compliance (internal tool = no GDPR concerns)

3. **Integration Simplicity:**
   - Auth.js Credentials Provider calls our existing FastAPI `/api/v1/auth/login` endpoint
   - No user data sync between systems
   - Reuses existing password hashing, lockout logic, audit logs

4. **Customization:**
   - Full control over session structure
   - Custom callbacks for multi-tenant context
   - Easy to implement "switch tenant" feature
   - Can modify authentication flow as needs change

5. **Development Velocity:**
   - Auth.js has excellent Next.js 14 integration
   - Minimal configuration for JWT strategy
   - Middleware for route protection works out of the box

### Negative

1. **No Pre-built UI:**
   - Need to build login/register forms ourselves
   - **Mitigation:** Design system (Story 0) includes form components. Simple login form takes 1-2 hours.

2. **Self-Managed Security:**
   - Responsible for keeping Auth.js updated
   - Must monitor for security advisories
   - **Mitigation:** Auth.js is widely used (>24k GitHub stars), security issues are found and patched quickly. Subscribe to GitHub security advisories.

3. **No Built-in User Management UI:**
   - No admin dashboard for managing users (unlike Clerk/Auth0)
   - **Mitigation:** Build simple user management page in Next.js (Story 1C includes `/users` CRUD endpoints)

4. **Session Management Complexity:**
   - Need to implement JWT refresh token logic
   - Must handle token expiration gracefully
   - **Mitigation:** Auth.js provides refresh token rotation out of the box

---

## Implementation Notes

### Auth.js Configuration

**Session Strategy: JWT**
```typescript
// /app/lib/auth.ts
import NextAuth from "next-auth"
import CredentialsProvider from "next-auth/providers/credentials"

export const { handlers, auth, signIn, signOut } = NextAuth({
  providers: [
    CredentialsProvider({
      name: "Credentials",
      credentials: {
        email: { label: "Email", type: "email" },
        password: { label: "Password", type: "password" }
      },
      async authorize(credentials) {
        // Call FastAPI /api/v1/auth/login endpoint
        const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/auth/login`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            email: credentials.email,
            password: credentials.password
          })
        })

        const data = await res.json()

        if (res.ok && data.user) {
          return {
            id: data.user.id,
            email: data.user.email,
            defaultTenantId: data.user.default_tenant_id,
            accessToken: data.access_token
          }
        }
        return null
      }
    })
  ],
  callbacks: {
    async jwt({ token, user }) {
      if (user) {
        token.accessToken = user.accessToken
        token.userId = user.id
        token.defaultTenantId = user.defaultTenantId
      }
      return token
    },
    async session({ session, token }) {
      session.user.id = token.userId
      session.user.defaultTenantId = token.defaultTenantId
      session.accessToken = token.accessToken
      return session
    }
  },
  pages: {
    signIn: "/auth/login",
    error: "/auth/error"
  },
  session: {
    strategy: "jwt",
    maxAge: 7 * 24 * 60 * 60 // 7 days
  }
})
```

### Route Protection

**Middleware:**
```typescript
// /middleware.ts
import { auth } from "@/lib/auth"
import { NextResponse } from "next/server"

export default auth((req) => {
  if (!req.auth && req.nextUrl.pathname.startsWith("/dashboard")) {
    return NextResponse.redirect(new URL("/auth/login", req.url))
  }
})

export const config = {
  matcher: ["/dashboard/:path*"]
}
```

### Multi-Tenant Context

**Session Callback:**
```typescript
// Fetch user's role for selected tenant on each request
async session({ session, token }) {
  const tenantId = session.selectedTenantId || token.defaultTenantId

  // Fetch role from FastAPI /api/v1/users/me/role?tenant_id=xxx
  const res = await fetch(
    `${process.env.API_URL}/api/v1/users/me/role?tenant_id=${tenantId}`,
    { headers: { Authorization: `Bearer ${token.accessToken}` } }
  )

  const data = await res.json()
  session.user.role = data.role
  session.user.tenantId = tenantId

  return session
}
```

### Technology Stack

- **Auth Library:** Auth.js v5 (NextAuth)
- **Session:** JWT (stored in httpOnly cookie)
- **Token Expiry:** 7 days (access token), 30 days (refresh token)
- **Password Hashing:** bcrypt (handled by FastAPI backend)
- **Backend Integration:** Credentials provider → FastAPI `/api/v1/auth/*` endpoints

### Security Considerations

1. **HTTPS Only:** Enforce in production (Render.com provides SSL)
2. **httpOnly Cookies:** Prevents XSS attacks on JWT
3. **CSRF Protection:** Auth.js handles CSRF tokens automatically
4. **Token Rotation:** Implement refresh token rotation (future enhancement)
5. **Rate Limiting:** FastAPI backend rate-limits login attempts (5 per 15 min)

---

## References

- [Auth.js Documentation](https://authjs.dev/)
- [Next.js 14 Authentication](https://nextjs.org/docs/app/building-your-application/authentication)
- [JWT Best Practices](https://datatracker.ietf.org/doc/html/rfc8725)
- [OWASP Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html)

---

## Related Decisions

- **ADR 001:** Next.js framework selection
- **ADR 003:** JWT roles-on-demand architecture
- **Story 1B:** Auth service implementation in FastAPI backend

---

**Decision Made By:** Ravi (Product Owner)
**Reviewed By:** Architecture Team
**Supersedes:** None
**Superseded By:** None
