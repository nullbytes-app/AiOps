/**
 * ErrorRateCard Component
 *
 * Displays ticket processing error rate with color-coded severity.
 * Green (<5%), Yellow (5-10%), Red (>10%).
 */

'use client';

import React from 'react';
import { Card } from '@/components/ui/Card';
import { AlertTriangle, CheckCircle, AlertCircle } from 'lucide-react';

export interface ErrorRateCardProps {
  errorRate: number; // Percentage (0-100)
  totalProcessed?: number;
  className?: string;
}

/**
 * Determine severity level based on error rate
 */
function getSeverity(rate: number): {
  level: 'low' | 'medium' | 'high';
  color: string;
  bgColor: string;
  Icon: React.ComponentType<{ className?: string }>;
  label: string;
} {
  if (rate < 5) {
    return {
      level: 'low',
      color: 'text-success',
      bgColor: 'bg-success/10',
      Icon: CheckCircle,
      label: 'Healthy',
    };
  }

  if (rate < 10) {
    return {
      level: 'medium',
      color: 'text-warning',
      bgColor: 'bg-warning/10',
      Icon: AlertTriangle,
      label: 'Warning',
    };
  }

  return {
    level: 'high',
    color: 'text-destructive',
    bgColor: 'bg-destructive/10',
    Icon: AlertCircle,
    label: 'Critical',
  };
}

/**
 * ErrorRateCard Component
 *
 * @example
 * ```tsx
 * <ErrorRateCard
 *   errorRate={5.6}
 *   totalProcessed={100}
 * />
 * ```
 */
export function ErrorRateCard({
  errorRate,
  totalProcessed,
  className = '',
}: ErrorRateCardProps) {
  const { color, bgColor, Icon, label } = getSeverity(errorRate);

  return (
    <Card className={`glass-card p-6 ${className}`}>
      <div className="flex items-start justify-between mb-4">
        <div className="flex-1">
          <h3 className="text-sm font-medium text-muted-foreground mb-2">
            Error Rate
          </h3>
          <div className="flex items-baseline gap-2">
            <p className={`text-4xl font-bold ${color}`} aria-label={`Error rate: ${errorRate.toFixed(1)} percent`}>
              {errorRate.toFixed(1)}%
            </p>
          </div>
          {totalProcessed !== undefined && (
            <p className="text-sm text-muted-foreground mt-1">
              of {totalProcessed} tickets
            </p>
          )}
        </div>

        {/* Status Badge */}
        <div className={`${bgColor} ${color} px-3 py-1 rounded-full flex items-center gap-2`}>
          <Icon className="h-4 w-4" aria-hidden="true" />
          <span className="text-sm font-semibold">{label}</span>
        </div>
      </div>

      {/* Severity Indicator Bar */}
      <div className="mt-4">
        <div className="flex justify-between text-xs text-muted-foreground mb-2">
          <span>0%</span>
          <span className="text-success">Healthy (&lt;5%)</span>
          <span className="text-warning">Warning (5-10%)</span>
          <span className="text-destructive">Critical (&gt;10%)</span>
        </div>
        <div className="relative h-2 bg-muted rounded-full overflow-hidden">
          {/* Background gradient */}
          <div className="absolute inset-0 bg-gradient-to-r from-success via-warning to-destructive opacity-30" />

          {/* Current position indicator */}
          <div
            className={`absolute top-0 bottom-0 w-1 ${bgColor} ${color} transition-all duration-500`}
            style={{ left: `${Math.min(errorRate, 100)}%` }}
            aria-label={`Error rate position at ${errorRate.toFixed(1)}%`}
          />
        </div>
      </div>
    </Card>
  );
}
