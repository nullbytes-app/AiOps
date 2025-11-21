/**
 * Types for Agent Performance Dashboard (Story 13, 14 & 15)
 */

// Story 13 - Metrics Overview Types
export interface AgentMetricsDTO {
  agent_id: string;
  agent_name: string;
  date_range: {
    start: string;
    end: string;
  };
  metrics: {
    total_executions: number;
    successful_executions: number;
    failed_executions: number;
    success_rate: number; // percentage (0-100)
    avg_execution_time_ms: number;
    p50_execution_time_ms: number;
    p95_execution_time_ms: number;
    total_errors: number;
    error_rate: number; // percentage (0-100)
  };
}

// Story 14 - Trend Chart Types
export type TrendGranularity = 'hourly' | 'daily';

export interface AgentTrendDataPoint {
  timestamp: string; // ISO 8601
  execution_count: number;
  avg_execution_time_ms: number;
  p50_execution_time_ms: number;
  p95_execution_time_ms: number;
}

export interface AgentTrendsDTO {
  agent_id: string;
  agent_name: string;
  granularity: TrendGranularity;
  date_range: {
    start: string;
    end: string;
  };
  data_points: AgentTrendDataPoint[];
  summary: {
    total_data_points: number;
    peak_execution_count: number;
    peak_timestamp: string;
    avg_execution_time_overall_ms: number;
  };
}

// Story 15 - Error Analysis Types
export type SeverityLevel = 'low' | 'medium' | 'high';

export interface ErrorAnalysisDTO {
  error_type: string;
  error_message: string;
  occurrences: number;
  first_seen: string; // ISO 8601 timestamp
  last_seen: string; // ISO 8601 timestamp
  affected_executions: number;
  sample_stack_trace?: string;
  execution_ids: string[];
}

export interface ErrorAnalysisResponse {
  errors: ErrorAnalysisDTO[];
}

// Story 16 - Slowest Executions Types
export interface SlowestExecutionDTO {
  execution_id: string;
  agent_name: string;
  duration_ms: number; // milliseconds
  start_time: string; // ISO 8601 timestamp
  status: 'success' | 'failed' | 'pending';
  input_preview: string; // First 80 chars
  output_preview: string; // First 200 chars
  conversation_steps_count: number;
  tool_calls_count: number;
  error_message?: string; // Only if status = failed
}

export interface SlowestExecutionsResponse {
  executions: SlowestExecutionDTO[];
  total_count: number;
}
