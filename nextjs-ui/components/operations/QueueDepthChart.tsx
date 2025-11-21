/**
 * Queue Depth Chart Component
 *
 * Recharts LineChart showing queue depth over last 60 minutes.
 * - Real-time updates (10-second refresh)
 * - Responsive design with ResponsiveContainer
 * - X-axis: Time (HH:MM format, 5-minute intervals)
 * - Y-axis: Queue depth (tasks)
 * - Collapses to sparkline on mobile
 *
 * Reference: Story 5, AC-1
 * Recharts v3.3.0 best practices from Context7
 */

'use client';

import { useQueueDepthHistory } from '@/lib/hooks/useQueue';
import { format, parseISO } from 'date-fns';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { Loader2 } from 'lucide-react';

/**
 * Format timestamp for X-axis labels (HH:MM)
 */
const formatTime = (timestamp: string): string => {
  try {
    return format(parseISO(timestamp), 'HH:mm');
  } catch {
    return '';
  }
};

/**
 * Custom tooltip for chart
 */
interface TooltipProps {
  active?: boolean;
  payload?: Array<{
    value: number;
    payload: { timestamp: string };
  }>;
}

const CustomTooltip = ({ active, payload }: TooltipProps) => {
  if (!active || !payload || !payload.length) {
    return null;
  }

  const data = payload[0];
  return (
    <div className="glass-card p-3 shadow-lg">
      <p className="text-xs text-text-secondary mb-1">
        {format(parseISO(data.payload.timestamp), 'HH:mm:ss')}
      </p>
      <p className="text-sm font-semibold text-text-primary">
        {data.value} tasks
      </p>
    </div>
  );
};

export function QueueDepthChart() {
  const { data: history, isLoading, error } = useQueueDepthHistory(60);

  if (isLoading) {
    return (
      <div className="glass-card p-6 h-80 flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-text-secondary" />
      </div>
    );
  }

  if (error || !history || history.length === 0) {
    return (
      <div className="glass-card p-6 h-80 flex items-center justify-center">
        <p className="text-sm text-text-secondary">
          {error ? 'Failed to load chart data' : 'No data available'}
        </p>
      </div>
    );
  }

  return (
    <div className="glass-card p-6">
      <h3 className="text-h4 font-semibold text-text-primary mb-4">
        Queue Depth (Last 60 Minutes)
      </h3>
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart
            data={history}
            margin={{ top: 5, right: 30, left: 10, bottom: 5 }}
            accessibilityLayer
          >
            <CartesianGrid stroke="#e5e7eb" strokeDasharray="3 3" opacity={0.3} />
            <XAxis
              dataKey="timestamp"
              tickFormatter={formatTime}
              stroke="#6b7280"
              style={{ fontSize: '12px' }}
              interval="preserveStartEnd"
              minTickGap={50}
            />
            <YAxis
              stroke="#6b7280"
              style={{ fontSize: '12px' }}
              label={{
                value: 'Tasks',
                angle: -90,
                position: 'insideLeft',
                style: { fontSize: '12px', fill: '#6b7280' },
              }}
            />
            <Tooltip content={<CustomTooltip />} />
            <Line
              type="monotone"
              dataKey="depth"
              stroke="#3b82f6"
              strokeWidth={2}
              dot={{ r: 3, fill: '#3b82f6' }}
              activeDot={{ r: 5, fill: '#2563eb' }}
              isAnimationActive={true}
              animationDuration={500}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
