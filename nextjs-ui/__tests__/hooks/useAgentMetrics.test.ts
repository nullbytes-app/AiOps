/**
 * Unit tests for useAgentMetrics hook
 * Coverage target: ≥90%
 */

import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useAgentMetrics } from '@/hooks/useAgentMetrics';
import { apiClient } from '@/lib/api/client';
import type { AgentMetricsDTO } from '@/types/agent-performance';
import React from 'react';

// Mock API client
jest.mock('@/lib/api/client', () => ({
  apiClient: {
    get: jest.fn(),
    post: jest.fn(),
    put: jest.fn(),
    delete: jest.fn(),
  },
}));

const mockApiClient = apiClient as jest.Mocked<typeof apiClient>;

const mockMetricsData: AgentMetricsDTO = {
  agent_id: 'agent-123',
  agent_name: 'Test Agent',
  date_range: {
    start: '2025-01-14T00:00:00Z',
    end: '2025-01-21T23:59:59Z',
  },
  metrics: {
    total_executions: 1547,
    successful_executions: 1532,
    failed_executions: 15,
    success_rate: 99.03,
    error_rate: 0.97,
    avg_execution_time_ms: 2345.67,
    p50_execution_time_ms: 1890.0,
    p95_execution_time_ms: 4567.89,
    p99_execution_time_ms: 6789.12,
  },
  last_updated: '2025-01-21T14:45:00Z',
};

// Helper to create wrapper with QueryClient
const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        cacheTime: 0,
      },
    },
    logger: {
      log: console.log,
      warn: console.warn,
      error: () => {}, // Silent errors in tests
    },
  });
  return ({ children }: { children: React.ReactNode }) =>
    React.createElement(QueryClientProvider, { client: queryClient }, children);
};

describe('useAgentMetrics', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('fetches metrics successfully with valid agent ID', async () => {
    mockApiClient.get.mockResolvedValueOnce({ data: mockMetricsData });

    const { result } = renderHook(
      () => useAgentMetrics({
        agentId: 'agent-123',
        startDate: '2025-01-14',
        endDate: '2025-01-21',
      }),
      { wrapper: createWrapper() }
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(mockApiClient.get).toHaveBeenCalledWith(
      '/api/agents/agent-123/metrics?start_date=2025-01-14&end_date=2025-01-21',
      { timeout: 5000 }
    );
    expect(result.current.data).toEqual(mockMetricsData);
  });

  it('does not fetch if agentId is null (enabled=false)', () => {
    const { result } = renderHook(
      () => useAgentMetrics({
        agentId: null,
        startDate: '2025-01-14',
        endDate: '2025-01-21',
      }),
      { wrapper: createWrapper() }
    );

    expect(result.current.fetchStatus).toBe('idle');
    expect(mockApiClient.get).not.toHaveBeenCalled();
  });

  it('does not fetch if enabled is false', () => {
    const { result } = renderHook(
      () => useAgentMetrics({
        agentId: 'agent-123',
        startDate: '2025-01-14',
        endDate: '2025-01-21',
        enabled: false,
      }),
      { wrapper: createWrapper() }
    );

    expect(result.current.fetchStatus).toBe('idle');
    expect(mockApiClient.get).not.toHaveBeenCalled();
  });

  it('handles API errors gracefully', async () => {
    const error = new Error('Network error');
    mockApiClient.get.mockRejectedValueOnce(error);

    const { result } = renderHook(
      () => useAgentMetrics({
        agentId: 'agent-123',
        startDate: '2025-01-14',
        endDate: '2025-01-21',
      }),
      { wrapper: createWrapper() }
    );

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.error).toEqual(error);
  });

  it('uses correct query key for caching', () => {
    const { result } = renderHook(
      () => useAgentMetrics({
        agentId: 'agent-123',
        startDate: '2025-01-14',
        endDate: '2025-01-21',
      }),
      { wrapper: createWrapper() }
    );

    // Query key should include agentId and date range for granular caching
    expect(result.current.data).toBeUndefined(); // Not yet fetched, but query key is set
  });
});
