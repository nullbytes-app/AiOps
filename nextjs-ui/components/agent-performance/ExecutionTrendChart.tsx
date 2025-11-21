'use client';

import { useState } from 'react';
import {
  ComposedChart,
  Bar,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { useAgentTrends } from '@/hooks/useAgentTrends';
import { GranularityToggle } from './GranularityToggle';
import {
  formatChartTimestamp,
  formatTooltipTimestamp,
  transformTrendData,
} from '@/lib/utils/chart';
import { formatExecutionTime } from '@/lib/utils/performance';
import { Skeleton } from '@/components/ui/skeleton';
import { Button } from '@/components/ui/button';

interface ExecutionTrendChartProps {
  agentId: string | null;
  startDate: string;
  endDate: string;
  defaultGranularity: 'hourly' | 'daily';
}

/**
 * Execution Trend Chart - Dual-axis chart showing execution count (bars) and avg execution time (line).
 */
export function ExecutionTrendChart({
  agentId,
  startDate,
  endDate,
  defaultGranularity,
}: ExecutionTrendChartProps) {
  const [granularity, setGranularity] = useState(defaultGranularity);
  const [hiddenSeries, setHiddenSeries] = useState<Set<string>>(new Set());

  const { data, isLoading, error, refetch } = useAgentTrends({
    agentId,
    startDate,
    endDate,
    granularity,
  });

  if (isLoading) {
    return <Skeleton className="h-[400px] w-full rounded-md" />;
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-[400px] border rounded-md bg-muted/50">
        <p className="text-sm text-destructive mb-4">
          Failed to load execution trends
        </p>
        <Button size="sm" onClick={() => refetch()}>
          Retry
        </Button>
      </div>
    );
  }

  if (!data || data.data_points.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-[400px] border rounded-md bg-muted/50">
        <p className="text-sm text-muted-foreground mb-2">
          No execution data available for the selected date range
        </p>
        <p className="text-xs text-muted-foreground">
          Try selecting a different date range or agent
        </p>
      </div>
    );
  }

  const chartData = transformTrendData(data.data_points);

  const toggleSeries = (seriesName: string) => {
    setHiddenSeries((prev) => {
      const next = new Set(prev);
      const totalSeries = 2; // execution_count + avg_execution_time_s

      if (next.has(seriesName)) {
        // Always allow unhiding
        next.delete(seriesName);
      } else {
        // Only hide if at least one series will remain visible
        if (next.size < totalSeries - 1) {
          next.add(seriesName);
        }
        // When next.size === 1 (one hidden), prevent hiding the last visible one
      }
      return next;
    });
  };

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h3 className="text-lg font-semibold">Execution Trends</h3>
        <GranularityToggle value={granularity} onChange={setGranularity} />
      </div>

      <ResponsiveContainer width="100%" height={400}>
        <ComposedChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
          <XAxis
            dataKey="timestamp"
            tickFormatter={(value) => formatChartTimestamp(value, granularity)}
            angle={-45}
            textAnchor="end"
            height={80}
          />
          <YAxis
            yAxisId="left"
            label={{
              value: 'Execution Count',
              angle: -90,
              position: 'insideLeft',
            }}
          />
          <YAxis
            yAxisId="right"
            orientation="right"
            label={{
              value: 'Avg Time (s)',
              angle: 90,
              position: 'insideRight',
            }}
          />
          <Tooltip
            content={({ active, payload }) => {
              if (!active || !payload || payload.length === 0) return null;

              return (
                <div className="bg-background border rounded-md p-3 shadow-md">
                  <p className="font-semibold text-sm mb-2">
                    {formatTooltipTimestamp(payload[0].payload.timestamp)}
                  </p>
                  <p className="text-xs text-blue-600">
                    Executions: {payload[0].value}
                  </p>
                  <p className="text-xs text-green-600">
                    Avg Time:{' '}
                    {formatExecutionTime(
                      (payload[1]?.value as number) * 1000 || 0
                    )}
                  </p>
                </div>
              );
            }}
          />
          <Legend
            onClick={(e) => toggleSeries(e.dataKey as string)}
            wrapperStyle={{ cursor: 'pointer' }}
          />
          {!hiddenSeries.has('execution_count') && (
            <Bar
              yAxisId="left"
              dataKey="execution_count"
              fill="hsl(var(--chart-1))"
              name="Execution Count"
              radius={[4, 4, 0, 0]}
            />
          )}
          {!hiddenSeries.has('avg_execution_time_s') && (
            <Line
              yAxisId="right"
              type="monotone"
              dataKey="avg_execution_time_s"
              stroke="hsl(var(--chart-2))"
              strokeWidth={2}
              name="Avg Execution Time"
              dot={false}
            />
          )}
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
