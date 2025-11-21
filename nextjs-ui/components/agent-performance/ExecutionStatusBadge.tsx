/**
 * Execution Status Badge Component
 * Story 16: Agent Performance Dashboard - Slowest Executions
 * AC #1: Status badges with icons (success, failed, pending)
 * AC #8: ARIA labels for accessibility
 */

'use client';

import { Check, X, Clock } from 'lucide-react';

interface ExecutionStatusBadgeProps {
  status: 'success' | 'failed' | 'pending';
  className?: string;
}

export function ExecutionStatusBadge({ status, className = '' }: ExecutionStatusBadgeProps) {
  const getStatusConfig = () => {
    switch (status) {
      case 'success':
        return {
          label: 'Success',
          icon: Check,
          colorClasses: 'bg-green-100 text-green-700 border-green-300',
        };
      case 'failed':
        return {
          label: 'Failed',
          icon: X,
          colorClasses: 'bg-red-100 text-red-700 border-red-300',
        };
      case 'pending':
        return {
          label: 'Pending',
          icon: Clock,
          colorClasses: 'bg-yellow-100 text-yellow-700 border-yellow-300',
        };
    }
  };

  const config = getStatusConfig();
  const Icon = config.icon;

  return (
    <span
      className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium border ${config.colorClasses} ${className}`}
      aria-label={`Status: ${config.label}`}
    >
      <Icon className="w-3 h-3" aria-hidden="true" />
      {config.label}
    </span>
  );
}
