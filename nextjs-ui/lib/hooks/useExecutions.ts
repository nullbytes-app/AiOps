/**
 * Execution History React Query Hooks
 *
 * Custom hooks for execution operations with filtering, pagination,
 * and CSV export using TanStack Query v5
 */

import { useQuery, useMutation } from '@tanstack/react-query';
import { toast } from 'sonner';
import Papa from 'papaparse';
import {
  getExecutions,
  getExecutionDetail,
  getAgentOptions,
  type ExecutionFilters,
  type AgentExecution,
  type ExecutionDetail,
  type AgentOption,
} from '../api/executions';

// Re-export types for use in components
export type { AgentExecution, ExecutionDetail, ExecutionFilters, AgentOption };
export type { ExecutionStatus } from '../api/executions';

/**
 * Query keys for cache management
 */
export const executionKeys = {
  all: ['executions'] as const,
  lists: () => [...executionKeys.all, 'list'] as const,
  list: (filters: ExecutionFilters) => [...executionKeys.lists(), filters] as const,
  details: () => [...executionKeys.all, 'detail'] as const,
  detail: (id: string) => [...executionKeys.details(), id] as const,
  agents: () => [...executionKeys.all, 'agents'] as const,
};

/**
 * Fetch executions with filters and pagination
 */
export const useExecutions = (filters: ExecutionFilters) => {
  return useQuery({
    queryKey: executionKeys.list(filters),
    queryFn: () => getExecutions(filters),
    staleTime: 30000, // 30 seconds
    refetchOnWindowFocus: true,
  });
};

/**
 * Fetch execution detail by ID
 */
export const useExecutionDetail = (id: string | null) => {
  return useQuery({
    queryKey: executionKeys.detail(id || ''),
    queryFn: () => getExecutionDetail(id!),
    enabled: !!id, // Only fetch if ID provided
    staleTime: 60000, // 1 minute
  });
};

/**
 * Fetch agent options for filter dropdown
 */
export const useAgentOptions = () => {
  return useQuery({
    queryKey: executionKeys.agents(),
    queryFn: getAgentOptions,
    staleTime: 300000, // 5 minutes (agents don't change often)
    gcTime: 600000, // 10 minutes (formerly cacheTime in v4)
  });
};

/**
 * Export executions to CSV and trigger browser download
 */
export const useExportExecutions = () => {
  return useMutation({
    mutationFn: async (filters: ExecutionFilters) => {
      // Fetch filtered data (up to 10,000 rows)
      const response = await getExecutions({ ...filters, limit: 10000 });
      return response.executions;
    },
    onSuccess: (executions: AgentExecution[]) => {
      try {
        // Convert to CSV using papaparse
        const csv = Papa.unparse(
          executions.map((exec) => ({
            'Execution ID': exec.id,
            'Agent Name': exec.agent_name,
            Status: exec.status,
            'Duration (ms)': exec.duration_ms || 'N/A',
            'Started At': exec.started_at,
            'Completed At': exec.completed_at || 'N/A',
            'Error Message': exec.error_message || '',
            'Tenant ID': exec.tenant_id,
          })),
          {
            quotes: true,
            delimiter: ',',
            header: true,
            newline: '\r\n',
          }
        );

        // Trigger browser download
        const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `execution-history-${new Date().toISOString().split('T')[0]}.csv`;
        link.click();
        URL.revokeObjectURL(url);

        toast.success(`Exported ${executions.length} executions to CSV`);
      } catch (error) {
        toast.error('Failed to generate CSV', {
          description: error instanceof Error ? error.message : 'An error occurred',
        });
      }
    },
    onError: (error) => {
      toast.error('Failed to export executions', {
        description: error instanceof Error ? error.message : 'An error occurred',
      });
    },
  });
};
