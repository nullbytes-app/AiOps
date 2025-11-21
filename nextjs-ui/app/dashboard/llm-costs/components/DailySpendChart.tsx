/**
 * DailySpendChart Component
 *
 * Recharts area chart displaying 30 days of daily LLM cost trend data.
 * Follows 2025 Recharts v3 + Next.js 14 best practices validated via Context7 MCP research.
 *
 * Maps to Story: nextjs-story-10-llm-cost-dashboard-trend-chart
 * Backend API: GET /api/v1/costs/trend?days=30
 *
 * Research Notes:
 * - Context7 MCP: /recharts/recharts/v3.3.0 (93 snippets, Trust 8.7)
 * - ResponsiveContainer with SSR support (initialDimension prop)
 * - Gradient fill pattern for professional appearance
 * - Custom tooltip with delta calculations
 */

'use client';

import React, { useRef, useState } from 'react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from 'recharts';
import { parseISO, format } from 'date-fns';
import { DailySpendDTO } from '@/types/costs';
import { CustomTooltip } from './CustomTooltip';
import { Button } from '@/components/ui/Button';
import { Download, AlertCircle, BarChart3 } from 'lucide-react';
import { exportChartAsPNG } from '@/lib/chartExport';

/**
 * Transformed data structure optimized for Recharts rendering
 * Includes calculated fields for delta and formatted labels
 */
export interface ChartDataPoint {
  /** JavaScript Date object for Recharts date axis */
  date: Date;
  /** Formatted date label for X-axis (e.g., "01/15") */
  dateLabel: string;
  /** Raw USD amount */
  amount: number;
  /** Formatted amount for tooltip (e.g., "$1,234.56") */
  amountLabel: string;
  /** Percentage change from previous day (null for first day) */
  delta: number | null;
  /** Formatted delta with arrow (e.g., "↑ 15.2%" or "↓ 8.5%") */
  deltaLabel: string | null;
  /** Color for delta text: 'green' for decrease, 'red' for increase */
  deltaColor: 'green' | 'red' | null;
}

/**
 * DailySpendChart Props
 */
interface DailySpendChartProps {
  /** Daily spend data from API */
  data?: DailySpendDTO[];
  /** Loading state */
  loading?: boolean;
  /** Error state (AC#10) */
  error?: Error | null;
  /** Retry callback for error state (AC#10) */
  onRetry?: () => void;
  /** Optional CSS class */
  className?: string;
}

/**
 * Format full currency with 2 decimal places
 * @example formatCurrency(1234.56) // "$1,234.56"
 */
function formatCurrency(amount: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(amount);
}

/**
 * Format compact currency for Y-axis (e.g., "$1.2K", "$1.5M")
 * @example formatCompactCurrency(1234) // "$1.2K"
 * @example formatCompactCurrency(1500000) // "$1.5M"
 */
function formatCompactCurrency(amount: number): string {
  if (amount >= 1_000_000) {
    return `$${(amount / 1_000_000).toFixed(1)}M`;
  } else if (amount >= 1_000) {
    return `$${(amount / 1_000).toFixed(1)}K`;
  } else {
    return `$${amount.toFixed(0)}`;
  }
}

/**
 * Transform API response to chart-ready format with delta calculations
 */
function transformToChartData(apiData: DailySpendDTO[]): ChartDataPoint[] {
  return apiData.map((item, index) => {
    const date = parseISO(item.date); // Convert ISO string to Date
    const prevAmount = index > 0 ? apiData[index - 1].total_spend : null;
    const delta = prevAmount
      ? ((item.total_spend - prevAmount) / prevAmount) * 100
      : null;

    return {
      date,
      dateLabel: format(date, 'MM/dd'),
      amount: item.total_spend,
      amountLabel: formatCurrency(item.total_spend),
      delta,
      deltaLabel:
        delta !== null
          ? `${delta >= 0 ? '↑' : '↓'} ${Math.abs(delta).toFixed(1)}%`
          : null,
      deltaColor: delta !== null ? (delta >= 0 ? 'red' : 'green') : null,
    };
  });
}

/**
 * Loading Skeleton Component (AC#8)
 */
function ChartSkeleton() {
  return (
    <div className="animate-pulse space-y-4" role="status" aria-label="Loading chart data">
      <div className="h-6 bg-muted/50 rounded w-64" />
      <div className="h-[300px] bg-muted/50 rounded" />
      <span className="sr-only">Loading chart data...</span>
    </div>
  );
}

/**
 * Empty State Component
 */
function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center py-16">
      <BarChart3 className="h-16 w-16 text-muted-foreground/50 mb-4" />
      <p className="text-lg font-semibold text-foreground mb-1">
        No cost data available for the last 30 days
      </p>
      <p className="text-sm text-muted-foreground">
        Data will appear once LLM usage is recorded
      </p>
    </div>
  );
}

/**
 * Error State Component with Retry Button (AC#10)
 */
