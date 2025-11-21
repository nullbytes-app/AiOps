"use client";

import { Progress } from "@/components/ui/Progress";
import { cn } from "@/lib/utils/cn";
import { getBudgetColor, formatCurrency } from "@/lib/utils/budget";

interface BudgetProgressBarProps {
  /** Utilization percentage (0-100+) */
  utilized: number;

  /** Budget amount in USD (null if not configured) */
  budget: number | null;

  /** Amount spent in USD */
  spent: number;

  /** Optional custom className for the root container */
  className?: string;
}

/**
 * BudgetProgressBar Component
 *
 * Visual progress bar showing budget utilization with color-coded thresholds:
 * - Green (< 75%): Safe, on track
 * - Yellow (75-90%): High utilization, monitor closely
 * - Red (> 90%): Critical, immediate action needed
 * - Gray (null/0): No budget configured
 *
 * Displays over-budget indicator (⚠️) when spending exceeds 100% of budget.
 * Caps visual progress at 100% to prevent UI overflow.
 *
 * @param utilized - Utilization percentage (0-100+)
 * @param budget - Budget amount in USD, or null if not configured
 * @param spent - Amount spent in USD
 * @param className - Optional custom classes for root container
 *
 * @example
 * ```tsx
 * // On track (50% utilization)
 * <BudgetProgressBar utilized={50} budget={1000} spent={500} />
 *
 * // High utilization (80%)
 * <BudgetProgressBar utilized={80} budget={5000} spent={4000} />
 *
 * // Over budget (120%)
 * <BudgetProgressBar utilized={120} budget={1000} spent={1200} />
 *
 * // No budget configured
 * <BudgetProgressBar utilized={0} budget={null} spent={500} />
 * ```
 */
export function BudgetProgressBar({
  utilized,
  budget,
  spent,
  className,
}: BudgetProgressBarProps) {
  const { color, variant } = getBudgetColor(utilized);

  // Cap visual progress at 100% (but show >100% in label)
  const visualProgress = Math.min(utilized, 100);

  return (
    <div className={cn("space-y-1", className)}>
      {/* Utilization percentage label with color coding */}
      <div className="flex justify-between items-center text-sm">
        <span className={cn("font-medium", color)}>
          {utilized.toFixed(1)}% utilized
        </span>

        {/* Over budget indicator */}
        {utilized > 100 && (
          <span className="text-red-600 font-semibold flex items-center gap-1">
            ⚠️ Over budget!
          </span>
        )}
      </div>

      {/* Progress bar with color-coded indicator */}
      <Progress
        value={visualProgress}
        className="h-2"
        indicatorClassName={cn(
          variant === "success" && "bg-green-500",
          variant === "warning" && "bg-yellow-500",
          variant === "destructive" && "bg-red-500",
          variant === "neutral" && "bg-gray-300"
        )}
        aria-label={`Budget utilization: ${utilized.toFixed(1)}%`}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={Math.min(utilized, 100)}
      />

      {/* Spent / Budget amounts */}
      {budget !== null ? (
        <div className="flex justify-between text-xs text-muted-foreground">
          <span>Spent: {formatCurrency(spent)}</span>
          <span>Budget: {formatCurrency(budget)}</span>
        </div>
      ) : (
        <p className="text-xs text-muted-foreground italic">
          No budget configured
        </p>
      )}
    </div>
  );
}
