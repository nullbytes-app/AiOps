/**
 * Metric Card Component
 * Displays a single performance metric with optional color coding and trend
 * Following existing glass-card pattern from llm-costs components
 */

'use client';

import { cn } from '@/lib/utils/cn';

interface MetricCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon?: React.ReactNode;
  colorClass?: string;
  trend?: {
    value: number;
    direction: 'up' | 'down';
  };
  isLoading?: boolean;
}

export function MetricCard({
  title,
  value,
  subtitle,
  icon,
  colorClass = 'text-foreground',
  trend,
  isLoading = false
}: MetricCardProps) {
  // Skeleton loading state
  if (isLoading) {
    return (
      <div
        className="glass-card p-6 rounded-xl animate-pulse"
        role="status"
        aria-label="Loading metric"
      >
        <div className="h-4 bg-muted/50 rounded w-24 mb-4" />
        <div className="h-8 bg-muted/50 rounded w-32 mb-2" />
        {subtitle && <div className="h-4 bg-muted/50 rounded w-36" />}
      </div>
    );
  }

  return (
    <div className="glass-card p-6 rounded-xl transition-all duration-300 hover:scale-[1.02] border border-border/50">
      {/* Header with title and optional icon */}
      <div className="flex items-center justify-between mb-2">
        <p className="text-sm font-medium text-muted-foreground">
          {title}
        </p>
        {icon && <div className="text-muted-foreground">{icon}</div>}
      </div>

      {/* Value */}
      <div className={cn("text-3xl font-bold tabular-nums", colorClass)}>
        {value}
      </div>

      {/* Subtitle */}
      {subtitle && (
        <p className="text-xs text-muted-foreground mt-2">{subtitle}</p>
      )}

      {/* Trend indicator */}
      {trend && (
        <div className={cn(
          "text-xs mt-2 flex items-center gap-1 tabular-nums font-medium",
          trend.direction === 'up' ? 'text-green-600' : 'text-red-600'
        )}>
          <span>{trend.direction === 'up' ? '↑' : '↓'}</span>
          <span>{Math.abs(trend.value).toFixed(1)}% vs previous period</span>
        </div>
      )}
    </div>
  );
}
