/**
 * useHealthStatus Hook
 *
 * TanStack Query hook for fetching system health status with auto-refresh.
 * Follows 2025 best practices with proper staleTime and refetchInterval configuration.
 */

import { useQuery, UseQueryResult } from '@tanstack/react-query';
import { healthApi, SystemHealthStatus } from '../api/health';

/**
 * Fetch system health status with auto-refresh
 *
 * Auto-refreshes every 5 seconds to keep health status current.
 * Pauses refresh when tab is inactive to save resources.
 *
 * @returns Query result with health status data
 *
 * @example
 * ```tsx
 * function HealthDashboard() {
 *   const { data, isLoading, isError, refetch } = useHealthStatus();
 *
 *   if (isLoading) return <LoadingSkeleton />;
 *   if (isError) return <ErrorState onRetry={refetch} />;
 *
 *   return (
 *     <div>
 *       <HealthCard component="api" health={data.api} />
 *       <HealthCard component="workers" health={data.workers} />
 *     </div>
 *   );
 * }
 * ```
 */
export function useHealthStatus(): UseQueryResult<SystemHealthStatus, Error> {
  return useQuery({
    queryKey: ['health', 'status'],
    queryFn: () => healthApi.getStatus(),
    staleTime: 4000, // Consider data fresh for 4 seconds
    refetchInterval: 5000, // Auto-refresh every 5 seconds
    refetchIntervalInBackground: false, // Pause when tab inactive
    retry: 3, // Retry failed requests up to 3 times
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000), // Exponential backoff
  });
}
