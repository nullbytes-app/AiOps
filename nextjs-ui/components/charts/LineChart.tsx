/**
 * LineChart Component
 *
 * Reusable Recharts LineChart with ResponsiveContainer.
 * Follows 2025 Recharts v3.3.0 best practices for accessibility and performance.
 */

'use client';

import React from 'react';
import {
  ResponsiveContainer,
  LineChart as RechartsLineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts';

/**
 * Line series configuration
 */
export interface LineSeries {
  dataKey: string;
  name: string;
  stroke: string;
  strokeWidth?: number;
  strokeDasharray?: string;
}

/**
 * LineChart component props
 */
export interface LineChartProps {
  data: Array<Record<string, unknown>>;
  lines: LineSeries[];
  xAxisKey: string;
  xAxisFormatter?: (value: unknown) => string;
  yAxisFormatter?: (value: unknown) => string;
  height?: number;
  ariaLabel?: string;
}

/**
 * Custom tooltip component for better UX
 */
interface CustomTooltipProps {
  active?: boolean;
  payload?: Array<{
    name: string;
    value: number;
    color: string;
    dataKey: string;
  }>;
  label?: string;
}

const CustomTooltip = ({ active, payload, label }: CustomTooltipProps) => {
  if (!active || !payload || payload.length === 0) {
    return null;
  }

  return (
    <div className="rounded-lg border border-border bg-card p-3 shadow-lg">
      <p className="text-sm font-medium text-foreground mb-2">{label}</p>
      {payload.map((entry, index) => (
        <div key={index} className="flex items-center gap-2 text-sm">
          <div
            className="w-3 h-3 rounded-full"
            style={{ backgroundColor: entry.color }}
          />
          <span className="text-muted-foreground">{entry.name}:</span>
          <span className="font-medium text-foreground">{entry.value}</span>
        </div>
      ))}
    </div>
  );
};

/**
 * Responsive Line Chart component
 *
 * @example
 * ```tsx
 * <LineChart
 *   data={chartData}
 *   lines={[
 *     { dataKey: 'success', name: 'Success', stroke: '#10b981' },
 *     { dataKey: 'failure', name: 'Failed', stroke: '#ef4444', strokeDasharray: '5 5' },
 *   ]}
 *   xAxisKey="hour"
 *   xAxisFormatter={(value) => new Date(value).toLocaleTimeString()}
 *   height={300}
 *   ariaLabel="Agent execution timeline showing success and failure trends"
 * />
 * ```
 */
export function LineChart({
  data,
  lines,
  xAxisKey,
  xAxisFormatter,
  yAxisFormatter,
  height = 300,
  ariaLabel,
}: LineChartProps) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <RechartsLineChart
        data={data}
        margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
        aria-label={ariaLabel}
      >
        <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--muted))" />
        <XAxis
          dataKey={xAxisKey}
          stroke="hsl(var(--foreground))"
          fontSize={12}
          tickFormatter={xAxisFormatter}
        />
        <YAxis
          stroke="hsl(var(--foreground))"
          fontSize={12}
          tickFormatter={yAxisFormatter}
        />
        <Tooltip content={<CustomTooltip />} />
        <Legend />
        {lines.map((line) => (
          <Line
            key={line.dataKey}
            type="monotone"
            dataKey={line.dataKey}
            name={line.name}
            stroke={line.stroke}
            strokeWidth={line.strokeWidth || 2}
            strokeDasharray={line.strokeDasharray}
            dot={{ r: 4 }}
            activeDot={{ r: 6 }}
          />
        ))}
      </RechartsLineChart>
    </ResponsiveContainer>
  );
}
