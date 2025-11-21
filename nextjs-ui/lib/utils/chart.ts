import { format } from 'date-fns';
import type { AgentTrendDataPoint } from '@/types/agent-performance';

/**
 * Format timestamp for chart X-axis based on granularity.
 *
 * @param timestamp - ISO 8601 timestamp
 * @param granularity - "hourly" or "daily"
 * @returns Formatted string ("MMM d, ha" for hourly, "MMM d" for daily)
 */
export function formatChartTimestamp(
  timestamp: string,
  granularity: 'hourly' | 'daily'
): string {
  const date = new Date(timestamp);

  if (granularity === 'hourly') {
    return format(date, 'MMM d, ha'); // "Jan 14, 2pm"
  } else {
    return format(date, 'MMM d'); // "Jan 14"
  }
}

/**
 * Format tooltip timestamp with full date/time.
 *
 * @param timestamp - ISO 8601 timestamp
 * @returns Full formatted string ("MMM d, yyyy h:mm a")
 */
export function formatTooltipTimestamp(timestamp: string): string {
  const date = new Date(timestamp);
  return format(date, 'MMM d, yyyy h:mm a'); // "Jan 14, 2025 2:00 PM"
}

/**
 * Auto-select granularity based on date range duration.
 *
 * @param startDate - ISO 8601 date (YYYY-MM-DD)
 * @param endDate - ISO 8601 date (YYYY-MM-DD)
 * @returns "hourly" if < 7 days, "daily" if >= 7 days
 */
export function autoSelectGranularity(
  startDate: string,
  endDate: string
): 'hourly' | 'daily' {
  const start = new Date(startDate);
  const end = new Date(endDate);
  const daysDiff = (end.getTime() - start.getTime()) / (1000 * 60 * 60 * 24);

  return daysDiff < 7 ? 'hourly' : 'daily';
}

/**
 * Transform trend data for Recharts (convert ms to seconds for readability).
 *
 * @param dataPoints - Raw API data points
 * @returns Transformed data with avg_execution_time_s field
 */
export function transformTrendData(dataPoints: AgentTrendDataPoint[]) {
  return dataPoints.map((point) => ({
    ...point,
    avg_execution_time_s: point.avg_execution_time_ms / 1000,
  }));
}
