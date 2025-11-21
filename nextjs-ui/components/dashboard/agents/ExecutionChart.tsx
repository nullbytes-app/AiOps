/**
 * ExecutionChart Component
 *
 * Line chart showing agent execution timeline with success/failure breakdown.
 * Uses Recharts v3.3.0 with 2025 best practices for performance and accessibility.
 */

'use client';

import React from 'react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts';

export interface ExecutionChartData {
  hour: string;
  success: number;
  failure: number;
}

export interface ExecutionChartProps {
  data: ExecutionChartData[];
  className?: string;
}

/**
 * Custom Tooltip Component
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

function CustomTooltip({ active, payload, label }: CustomTooltipProps) {
  if (!active || !payload || payload.length === 0 || !label) return null;

  const date = new Date(label);
  const formattedDate = date.toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });

  return (
    <div className="glass-card p-4 border border-border rounded-lg shadow-lg">
      <p className="text-sm font-medium text-foreground mb-2">{formattedDate}</p>
      <div className="space-y-1">
        {payload.map((entry, index) => (
          <div key={`tooltip-${index}`} className="flex items-center gap-2">
            <div
              className="w-3 h-3 rounded-full"
              style={{ backgroundColor: entry.color }}
            />
            <span className="text-sm text-muted-foreground capitalize">
              {entry.name}:
            </span>
            <span className="text-sm font-semibold text-foreground">
              {entry.value}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

/**
 * Format X-axis tick to show hour only
 */
function formatXAxis(timestamp: string): string {
  const date = new Date(timestamp);
  return date.toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  });
}

/**
 * ExecutionChart Component
 *
 * Displays agent execution timeline with success and failure trends.
 * Auto-updates when parent component refreshes data.
 *
 * @example
 * ```tsx
 * const { data } = useAgentMetrics('24h');
 *
 * <ExecutionChart data={data.chartData} />
 * ```
 */
export function ExecutionChart({ data, className = '' }: ExecutionChartProps) {
  return (
    <div className={`glass-card p-6 ${className}`}>
      <h3 className="text-lg font-semibold text-foreground mb-4">
        Execution Timeline (Last 24 Hours)
      </h3>

      <ResponsiveContainer width="100%" height={300}>
        <LineChart
          data={data}
          margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
          aria-label="Agent execution timeline showing success and failure trends over the last 24 hours"
        >
          <CartesianGrid
            strokeDasharray="3 3"
            stroke="hsl(var(--muted))"
            opacity={0.3}
          />
          <XAxis
            dataKey="hour"
            stroke="hsl(var(--muted-foreground))"
            fontSize={12}
            tickFormatter={formatXAxis}
            tick={{ fill: 'hsl(var(--muted-foreground))' }}
          />
          <YAxis
            stroke="hsl(var(--muted-foreground))"
            fontSize={12}
            tick={{ fill: 'hsl(var(--muted-foreground))' }}
          />
          <Tooltip content={<CustomTooltip />} />
          <Legend
            wrapperStyle={{
              paddingTop: '20px',
              fontSize: '14px',
              color: 'hsl(var(--foreground))',
            }}
          />
          <Line
            type="monotone"
            dataKey="success"
            name="Successful"
            stroke="hsl(142, 76%, 36%)"
            strokeWidth={2}
            dot={{ r: 4, fill: 'hsl(142, 76%, 36%)' }}
            activeDot={{ r: 6 }}
            isAnimationActive={true}
            animationDuration={500}
          />
          <Line
            type="monotone"
            dataKey="failure"
            name="Failed"
            stroke="hsl(0, 84%, 60%)"
            strokeWidth={2}
            dot={{ r: 4, fill: 'hsl(0, 84%, 60%)' }}
            activeDot={{ r: 6 }}
            isAnimationActive={true}
            animationDuration={500}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
