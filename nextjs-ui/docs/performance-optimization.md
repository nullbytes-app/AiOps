# Performance Optimization Guide

This document outlines the performance optimizations implemented in the Next.js Dashboard UI and provides recommendations for maintaining optimal performance.

## Implemented Optimizations

### 1. **React Server Components (Next.js 14 App Router)**

All dashboard pages use Server Components by default, with Client Components (`'use client'`) only where necessary:

- ✅ Layout components are Server Components
- ✅ Data-fetching logic isolated in custom hooks
- ✅ Interactive components marked with `'use client'`

**Files:**
- `app/dashboard/health/page.tsx` - Server Component
- `app/dashboard/agents/page.tsx` - Server Component
- `app/dashboard/tickets/page.tsx` - Server Component

### 2. **Optimized Data Fetching (TanStack Query v5)**

All data fetching uses TanStack Query with strategic caching:

```typescript
// Health Status: 5-second auto-refresh
staleTime: 4000,
refetchInterval: 5000,

// Agent Metrics: 30-second auto-refresh
staleTime: 25000,
refetchInterval: 30000,

// Ticket Metrics: 10-second auto-refresh (critical data)
staleTime: 8000,
refetchInterval: 10000,
```

**Benefits:**
- Reduces unnecessary API calls
- Background refetching when tab is active
- Automatic retry with exponential backoff
- Deduplication of simultaneous requests

**Files:**
- `lib/hooks/useHealthStatus.ts`
- `lib/hooks/useAgentMetrics.ts`
- `lib/hooks/useTicketMetrics.ts`

### 3. **Chart Performance (Recharts v3.3.0)**

Recharts is configured for optimal performance:

- ✅ ResponsiveContainer for fluid sizing
- ✅ Animation disabled on large datasets
- ✅ Data transformation in `useMemo`
- ✅ Sparklines limited to <50 data points

**Optimized Components:**
- `components/dashboard/agents/ExecutionChart.tsx`
- `components/charts/QueueGauge.tsx`
- `components/charts/Sparkline.tsx`

### 4. **Table Virtualization Ready**

AgentTable component uses client-side pagination (10 rows per page) to avoid rendering large datasets:

**File:** `components/dashboard/agents/AgentTable.tsx`

**Future Enhancement:** For >1000 agents, consider adding `react-window` or `@tanstack/react-virtual` for true virtualization.

### 5. **Image Optimization**

Next.js Image component used for all images:

```tsx
import Image from 'next/image'

<Image
  src="/logo.png"
  alt="Logo"
  width={200}
  height={50}
  priority  // For above-the-fold images
/>
```

### 6. **Code Splitting**

Dashboard pages are automatically code-split by Next.js:

- Each route loads only its required JavaScript
- Shared components bundled separately
- Dynamic imports for heavy components (if needed)

## Recommended React.memo Usage

Apply `React.memo` to frequently re-rendering components with stable props:

### Priority 1: Chart Components (Expensive Renders)

```tsx
// components/dashboard/agents/ExecutionChart.tsx
import { memo } from 'react'

export const ExecutionChart = memo(function ExecutionChart({ data, className }: ExecutionChartProps) {
  // ... existing code
})

// Comparison function for complex data
export const ExecutionChart = memo(
  function ExecutionChart(props) { /* ... */ },
  (prevProps, nextProps) => {
    // Only re-render if data actually changed
    return prevProps.data === nextProps.data &&
           prevProps.className === nextProps.className
  }
)
```

**Apply to:**
- `ExecutionChart.tsx` ✅ (Recharts LineChart)
- `QueueGauge.tsx` ✅ (Recharts RadialBarChart)
- `Sparkline.tsx` ✅ (Mini chart with frequent updates)

### Priority 2: Table Components

```tsx
// components/dashboard/agents/AgentTable.tsx
import { memo } from 'react'

export const AgentTable = memo(function AgentTable({ data, className }: AgentTableProps) {
  // ... existing code
})
```

**Apply to:**
- `AgentTable.tsx` ✅ (Large dataset rendering)
- `RecentActivity.tsx` ✅ (Ticket table)

### Priority 3: Card Components (Lower Priority)

Only if profiling shows unnecessary re-renders:

```tsx
// components/dashboard/health/HealthCard.tsx
import { memo } from 'react'

export const HealthCard = memo(function HealthCard({ title, health, icon, lastUpdated }: HealthCardProps) {
  // ... existing code
})
```

**Apply to:**
- `HealthCard.tsx` (if health status updates cause parent re-renders)
- `KPICard.tsx` (if KPI values update frequently)

## Lighthouse Audit Recommendations

### Running Lighthouse Audits

```bash
# 1. Build production bundle
npm run build

# 2. Start production server
npm start

# 3. Run Lighthouse (Chrome DevTools or CLI)
npx lighthouse http://localhost:3000/dashboard/health --view

# 4. Or use Chrome DevTools
# Open DevTools > Lighthouse tab > Generate report
```

### Target Scores (Production)

- **Performance:** ≥ 90
- **Accessibility:** ≥ 95
- **Best Practices:** ≥ 95
- **SEO:** ≥ 90

### Common Issues & Fixes

#### 1. **Largest Contentful Paint (LCP)**

**Target:** < 2.5s

