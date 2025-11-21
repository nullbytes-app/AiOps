/**
 * React Query Hook for Agent Error Analysis
 * Story 15: Agent Performance Dashboard - Error Analysis
 * AC #7: Auto-refresh when agent or date range changes
 */

'use client';

import { useQuery } from '@tanstack/react-query';
import { getAgentErrorAnalysis } from '@/lib/api/error-analysis';
import type { ErrorAnalysisResponse } from '@/types/agent-performance';

interface UseAgentErrorAnalysisProps {
  agentId: string | null;
  startDate: Date;
  endDate: Date;
  enabled?: boolean;
}

export function useAgentErrorAnalysis({
  agentId,
  startDate,
  endDate,
  enabled = true,
}: UseAgentErrorAnalysisProps) {
  return useQuery<ErrorAnalysisResponse>({
    queryKey: ['agent-error-analysis', agentId, startDate.toISOString(), endDate.toISOString()],
    queryFn: () => {
      if (!agentId) {
        throw new Error('Agent ID is required');
      }
      return getAgentErrorAnalysis(agentId, startDate, endDate);
    },
    enabled: enabled && !!agentId,
    staleTime: 60000, // 60 seconds - matches Story 14 pattern
    retry: process.env.NODE_ENV === 'test' ? false : 3, // Disable retry in tests for immediate error state
    refetchOnMount: true,
    refetchOnWindowFocus: false,
  });
}
