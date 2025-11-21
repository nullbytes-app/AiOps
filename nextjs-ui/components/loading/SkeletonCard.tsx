import { Skeleton } from "@/components/ui/Skeleton";
import { Card } from "@/components/ui/Card";

interface SkeletonCardProps {
  /**
   * Card variant (affects height and content structure)
   */
  variant?: "stat" | "list" | "detail" | "metric";
  /**
   * Card padding (matches Card component)
   */
  padding?: "none" | "sm" | "md" | "lg";
  /**
   * Optional className for the wrapper
   */
  className?: string;
  /**
   * Whether to show action buttons at bottom
   */
  showActions?: boolean;
}

/**
 * SkeletonCard Component
 *
 * Skeleton loader for card components with shimmer animation.
 * Matches actual card dimensions for smooth loading transitions.
 *
 * Features:
 * - Shimmer animation (left-to-right gradient)
 * - Multiple variants (stat, list, detail, metric)
 * - Matches Card component structure
 * - Supports light/dark mode
 * - Accessible (aria-busy, role="status")
 *
 * Design:
 * - Uses Liquid Glass design system (glass-card effect)
 * - Matches Card.tsx padding options
 * - Consistent spacing and layout
 *
 * Variants:
 * - stat: Single metric card (e.g., "Total Agents: 42")
 * - list: List of items with icons
 * - detail: Detailed info card with title, description, metadata
 * - metric: Metric card with chart placeholder
 *
 * @example
 * ```tsx
 * // Basic stat card skeleton
 * <SkeletonCard variant="stat" />
 *
 * // List card skeleton
 * <SkeletonCard variant="list" />
 *
 * // Detail card with actions
 * <SkeletonCard variant="detail" showActions />
 *
 * // Usage with TanStack Query
 * const { data, isLoading } = useAgentStats();
 *
 * if (isLoading) {
 *   return <SkeletonCard variant="stat" />;
 * }
 *
 * return <StatCard data={data} />;
 * ```
 *
 * Reference: Story 6 AC-4 (Loading States & Skeleton Loaders)
 */
export function SkeletonCard({
  variant = "detail",
  padding = "md",
  className = "",
  showActions = false,
}: SkeletonCardProps) {
  if (variant === "stat") {
    return <SkeletonCardStat padding={padding} className={className} />;
  }

  if (variant === "list") {
    return <SkeletonCardList padding={padding} className={className} />;
  }

  if (variant === "metric") {
    return <SkeletonCardMetric padding={padding} className={className} />;
  }

  // Default: detail variant
  return (
    <Card
      padding={padding}
      hover={false}
      className={className}
      role="status"
      aria-busy="true"
      aria-label="Loading card content"
    >
      {/* Header: Title + Icon */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex-1">
          <Skeleton width="60%" height="24px" className="mb-2" />
          <Skeleton width="80%" height="16px" />
        </div>
        <Skeleton width="40px" height="40px" rounded="8px" />
      </div>

      {/* Content: Description lines */}
      <div className="space-y-2 mb-4">
        <Skeleton width="100%" height="14px" />
        <Skeleton width="95%" height="14px" />
        <Skeleton width="88%" height="14px" />
      </div>

      {/* Metadata: Tags or badges */}
      <div className="flex items-center gap-2 mb-4">
        <Skeleton width="60px" height="24px" rounded="12px" />
        <Skeleton width="80px" height="24px" rounded="12px" />
        <Skeleton width="70px" height="24px" rounded="12px" />
      </div>

      {/* Actions: Buttons */}
      {showActions && (
        <div className="flex items-center gap-2 pt-4 border-t border-white/10">
          <Skeleton width="80px" height="36px" rounded="6px" />
          <Skeleton width="100px" height="36px" rounded="6px" />
        </div>
      )}
    </Card>
  );
}

/**
 * SkeletonCardStat Component
 *
 * Skeleton for stat cards (single metric with icon).
 *
 * @example
 * ```tsx
 * <SkeletonCardStat />
 * ```
 */
function SkeletonCardStat({
  padding = "md",
  className = "",
}: Omit<SkeletonCardProps, "variant" | "showActions">) {
  return (
    <Card padding={padding} hover={false} className={className}>
      <div className="flex items-center justify-between">
        <div className="flex-1">
          <Skeleton width="40%" height="14px" className="mb-2" />
          <Skeleton width="60%" height="32px" />
        </div>
        <Skeleton width="48px" height="48px" rounded="10px" />
      </div>
    </Card>
  );
}

/**
 * SkeletonCardList Component
 *
 * Skeleton for list cards (multiple items with icons).
 *
 * @example
 * ```tsx
 * <SkeletonCardList />
 * ```
 */
function SkeletonCardList({
  padding = "md",
  className = "",
}: Omit<SkeletonCardProps, "variant" | "showActions">) {
  return (
    <Card padding={padding} hover={false} className={className}>
      {/* Card title */}
      <Skeleton width="50%" height="20px" className="mb-4" />

      {/* List items */}
      <div className="space-y-3">
        {Array.from({ length: 5 }).map((_, index) => (
          <div key={index} className="flex items-center gap-3">
            <Skeleton width="32px" height="32px" rounded="6px" />
            <div className="flex-1">
              <Skeleton width="70%" height="14px" className="mb-1" />
              <Skeleton width="50%" height="12px" />
            </div>
            <Skeleton width="40px" height="20px" rounded="4px" />
          </div>
        ))}
      </div>
    </Card>
  );
}

/**
 * SkeletonCardMetric Component
 *
 * Skeleton for metric cards (chart + value).
 *
 * @example
 * ```tsx
 * <SkeletonCardMetric />
 * ```
 */
function SkeletonCardMetric({
  padding = "md",
  className = "",
}: Omit<SkeletonCardProps, "variant" | "showActions">) {
  return (
    <Card padding={padding} hover={false} className={className}>
      {/* Metric header */}
      <div className="flex items-center justify-between mb-4">
        <Skeleton width="50%" height="18px" />
        <Skeleton width="60px" height="24px" rounded="12px" />
      </div>

      {/* Big number */}
      <Skeleton width="40%" height="40px" className="mb-4" />

      {/* Chart placeholder */}
      <div className="h-32 flex items-end gap-1">
        {Array.from({ length: 12 }).map((_, index) => (
          <Skeleton
            key={index}
            width="100%"
            height={`${Math.random() * 80 + 20}%`}
            rounded="2px"
          />
        ))}
      </div>
    </Card>
  );
}

/**
 * SkeletonCardGrid Component
 *
 * Grid of skeleton cards (useful for dashboard layouts).
 *
 * @example
 * ```tsx
 * <SkeletonCardGrid count={4} variant="stat" />
 * ```
 */
export function SkeletonCardGrid({
  count = 4,
  variant = "stat",
  cols = 4,
}: {
  count?: number;
  variant?: "stat" | "list" | "detail" | "metric";
  cols?: 2 | 3 | 4;
}) {
  const gridCols = {
    2: "grid-cols-1 sm:grid-cols-2",
    3: "grid-cols-1 sm:grid-cols-2 lg:grid-cols-3",
    4: "grid-cols-1 sm:grid-cols-2 lg:grid-cols-4",
  };

  return (
    <div className={`grid ${gridCols[cols]} gap-6`}>
      {Array.from({ length: count }).map((_, index) => (
        <SkeletonCard key={index} variant={variant} />
      ))}
    </div>
  );
}
