/**
 * useTokenBreakdown Hook
 *
 * TanStack Query hook for fetching token breakdown data with date range filtering.
 * Calculates percentages client-side for pie chart visualization.
 *
 * Maps to Backend API: GET /api/v1/costs/token-breakdown
 * Uses TokenBreakdownDTO schema (types/costs.ts:68-79)
 */

import { useQuery, UseQueryResult } from '@tanstack/react-query';
import axios from 'axios';
import { TokenBreakdownDTO, TokenBreakdownWithPercentage } from '@/types/costs';

/**
 * Calculate percentage for each token type
 * @param data Array of token breakdown data from API
 * @returns Array with percentage field added (0% if total is zero)
 *
 * @example
 * const input = [
 *   { tokenType: 'input', count: 750, cost: 0.015 },
 *   { tokenType: 'output', count: 250, cost: 0.030 }
 * ];
 * const result = calculatePercentages(input);
 * // result[0].percentage === 75
 * // result[1].percentage === 25
 */
export function calculatePercentages(
  data: TokenBreakdownDTO[]
): TokenBreakdownWithPercentage[] {
  // Calculate total tokens across all types
  const totalTokens = data.reduce((sum, item) => sum + item.count, 0);

  // Handle edge case: zero total tokens (prevent division by zero)
  if (totalTokens === 0) {
    return data.map((item) => ({
      ...item,
      percentage: 0,
    }));
  }

  // Calculate percentage for each token type
  return data.map((item) => ({
    ...item,
    percentage: (item.count / totalTokens) * 100,
  }));
}

/**
 * Fetch token breakdown from API with optional date range
 * @param startDate Optional start date (defaults to 30 days ago on backend)
 * @param endDate Optional end date (defaults to today on backend)
 * @returns Promise resolving to TokenBreakdownDTO array
 * @throws Error if API request fails or returns non-200 status
 */
async function fetchTokenBreakdown(
  startDate?: Date,
  endDate?: Date
): Promise<TokenBreakdownDTO[]> {
  // Build query params for date range
  const params = new URLSearchParams();

  if (startDate) {
    // Format as ISO 8601 date string (YYYY-MM-DD)
    params.append('start_date', startDate.toISOString().split('T')[0]);
  }

  if (endDate) {
    params.append('end_date', endDate.toISOString().split('T')[0]);
  }

  // Use API endpoint with versioned URL per ADR-004
  const url = `/api/v1/costs/token-breakdown${params.toString() ? `?${params.toString()}` : ''}`;

  const response = await axios.get<TokenBreakdownDTO[]>(url, {
    headers: {
      'Content-Type': 'application/json',
    },
    timeout: 5000, // 5 second timeout for dashboard metrics
  });

  return response.data;
}

/**
 * Fetch token breakdown data with client-side percentage calculations
 *
 * Supports date range filtering via optional start/end dates.
 * Calculates percentages client-side for pie chart visualization.
 *
 * Features:
 * - Date range filtering: Optional start/end dates (default: 30 days)
 * - Client-side calculations: Adds percentage field to each token type
 * - Retry logic: 3 attempts with exponential backoff
 * - Stale time: 5 minutes (token data changes slowly)
 * - Error handling: Automatic retry with exponential backoff
 *
 * @param startDate Optional start date for filtering (defaults to 30 days ago on backend)
 * @param endDate Optional end date for filtering (defaults to today on backend)
 * @returns Query result with token breakdown data + percentages, loading, error states
 *
 * @example
 * ```tsx
 * function TokenBreakdownSection() {
 *   const thirtyDaysAgo = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000);
 *   const today = new Date();
 *
 *   const { data, isLoading, isError, error, refetch } = useTokenBreakdown(
 *     thirtyDaysAgo,
 *     today
 *   );
 *
 *   if (isLoading) return <SkeletonUI />;
 *   if (isError) return <ErrorState error={error} onRetry={refetch} />;
 *
 *   return (
 *     <div>
 *       <TokenBreakdownChart data={data} />
 *       <TokenBreakdownTable data={data} />
 *     </div>
 *   );
 * }
 * ```
 */
export function useTokenBreakdown(
  startDate?: Date,
  endDate?: Date
): UseQueryResult<TokenBreakdownWithPercentage[], Error> {
  return useQuery({
    // Include date params in query key for cache invalidation when dates change
    queryKey: ['costs', 'token-breakdown', startDate?.toISOString(), endDate?.toISOString()],
    queryFn: async () => {
      const rawData = await fetchTokenBreakdown(startDate, endDate);
      return calculatePercentages(rawData);
    },
    staleTime: 5 * 60 * 1000, // Consider data fresh for 5 minutes (token data changes slowly)
    retry: 3, // Retry failed requests up to 3 times
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000), // Exponential backoff: 1s, 2s, 4s, max 30s
  });
}
