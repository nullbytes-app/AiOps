/**
 * Slowest Executions API Client
 * Story 16: Agent Performance Dashboard - Slowest Executions
 * AC #7: API integration with React Query caching
 */

import { apiClient } from './client';
import type { SlowestExecutionsResponse } from '@/types/agent-performance';

export async function getSlowestExecutions(
  agentId: string,
  startDate: Date,
  endDate: Date,
  limit: number = 10,
  offset: number = 0,
  statusFilter: 'all' | 'success' | 'failed' = 'all'
): Promise<SlowestExecutionsResponse> {
  const params = new URLSearchParams({
    start_date: startDate.toISOString(),
    end_date: endDate.toISOString(),
    limit: limit.toString(),
    offset: offset.toString(),
  });

  // Only add status filter if not "all"
  if (statusFilter !== 'all') {
    params.append('status', statusFilter);
  }

  const response = await apiClient.get<SlowestExecutionsResponse>(
    `/agents/${agentId}/slowest-executions?${params}`
  );

  return response.data;
}
