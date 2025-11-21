import { Skeleton } from "@/components/ui/Skeleton";
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from "@/components/ui/Table";

interface SkeletonTableProps {
  /**
   * Number of skeleton rows to display
   * @default 10
   */
  rows?: number;
  /**
   * Number of columns per row
   * @default 5
   */
  columns?: number;
  /**
   * Optional className for the wrapper
   */
  className?: string;
  /**
   * Whether to show the header skeleton
   * @default true
   */
  showHeader?: boolean;
}

/**
 * SkeletonTable Component
 *
 * Skeleton loader for table data with shimmer animation.
 * Matches actual table dimensions for smooth loading transitions.
 *
 * Features:
 * - Shimmer animation (left-to-right gradient)
 * - Configurable rows and columns
 * - Matches Table component structure
 * - Supports light/dark mode
 * - Accessible (aria-busy, role="status")
 *
 * Design:
 * - Uses Liquid Glass design system (matches Table.tsx)
 * - Header: bg-white/30 backdrop-blur-glass
 * - Body: divide-y divide-white/20
 * - Consistent padding: px-6 py-3 (header), px-6 py-4 (cells)
 *
 * Loading State Thresholds:
 * - < 300ms: No loading indicator
 * - 300ms - 1s: Show spinner
 * - > 1s: Show SkeletonTable
 * - > 5s: Add "Taking longer than usual..." message
 *
 * @example
 * ```tsx
 * // Basic table skeleton (10 rows × 5 columns)
 * <SkeletonTable />
 *
 * // Custom dimensions
 * <SkeletonTable rows={5} columns={3} />
 *
 * // No header skeleton
 * <SkeletonTable showHeader={false} />
 *
 * // Usage with TanStack Query
 * const { data, isLoading } = useAgents();
 *
 * if (isLoading) {
 *   return <SkeletonTable rows={10} columns={5} />;
 * }
 *
 * return <AgentsTable data={data} />;
 * ```
 *
 * Reference: Story 6 AC-4 (Loading States & Skeleton Loaders)
 */
export function SkeletonTable({
  rows = 10,
  columns = 5,
  className = "",
  showHeader = true,
}: SkeletonTableProps) {
  return (
    <div className={`glass-card p-6 ${className}`} role="status" aria-busy="true" aria-label="Loading table data">
      <Table>
        {showHeader && (
          <TableHeader>
            <TableRow>
              {Array.from({ length: columns }).map((_, colIndex) => (
                <TableHead key={`header-${colIndex}`}>
                  <Skeleton width="80%" height="16px" />
                </TableHead>
              ))}
            </TableRow>
          </TableHeader>
        )}
        <TableBody>
          {Array.from({ length: rows }).map((_, rowIndex) => (
            <TableRow key={`row-${rowIndex}`}>
              {Array.from({ length: columns }).map((_, colIndex) => (
                <TableCell key={`cell-${rowIndex}-${colIndex}`}>
                  <Skeleton width="100%" height="16px" />
                </TableCell>
              ))}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

/**
 * SkeletonTableCompact Component
 *
 * Compact version without the glass-card wrapper.
 * Useful for embedding in existing containers.
 *
 * @example
 * ```tsx
 * <div className="glass-card p-6">
 *   <SkeletonTableCompact rows={5} columns={3} />
 * </div>
 * ```
 */
export function SkeletonTableCompact({
  rows = 10,
  columns = 5,
  showHeader = true,
}: Omit<SkeletonTableProps, "className">) {
  return (
    <Table>
      {showHeader && (
        <TableHeader>
          <TableRow>
            {Array.from({ length: columns }).map((_, colIndex) => (
              <TableHead key={`header-${colIndex}`}>
                <Skeleton width="80%" height="16px" />
              </TableHead>
            ))}
          </TableRow>
        </TableHeader>
      )}
      <TableBody>
        {Array.from({ length: rows }).map((_, rowIndex) => (
          <TableRow key={`row-${rowIndex}`}>
            {Array.from({ length: columns }).map((_, colIndex) => (
              <TableCell key={`cell-${rowIndex}-${colIndex}`}>
                <Skeleton width="100%" height="16px" />
              </TableCell>
            ))}
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

/**
 * SkeletonTableWithActions Component
 *
 * Table skeleton with action column (e.g., Edit, Delete buttons).
 * Useful for admin tables with row-level actions.
 *
 * @example
 * ```tsx
 * <SkeletonTableWithActions rows={10} columns={4} />
 * ```
 */
export function SkeletonTableWithActions({
  rows = 10,
  columns = 5,
  className = "",
}: SkeletonTableProps) {
  return (
    <div className={`glass-card p-6 ${className}`}>
      <Table>
        <TableHeader>
          <TableRow>
            {Array.from({ length: columns }).map((_, colIndex) => (
              <TableHead key={`header-${colIndex}`}>
                <Skeleton width="80%" height="16px" />
              </TableHead>
            ))}
            <TableHead>
              <Skeleton width="60px" height="16px" />
            </TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {Array.from({ length: rows }).map((_, rowIndex) => (
            <TableRow key={`row-${rowIndex}`}>
              {Array.from({ length: columns }).map((_, colIndex) => (
                <TableCell key={`cell-${rowIndex}-${colIndex}`}>
                  <Skeleton width="100%" height="16px" />
                </TableCell>
              ))}
              <TableCell>
                <div className="flex items-center gap-2">
                  <Skeleton width="32px" height="32px" rounded="6px" />
                  <Skeleton width="32px" height="32px" rounded="6px" />
                </div>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
