/**
 * CustomTooltip Component
 *
 * Recharts custom tooltip displaying date, amount, and percentage delta.
 * Follows 2025 Recharts v3 best practices validated via Context7 MCP research.
 *
 * Maps to Story: nextjs-story-10-llm-cost-dashboard-trend-chart (AC#3)
 *
 * Research Notes:
 * - Context7 MCP: /recharts/recharts/v3.3.0 (93 snippets, Trust 8.7)
 * - Custom tooltip pattern validated for hover interactions
 */

import React from 'react';
import { format } from 'date-fns';
import { ChartDataPoint } from './DailySpendChart';

/**
 * Recharts tooltip payload type
 */
interface TooltipPayloadItem {
  value: number;
  payload: ChartDataPoint;
}

/**
 * Custom tooltip for daily spend trend chart
 *
 * Displays:
 * - Full date (e.g., "January 15, 2025")
 * - Exact amount (e.g., "$1,234.56")
 * - Percentage delta vs previous day with color coding
 *   - Green: cost decreased (good)
 *   - Red: cost increased (needs attention)
 *
 * @param active - True when tooltip is active (hovering)
 * @param payload - Array of data points being hovered
 */
export function CustomTooltip({ active, payload }: { active?: boolean; payload?: TooltipPayloadItem[] }) {
  // Don't render if not active or no data
  if (!active || !payload?.[0]) {
    return null;
  }

  // Extract chart data point from payload
  const data = payload[0].payload;

  return (
    <div className="bg-card border border-border rounded-lg shadow-lg p-3 min-w-[200px]">
      {/* Date (full format) */}
      <p className="text-sm font-semibold mb-1 text-foreground">
        {format(data.date, 'MMMM dd, yyyy')}
      </p>

      {/* Amount (exact USD) */}
      <p className="text-2xl font-bold text-foreground">
        {data.amountLabel}
      </p>

      {/* Delta (percentage change vs previous day) */}
      {data.deltaLabel && (
        <p
          className={`text-sm mt-1 font-medium ${
            data.deltaColor === 'red' ? 'text-destructive' : 'text-green-600'
          }`}
        >
          {data.deltaLabel} vs yesterday
        </p>
      )}
    </div>
  );
}
