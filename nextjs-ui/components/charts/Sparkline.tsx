/**
 * Sparkline Component
 *
 * Mini trend chart for compact visualization.
 * Optimized for performance with reduced data points (<50).
 */

'use client';

import React from 'react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
} from 'recharts';

/**
 * Sparkline component props
 */
export interface SparklineProps {
  data: Array<{ value: number }>;
  stroke?: string;
  fill?: string;
  height?: number;
}

/**
 * Compact sparkline chart for showing trends
 *
 * @example
 * ```tsx
 * <Sparkline
 *   data={last12Hours.map(h => ({ value: h.processed }))}
 *   stroke="hsl(var(--success))"
 *   fill="hsl(var(--success) / 0.2)"
 *   height={40}
 * />
 * ```
 */
export function Sparkline({
  data,
  stroke = 'hsl(var(--primary))',
  fill = 'hsl(var(--primary) / 0.2)',
  height = 40,
}: SparklineProps) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={data} margin={{ top: 0, right: 0, left: 0, bottom: 0 }}>
        <Area
          type="monotone"
          dataKey="value"
          stroke={stroke}
          strokeWidth={2}
          fill={fill}
          isAnimationActive={false} // Disable animation for performance
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}
