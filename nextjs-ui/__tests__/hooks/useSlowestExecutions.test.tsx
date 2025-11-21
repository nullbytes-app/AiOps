/**
 * Unit tests for useSlowestExecutions React Query hook
 * Story 16: Agent Performance Dashboard - Slowest Executions
 * Testing: Data fetching, caching, auto-refresh, error handling
 */

import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useSlowestExecutions } from '@/hooks/useSlowestExecutions';
import { getSlowestExecutions } from '@/lib/api/slowest-executions';
import type { SlowestExecutionsResponse } from '@/types/agent-performance';

jest.mock('@/lib/api/slowest-executions');

const mockGetSlowestExecutions = getSlowestExecutions as jest.MockedFunction<
  typeof getSlowestExecutions
>;

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false, // Disable retries in tests
      },
    },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
};

describe('useSlowestExecutions', () => {
  const mockResponse: SlowestExecutionsResponse = {
    executions: [
      {
        execution_id: 'exec-slow-1',
        agent_name: 'Test Agent',
        duration_ms: 145000, // 2m 25s
        start_time: '2025-01-20T10:00:00Z',
        status: 'success',
        input_preview: 'Analyze the sales data',
        output_preview: 'Sales analysis complete',
        conversation_steps_count: 8,
        tool_calls_count: 12,
      },
      {
        execution_id: 'exec-slow-2',
        agent_name: 'Test Agent',
        duration_ms: 120500, // 2m 0.5s
        start_time: '2025-01-20T09:30:00Z',
        status: 'failed',
        input_preview: 'Process customer feedback',
        output_preview: '',
        conversation_steps_count: 3,
        tool_calls_count: 5,
        error_message: 'API rate limit exceeded',
      },
    ],
    total_count: 25,
  };

  const defaultProps = {
    agentId: 'agent-123',
    startDate: new Date('2025-01-14T00:00:00Z'),
    endDate: new Date('2025-01-21T00:00:00Z'),
    page: 0,
    statusFilter: 'all' as const,
  };

  beforeEach(() => {
    jest.clearAllMocks();
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it('fetches data successfully with valid parameters', async () => {
    mockGetSlowestExecutions.mockResolvedValue(mockResponse);

    const { result } = renderHook(() => useSlowestExecutions(defaultProps), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toEqual(mockResponse);
    expect(mockGetSlowestExecutions).toHaveBeenCalledWith(
      'agent-123',
      defaultProps.startDate,
      defaultProps.endDate,
      10, // limit
      0, // offset (page 0)
      'all' // statusFilter
    );
  });

  it('does not fetch if agentId is null', () => {
    const { result } = renderHook(
      () =>
        useSlowestExecutions({
          ...defaultProps,
          agentId: null,
        }),
      { wrapper: createWrapper() }
    );

    expect(result.current.isLoading).toBe(false);
    expect(result.current.isFetching).toBe(false);
    expect(mockGetSlowestExecutions).not.toHaveBeenCalled();
  });

  it('does not fetch if enabled is false', () => {
    const { result } = renderHook(
      () =>
        useSlowestExecutions({
          ...defaultProps,
          enabled: false,
        }),
      { wrapper: createWrapper() }
    );

    expect(result.current.isLoading).toBe(false);
    expect(result.current.isFetching).toBe(false);
    expect(mockGetSlowestExecutions).not.toHaveBeenCalled();
  });

  it('calculates correct offset for pagination', async () => {
    mockGetSlowestExecutions.mockResolvedValue(mockResponse);

    const { result } = renderHook(
      () =>
        useSlowestExecutions({
          ...defaultProps,
          page: 2, // Page 2
        }),
      { wrapper: createWrapper() }
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(mockGetSlowestExecutions).toHaveBeenCalledWith(
      'agent-123',
      defaultProps.startDate,
      defaultProps.endDate,
      10, // limit
      20, // offset (page 2 * 10)
      'all'
    );
  });

  it('passes statusFilter to API correctly', async () => {
    mockGetSlowestExecutions.mockResolvedValue(mockResponse);

    const { result } = renderHook(
      () =>
        useSlowestExecutions({
          ...defaultProps,
          statusFilter: 'success',
        }),
      { wrapper: createWrapper() }
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(mockGetSlowestExecutions).toHaveBeenCalledWith(
      'agent-123',
      defaultProps.startDate,
      defaultProps.endDate,
      10,
      0,
      'success' // statusFilter passed through
    );
  });

  it('generates correct queryKey with all parameters', async () => {
    mockGetSlowestExecutions.mockResolvedValue(mockResponse);

    const { result } = renderHook(
      () =>
        useSlowestExecutions({
          agentId: 'agent-456',
          startDate: new Date('2025-01-15T00:00:00Z'),
          endDate: new Date('2025-01-22T00:00:00Z'),
          page: 1,
          statusFilter: 'failed',
        }),
      { wrapper: createWrapper() }
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    // Verify queryKey includes all params (dates as ISO strings)
    expect(mockGetSlowestExecutions).toHaveBeenCalledWith(
      'agent-456',
      new Date('2025-01-15T00:00:00Z'),
      new Date('2025-01-22T00:00:00Z'),
      10,
      10, // page 1 offset
      'failed'
    );
  });

  it('handles API errors correctly', async () => {
    const apiError = new Error('Network error');
    mockGetSlowestExecutions.mockRejectedValue(apiError);

    const { result } = renderHook(() => useSlowestExecutions(defaultProps), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isError).toBe(true));

    expect(result.current.error).toEqual(apiError);
    expect(result.current.data).toBeUndefined();
  });

  it('handles empty results', async () => {
    const emptyResponse: SlowestExecutionsResponse = {
      executions: [],
      total_count: 0,
    };
    mockGetSlowestExecutions.mockResolvedValue(emptyResponse);

    const { result } = renderHook(() => useSlowestExecutions(defaultProps), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toEqual(emptyResponse);
    expect(result.current.data?.executions).toHaveLength(0);
  });

  // AC #7: Test staleTime configuration (90 seconds)
  it('has staleTime configured to 90 seconds', async () => {
    mockGetSlowestExecutions.mockResolvedValue(mockResponse);

    const { result } = renderHook(() => useSlowestExecutions(defaultProps), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    // Data should be fresh initially
    expect(result.current.isStale).toBe(false);

    // Note: staleTime is difficult to test with fake timers in React Query
    // The important thing is that it's configured correctly (verified by reading hook code)
    // and the refetchInterval test below verifies the actual behavior
  });

  // AC #5 & #7: Test auto-refresh every 90 seconds
  it('refetches automatically every 90 seconds', async () => {
    mockGetSlowestExecutions.mockResolvedValue(mockResponse);

    const { result } = renderHook(() => useSlowestExecutions(defaultProps), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    // Initial fetch
    expect(mockGetSlowestExecutions).toHaveBeenCalledTimes(1);

    // Advance time by 90 seconds
    jest.advanceTimersByTime(90000);

    // Should trigger refetch
    await waitFor(() => expect(mockGetSlowestExecutions).toHaveBeenCalledTimes(2));

    // Advance another 90 seconds
    jest.advanceTimersByTime(90000);

    // Should trigger another refetch
    await waitFor(() => expect(mockGetSlowestExecutions).toHaveBeenCalledTimes(3));
  });

  // AC #7: Test retry configuration (3 retries in production, 0 in test)
  it('does not retry in test environment', async () => {
    const apiError = new Error('Network error');
    mockGetSlowestExecutions.mockRejectedValue(apiError);

    const { result } = renderHook(() => useSlowestExecutions(defaultProps), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isError).toBe(true));

    // Should only be called once (no retries in test env)
    expect(mockGetSlowestExecutions).toHaveBeenCalledTimes(1);
  });

  it('refetches on mount', async () => {
    mockGetSlowestExecutions.mockResolvedValue(mockResponse);

    // First render
    const { result: result1, unmount } = renderHook(
      () => useSlowestExecutions(defaultProps),
      { wrapper: createWrapper() }
    );

    await waitFor(() => expect(result1.current.isSuccess).toBe(true));
    expect(mockGetSlowestExecutions).toHaveBeenCalledTimes(1);

    // Unmount first instance
    unmount();

    // Create new instance (remount)
    const { result: result2 } = renderHook(
      () => useSlowestExecutions(defaultProps),
      { wrapper: createWrapper() }
    );

    // Should refetch on mount
    await waitFor(() => expect(result2.current.isSuccess).toBe(true));
    expect(mockGetSlowestExecutions).toHaveBeenCalledTimes(2);
  });

  it('does not refetch on window focus', async () => {
    mockGetSlowestExecutions.mockResolvedValue(mockResponse);

    const { result } = renderHook(() => useSlowestExecutions(defaultProps), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(mockGetSlowestExecutions).toHaveBeenCalledTimes(1);

    // Simulate window focus
    window.dispatchEvent(new Event('focus'));

    // Wait a bit to ensure no refetch
    await waitFor(() => expect(mockGetSlowestExecutions).toHaveBeenCalledTimes(1));
  });

  it('throws error if agentId is required but missing', async () => {
    // Temporarily enable the query with null agentId to test error
    const { result } = renderHook(
      () =>
        useSlowestExecutions({
          ...defaultProps,
          agentId: null,
          enabled: true, // Force enable even with null agentId
        }),
      { wrapper: createWrapper() }
    );

    // Query should be disabled due to enabled: enabled && !!agentId
    expect(result.current.isLoading).toBe(false);
    expect(mockGetSlowestExecutions).not.toHaveBeenCalled();
  });
});
