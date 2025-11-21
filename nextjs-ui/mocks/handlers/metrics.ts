/**
 * MSW Mock Handlers - Metrics APIs
 *
 * Mock handlers for agent and ticket metrics endpoints.
 * Generates realistic test data for development and testing.
 */

import { http, HttpResponse } from 'msw';

/**
 * Generate hourly data for the last 24 hours
 */
function generateHourlyData() {
  const data = [];
  const now = new Date();

  for (let i = 23; i >= 0; i--) {
    const hour = new Date(now.getTime() - i * 60 * 60 * 1000);
    data.push({
      hour: hour.toISOString(),
      success_count: Math.floor(Math.random() * 50) + 30,
      failure_count: Math.floor(Math.random() * 5),
    });
  }

  return data;
}

/**
 * Generate recent ticket activity
 */
function generateRecentTickets() {
  const statuses = ['success', 'failed', 'pending'] as const;
  const tickets = [];

  for (let i = 0; i < 20; i++) {
    const timestamp = new Date(Date.now() - i * 60 * 1000); // Last 20 minutes
    tickets.push({
      ticket_id: `TKT-${(10000 + i).toString()}`,
      status: statuses[Math.floor(Math.random() * statuses.length)],
      processing_time_ms: Math.floor(Math.random() * 5000) + 1000,
      timestamp: timestamp.toISOString(),
    });
  }

  return tickets;
}

/**
 * Metrics API Mock Handlers
 */
export const metricsHandlers = [
  /**
   * GET /api/v1/metrics/agents
   *
   * Returns agent execution metrics for specified time range.
   */
  http.get('/api/v1/metrics/agents', ({ request }) => {
    const url = new URL(request.url);
    const timeRange = url.searchParams.get('time_range') || '24h';

    return HttpResponse.json({
      total_executions: 1250,
      successful_executions: 1180,
      failed_executions: 70,
      total_cost: 15.4523,
      hourly_breakdown: generateHourlyData(),
      agent_breakdown: [
        {
          agent_name: 'ticket-enhancer',
          total_runs: 850,
          success_rate: 0.96,
          avg_latency_ms: 2340,
          total_cost: 10.23,
        },
        {
          agent_name: 'context-gatherer',
          total_runs: 400,
          success_rate: 0.92,
          avg_latency_ms: 1820,
          total_cost: 5.22,
        },
        {
          agent_name: 'monitoring-scanner',
          total_runs: 150,
          success_rate: 0.88,
          avg_latency_ms: 3120,
          total_cost: 2.15,
        },
        {
          agent_name: 'documentation-search',
          total_runs: 320,
          success_rate: 0.94,
          avg_latency_ms: 1650,
          total_cost: 4.18,
        },
        {
          agent_name: 'ip-lookup',
          total_runs: 280,
          success_rate: 0.98,
          avg_latency_ms: 890,
          total_cost: 1.42,
        },
      ],
    });
  }),

  /**
   * GET /api/v1/metrics/queue
   *
   * Returns ticket queue and processing metrics.
   */
  http.get('/api/v1/metrics/queue', () => {
    return HttpResponse.json({
      queue_depth: 42,
      processing_rate_per_hour: 85,
      error_rate_percentage: 5.6,
      recent_tickets: generateRecentTickets(),
    });
  }),
];