function ErrorState({
  message,
  onRetry,
}: {
  message?: string;
  onRetry?: () => void;
}) {
  return (
    <div className="flex flex-col items-center justify-center py-16">
      <AlertCircle className="h-16 w-16 text-destructive mb-4" />
      <p className="text-lg font-semibold text-foreground mb-1">
        Unable to load cost trend data
      </p>
      {message && (
        <p className="text-sm text-muted-foreground font-mono mb-4">{message}</p>
      )}
      {onRetry && (
        <Button variant="secondary" size="sm" onClick={onRetry}>
          Retry
        </Button>
      )}
    </div>
  );
}

/**
 * Daily Spend Trend Chart Component
 *
 * Features (Story AC#1-AC#11):
 * - Responsive area chart with gradient fill
 * - 30 days of daily cost data
 * - Interactive tooltip with delta calculations
 * - Export to PNG functionality
 * - Loading, empty, and error states
 * - Responsive layout (mobile, tablet, desktop)
 * - Auto-scaled currency formatting
 * - Smooth curves and visual polish
 */
export function DailySpendChart({
  data,
  loading = false,
  error = null,
  onRetry,
  className = '',
}: DailySpendChartProps) {
  const chartRef = useRef<HTMLDivElement>(null);
  const [isExporting, setIsExporting] = useState(false);

  // Show loading skeleton (AC#8)
  if (loading) {
    return (
      <div className={`bg-card rounded-lg border border-border p-6 ${className}`}>
        <ChartSkeleton />
      </div>
    );
  }

  // Show error state if API call failed (AC#10)
  if (error) {
    return (
      <div className={`bg-card rounded-lg border border-border p-6 ${className}`}>
        <ErrorState message={error.message} onRetry={onRetry} />
      </div>
    );
  }

  // Show empty state if no data (AC#9)
  if (!data || data.length === 0) {
    return (
      <div className={`bg-card rounded-lg border border-border p-6 ${className}`}>
        <EmptyState />
      </div>
    );
  }

  // Transform data for chart
  const chartData = transformToChartData(data);

  // Handle export button click (AC#4)
  const handleExport = async () => {
    setIsExporting(true);
    try {
      await exportChartAsPNG(chartRef);
    } catch (error) {
      console.error('Export failed:', error);
      // TODO: Show toast notification for export error
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <div
      className={`bg-card rounded-lg border border-border p-6 ${className}`}
      ref={chartRef}
    >
      {/* Section Header with Export Button */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-xl font-bold text-foreground">
            Daily Spend Trend (Last 30 Days)
          </h2>
          <p className="text-sm text-muted-foreground mt-1">
            {format(chartData[0].date, 'MMM dd')} -{' '}
            {format(chartData[chartData.length - 1].date, 'MMM dd, yyyy')}
          </p>
        </div>

        {/* Export Button (AC#4) - Hidden on mobile, icon-only on tablet, full on desktop */}
        <Button
          variant="secondary"
          size="sm"
          onClick={handleExport}
          disabled={isExporting}
          className="gap-2"
          data-export-hide
          aria-label="Export chart as PNG"
        >
          <Download className="h-4 w-4" />
          <span className="hidden sm:inline">{isExporting ? 'Exporting...' : 'Export as PNG'}</span>
        </Button>
      </div>

      {/* Recharts Area Chart (AC#1-AC#7, AC#11) */}
      <ResponsiveContainer
        width="100%"
        height={300}
        initialDimension={{ width: 800, height: 300 }} // SSR fallback for Next.js
        debounce={300} // Optimize resize performance (AC#11)
      >
        <AreaChart
          data={chartData}
          margin={{ top: 10, right: 10, left: 0, bottom: 0 }}
        >
          {/* Gradient Fill Definition (AC#1) */}
          <defs>
            <linearGradient id="costGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="hsl(var(--accent-blue))" stopOpacity={0.3} />
              <stop offset="95%" stopColor="hsl(var(--accent-blue))" stopOpacity={0} />
            </linearGradient>
          </defs>

          {/* Grid */}
          <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />

          {/* X-Axis (AC#1) */}
          <XAxis
            dataKey="dateLabel"
            stroke="hsl(var(--muted-foreground))"
            tick={{ fontSize: 12 }}
            tickLine={false}
            axisLine={false}
          />

          {/* Y-Axis (AC#1) */}
          <YAxis
            tickFormatter={formatCompactCurrency}
            stroke="hsl(var(--muted-foreground))"
            tick={{ fontSize: 12 }}
            tickLine={false}
            axisLine={false}
            width={60}
          />

          {/* Tooltip (AC#3) */}
          <Tooltip
            content={<CustomTooltip />}
            cursor={{ stroke: 'hsl(var(--muted-foreground))', strokeWidth: 1, strokeDasharray: '5 5' }}
          />

          {/* Area (AC#1, AC#2) */}
          <Area
            type="monotone"
            dataKey="amount"
            stroke="hsl(var(--accent-blue))"
            fill="url(#costGradient)"
            strokeWidth={2}
            dot={{ fill: 'hsl(var(--accent-blue))', strokeWidth: 0, r: 3 }}
            activeDot={{ r: 5 }}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
