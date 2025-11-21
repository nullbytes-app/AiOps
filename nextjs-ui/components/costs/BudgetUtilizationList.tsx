"use client";

import { useState } from "react";
import { useBudgetUtilization } from "@/hooks/useBudgetUtilization";
import { BudgetFilters } from "./BudgetFilters";
import { BudgetUtilizationRow } from "./BudgetUtilizationRow";
import { Button } from "@/components/ui/Button";
import { AlertCircle, RefreshCw } from "lucide-react";
import type { BudgetFilter, BudgetSortBy } from "@/types/costs";

interface BudgetUtilizationListProps {
  /** Optional custom className for the container */
  className?: string;
}

/**
 * BudgetUtilizationList Component
 *
 * Main container component for budget utilization dashboard.
 * Fetches data, handles loading/error states, and renders tenant list
 * with filtering and sorting capabilities.
 *
 * Features:
 * - Auto-refresh every 60 seconds
 * - Filter: All tenants, Over budget only, High utilization (> 75%)
 * - Sort: Highest utilization, Alphabetical, Budget amount
 * - Loading skeleton
 * - Error state with retry button
 * - Empty state for each filter
 * - Pagination (future: currently shows first 20)
 *
 * @param className - Optional custom classes for container
 *
 * @example
 * ```tsx
 * // In /dashboard/llm-costs/page.tsx
 * <BudgetUtilizationList />
 * ```
 */
export function BudgetUtilizationList({
  className,
}: BudgetUtilizationListProps) {
  const [filter, setFilter] = useState<BudgetFilter>("all");
  const [sortBy, setSortBy] = useState<BudgetSortBy>("utilization");

  const { data, isLoading, error, refetch } = useBudgetUtilization({
    filter,
    sortBy,
    page: 1,
    pageSize: 20,
  });

  // Loading State
  if (isLoading) {
    return (
      <div className={className}>
        <div className="space-y-4">
          {/* Filter skeleton */}
          <div className="flex justify-between items-center">
            <div className="h-4 w-24 bg-gray-200 rounded animate-pulse" />
            <div className="flex gap-3">
              <div className="h-10 w-48 bg-gray-200 rounded animate-pulse" />
              <div className="h-10 w-52 bg-gray-200 rounded animate-pulse" />
            </div>
          </div>

          {/* Row skeletons */}
          {[1, 2, 3, 4, 5].map((i) => (
            <div
              key={i}
              className="border-b border-gray-200 p-4 space-y-3"
            >
              <div className="h-5 w-48 bg-gray-200 rounded animate-pulse" />
              <div className="h-4 w-64 bg-gray-200 rounded animate-pulse" />
              <div className="h-2 w-full bg-gray-200 rounded animate-pulse" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  // Error State
  if (error) {
    return (
      <div className={className}>
        <div className="flex flex-col items-center justify-center py-12 px-4 text-center">
          <AlertCircle className="w-12 h-12 text-red-500 mb-4" />
          <h3 className="text-lg font-semibold text-text-primary mb-2">
            Failed to load budget data
          </h3>
          <p className="text-sm text-muted-foreground mb-6 max-w-md">
            {error.message || "An unexpected error occurred while fetching budget utilization data."}
          </p>
          <Button onClick={() => refetch()} variant="primary">
            <RefreshCw className="w-4 h-4 mr-2" />
            Retry
          </Button>
        </div>
      </div>
    );
  }

  const tenants = data?.data || [];
  const totalCount = data?.total_count || 0;

  // Empty State (filter-specific messages)
  if (tenants.length === 0) {
    let emptyMessage = "No tenants found.";

    if (filter === "over_budget") {
      emptyMessage = "No tenants are currently over budget. Great job!";
    } else if (filter === "high_utilization") {
      emptyMessage = "All tenants within budget limits. Great job!";
    }

    return (
      <div className={className}>
        <BudgetFilters
          filter={filter}
          sortBy={sortBy}
          itemCount={totalCount}
          onFilterChange={setFilter}
          onSortChange={setSortBy}
          className="mb-6"
        />

        <div className="flex flex-col items-center justify-center py-12 px-4 text-center bg-gray-50 rounded-lg border border-gray-200">
          <p className="text-sm text-muted-foreground">{emptyMessage}</p>
        </div>
      </div>
    );
  }

  // Success State (with data)
  return (
    <div className={className}>
      {/* Filters */}
      <BudgetFilters
        filter={filter}
        sortBy={sortBy}
        itemCount={totalCount}
        onFilterChange={setFilter}
        onSortChange={setSortBy}
        className="mb-6"
      />

      {/* Tenant List */}
      <div className="border border-gray-200 rounded-lg overflow-hidden">
        {tenants.map((tenant) => (
          <BudgetUtilizationRow key={tenant.tenant_id} tenant={tenant} />
        ))}
      </div>

      {/* Pagination (Future Enhancement) */}
      {totalCount > 20 && (
        <div className="mt-4 text-center text-sm text-muted-foreground">
          Showing 20 of {totalCount} tenants. Pagination coming soon.
        </div>
      )}
    </div>
  );
}
