/**
 * Budget Utility Functions
 *
 * Helper functions for budget utilization calculations, formatting,
 * and color threshold logic used in the LLM Costs dashboard.
 *
 * Color Thresholds:
 * - Green (< 75%): Safe, on track
 * - Yellow (75-90%): High utilization, monitor closely
 * - Red (> 90%): Critical, immediate action needed
 * - Gray (null/0): No budget configured or no spend
 *
 * @module lib/utils/budget
 */

export type BudgetVariant = "success" | "warning" | "destructive" | "neutral";

export interface BudgetColorResult {
  color: string;
  variant: BudgetVariant;
}

/**
 * Determines the color and variant for a budget utilization percentage
 *
 * @param utilizationPercentage - The utilization percentage (0-100+), or null if no budget
 * @returns Object with Tailwind color class and variant name
 *
 * @example
 * ```ts
 * getBudgetColor(50) // { color: 'text-green-600', variant: 'success' }
 * getBudgetColor(80) // { color: 'text-yellow-600', variant: 'warning' }
 * getBudgetColor(95) // { color: 'text-red-600', variant: 'destructive' }
 * getBudgetColor(null) // { color: 'text-gray-500', variant: 'neutral' }
 * ```
 */
export function getBudgetColor(
  utilizationPercentage: number | null
): BudgetColorResult {
  // Handle null or zero budget cases
  if (utilizationPercentage === null || utilizationPercentage === 0) {
    return { color: "text-gray-500", variant: "neutral" };
  }

  // Apply color thresholds
  if (utilizationPercentage < 75) {
    return { color: "text-green-600", variant: "success" };
  } else if (utilizationPercentage < 90) {
    return { color: "text-yellow-600", variant: "warning" };
  } else {
    return { color: "text-red-600", variant: "destructive" };
  }
}

/**
 * Formats a number as USD currency with 2 decimal places
 *
 * @param amount - The amount in USD, or null if not set
 * @returns Formatted currency string (e.g., "$1,234.56", "$0.00")
 *
 * @example
 * ```ts
 * formatCurrency(1234.56) // "$1,234.56"
 * formatCurrency(0) // "$0.00"
 * formatCurrency(null) // "$0.00"
 * formatCurrency(123456.789) // "$123,456.79" (rounded)
 * ```
 */
export function formatCurrency(amount: number | null): string {
  if (amount === null || amount === 0) {
    return "$0.00";
  }

  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(amount);
}

/**
 * Calculates utilization percentage from spent and budget amounts
 *
 * @param spent - Amount spent in USD
 * @param budget - Budget amount in USD (null if not set)
 * @returns Utilization percentage (0-100+), or null if no budget
 *
 * @example
 * ```ts
 * calculateUtilization(750, 1000) // 75
 * calculateUtilization(1200, 1000) // 120 (over budget)
 * calculateUtilization(500, null) // null (no budget)
 * calculateUtilization(0, 1000) // 0
 * ```
 */
export function calculateUtilization(
  spent: number,
  budget: number | null
): number | null {
  if (budget === null || budget === 0) {
    return null;
  }

  return (spent / budget) * 100;
}

/**
 * Determines if a tenant is over budget
 *
 * @param spent - Amount spent in USD
 * @param budget - Budget amount in USD (null if not set)
 * @returns True if spent exceeds budget, false otherwise
 *
 * @example
 * ```ts
 * isOverBudget(1200, 1000) // true
 * isOverBudget(800, 1000) // false
 * isOverBudget(500, null) // false (no budget to exceed)
 * ```
 */
export function isOverBudget(spent: number, budget: number | null): boolean {
  if (budget === null || budget === 0) {
    return false;
  }

  return spent > budget;
}
