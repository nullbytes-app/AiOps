/**
 * Error Analysis API Client
 * Story 15: Agent Performance Dashboard - Error Analysis
 */

import { apiClient } from './client';
import type { ErrorAnalysisResponse } from '@/types/agent-performance';

export async function getAgentErrorAnalysis(
  agentId: string,
  startDate: Date,
  endDate: Date
): Promise<ErrorAnalysisResponse> {
  const params = new URLSearchParams({
    start_date: startDate.toISOString(),
    end_date: endDate.toISOString(),
  });

  const response = await apiClient.get<ErrorAnalysisResponse>(
    `/agents/${agentId}/error-analysis?${params}`
  );

  return response.data;
}
