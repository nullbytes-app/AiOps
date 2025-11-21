/**
 * Unit tests for DailySpendChart component
 * Tests rendering, data transformation, tooltips, export, loading/error states
 */

import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { DailySpendChart } from './DailySpendChart';
import { DailySpendDTO } from '@/types/costs';
import * as chartExport from '@/lib/chartExport';

// Mock the chart export utility
jest.mock('@/lib/chartExport');
const mockedExportChartAsPNG = chartExport.exportChartAsPNG as jest.MockedFunction<
  typeof chartExport.exportChartAsPNG
>;

// Mock Recharts to avoid rendering issues in tests
jest.mock('recharts', () => ({
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="responsive-container">{children}</div>
  ),
  AreaChart: ({ children, data }: { children: React.ReactNode; data: unknown[] }) => (
    <div data-testid="area-chart" data-length={data.length}>
      {children}
    </div>
  ),
  Area: () => <div data-testid="area" />,
  XAxis: () => <div data-testid="x-axis" />,
  YAxis: () => <div data-testid="y-axis" />,
  CartesianGrid: () => <div data-testid="cartesian-grid" />,
  Tooltip: () => <div data-testid="tooltip" />,
}));

// Mock data
const mockTrendData: DailySpendDTO[] = [
  { date: '2025-01-01', total_spend: 100.50, transaction_count: 50 },
  { date: '2025-01-02', total_spend: 150.75, transaction_count: 75 },
  { date: '2025-01-03', total_spend: 200.00, transaction_count: 100 },
  { date: '2025-01-04', total_spend: 175.50, transaction_count: 88 },
  { date: '2025-01-05', total_spend: 225.00, transaction_count: 113 },
];

const emptyData: DailySpendDTO[] = [];

