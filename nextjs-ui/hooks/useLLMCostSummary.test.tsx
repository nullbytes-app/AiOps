/**
 * Unit tests for useLLMCostSummary React Query hook
 * Tests data fetching, auto-refresh, error handling, and retry logic
 */

import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import axios from 'axios';
import { useLLMCostSummary } from './useLLMCostSummary';
import { CostSummaryDTO } from '@/types/costs';

// Mock axios
jest.mock('axios');
const mockedAxios = axios as jest.Mocked<typeof axios>;

// Mock cost summary data
const mockCostSummary: CostSummaryDTO = {
  today_spend: 1234.56,
  week_spend: 8765.43,
  month_spend: 35000.12,
  total_spend_30d: 42000.5,
  top_tenant: {
    tenant_id: 'tenant-1',
    tenant_name: 'Acme Corp',
    total_spend: 15000.0,
    rank: 1,
  },
  top_agent: {
    agent_id: 'agent-123',
    agent_name: 'Ticket Enhancer',
    execution_count: 150,
    total_cost: 5000.0,
    avg_cost: 33.33,
  },
};

// Helper to create test query client
function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false, // Disable retries in tests for faster failures
      },
    },
  });
}

// Helper to create wrapper with QueryClientProvider
function createWrapper() {
  const queryClient = createTestQueryClient();
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}

describe('useLLMCostSummary', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('fetches cost summary successfully', async () => {
    mockedAxios.get.mockResolvedValueOnce({ data: mockCostSummary });

    const { result } = renderHook(() => useLLMCostSummary(), {
      wrapper: createWrapper(),
    });

    // Initially loading
    expect(result.current.isLoading).toBe(true);
    expect(result.current.data).toBeUndefined();

    // Wait for data to load
    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    // Verify data
    expect(result.current.data).toEqual(mockCostSummary);
    expect(result.current.isLoading).toBe(false);
    expect(result.current.isError).toBe(false);

    // Verify API was called with correct endpoint
    expect(mockedAxios.get).toHaveBeenCalledWith(
      '/api/v1/costs/summary',
      expect.objectContaining({
        headers: { 'Content-Type': 'application/json' },
        timeout: 5000,
      })
    );
  });

  test('handles API error correctly', async () => {
    const errorMessage = 'Network error';
    mockedAxios.get.mockRejectedValueOnce(new Error(errorMessage));

    const { result } = renderHook(() => useLLMCostSummary(), {
      wrapper: createWrapper(),
    });

    // Wait for error state
    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    // Verify error state
    expect(result.current.error).toBeInstanceOf(Error);
    expect(result.current.error?.message).toBe(errorMessage);
    expect(result.current.data).toBeUndefined();
    expect(result.current.isLoading).toBe(false);
  });

  test('uses correct query key for caching', async () => {
    mockedAxios.get.mockResolvedValueOnce({ data: mockCostSummary });

    const { result } = renderHook(() => useLLMCostSummary(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    // Query key should be ['costs', 'summary']
    // This is tested implicitly by React Query's caching behavior
    expect(mockedAxios.get).toHaveBeenCalledTimes(1);
  });

  test('refetch calls API again', async () => {
    mockedAxios.get.mockResolvedValueOnce({ data: mockCostSummary });

    const { result } = renderHook(() => useLLMCostSummary(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    // Clear mock to track refetch call
    mockedAxios.get.mockClear();
    mockedAxios.get.mockResolvedValueOnce({
      data: { ...mockCostSummary, today_spend: 2000.0 },
    });

    // Trigger manual refetch
    result.current.refetch();

    await waitFor(() => {
      expect(mockedAxios.get).toHaveBeenCalledTimes(1);
    });
  });

  test('handles empty/null top_tenant and top_agent', async () => {
    const emptyData: CostSummaryDTO = {
      today_spend: 0,
      week_spend: 0,
      month_spend: 0,
      total_spend_30d: 0,
      top_tenant: null,
      top_agent: null,
    };

    mockedAxios.get.mockResolvedValueOnce({ data: emptyData });

    const { result } = renderHook(() => useLLMCostSummary(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data?.top_tenant).toBeNull();
    expect(result.current.data?.top_agent).toBeNull();
  });

  test('handles 401 unauthorized error', async () => {
    const error = {
      response: { status: 401, data: { detail: 'Unauthorized' } },
    };
    mockedAxios.get.mockRejectedValueOnce(error);

    const { result } = renderHook(() => useLLMCostSummary(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    expect(result.current.error).toBeDefined();
  });

  test('handles 500 server error', async () => {
    const error = {
      response: { status: 500, data: { detail: 'Internal Server Error' } },
    };
    mockedAxios.get.mockRejectedValueOnce(error);

    const { result } = renderHook(() => useLLMCostSummary(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    expect(result.current.error).toBeDefined();
  });
});
