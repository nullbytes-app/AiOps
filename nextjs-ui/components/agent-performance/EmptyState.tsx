/**
 * Empty State Component
 * Displayed when no agent selected or no data available
 * Following 2025 UI patterns for empty states
 */

'use client';

import { BarChart3 } from 'lucide-react';

interface EmptyStateProps {
  message?: string;
  suggestion?: string;
}

export function EmptyState({
  message = 'No executions found for this agent in the selected date range',
  suggestion = 'Try selecting a different date range or agent',
}: EmptyStateProps) {
  return (
    <div className="col-span-full">
      <div className="flex flex-col items-center justify-center p-12 bg-muted/30 border border-dashed border-muted-foreground/30 rounded-lg">
        <BarChart3 className="h-16 w-16 text-muted-foreground/50 mb-4" />
        <h3 className="text-lg font-semibold text-foreground mb-2">{message}</h3>
        <p className="text-sm text-muted-foreground">{suggestion}</p>
      </div>
    </div>
  );
}