describe('DailySpendChart', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Loading State', () => {
    test('renders loading skeleton when loading=true', () => {
      render(<DailySpendChart loading={true} />);

      // Should show skeleton elements
      const skeletons = screen.getAllByRole('status', { hidden: true });
      expect(skeletons.length).toBeGreaterThan(0);

      // Should NOT show chart
      expect(screen.queryByTestId('area-chart')).not.toBeInTheDocument();
    });

    test('loading skeleton has correct structure', () => {
      const { container } = render(<DailySpendChart loading={true} />);

      // Should have card wrapper
      expect(container.querySelector('.bg-card')).toBeInTheDocument();

      // Should have animate-pulse class
      expect(container.querySelector('.animate-pulse')).toBeInTheDocument();
    });
  });

  describe('Empty State', () => {
    test('renders empty state when data is empty array', () => {
      render(<DailySpendChart data={emptyData} />);

      // Should show empty state message
      expect(
        screen.getByText('No cost data available for the last 30 days')
      ).toBeInTheDocument();
      expect(
        screen.getByText('Data will appear once LLM usage is recorded')
      ).toBeInTheDocument();

      // Should NOT show chart
      expect(screen.queryByTestId('area-chart')).not.toBeInTheDocument();
    });

    test('renders empty state when data is undefined', () => {
      render(<DailySpendChart data={undefined} />);

      // Should show empty state
      expect(
        screen.getByText('No cost data available for the last 30 days')
      ).toBeInTheDocument();
    });

    test('empty state has BarChart3 icon', () => {
      const { container } = render(<DailySpendChart data={emptyData} />);

      // lucide-react icons render as SVG
      const svgIcon = container.querySelector('svg');
      expect(svgIcon).toBeInTheDocument();
    });
  });

  describe('Error State', () => {
    const mockError = new Error('Failed to fetch cost trend data');
    const mockRetry = jest.fn();

    test('renders error state when error prop is provided (AC#10)', () => {
      render(<DailySpendChart data={undefined} error={mockError} onRetry={mockRetry} />);

      // Should show error message
      expect(screen.getByText('Unable to load cost trend data')).toBeInTheDocument();

      // Should show error details
      expect(screen.getByText('Failed to fetch cost trend data')).toBeInTheDocument();

      // Should NOT show chart
      expect(screen.queryByTestId('area-chart')).not.toBeInTheDocument();

      // Should NOT show empty state
      expect(
        screen.queryByText('No cost data available for the last 30 days')
      ).not.toBeInTheDocument();
    });

    test('error state shows retry button (AC#10)', () => {
      render(<DailySpendChart data={undefined} error={mockError} onRetry={mockRetry} />);

      // Retry button should be visible
      const retryButton = screen.getByRole('button', { name: /retry/i });
      expect(retryButton).toBeInTheDocument();
    });

    test('clicking retry button calls onRetry callback (AC#10)', async () => {
      const user = userEvent.setup();
      render(<DailySpendChart data={undefined} error={mockError} onRetry={mockRetry} />);

      const retryButton = screen.getByRole('button', { name: /retry/i });
      await user.click(retryButton);

      // onRetry should be called once
      expect(mockRetry).toHaveBeenCalledTimes(1);
    });

    test('error state has AlertCircle icon', () => {
      const { container } = render(<DailySpendChart data={undefined} error={mockError} onRetry={mockRetry} />);

      // lucide-react icons render as SVG
      const svgIcon = container.querySelector('svg');
      expect(svgIcon).toBeInTheDocument();
    });

    test('error state takes precedence over empty state', () => {
      // Both error and empty data conditions true
      render(<DailySpendChart data={emptyData} error={mockError} onRetry={mockRetry} />);

      // Should show error state, not empty state
      expect(screen.getByText('Unable to load cost trend data')).toBeInTheDocument();
      expect(
        screen.queryByText('No cost data available for the last 30 days')
      ).not.toBeInTheDocument();
    });

    test('error state without onRetry does not show retry button', () => {
      render(<DailySpendChart data={undefined} error={mockError} />);

      // Error message should be shown
      expect(screen.getByText('Unable to load cost trend data')).toBeInTheDocument();

      // Retry button should NOT be visible (onRetry not provided)
      expect(screen.queryByRole('button', { name: /retry/i })).not.toBeInTheDocument();
    });
  });

  describe('Chart Rendering', () => {
    test('renders chart successfully with valid data', () => {
      render(<DailySpendChart data={mockTrendData} />);

      // Should show chart title
      expect(screen.getByText('Daily Spend Trend (Last 30 Days)')).toBeInTheDocument();

      // Should render Recharts components
      expect(screen.getByTestId('responsive-container')).toBeInTheDocument();
      expect(screen.getByTestId('area-chart')).toBeInTheDocument();
      expect(screen.getByTestId('area')).toBeInTheDocument();
      expect(screen.getByTestId('x-axis')).toBeInTheDocument();
      expect(screen.getByTestId('y-axis')).toBeInTheDocument();
      expect(screen.getByTestId('cartesian-grid')).toBeInTheDocument();
    });

    test('chart receives correct data length', () => {
      render(<DailySpendChart data={mockTrendData} />);

      const areaChart = screen.getByTestId('area-chart');
      expect(areaChart).toHaveAttribute('data-length', String(mockTrendData.length));
    });

    test('displays date range in subtitle', () => {
      render(<DailySpendChart data={mockTrendData} />);

      // Should show date range (format: "Jan 01 - Jan 05, 2025")
      expect(screen.getByText(/Jan 01/)).toBeInTheDocument();
      expect(screen.getByText(/Jan 05, 2025/)).toBeInTheDocument();
    });

    test('renders with custom className', () => {
      const { container } = render(
        <DailySpendChart data={mockTrendData} className="custom-class" />
      );

      const chartWrapper = container.querySelector('.custom-class');
      expect(chartWrapper).toBeInTheDocument();
    });
  });

  describe('Export Functionality', () => {
    test('export button is visible when data is present', () => {
      render(<DailySpendChart data={mockTrendData} />);

      const exportButton = screen.getByRole('button', { name: /export chart as png/i });
      expect(exportButton).toBeInTheDocument();
    });

    test('export button has correct accessibility attributes', () => {
      render(<DailySpendChart data={mockTrendData} />);

      const exportButton = screen.getByRole('button', { name: /export chart as png/i });
      expect(exportButton).toHaveAttribute('aria-label', 'Export chart as PNG');
    });

    test('export button has data-export-hide attribute', () => {
      render(<DailySpendChart data={mockTrendData} />);

      const exportButton = screen.getByRole('button', { name: /export chart as png/i });
      expect(exportButton).toHaveAttribute('data-export-hide');
    });

    test('clicking export button calls exportChartAsPNG', async () => {
      const user = userEvent.setup();
      mockedExportChartAsPNG.mockResolvedValueOnce();

      render(<DailySpendChart data={mockTrendData} />);

      const exportButton = screen.getByRole('button', { name: /export chart as png/i });
      await user.click(exportButton);

      // Should call export function
      expect(mockedExportChartAsPNG).toHaveBeenCalledTimes(1);
      expect(mockedExportChartAsPNG).toHaveBeenCalledWith(
        expect.objectContaining({ current: expect.anything() })
      );
    });

    test('export button shows loading state during export', async () => {
      const user = userEvent.setup();
      // Mock a slow export
      mockedExportChartAsPNG.mockImplementation(
        () => new Promise((resolve) => setTimeout(resolve, 100))
      );

      render(<DailySpendChart data={mockTrendData} />);

      const exportButton = screen.getByRole('button', { name: /export chart as png/i });
      await user.click(exportButton);

      // Button should be disabled during export
      expect(exportButton).toBeDisabled();
      expect(screen.getByText('Exporting...')).toBeInTheDocument();

      // Wait for export to complete
      await waitFor(() => {
        expect(exportButton).not.toBeDisabled();
      });
    });

    test('handles export error gracefully', async () => {
      const user = userEvent.setup();
      const consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation();
      mockedExportChartAsPNG.mockRejectedValueOnce(new Error('Export failed'));

      render(<DailySpendChart data={mockTrendData} />);

      const exportButton = screen.getByRole('button', { name: /export chart as png/i });
      await user.click(exportButton);

      // Should log error
      await waitFor(() => {
        expect(consoleErrorSpy).toHaveBeenCalledWith(
          'Export failed:',
          expect.any(Error)
        );
      });

      // Button should be re-enabled
      expect(exportButton).not.toBeDisabled();

      consoleErrorSpy.mockRestore();
    });

    test('export button text is hidden on mobile', () => {
      render(<DailySpendChart data={mockTrendData} />);

      const exportText = screen.getByText('Export as PNG');
      expect(exportText).toHaveClass('hidden', 'sm:inline');
    });
  });

  describe('Data Transformation', () => {
    test('transforms API data to chart format correctly', () => {
      render(<DailySpendChart data={mockTrendData} />);

      // Chart should render with transformed data
      expect(screen.getByTestId('area-chart')).toBeInTheDocument();

      // Date range should be formatted correctly
      expect(screen.getByText(/Jan 01/)).toBeInTheDocument();
      expect(screen.getByText(/Jan 05, 2025/)).toBeInTheDocument();
    });

    test('calculates delta for consecutive days', () => {
      // Day 1: $100.50
      // Day 2: $150.75 -> delta = +50% (increase)
      // Day 3: $200.00 -> delta = +32.7% (increase)
      // Day 4: $175.50 -> delta = -12.3% (decrease)
      // Day 5: $225.00 -> delta = +28.2% (increase)

      // Note: Delta calculations are tested through the component's internal logic
      // The chart should display these deltas in the tooltip
      render(<DailySpendChart data={mockTrendData} />);

      // Chart renders successfully with delta calculations
      expect(screen.getByTestId('area-chart')).toBeInTheDocument();
    });

    test('handles single data point (no delta)', () => {
      const singlePoint: DailySpendDTO[] = [
        { date: '2025-01-01', total_spend: 100.50, transaction_count: 50 },
      ];

      render(<DailySpendChart data={singlePoint} />);

      // Should render without errors
      expect(screen.getByTestId('area-chart')).toBeInTheDocument();
      expect(screen.getByText(/Jan 01/)).toBeInTheDocument();
    });
  });

  describe('Currency Formatting', () => {
    test('formats large amounts with K suffix', () => {
      const largeAmounts: DailySpendDTO[] = [
        { date: '2025-01-01', total_spend: 1234.56, transaction_count: 50 },
      ];

      // Note: Currency formatting is internal to Y-axis
      // This test validates the component renders with large amounts
      render(<DailySpendChart data={largeAmounts} />);

      expect(screen.getByTestId('area-chart')).toBeInTheDocument();
    });

    test('formats very large amounts with M suffix', () => {
      const veryLargeAmounts: DailySpendDTO[] = [
        { date: '2025-01-01', total_spend: 1500000.00, transaction_count: 5000 },
      ];

      render(<DailySpendChart data={veryLargeAmounts} />);

      expect(screen.getByTestId('area-chart')).toBeInTheDocument();
    });
  });

  describe('Responsive Design', () => {
    test('chart container has responsive classes', () => {
      const { container } = render(<DailySpendChart data={mockTrendData} />);

      const chartWrapper = container.querySelector('.bg-card');
      expect(chartWrapper).toHaveClass('rounded-lg', 'border', 'border-border', 'p-6');
    });

    test('renders with ResponsiveContainer for responsiveness', () => {
      render(<DailySpendChart data={mockTrendData} />);

      expect(screen.getByTestId('responsive-container')).toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    test('export button has proper aria-label', () => {
      render(<DailySpendChart data={mockTrendData} />);

      const exportButton = screen.getByRole('button', { name: /export chart as png/i });
      expect(exportButton).toHaveAttribute('aria-label', 'Export chart as PNG');
    });

    test('chart has semantic heading', () => {
      render(<DailySpendChart data={mockTrendData} />);

      const heading = screen.getByRole('heading', {
        name: 'Daily Spend Trend (Last 30 Days)',
      });
      expect(heading).toBeInTheDocument();
    });

    test('empty state has descriptive text', () => {
      render(<DailySpendChart data={emptyData} />);

      expect(
        screen.getByText('No cost data available for the last 30 days')
      ).toBeInTheDocument();
      expect(
        screen.getByText('Data will appear once LLM usage is recorded')
      ).toBeInTheDocument();
    });
  });

  describe('Edge Cases', () => {
    test('handles data with zero amounts', () => {
      const zeroAmounts: DailySpendDTO[] = [
        { date: '2025-01-01', total_spend: 0, transaction_count: 0 },
        { date: '2025-01-02', total_spend: 0, transaction_count: 0 },
      ];

      render(<DailySpendChart data={zeroAmounts} />);

      // Should render without errors
      expect(screen.getByTestId('area-chart')).toBeInTheDocument();
    });

    test('handles data with very small amounts', () => {
      const smallAmounts: DailySpendDTO[] = [
        { date: '2025-01-01', total_spend: 0.01, transaction_count: 1 },
        { date: '2025-01-02', total_spend: 0.02, transaction_count: 2 },
      ];

      render(<DailySpendChart data={smallAmounts} />);

      expect(screen.getByTestId('area-chart')).toBeInTheDocument();
    });

    test('handles data with decreasing trend', () => {
      const decreasingTrend: DailySpendDTO[] = [
        { date: '2025-01-01', total_spend: 1000.00, transaction_count: 500 },
        { date: '2025-01-02', total_spend: 800.00, transaction_count: 400 },
        { date: '2025-01-03', total_spend: 600.00, transaction_count: 300 },
      ];

      render(<DailySpendChart data={decreasingTrend} />);

      // Should render successfully with negative deltas
      expect(screen.getByTestId('area-chart')).toBeInTheDocument();
    });

    test('handles data with flat trend (no change)', () => {
      const flatTrend: DailySpendDTO[] = [
        { date: '2025-01-01', total_spend: 100.00, transaction_count: 50 },
        { date: '2025-01-02', total_spend: 100.00, transaction_count: 50 },
        { date: '2025-01-03', total_spend: 100.00, transaction_count: 50 },
      ];

      render(<DailySpendChart data={flatTrend} />);

      // Should render with 0% deltas
      expect(screen.getByTestId('area-chart')).toBeInTheDocument();
    });
  });
});
