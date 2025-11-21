/**
 * Agent Metrics Dashboard Page
 *
 * Displays real-time agent execution metrics with KPI cards, timeline chart, and performance table.
 * Auto-refreshes every 30 seconds following 2025 TanStack Query best practices.
 */

'use client';

import React from 'react';
import { useAgentMetrics } from '@/lib/hooks/useAgentMetrics';
import { KPICard } from '@/components/dashboard/agents/KPICard';
import { ExecutionChart } from '@/components/dashboard/agents/ExecutionChart';
import { AgentTable } from '@/components/dashboard/agents/AgentTable';
import { Button } from '@/components/ui/Button';
import { RefreshCw, AlertCircle } from 'lucide-react';

/**
 * Error State Component
 */
function ErrorState({ onRetry }: { onRetry: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center py-24">
      <AlertCircle className="h-16 w-16 text-destructive mb-4" />
      <h2 className="text-2xl font-bold text-foreground mb-2">
        Failed to Load Metrics
      </h2>
      <p className="text-muted-foreground mb-6 max-w-md text-center">
        We couldn&apos;t fetch the agent metrics data. Please check your connection and try again.
      </p>
      <Button onClick={onRetry} className="gap-2">
        <RefreshCw className="h-4 w-4" />
        Retry
      </Button>
    </div>
  );
}

/**
 * Empty State Component
 */
function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center py-24">
      <div className="text-6xl mb-4" role="img" aria-label="Robot">
        🤖
      </div>
      <h2 className="text-2xl font-bold text-foreground mb-2">
        No Agent Executions Yet
      </h2>
      <p className="text-muted-foreground max-w-md text-center">
        Once agents start processing tickets, execution metrics will appear here.
        Check back after your first ticket is enhanced.
      </p>
    </div>
  );
}

/**
 * Skeleton Loading State
 */
function SkeletonUI() {
  return (
    <div className="space-y-6 animate-pulse">
      {/* KPI Cards Skeleton */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {[1, 2, 3].map((i) => (
          <div key={i} className="glass-card p-6 h-32" />
        ))}
      </div>

      {/* Chart Skeleton */}
      <div className="glass-card p-6 h-96" />

      {/* Table Skeleton */}
      <div className="glass-card p-6 h-96" />
    </div>
  );
}

/**
 * Agent Metrics Dashboard Page
 *
 * Main page component showing agent execution metrics and performance data.
 */
export default function AgentMetricsPage() {
  const { data, isLoading, isError, refetch, isFetching } = useAgentMetrics('24h');

  // Loading state
  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-foreground">
              Agent Metrics
            </h1>
            <p className="text-muted-foreground mt-2">
              Monitor agent execution performance and costs
            </p>
          </div>
        </div>
        <SkeletonUI />
      </div>
    );
  }

  // Error state
  if (isError) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-foreground">
              Agent Metrics
            </h1>
            <p className="text-muted-foreground mt-2">
              Monitor agent execution performance and costs
            </p>
          </div>
        </div>
        <ErrorState onRetry={refetch} />
      </div>
    );
  }

  // Empty state
  if (!data || data.kpis.totalExecutions === 0) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-foreground">
              Agent Metrics
            </h1>
            <p className="text-muted-foreground mt-2">
              Monitor agent execution performance and costs
            </p>
          </div>
        </div>
        <EmptyState />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-foreground">
            Agent Metrics
          </h1>
          <p className="text-muted-foreground mt-2">
            Monitor agent execution performance and costs
          </p>
        </div>

        {/* Refresh Indicator */}
        <div className="flex items-center gap-3">
          {isFetching && (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <div className="w-2 h-2 bg-success rounded-full animate-pulse" />
              <span>Updating...</span>
            </div>
          )}
          <Button
            variant="secondary"
            size="sm"
            onClick={() => refetch()}
            className="gap-2"
            aria-label="Manually refresh data"
          >
            <RefreshCw className="h-4 w-4" />
            Refresh
          </Button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <KPICard
          title="Total Executions (24h)"
          value={data.kpis.totalExecutions}
          changePercent={data.kpis.changePercent}
          format="number"
        />
        <KPICard
          title="Success Rate"
          value={data.kpis.successRate}
          changePercent={data.kpis.changePercent > 0 ? 2.1 : -1.3} // Placeholder trend
          format="percentage"
          decimals={1}
        />
        <KPICard
          title="Avg Cost per Execution"
          value={data.kpis.avgCost}
          format="currency"
          decimals={4}
        />
      </div>

      {/* Execution Timeline Chart */}
      <ExecutionChart data={data.chartData} />

      {/* Agent Performance Table */}
      <AgentTable data={data.tableData} />

      {/* Auto-refresh Info */}
      <p className="text-xs text-muted-foreground text-center">
        Data auto-refreshes every 30 seconds • Last updated: {new Date().toLocaleTimeString()}
      </p>
    </div>
  );
}
