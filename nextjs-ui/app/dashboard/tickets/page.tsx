/**
 * Ticket Processing Dashboard Page
 *
 * Displays real-time ticket processing metrics with queue gauge, processing rate, error rate, and recent activity.
 * Auto-refreshes queue depth every 10 seconds and activity every 15 seconds.
 */

'use client';

import React from 'react';
import { useTicketMetrics } from '@/lib/hooks/useTicketMetrics';
import { QueueGauge } from '@/components/charts/QueueGauge';
import { ProcessingRateCard } from '@/components/dashboard/tickets/ProcessingRateCard';
import { ErrorRateCard } from '@/components/dashboard/tickets/ErrorRateCard';
import { RecentActivity } from '@/components/dashboard/tickets/RecentActivity';
import { Button } from '@/components/ui/Button';
import { RefreshCw, AlertCircle } from 'lucide-react';
import { Card } from '@/components/ui/Card';

/**
 * Error State Component
 */
function ErrorState({ onRetry }: { onRetry: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center py-24">
      <AlertCircle className="h-16 w-16 text-destructive mb-4" />
      <h2 className="text-2xl font-bold text-foreground mb-2">
        Failed to Load Ticket Metrics
      </h2>
      <p className="text-muted-foreground mb-6 max-w-md text-center">
        We couldn&apos;t fetch the ticket processing data. Please check your connection and try again.
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
      <div className="text-6xl mb-4" role="img" aria-label="Ticket">
        🎫
      </div>
      <h2 className="text-2xl font-bold text-foreground mb-2">
        No Ticket Activity Yet
      </h2>
      <p className="text-muted-foreground max-w-md text-center">
        Once tickets start being processed, metrics and activity will appear here.
        Configure your ServiceDesk Plus webhook to begin tracking.
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
      {/* Top Row: Gauge + Stats */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="glass-card p-6 h-80" />
        <div className="glass-card p-6 h-80" />
        <div className="glass-card p-6 h-80" />
      </div>

      {/* Recent Activity */}
      <div className="glass-card p-6 h-96" />
    </div>
  );
}

/**
 * Ticket Processing Dashboard Page
 *
 * Main page component showing ticket queue and processing metrics.
 */
export default function TicketProcessingPage() {
  const { data, isLoading, isError, refetch, isFetching } = useTicketMetrics();

  // Handle ticket click (placeholder - would navigate to ticket details)
  const handleTicketClick = (ticketId: string) => {
    console.log('Navigate to ticket:', ticketId);
    // TODO: Implement navigation to ticket details page
    // router.push(`/tickets/${ticketId}`);
  };

  // Loading state
  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-foreground">
              Ticket Processing
            </h1>
            <p className="text-muted-foreground mt-2">
              Monitor ticket queue depth and processing performance
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
              Ticket Processing
            </h1>
            <p className="text-muted-foreground mt-2">
              Monitor ticket queue depth and processing performance
            </p>
          </div>
        </div>
        <ErrorState onRetry={refetch} />
      </div>
    );
  }

  // Empty state (no recent tickets)
  if (!data || data.recent_tickets.length === 0) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-foreground">
              Ticket Processing
            </h1>
            <p className="text-muted-foreground mt-2">
              Monitor ticket queue depth and processing performance
            </p>
          </div>
        </div>
        <EmptyState />
      </div>
    );
  }

  // Generate mock sparkline data for processing rate (last 12 hours)
  const sparklineData = Array.from({ length: 12 }, () =>
    Math.floor(Math.random() * 30) + 70
  );

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-foreground">
            Ticket Processing
          </h1>
          <p className="text-muted-foreground mt-2">
            Monitor ticket queue depth and processing performance
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

      {/* Top Row: Queue Gauge + Processing Rate + Error Rate */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Queue Depth Gauge */}
        <Card className="glass-card p-6">
          <h3 className="text-lg font-semibold text-foreground mb-4">
            Queue Depth
          </h3>
          <QueueGauge queueDepth={data.queue_depth} maxCapacity={200} />
        </Card>

        {/* Processing Rate */}
        <ProcessingRateCard
          ratePerHour={data.processing_rate_per_hour}
          trendData={sparklineData}
        />

        {/* Error Rate */}
        <ErrorRateCard
          errorRate={data.error_rate_percentage}
          totalProcessed={100}
        />
      </div>

      {/* Recent Ticket Activity */}
      <RecentActivity
        tickets={data.recent_tickets}
        onTicketClick={handleTicketClick}
      />

      {/* Auto-refresh Info */}
      <p className="text-xs text-muted-foreground text-center">
        Queue depth refreshes every 10 seconds • Activity refreshes every 15 seconds • Last updated: {new Date().toLocaleTimeString()}
      </p>
    </div>
  );
}
