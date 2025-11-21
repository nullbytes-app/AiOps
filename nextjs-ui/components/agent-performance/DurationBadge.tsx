/**
 * Duration Badge Component
 * Story 16: Agent Performance Dashboard - Slowest Executions
 * AC #3: Badge for very slow executions (> 120s)
 * Displays turtle emoji 🐢 or Clock icon for executions exceeding 2 minutes
 */

'use client';

import { Clock } from 'lucide-react';

interface DurationBadgeProps {
  durationMs: number;
  className?: string;
}

export function DurationBadge({ durationMs, className = '' }: DurationBadgeProps) {
  const seconds = durationMs / 1000;

  // Only show badge for very slow executions (> 120s)
  if (seconds <= 120) {
    return null;
  }

  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-red-50 text-red-700 border border-red-300 ${className}`}
      aria-label={`Very slow execution: ${Math.floor(seconds)}  seconds`}
      title="Very slow execution (> 2 minutes)"
    >
      <Clock className="w-3 h-3" aria-hidden="true" />
      <span className="font-semibold">Slow</span>
    </span>
  );
}
