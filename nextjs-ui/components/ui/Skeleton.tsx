import { HTMLAttributes } from "react";

interface SkeletonProps extends HTMLAttributes<HTMLDivElement> {
  /**
   * Skeleton width (CSS value: '100%', '200px', etc.)
   */
  width?: string;
  /**
   * Skeleton height (CSS value: '20px', '100px', etc.)
   */
  height?: string;
  /**
   * Border radius (CSS value: '4px', '8px', '50%', etc.)
   */
  rounded?: string;
  /**
   * Shimmer animation direction
   */
  shimmerDirection?: "ltr" | "rtl";
  /**
   * Additional CSS classes
   */
  className?: string;
}

/**
 * Skeleton Component
 *
 * Base skeleton loader with shimmer animation.
 * Used as building block for loading states.
 *
 * Features:
 * - Shimmer animation (left-to-right or right-to-left)
 * - Customizable dimensions
 * - Accessible (aria-busy, aria-label)
 * - Supports light/dark mode
 *
 * Loading State Thresholds:
 * - < 300ms: No loading indicator
 * - 300ms - 1s: Show spinner
 * - > 1s: Show skeleton loader
 * - > 5s: Add "Taking longer than usual..." message
 *
 * @example
 * ```tsx
 * // Basic skeleton
 * <Skeleton width="200px" height="20px" />
 *
 * // Circular avatar skeleton
 * <Skeleton width="40px" height="40px" rounded="50%" />
 *
 * // Full width skeleton
 * <Skeleton height="16px" />
 *
 * // RTL shimmer direction
 * <Skeleton width="300px" height="24px" shimmerDirection="rtl" />
 * ```
 *
 * Reference: Story 6 AC-4 (Loading States & Skeleton Loaders)
 */
export function Skeleton({
  width = "100%",
  height = "20px",
  rounded = "4px",
  shimmerDirection = "ltr",
  className = "",
  ...props
}: SkeletonProps) {
  const shimmerKeyframes =
    shimmerDirection === "ltr"
      ? "shimmer-ltr 2s ease-in-out infinite"
      : "shimmer-rtl 2s ease-in-out infinite";

  return (
    <>
      {/* CSS animation keyframes */}
      <style jsx>{`
        @keyframes shimmer-ltr {
          0% {
            background-position: -200% 0;
          }
          100% {
            background-position: 200% 0;
          }
        }

        @keyframes shimmer-rtl {
          0% {
            background-position: 200% 0;
          }
          100% {
            background-position: -200% 0;
          }
        }
      `}</style>

      <div
        role="status"
        aria-busy="true"
        aria-label="Loading content"
        className={`skeleton-loader ${className}`}
        style={{
          width,
          height,
          borderRadius: rounded,
          background:
            "linear-gradient(90deg, #f3f4f6 0%, #e5e7eb 50%, #f3f4f6 100%)",
          backgroundSize: "200% 100%",
          animation: shimmerKeyframes,
        }}
        {...props}
      />
    </>
  );
}

/**
 * Dark mode skeleton (for dark theme)
 */
export function SkeletonDark({
  width = "100%",
  height = "20px",
  rounded = "4px",
  shimmerDirection = "ltr",
  className = "",
  ...props
}: SkeletonProps) {
  const shimmerKeyframes =
    shimmerDirection === "ltr"
      ? "shimmer-ltr 2s ease-in-out infinite"
      : "shimmer-rtl 2s ease-in-out infinite";

  return (
    <>
      <style jsx>{`
        @keyframes shimmer-ltr {
          0% {
            background-position: -200% 0;
          }
          100% {
            background-position: 200% 0;
          }
        }

        @keyframes shimmer-rtl {
          0% {
            background-position: 200% 0;
          }
          100% {
            background-position: -200% 0;
          }
        }
      `}</style>

      <div
        role="status"
        aria-busy="true"
        aria-label="Loading content"
        className={`skeleton-loader dark:block hidden ${className}`}
        style={{
          width,
          height,
          borderRadius: rounded,
          background:
            "linear-gradient(90deg, #1f2937 0%, #374151 50%, #1f2937 100%)",
          backgroundSize: "200% 100%",
          animation: shimmerKeyframes,
        }}
        {...props}
      />
    </>
  );
}

/**
 * Responsive skeleton that adapts to light/dark mode
 */
export function SkeletonResponsive(props: SkeletonProps) {
  return (
    <div className="skeleton-wrapper">
      {/* Light mode skeleton */}
      <div className="dark:hidden">
        <Skeleton {...props} />
      </div>
      {/* Dark mode skeleton */}
      <div className="hidden dark:block">
        <SkeletonDark {...props} />
      </div>
    </div>
  );
}
