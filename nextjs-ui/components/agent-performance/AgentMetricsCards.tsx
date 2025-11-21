/**
 * Agent Metrics Cards Component
 * Grid of 6 metric cards displaying agent performance
 * Following 2025 patterns with error states and retries
 */

'use client';

import { Activity, CheckCircle2, Clock, TrendingUp, XCircle, AlertTriangle } from 'lucide-react';
import { MetricCard } from './MetricCard';
import { EmptyState } from './EmptyState';
import { Button } from '@/components/ui/button';
import { useAgentMetrics } from '@/hooks/useAgentMetrics';
import {
  formatExecutionTime,
  formatCount,
  getSuccessRateColor,
} from '@/lib/utils/performance';

interface AgentMetricsCardsProps {
  agentId: string | null;
  startDate: string;
  endDate: string;
}

export function AgentMetricsCards({ agentId, startDate, endDate }: AgentMetricsCardsProps) {
  const { data, isLoading, error, refetch } = useAgentMetrics({
    agentId,
    startDate,
    endDate,
  });

  // Error state
  if (error) {
    return (
      <div className="col-span-full">
        <div className="flex flex-col items-center justify-center p-8 bg-red-50 border border-red-200 rounded-lg">
          <AlertTriangle className="h-12 w-12 text-red-600 mb-4" />
          <h3 className="text-lg font-semibold text-red-900 mb-2">Failed to load metrics</h3>
          <p className="text-sm text-red-700 mb-4">
            {error instanceof Error ? error.message : 'An error occurred while fetching data'}
          </p>
          <Button onClick={() => refetch()} variant="outline">
            Retry
          </Button>
        </div>
      </div>
    );
  }

  const metrics = data?.metrics;

  // Check for 0 executions (AC-6)
  if (metrics && metrics.total_executions === 0) {
    return (
      <EmptyState
        message="No executions found for this agent in the selected date range"
        suggestion="Try selecting a different date range or agent"
      />
    );
  }

  const successColor = metrics ? getSuccessRateColor(metrics.success_rate) : { color: '', variant: 'success' as const };

  return (
    <>
      <MetricCard
        title="Total Executions"
        value={isLoading ? '...' : formatCount(metrics?.total_executions || 0)}
        icon={<Activity className="h-4 w-4" />}
        isLoading={isLoading}
      />

      <MetricCard
        title="Success Rate"
        value={isLoading ? '...' : `${metrics?.success_rate.toFixed(1)}%`}
        icon={<CheckCircle2 className="h-4 w-4" />}
        colorClass={successColor.color}
        isLoading={isLoading}
      />

      <MetricCard
        title="Average Execution Time"
        value={isLoading ? '...' : formatExecutionTime(metrics?.avg_execution_time_ms || 0)}
        icon={<Clock className="h-4 w-4" />}
        isLoading={isLoading}
      />

      <MetricCard
        title="P95 Execution Time"
        value={isLoading ? '...' : formatExecutionTime(metrics?.p95_execution_time_ms || 0)}
        subtitle="95th percentile"
        icon={<TrendingUp className="h-4 w-4" />}
        isLoading={isLoading}
      />

      <MetricCard
        title="Total Errors"
        value={isLoading ? '...' : formatCount(metrics?.failed_executions || 0)}
        icon={<XCircle className="h-4 w-4" />}
        colorClass={metrics && metrics.failed_executions > 0 ? 'text-red-600' : 'text-foreground'}
        isLoading={isLoading}
      />

      <MetricCard
        title="Error Rate"
        value={isLoading ? '...' : `${metrics?.error_rate.toFixed(1)}%`}
        icon={<AlertTriangle className="h-4 w-4" />}
        colorClass={metrics && metrics.error_rate > 0 ? 'text-red-600' : 'text-green-600'}
        isLoading={isLoading}
      />
    </>
  );
}
