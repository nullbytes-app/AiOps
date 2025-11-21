import { useQuery, UseQueryResult } from "@tanstack/react-query";
import axios from "axios";
import type {
  BudgetUtilizationResponse,
  BudgetFilter,
  BudgetSortBy,
} from "@/types/costs";

/**
 * Options for budget utilization query
 */
export interface UseBudgetUtilizationOptions {
  /** Filter criteria (default: 'all') */
  filter?: BudgetFilter;

  /** Sort field (default: 'utilization') */
  sortBy?: BudgetSortBy;

  /** Page number for pagination (default: 1) */
  page?: number;

  /** Items per page (default: 20) */
  pageSize?: number;
}

/**
 * React Query hook for fetching budget utilization data
 *
 * Features:
 * - Auto-refresh every 60 seconds
 * - 30-second stale time
 * - Automatic retry with exponential backoff
 * - Query key includes all filter/sort params for proper caching
 *
 * @param options - Query configuration options
 * @returns React Query result with budget utilization data
 *
 * @example
 * ```tsx
 * function BudgetDashboard() {
 *   const { data, isLoading, error, refetch } = useBudgetUtilization({
 *     filter: 'high_utilization',
 *     sortBy: 'utilization',
 *   });
 *
 *   if (isLoading) return <LoadingSkeleton />;
 *   if (error) return <ErrorState onRetry={refetch} />;
 *
 *   return <BudgetList tenants={data.data} />;
 * }
 * ```
 */
export function useBudgetUtilization(
  options: UseBudgetUtilizationOptions = {}
): UseQueryResult<BudgetUtilizationResponse, Error> {
  const {
    filter = "all",
    sortBy = "utilization",
    page = 1,
    pageSize = 20,
  } = options;

  return useQuery({
    queryKey: ["budget-utilization", filter, sortBy, page, pageSize],
    queryFn: async (): Promise<BudgetUtilizationResponse> => {
      const params = new URLSearchParams({
        filter,
        sort_by: sortBy,
        page: page.toString(),
        page_size: pageSize.toString(),
      });

      const response = await axios.get<BudgetUtilizationResponse>(
        `/api/v1/costs/budget-utilization?${params.toString()}`,
        {
          headers: {
            "Content-Type": "application/json",
          },
          timeout: 5000, // 5 second timeout for dashboard metrics
        }
      );

      return response.data;
    },
    // Auto-refresh every 60 seconds to keep data current
    refetchInterval: 60000,
    // Consider data fresh for 30 seconds (reduces redundant requests)
    staleTime: 30000,
    // Retry failed requests 3 times with exponential backoff
    retry: 3,
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
  });
}
