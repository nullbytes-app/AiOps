import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api/client';
import type {
  AgentTrendsDTO,
  TrendGranularity,
} from '@/types/agent-performance';

interface UseAgentTrendsOptions {
  agentId: string | null;
  startDate: string;
  endDate: string;
  granularity: TrendGranularity;
  enabled?: boolean;
}

/**
 * Fetch agent execution trend data with hourly or daily granularity.
 *
 * @param options - Query options
 * @returns React Query result with AgentTrendsDTO data
 */
export function useAgentTrends(options: UseAgentTrendsOptions) {
  const { agentId, startDate, endDate, granularity, enabled = true } = options;

  return useQuery({
    queryKey: ['agent-trends', agentId, startDate, endDate, granularity],
    queryFn: async (): Promise<AgentTrendsDTO> => {
      if (!agentId) throw new Error('Agent ID required');

      const params = new URLSearchParams({
        start_date: startDate,
        end_date: endDate,
        granularity,
      });

      const response = await apiClient.get<AgentTrendsDTO>(
        `/api/agents/${agentId}/trends?${params}`,
        { timeout: 5000 }
      );
      return response.data;
    },
    enabled: enabled && !!agentId,
    staleTime: 60000, // 1 minute (trends don't change rapidly)
    retry: 3,
  });
}
