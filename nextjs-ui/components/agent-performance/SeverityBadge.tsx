/**
 * Severity Badge Component
 * Story 15: Agent Performance Dashboard - Error Analysis
 * Displays color-coded severity indicator based on error occurrence count
 * AC #3: Low (<5 gray), Medium (5-20 yellow), High (>20 red)
 */

'use client';

import { getSeverityLevel, getSeverityColor, getSeverityLabel } from '@/lib/utils/severity';
import type { SeverityLevel } from '@/types/agent-performance';

interface SeverityBadgeProps {
  occurrences: number;
  className?: string;
}

export function SeverityBadge({ occurrences, className = '' }: SeverityBadgeProps) {
  const severity: SeverityLevel = getSeverityLevel(occurrences);
  const colorClasses = getSeverityColor(severity);
  const ariaLabel = getSeverityLabel(severity);

  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${colorClasses} ${className}`}
      aria-label={ariaLabel}
    >
      {severity.charAt(0).toUpperCase() + severity.slice(1)}
    </span>
  );
}
