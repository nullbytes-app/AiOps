/**
 * LLM Cost Dashboard Page
 *
 * Displays real-time cost summary metrics with auto-refresh.
 * Auto-refreshes every 60 seconds following 2025 TanStack Query best practices.
 *
 * Maps to Story: nextjs-story-9-llm-cost-dashboard-overview
 * Backend API: GET /api/v1/costs/summary
 *
 * RBAC: admin (super_admin, tenant_admin) + operator roles only
 */

'use client';

import React from 'react';
import { useLLMCostSummary } from '@/hooks/useLLMCostSummary';
import { useLLMCostTrend } from '@/hooks/useLLMCostTrend';
import { useTokenBreakdown } from '@/hooks/useTokenBreakdown';
import { CostMetricsCards } from '@/components/costs/CostMetricsCards';
import { DailySpendChart } from './components/DailySpendChart';
import { DateRangeSelector } from '@/components/costs/DateRangeSelector';
import { TokenBreakdownChart } from '@/components/costs/TokenBreakdownChart';
import { TokenBreakdownTable } from '@/components/costs/TokenBreakdownTable';
import { BudgetUtilizationList } from '@/components/costs/BudgetUtilizationList';
import { Button } from '@/components/ui/Button';
import { RefreshCw, AlertCircle } from 'lucide-react';
import { useSession } from 'next-auth/react';
import { useRouter } from 'next/navigation';

/**
 * Error State Component
 * Shown when API request fails
 */
function ErrorState({ onRetry, error }: { onRetry: () => void; error: Error | null }) {
  return (
    <div className="flex flex-col items-center justify-center py-24">
      <AlertCircle className="h-16 w-16 text-destructive mb-4" />
      <h2 className="text-2xl font-bold text-foreground mb-2">
        Failed to Load Cost Data
      </h2>
      <p className="text-muted-foreground mb-2 max-w-md text-center">
        We couldn&apos;t fetch the LLM cost metrics. Please check your connection and try again.
      </p>
      {error && (
        <p className="text-xs text-muted-foreground mb-6 font-mono">
          Error: {error.message}
        </p>
      )}
      <Button onClick={onRetry} className="gap-2">
        <RefreshCw className="h-4 w-4" />
        Retry
      </Button>
    </div>
  );
}

/**
 * Loading Skeleton Component
 * Shown while initial data is loading
 */
function LoadingSkeleton() {
  return (
    <div className="space-y-6">
      {/* Header Skeleton */}
      <div className="animate-pulse">
        <div className="h-8 bg-muted/50 rounded w-64 mb-2" />
        <div className="h-4 bg-muted/50 rounded w-96" />
      </div>

      {/* Metrics Cards Skeleton */}
      <CostMetricsCards loading={true} />
    </div>
  );
}

/**
 * LLM Cost Dashboard Page
 *
 * Features:
 * - Real-time cost metrics with 60s auto-refresh (AC#1)
 * - Responsive grid layout (4/2/1 cols) (AC#1)
 * - RBAC enforcement (admin + operator only) (AC#1)
 * - Loading states (AC#1)
 * - Error handling with retry (AC#1)
 * - Currency formatting ($1,234.56) (AC#2)
 * - Large number formatting (1.2K, 1.2M) (AC#2)
 *
 * @example
 * URL: /dashboard/llm-costs
 * Role: admin or operator
 */
