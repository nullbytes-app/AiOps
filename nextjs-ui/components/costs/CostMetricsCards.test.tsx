/**
 * Unit tests for CostMetricsCards component
 * Tests rendering, loading states, empty states, and metric display
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import { CostMetricsCards } from './CostMetricsCards';
import { CostSummaryDTO } from '@/types/costs';

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

describe('CostMetricsCards', () => {
  test('renders all 5 metric cards with data', () => {
    render(<CostMetricsCards data={mockCostSummary} />);

    // Check for all 5 metric labels
    expect(screen.getByText("Today's Spend")).toBeInTheDocument();
    expect(screen.getByText('This Week')).toBeInTheDocument();
    expect(screen.getByText('This Month')).toBeInTheDocument();
    expect(screen.getByText('Top Tenant')).toBeInTheDocument();
    expect(screen.getByText('Top Agent')).toBeInTheDocument();
  });

  test('formats currency values correctly', () => {
    render(<CostMetricsCards data={mockCostSummary} />);

    // Today's spend: $1,234.56
    expect(screen.getByText('$1,234.56')).toBeInTheDocument();

    // Week spend: $8,765.43
    expect(screen.getByText('$8,765.43')).toBeInTheDocument();

    // Month spend: $35,000.12
    expect(screen.getByText('$35,000.12')).toBeInTheDocument();

    // Top tenant: $15,000.00
    expect(screen.getByText('$15,000.00')).toBeInTheDocument();

    // Top agent: $5,000.00
    expect(screen.getByText('$5,000.00')).toBeInTheDocument();
  });

  test('displays tenant and agent names in subtitles', () => {
    render(<CostMetricsCards data={mockCostSummary} />);

    // Top tenant name
    expect(screen.getByText('Acme Corp')).toBeInTheDocument();

    // Top agent name with execution count
    expect(screen.getByText(/Ticket Enhancer/)).toBeInTheDocument();
    expect(screen.getByText(/1.5K runs/)).toBeInTheDocument();
  });

  test('displays loading skeleton when loading=true', () => {
    render(<CostMetricsCards loading={true} />);

    // Should show 5 loading cards with role="status"
    const loadingCards = screen.getAllByRole('status', { name: /loading/i });
    expect(loadingCards).toHaveLength(5);

    // Should NOT show actual data
    expect(screen.queryByText("Today's Spend")).not.toBeInTheDocument();
  });

  test('displays empty state when data is undefined', () => {
    render(<CostMetricsCards data={undefined} />);

    // Empty state heading
    expect(screen.getByText('No Cost Data Yet')).toBeInTheDocument();

    // Empty state message
    expect(
      screen.getByText(/Once agents start processing tickets/)
    ).toBeInTheDocument();

    // Should NOT show metric cards
    expect(screen.queryByText("Today's Spend")).not.toBeInTheDocument();
  });

  test('handles null top_tenant gracefully', () => {
    const dataWithoutTenant: CostSummaryDTO = {
      ...mockCostSummary,
      top_tenant: null,
    };

    render(<CostMetricsCards data={dataWithoutTenant} />);

    // Should show "No data" for value
    expect(screen.getByText('No data')).toBeInTheDocument();

    // Should show "N/A" for subtitle
    expect(screen.getByText('N/A')).toBeInTheDocument();
  });

  test('handles null top_agent gracefully', () => {
    const dataWithoutAgent: CostSummaryDTO = {
      ...mockCostSummary,
      top_agent: null,
    };

    render(<CostMetricsCards data={dataWithoutAgent} />);

    // Should show "No data" for value (appears twice: tenant + agent)
    const noDataElements = screen.getAllByText('No data');
    expect(noDataElements.length).toBeGreaterThanOrEqual(1);
  });

  test('displays subtitles for week and month', () => {
    render(<CostMetricsCards data={mockCostSummary} />);

    expect(screen.getByText('7-day rolling')).toBeInTheDocument();
    expect(screen.getByText('Month-to-date')).toBeInTheDocument();
  });

  test('applies responsive grid classes', () => {
    const { container } = render(<CostMetricsCards data={mockCostSummary} />);

    const gridDiv = container.querySelector('.grid');
    expect(gridDiv).toHaveClass('grid-cols-1');
    expect(gridDiv).toHaveClass('md:grid-cols-2');
    expect(gridDiv).toHaveClass('lg:grid-cols-4');
  });

  test('renders with custom className', () => {
    const { container } = render(
      <CostMetricsCards data={mockCostSummary} className="custom-class" />
    );

    const gridDiv = container.querySelector('.custom-class');
    expect(gridDiv).toBeInTheDocument();
  });

  test('handles zero values correctly', () => {
    const zeroData: CostSummaryDTO = {
      today_spend: 0,
      week_spend: 0,
      month_spend: 0,
      total_spend_30d: 0,
      top_tenant: null,
      top_agent: null,
    };

    render(<CostMetricsCards data={zeroData} />);

    // Should display $0.00 for all metrics
    const zeroValues = screen.getAllByText('$0.00');
    expect(zeroValues.length).toBeGreaterThanOrEqual(3); // Today, week, month
  });
});
