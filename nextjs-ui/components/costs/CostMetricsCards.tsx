/**
 * CostMetricsCards Component
 *
 * Displays a grid of cost metric cards for the LLM Cost Dashboard.
 * Includes loading states, empty states, and responsive layout.
 *
 * Used by: /dashboard/llm-costs/page.tsx
 */

'use client';

import React from 'react';
import { MetricCard } from './MetricCard';
import { CostSummaryDTO } from '@/types/costs';
import { formatCurrency, formatLargeNumber, formatPercentageChange } from '@/lib/formatters';
import { cn } from '@/lib/utils';

export interface CostMetricsCardsProps {
  /** Cost summary data from API */
  data?: CostSummaryDTO;
  /** Loading state - shows skeleton cards */
  loading?: boolean;
  /** Optional CSS classes */
  className?: string;
}

/**
 * Empty State Component
 * Shown when no cost data is available
 */
function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center py-24">
      <div className="text-6xl mb-4" role="img" aria-label="Empty">
        📊
      </div>
      <h2 className="text-2xl font-bold text-foreground mb-2">
        No Cost Data Yet
      </h2>
      <p className="text-muted-foreground max-w-md text-center">
        Once agents start processing tickets, cost metrics will appear here.
        Check back after your first agent execution.
      </p>
    </div>
  );
}

/**
 * CostMetricsCards - Grid of cost metric cards
 *
 * Displays 5 metric cards in responsive grid:
 * - Today's Spend
 * - This Week's Spend
 * - This Month's Spend
 * - Top Spending Tenant
 * - Top Spending Agent
 *
 * Features:
 * - Responsive grid: 4 cols desktop, 2 cols tablet, 1 col mobile (AC#1)
 * - Loading skeleton states (AC#1)
 * - Empty state when no data
 * - Currency formatting with 2 decimals (AC#2)
 * - Large number formatting (1.2K, 1.2M) (AC#2)
 * - Percentage change indicators (AC#2)
 *
 * @example
 * ```tsx
 * <CostMetricsCards
 *   data={costSummary}
 *   loading={isLoading}
 * />
 * ```
 */
export function CostMetricsCards({
  data,
  loading = false,
  className,
}: CostMetricsCardsProps) {
  // Show loading skeleton
  if (loading) {
    return (
      <div
        className={cn(
          'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6',
          className
        )}
      >
        {[1, 2, 3, 4, 5].map((i) => (
          <MetricCard
            key={i}
            label="Loading..."
            value="..."
            loading={true}
          />
        ))}
      </div>
    );
  }

  // Show empty state if no data
  if (!data) {
    return <EmptyState />;
  }

  // Calculate percentage change for "Today vs Yesterday"
  // Note: Backend doesn't provide yesterday's data yet, so we'll show N/A
  // TODO: Add todayVsYesterday field to CostSummaryDTO in backend
  const todayChange = formatPercentageChange(data.today_spend, 0);

  return (
    <div
      className={cn(
        'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6',
        className
      )}
    >
      {/* Today's Spend */}
      <MetricCard
        label="Today's Spend"
        value={formatCurrency(data.today_spend)}
        trendPercent={todayChange.value !== 0 ? todayChange.value : undefined}
        trendIcon={todayChange.icon}
      />

      {/* This Week's Spend (7-day rolling) */}
      <MetricCard
        label="This Week"
        value={formatCurrency(data.week_spend)}
        subtitle="7-day rolling"
      />

      {/* This Month's Spend (MTD) */}
      <MetricCard
        label="This Month"
        value={formatCurrency(data.month_spend)}
        subtitle="Month-to-date"
      />

      {/* Top Spending Tenant */}
      <MetricCard
        label="Top Tenant"
        value={
          data.top_tenant
            ? formatCurrency(data.top_tenant.total_spend)
            : 'No data'
        }
        subtitle={data.top_tenant?.tenant_name || 'N/A'}
      />

      {/* Top Spending Agent */}
      <MetricCard
        label="Top Agent"
        value={
          data.top_agent
            ? formatCurrency(data.top_agent.total_cost)
            : 'No data'
        }
        subtitle={
          data.top_agent
            ? `${data.top_agent.agent_name} • ${formatLargeNumber(
                data.top_agent.execution_count
              )} runs`
            : 'N/A'
        }
      />
    </div>
  );
}
