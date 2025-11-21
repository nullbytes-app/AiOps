import { SkeletonResponsive } from "./Skeleton";

interface SkeletonCardProps {
  /**
   * Show avatar/icon skeleton
   */
  showAvatar?: boolean;
  /**
   * Show title skeleton
   */
  showTitle?: boolean;
  /**
   * Show description skeleton
   */
  showDescription?: boolean;
  /**
   * Show action buttons skeleton
   */
  showActions?: boolean;
  /**
   * Number of description lines
   */
  descriptionLines?: number;
  /**
   * Number of action buttons
   */
  actionButtons?: number;
}

/**
 * SkeletonCard Component
 *
 * Card skeleton loader matching actual card dimensions.
 * Includes avatar, title, description, and action buttons.
 *
 * Features:
 * - Configurable elements (avatar, title, description, actions)
 * - Matches glass-card styling
 * - Multiple description lines
 * - Action button skeletons
 * - Light/dark mode support
 *
 * @example
 * ```tsx
 * // Full card skeleton
 * <SkeletonCard />
 *
 * // Card without avatar
 * <SkeletonCard showAvatar={false} />
 *
 * // Card with 3 description lines
 * <SkeletonCard descriptionLines={3} />
 *
 * // Card with 2 action buttons
 * <SkeletonCard actionButtons={2} />
 * ```
 *
 * Reference: Story 6 AC-4 (Loading States - Card Pattern)
 */
export function SkeletonCard({
  showAvatar = true,
  showTitle = true,
  showDescription = true,
  showActions = true,
  descriptionLines = 2,
  actionButtons = 2,
}: SkeletonCardProps) {
  return (
    <div
      className="glass-card p-6 border border-gray-200 dark:border-gray-700 rounded-lg"
      role="status"
      aria-label="Loading card content"
    >
      {/* Header with Avatar + Title */}
      <div className="flex items-start gap-4 mb-4">
        {/* Avatar Skeleton */}
        {showAvatar && (
          <div className="flex-shrink-0">
            <SkeletonResponsive width="48px" height="48px" rounded="50%" />
          </div>
        )}

        {/* Title & Subtitle */}
        {showTitle && (
          <div className="flex-1 min-w-0">
            <SkeletonResponsive height="20px" rounded="4px" className="mb-2" />
            <SkeletonResponsive
              width="60%"
              height="16px"
              rounded="4px"
              className="mb-0"
            />
          </div>
        )}
      </div>

      {/* Description Lines */}
      {showDescription && (
        <div className="space-y-2 mb-4">
          {Array.from({ length: descriptionLines }).map((_, index) => (
            <SkeletonResponsive
              key={`desc-${index}`}
              width={index === descriptionLines - 1 ? "80%" : "100%"}
              height="14px"
              rounded="4px"
            />
          ))}
        </div>
      )}

      {/* Action Buttons */}
      {showActions && (
        <div className="flex items-center gap-3 pt-4 border-t border-gray-200 dark:border-gray-700">
          {Array.from({ length: actionButtons }).map((_, index) => (
            <SkeletonResponsive
              key={`action-${index}`}
              width="100px"
              height="36px"
              rounded="8px"
            />
          ))}
        </div>
      )}
    </div>
  );
}

/**
 * SkeletonCardCompact Component
 *
 * Compact card skeleton with less padding and smaller elements.
 * Useful for grid layouts or list items.
 *
 * @example
 * ```tsx
 * // Grid of compact cards
 * <div className="grid grid-cols-3 gap-4">
 *   <SkeletonCardCompact />
 *   <SkeletonCardCompact />
 *   <SkeletonCardCompact />
 * </div>
 * ```
 */
export function SkeletonCardCompact({
  showAvatar = true,
  showTitle = true,
  showDescription = true,
  showActions = false,
  descriptionLines = 1,
  actionButtons = 1,
}: SkeletonCardProps) {
  return (
    <div
      className="glass-card p-4 border border-gray-200 dark:border-gray-700 rounded-lg"
      role="status"
      aria-label="Loading card content"
    >
      {/* Header */}
      <div className="flex items-center gap-3 mb-3">
        {showAvatar && (
          <SkeletonResponsive width="32px" height="32px" rounded="50%" />
        )}
        {showTitle && (
          <div className="flex-1">
            <SkeletonResponsive height="16px" rounded="4px" />
          </div>
        )}
      </div>

      {/* Description */}
      {showDescription && (
        <div className="space-y-2">
          {Array.from({ length: descriptionLines }).map((_, index) => (
            <SkeletonResponsive
              key={`desc-${index}`}
              width={index === descriptionLines - 1 ? "70%" : "100%"}
              height="12px"
              rounded="4px"
            />
          ))}
        </div>
      )}

      {/* Actions */}
      {showActions && (
        <div className="flex items-center gap-2 mt-3 pt-3 border-t border-gray-200 dark:border-gray-700">
          {Array.from({ length: actionButtons }).map((_, index) => (
            <SkeletonResponsive
              key={`action-${index}`}
              width="80px"
              height="28px"
              rounded="6px"
            />
          ))}
        </div>
      )}
    </div>
  );
}

/**
 * SkeletonCardGrid Component
 *
 * Grid of skeleton cards for loading states.
 * Useful for dashboard widgets or card listings.
 *
 * @example
 * ```tsx
 * // 3-column grid with 6 cards
 * <SkeletonCardGrid columns={3} count={6} />
 * ```
 */
export function SkeletonCardGrid({
  columns = 3,
  count = 6,
  compact = false,
}: {
  columns?: number;
  count?: number;
  compact?: boolean;
}) {
  const Card = compact ? SkeletonCardCompact : SkeletonCard;

  return (
    <div
      className={`grid gap-6`}
      style={{
        gridTemplateColumns: `repeat(${columns}, minmax(0, 1fr))`,
      }}
    >
      {Array.from({ length: count }).map((_, index) => (
        <Card key={`card-${index}`} />
      ))}
    </div>
  );
}
