/**
 * useLLMCostTrend Hook
 *
 * TanStack Query hook for fetching daily LLM cost trend data with auto-refresh.
 * Follows 2025 React Query v5 best practices validated via Context7 MCP research.
 *
 * Maps to Backend API: GET /api/v1/costs/trend (src/api/llm_costs.py:183-202)
 * Uses DailySpendDTO schema (src/schemas/llm_cost.py:75-89)
 *
 * Research Notes:
 * - Context7 MCP: /websites/tanstack_query_v5 (1158 snippets, Trust 8.9)
 * - Validated patterns: refetchInterval, retry with exponential backoff, staleTime
 * - 2025 best practice: refetchIntervalInBackground: false (pause when tab inactive)
 */

import { useQuery, UseQueryResult } from '@tanstack/react-query';
import axios from 'axios';
import { DailySpendDTO } from '@/types/costs';

/**
 * Fetch daily cost trend data from API
 * @param days - Number of days of historical data (1-365)
 * @returns Promise resolving to DailySpendDTO[]
 * @throws Error if API request fails or returns non-200 status
 */
async function fetchDailyTrend(days: number): Promise<DailySpendDTO[]> {
  // Use API endpoint with versioned URL per ADR-004
  const response = await axios.get<DailySpendDTO[]>(
    `/api/v1/costs/trend?days=${days}`,
    {
      headers: {
        'Content-Type': 'application/json',
      },
      timeout: 5000, // 5 second timeout for dashboard metrics
    }
  );

  return response.data;
}

/**
 * Fetch daily LLM cost trend data with auto-refresh
 *
 * Automatically refreshes every 60 seconds to show near real-time cost data.
 * Uses React Query v5 patterns validated via Context7 MCP research.
 *
 * Features:
 * - Auto-refresh: 60s interval (AC#11 performance requirement)
 * - Retry logic: 3 attempts with exponential backoff (1s, 2s, 4s, max 30s)
 * - Stale time: 55s (data considered fresh)
 * - Background refetch: Disabled (pauses when tab inactive - performance optimization)
 * - Error handling: Automatic retry with exponential backoff
 *
 * @param days - Number of days to fetch (default: 30, max: 365)
 * @returns Query result with daily trend data, loading, error states
 *
 * @example
 * ```tsx
 * function LLMCostsDashboard() {
 *   const { data, isLoading, isError, error, refetch } = useLLMCostTrend(30);
 *
 *   if (isLoading) return <ChartSkeleton />;
 *   if (isError) return <ErrorState error={error} onRetry={refetch} />;
 *
 *   return <DailySpendChart data={data} />;
 * }
 * ```
 */
export function useLLMCostTrend(
  days: number = 30
): UseQueryResult<DailySpendDTO[], Error> {
  return useQuery({
    queryKey: ['costs', 'trend', days], // Unique query key for caching (AC#2)
    queryFn: () => fetchDailyTrend(days),
    staleTime: 55000, // Consider data fresh for 55 seconds (slightly less than refetch interval)
    refetchInterval: 60000, // Auto-refresh every 60 seconds (AC#11 requirement)
    refetchIntervalInBackground: false, // Pause auto-refresh when tab inactive (performance optimization)
    retry: 3, // Retry failed requests up to 3 times (AC#10 error handling)
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000), // Exponential backoff: 1s, 2s, 4s, max 30s
  });
}
