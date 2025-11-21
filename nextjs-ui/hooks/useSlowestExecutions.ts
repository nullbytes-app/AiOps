/**
 * React Query Hook for Slowest Executions
 * Story 16: Agent Performance Dashboard - Slowest Executions
 * AC #7: Auto-refresh every 90 seconds, staleTime 90s, retry 3
 */

'use client';

import { useQuery } from '@tanstack/react-query';
import { getSlowestExecutions } from '@/lib/api/slowest-executions';
import type { SlowestExecutionsResponse } from '@/types/agent-performance';

interface UseSlowestExecutionsProps {
  agentId: string | null;
  startDate: Date;
  endDate: Date;
  page: number;
  statusFilter: 'all' | 'success' | 'failed';
  enabled?: boolean;
  refetchInterval?: number | false; // Allow disabling auto-refresh (AC #5)
}

export function useSlowestExecutions({
  agentId,
  startDate,
  endDate,
  page,
  statusFilter,
  enabled = true,
  refetchInterval = 90000, // Default: 90 seconds (AC #5)
}: UseSlowestExecutionsProps) {
  const limit = 10; // Fixed page size (AC #2)
  const offset = page * limit;

  return useQuery<SlowestExecutionsResponse>({
    queryKey: [
      'slowest-executions',
      agentId,
      startDate.toISOString(),
      endDate.toISOString(),
      page,
      statusFilter,
    ],
    queryFn: () => {
      if (!agentId) {
        throw new Error('Agent ID is required');
      }
      return getSlowestExecutions(agentId, startDate, endDate, limit, offset, statusFilter);
    },
    enabled: enabled && !!agentId,
    staleTime: 90000, // 90 seconds (AC #7)
    refetchInterval, // Auto-refresh interval (90s default, false when rows expanded - AC #5)
    retry: process.env.NODE_ENV === 'test' ? false : 3,
    refetchOnMount: true,
    refetchOnWindowFocus: false,
  });
}
