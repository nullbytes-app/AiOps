/**
 * ProcessingRateCard Component
 *
 * Displays ticket processing rate with sparkline trend chart.
 * Shows tickets processed per hour with historical trend.
 */

'use client';

import React from 'react';
import { Card } from '@/components/ui/Card';
import { Sparkline } from '@/components/charts/Sparkline';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';

export interface ProcessingRateCardProps {
  ratePerHour: number;
  trendData?: number[]; // Last 12 hours of processing rates
  className?: string;
}

/**
 * Determine trend direction from sparkline data
 */
function getTrendDirection(data: number[]): 'up' | 'down' | 'steady' {
  if (data.length < 2) return 'steady';

  const recent = data.slice(-3).reduce((a, b) => a + b, 0) / 3;
  const older = data.slice(0, 3).reduce((a, b) => a + b, 0) / 3;

  const diff = ((recent - older) / older) * 100;

  if (diff > 5) return 'up';
  if (diff < -5) return 'down';
  return 'steady';
}

/**
 * ProcessingRateCard Component
 *
 * @example
 * ```tsx
 * <ProcessingRateCard
 *   ratePerHour={85}
 *   trendData={[72, 78, 81, 85, 88, 92, 90, 85, 82, 79, 83, 85]}
 * />
 * ```
 */
export function ProcessingRateCard({
  ratePerHour,
  trendData = [],
  className = '',
}: ProcessingRateCardProps) {
  const trend = getTrendDirection(trendData);

  const TrendIcon =
    trend === 'up' ? TrendingUp : trend === 'down' ? TrendingDown : Minus;

  const trendColor =
    trend === 'up'
      ? 'text-success'
      : trend === 'down'
      ? 'text-destructive'
      : 'text-muted-foreground';

  const trendLabel =
    trend === 'up'
      ? 'Increasing'
      : trend === 'down'
      ? 'Decreasing'
      : 'Steady';

  return (
    <Card className={`glass-card p-6 ${className}`}>
      <div className="flex items-start justify-between mb-4">
        <div>
          <h3 className="text-sm font-medium text-muted-foreground mb-2">
            Processing Rate
          </h3>
          <p className="text-4xl font-bold text-foreground" aria-label={`Processing rate: ${ratePerHour} tickets per hour`}>
            {ratePerHour}
          </p>
          <p className="text-sm text-muted-foreground mt-1">tickets/hour</p>
        </div>

        {/* Trend Indicator */}
        <div className={`flex items-center gap-1 ${trendColor}`} aria-label={`Trend: ${trendLabel}`}>
          <TrendIcon className="h-5 w-5" aria-hidden="true" />
          <span className="text-sm font-semibold capitalize">{trendLabel}</span>
        </div>
      </div>

      {/* Sparkline Chart */}
      {trendData.length > 0 && (
        <div className="mt-4">
          <p className="text-xs text-muted-foreground mb-2">Last 12 Hours</p>
          <Sparkline
            data={trendData.map(value => ({ value }))}
            stroke="hsl(var(--primary))"
            fill="hsl(var(--primary) / 0.2)"
            height={60}
          />
        </div>
      )}
    </Card>
  );
}
