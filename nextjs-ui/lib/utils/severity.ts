/**
 * Severity calculation utilities for error analysis
 * Story 15: Agent Performance Dashboard - Error Analysis
 */

import type { SeverityLevel } from '@/types/agent-performance';

/**
 * Calculate severity level based on error occurrence count
 * AC #3: Low (<5), Medium (5-20), High (>20)
 */
export function getSeverityLevel(occurrences: number): SeverityLevel {
  if (occurrences < 5) return 'low';
  if (occurrences <= 20) return 'medium';
  return 'high';
}

/**
 * Get Tailwind CSS classes for severity badge
 * AC #3: Gray (low), Yellow (medium), Red (high)
 */
export function getSeverityColor(severity: SeverityLevel): string {
  const colors = {
    low: 'bg-gray-100 text-gray-700 border-gray-300',
    medium: 'bg-yellow-100 text-yellow-700 border-yellow-300',
    high: 'bg-red-100 text-red-700 border-red-300',
  };
  return colors[severity];
}

/**
 * Get accessible label for severity (for screen readers)
 */
export function getSeverityLabel(severity: SeverityLevel): string {
  const labels = {
    low: 'Low severity',
    medium: 'Medium severity',
    high: 'High severity',
  };
  return labels[severity];
}
