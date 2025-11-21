/**
 * Execution History API Functions
 *
 * API client functions for agent execution history operations including
 * filtering, pagination, detail view, and CSV export
 */

import { apiClient } from './client';

/**
 * Execution Status
 */
export type ExecutionStatus = 'pending' | 'processing' | 'completed' | 'failed' | 'cancelled';

/**
 * Agent Execution Record
 */
export interface AgentExecution {
  id: string;
  agent_id: string;
  agent_name: string;
  tenant_id: string;
  status: ExecutionStatus;
  duration_ms: number | null; // null if still running
  started_at: string; // ISO 8601
  completed_at: string | null; // ISO 8601
  error_message: string | null;
  // Input/output stored separately for performance
}

/**
 * Execution Detail (includes input/output/metadata)
 */
export interface ExecutionDetail extends AgentExecution {
  input: Record<string, unknown>;
  output: Record<string, unknown> | null;
  metadata: {
    user_id?: string;
    correlation_id?: string;
    retry_count?: number;
    triggered_by?: string;
    [key: string]: unknown;
  };
  logs: ExecutionLogEntry[];
}

/**
 * Execution Log Entry
 */
export interface ExecutionLogEntry {
  timestamp: string;
  level: 'debug' | 'info' | 'warning' | 'error';
  message: string;
  context?: Record<string, unknown>;
}

/**
 * Paginated Execution List Response
 */
export interface ExecutionListResponse {
  executions: AgentExecution[];
  total: number;
  page: number;
  pages: number;
}

/**
 * Execution Filter Parameters
 */
export interface ExecutionFilters {
  page?: number;
  limit?: number;
  date_from?: string; // ISO 8601
  date_to?: string; // ISO 8601
  status?: ExecutionStatus[];
  agent_id?: string;
  tenant_id?: string; // super_admin only
  search?: string; // Search in agent name, execution ID
}

/**
 * Get paginated list of executions with filters
 */
export const getExecutions = async (filters: ExecutionFilters = {}): Promise<ExecutionListResponse> => {
  const {
    page = 1,
    limit = 50,
    date_from,
    date_to,
    status,
    agent_id,
    tenant_id,
    search,
  } = filters;

  const response = await apiClient.get<ExecutionListResponse>('/api/v1/executions', {
    params: {
      page,
      limit,
      ...(date_from && { date_from }),
      ...(date_to && { date_to }),
      ...(status && status.length > 0 && { status: status.join(',') }),
      ...(agent_id && { agent_id }),
      ...(tenant_id && { tenant_id }),
      ...(search && { search }),
    },
  });
  return response.data;
};

/**
 * Get execution detail by ID
 */
export const getExecutionDetail = async (id: string): Promise<ExecutionDetail> => {
  const response = await apiClient.get<ExecutionDetail>(`/api/v1/executions/${id}`);
  return response.data;
};

/**
 * Export executions to CSV
 * Returns CSV string
 */
export const exportExecutionsCSV = async (filters: ExecutionFilters = {}): Promise<string> => {
  const {
    date_from,
    date_to,
    status,
    agent_id,
    tenant_id,
    search,
  } = filters;

  const response = await apiClient.get<string>('/api/v1/executions/export', {
    params: {
      ...(date_from && { date_from }),
      ...(date_to && { date_to }),
      ...(status && status.length > 0 && { status: status.join(',') }),
      ...(agent_id && { agent_id }),
      ...(tenant_id && { tenant_id }),
      ...(search && { search }),
      format: 'csv',
    },
  });
  return response.data;
};

/**
 * Get list of agents for filter dropdown
 */
export interface AgentOption {
  id: string;
  name: string;
}

export const getAgentOptions = async (): Promise<AgentOption[]> => {
  const response = await apiClient.get<AgentOption[]>('/api/v1/agents/options');
  return response.data;
};
