/**
 * Health API Client
 *
 * API functions for system health monitoring endpoints.
 */

import { apiClient } from './client';

/**
 * Component health status
 */
export type HealthStatus = 'healthy' | 'degraded' | 'down';

/**
 * Individual component health details
 */
export interface ComponentHealth {
  status: HealthStatus;
  uptime?: number;
  response_time_ms?: number;
  details?: Record<string, unknown>;
}

/**
 * System health status response
 */
export interface SystemHealthStatus {
  api: ComponentHealth;
  workers: ComponentHealth;
  database: ComponentHealth;
  redis: ComponentHealth;
  timestamp: string;
}

/**
 * Health API endpoints
 */
export const healthApi = {
  /**
   * Get system health status
   *
   * @returns System health status for all components
   * @throws {AxiosError} If API request fails
   */
  getStatus: async (): Promise<SystemHealthStatus> => {
    const response = await apiClient.get<SystemHealthStatus>('/api/v1/health');
    return response.data;
  },
};
