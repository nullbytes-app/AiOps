/**
 * Unit tests for MetricCard component
 * Coverage target: ≥90%
 */

import { render, screen } from '@testing-library/react';
import { MetricCard } from '@/components/agent-performance/MetricCard';
import { Activity } from 'lucide-react';

describe('MetricCard', () => {
  it('renders title, value, and subtitle correctly', () => {
    render(
      <MetricCard
        title="Total Executions"
        value="1.5K"
        subtitle="Last 7 days"
      />
    );

    expect(screen.getByText('Total Executions')).toBeInTheDocument();
    expect(screen.getByText('1.5K')).toBeInTheDocument();
    expect(screen.getByText('Last 7 days')).toBeInTheDocument();
  });

  it('applies custom color class', () => {
    render(
      <MetricCard
        title="Success Rate"
        value="99.5%"
        colorClass="text-green-600"
      />
    );

    const valueElement = screen.getByText('99.5%');
    expect(valueElement.className).toContain('text-green-600');
  });

  it('shows trend indicator when provided', () => {
    render(
      <MetricCard
        title="Execution Time"
        value="2.34s"
        trend={{ value: 5.2, direction: 'up' }}
      />
    );

    expect(screen.getByText('↑')).toBeInTheDocument();
    expect(screen.getByText('5.2% vs previous period')).toBeInTheDocument();
  });

  it('shows down trend with correct color', () => {
    render(
      <MetricCard
        title="Error Rate"
        value="2.1%"
        trend={{ value: -3.5, direction: 'down' }}
      />
    );

    expect(screen.getByText('↓')).toBeInTheDocument();
    expect(screen.getByText('3.5% vs previous period')).toBeInTheDocument();
  });

  it('renders icon when provided', () => {
    render(
      <MetricCard
        title="Total Executions"
        value="1000"
        icon={<Activity className="h-4 w-4" data-testid="activity-icon" />}
      />
    );

    expect(screen.getByTestId('activity-icon')).toBeInTheDocument();
  });

  it('handles missing optional props gracefully', () => {
    render(
      <MetricCard
        title="Simple Metric"
        value="42"
      />
    );

    expect(screen.getByText('Simple Metric')).toBeInTheDocument();
    expect(screen.getByText('42')).toBeInTheDocument();
    expect(screen.queryByRole('img')).not.toBeInTheDocument(); // No icon
  });

  it('shows loading skeleton when isLoading is true', () => {
    render(
      <MetricCard
        title="Total Executions"
        value="1000"
        isLoading={true}
      />
    );

    // Loading skeleton doesn't show title or value, just placeholder divs
    expect(screen.getByRole('status', { name: 'Loading metric' })).toBeInTheDocument();
    expect(screen.queryByText('Total Executions')).not.toBeInTheDocument();
    expect(screen.queryByText('1000')).not.toBeInTheDocument();
  });

  it('uses tabular-nums class for numeric values', () => {
    render(
      <MetricCard
        title="Execution Time"
        value="2.34s"
      />
    );

    const valueElement = screen.getByText('2.34s');
    expect(valueElement).toHaveClass('tabular-nums');
  });
});
