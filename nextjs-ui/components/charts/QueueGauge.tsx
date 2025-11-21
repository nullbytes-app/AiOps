/**
 * QueueGauge Component
 *
 * Circular gauge using Recharts RadialBarChart for queue depth visualization.
 * Color-coded based on capacity thresholds.
 */

'use client';

import React from 'react';
import {
  ResponsiveContainer,
  RadialBarChart,
  RadialBar,
  PolarAngleAxis,
} from 'recharts';

/**
 * QueueGauge component props
 */
export interface QueueGaugeProps {
  queueDepth: number;
  maxCapacity?: number;
}

/**
 * Get color based on queue depth percentage
 */
function getGaugeColor(percentage: number): string {
  if (percentage > 75) return 'hsl(var(--destructive))'; // Red for >75%
  if (percentage > 50) return 'hsl(var(--warning))'; // Yellow for 50-75%
  return 'hsl(var(--success))'; // Green for <50%
}

/**
 * Circular gauge for queue depth visualization
 *
 * @example
 * ```tsx
 * <QueueGauge queueDepth={42} maxCapacity={200} />
 * ```
 */
export function QueueGauge({ queueDepth, maxCapacity = 200 }: QueueGaugeProps) {
  const percentage = Math.min((queueDepth / maxCapacity) * 100, 100);
  const color = getGaugeColor(percentage);

  const data = [{ name: 'Queue Depth', value: percentage }];

  return (
    <div className="relative">
      <ResponsiveContainer width="100%" height={250}>
        <RadialBarChart
          cx="50%"
          cy="50%"
          innerRadius="60%"
          outerRadius="80%"
          barSize={20}
          data={data}
          startAngle={180}
          endAngle={0}
        >
          <PolarAngleAxis
            type="number"
            domain={[0, 100]}
            angleAxisId={0}
            tick={false}
          />
          <RadialBar
            background
            dataKey="value"
            fill={color}
            cornerRadius={10}
            aria-label={`Queue depth at ${percentage.toFixed(0)}% capacity`}
          />
        </RadialBarChart>
      </ResponsiveContainer>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-4xl font-bold" style={{ color }}>
          {queueDepth}
        </span>
        <span className="text-sm text-muted-foreground">Jobs in Queue</span>
      </div>
    </div>
  );
}
