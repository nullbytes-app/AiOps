/**
 * DateRangeSelector Component
 *
 * Reusable date range picker for LLM cost dashboard features.
 * Stores selection in URL query params for shareability.
 * Supports preset buttons ("Last 7 days", "Last 30 days") and custom range.
 *
 * Used in Stories: 1.3, 1.4, 1.5, 1.6, 1.7, 1.8
 */

'use client';

import React from 'react';
import { useSearchParams, useRouter, usePathname } from 'next/navigation';
import { Button } from '@/components/ui/Button';
import { Calendar } from 'lucide-react';

export interface DateRangeValue {
  startDate: Date;
  endDate: Date;
}

export interface DateRangeSelectorProps {
  /** Callback fired when date range changes */
  onChange: (range: DateRangeValue) => void;
  /** Custom CSS classes */
  className?: string;
}

/**
 * Get default date range (Last 30 days)
 */
function getDefaultRange(): DateRangeValue {
  const endDate = new Date();
  const startDate = new Date();
  startDate.setDate(startDate.getDate() - 30);

  return { startDate, endDate };
}

/**
 * Parse date from YYYY-MM-DD string
 */
function parseDate(dateStr: string | null): Date | null {
  if (!dateStr) return null;

  try {
    const date = new Date(dateStr);
    return isNaN(date.getTime()) ? null : date;
  } catch {
    return null;
  }
}

/**
 * Format date as YYYY-MM-DD for URL params
 */
function formatDate(date: Date): string {
  return date.toISOString().split('T')[0];
}

/**
 * DateRangeSelector Component
 *
 * Features:
 * - Preset buttons: "Last 7 days", "Last 30 days" (AC requirement)
 * - Custom date range picker (AC requirement)
 * - URL query params storage for shareability (AC requirement)
 * - Default: "Last 30 days" (AC requirement)
 * - Validation: Start date must be before end date
 * - Max range: 90 days (prevent large queries)
 *
 * URL Params:
 * - ?start_date=YYYY-MM-DD
 * - ?end_date=YYYY-MM-DD
 *
 * @example
 * ```tsx
 * function TokenBreakdownPage() {
 *   const [dateRange, setDateRange] = useState(getDefaultRange());
 *
 *   return (
 *     <div>
 *       <DateRangeSelector onChange={setDateRange} />
 *       <TokenBreakdownChart startDate={dateRange.startDate} endDate={dateRange.endDate} />
 *     </div>
 *   );
 * }
 * ```
 */
export function DateRangeSelector({ onChange, className }: DateRangeSelectorProps) {
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();

  // Initialize from URL or use default (Last 30 days)
  const [customMode, setCustomMode] = React.useState(false);
  const [startDateStr, setStartDateStr] = React.useState('');
  const [endDateStr, setEndDateStr] = React.useState('');
  const [validationError, setValidationError] = React.useState('');

  // Parse dates from URL on mount
  React.useEffect(() => {
    const urlStartDate = searchParams.get('start_date');
    const urlEndDate = searchParams.get('end_date');

    if (urlStartDate && urlEndDate) {
      const start = parseDate(urlStartDate);
      const end = parseDate(urlEndDate);

      if (start && end) {
        onChange({ startDate: start, endDate: end });
        return;
      }
    }

    // Use default range if no valid URL params
    const defaultRange = getDefaultRange();
    onChange(defaultRange);

    // Set URL params to default
    updateURLParams(defaultRange.startDate, defaultRange.endDate);
  }, []); // Run once on mount

  /**
   * Update URL query params without page reload
   */
  const updateURLParams = (start: Date, end: Date) => {
    const params = new URLSearchParams(searchParams.toString());
    params.set('start_date', formatDate(start));
    params.set('end_date', formatDate(end));
    router.replace(`${pathname}?${params.toString()}`, { scroll: false });
  };

  /**
   * Handle preset button click (Last 7 days, Last 30 days)
   */
  const handlePreset = (days: number) => {
    const endDate = new Date();
    const startDate = new Date();
    startDate.setDate(startDate.getDate() - days);

    onChange({ startDate, endDate });
    updateURLParams(startDate, endDate);
    setCustomMode(false);
    setValidationError('');
  };

  /**
   * Handle custom date range submission
   */
  const handleCustomSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setValidationError('');

    const startDate = parseDate(startDateStr);
    const endDate = parseDate(endDateStr);

    // Validation: Both dates must be provided
    if (!startDate || !endDate) {
      setValidationError('Please enter both start and end dates');
      return;
    }

    // Validation: Start date must be before end date
    if (startDate > endDate) {
      setValidationError('Start date must be before end date');
      return;
    }

    // Validation: Max 90 days range
    const diffMs = endDate.getTime() - startDate.getTime();
    const diffDays = Math.ceil(diffMs / (1000 * 60 * 60 * 24));
    if (diffDays > 90) {
      setValidationError('Date range limited to 90 days');
      return;
    }

    onChange({ startDate, endDate });
    updateURLParams(startDate, endDate);
    setValidationError('');
  };

  return (
    <div className={`space-y-4 ${className || ''}`}>
      {/* Preset Buttons */}
      <div className="flex items-center gap-2 flex-wrap">
        <Calendar className="h-4 w-4 text-muted-foreground" />
        <span className="text-sm font-medium text-foreground">Date Range:</span>

        <Button
          variant="secondary"
          size="sm"
          onClick={() => handlePreset(7)}
          className="gap-1"
        >
          Last 7 days
        </Button>

        <Button
          variant="secondary"
          size="sm"
          onClick={() => handlePreset(30)}
          className="gap-1"
        >
          Last 30 days
        </Button>

        <Button
          variant="secondary"
          size="sm"
          onClick={() => setCustomMode(!customMode)}
          className="gap-1"
        >
          Custom Range
        </Button>
      </div>

      {/* Custom Date Range Form */}
      {customMode && (
        <form
          onSubmit={handleCustomSubmit}
          className="flex items-end gap-3 p-4 bg-muted/30 rounded-lg border border-border"
        >
          <div className="flex-1">
            <label htmlFor="start-date" className="block text-xs font-medium text-muted-foreground mb-1">
              Start Date
            </label>
            <input
              id="start-date"
              type="date"
              value={startDateStr}
              onChange={(e) => setStartDateStr(e.target.value)}
              className="w-full px-3 py-2 text-sm rounded-md border border-input bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
              required
            />
          </div>

          <div className="flex-1">
            <label htmlFor="end-date" className="block text-xs font-medium text-muted-foreground mb-1">
              End Date
            </label>
            <input
              id="end-date"
              type="date"
              value={endDateStr}
              onChange={(e) => setEndDateStr(e.target.value)}
              className="w-full px-3 py-2 text-sm rounded-md border border-input bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
              required
            />
          </div>

          <Button type="submit" size="sm">
            Apply
          </Button>
        </form>
      )}

      {/* Validation Error */}
      {validationError && (
        <p className="text-xs text-destructive">{validationError}</p>
      )}
    </div>
  );
}
