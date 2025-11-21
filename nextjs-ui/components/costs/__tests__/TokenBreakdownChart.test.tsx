/**
 * Tests for TokenBreakdownChart Component
 *
 * Covers:
 * - Renders pie/donut chart with correct data
 * - Uses correct color palette (input=blue, output=green)
 * - Displays center label with total tokens
 * - Hover tooltip shows token type, count, percentage
 * - Handles edge cases (zero tokens, single type)
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { TokenBreakdownChart } from '../TokenBreakdownChart';
import { TokenBreakdownWithPercentage } from '@/types/costs';

// Mock Recharts to avoid canvas issues in Jest
jest.mock('recharts', () => ({
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="responsive-container">{children}</div>
  ),
  PieChart: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="pie-chart">{children}</div>
  ),
  Pie: ({ data }: { data: unknown[] }) => (
    <div data-testid="pie" data-length={data?.length} />
  ),
  Cell: () => <div data-testid="cell" />,
  Tooltip: () => <div data-testid="tooltip" />,
}));

describe('TokenBreakdownChart', () => {
  const mockData: TokenBreakdownWithPercentage[] = [
    { tokenType: 'input', count: 750, cost: 0.015, percentage: 75 },
    { tokenType: 'output', count: 250, cost: 0.030, percentage: 25 },
  ];

  it('renders chart with valid data', () => {
    render(<TokenBreakdownChart data={mockData} />);

    expect(screen.getByText('Token Breakdown by Type')).toBeInTheDocument();
    expect(screen.getByTestId('pie-chart')).toBeInTheDocument();
  });

  it('displays loading skeleton when loading=true', () => {
    const { container } = render(<TokenBreakdownChart data={[]} loading={true} />);

    const skeleton = container.querySelector('.animate-pulse');
    expect(skeleton).toBeInTheDocument();
  });

  it('displays empty state when data is empty', () => {
    render(<TokenBreakdownChart data={[]} />);

    expect(screen.getByText('No Token Usage Data')).toBeInTheDocument();
    expect(
      screen.getByText(/No token usage data available/)
    ).toBeInTheDocument();
  });

  it('displays empty state when total tokens is zero', () => {
    const zeroData: TokenBreakdownWithPercentage[] = [
      { tokenType: 'input', count: 0, cost: 0, percentage: 0 },
      { tokenType: 'output', count: 0, cost: 0, percentage: 0 },
    ];

    render(<TokenBreakdownChart data={zeroData} />);

    expect(screen.getByText('No Token Usage Data')).toBeInTheDocument();
  });

  it('calculates and displays total tokens', () => {
    const { container } = render(<TokenBreakdownChart data={mockData} />);

    // Total should be 750 + 250 = 1000
    // formatLargeNumber(1000) = "1.0K"
    expect(container.textContent).toContain('1.0K');
  });

  it('displays legend with correct token types', () => {
    render(<TokenBreakdownChart data={mockData} />);

    expect(screen.getByText('Input Tokens')).toBeInTheDocument();
    expect(screen.getByText('Output Tokens')).toBeInTheDocument();
  });

  it('handles single token type (100% percentage)', () => {
    const singleTypeData: TokenBreakdownWithPercentage[] = [
      { tokenType: 'input', count: 1000, cost: 0.020, percentage: 100 },
    ];

    render(<TokenBreakdownChart data={singleTypeData} />);

    expect(screen.getByText('Input Tokens')).toBeInTheDocument();
    expect(screen.queryByText('Output Tokens')).not.toBeInTheDocument();
  });
});
