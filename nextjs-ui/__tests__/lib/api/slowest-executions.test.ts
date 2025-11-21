/**
 * Unit tests for slowest-executions API client
 * Story 16: Agent Performance Dashboard - Slowest Executions
 * Testing: getSlowestExecutions function with various parameters
 */

import { getSlowestExecutions } from '@/lib/api/slowest-executions';
import { apiClient } from '@/lib/api/client';
import type { SlowestExecutionsResponse } from '@/types/agent-performance';

jest.mock('@/lib/api/client');

const mockApiClient = apiClient as jest.Mocked<typeof apiClient>;

describe('getSlowestExecutions', () => {
  const mockResponse: SlowestExecutionsResponse = {
    executions: [
      {
        execution_id: 'exec-slow-1',
        agent_name: 'Test Agent',
        duration_ms: 145000, // 2m 25s
        start_time: '2025-01-20T10:00:00Z',
        status: 'success',
        input_preview: 'Analyze the sales data and generate comprehensive report',
        output_preview: 'Sales analysis complete. Revenue increased by 25% compared to last quarter',
        conversation_steps_count: 8,
        tool_calls_count: 12,
      },
      {
        execution_id: 'exec-slow-2',
        agent_name: 'Test Agent',
        duration_ms: 120500, // 2m 0.5s
        start_time: '2025-01-20T09:30:00Z',
        status: 'failed',
        input_preview: 'Process customer feedback and extract sentiment scores',
        output_preview: '',
        conversation_steps_count: 3,
        tool_calls_count: 5,
        error_message: 'API rate limit exceeded',
      },
    ],
    total_count: 25,
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('fetches slowest executions with default parameters', async () => {
    mockApiClient.get.mockResolvedValue({ data: mockResponse });

    const startDate = new Date('2025-01-14T00:00:00Z');
    const endDate = new Date('2025-01-21T00:00:00Z');

    const result = await getSlowestExecutions('agent-123', startDate, endDate);

    expect(result).toEqual(mockResponse);
    expect(mockApiClient.get).toHaveBeenCalledWith(
      expect.stringContaining('/agents/agent-123/slowest-executions')
    );

    const callArg = mockApiClient.get.mock.calls[0][0];
    expect(callArg).toContain('start_date=2025-01-14T00%3A00%3A00.000Z');
    expect(callArg).toContain('end_date=2025-01-21T00%3A00%3A00.000Z');
    expect(callArg).toContain('limit=10');
    expect(callArg).toContain('offset=0');
    expect(callArg).not.toContain('status='); // Default "all" should not add status param
  });

  it('fetches with custom limit and offset (pagination)', async () => {
    mockApiClient.get.mockResolvedValue({ data: mockResponse });

    const startDate = new Date('2025-01-14T00:00:00Z');
    const endDate = new Date('2025-01-21T00:00:00Z');

    await getSlowestExecutions('agent-123', startDate, endDate, 20, 10);

    const callArg = mockApiClient.get.mock.calls[0][0];
    expect(callArg).toContain('limit=20');
    expect(callArg).toContain('offset=10');
  });

  it('includes status filter when set to "success"', async () => {
    mockApiClient.get.mockResolvedValue({ data: mockResponse });

    const startDate = new Date('2025-01-14T00:00:00Z');
    const endDate = new Date('2025-01-21T00:00:00Z');

    await getSlowestExecutions('agent-123', startDate, endDate, 10, 0, 'success');

    const callArg = mockApiClient.get.mock.calls[0][0];
    expect(callArg).toContain('status=success');
  });

  it('includes status filter when set to "failed"', async () => {
    mockApiClient.get.mockResolvedValue({ data: mockResponse });

    const startDate = new Date('2025-01-14T00:00:00Z');
    const endDate = new Date('2025-01-21T00:00:00Z');

    await getSlowestExecutions('agent-123', startDate, endDate, 10, 0, 'failed');

    const callArg = mockApiClient.get.mock.calls[0][0];
    expect(callArg).toContain('status=failed');
  });

  it('does not include status filter when set to "all"', async () => {
    mockApiClient.get.mockResolvedValue({ data: mockResponse });

    const startDate = new Date('2025-01-14T00:00:00Z');
    const endDate = new Date('2025-01-21T00:00:00Z');

    await getSlowestExecutions('agent-123', startDate, endDate, 10, 0, 'all');

    const callArg = mockApiClient.get.mock.calls[0][0];
    expect(callArg).not.toContain('status=');
  });

  it('handles different agent IDs correctly', async () => {
    mockApiClient.get.mockResolvedValue({ data: mockResponse });

    const startDate = new Date('2025-01-14T00:00:00Z');
    const endDate = new Date('2025-01-21T00:00:00Z');

    await getSlowestExecutions('agent-456', startDate, endDate);

    const callArg = mockApiClient.get.mock.calls[0][0];
    expect(callArg).toContain('/agents/agent-456/slowest-executions');
  });

  it('correctly formats ISO 8601 timestamps in query params', async () => {
    mockApiClient.get.mockResolvedValue({ data: mockResponse });

    const startDate = new Date('2025-01-14T15:30:45.123Z');
    const endDate = new Date('2025-01-21T18:45:30.456Z');

    await getSlowestExecutions('agent-123', startDate, endDate);

    const callArg = mockApiClient.get.mock.calls[0][0];
    // URL encoding: ':' becomes %3A
    expect(callArg).toContain('start_date=2025-01-14T15%3A30%3A45.123Z');
    expect(callArg).toContain('end_date=2025-01-21T18%3A45%3A30.456Z');
  });

  it('handles empty results', async () => {
    const emptyResponse: SlowestExecutionsResponse = {
      executions: [],
      total_count: 0,
    };

    mockApiClient.get.mockResolvedValue({ data: emptyResponse });

    const startDate = new Date('2025-01-14T00:00:00Z');
    const endDate = new Date('2025-01-21T00:00:00Z');

    const result = await getSlowestExecutions('agent-123', startDate, endDate);

    expect(result).toEqual(emptyResponse);
    expect(result.executions).toHaveLength(0);
    expect(result.total_count).toBe(0);
  });

  it('propagates API errors correctly', async () => {
    const apiError = new Error('Network error');
    mockApiClient.get.mockRejectedValue(apiError);

    const startDate = new Date('2025-01-14T00:00:00Z');
    const endDate = new Date('2025-01-21T00:00:00Z');

    await expect(
      getSlowestExecutions('agent-123', startDate, endDate)
    ).rejects.toThrow('Network error');
  });

  it('handles 404 errors when agent not found', async () => {
    const notFoundError = {
      response: {
        status: 404,
        data: { message: 'Agent not found' },
      },
    };
    mockApiClient.get.mockRejectedValue(notFoundError);

    const startDate = new Date('2025-01-14T00:00:00Z');
    const endDate = new Date('2025-01-21T00:00:00Z');

    await expect(
      getSlowestExecutions('nonexistent-agent', startDate, endDate)
    ).rejects.toEqual(notFoundError);
  });

  it('constructs correct URL with all parameters', async () => {
    mockApiClient.get.mockResolvedValue({ data: mockResponse });

    const startDate = new Date('2025-01-14T00:00:00Z');
    const endDate = new Date('2025-01-21T00:00:00Z');

    await getSlowestExecutions('agent-123', startDate, endDate, 15, 5, 'success');

    expect(mockApiClient.get).toHaveBeenCalledTimes(1);
    const callArg = mockApiClient.get.mock.calls[0][0];

    // Verify all query params are present
    expect(callArg).toContain('start_date=');
    expect(callArg).toContain('end_date=');
    expect(callArg).toContain('limit=15');
    expect(callArg).toContain('offset=5');
    expect(callArg).toContain('status=success');
  });
});
