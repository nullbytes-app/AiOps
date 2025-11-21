/**
 * useLLMCostSummary Hook
 *
 * TanStack Query hook for fetching LLM cost summary metrics with auto-refresh.
 * Follows 2025 React Query v5 best practices for real-time dashboards.
 *
 * Maps to Backend API: GET /api/v1/costs/summary (src/api/llm_costs.py:40-64)
 * Uses CostSummaryDTO schema (src/schemas/llm_cost.py:187-201)
 */

import { useQuery, UseQueryResult } from '@tanstack/react-query';
import axios from 'axios';
import { CostSummaryDTO } from '@/types/costs';

/**
 * Fetch cost summary from API
 * @returns Promise resolving to CostSummaryDTO
 * @throws Error if API request fails or returns non-200 status
 */
async function fetchCostSummary(): Promise<CostSummaryDTO> {
  // Use API endpoint with versioned URL per ADR-004
  const response = await axios.get<CostSummaryDTO>('/api/v1/costs/summary', {
    headers: {
      'Content-Type': 'application/json',
    },
    timeout: 5000, // 5 second timeout for dashboard metrics
  });

  return response.data;
}

/**
 * Fetch LLM cost summary metrics with auto-refresh
 *
 * Automatically refreshes every 60 seconds to show near real-time cost data.
 * Uses React Query v5 patterns (queryKey, queryFn, refetchInterval).
 *
 * Features:
 * - Auto-refresh: 60s interval (AC#1 requirement)
 * - Retry logic: 3 attempts with exponential backoff
 * - Stale time: 55s (data considered fresh)
 * - Background refetch: Disabled (pauses when tab inactive)
 * - Error handling: Automatic retry with exponential backoff
 *
 * @returns Query result with cost summary data, loading, error states
 *
 * @example
 * ```tsx
 * function LLMCostsDashboard() {
 *   const { data, isLoading, isError, error, refetch } = useLLMCostSummary();
 *
 *   if (isLoading) return <SkeletonUI />;
 *   if (isError) return <ErrorState error={error} onRetry={refetch} />;
 *
 *   return (
 *     <div>
 *       <MetricCard label="Today's Spend" value={data.today_spend} />
 *       <MetricCard label="This Week" value={data.week_spend} />
 *       <MetricCard label="This Month" value={data.month_spend} />
 *     </div>
 *   );
 * }
 * ```
 */
export function useLLMCostSummary(): UseQueryResult<CostSummaryDTO, Error> {
  return useQuery({
    queryKey: ['costs', 'summary'], // Unique query key for caching
    queryFn: fetchCostSummary,
    staleTime: 55000, // Consider data fresh for 55 seconds (slightly less than refetch interval)
    refetchInterval: 60000, // Auto-refresh every 60 seconds (AC#1 requirement)
    refetchIntervalInBackground: false, // Pause auto-refresh when tab inactive (performance optimization)
    retry: 3, // Retry failed requests up to 3 times
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000), // Exponential backoff: 1s, 2s, 4s, max 30s
  });
}
