import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ExecutionTrendChart } from '@/components/agent-performance/ExecutionTrendChart';
import { useAgentTrends } from '@/hooks/useAgentTrends';
import type { AgentTrendsDTO } from '@/types/agent-performance';

jest.mock('@/hooks/useAgentTrends');
jest.mock('recharts', () => ({
  ...jest.requireActual('recharts'),
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="responsive-container">{children}</div>
  ),
}));

const mockUseAgentTrends = useAgentTrends as jest.MockedFunction<
  typeof useAgentTrends
>;

const mockTrendData: AgentTrendsDTO = {
  agent_id: 'agent-123',
  agent_name: 'Test Agent',
  granularity: 'hourly',
  date_range: {
    start: '2025-01-14T00:00:00Z',
    end: '2025-01-21T00:00:00Z',
  },
  data_points: [
    {
      timestamp: '2025-01-14T00:00:00Z',
      execution_count: 45,
      avg_execution_time_ms: 2345.67,
      p50_execution_time_ms: 1890.0,
      p95_execution_time_ms: 4567.89,
    },
    {
      timestamp: '2025-01-14T01:00:00Z',
      execution_count: 52,
      avg_execution_time_ms: 2123.45,
      p50_execution_time_ms: 1780.0,
      p95_execution_time_ms: 4234.56,
    },
  ],
  summary: {
    total_data_points: 2,
    peak_execution_count: 52,
    peak_timestamp: '2025-01-14T01:00:00Z',
    avg_execution_time_overall_ms: 2234.56,
  },
};

const createWrapper = () => {
  const queryClient = new QueryClient();
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
};

describe('ExecutionTrendChart', () => {
  const defaultProps = {
    agentId: 'agent-123',
    startDate: '2025-01-14',
    endDate: '2025-01-21',
    defaultGranularity: 'hourly' as const,
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('shows loading skeleton while fetching', () => {
    mockUseAgentTrends.mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
      refetch: jest.fn(),
    } as any);

    render(<ExecutionTrendChart {...defaultProps} />, { wrapper: createWrapper() });

    // Use queryByTestId to check element doesn't exist (getByTestId throws if not found)
    expect(screen.queryByTestId('responsive-container')).not.toBeInTheDocument();
    // Skeleton should be visible (check for skeleton class from Skeleton component)
    expect(screen.getByRole('status', { name: /loading/i })).toBeInTheDocument();
  });

  it('shows error state when API fails', () => {
    const mockRefetch = jest.fn();
    mockUseAgentTrends.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error('API Error'),
      refetch: mockRefetch,
    } as any);

    render(<ExecutionTrendChart {...defaultProps} />, { wrapper: createWrapper() });

    expect(screen.getByText(/Failed to load execution trends/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /retry/i })).toBeInTheDocument();
  });

  it('calls refetch when retry button clicked', async () => {
    const user = userEvent.setup();
    const mockRefetch = jest.fn();
    mockUseAgentTrends.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error('API Error'),
      refetch: mockRefetch,
    } as any);

    render(<ExecutionTrendChart {...defaultProps} />, { wrapper: createWrapper() });

    const retryButton = screen.getByRole('button', { name: /retry/i });
    await user.click(retryButton);

    expect(mockRefetch).toHaveBeenCalledTimes(1);
  });

  it('shows empty state when no data points', () => {
    mockUseAgentTrends.mockReturnValue({
      data: { ...mockTrendData, data_points: [] },
      isLoading: false,
      error: null,
      refetch: jest.fn(),
    } as any);

    render(<ExecutionTrendChart {...defaultProps} />, { wrapper: createWrapper() });

    expect(
      screen.getByText(/No execution data available for the selected date range/i)
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Try selecting a different date range or agent/i)
    ).toBeInTheDocument();
  });

  it('renders chart with data from API', () => {
    mockUseAgentTrends.mockReturnValue({
      data: mockTrendData,
      isLoading: false,
      error: null,
      refetch: jest.fn(),
    } as any);

    render(<ExecutionTrendChart {...defaultProps} />, { wrapper: createWrapper() });

    expect(screen.getByText('Execution Trends')).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /hourly/i })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /daily/i })).toBeInTheDocument();
    expect(screen.getByTestId('responsive-container')).toBeInTheDocument();
  });

  it('toggles granularity when tab clicked', async () => {
    const user = userEvent.setup();
    mockUseAgentTrends.mockReturnValue({
      data: mockTrendData,
      isLoading: false,
      error: null,
      refetch: jest.fn(),
    } as any);

    render(<ExecutionTrendChart {...defaultProps} />, { wrapper: createWrapper() });

    const dailyTab = screen.getByRole('tab', { name: /daily/i });
    await user.click(dailyTab);

    // After clicking daily, useAgentTrends should be called with granularity='daily'
    // (Tested indirectly - hook is mocked, but component state changes)
    // Headless UI uses aria-selected for selected tabs
    expect(dailyTab).toHaveAttribute('aria-selected', 'true');
  });

  // TODO: Test legend click to hide/show series (requires more complex Recharts mocking)
  // it('clicking legend hides/shows series', async () => { ... });

  // TODO: Test that cannot hide both series
  // it('cannot hide both series', async () => { ... });
});
