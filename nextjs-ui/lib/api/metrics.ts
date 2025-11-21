/**
 * Metrics API Client
 *
 * API functions for agent execution and ticket processing metrics.
 */

import { apiClient } from './client';

/**
 * Time range options for metrics queries
 */
export type TimeRange = '24h' | '7d' | '30d';

/**
 * Hourly data point for execution timeline
 */
export interface HourlyData {
  hour: string; // ISO timestamp
  success_count: number;
  failure_count: number;
}

/**
 * Agent performance metrics
 */
export interface AgentPerformance {
  agent_name: string;
  total_runs: number;
  success_rate: number;
  avg_latency_ms: number;
  total_cost: number;
}

/**
 * Agent metrics response
 */
export interface AgentMetrics {
  total_executions: number;
  successful_executions: number;
  failed_executions: number;
  total_cost: number;
  hourly_breakdown: HourlyData[];
  agent_breakdown: AgentPerformance[];
}

/**
 * Recent ticket status
 */
export type TicketStatus = 'success' | 'failed' | 'pending';

/**
 * Recent ticket activity
 */
export interface RecentTicket {
  ticket_id: string;
  status: TicketStatus;
  processing_time_ms: number;
  timestamp: string;
}

/**
 * Ticket metrics response
 */
export interface TicketMetrics {
  queue_depth: number;
  processing_rate_per_hour: number;
  error_rate_percentage: number;
  recent_tickets: RecentTicket[];
}

/**
 * Metrics API endpoints
 */
export const metricsApi = {
  /**
   * Get agent execution metrics
   *
   * @param timeRange - Time range for metrics (default: 24h)
   * @returns Agent execution metrics and breakdowns
   * @throws {AxiosError} If API request fails
   */
  getAgentMetrics: async (timeRange: TimeRange = '24h'): Promise<AgentMetrics> => {
    const response = await apiClient.get<AgentMetrics>('/api/v1/metrics/agents', {
      params: { time_range: timeRange },
    });
    return response.data;
  },

  /**
   * Get ticket processing metrics
   *
   * @returns Ticket queue and processing metrics
   * @throws {AxiosError} If API request fails
   */
  getTicketMetrics: async (): Promise<TicketMetrics> => {
    const response = await apiClient.get<TicketMetrics>('/api/v1/metrics/queue');
    return response.data;
  },
};
