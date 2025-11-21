# ADR 005: TanStack Query Over SWR for Data Fetching

**Status:** Accepted
**Date:** 2025-01-17
**Deciders:** Ravi (Product Owner), Architecture Team
**Technical Story:** Story 0 - User Research & Design Preparation

---

## Context

The Next.js UI needs a data fetching library for:
- **Server state management:** Caching API responses
- **Automatic refetching:** Keep data fresh (polling for dashboard metrics)
- **Optimistic updates:** Update UI before API confirms (CRUD operations)
- **Loading and error states:** Manage async data flow
- **Pagination and infinite scroll:** Execution history, agent lists

**Candidates Evaluated:**
1. **TanStack Query (React Query v5)** - Powerful server state library
2. **SWR** - Lightweight stale-while-revalidate library
3. **RTK Query** - Redux Toolkit query API
4. **Apollo Client** - GraphQL client (if we were using GraphQL)

---

## Decision

We will use **TanStack Query v5** (React Query) for all data fetching in the Next.js UI.

---

## Rationale

### Why TanStack Query?

**1. Feature Completeness:**

TanStack Query provides everything we need out of the box:
- **Caching:** Automatic background refetch with stale-while-revalidate
- **Polling:** `refetchInterval` for real-time dashboard updates
- **Mutations:** Optimistic updates for CRUD operations
- **Pagination:** `useInfiniteQuery` for infinite scroll
- **Prefetching:** Server-side data fetching with Next.js RSC
- **Devtools:** React Query DevTools for debugging

**2. TypeScript Support:**

TanStack Query is **TypeScript-first**:
```typescript
// Type-safe queries
const { data, isLoading, error } = useQuery<Agent[]>({
  queryKey: ['agents'],
  queryFn: () => apiClient.get('/agents')
})

// data is typed as Agent[] (not any)
// Autocomplete works throughout
```

**3. Optimistic Updates for Fast UX:**

Critical for operations like "pause queue", "delete agent", "assign role":
```typescript
// Optimistic update: UI updates instantly, rollback on error
const mutation = useMutation({
  mutationFn: pauseQueue,
  onMutate: async () => {
    // Cancel ongoing queries
    await queryClient.cancelQueries({ queryKey: ['queue'] })

    // Snapshot previous state
    const previousQueue = queryClient.getQueryData(['queue'])

    // Optimistically update UI
    queryClient.setQueryData(['queue'], (old) => ({ ...old, status: 'paused' }))

    return { previousQueue }
  },
  onError: (err, variables, context) => {
    // Rollback on error
    queryClient.setQueryData(['queue'], context.previousQueue)
  },
  onSettled: () => {
    // Refetch to sync with server
    queryClient.invalidateQueries({ queryKey: ['queue'] })
  }
})
```

**4. Polling for Real-Time Dashboards:**

Dashboard metrics need to update every 3-10 seconds:
```typescript
// Automatic polling every 5 seconds
const { data: metrics } = useQuery({
  queryKey: ['metrics', 'summary'],
  queryFn: () => apiClient.get('/metrics/summary'),
  refetchInterval: 5000,  // Poll every 5s
  refetchOnWindowFocus: true  // Refetch when user returns to tab
})
```

**5. Cache Management:**

Smart caching reduces unnecessary API calls:
```typescript
// Query client config
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000,  // 5 minutes
      cacheTime: 10 * 60 * 1000,  // 10 minutes
      retry: 3,  // Retry failed requests 3 times
      refetchOnWindowFocus: true
    }
  }
})

// Result: Agent list cached for 5 min, refetched on tab focus
```

**6. DevTools for Debugging:**

React Query DevTools shows:
- All active queries and their status
- Cache contents
- Query timelines
- Network requests

Critical for debugging "why isn't my data updating?"

**7. Community and Ecosystem:**

