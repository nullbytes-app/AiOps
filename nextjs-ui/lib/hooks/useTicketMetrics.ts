/**
 * useTicketMetrics Hook
 *
 * TanStack Query hook for fetching ticket processing metrics with frequent refresh.
 * Optimized for real-time queue monitoring.
 */

import { useQuery, UseQueryResult } from '@tanstack/react-query';
import { metricsApi, TicketMetrics } from '../api/metrics';

/**
 * Fetch ticket processing metrics with frequent auto-refresh
 *
 * Queue depth updates frequently (every 10 seconds) to provide
 * near real-time visibility into ticket processing pipeline.
 *
 * @returns Query result with ticket metrics data
 *
 * @example
 * ```tsx
 * function TicketProcessingDashboard() {
 *   const { data, isLoading, isError, refetch } = useTicketMetrics();
 *
 *   if (isLoading) return <LoadingSkeleton />;
 *   if (isError) return <ErrorState onRetry={refetch} />;
 *
 *   return (
 *     <div>
 *       <QueueGauge queueDepth={data.queue_depth} />
 *       <ProcessingRateCard rate={data.processing_rate_per_hour} />
 *       <ErrorRateCard percentage={data.error_rate_percentage} />
 *       <RecentActivity tickets={data.recent_tickets} />
 *     </div>
 *   );
 * }
 * ```
 */
export function useTicketMetrics(): UseQueryResult<TicketMetrics, Error> {
  return useQuery({
    queryKey: ['metrics', 'tickets'],
    queryFn: () => metricsApi.getTicketMetrics(),
    staleTime: 8000, // Consider data fresh for 8 seconds
    refetchInterval: 10000, // Auto-refresh every 10 seconds (queue needs frequent updates)
    refetchIntervalInBackground: false, // Pause when tab inactive
    retry: 3,
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
  });
}
