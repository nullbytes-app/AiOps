/**
 * React Query hook for fetching agent performance metrics
 * Following 2025 TanStack Query v5 best practices with auto-refresh
 */

import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api/client';
import type { AgentMetricsDTO } from '@/types/agent-performance';

interface UseAgentMetricsOptions {
  agentId: string | null;
  startDate: string;
  endDate: string;
  enabled?: boolean;
}

/**
 * Fetch agent performance metrics with auto-refresh
 * @param options - Query options (agentId, date range, enabled flag)
 * @returns React Query result with metrics data
 *
 * Query configuration:
 * - refetchInterval: 60 seconds (auto-refresh for real-time data)
 * - staleTime: 30 seconds (consider fresh for 30s)
 * - retry: 3 attempts with exponential backoff
 * - timeout: 5 seconds (prevent hanging requests)
 * - enabled: Only fetch if agent selected and enabled=true
 */
export function useAgentMetrics(options: UseAgentMetricsOptions) {
  const { agentId, startDate, endDate, enabled = true } = options;

  return useQuery({
    queryKey: ['agent-metrics', agentId, startDate, endDate],
    queryFn: async () => {
      if (!agentId) throw new Error('Agent ID required');

      const params = new URLSearchParams({
        start_date: startDate,
        end_date: endDate,
      });

      const response = await apiClient.get<AgentMetricsDTO>(
        `/api/agents/${agentId}/metrics?${params}`,
        { timeout: 5000 }
      );
      return response.data;
    },
    enabled: enabled && !!agentId,  // Only fetch if agent selected
    refetchInterval: 60000,          // Auto-refresh every 60 seconds
    staleTime: 30000,                // Consider fresh for 30 seconds
    retry: 3,                        // Retry failed requests 3 times
  });
}
