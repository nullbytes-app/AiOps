/**
 * MetricCard Component
 *
 * Displays a single cost metric card with formatted value and optional trend indicator.
 * Follows 2025 Liquid Glass design system with glassmorphic styling.
 *
 * Used by: CostMetricsCards component for LLM Cost Dashboard
 */

'use client';

import React from 'react';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface MetricCardProps {
  /** Card label/title (e.g., "Today's Spend") */
  label: string;
  /** Formatted value to display (e.g., "$1,234.56", "1.2K") */
  value: string;
  /** Optional subtitle for additional context */
  subtitle?: string;
  /** Optional trend percentage (positive = increase, negative = decrease, 0 = no change) */
  trendPercent?: number;
  /** Optional trend icon (↑, ↓, →) */
  trendIcon?: string;
  /** Loading state - shows skeleton animation */
  loading?: boolean;
  /** Additional CSS classes */
  className?: string;
}

/**
 * Determine trend color and icon component based on percentage
 */
function getTrendInfo(trendPercent?: number): {
  Icon: React.ComponentType<{ className?: string }>;
  color: string;
  ariaLabel: string;
} {
  if (trendPercent === undefined || trendPercent === 0) {
    return {
      Icon: Minus,
      color: 'text-muted-foreground',
      ariaLabel: 'No change',
    };
  }

  if (trendPercent > 0) {
    return {
      Icon: TrendingUp,
      color: 'text-green-500',
      ariaLabel: `Increased by ${Math.abs(trendPercent).toFixed(1)}%`,
    };
  }

  return {
    Icon: TrendingDown,
    color: 'text-red-500',
    ariaLabel: `Decreased by ${Math.abs(trendPercent).toFixed(1)}%`,
  };
}

/**
 * MetricCard - Single cost metric display
 *
 * Renders a glassmorphic card with:
 * - Label (e.g., "Today's Spend")
 * - Large formatted value (e.g., "$1,234.56")
 * - Optional subtitle (e.g., "Top Tenant: Acme Corp")
 * - Optional trend indicator with percentage
 *
 * @example
 * ```tsx
 * <MetricCard
 *   label="Today's Spend"
 *   value="$1,234.56"
 *   trendPercent={15.3}
 *   trendIcon="↑"
 * />
 * ```
 */
export function MetricCard({
  label,
  value,
  subtitle,
  trendPercent,
  trendIcon,
  loading = false,
  className,
}: MetricCardProps) {
  const { Icon, color, ariaLabel } = getTrendInfo(trendPercent);

  // Skeleton loading state
  if (loading) {
    return (
      <div
        className={cn(
          'glass-card p-6 rounded-xl',
          'animate-pulse',
          className
        )}
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
    <div
      className={cn(
        'glass-card p-6 rounded-xl',
        'transition-all duration-300 hover:scale-[1.02]',
        'border border-border/50',
        className
      )}
    >
      {/* Label */}
      <p className="text-sm font-medium text-muted-foreground mb-2">
        {label}
      </p>

      {/* Value */}
      <div className="flex items-baseline gap-3">
        <h3 className="text-3xl font-bold text-foreground">
          {value}
        </h3>

        {/* Trend Indicator */}
        {trendPercent !== undefined && (
          <div
            className={cn('flex items-center gap-1 text-sm font-medium', color)}
            aria-label={ariaLabel}
          >
            <Icon className="h-4 w-4" />
            <span>
              {trendIcon} {Math.abs(trendPercent).toFixed(1)}%
            </span>
          </div>
        )}
      </div>

      {/* Subtitle */}
      {subtitle && (
        <p className="text-xs text-muted-foreground mt-2">
          {subtitle}
        </p>
      )}
    </div>
  );
}
