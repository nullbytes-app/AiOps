/**
 * Formatting utilities for LLM Cost Dashboard
 * Handles currency, large numbers, and percentage formatting
 */

/**
 * Format number as currency with 2 decimal places
 * @param value - Number to format (USD amount)
 * @returns Formatted string like "$1,234.56"
 *
 * @example
 * formatCurrency(1234.56) // "$1,234.56"
 * formatCurrency(1234.5) // "$1,234.50"
 * formatCurrency(0) // "$0.00"
 */
export function formatCurrency(value: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
}

/**
 * Format large numbers with K/M notation
 * @param value - Number to format
 * @returns Formatted string like "1.2K", "1.2M", or "1,234" for values < 1000
 *
 * @example
 * formatLargeNumber(1234) // "1.2K"
 * formatLargeNumber(1234567) // "1.2M"
 * formatLargeNumber(999) // "999"
 * formatLargeNumber(1500) // "1.5K"
 */
export function formatLargeNumber(value: number): string {
  if (value < 1000) {
    return value.toLocaleString('en-US');
  }

  if (value < 1_000_000) {
    // Format as K (thousands)
    return (value / 1000).toFixed(1) + 'K';
  }

  // Format as M (millions)
  return (value / 1_000_000).toFixed(1) + 'M';
}

/**
 * Calculate and format percentage change
 * @param current - Current value
 * @param previous - Previous value for comparison
 * @returns Object with percentage value, formatted string, and direction icon
 *
 * @example
 * formatPercentageChange(115, 100) // { value: 15, formatted: "+15%", icon: "↑", isPositive: true }
 * formatPercentageChange(90, 100) // { value: -10, formatted: "-10%", icon: "↓", isPositive: false }
 * formatPercentageChange(100, 100) // { value: 0, formatted: "0%", icon: "→", isPositive: null }
 * formatPercentageChange(100, 0) // { value: 0, formatted: "N/A", icon: "→", isPositive: null }
 */
export function formatPercentageChange(
  current: number,
  previous: number
): {
  value: number;
  formatted: string;
  icon: string;
  isPositive: boolean | null; // null for zero change
} {
  // Handle edge case: division by zero
  if (previous === 0) {
    return {
      value: 0,
      formatted: 'N/A',
      icon: '→',
      isPositive: null,
    };
  }

  const percentChange = ((current - previous) / previous) * 100;

  let icon: string;
  let isPositive: boolean | null;

  if (percentChange > 0) {
    icon = '↑';
    isPositive = true;
  } else if (percentChange < 0) {
    icon = '↓';
    isPositive = false;
  } else {
    icon = '→';
    isPositive = null;
  }

  // Format with + or - prefix (no prefix for zero)
  const sign = percentChange > 0 ? '+' : '';
  const formatted = `${sign}${Math.abs(percentChange).toFixed(1)}%`;

  return {
    value: percentChange,
    formatted,
    icon,
    isPositive,
  };
}

/**
 * Format a simple percentage value (0-100 scale)
 * @param value - Percentage value (0-100)
 * @returns Formatted string like "85.5%"
 *
 * @example
 * formatPercentage(85.5) // "85.5%"
 * formatPercentage(100) // "100.0%"
 * formatPercentage(0) // "0.0%"
 */
export function formatPercentage(value: number): string {
  return `${value.toFixed(1)}%`;
}
