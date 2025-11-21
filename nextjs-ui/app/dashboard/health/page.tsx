/**
 * System Health Dashboard Page
 *
 * Real-time monitoring of system component health status.
 * Auto-refreshes every 5 seconds using TanStack Query.
 */

'use client';

import React from 'react';
import { useHealthStatus } from '@/lib/hooks/useHealthStatus';
import { HealthCard } from '@/components/dashboard/health/HealthCard';
import { Button } from '@/components/ui/Button';
import { Server, Database, Cpu, Activity, RefreshCw, AlertCircle } from 'lucide-react';

/**
 * Skeleton loading state for health cards
 */
function HealthDashboardSkeleton() {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
      {[1, 2, 3, 4].map((i) => (
        <div key={i} className="glass-card h-48 animate-pulse">
          <div className="p-6 space-y-4">
            <div className="h-4 bg-muted rounded w-1/2" />
            <div className="h-8 bg-muted rounded w-1/3" />
            <div className="space-y-2">
              <div className="h-3 bg-muted rounded" />
              <div className="h-3 bg-muted rounded w-5/6" />
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

/**
 * Error state component
 */
function ErrorState({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center py-12 glass-card rounded-lg">
      <AlertCircle className="h-12 w-12 text-destructive mb-4" />
      <h3 className="text-lg font-semibold mb-2">Failed to Load Health Data</h3>
      <p className="text-sm text-muted-foreground mb-6 max-w-md text-center">
        {message}
      </p>
      <Button onClick={onRetry} variant="secondary">
        <RefreshCw className="mr-2 h-4 w-4" />
        Retry
      </Button>
    </div>
  );
}

/**
 * System Health Dashboard Page Component
 */
export default function HealthDashboardPage() {
  const { data, isLoading, isError, error, refetch, isFetching } = useHealthStatus();

  // Loading state
  if (isLoading) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold">System Health</h1>
          <p className="text-muted-foreground">
            Monitor the health status of all system components
          </p>
        </div>
        <HealthDashboardSkeleton />
      </div>
    );
  }

  // Error state
  if (isError) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold">System Health</h1>
          <p className="text-muted-foreground">
            Monitor the health status of all system components
          </p>
        </div>
        <ErrorState
          message={error?.message || 'An unexpected error occurred'}
          onRetry={() => refetch()}
        />
      </div>
    );
  }

  // Data undefined check
  if (!data) {
    return null;
  }

  // Success state with data
  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">System Health</h1>
          <p className="text-muted-foreground">
            Monitor the health status of all system components
          </p>
        </div>
        {/* Refresh Indicator */}
        {isFetching && (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <RefreshCw className="h-4 w-4 animate-spin" />
            Updating...
          </div>
        )}
      </div>

      {/* Breadcrumbs */}
      <nav className="text-sm text-muted-foreground">
        Dashboard &gt; System Health
      </nav>

      {/* Health Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <HealthCard
          title="API Server"
          health={data.api}
          lastUpdated={data.timestamp}
          icon={<Server className="h-4 w-4" />}
        />
        <HealthCard
          title="Celery Workers"
          health={data.workers}
          lastUpdated={data.timestamp}
          icon={<Cpu className="h-4 w-4" />}
        />
        <HealthCard
          title="PostgreSQL Database"
          health={data.database}
          lastUpdated={data.timestamp}
          icon={<Database className="h-4 w-4" />}
        />
        <HealthCard
          title="Redis Cache"
          health={data.redis}
          lastUpdated={data.timestamp}
          icon={<Activity className="h-4 w-4" />}
        />
      </div>

      {/* Auto-refresh Info */}
      <div className="text-xs text-muted-foreground text-center">
        Auto-refreshes every 5 seconds • Last updated: {new Date(data.timestamp).toLocaleTimeString()}
      </div>
    </div>
  );
}
