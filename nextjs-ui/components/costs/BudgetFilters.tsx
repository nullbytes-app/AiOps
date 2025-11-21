"use client";

import { Select } from "@/components/ui/Select";
import type { BudgetFilter, BudgetSortBy } from "@/types/costs";

interface BudgetFiltersProps {
  /** Current filter value */
  filter: BudgetFilter;

  /** Current sort value */
  sortBy: BudgetSortBy;

  /** Total number of items matching current filter */
  itemCount: number;

  /** Callback when filter changes */
  onFilterChange: (filter: BudgetFilter) => void;

  /** Callback when sort changes */
  onSortChange: (sortBy: BudgetSortBy) => void;

  /** Optional custom className */
  className?: string;
}

/**
 * BudgetFilters Component
 *
 * Filter and sort controls for the budget utilization list.
 *
 * Filter Options:
 * - All tenants (default): Show all tenants regardless of utilization
 * - Over budget only: Filter to show only tenants where spent > budget
 * - High utilization (> 75%): Show tenants at 75%+ utilization
 *
 * Sort Options:
 * - Highest utilization first (default)
 * - Alphabetical (tenant name A-Z)
 * - Budget amount (largest to smallest)
 *
 * @param filter - Current filter value
 * @param sortBy - Current sort value
 * @param itemCount - Total number of items matching filter
 * @param onFilterChange - Callback when filter changes
 * @param onSortChange - Callback when sort changes
 * @param className - Optional custom classes
 *
 * @example
 * ```tsx
 * const [filter, setFilter] = useState<BudgetFilter>("all");
 * const [sortBy, setSortBy] = useState<BudgetSortBy>("utilization");
 *
 * <BudgetFilters
 *   filter={filter}
 *   sortBy={sortBy}
 *   itemCount={23}
 *   onFilterChange={setFilter}
 *   onSortChange={setSortBy}
 * />
 * ```
 */
export function BudgetFilters({
  filter,
  sortBy,
  itemCount,
  onFilterChange,
  onSortChange,
  className,
}: BudgetFiltersProps) {
  const filterOptions = [
    { value: "all", label: "All tenants" },
    { value: "over_budget", label: "Over budget only" },
    { value: "high_utilization", label: "High utilization (> 75%)" },
  ];

  const sortOptions = [
    { value: "utilization", label: "Highest utilization" },
    { value: "name", label: "Alphabetical" },
    { value: "budget", label: "Budget amount" },
  ];

  return (
    <div className={`flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between ${className || ""}`}>
      {/* Item count */}
      <div className="text-sm text-muted-foreground">
        <span className="font-medium">{itemCount}</span> tenant
        {itemCount !== 1 ? "s" : ""}
      </div>

      {/* Filter and Sort Controls */}
      <div className="flex flex-col sm:flex-row gap-3 w-full sm:w-auto">
        {/* Filter Dropdown */}
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium whitespace-nowrap">
            Filter:
          </span>
          <Select
            id="budget-filter"
            value={filter}
            onChange={(e) => onFilterChange(e.target.value as BudgetFilter)}
            options={filterOptions}
            className="w-full sm:w-48"
          />
        </div>

        {/* Sort Dropdown */}
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium whitespace-nowrap">
            Sort by:
          </span>
          <Select
            id="budget-sort"
            value={sortBy}
            onChange={(e) => onSortChange(e.target.value as BudgetSortBy)}
            options={sortOptions}
            className="w-full sm:w-52"
          />
        </div>
      </div>
    </div>
  );
}
