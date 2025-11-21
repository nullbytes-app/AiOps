# Runbook: Performance Issues

**Objective:** Diagnose and resolve slow page load times in the Next.js UI

**Severity:** Medium (degrades user experience but doesn't block access)

**Estimated Time:** 10-20 minutes

---

## Prerequisites

Before starting, ensure you have:
- [ ] Browser DevTools (Chrome/Firefox/Safari)
- [ ] Access to application logs
- [ ] Access to Prometheus metrics (if configured)
- [ ] Network speed test results (`fast.com` or `speedtest.net`)
- [ ] User's browser version and OS

---

## Performance Targets

| Metric | Target | Acceptable | Unacceptable |
|--------|--------|------------|--------------|
| **Initial Page Load** | < 2s | 2-4s | > 4s |
| **API Response (p95)** | < 500ms | 500ms-1s | > 1s |
| **Dashboard Refresh** | < 300ms | 300ms-500ms | > 500ms |
| **Navigation Between Pages** | < 200ms | 200ms-500ms | > 500ms |
| **Lighthouse Performance Score** | 90+ | 70-89 | < 70 |

---

## Decision Tree

```
Page loads slowly
├── Network Issues
│   ├── Slow internet connection (< 5 Mbps)
│   ├── High latency to API server (> 200ms ping)
│   └── Solution: Check network, use CDN, enable compression
│
├── FastAPI Backend Slow
│   ├── Database query slow (> 1s)
│   ├── Missing database indexes
│   ├── No caching (Redis)
│   └── Solution: Add indexes, enable caching, optimize queries
│
├── Browser Extensions
│   ├── Ad blockers interfering with React
│   ├── Excessive extensions (> 10 active)
│   └── Solution: Disable extensions, test in incognito
│
├── Large Bundle Size
│   ├── JavaScript bundle > 500KB
│   ├── Unoptimized images
│   └── Solution: Code splitting, image optimization
│
└── Client-Side Issues
    ├── Memory leak (tabs open for days)
    ├── Too many browser tabs (> 20)
    └── Solution: Restart browser, close unused tabs
```

---

## Step-by-Step Troubleshooting

### Issue 1: Slow Network Connection

**Symptoms:**
- All pages load slowly (not just dashboard)
- Browser shows "Waiting for connection..." for > 2s
- Network speed test shows < 5 Mbps

**Diagnosis:**
1. **Test Network Speed:**
   - Go to https://fast.com
   - Expected: > 10 Mbps download, > 5 Mbps upload

2. **Test API Latency:**
   ```bash
   # From user's machine
   curl -w "@curl-format.txt" -o /dev/null -s http://your-domain.com/health

   # curl-format.txt:
   time_namelookup: %{time_namelookup}\n
   time_connect: %{time_connect}\n
   time_starttransfer: %{time_starttransfer}\n
   time_total: %{time_total}\n
   ```

   Expected:
   - `time_namelookup` < 50ms
   - `time_connect` < 100ms
   - `time_total` < 300ms

**Solution:**

**A. User on Slow Network (< 5 Mbps):**
- **Short-term:** Use mobile hotspot, switch to wired connection
- **Long-term:** Request IT to upgrade internet plan

**B. High Latency to Server:**
```bash
# Check if using CDN
curl -I https://your-domain.com
# Look for: X-Cache: HIT from cloudflare
```

- **If no CDN:** Enable Cloudflare or AWS CloudFront
- **If CDN enabled:** Check CDN cache hit rate (should be > 80%)

**C. Enable Compression:**
```nginx
# nginx.conf (if using nginx proxy)
gzip on;
gzip_types text/plain text/css application/json application/javascript;
gzip_min_length 1000;
```

**Verification:**
```bash
curl -H "Accept-Encoding: gzip" -I https://your-domain.com
# Look for: Content-Encoding: gzip
```

---

### Issue 2: FastAPI Backend API Slow

**Symptoms:**
- Browser DevTools shows API calls taking > 1s
- Specific pages slow (e.g., Execution History)
- Network tab shows: `GET /api/v1/executions` → 1500ms

**Diagnosis:**
1. **Check API Response Times:**
   ```bash
   # Test dashboard metrics endpoint
   time curl http://localhost:8000/api/v1/metrics/summary

   # Test execution history endpoint
   time curl "http://localhost:8000/api/v1/executions?limit=50"
   ```

2. **Check Database Query Performance:**
   ```bash
   docker exec -it ai-agents-postgres psql -U aiagents -d ai_agents -c \
     "SELECT query, mean_exec_time, calls FROM pg_stat_statements ORDER BY mean_exec_time DESC LIMIT 10;"
   ```

**Solution:**

**A. Missing Database Indexes:**
```sql
-- Check if indexes exist
SELECT tablename, indexname FROM pg_indexes WHERE schemaname = 'public';

-- Add missing indexes (if not present)
CREATE INDEX IF NOT EXISTS idx_enhancement_history_tenant ON enhancement_history(tenant_id);
CREATE INDEX IF NOT EXISTS idx_enhancement_history_created_at ON enhancement_history(created_at);
CREATE INDEX IF NOT EXISTS idx_executions_tenant_created ON agent_executions(tenant_id, created_at);
```

**B. Enable Redis Caching:**
```python
# src/services/metrics_service.py
from src.cache.redis_client import redis_client

async def get_dashboard_metrics(tenant_id: str):
    # Check cache first
    cache_key = f"metrics:dashboard:{tenant_id}"
    cached = await redis_client.get(cache_key)
    if cached:
        return json.loads(cached)

    # Fetch from DB
    metrics = await fetch_from_db(tenant_id)

    # Cache for 30 seconds
    await redis_client.setex(cache_key, 30, json.dumps(metrics))
    return metrics
```

**C. Optimize Queries:**
```sql
-- Before (slow): Full table scan
SELECT * FROM enhancement_history WHERE tenant_id = 'tenant-abc';

-- After (fast): Use index + limit
SELECT * FROM enhancement_history
WHERE tenant_id = 'tenant-abc'
ORDER BY created_at DESC
LIMIT 100;
```

**Verification:**
```bash
# API should respond in < 500ms
time curl "http://localhost:8000/api/v1/metrics/summary?tenant_id=tenant-abc"

# Check Redis cache hits
docker exec -it ai-agents-redis redis-cli INFO stats | grep keyspace_hits
```

---

### Issue 3: Browser Extensions Interfering

**Symptoms:**
- Page loads fast in incognito mode
- Page loads slow in regular browser with extensions
- Console shows errors from extension scripts

**Diagnosis:**
1. **Test in Incognito Mode:**
   - Open browser incognito/private window
   - Navigate to https://your-domain.com
   - If fast → Extensions are the issue

2. **Check Extension Count:**
   - Chrome: chrome://extensions
   - Firefox: about:addons
   - Count active extensions (if > 10 → likely issue)

**Solution:**
1. **Disable Extensions One-by-One:**
   - Start with ad blockers (uBlock Origin, AdBlock)
   - Disable privacy extensions (Privacy Badger, Ghostery)
   - Disable React DevTools (ironically can slow React apps)

2. **Whitelist Your Domain:**
   ```
   uBlock Origin → Settings → Whitelist
   Add: your-domain.com
   ```

3. **Use Browser Profiles:**
   ```
   Chrome: Create new profile → chrome://settings/manageProfile
   Firefox: Create new profile → about:profiles
   ```
   Use "Work" profile with minimal extensions for AI Agents platform.

**Verification:**
- Page load time < 2s in profile with no extensions
- No console errors from extension scripts

---

### Issue 4: Large JavaScript Bundle Size

**Symptoms:**
- Initial page load takes > 4s
- Network tab shows large JS files (> 1MB)
- Happens on first visit (no cache)

**Diagnosis:**
1. **Check Bundle Size:**
   ```bash
   cd nextjs-ui
   npm run build
   npm run analyze  # Opens webpack-bundle-analyzer
   ```

2. **Check Network Tab:**
   - Open DevTools → Network tab → JS filter
   - Look for large files: `_app.js` > 500KB, `chunk-xxx.js` > 200KB

**Solution:**

**A. Enable Code Splitting (Dynamic Imports):**
```typescript
// Before: Synchronous import (loads on every page)
import HeavyChart from '@/components/HeavyChart';

// After: Dynamic import (loads only when needed)
const HeavyChart = dynamic(() => import('@/components/HeavyChart'), {
  loading: () => <Skeleton />
});
```

**B. Optimize Images:**
```typescript
// Use Next.js Image component (auto-optimizes, lazy loads)
import Image from 'next/image';

<Image
  src="/logo.png"
  alt="Logo"
  width={200}
  height={50}
  loading="lazy"  // Lazy load images
  quality={75}    // Reduce quality (default 75)
/>
```

**C. Remove Unused Dependencies:**
```bash
# Analyze what's in bundle
npx depcheck

# Remove unused packages
npm uninstall unused-package-name
```

**Verification:**
```bash
npm run build
# Check output:
# First Load JS: < 300KB gzipped ✅
# If > 500KB: continue optimization
```

---

### Issue 5: Client-Side Memory Leak

**Symptoms:**
- Page fast initially, slows down over time
- Browser tab uses > 1GB RAM
- User has kept tab open for days with auto-refresh

**Diagnosis:**
1. **Check Memory Usage:**
   - Chrome: DevTools → Performance → Memory
   - Record for 30 seconds
   - Look for saw-tooth pattern (leak) vs flat line (healthy)

2. **Check React Query Cache:**
   ```javascript
   // In browser console
   window.__REACT_QUERY_DEVTOOLS__.client.getQueryCache().getAll().length
   // If > 1000 queries → cache not being garbage collected
   ```

**Solution:**

**A. Fix React Query Cache:**
```typescript
// src/lib/react-query.tsx
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000,  // 5 minutes
      cacheTime: 10 * 60 * 1000, // 10 minutes (was: Infinity)
      gcTime: 10 * 60 * 1000,    // Garbage collect after 10 min
    },
  },
});
```

**B. Stop Polling When Tab Inactive:**
```typescript
// src/hooks/useDashboardMetrics.ts
const { data } = useQuery({
  queryKey: ['dashboard-metrics', tenantId],
  queryFn: fetchMetrics,
  refetchInterval: 5000,  // 5s polling
  refetchIntervalInBackground: false,  // Stop polling when tab hidden
});
```

**C. User Workaround:**
- Refresh page once per day (Cmd+R / Ctrl+R)
- Close and reopen tab weekly
- Use "Discard tabs" Chrome extension to free memory

**Verification:**
- Browser memory usage < 500MB after 1 hour
- No console warnings about memory

---

### Issue 6: Too Many React Re-Renders

**Symptoms:**
- Page sluggish when typing in forms
- Animations stutter (< 30 FPS)
- Browser DevTools Profiler shows excessive renders

**Diagnosis:**
1. **Profile React Renders:**
   - Install React DevTools extension
   - Open Profiler tab
   - Record interaction (e.g., typing in form)
   - Look for > 10 renders/second

2. **Check Console for Warnings:**
   ```
   Warning: Cannot update a component while rendering a different component
   ```

**Solution:**

**A. Memoize Expensive Computations:**
```typescript
// Before: Recalculated on every render
const filteredAgents = agents.filter(a => a.status === 'active');

// After: Memoized (only recalculates when agents change)
const filteredAgents = useMemo(
  () => agents.filter(a => a.status === 'active'),
  [agents]
);
```

**B. Debounce Search Input:**
```typescript
// Before: API call on every keystroke
const handleSearch = (query: string) => {
  fetchAgents(query);
};

// After: API call only after 500ms of no typing
const debouncedFetchAgents = useMemo(
  () => debounce(fetchAgents, 500),
  []
);
```

**C. Use React.memo for Lists:**
```typescript
// Memoize row component to prevent re-render of entire table
const AgentRow = React.memo(({ agent }: { agent: Agent }) => {
  return <tr>...</tr>;
});
```

**Verification:**
- React Profiler shows < 5 renders/second during typing
- Animations smooth at 60 FPS

---

## Common Performance Issues Summary

| Symptom | Likely Cause | Quick Fix |
|---------|--------------|-----------|
| All pages slow (> 4s) | Slow network | Test network speed, use CDN |
| Specific page slow (e.g., Execution History) | Backend API slow | Add DB indexes, enable caching |
| Fast in incognito, slow in normal browser | Browser extensions | Disable extensions, test in clean profile |
| First load slow (> 4s), subsequent fast | Large bundle size | Code splitting, image optimization |
| Fast initially, slows over time | Memory leak | Fix React Query cache, stop polling when hidden |
| Typing in forms sluggish | Too many re-renders | Debounce input, memoize computations |

---

## Diagnostic Commands

```bash
# Check bundle size
cd nextjs-ui && npm run build && npm run analyze

# Check API response time
time curl http://localhost:8000/api/v1/metrics/summary

# Check database slow queries
docker exec -it ai-agents-postgres psql -U aiagents -d ai_agents -c \
  "SELECT query, mean_exec_time, calls FROM pg_stat_statements ORDER BY mean_exec_time DESC LIMIT 5;"

# Check Redis cache stats
docker exec -it ai-agents-redis redis-cli INFO stats | grep keyspace

# Check memory usage
docker stats --no-stream

# Run Lighthouse audit
npx lighthouse https://your-domain.com --view
```

---

## Escalation

If issue persists after following this runbook:

1. **Collect Performance Diagnostics:**
   - Lighthouse report (HTML file)
   - Chrome DevTools Performance recording (export as JSON)
   - Network HAR file (DevTools → Network → Export HAR)
   - Browser console output (errors + warnings)
   - User's network speed test result

2. **Contact:**
   - **Frontend Team:** Slack #frontend-performance
   - **Backend Team:** Slack #backend-performance
   - **On-Call Engineer:** PagerDuty escalation

3. **Temporary Workaround:**
   - Advise user to use Chrome (fastest React rendering)
   - Suggest closing unused tabs, disabling extensions
   - Provide direct API endpoints as fallback

---

**Last Updated:** January 2025
**Version:** 1.0
**Owner:** Operations Team
