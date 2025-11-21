/**
 * KPICard Component
 *
 * Displays a key performance indicator with value, trend, and change percentage.
 * Follows 2025 Liquid Glass design system with auto-updating metrics.
 */

'use client';

import React from 'react';
import { Card } from '@/components/ui/Card';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';

export interface KPICardProps {
  title: string;
  value: number | string;
  changePercent?: number;
  format?: 'number' | 'currency' | 'percentage';
  decimals?: number;
  loading?: boolean;
  className?: string;
}

/**
 * Format value based on type
 */
function formatValue(
  value: number | string,
  format: 'number' | 'currency' | 'percentage' = 'number',
  decimals: number = 0
): string {
  if (typeof value === 'string') return value;

  switch (format) {
    case 'currency':
      return `$${value.toFixed(decimals)}`;
    case 'percentage':
      return `${value.toFixed(decimals)}%`;
    default:
      return value.toLocaleString(undefined, {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals,
      });
  }
}

/**
 * Determine trend icon and color based on change percentage
 */
function getTrendInfo(changePercent?: number): {
  Icon: React.ComponentType<{ className?: string }>;
  color: string;
  ariaLabel: string;
} {
  if (changePercent === undefined || changePercent === 0) {
    return {
      Icon: Minus,
      color: 'text-muted-foreground',
      ariaLabel: 'No change',
    };
  }

  if (changePercent > 0) {
    return {
      Icon: TrendingUp,
      color: 'text-success',
      ariaLabel: `Increased by ${Math.abs(changePercent).toFixed(1)}%`,
    };
  }

  return {
    Icon: TrendingDown,
    color: 'text-destructive',
    ariaLabel: `Decreased by ${Math.abs(changePercent).toFixed(1)}%`,
  };
}

/**
 * KPI Card Component
 *
 * @example
 * ```tsx
 * <KPICard
 *   title="Total Executions"
 *   value={1250}
 *   changePercent={12.5}
 *   format="number"
 * />
 *
 * <KPICard
 *   title="Success Rate"
 *   value={94.4}
 *   changePercent={-2.1}
 *   format="percentage"
 *   decimals={1}
 * />
 *
 * <KPICard
 *   title="Avg Cost"
 *   value={0.0124}
 *   format="currency"
 *   decimals={4}
 * />
 * ```
 */
export function KPICard({
  title,
  value,
  changePercent,
  format = 'number',
  decimals = 0,
  loading = false,
  className = '',
}: KPICardProps) {
  const { Icon, color, ariaLabel } = getTrendInfo(changePercent);
  const formattedValue = formatValue(value, format, decimals);

  return (
    <Card className={`glass-card p-6 ${className}`}>
      {/* Title */}
      <h3 className="text-sm font-medium text-muted-foreground mb-2">
        {title}
      </h3>

      {/* Value */}
      <div className="flex items-baseline justify-between">
        <p
          className="text-4xl font-bold text-foreground"
          aria-label={`${title}: ${formattedValue}`}
        >
          {loading ? (
            <span className="animate-pulse text-muted-foreground">--</span>
          ) : (
            formattedValue
          )}
        </p>

        {/* Trend Indicator */}
        {!loading && changePercent !== undefined && (
          <div
            className={`flex items-center gap-1 ${color}`}
            aria-label={ariaLabel}
          >
            <Icon className="h-5 w-5" aria-hidden="true" />
            <span className="text-sm font-semibold">
              {changePercent > 0 ? '+' : ''}
              {changePercent.toFixed(1)}%
            </span>
          </div>
        )}
      </div>

      {/* Supporting Info */}
      {!loading && changePercent !== undefined && (
        <p className="text-xs text-muted-foreground mt-2">
          vs. previous {format === 'percentage' ? 'period' : '24h'}
        </p>
      )}
    </Card>
  );
}
