/**
 * Performance utility functions for agent metrics formatting
 * Following 2025 best practices for number formatting and color coding
 */

/**
 * Format execution time with appropriate unit (ms or s)
 * @param timeMs - Execution time in milliseconds
 * @returns Formatted string with unit (e.g., "450ms" or "2.34s")
 *
 * @example
 * formatExecutionTime(450) // "450ms"
 * formatExecutionTime(2345) // "2.35s"
 */
export function formatExecutionTime(timeMs: number): string {
  if (timeMs < 1000) {
    return `${Math.round(timeMs)}ms`;
  }
  return `${(timeMs / 1000).toFixed(2)}s`;
}

/**
 * Format large numbers with K/M notation
 * @param count - Number to format
 * @returns Formatted string with K/M suffix (e.g., "1.2K", "1.5M")
 *
 * @example
 * formatCount(450) // "450"
 * formatCount(1234) // "1.2K"
 * formatCount(1500000) // "1.5M"
 */
export function formatCount(count: number): string {
  if (count < 1000) {
    return count.toString();
  } else if (count < 1_000_000) {
    return `${(count / 1000).toFixed(1)}K`;
  } else {
    return `${(count / 1_000_000).toFixed(1)}M`;
  }
}

/**
 * Get color coding for success rate based on thresholds
 * @param rate - Success rate percentage (0-100)
 * @returns Object with Tailwind color class and variant
 *
 * @example
 * getSuccessRateColor(99) // { color: "text-green-600", variant: "success" }
 * getSuccessRateColor(90) // { color: "text-yellow-600", variant: "warning" }
 * getSuccessRateColor(80) // { color: "text-red-600", variant: "destructive" }
 */
export function getSuccessRateColor(rate: number): {
  color: string;
  variant: 'success' | 'warning' | 'destructive';
} {
  if (rate >= 95) {
    return { color: 'text-green-600', variant: 'success' };
  } else if (rate >= 85) {
    return { color: 'text-yellow-600', variant: 'warning' };
  } else {
    return { color: 'text-red-600', variant: 'destructive' };
  }
}

/**
 * Calculate date range presets for filtering
 * @param preset - Preset identifier ('last_7', 'last_30', or 'custom')
 * @returns Object with start and end dates in YYYY-MM-DD format
 *
 * @example
 * getDateRangePreset('last_7') // { start: "2025-01-14", end: "2025-01-21" }
 */
export function getDateRangePreset(preset: 'last_7' | 'last_30' | 'custom'): {
  start: string;
  end: string;
} {
  const end = new Date();
  const start = new Date();

  if (preset === 'last_7') {
    start.setDate(end.getDate() - 7);
  } else if (preset === 'last_30') {
    start.setDate(end.getDate() - 30);
  }

  return {
    start: start.toISOString().split('T')[0],  // YYYY-MM-DD
    end: end.toISOString().split('T')[0],
  };
}

/**
 * Get duration severity level based on thresholds (Story 16 AC #3)
 * @param durationMs - Duration in milliseconds
 * @returns Severity level: 'normal' (<30s), 'warning' (30-60s), 'slow' (>60s)
 *
 * @example
 * getDurationSeverity(25000) // "normal"
 * getDurationSeverity(45000) // "warning"
 * getDurationSeverity(75000) // "slow"
 */
export function getDurationSeverity(durationMs: number): 'normal' | 'warning' | 'slow' {
  const seconds = durationMs / 1000;
  if (seconds < 30) return 'normal';
  if (seconds <= 60) return 'warning';
  return 'slow';
}

/**
 * Get Tailwind color class for duration severity
 * @param severity - Severity level from getDurationSeverity
 * @returns Tailwind text color class
 */
export function getDurationColor(severity: 'normal' | 'warning' | 'slow'): string {
  switch (severity) {
    case 'normal':
      return 'text-foreground';
    case 'warning':
      return 'text-warning-600';
    case 'slow':
      return 'text-destructive';
  }
}

/**
 * Format execution time with appropriate unit (seconds or minutes+seconds)
 * Enhanced version for Story 16 (AC #1) to handle longer durations
 * @param durationMs - Duration in milliseconds
 * @returns Formatted string (e.g., "45.23s" or "2m 15s")
 *
 * @example
 * formatExecutionTimeLong(450) // "0.45s"
 * formatExecutionTimeLong(45230) // "45.23s"
 * formatExecutionTimeLong(145230) // "2m 25s"
 */
export function formatExecutionTimeLong(durationMs: number): string {
  const seconds = durationMs / 1000;

  if (seconds < 60) {
    return `${seconds.toFixed(2)}s`;
  }

  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = Math.floor(seconds % 60);
  return `${minutes}m ${remainingSeconds}s`;
}
