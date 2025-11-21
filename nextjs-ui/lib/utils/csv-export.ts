/**
 * CSV Export Utilities for Error Analysis
 * Story 15: Agent Performance Dashboard - Error Analysis
 * AC #5: Export all columns, formatted timestamps, full error messages
 */

import Papa from 'papaparse';
import type { ErrorAnalysisDTO } from '@/types/agent-performance';

/**
 * Export error analysis data to CSV file
 * Filename format: agent-{agent_id}-errors-{date}.csv
 */
export function exportErrorsToCSV(errors: ErrorAnalysisDTO[], agentId: string): void {
  // Transform data for CSV export
  const csvData = errors.map((error) => ({
    'Error Type': error.error_type,
    'Error Message': error.error_message, // Full message, not truncated
    'Occurrences': error.occurrences,
    'First Seen': error.first_seen, // ISO 8601 format
    'Last Seen': error.last_seen, // ISO 8601 format
    'Affected Executions': error.affected_executions,
    'Severity': getSeverity(error.occurrences),
  }));

  // Generate CSV string
  const csv = Papa.unparse(csvData, {
    quotes: true, // Quote all fields
    header: true,
  });

  // Create filename with current date
  const today = new Date().toISOString().split('T')[0]; // YYYY-MM-DD
  const filename = `agent-${agentId}-errors-${today}.csv`;

  // Download CSV file
  downloadCSV(csv, filename);
}

/**
 * Helper: Get severity level for CSV export
 */
function getSeverity(occurrences: number): string {
  if (occurrences < 5) return 'low';
  if (occurrences <= 20) return 'medium';
  return 'high';
}

/**
 * Helper: Trigger browser download of CSV content
 */
function downloadCSV(csvContent: string, filename: string): void {
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);

  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  link.style.display = 'none';

  document.body.appendChild(link);
  link.click();

  // Cleanup
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}