- **200k+ weekly npm downloads** (vs SWR's 100k)
- **Active maintenance:** Weekly releases, bug fixes
- **Extensive documentation:** 100+ examples, video tutorials
- **Third-party integrations:** NextAuth, Axios, TRPC, etc.

### Why Not SWR?

**SWR Strengths:**
- Lightweight (5KB vs TanStack Query's 12KB)
- Simple API (`useSWR(key, fetcher)`)
- Built by Vercel (Next.js creators)
- Fast setup

**SWR Limitations:**
- **No built-in pagination:** Must implement manually
- **No optimistic updates:** Requires custom logic
- **Less powerful caching:** Simpler cache invalidation
- **Smaller feature set:** Missing infinite queries, prefetching, etc.
- **Less TypeScript support:** Generic types work, but not as tight

**Verdict:** SWR is great for simple use cases, but TanStack Query better matches our complex requirements (polling, optimistic updates, pagination).

### Why Not RTK Query?

**RTK Query Strengths:**
- Part of Redux Toolkit (if using Redux)
- Tight Redux integration
- Code generation from OpenAPI specs

**RTK Query Limitations:**
- **Requires Redux:** We're not using Redux (using Zustand for client state)
- **Heavier bundle:** Redux + RTK + RTK Query = ~40KB
- **More boilerplate:** Slice definitions, store setup
- **Overkill:** Don't need Redux for just server state

**Verdict:** RTK Query is excellent if you're already using Redux. We're not, so TanStack Query is simpler.

---

## Alternatives Considered

### Alternative 1: SWR
- **Pros:** Lightweight, simple API, Vercel-backed
- **Cons:** Fewer features, no pagination, no optimistic updates, less TypeScript support
- **Rejected because:** Missing critical features (pagination, optimistic updates) we need

### Alternative 2: RTK Query
- **Pros:** Redux integration, code generation, caching
- **Cons:** Requires Redux (we're using Zustand), heavier bundle, more boilerplate
- **Rejected because:** Don't need Redux, TanStack Query is simpler

### Alternative 3: Apollo Client
- **Pros:** Best GraphQL client, normalized cache, devtools
- **Cons:** **We're not using GraphQL** (using REST API), heavy bundle (30KB), complex setup
- **Rejected because:** GraphQL-first, not designed for REST APIs

### Alternative 4: Native fetch() + useState
- **Pros:** Zero dependencies, maximum flexibility
- **Cons:** Must implement caching, polling, error handling, loading states manually (100s of lines)
- **Rejected because:** Reinventing the wheel, TanStack Query solves this

---

## Consequences

### Positive

1. **Developer Productivity:**
   - `useQuery` hook handles loading, error, success states automatically
   - No need to write `useState`, `useEffect`, error handling boilerplate
   - Estimated 40% reduction in data fetching code

2. **User Experience:**
   - Optimistic updates make UI feel instant
   - Automatic polling keeps dashboards fresh
   - Background refetching ensures data stays current

3. **Performance:**
   - Smart caching reduces API calls by 60-70%
   - Deduplicated requests (multiple components calling same query → single API call)
   - Prefetching speeds up navigation

4. **Debugging:**
   - React Query DevTools show all queries, cache contents, timelines
   - Easy to identify stale data, failed requests, slow queries

5. **TypeScript Benefits:**
   - Type-safe queries (no `any` types)
   - Autocomplete for data properties
   - Compile-time errors for incorrect data access

### Negative

1. **Bundle Size:**
   - TanStack Query adds ~12KB gzipped to client bundle
   - **Impact:** Acceptable (< 4% of 300KB budget)
   - **Mitigation:** Tree-shaking removes unused features

2. **Learning Curve:**
   - Team needs to learn TanStack Query concepts (queries, mutations, cache invalidation)
   - **Estimated:** 1-2 days to become proficient
   - **Mitigation:** Excellent documentation, video tutorials, team training session

3. **Cache Invalidation Complexity:**
   - Must manually invalidate queries after mutations
   - Easy to forget → stale data bugs
   - **Mitigation:** Establish patterns (always invalidate in `onSuccess`), code review checklist

4. **Debugging Cache Issues:**
   - Cache behavior can be non-obvious (why is this query refetching?)
   - **Mitigation:** React Query DevTools make cache behavior visible

---

## Implementation Notes

### Setup

**Install:**
```bash
npm install @tanstack/react-query @tanstack/react-query-devtools
```

**Provider:**
```typescript
// /app/providers.tsx
'use client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ReactQueryDevtools } from '@tanstack/react-query-devtools'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000,  // 5 minutes
      cacheTime: 10 * 60 * 1000,  // 10 minutes
      retry: 3,
      refetchOnWindowFocus: true,
      refetchOnReconnect: true
    }
  }
})

export function Providers({ children }: { children: React.Node }) {
  return (
    <QueryClientProvider client={queryClient}>
      {children}
      <ReactQueryDevtools initialIsOpen={false} />
    </QueryClientProvider>
  )
}
```

### Query Examples

**Basic Query:**
```typescript
// Fetch agent list
const { data: agents, isLoading, error } = useQuery({
  queryKey: ['agents'],
  queryFn: () => apiClient.get<Agent[]>('/agents')
})

if (isLoading) return <Skeleton />
if (error) return <ErrorState error={error} />
return <AgentTable agents={agents} />
```

**Polling Query:**
```typescript
// Dashboard metrics (poll every 5s)
const { data: metrics } = useQuery({
  queryKey: ['metrics', 'summary'],
  queryFn: () => apiClient.get('/metrics/summary'),
  refetchInterval: 5000
})
```

**Mutation with Optimistic Update:**
```typescript
// Delete agent with optimistic update
const deleteMutation = useMutation({
  mutationFn: (agentId: string) => apiClient.delete(`/agents/${agentId}`),
  onMutate: async (agentId) => {
    await queryClient.cancelQueries({ queryKey: ['agents'] })
    const previous = queryClient.getQueryData(['agents'])
    queryClient.setQueryData(['agents'], (old: Agent[]) =>
      old.filter(a => a.id !== agentId)
    )
    return { previous }
  },
  onError: (err, agentId, context) => {
    queryClient.setQueryData(['agents'], context.previous)
  },
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['agents'] })
  }
})
```

**Infinite Query (Pagination):**
```typescript
// Execution history with infinite scroll
const {
  data,
  fetchNextPage,
  hasNextPage,
  isFetchingNextPage
} = useInfiniteQuery({
  queryKey: ['executions'],
  queryFn: ({ pageParam = 0 }) =>
    apiClient.get(`/executions?page=${pageParam}`),
  getNextPageParam: (lastPage, pages) =>
    lastPage.hasMore ? pages.length : undefined
})
```

### Best Practices

1. **Query Keys:**
   - Use arrays for hierarchical keys: `['agents', agentId, 'tools']`
   - Include all variables: `['executions', { status, dateRange }]`

2. **Cache Invalidation:**
   - Always invalidate related queries after mutations
   - Use `invalidateQueries` (refetch) or `setQueryData` (update cache directly)

3. **Error Handling:**
   - Use `onError` in mutations for user feedback (toast notification)
   - Use `useQuery` error state for display

4. **Stale Time:**
   - Dashboard metrics: 5s stale time (real-time)
   - Agent config: 5min stale time (rarely changes)
   - User profile: 10min stale time (almost never changes)

---

## References

- [TanStack Query Documentation](https://tanstack.com/query/latest)
- [React Query vs SWR Comparison](https://tkdodo.eu/blog/react-query-vs-swr)
- [TanStack Query Best Practices](https://tkdodo.eu/blog/practical-react-query)

---

## Related Decisions

- **ADR 001:** Next.js framework (provides React context for TanStack Query)
- **Story 2:** Next.js setup (install and configure TanStack Query)
- **Story 3-5:** Page implementation (use TanStack Query for data fetching)

---

**Decision Made By:** Ravi (Product Owner)
**Reviewed By:** Architecture Team
**Supersedes:** None
**Superseded By:** None
