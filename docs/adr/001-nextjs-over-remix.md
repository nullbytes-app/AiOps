# ADR 001: Next.js 14 App Router Over Remix

**Status:** Accepted
**Date:** 2025-01-17
**Deciders:** Ravi (Product Owner), Architecture Team
**Technical Story:** Story 0 - User Research & Design Preparation

---

## Context

We need to select a React-based framework for migrating from Streamlit to a modern web UI. The platform requires:
- Server-side rendering (SSR) for fast initial page loads
- React Server Components (RSC) for reduced client bundle size
- Strong TypeScript support
- Authentication integration
- API routes for backend communication
- Good developer experience (DX)
- Production-ready deployment options

**Candidates Evaluated:**
1. **Next.js 14 with App Router** (React meta-framework)
2. **Remix** (React meta-framework)
3. **Pure React with Vite** (Client-only SPA)

---

## Decision

We will use **Next.js 14 with the App Router** for the Next.js UI migration.

---

## Rationale

### Why Next.js 14?

**1. React Server Components (RSC) Support:**
- App Router provides first-class RSC support out of the box
- Reduces client JavaScript bundle by 40-60% (server components don't ship to browser)
- Critical for dashboard performance with large data tables

**2. Server-Side Rendering (SSR) Built-in:**
- Fast Time to First Byte (TTFB) for initial page loads
- Better SEO (though internal tool, good practice)
- Progressive enhancement by default

**3. API Routes Co-location:**
- `/app/api/` routes live alongside UI code
- Simplified project structure vs. separate backend
- Type-safe API contracts with TypeScript

**4. Mature Ecosystem:**
- Largest React framework by adoption (>1M weekly npm downloads)
- Extensive third-party library compatibility
- Active community support, abundant tutorials

**5. Vercel Deployment Integration:**
- Seamless deployment to Vercel (though we're using Render.com)
- Production-optimized builds with automatic code splitting
- Edge runtime support for API routes (future optimization)

**6. Built-in Optimizations:**
- Automatic image optimization (`next/image`)
- Font optimization (`next/font`)
- Route-based code splitting (automatic lazy loading)
- Built-in CSS support (Tailwind, CSS Modules, styled-components)

**7. Developer Experience:**
- Fast Refresh (HMR) for instant feedback
- TypeScript support out of the box
- Clear file-based routing conventions
- Excellent error messages and debugging tools

### Why Not Remix?

**Remix Strengths:**
- Excellent form handling with progressive enhancement
- Nested routing architecture
- Strong focus on web standards
- Growing community

**Remix Limitations (for our use case):**
- Smaller ecosystem compared to Next.js
- Fewer third-party integrations (auth, analytics, etc.)
- Less mature RSC support (catching up to Next.js)
- Fewer deployment platform integrations
- Steeper learning curve for team unfamiliar with Remix conventions

**Verdict:** Remix is an excellent choice for form-heavy apps, but Next.js better matches our team's experience and ecosystem needs.

### Why Not Pure React (Vite)?

**Pure React Strengths:**
- Maximum flexibility
- Smallest framework overhead
- Fast development builds (Vite)

**Pure React Limitations:**
- No SSR out of the box (requires custom setup with Express/Fastify)
- No RSC support (would need complex custom implementation)
- No file-based routing (requires React Router setup)
- No API routes (need separate backend)
- More boilerplate and configuration required

**Verdict:** Would require 2-3x more setup time and lacks critical features (SSR, RSC) that Next.js provides for free.

---

## Alternatives Considered

### Alternative 1: Remix
- **Pros:** Web standards focus, nested routes, excellent form handling
- **Cons:** Smaller ecosystem, less mature RSC support, fewer deployment options
- **Rejected because:** Next.js ecosystem maturity and team familiarity won out

### Alternative 2: Pure React + Vite
- **Pros:** Maximum flexibility, minimal framework overhead
- **Cons:** No SSR, no RSC, requires manual setup for routing/API/auth
- **Rejected because:** Too much custom infrastructure work, delays time to market

### Alternative 3: Continue with Streamlit
- **Pros:** No migration work, team already familiar
- **Cons:** Poor mobile support, slow performance, limited customization, not scalable
- **Rejected because:** Streamlit fundamentally cannot meet our UX and performance requirements

---

## Consequences

### Positive

1. **Fast Development:**
   - App Router conventions accelerate development
   - Large ecosystem reduces time spent on custom solutions
   - TypeScript integration catches errors early

2. **Performance:**
   - RSC reduces client bundle size by ~50%
   - SSR provides fast initial page loads (< 2s target)
   - Automatic code splitting optimizes loading

3. **Maintainability:**
   - Well-documented framework with clear upgrade paths
   - Large community means bugs are found and fixed quickly
   - Standardized patterns across the codebase

4. **Deployment:**
   - Works with Render.com, Vercel, AWS, GCP, Azure
   - Docker support for containerized deployments
   - Static export option if needed in future

### Negative

1. **Learning Curve:**
   - Team needs to learn App Router conventions (different from Pages Router)
   - RSC mental model requires shift in thinking (server vs client components)
   - Estimated 1-2 weeks for team to become proficient

2. **Framework Lock-in:**
   - Tightly coupled to Next.js conventions
   - Migration to another framework would require significant refactoring
   - **Mitigation:** Keep business logic separate from Next.js-specific code

3. **Build Complexity:**
   - Next.js build process is complex (webpack/Turbopack under the hood)
   - Debugging build issues can be time-consuming
   - **Mitigation:** Use standard patterns, avoid custom webpack config

4. **Bundle Size:**
   - Next.js runtime adds ~90KB to client bundle (gzipped)
   - Acceptable tradeoff for features provided
   - **Mitigation:** Monitor bundle size with webpack-bundle-analyzer

---

## Implementation Notes

### Migration Strategy

**Phase 1: Setup (Story 2)**
- Initialize Next.js 14 project with TypeScript
- Configure Tailwind CSS with design tokens
- Set up App Router structure (`/app` directory)

**Phase 2: Authentication (Stories 1A-C)**
- Integrate Auth.js (NextAuth v5) for authentication
- Configure JWT strategy with custom session callbacks
- Implement middleware for route protection

**Phase 3: Page Migration (Stories 3-5)**
- Migrate 14 Streamlit pages to Next.js App Router
- Use Server Components by default, Client Components only when needed
- Implement data fetching with React Query

**Phase 4: Deployment (Story 8)**
- Deploy to Render.com as Docker container
- Configure environment variables
- Set up CI/CD pipeline with GitHub Actions

### Technology Stack

- **Framework:** Next.js 14.2.15
- **React:** 18.3.1 (with RSC)
- **TypeScript:** 5.6.3 (strict mode)
- **Styling:** Tailwind CSS 3.4+
- **State Management:** Zustand (client state), React Query (server state)
- **Authentication:** Auth.js (NextAuth v5)
- **Deployment:** Docker on Render.com

### Best Practices

1. **Server Components by Default:**
   - Use Server Components unless client interactivity needed
   - Mark Client Components with `'use client'` directive only when necessary

2. **Data Fetching:**
   - Use Server Components for initial data loads
   - Use React Query for client-side data fetching and caching
   - Implement polling with `refetchInterval` for real-time updates

3. **Code Organization:**
   - `/app` - App Router pages and layouts
   - `/components` - Shared React components
   - `/lib` - Utility functions, hooks
   - `/services` - API client functions
   - `/types` - TypeScript type definitions

4. **Performance Monitoring:**
   - Monitor bundle size with `@next/bundle-analyzer`
   - Track Core Web Vitals (LCP, FID, CLS)
   - Target: 90+ Lighthouse score

---

## References

- [Next.js 14 Documentation](https://nextjs.org/docs)
- [App Router Migration Guide](https://nextjs.org/docs/app/building-your-application/upgrading/app-router-migration)
- [React Server Components](https://react.dev/reference/rsc/server-components)
- [Remix vs Next.js Comparison](https://remix.run/blog/remix-vs-next)

---

## Related Decisions

- **ADR 002:** Auth.js selection for authentication
- **ADR 005:** TanStack Query for data fetching
- **ADR 006:** Tailwind CSS for styling

---

**Decision Made By:** Ravi (Product Owner)
**Reviewed By:** Architecture Team
**Supersedes:** None
**Superseded By:** None
