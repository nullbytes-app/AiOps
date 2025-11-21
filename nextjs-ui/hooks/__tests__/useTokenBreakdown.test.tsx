/**
 * Tests for useTokenBreakdown Hook and calculatePercentages Utility
 *
 * Covers:
 * - Percentage calculation: (count / total) * 100
 * - Edge case: total = 0 (prevent division by zero)
 * - Rounding to 2 decimal places
 * - API integration with date range params
 */

import React from 'react';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import axios from 'axios';
import { useTokenBreakdown, calculatePercentages } from '../useTokenBreakdown';
import { TokenBreakdownDTO } from '@/types/costs';

// Mock axios
jest.mock('axios');
const mockedAxios = axios as jest.Mocked<typeof axios>;

// Test wrapper with QueryClient
function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });

  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}

describe('calculatePercentages', () => {
  it('calculates correct percentages for normal data', () => {
    const data: TokenBreakdownDTO[] = [
      { tokenType: 'input', count: 750, cost: 0.015 },
      { tokenType: 'output', count: 250, cost: 0.030 },
    ];

    const result = calculatePercentages(data);

    expect(result).toHaveLength(2);
    expect(result[0].percentage).toBe(75); // 750 / 1000 * 100
    expect(result[1].percentage).toBe(25); // 250 / 1000 * 100
  });

  it('handles zero total tokens (edge case)', () => {
    const data: TokenBreakdownDTO[] = [
      { tokenType: 'input', count: 0, cost: 0 },
      { tokenType: 'output', count: 0, cost: 0 },
    ];

    const result = calculatePercentages(data);

    expect(result).toHaveLength(2);
    expect(result[0].percentage).toBe(0);
    expect(result[1].percentage).toBe(0);
  });

  it('calculates percentages with precision for uneven splits', () => {
    const data: TokenBreakdownDTO[] = [
      { tokenType: 'input', count: 333, cost: 0.007 },
      { tokenType: 'output', count: 667, cost: 0.013 },
    ];

    const result = calculatePercentages(data);

    expect(result[0].percentage).toBeCloseTo(33.3, 1); // 333 / 1000 * 100 = 33.3%
    expect(result[1].percentage).toBeCloseTo(66.7, 1); // 667 / 1000 * 100 = 66.7%
  });

  it('handles single token type (100% percentage)', () => {
    const data: TokenBreakdownDTO[] = [
      { tokenType: 'input', count: 1000, cost: 0.020 },
    ];

    const result = calculatePercentages(data);

    expect(result).toHaveLength(1);
    expect(result[0].percentage).toBe(100);
  });

  it('preserves original data fields', () => {
    const data: TokenBreakdownDTO[] = [
      { tokenType: 'input', count: 600, cost: 0.012 },
      { tokenType: 'output', count: 400, cost: 0.024 },
    ];

    const result = calculatePercentages(data);

    expect(result[0]).toMatchObject({
      tokenType: 'input',
      count: 600,
      cost: 0.012,
    });
    expect(result[1]).toMatchObject({
      tokenType: 'output',
      count: 400,
      cost: 0.024,
    });
  });
});

describe('useTokenBreakdown Hook', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('fetches token breakdown data successfully', async () => {
    const mockData: TokenBreakdownDTO[] = [
      { tokenType: 'input', count: 800, cost: 0.016 },
      { tokenType: 'output', count: 200, cost: 0.012 },
    ];

    mockedAxios.get.mockResolvedValueOnce({ data: mockData });

    const { result } = renderHook(() => useTokenBreakdown(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toHaveLength(2);
    expect(result.current.data?.[0].percentage).toBe(80); // 800 / 1000 * 100
    expect(result.current.data?.[1].percentage).toBe(20); // 200 / 1000 * 100
  });

  it('includes date range params in API request', async () => {
    const startDate = new Date('2025-01-01');
    const endDate = new Date('2025-01-31');

    mockedAxios.get.mockResolvedValueOnce({ data: [] });

    renderHook(() => useTokenBreakdown(startDate, endDate), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(mockedAxios.get).toHaveBeenCalled());

    expect(mockedAxios.get).toHaveBeenCalledWith(
      expect.stringContaining('?start_date=2025-01-01&end_date=2025-01-31'),
      expect.anything()
    );
  });

  it('formats date as ISO 8601 (YYYY-MM-DD)', async () => {
    const startDate = new Date('2025-11-15T10:30:00Z');
    const endDate = new Date('2025-11-20T23:45:00Z');

    mockedAxios.get.mockResolvedValueOnce({ data: [] });

    renderHook(() => useTokenBreakdown(startDate, endDate), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(mockedAxios.get).toHaveBeenCalled());

    // Verify date format is YYYY-MM-DD (no time component)
    expect(mockedAxios.get).toHaveBeenCalledWith(
      expect.stringContaining('start_date=2025-11-15'),
      expect.anything()
    );
    expect(mockedAxios.get).toHaveBeenCalledWith(
      expect.stringContaining('end_date=2025-11-20'),
      expect.anything()
    );
  });

  it('uses default date range when no dates provided', async () => {
    mockedAxios.get.mockResolvedValueOnce({ data: [] });

    renderHook(() => useTokenBreakdown(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(mockedAxios.get).toHaveBeenCalled());

    // Verify no query params when dates are omitted
    expect(mockedAxios.get).toHaveBeenCalledWith(
      '/api/v1/costs/token-breakdown',
      expect.anything()
    );
  });
});
