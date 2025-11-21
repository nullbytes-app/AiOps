/**
 * useAgentMetrics Hook
 *
 * TanStack Query hook for fetching agent execution metrics with data transformation.
 * Follows 2025 best practices for real-time dashboards.
 */

import { useQuery, UseQueryResult } from '@tanstack/react-query';
import { metricsApi, AgentMetrics, TimeRange } from '../api/metrics';

/**
 * Transformed metrics data for chart rendering
 */
export interface TransformedAgentMetrics {
  kpis: {
    totalExecutions: number;
    successRate: number;
    avgCost: number;
    changePercent: number; // +/- change from previous period
  };
  chartData: Array<{
    hour: string;
    success: number;
    failure: number;
  }>;
  tableData: AgentMetrics['agent_breakdown'];
}

/**
 * Transform hourly breakdown to chart-friendly format
 */
function transformToChartData(hourly: AgentMetrics['hourly_breakdown']) {
  return hourly.map((item) => ({
    hour: item.hour,
    success: item.success_count,
    failure: item.failure_count,
  }));
}

/**
 * Fetch agent execution metrics with auto-refresh and data transformation
 *
 * Automatically transforms raw API data into chart-friendly formats.
 * Refreshes every 30 seconds to show near real-time metrics.
 *
 * @param timeRange - Time window for metrics (default: 24h)
 * @returns Query result with transformed metrics data
 *
 * @example
 * ```tsx
 * function AgentMetricsDashboard() {
 *   const { data, isLoading, isError, refetch } = useAgentMetrics('24h');
 *
 *   if (isLoading) return <SkeletonUI />;
 *   if (isError) return <ErrorState onRetry={refetch} />;
 *
 *   return (
 *     <div>
 *       <KPICard
 *         title="Total Executions"
 *         value={data.kpis.totalExecutions}
 *         change={data.kpis.changePercent}
 *       />
 *       <ExecutionChart data={data.chartData} />
 *       <AgentTable data={data.tableData} />
 *     </div>
 *   );
 * }
 * ```
 */
export function useAgentMetrics(
  timeRange: TimeRange = '24h'
): UseQueryResult<TransformedAgentMetrics, Error> {
  return useQuery({
    queryKey: ['metrics', 'agents', { timeRange }],
    queryFn: () => metricsApi.getAgentMetrics(timeRange),
    staleTime: 25000, // Consider data fresh for 25 seconds
    refetchInterval: 30000, // Auto-refresh every 30 seconds
    refetchIntervalInBackground: false, // Pause when tab inactive
    retry: 3,
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
    select: (data): TransformedAgentMetrics => {
      // Transform API response to UI-friendly format
      const totalExecutions = data.total_executions;
      const successRate = totalExecutions > 0
        ? (data.successful_executions / totalExecutions) * 100
        : 0;
      const avgCost = totalExecutions > 0
        ? data.total_cost / totalExecutions
        : 0;

      // Calculate change percentage (placeholder - would need previous period data from API)
      const changePercent = 0; // TODO: Implement when API provides previous period data

      return {
        kpis: {
          totalExecutions,
          successRate,
          avgCost,
          changePercent,
        },
        chartData: transformToChartData(data.hourly_breakdown),
        tableData: data.agent_breakdown,
      };
    },
  });
}
