/**
 * HealthCard Component
 *
 * Displays health status for a system component with metrics and indicators.
 */

'use client';

import React from 'react';
import { ComponentHealth, HealthStatus } from '@/lib/api/health';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { formatDistanceToNow } from '@/lib/utils/date';

interface HealthCardProps {
  title: string;
  health: ComponentHealth;
  lastUpdated?: string;
  icon?: React.ReactNode;
}

/**
 * Get badge variant based on health status
 */
function getStatusVariant(status: HealthStatus): 'success' | 'warning' | 'error' {
  switch (status) {
    case 'healthy':
      return 'success';
    case 'degraded':
      return 'warning';
    case 'down':
      return 'error';
  }
}

/**
 * Get status badge color class
 */
function getStatusColorClass(status: HealthStatus): string {
  switch (status) {
    case 'healthy':
      return 'bg-accent-green text-white';
    case 'degraded':
      return 'bg-accent-orange text-white';
    case 'down':
      return 'bg-red-600 text-white';
  }
}

/**
 * Health status card component
 */
export function HealthCard({ title, health, lastUpdated, icon }: HealthCardProps) {
  return (
    <Card padding="none">
      {/* Header */}
      <div className="p-4 pb-2 flex flex-row items-center justify-between">
        <div className="text-sm font-medium flex items-center gap-2">
          {icon}
          {title}
        </div>
        <Badge
          data-testid="status-badge"
          variant={getStatusVariant(health.status)}
          className={getStatusColorClass(health.status)}
          aria-live="polite"
        >
          {health.status.charAt(0).toUpperCase() + health.status.slice(1)}
        </Badge>
      </div>

      {/* Content */}
      <div className="p-4 pt-2">
        <div className="space-y-2">
          {/* Primary Metrics */}
          {health.uptime !== undefined && (
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-600">Uptime</span>
              <span className="text-lg font-semibold">
                {Math.floor(health.uptime / 3600)}h
              </span>
            </div>
          )}

          {health.response_time_ms !== undefined && (
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-600">Response Time</span>
              <span className="text-lg font-semibold">{health.response_time_ms}ms</span>
            </div>
          )}

          {/* Additional Details */}
          {health.details && (
            <div className="mt-3 pt-3 border-t border-gray-200 space-y-1">
              {Object.entries(health.details).map(([key, value]) => (
                <div key={key} className="flex justify-between items-center text-xs">
                  <span className="text-gray-600">
                    {key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                  </span>
                  <span className="font-medium">{String(value)}</span>
                </div>
              ))}
            </div>
          )}

          {/* Last Updated */}
          {lastUpdated && (
            <div className="text-xs text-gray-500 mt-2">
              Updated {formatDistanceToNow(new Date(lastUpdated))}
            </div>
          )}
        </div>
      </div>
    </Card>
  );
}
