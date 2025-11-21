/**
 * MSW Mock Handlers for Health API
 *
 * Provides realistic mock data for health endpoints during development and testing.
 */

import { http, HttpResponse } from 'msw';

/**
 * Health API mock handlers
 */
export const healthHandlers = [
  // GET /api/v1/health
  http.get('/api/v1/health', () => {
    return HttpResponse.json({
      api: {
        status: 'healthy',
        uptime: 86400, // 24 hours in seconds
        response_time_ms: 45,
      },
      workers: {
        status: 'healthy',
        details: {
          active_workers: 5,
          total_workers: 10,
          cpu_usage_percent: 35.2,
          memory_usage_mb: 512,
        },
      },
      database: {
        status: 'healthy',
        response_time_ms: 12,
        details: {
          connection_count: 15,
          max_connections: 100,
        },
      },
      redis: {
        status: 'healthy',
        details: {
          memory_usage_mb: 128,
          max_memory_mb: 2048,
          hit_rate: 0.95,
        },
      },
      timestamp: new Date().toISOString(),
    });
  }),
];
