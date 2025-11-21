/**
 * Tests for TokenBreakdownTable Component
 *
 * Covers:
 * - Renders table with all columns (token type, count, cost, percentage)
 * - Sortable columns (click header toggles ascending/descending)
 * - Number formatting (1.2M notation, currency)
 * - Loading skeleton for table rows
 */

import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import { TokenBreakdownTable } from '../TokenBreakdownTable';
import { TokenBreakdownWithPercentage } from '@/types/costs';

describe('TokenBreakdownTable', () => {
  const mockData: TokenBreakdownWithPercentage[] = [
    { tokenType: 'input', count: 750000, cost: 15.50, percentage: 75 },
    { tokenType: 'output', count: 250000, cost: 30.25, percentage: 25 },
  ];

  it('renders table with all columns', () => {
    render(<TokenBreakdownTable data={mockData} />);

    expect(screen.getByText('Token Type')).toBeInTheDocument();
    expect(screen.getByText('Count')).toBeInTheDocument();
    expect(screen.getByText('Cost')).toBeInTheDocument();
    expect(screen.getByText('Percentage')).toBeInTheDocument();
  });

  it('displays data with correct formatting', () => {
    render(<TokenBreakdownTable data={mockData} />);

    // Token types
    expect(screen.getByText('input')).toBeInTheDocument();
    expect(screen.getByText('output')).toBeInTheDocument();

    // Count with 1.2M notation
    expect(screen.getByText('750.0K')).toBeInTheDocument();
    expect(screen.getByText('250.0K')).toBeInTheDocument();

    // Cost with currency format
    expect(screen.getByText('$15.50')).toBeInTheDocument();
    expect(screen.getByText('$30.25')).toBeInTheDocument();

    // Percentage
    expect(screen.getByText('75.0%')).toBeInTheDocument();
    expect(screen.getByText('25.0%')).toBeInTheDocument();
  });

  it('displays loading skeleton when loading=true', () => {
    const { container } = render(<TokenBreakdownTable data={[]} loading={true} />);

    const skeletons = container.querySelectorAll('.animate-pulse');
    expect(skeletons.length).toBeGreaterThan(0);
  });

  it('sorts by count in descending order by default', () => {
    render(<TokenBreakdownTable data={mockData} />);

    const rows = screen.getAllByRole('row');
    // First row is header, second row should be input (750K > 250K)
    expect(rows[1]).toHaveTextContent('input');
    expect(rows[2]).toHaveTextContent('output');
  });

  it('toggles sort direction on column header click', () => {
    render(<TokenBreakdownTable data={mockData} />);

    const countHeader = screen.getByText('Count').closest('th');
    expect(countHeader).not.toBeNull();

    // Click once: ascending (250K first)
    fireEvent.click(countHeader!);

    let rows = screen.getAllByRole('row');
    expect(rows[1]).toHaveTextContent('output'); // 250K
    expect(rows[2]).toHaveTextContent('input'); // 750K

    // Click again: reset to default (descending)
    fireEvent.click(countHeader!);

    rows = screen.getAllByRole('row');
    expect(rows[1]).toHaveTextContent('input'); // 750K
    expect(rows[2]).toHaveTextContent('output'); // 250K
  });

  it('sorts by cost column', () => {
    render(<TokenBreakdownTable data={mockData} />);

    const costHeader = screen.getByText('Cost').closest('th');
    expect(costHeader).not.toBeNull();

    // Click: descending (highest cost first)
    fireEvent.click(costHeader!);

    const rows = screen.getAllByRole('row');
    expect(rows[1]).toHaveTextContent('output'); // $30.25
    expect(rows[2]).toHaveTextContent('input'); // $15.50
  });

  it('displays empty state when no data', () => {
    render(<TokenBreakdownTable data={[]} />);

    expect(
      screen.getByText(/No token data available/)
    ).toBeInTheDocument();
  });
});
