/**
 * Agent Performance Dashboard Page
 * Real-time performance metrics for selected agent
 * RBAC: developer/admin only
 * Following 2025 Next.js 14 App Router patterns
 */

'use client';

import { useState, useEffect } from 'react';
import { useSession } from 'next-auth/react';
import { useRouter } from 'next/navigation';
import { AgentSelector } from '@/components/agent-performance/AgentSelector';
import { DateRangeSelector } from '@/components/agent-performance/DateRangeSelector';
import { AgentMetricsCards } from '@/components/agent-performance/AgentMetricsCards';
import { ExecutionTrendChart } from '@/components/agent-performance/ExecutionTrendChart';
import { ErrorAnalysisTable } from '@/components/agent-performance/ErrorAnalysisTable';
import { SlowestExecutionsList } from '@/components/agent-performance/SlowestExecutionsList';
import { EmptyState } from '@/components/agent-performance/EmptyState';
import { getDateRangePreset } from '@/lib/utils/performance';
import { autoSelectGranularity } from '@/lib/utils/chart';
import { RefreshCw } from 'lucide-react';

type DateRangePreset = 'last_7' | 'last_30' | 'custom';

export default function AgentPerformancePage() {
  const { data: session, status } = useSession();
  const router = useRouter();

  // RBAC check: only developer/admin allowed
  useEffect(() => {
    if (status === 'loading') return;

    if (!session) {
      router.push('/login');
      return;
    }

    const userRole = session.user?.role;
    if (userRole !== 'developer' && userRole !== 'admin' && userRole !== 'super_admin' && userRole !== 'tenant_admin') {
      router.push('/dashboard');
    }
  }, [session, status, router]);

  // State management
  const [selectedAgentId, setSelectedAgentId] = useState<string | null>(null);
  const [dateRangePreset, setDateRangePreset] = useState<DateRangePreset>('last_7');
  const [dateRange, setDateRange] = useState(() => getDateRangePreset('last_7'));
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());

  // Update date range when preset changes
  const handlePresetChange = (preset: DateRangePreset) => {
    setDateRangePreset(preset);
    if (preset !== 'custom') {
      const range = getDateRangePreset(preset);
      setDateRange(range);
    }
  };

  // Auto-refresh timestamp update (60s interval matches React Query)
  useEffect(() => {
    const interval = setInterval(() => {
      setLastUpdate(new Date());
    }, 60000);

    return () => clearInterval(interval);
  }, []);

  // Loading state while checking auth
  if (status === 'loading') {
    return (
      <div className="container mx-auto p-6">
        <div className="h-10 w-64 bg-gray-200 animate-pulse rounded mb-6" />
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="h-32 bg-gray-200 animate-pulse rounded" />
          ))}
        </div>
      </div>
    );
  }

  const formatLastUpdate = () => {
    const seconds = Math.floor((Date.now() - lastUpdate.getTime()) / 1000);
    if (seconds < 60) return `${seconds}s ago`;
    const minutes = Math.floor(seconds / 60);
    return `${minutes}m ago`;
  };

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Agent Performance Dashboard</h1>
        <p className="text-muted-foreground mt-2">
          Monitor execution metrics, success rates, and performance trends for your agents
        </p>
      </div>

      {/* Controls Row */}
      <div className="flex flex-col md:flex-row gap-4 items-start md:items-center justify-between">
        <div className="flex flex-col sm:flex-row gap-4">
          <div>
            <label className="text-sm font-medium mb-2 block">Select Agent</label>
            <AgentSelector value={selectedAgentId} onChange={setSelectedAgentId} />
          </div>

          <div>
            <label className="text-sm font-medium mb-2 block">Date Range</label>
            <DateRangeSelector
              value={dateRangePreset}
              onChange={handlePresetChange}
              onDateChange={(start, end) => setDateRange({ start, end })}
            />
          </div>
        </div>

        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <RefreshCw className="h-4 w-4" />
          <span>Last updated: {formatLastUpdate()}</span>
        </div>
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {!selectedAgentId ? (
          <EmptyState
            message="No agent selected"
            suggestion="Please select an agent from the dropdown above to view performance metrics"
          />
        ) : (
          <AgentMetricsCards
            agentId={selectedAgentId}
            startDate={dateRange.start}
            endDate={dateRange.end}
          />
        )}
      </div>

      {/* Execution Trend Chart */}
      {selectedAgentId && (
        <ExecutionTrendChart
          agentId={selectedAgentId}
          startDate={dateRange.start}
          endDate={dateRange.end}
          defaultGranularity={autoSelectGranularity(dateRange.start, dateRange.end)}
        />
      )}

      {/* Error Analysis Table (Story 15) */}
      {selectedAgentId && (
        <div>
          <h2 className="text-2xl font-bold mb-4">Error Analysis</h2>
          <ErrorAnalysisTable
            agentId={selectedAgentId}
            startDate={new Date(dateRange.start)}
            endDate={new Date(dateRange.end)}
          />
        </div>
      )}

      {/* Slowest Executions List (Story 16) */}
      {selectedAgentId && (
        <SlowestExecutionsList
          agentId={selectedAgentId}
          startDate={new Date(dateRange.start)}
          endDate={new Date(dateRange.end)}
        />
      )}
    </div>
  );
}
