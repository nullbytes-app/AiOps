/**
 * TokenBreakdownTable Component
 *
 * Data table with sorting for token usage breakdown by type.
 * Shows token type, count, cost, and percentage with sortable columns.
 *
 * AC#2: Data table below chart shows token type | count | cost | percentage
 * with sortable columns and formatted numbers (1.2M notation)
 */

'use client';

import React from 'react';
import { TokenBreakdownWithPercentage } from '@/types/costs';
import { formatLargeNumber, formatCurrency, formatPercentage } from '@/lib/formatters';
import { ArrowUp, ArrowDown, ArrowUpDown } from 'lucide-react';

export interface TokenBreakdownTableProps {
  /** Token breakdown data with percentages */
  data: TokenBreakdownWithPercentage[];
  /** Show loading skeleton */
  loading?: boolean;
  /** Custom CSS classes */
  className?: string;
}

type SortColumn = 'tokenType' | 'count' | 'cost' | 'percentage';
type SortDirection = 'asc' | 'desc' | null;

/**
 * Loading Skeleton for Table Rows
 */
function LoadingSkeleton() {
  return (
    <>
      {[1, 2].map((i) => (
        <tr key={i} className="animate-pulse">
          <td className="px-4 py-3"><div className="h-4 bg-muted/50 rounded w-24" /></td>
          <td className="px-4 py-3"><div className="h-4 bg-muted/50 rounded w-20" /></td>
          <td className="px-4 py-3"><div className="h-4 bg-muted/50 rounded w-16" /></td>
          <td className="px-4 py-3"><div className="h-4 bg-muted/50 rounded w-16" /></td>
        </tr>
      ))}
    </>
  );
}

/**
 * Sort Icon Component
 * Shows current sort direction with visual indicator
 */
function SortIcon({ direction }: { direction: SortDirection }) {
  if (direction === 'asc') {
    return <ArrowUp className="h-3 w-3" />;
  }
  if (direction === 'desc') {
    return <ArrowDown className="h-3 w-3" />;
  }
  return <ArrowUpDown className="h-3 w-3 opacity-40" />;
}

/**
 * TokenBreakdownTable Component
 *
 * Features:
 * - Sortable columns (click header to toggle ascending/descending) (AC#2)
 * - Formatted numbers: 1.2M notation for counts (AC#2)
 * - Currency formatting: $1,234.56 for costs (AC#2)
 * - Percentage formatting: 85.5% (AC#2)
 * - Loading skeleton for table rows
 * - Responsive: horizontal scroll on mobile
 *
 * @example
 * ```tsx
 * function TokenBreakdownSection() {
 *   const { data, isLoading } = useTokenBreakdown(startDate, endDate);
 *
 *   return <TokenBreakdownTable data={data || []} loading={isLoading} />;
 * }
 * ```
 */
export function TokenBreakdownTable({
  data,
  loading = false,
  className,
}: TokenBreakdownTableProps) {
  const [sortColumn, setSortColumn] = React.useState<SortColumn>('count');
  const [sortDirection, setSortDirection] = React.useState<SortDirection>('desc');

  /**
   * Handle column header click for sorting
   */
  const handleSort = (column: SortColumn) => {
    if (sortColumn === column) {
      // Toggle direction: desc -> asc -> null -> desc
      if (sortDirection === 'desc') {
        setSortDirection('asc');
      } else if (sortDirection === 'asc') {
        setSortDirection(null);
        setSortColumn('count'); // Reset to default
      }
    } else {
      // New column: start with desc
      setSortColumn(column);
      setSortDirection('desc');
    }
  };

  /**
   * Sort data based on current column and direction
   */
  const sortedData = React.useMemo(() => {
    if (!sortDirection || !data) return data;

    const sorted = [...data].sort((a, b) => {
      let aValue: string | number;
      let bValue: string | number;

      switch (sortColumn) {
        case 'tokenType':
          aValue = a.tokenType;
          bValue = b.tokenType;
          break;
        case 'count':
          aValue = a.count;
          bValue = b.count;
          break;
        case 'cost':
          aValue = a.cost;
          bValue = b.cost;
          break;
        case 'percentage':
          aValue = a.percentage;
          bValue = b.percentage;
          break;
        default:
          return 0;
      }

      if (aValue < bValue) return sortDirection === 'asc' ? -1 : 1;
      if (aValue > bValue) return sortDirection === 'asc' ? 1 : -1;
      return 0;
    });

    return sorted;
  }, [data, sortColumn, sortDirection]);

  return (
    <div className={`bg-white/75 backdrop-blur-[32px] rounded-[24px] shadow-lg border border-white/20 p-6 ${className || ''}`}>
      <h3 className="text-lg font-semibold text-foreground mb-4">
        Token Breakdown Details
      </h3>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border">
              <th
                className="text-left px-4 py-3 font-semibold text-muted-foreground cursor-pointer hover:text-foreground transition-colors"
                onClick={() => handleSort('tokenType')}
              >
                <div className="flex items-center gap-1">
                  Token Type
                  <SortIcon direction={sortColumn === 'tokenType' ? sortDirection : null} />
                </div>
              </th>
              <th
                className="text-right px-4 py-3 font-semibold text-muted-foreground cursor-pointer hover:text-foreground transition-colors"
                onClick={() => handleSort('count')}
              >
                <div className="flex items-center justify-end gap-1">
                  Count
                  <SortIcon direction={sortColumn === 'count' ? sortDirection : null} />
                </div>
              </th>
              <th
                className="text-right px-4 py-3 font-semibold text-muted-foreground cursor-pointer hover:text-foreground transition-colors"
                onClick={() => handleSort('cost')}
              >
                <div className="flex items-center justify-end gap-1">
                  Cost
                  <SortIcon direction={sortColumn === 'cost' ? sortDirection : null} />
                </div>
              </th>
              <th
                className="text-right px-4 py-3 font-semibold text-muted-foreground cursor-pointer hover:text-foreground transition-colors"
                onClick={() => handleSort('percentage')}
              >
                <div className="flex items-center justify-end gap-1">
                  Percentage
                  <SortIcon direction={sortColumn === 'percentage' ? sortDirection : null} />
                </div>
              </th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <LoadingSkeleton />
            ) : sortedData && sortedData.length > 0 ? (
              sortedData.map((item, index) => (
                <tr
                  key={index}
                  className="border-b border-border last:border-0 hover:bg-muted/30 transition-colors"
                >
                  <td className="px-4 py-3 font-medium text-foreground capitalize">
                    {item.tokenType}
                  </td>
                  <td className="px-4 py-3 text-right text-foreground">
                    {formatLargeNumber(item.count)}
                  </td>
                  <td className="px-4 py-3 text-right text-foreground">
                    {formatCurrency(item.cost)}
                  </td>
                  <td className="px-4 py-3 text-right text-foreground">
                    {formatPercentage(item.percentage)}
                  </td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={4} className="px-4 py-8 text-center text-muted-foreground">
                  No token data available for the selected date range.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
