/**
 * Queue Status Dashboard Component
 *
 * Displays 4 glassmorphic metric cards:
 * - Queue Depth (color-coded: green < 10, yellow 10-50, red > 50)
 * - Processing Rate (tasks/min)
 * - Avg Wait Time (seconds)
 * - Failed Tasks (last 24 hours)
 *
 * Reference: Story 5, AC-1
 */

'use client';

import { useQueueStatus } from '@/lib/hooks/useQueue';

/**
 * Get color indicator based on queue depth
 */
const getDepthColor = (depth: number): string => {
  if (depth < 10) return 'text-accent-green';
  if (depth <= 50) return 'text-accent-orange';
  return 'text-accent-red';
};

/**
 * Format seconds to human-readable time
 */
const formatWaitTime = (seconds: number): string => {
  if (seconds < 60) return `${seconds.toFixed(1)}s`;
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  return `${minutes}m ${remainingSeconds.toFixed(0)}s`;
};

export function QueueStatus() {
  const { data: status, isLoading, error } = useQueueStatus();

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="glass-card p-6 animate-pulse">
            <div className="h-4 bg-white/20 rounded w-24 mb-2" />
            <div className="h-8 bg-white/20 rounded w-16" />
          </div>
        ))}
      </div>
    );
  }

  if (error || !status) {
    return (
      <div className="glass-card p-6 bg-accent-red/10">
        <p className="text-sm text-accent-red">
          Failed to load queue status. Retrying...
        </p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
      {/* Queue Depth Card */}
      <div className="glass-card p-6">
        <div className="text-caption text-text-secondary mb-2">Queue Depth</div>
        <div className={`text-h2 font-bold ${getDepthColor(status.depth)}`}>
          {status.depth}
        </div>
        <div className="text-small text-text-secondary mt-2">
          {status.is_paused ? '⏸️ Paused' : '▶️ Processing'}
        </div>
      </div>

      {/* Processing Rate Card */}
      <div className="glass-card p-6">
        <div className="text-caption text-text-secondary mb-2">
          Processing Rate
        </div>
        <div className="text-h2 font-bold text-text-primary">
          {status.processing_rate.toFixed(1)}
        </div>
        <div className="text-small text-text-secondary mt-2">tasks/min</div>
      </div>

      {/* Avg Wait Time Card */}
      <div className="glass-card p-6">
        <div className="text-caption text-text-secondary mb-2">
          Avg Wait Time
        </div>
        <div className="text-h2 font-bold text-text-primary">
          {formatWaitTime(status.avg_wait_time)}
        </div>
        <div className="text-small text-text-secondary mt-2">
          per task
        </div>
      </div>

      {/* Failed Tasks Card */}
      <div className="glass-card p-6">
        <div className="text-caption text-text-secondary mb-2">
          Failed Tasks
        </div>
        <div className="text-h2 font-bold text-accent-red">
          {status.failed_tasks_24h}
        </div>
        <div className="text-small text-text-secondary mt-2">last 24 hours</div>
      </div>
    </div>
  );
}
