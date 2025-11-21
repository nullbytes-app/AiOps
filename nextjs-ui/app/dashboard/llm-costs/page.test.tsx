/**
 * Unit tests for LLM Cost Dashboard Page
 * Tests RBAC, rendering, loading states, error handling
 */

import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useSession } from 'next-auth/react';
import { useRouter } from 'next/navigation';
import LLMCostsPage from './page';
import * as useLLMCostSummaryModule from '@/hooks/useLLMCostSummary';
import * as useLLMCostTrendModule from '@/hooks/useLLMCostTrend';
import { CostSummaryDTO, DailySpendDTO } from '@/types/costs';

// Mock dependencies
jest.mock('next-auth/react');
jest.mock('next/navigation');
jest.mock('@/hooks/useLLMCostSummary');
jest.mock('@/hooks/useLLMCostTrend');
jest.mock('./components/DailySpendChart', () => ({
  DailySpendChart: ({ data, loading }: { data?: Array<Record<string, string | number | boolean>>; loading?: boolean }) => (
    <div data-testid="daily-spend-chart" data-loading={loading} data-has-data={!!data}>
      {loading ? 'Chart Loading...' : data ? `Chart with ${data.length} days` : 'No chart data'}
    </div>
  ),
}));

const mockedUseSession = useSession as jest.MockedFunction<typeof useSession>;
const mockedUseRouter = useRouter as jest.MockedFunction<typeof useRouter>;
const mockedUseLLMCostSummary = jest.spyOn(useLLMCostSummaryModule, 'useLLMCostSummary');
const mockedUseLLMCostTrend = jest.spyOn(useLLMCostTrendModule, 'useLLMCostTrend');

// Mock data
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
    execution_count: 1500,
    total_cost: 5000.0,
    avg_cost: 33.33,
  },
};

const mockTrendData: DailySpendDTO[] = [
  { date: '2025-01-01', total_spend: 100.50, transaction_count: 50 },
  { date: '2025-01-02', total_spend: 150.75, transaction_count: 75 },
  { date: '2025-01-03', total_spend: 200.00, transaction_count: 100 },
];

// Helper to create test query client
function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });
}

// Helper to create wrapper with QueryClientProvider
function renderWithProviders(component: React.ReactElement) {
  const queryClient = createTestQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>{component}</QueryClientProvider>
  );
}