export default function LLMCostsPage() {
  const { data: session, status } = useSession();
  const router = useRouter();
  const { data, isLoading, isError, error, refetch } = useLLMCostSummary();
  const {
    data: trendData,
    isLoading: trendLoading,
    isError: trendIsError,
    error: trendError,
    refetch: trendRefetch,
  } = useLLMCostTrend(30);

  // RBAC: Redirect non-admin/non-operator users
  // Note: Middleware already handles auth, this is additional client-side check
  React.useEffect(() => {
    if (status === 'authenticated' && session?.user) {
      // Check if user has admin or operator role
      // Role is fetched on-demand per ADR-003, not in JWT
      // For MVP, we rely on middleware RBAC enforcement
      // TODO: Add client-side role check via /api/v1/users/me/role
    }

    if (status === 'unauthenticated') {
      router.push('/login');
    }
  }, [status, session, router]);

  // Show loading skeleton during initial load
  if (isLoading) {
    return (
      <div className="container mx-auto py-8">
        <LoadingSkeleton />
      </div>
    );
  }

  // Show error state if API request failed
  if (isError) {
    return (
      <div className="container mx-auto py-8">
        <ErrorState onRetry={refetch} error={error} />
      </div>
    );
  }

  return (
    <div className="container mx-auto py-8 space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-foreground">
            LLM Cost Dashboard
          </h1>
          <p className="text-muted-foreground mt-1">
            Real-time cost metrics across all agents and tenants • Auto-refreshes every 60s
          </p>
        </div>

        {/* Manual Refresh Button */}
        <Button
          variant="secondary"
          size="sm"
          onClick={() => refetch()}
          className="gap-2"
          aria-label="Refresh cost data"
        >
          <RefreshCw className="h-4 w-4" />
          Refresh
        </Button>
      </div>

      {/* Cost Metrics Cards Grid */}
      <CostMetricsCards data={data} />

      {/* Daily Spend Trend Chart (Story nextjs-story-10) */}
      <DailySpendChart
        data={trendData}
        loading={trendLoading}
        error={trendIsError ? trendError : null}
        onRetry={trendRefetch}
        className="mt-6"
      />

      {/* Token Breakdown Section (Story nextjs-story-11) */}
      <TokenBreakdownSection />

      {/* Budget Utilization Section (Story nextjs-story-12) */}
      <BudgetUtilizationSection />

      {/* Footer Info */}
      <div className="text-xs text-muted-foreground text-center pt-4">
        Last updated: {new Date().toLocaleTimeString()} • Data refreshes automatically
      </div>
    </div>
  );
}

/**
 * Token Breakdown Section
 *
 * Displays token usage breakdown with date range selector, pie chart, and sortable table.
 * Maps to Story: nextjs-story-11-llm-cost-dashboard-token-breakdown
 *
 * Features:
 * - Date range selector with presets ("Last 7 days", "Last 30 days")
 * - Pie/donut chart visualization
 * - Sortable data table
 */
function TokenBreakdownSection() {
  const [dateRange, setDateRange] = React.useState<{
    startDate: Date;
    endDate: Date;
  } | null>(null);

  const { data, isLoading, isError, error, refetch } = useTokenBreakdown(
    dateRange?.startDate,
    dateRange?.endDate
  );

  // Show error state if API request failed
  if (isError) {
    return (
      <div className="space-y-4 mt-6">
        <h2 className="text-2xl font-bold text-foreground">Token Breakdown</h2>
        <div className="flex flex-col items-center justify-center py-12 bg-white/75 backdrop-blur-[32px] rounded-[24px] shadow-lg border border-white/20">
          <AlertCircle className="h-12 w-12 text-destructive mb-3" />
          <h3 className="text-lg font-semibold text-foreground mb-1">
            Failed to Load Token Data
          </h3>
          <p className="text-sm text-muted-foreground mb-4 text-center max-w-md">
            {error?.message || 'An error occurred while fetching token breakdown data.'}
          </p>
          <Button onClick={() => refetch()} className="gap-2" size="sm">
            <RefreshCw className="h-4 w-4" />
            Retry
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 mt-6">
      <h2 className="text-2xl font-bold text-foreground">Token Breakdown</h2>

      {/* Date Range Selector */}
      <DateRangeSelector
        onChange={setDateRange}
        className="mb-6"
      />

      {/* Chart and Table Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Pie Chart */}
        <TokenBreakdownChart
          data={data || []}
          loading={isLoading}
        />

        {/* Data Table */}
        <TokenBreakdownTable
          data={data || []}
          loading={isLoading}
        />
      </div>
    </div>
  );
}

/**
 * Budget Utilization Section
 *
 * Displays tenant budget utilization with filtering and sorting.
 * Maps to Story: nextjs-story-12-llm-cost-dashboard-budget-bars
 *
 * Features:
 * - Color-coded progress bars (green <75%, yellow 75-90%, red >90%)
 * - Expandable agent breakdowns
 * - Filter: All tenants, Over budget only, High utilization (>75%)
 * - Sort: Highest utilization, Alphabetical, Budget amount
 * - Auto-refresh every 60 seconds
 */
function BudgetUtilizationSection() {
  return (
    <div className="space-y-6 mt-6">
      <h2 className="text-2xl font-bold text-foreground">Budget Utilization by Tenant</h2>
      <BudgetUtilizationList />
    </div>
  );
}
