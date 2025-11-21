/**
 * React Query hook for fetching agents list
 * Following 2025 TanStack Query v5 best practices
 */

import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api/client';
import type { AgentListResponse } from '@/types/agent-performance';

/**
 * Fetch active agents for selector dropdown
 * @returns React Query result with agents list
 *
 * Query configuration:
 * - staleTime: 5 minutes (agents list changes rarely)
 * - retry: 3 attempts with exponential backoff
 * - refetchOnWindowFocus: false (reduces backend load)
 */
export function useAgents() {
  return useQuery({
    queryKey: ['agents', 'active'],
    queryFn: async () => {
      const response = await apiClient.get<AgentListResponse>('/api/agents?status=active');
      return response.data;
    },
    staleTime: 5 * 60 * 1000,  // 5 minutes (agents list changes rarely)
    refetchOnWindowFocus: false,
    retry: 3,
  });
}
