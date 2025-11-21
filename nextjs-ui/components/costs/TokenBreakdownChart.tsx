/**
 * TokenBreakdownChart Component
 *
 * Pie/Donut chart visualization for token usage breakdown by type (input/output).
 * Uses Recharts PieChart with responsive container, custom tooltip, and center label.
 *
 * AC#1: Shows pie/donut chart with input tokens (percentage + count), output tokens (percentage + count),
 * total tokens (center of donut), color-coded slices (design system), hover tooltip
 */

'use client';

import React from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts';
import { TokenBreakdownWithPercentage } from '@/types/costs';
import { formatLargeNumber, formatCurrency } from '@/lib/formatters';

export interface TokenBreakdownChartProps {
  /** Token breakdown data with percentages */
  data: TokenBreakdownWithPercentage[];
  /** Show loading skeleton */
  loading?: boolean;
  /** Custom CSS classes */
  className?: string;
}

/**
 * Color palette for token types (from design system)
 * Input tokens: #3B82F6 (blue)
 * Output tokens: #10B981 (green)
 */
const COLORS: Record<string, string> = {
  input: '#3B82F6',
  output: '#10B981',
};

/**
 * Chart data format for Recharts
 */
interface ChartDataPoint {
  name: string; // 'Input Tokens' | 'Output Tokens'
  value: number; // Token count
  percentage: number; // Calculated percentage
  cost: number; // USD cost
  tokenType: 'input' | 'output';
  [key: string]: string | number; // Index signature for Recharts compatibility
}

/**
 * Transform API data to Recharts format
 */
function transformData(data: TokenBreakdownWithPercentage[]): ChartDataPoint[] {
  return data.map((item) => ({
    name: item.tokenType === 'input' ? 'Input Tokens' : 'Output Tokens',
    value: item.count,
    percentage: item.percentage,
    cost: item.cost,
    tokenType: item.tokenType,
  }));
}

/**
 * Custom Tooltip Component
 * Shows token type, count, percentage on hover
 */
function CustomTooltip({ active, payload }: { active?: boolean; payload?: { payload: ChartDataPoint }[] }) {
  if (!active || !payload || payload.length === 0) {
    return null;
  }

  const data = payload[0].payload;

  return (
    <div className="bg-white/90 backdrop-blur-sm p-3 rounded-lg shadow-lg border border-gray-200">
      <p className="font-semibold text-foreground mb-1">{data.name}</p>
      <p className="text-sm text-muted-foreground">
        Count: {formatLargeNumber(data.value)}
      </p>
      <p className="text-sm text-muted-foreground">
        Percentage: {data.percentage.toFixed(2)}%
      </p>
      <p className="text-sm text-muted-foreground">
        Cost: {formatCurrency(data.cost)}
      </p>
    </div>
  );
}

/**
 * Loading Skeleton Component
 */
function LoadingSkeleton() {
  return (
    <div className="flex items-center justify-center" style={{ height: 300 }}>
      <div className="animate-pulse space-y-4">
        <div className="h-48 w-48 bg-muted/50 rounded-full mx-auto" />
        <div className="h-6 w-32 bg-muted/50 rounded mx-auto" />
      </div>
    </div>
  );
}

/**
 * Empty State Component
 * Shown when no token data is available
 */
function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center text-center py-12">
      <div className="h-16 w-16 rounded-full bg-muted/50 flex items-center justify-center mb-4">
        <svg
          className="h-8 w-8 text-muted-foreground"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
          />
        </svg>
      </div>
      <h3 className="text-lg font-semibold text-foreground mb-1">
        No Token Usage Data
      </h3>
      <p className="text-sm text-muted-foreground max-w-sm">
        No token usage data available for the selected date range. Try selecting a different date range.
      </p>
    </div>
  );
}

/**
 * TokenBreakdownChart Component
 *
 * Features:
 * - Donut chart with 60% inner radius (AC#1)
 * - Color-coded slices: input=blue, output=green (AC#1)
 * - Hover tooltip with token type, count, percentage (AC#1)
 * - Center label showing total tokens (AC#1)
 * - Responsive container (min-height 300px) (Constraint #7)
 * - Loading skeleton matching component dimensions
 * - Empty state for zero tokens
 *
 * @example
 * ```tsx
 * function TokenBreakdownSection() {
 *   const { data, isLoading } = useTokenBreakdown(startDate, endDate);
 *
 *   return <TokenBreakdownChart data={data || []} loading={isLoading} />;
 * }
 * ```
 */
export function TokenBreakdownChart({
  data,
  loading = false,
  className,
}: TokenBreakdownChartProps) {
  // Show loading skeleton
  if (loading) {
    return (
      <div className={`p-6 bg-white/75 backdrop-blur-[32px] rounded-[24px] shadow-lg border border-white/20 ${className || ''}`}>
        <LoadingSkeleton />
      </div>
    );
  }

  // Calculate total tokens for center label
  const totalTokens = data.reduce((sum, item) => sum + item.count, 0);

  // Show empty state if no data
  if (!data || data.length === 0 || totalTokens === 0) {
    return (
      <div className={`p-6 bg-white/75 backdrop-blur-[32px] rounded-[24px] shadow-lg border border-white/20 ${className || ''}`}>
        <EmptyState />
      </div>
    );
  }

  // Transform data for chart
  const chartData = transformData(data);

  return (
    <div className={`p-6 bg-white/75 backdrop-blur-[32px] rounded-[24px] shadow-lg border border-white/20 ${className || ''}`}>
      <h3 className="text-lg font-semibold text-foreground mb-4">
        Token Breakdown by Type
      </h3>

      <ResponsiveContainer width="100%" height={300}>
        <PieChart>
          <Pie
            data={chartData}
            cx="50%"
            cy="50%"
            innerRadius="60%"
            outerRadius="80%"
            fill="#8884d8"
            dataKey="value"
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            label={(props: any) => `${((props.percent || 0) * 100).toFixed(1)}%`}
            labelLine={false}
          >
            {chartData.map((entry, index) => (
              <Cell
                key={`cell-${index}`}
                fill={COLORS[entry.tokenType]}
              />
            ))}
          </Pie>
          <Tooltip content={<CustomTooltip />} />

          {/* Center Label: Total Tokens */}
          <text
            x="50%"
            y="50%"
            textAnchor="middle"
            dominantBaseline="middle"
            style={{ pointerEvents: 'none' }}
          >
            <tspan
              x="50%"
              dy="-0.5em"
              fontSize="24"
              fontWeight="bold"
              fill="hsl(var(--foreground))"
            >
              {formatLargeNumber(totalTokens)}
            </tspan>
            <tspan
              x="50%"
              dy="1.5em"
              fontSize="14"
              fill="hsl(var(--muted-foreground))"
            >
              Total Tokens
            </tspan>
          </text>
        </PieChart>
      </ResponsiveContainer>

      {/* Legend */}
      <div className="flex items-center justify-center gap-6 mt-4">
        {chartData.map((item) => (
          <div key={item.tokenType} className="flex items-center gap-2">
            <div
              className="h-3 w-3 rounded-full"
              style={{ backgroundColor: COLORS[item.tokenType] }}
            />
            <span className="text-sm text-muted-foreground">{item.name}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