**Optimizations:**
- ✅ Server Components for initial render
- ✅ Prioritized loading states
- ⚠️ Consider preloading critical data on server

#### 2. **Cumulative Layout Shift (CLS)**

**Target:** < 0.1

**Optimizations:**
- ✅ Fixed dimensions for charts (ResponsiveContainer)
- ✅ Skeleton loaders with matching dimensions
- ✅ No dynamic height changes after load

#### 3. **First Input Delay (FID)**

**Target:** < 100ms

**Optimizations:**
- ✅ Minimal JavaScript on initial load
- ✅ Client Components only where needed
- ✅ Auto-refresh in background (doesn't block main thread)

#### 4. **Total Blocking Time (TBT)**

**Target:** < 200ms

**Optimizations:**
- ✅ Data transformation in useMemo
- ✅ Debounced search input
- ⚠️ Consider web workers for heavy computations

## Bundle Size Optimization

### Current Dependencies (Production)

```json
{
  "@tanstack/react-query": "^5.62.2",  // 44KB gzipped
  "recharts": "^3.3.0",                 // 120KB gzipped
  "axios": "^1.7.9",                    // 13KB gzipped
  "lucide-react": "^0.462.0"            // Tree-shakeable (5-10KB per icon)
}
```

### Recommendations

1. **Tree-shake Lucide Icons:**
   ```tsx
   // ✅ Good: Import only used icons
   import { HeartPulse, Bot, Ticket } from 'lucide-react'

   // ❌ Avoid: Importing all icons
   import * as Icons from 'lucide-react'
   ```

2. **Dynamic Import Heavy Components:**
   ```tsx
   // For rarely-used components
   const HeavyChart = dynamic(() => import('@/components/charts/HeavyChart'), {
     loading: () => <LoadingSkeleton />,
     ssr: false, // If not needed for SEO
   })
   ```

3. **Analyze Bundle:**
   ```bash
   # Install analyzer
   npm install -D @next/bundle-analyzer

   # Update next.config.js
   const withBundleAnalyzer = require('@next/bundle-analyzer')({
     enabled: process.env.ANALYZE === 'true',
   })

   module.exports = withBundleAnalyzer(nextConfig)

   # Run analysis
   ANALYZE=true npm run build
   ```

## Runtime Performance Monitoring

### React DevTools Profiler

1. Install React DevTools browser extension
2. Navigate to Profiler tab
3. Record interaction (e.g., search, sort, navigate)
4. Analyze render times and unnecessary re-renders

### Chrome Performance Tab

1. Open DevTools > Performance
2. Start recording
3. Interact with dashboard (navigate, search, auto-refresh)
4. Stop recording
5. Analyze:
   - Long tasks (>50ms)
   - Layout shifts
   - JavaScript execution time

## Auto-Refresh Performance

Current implementation pauses auto-refresh when tab is inactive:

```typescript
refetchIntervalInBackground: false,  // ✅ Saves CPU/network when tab hidden
```

**Benefits:**
- Reduces unnecessary API calls
- Saves battery on mobile devices
- Improves performance on machines with many tabs

## Database Query Optimization (Backend)

Dashboard performance also depends on backend API response times:

**Health Endpoint:** `/api/health/status`
- Target: < 100ms response time
- Caching: Redis with 5-second TTL

**Metrics Endpoints:** `/api/metrics/agents`, `/api/metrics/tickets`
- Target: < 500ms response time
- Database indexes on: `agent_name`, `created_at`, `status`
- Aggregations pre-calculated hourly

## Performance Testing Checklist

Before deploying to production:

- [ ] Run Lighthouse audit on all 3 dashboards
- [ ] Test with throttled 3G network (Chrome DevTools)
- [ ] Test with 4x CPU throttling (simulates low-end devices)
- [ ] Verify auto-refresh doesn't degrade performance over time
- [ ] Check bundle size: `npm run build` (should be < 300KB gzipped for main bundle)
- [ ] Test with 1000+ agents in table (pagination working)
- [ ] Verify charts render smoothly with 168 data points (7 days hourly)
- [ ] Test accessibility with screen reader (NVDA/JAWS/VoiceOver)

## Monitoring in Production

Recommended tools for continuous performance monitoring:

1. **Vercel Analytics** (if deployed on Vercel)
   - Real User Monitoring (RUM)
   - Core Web Vitals tracking
   - Performance insights

2. **Google Analytics 4** with Web Vitals
   ```bash
   npm install web-vitals
   ```

3. **Sentry Performance Monitoring**
   - Transaction tracing
   - Slow component detection
   - Error tracking

## Summary

The dashboard is already optimized for performance with:
- ✅ Server Components and strategic client components
- ✅ Optimized data fetching with TanStack Query
- ✅ Efficient chart rendering with Recharts
- ✅ Client-side pagination for tables
- ✅ Background-paused auto-refresh

**Next Steps:**
1. Add React.memo to chart components (ExecutionChart, QueueGauge, Sparkline)
2. Run Lighthouse audits and address any issues
3. Set up production monitoring
4. Consider adding bundle analyzer for regular checks

**Performance Budget:**
- Total bundle size: < 300KB gzipped
- LCP: < 2.5s
- FID: < 100ms
- CLS: < 0.1
- Lighthouse Performance Score: ≥ 90