describe('LLMCostsPage', () => {
  const mockPush = jest.fn();
  const mockRefetch = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
    mockedUseRouter.mockReturnValue({
      push: mockPush,
      replace: jest.fn(),
      prefetch: jest.fn(),
      back: jest.fn(),
      forward: jest.fn(),
      refresh: jest.fn(),
    } as ReturnType<typeof useRouter>);
  });

  test('renders page with data successfully', async () => {
    // Mock authenticated session
    mockedUseSession.mockReturnValue({
      data: { user: { email: 'admin@example.com' }, expires: '2025-12-31' },
      status: 'authenticated',
      update: jest.fn(),
    } as ReturnType<typeof useSession>);

    // Mock successful data fetch
    mockedUseLLMCostSummary.mockReturnValue({
      data: mockCostSummary,
      isLoading: false,
      isError: false,
      error: null,
      refetch: mockRefetch,
    });

    mockedUseLLMCostTrend.mockReturnValue({
      data: mockTrendData,
      isLoading: false,
      isError: false,
      error: null,
      refetch: jest.fn(),
    });

    renderWithProviders(<LLMCostsPage />);

    // Check for page title
    expect(screen.getByText('LLM Cost Dashboard')).toBeInTheDocument();

    // Check for metrics
    expect(screen.getByText("Today's Spend")).toBeInTheDocument();
    expect(screen.getByText('$1,234.56')).toBeInTheDocument();

    // Check for auto-refresh info
    expect(screen.getByText(/Auto-refreshes every 60s/)).toBeInTheDocument();
  });

  test('shows loading skeleton when data is loading', () => {
    mockedUseSession.mockReturnValue({
      data: { user: { email: 'admin@example.com' }, expires: '2025-12-31' },
      status: 'authenticated',
      update: jest.fn(),
    } as ReturnType<typeof useSession>);

    mockedUseLLMCostSummary.mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
      error: null,
      refetch: mockRefetch,
    });

    mockedUseLLMCostTrend.mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
      error: null,
      refetch: jest.fn(),
    });

    renderWithProviders(<LLMCostsPage />);

    // Should show loading cards (5 total)
    const loadingCards = screen.getAllByRole('status', { name: /loading/i });
    expect(loadingCards.length).toBeGreaterThan(0);
  });

  test('shows error state when data fetch fails', () => {
    mockedUseSession.mockReturnValue({
      data: { user: { email: 'admin@example.com' }, expires: '2025-12-31' },
      status: 'authenticated',
      update: jest.fn(),
    } as ReturnType<typeof useSession>);

    const mockError = new Error('Network error');
    mockedUseLLMCostSummary.mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
      error: mockError,
      refetch: mockRefetch,
    });

    mockedUseLLMCostTrend.mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: false,
      error: null,
      refetch: jest.fn(),
    });

    renderWithProviders(<LLMCostsPage />);

    // Check for error message
    expect(screen.getByText('Failed to Load Cost Data')).toBeInTheDocument();
    expect(screen.getByText(/Network error/)).toBeInTheDocument();

    // Check for retry button
    expect(screen.getByRole('button', { name: /retry/i })).toBeInTheDocument();
  });

  test('refetch button calls refetch function', async () => {
    const user = userEvent.setup();

    mockedUseSession.mockReturnValue({
      data: { user: { email: 'admin@example.com' }, expires: '2025-12-31' },
      status: 'authenticated',
      update: jest.fn(),
    } as ReturnType<typeof useSession>);

    mockedUseLLMCostSummary.mockReturnValue({
      data: mockCostSummary,
      isLoading: false,
      isError: false,
      error: null,
      refetch: mockRefetch,
    });

    mockedUseLLMCostTrend.mockReturnValue({
      data: mockTrendData,
      isLoading: false,
      isError: false,
      error: null,
      refetch: jest.fn(),
    });

    renderWithProviders(<LLMCostsPage />);

    // Find and click refresh button
    const refreshButton = screen.getByRole('button', { name: /refresh/i });
    await user.click(refreshButton);

    // Verify refetch was called
    expect(mockRefetch).toHaveBeenCalledTimes(1);
  });

  test('retry button in error state calls refetch', async () => {
    const user = userEvent.setup();

    mockedUseSession.mockReturnValue({
      data: { user: { email: 'admin@example.com' }, expires: '2025-12-31' },
      status: 'authenticated',
      update: jest.fn(),
    } as ReturnType<typeof useSession>);

    mockedUseLLMCostSummary.mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
      error: new Error('Network error'),
      refetch: mockRefetch,
    });

    mockedUseLLMCostTrend.mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: false,
      error: null,
      refetch: jest.fn(),
    });

    renderWithProviders(<LLMCostsPage />);

    // Find and click retry button
    const retryButton = screen.getByRole('button', { name: /retry/i });
    await user.click(retryButton);

    // Verify refetch was called
    expect(mockRefetch).toHaveBeenCalledTimes(1);
  });

  test('redirects to login when unauthenticated', async () => {
    mockedUseSession.mockReturnValue({
      data: null,
      status: 'unauthenticated',
      update: jest.fn(),
    } as ReturnType<typeof useSession>);

    mockedUseLLMCostSummary.mockReturnValue({
      data: mockCostSummary,
      isLoading: false,
      isError: false,
      error: null,
      refetch: mockRefetch,
    });

    mockedUseLLMCostTrend.mockReturnValue({
      data: mockTrendData,
      isLoading: false,
      isError: false,
      error: null,
      refetch: jest.fn(),
    });

    renderWithProviders(<LLMCostsPage />);

    // Wait for redirect
    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith('/login');
    });
  });

  test('does not redirect when authenticated', () => {
    mockedUseSession.mockReturnValue({
      data: { user: { email: 'admin@example.com' }, expires: '2025-12-31' },
      status: 'authenticated',
      update: jest.fn(),
    } as ReturnType<typeof useSession>);

    mockedUseLLMCostSummary.mockReturnValue({
      data: mockCostSummary,
      isLoading: false,
      isError: false,
      error: null,
      refetch: mockRefetch,
    });

    mockedUseLLMCostTrend.mockReturnValue({
      data: mockTrendData,
      isLoading: false,
      isError: false,
      error: null,
      refetch: jest.fn(),
    });

    renderWithProviders(<LLMCostsPage />);

    // Should NOT redirect
    expect(mockPush).not.toHaveBeenCalled();

    // Should show page content
    expect(screen.getByText('LLM Cost Dashboard')).toBeInTheDocument();
  });

  describe('Daily Spend Chart Integration', () => {
    beforeEach(() => {
      mockedUseSession.mockReturnValue({
        data: { user: { email: 'admin@example.com' }, expires: '2025-12-31' },
        status: 'authenticated',
        update: jest.fn(),
      } as ReturnType<typeof useSession>);

      mockedUseLLMCostSummary.mockReturnValue({
        data: mockCostSummary,
        isLoading: false,
        isError: false,
        error: null,
        refetch: mockRefetch,
      });
    });

    test('renders daily spend chart with trend data', () => {
      mockedUseLLMCostTrend.mockReturnValue({
        data: mockTrendData,
        isLoading: false,
        isError: false,
        error: null,
        refetch: jest.fn(),
      });

      renderWithProviders(<LLMCostsPage />);

      // Should render chart component
      const chart = screen.getByTestId('daily-spend-chart');
      expect(chart).toBeInTheDocument();
      expect(chart).toHaveAttribute('data-has-data', 'true');
      expect(chart).toHaveAttribute('data-loading', 'false');
      expect(screen.getByText(`Chart with ${mockTrendData.length} days`)).toBeInTheDocument();
    });

    test('shows chart loading state when trend data is loading', () => {
      mockedUseLLMCostTrend.mockReturnValue({
        data: undefined,
        isLoading: true,
        isError: false,
        error: null,
        refetch: jest.fn(),
      });

      renderWithProviders(<LLMCostsPage />);

      // Chart should show loading state
      const chart = screen.getByTestId('daily-spend-chart');
      expect(chart).toHaveAttribute('data-loading', 'true');
      expect(screen.getByText('Chart Loading...')).toBeInTheDocument();
    });

    test('handles chart with no trend data', () => {
      mockedUseLLMCostTrend.mockReturnValue({
        data: undefined,
        isLoading: false,
        isError: false,
        error: null,
        refetch: jest.fn(),
      });

      renderWithProviders(<LLMCostsPage />);

      // Chart should handle empty state
      const chart = screen.getByTestId('daily-spend-chart');
      expect(chart).toHaveAttribute('data-has-data', 'false');
      expect(screen.getByText('No chart data')).toBeInTheDocument();
    });

    test('chart fetches 30 days of data by default', () => {
      mockedUseLLMCostTrend.mockReturnValue({
        data: mockTrendData,
        isLoading: false,
        isError: false,
        error: null,
        refetch: jest.fn(),
      });

      renderWithProviders(<LLMCostsPage />);

      // Verify hook was called with correct parameter
      expect(mockedUseLLMCostTrend).toHaveBeenCalledWith(30);
    });

    test('page renders both metrics cards and trend chart', () => {
      mockedUseLLMCostTrend.mockReturnValue({
        data: mockTrendData,
        isLoading: false,
        isError: false,
        error: null,
        refetch: jest.fn(),
      });

      renderWithProviders(<LLMCostsPage />);

      // Both components should be present
      expect(screen.getByText("Today's Spend")).toBeInTheDocument(); // Metrics card
      expect(screen.getByTestId('daily-spend-chart')).toBeInTheDocument(); // Chart
    });
  });
});
