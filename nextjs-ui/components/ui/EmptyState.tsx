import { ReactNode } from 'react';
import { cn } from '@/lib/utils/cn';

/**
 * Empty State Component
 *
 * Displays when no data is available with optional action button
 *
 * @example
 * ```tsx
 * <EmptyState
 *   icon={<Package className="w-12 h-12" />}
 *   title="No tenants found"
 *   description="Get started by creating your first tenant"
 *   action={
 *     <Button onClick={() => router.push('/dashboard/tenants/new')}>
 *       Create Tenant
 *     </Button>
 *   }
 * />
 * ```
 */

interface EmptyStateProps {
  icon?: ReactNode;
  title: string;
  description?: string;
  action?: ReactNode;
  className?: string;
}

export function EmptyState({
  icon,
  title,
  description,
  action,
  className,
}: EmptyStateProps) {
  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center py-12 px-6',
        'glass-card rounded-lg',
        className
      )}
    >
      {icon && (
        <div className="mb-4 text-text-secondary opacity-50">
          {icon}
        </div>
      )}
      <h3 className="text-lg font-semibold text-text-primary mb-2">
        {title}
      </h3>
      {description && (
        <p className="text-sm text-text-secondary text-center max-w-md mb-6">
          {description}
        </p>
      )}
      {action && <div>{action}</div>}
    </div>
  );
}
