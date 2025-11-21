/**
 * Slowest Executions List Component
 * Story 16: Agent Performance Dashboard - Slowest Executions
 * AC #1: Table with execution details
 * AC #2: Sorting, filtering, pagination, row expansion
 * AC #3: Duration color coding
 * AC #4: Inline details expansion
 * AC #5: Filter controls and auto-refresh
 * AC #6: Loading/empty/error states
 * AC #7: React Query integration (90s staleTime/refetchInterval)
 * AC #8: Accessibility (keyboard nav, ARIA labels)
 */

'use client';

import React, { useState, useMemo, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  getPaginationRowModel,
  getExpandedRowModel,
  flexRender,
  type SortingState,
  type ColumnDef,
  type ExpandedState,
} from '@tanstack/react-table';
import { ArrowUpDown, ArrowUp, ArrowDown, RefreshCw, ChevronDown, ChevronRight, ExternalLink } from 'lucide-react';
import Link from 'next/link';
import { useSlowestExecutions } from '@/hooks/useSlowestExecutions';
import { ExecutionStatusBadge } from './ExecutionStatusBadge';
import { DurationBadge } from './DurationBadge';
import { formatExecutionTimeLong, getDurationSeverity, getDurationColor } from '@/lib/utils/performance';
import type { SlowestExecutionDTO } from '@/types/agent-performance';

interface SlowestExecutionsListProps {
  agentId: string | null;
  startDate: Date;
  endDate: Date;
}

export function SlowestExecutionsList({ agentId, startDate, endDate }: SlowestExecutionsListProps) {
  const router = useRouter();
  const searchParams = useSearchParams();

  // State management
  const [sorting, setSorting] = useState<SortingState>([
    { id: 'duration_ms', desc: true }, // Default: slowest first (AC #2)
  ]);
  const [expanded, setExpanded] = useState<ExpandedState>({});
  const [page, setPage] = useState(0);

  // Get status filter from URL (AC #5)
  const statusFilter = (searchParams?.get('status') as 'all' | 'success' | 'failed') || 'all';

  // Check if any rows are expanded (AC #5 - pause auto-refresh during interaction)
  const hasExpandedRows = Object.keys(expanded).length > 0;

  // Fetch slowest executions data with React Query (AC #7)
  // Pause auto-refresh when user is viewing expanded rows (AC #5, Task 6.5)
  const { data, isLoading, isError, refetch, dataUpdatedAt } = useSlowestExecutions({
    agentId,
    startDate,
    endDate,
    page,
    statusFilter,
    refetchInterval: hasExpandedRows ? false : 90000, // Pause when expanded (AC #5)
  });

  // State for "Last updated" timestamp (AC #5, Task 6.4)
  const [timeSinceUpdate, setTimeSinceUpdate] = useState<string>('Never');

  // Update "Last updated" timestamp every second (AC #5, Task 6.4)
  useEffect(() => {
    if (!dataUpdatedAt) {
      setTimeSinceUpdate('Never');
      return;
    }

    const updateTimestamp = () => {
      const seconds = Math.floor((Date.now() - dataUpdatedAt) / 1000);
      if (seconds < 60) {
        setTimeSinceUpdate(`${seconds}s ago`);
      } else {
        const minutes = Math.floor(seconds / 60);
        setTimeSinceUpdate(`${minutes}m ago`);
      }
    };

    updateTimestamp(); // Initial update
    const interval = setInterval(updateTimestamp, 1000); // Update every second
    return () => clearInterval(interval);
  }, [dataUpdatedAt]);

  // Format timestamp for display (AC #1)
  const formatTimestamp = (isoString: string) => {
    return new Date(isoString).toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  };

  // Truncate text to max length (AC #1)
  const truncateText = (text: string, maxLength: number = 80) => {
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
  };

  // Handle status filter change (AC #5)
  const handleStatusFilterChange = (newStatus: 'all' | 'success' | 'failed') => {
    const params = new URLSearchParams(searchParams?.toString() || '');
    if (newStatus === 'all') {
      params.delete('status');
    } else {
      params.set('status', newStatus);
    }
    router.push(`?${params.toString()}`);
    setPage(0); // Reset to first page on filter change
  };

  // Define table columns (AC #1, #2, #3)
  const columns = useMemo<ColumnDef<SlowestExecutionDTO>[]>(
    () => [
      {
        id: 'expander',
        header: () => null,
        cell: ({ row }) => {
          return row.getCanExpand() ? (
            <button
              type="button"
              onClick={() => row.toggleExpanded()}
              className="cursor-pointer p-1 hover:bg-gray-100 rounded"
              aria-label={row.getIsExpanded() ? 'Collapse row' : 'Expand row'}
              aria-expanded={row.getIsExpanded()}
            >
              {row.getIsExpanded() ? (
                <ChevronDown className="w-4 h-4" aria-hidden="true" />
              ) : (
                <ChevronRight className="w-4 h-4" aria-hidden="true" />
              )}
            </button>
          ) : null;
        },
      },
      {
        accessorKey: 'execution_id',
        header: 'Execution ID',
        cell: ({ getValue }) => {
          const id = getValue() as string;
          return (
            <Link
              href={`/dashboard/execution-history/${id}`}
              className="text-blue-600 hover:text-blue-800 hover:underline font-medium inline-flex items-center gap-1"
              aria-label={`View execution details for ${id}`}
            >
              {id.substring(0, 8)}...
              <ExternalLink className="w-3 h-3" aria-hidden="true" />
            </Link>
          );
        },
      },
      {
        accessorKey: 'agent_name',
        header: 'Agent',
        cell: ({ getValue }) => (
          <span className="font-medium text-gray-900">{getValue() as string}</span>
        ),
      },
      {
        accessorKey: 'duration_ms',
        header: ({ column }) => (
          <button
            className="flex items-center gap-2 font-medium text-left hover:text-gray-900"
            onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
            aria-label="Sort by execution time"
          >
            Execution Time
            {column.getIsSorted() === 'asc' ? (
              <ArrowUp className="w-4 h-4" aria-hidden="true" />
            ) : column.getIsSorted() === 'desc' ? (
              <ArrowDown className="w-4 h-4" aria-hidden="true" />
            ) : (
              <ArrowUpDown className="w-4 h-4 text-gray-400" aria-hidden="true" />
            )}
          </button>
        ),
        cell: ({ getValue }) => {
          const durationMs = getValue() as number;
          const severity = getDurationSeverity(durationMs);
          const colorClass = getDurationColor(severity);
          const formattedTime = formatExecutionTimeLong(durationMs);

          return (
            <div className="flex items-center gap-2">
              <span
                className={`font-medium ${colorClass}`}
                aria-label={`Execution time: ${formattedTime}, ${severity}`}
              >
                {formattedTime}
              </span>
              <DurationBadge durationMs={durationMs} />
            </div>
          );
        },
      },
      {
        accessorKey: 'start_time',
        header: ({ column }) => (
          <button
            className="flex items-center gap-2 font-medium text-left hover:text-gray-900"
            onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
            aria-label="Sort by start time"
          >
            Start Time
            {column.getIsSorted() === 'asc' ? (
              <ArrowUp className="w-4 h-4" aria-hidden="true" />
            ) : column.getIsSorted() === 'desc' ? (
              <ArrowDown className="w-4 h-4" aria-hidden="true" />
            ) : (
              <ArrowUpDown className="w-4 h-4 text-gray-400" aria-hidden="true" />
            )}
          </button>
        ),
        cell: ({ getValue }) => (
          <span className="text-gray-600">{formatTimestamp(getValue() as string)}</span>
        ),
      },
      {
        accessorKey: 'status',
        header: 'Status',
        cell: ({ getValue }) => (
          <ExecutionStatusBadge status={getValue() as 'success' | 'failed' | 'pending'} />
        ),
      },
      {
        accessorKey: 'input_preview',
        header: 'Input Preview',
        cell: ({ getValue }) => (
          <span className="text-gray-600 text-sm">{truncateText(getValue() as string, 80)}</span>
        ),
      },
    ],
    [] // No dependencies needed - columns are static
  );

  // Initialize table (AC #2, #4)
  const table = useReactTable({
    data: data?.executions || [],
    columns,
    state: {
      sorting,
      expanded,
    },
    onSortingChange: setSorting,
    onExpandedChange: setExpanded,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    getExpandedRowModel: getExpandedRowModel(),
    getRowCanExpand: () => true, // All rows can be expanded
    manualPagination: false, // Client-side pagination for now
    pageCount: Math.ceil((data?.total_count || 0) / 10),
  });

  // Loading state (AC #6)
  if (isLoading) {
    return (
      <div className="mt-6" role="status" aria-live="polite" aria-label="Loading slowest executions">
        <div className="bg-white rounded-lg border border-gray-200 shadow-sm">
          <div className="px-6 py-4 border-b border-gray-200">
            <div className="h-6 w-48 bg-gray-200 animate-pulse rounded" />
          </div>
          <div className="divide-y divide-gray-200">
            {[...Array(10)].map((_, i) => (
              <div key={i} className="px-6 py-4 flex items-center gap-4">
                <div className="h-4 w-4 bg-gray-200 animate-pulse rounded" />
                <div className="h-4 w-20 bg-gray-200 animate-pulse rounded" />
                <div className="h-4 w-32 bg-gray-200 animate-pulse rounded" />
                <div className="h-4 w-24 bg-gray-200 animate-pulse rounded" />
                <div className="h-4 w-40 bg-gray-200 animate-pulse rounded" />
                <div className="h-4 w-16 bg-gray-200 animate-pulse rounded" />
                <div className="flex-1 h-4 bg-gray-200 animate-pulse rounded" />
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  // Error state (AC #6)
  if (isError) {
    return (
      <div className="mt-6">
        <div className="bg-white rounded-lg border border-red-200 shadow-sm p-8 text-center">
          <div className="text-red-600 text-lg font-semibold mb-2">Failed to load execution data</div>
          <p className="text-gray-600 mb-4">
            There was an error fetching the slowest executions. Please try again.
          </p>
          <button
            onClick={() => refetch()}
            className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
            Retry
          </button>
        </div>
      </div>
    );
  }

  // Empty state (AC #6)
  if (!data?.executions || data.executions.length === 0) {
    return (
      <div className="mt-6">
        <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-8 text-center">
          <div className="text-gray-900 text-lg font-semibold mb-2">No slow executions found</div>
          <p className="text-gray-600">
            {statusFilter !== 'all'
              ? `No ${statusFilter} executions found in the selected time range.`
              : 'No executions found in the selected time range.'}
          </p>
        </div>
      </div>
    );
  }

  // Success state: render table (AC #1, #2)
  return (
    <div className="mt-6">
      {/* Header with controls (AC #5) */}
      <div className="bg-white rounded-t-lg border border-gray-200 border-b-0 shadow-sm px-6 py-4 flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold text-gray-900">
            Slowest Executions
            <span className="ml-2 text-sm font-normal text-gray-500" role="status" aria-live="polite">
              (Showing {table.getRowModel().rows.length} of {data.total_count})
            </span>
          </h3>
          {/* Last updated timestamp (AC #5, Task 6.4) */}
          <p className="text-xs text-gray-400 mt-1">
            Last updated: {timeSinceUpdate}
            {hasExpandedRows && <span className="ml-2 text-amber-600">(Auto-refresh paused)</span>}
          </p>
        </div>

        <div className="flex items-center gap-4">
          {/* Status Filter (AC #5) */}
          <div className="flex items-center gap-2">
            <label htmlFor="status-filter" className="text-sm font-medium text-gray-700">
              Filter:
            </label>
            <select
              id="status-filter"
              value={statusFilter}
              onChange={(e) => handleStatusFilterChange(e.target.value as 'all' | 'success' | 'failed')}
              className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              aria-label="Filter executions by status"
            >
              <option value="all">All</option>
              <option value="success">Success Only</option>
              <option value="failed">Failed Only</option>
            </select>
          </div>

          {/* Manual Refresh Button (AC #5) */}
          <button
            onClick={() => refetch()}
            className="inline-flex items-center gap-2 px-3 py-1.5 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
            aria-label="Refresh slowest executions data"
          >
            <RefreshCw className="w-4 h-4" />
            Refresh
          </button>
        </div>
      </div>

      {/* Table (AC #1, #2, #3, #4) */}
      <div className="bg-white rounded-b-lg border border-gray-200 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full" role="table" aria-label="Slowest executions table">
            <thead className="bg-gray-50 border-b border-gray-200">
              {table.getHeaderGroups().map((headerGroup) => (
                <tr key={headerGroup.id} role="row">
                  {headerGroup.headers.map((header) => (
                    <th
                      key={header.id}
                      className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                      role="columnheader"
                    >
                      {header.isPlaceholder
                        ? null
                        : flexRender(header.column.columnDef.header, header.getContext())}
                    </th>
                  ))}
                </tr>
              ))}
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {table.getRowModel().rows.map((row) => (
                <React.Fragment key={row.id}>
                  {/* Main row (AC #1, #2) */}
                  <tr
                    className="hover:bg-gray-50"
                    role="row"
                    aria-expanded={row.getIsExpanded()}
                  >
                    {row.getVisibleCells().map((cell) => (
                      <td key={cell.id} className="px-6 py-4 whitespace-nowrap" role="cell">
                        {flexRender(cell.column.columnDef.cell, cell.getContext())}
                      </td>
                    ))}
                  </tr>

                  {/* Expanded details row (AC #4) */}
                  {row.getIsExpanded() && (
                    <tr key={`${row.id}-expanded`}>
                      <td colSpan={columns.length} className="px-6 py-4 bg-gray-50">
                        <div className="space-y-4">
                          {/* Full Input */}
                          <div>
                            <h4 className="text-sm font-semibold text-gray-900 mb-2">Input:</h4>
                            <pre className="text-sm text-gray-700 bg-white border border-gray-200 rounded p-3 overflow-x-auto whitespace-pre-wrap">
                              {row.original.input_preview}
                            </pre>
                          </div>

                          {/* Output Preview */}
                          <div>
                            <h4 className="text-sm font-semibold text-gray-900 mb-2">Output Preview:</h4>
                            <pre className="text-sm text-gray-700 bg-white border border-gray-200 rounded p-3 overflow-x-auto whitespace-pre-wrap">
                              {truncateText(row.original.output_preview, 200)}
                            </pre>
                          </div>

                          {/* Metadata */}
                          <div className="grid grid-cols-2 gap-4">
                            <div>
                              <span className="text-sm font-semibold text-gray-900">Conversation Steps:</span>
                              <span className="ml-2 text-sm text-gray-700">
                                {row.original.conversation_steps_count} steps
                              </span>
                            </div>
                            <div>
                              <span className="text-sm font-semibold text-gray-900">Tool Calls:</span>
                              <span className="ml-2 text-sm text-gray-700">
                                {row.original.tool_calls_count} invocations
                              </span>
                            </div>
                          </div>

                          {/* Error Message (if failed) */}
                          {row.original.status === 'failed' && row.original.error_message && (
                            <div>
                              <h4 className="text-sm font-semibold text-red-900 mb-2">Error:</h4>
                              <pre className="text-sm text-red-700 bg-red-50 border border-red-200 rounded p-3 overflow-x-auto whitespace-pre-wrap">
                                {row.original.error_message}
                              </pre>
                            </div>
                          )}

                          {/* View Full Details Button */}
                          <div>
                            <Link
                              href={`/dashboard/execution-history/${row.original.execution_id}`}
                              className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors"
                            >
                              View Full Details
                              <ExternalLink className="w-4 h-4" />
                            </Link>
                          </div>
                        </div>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              ))}
            </tbody>
          </table>
        </div>

        {/* Pagination (AC #2) */}
        <div className="px-6 py-4 border-t border-gray-200 flex items-center justify-between">
          <div className="text-sm text-gray-700">
            Page {page + 1} of {table.getPageCount()}
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setPage((p) => Math.max(0, p - 1))}
              disabled={page === 0}
              className="px-3 py-1.5 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              aria-label="Previous page"
            >
              Previous
            </button>
            <button
              onClick={() => setPage((p) => Math.min(table.getPageCount() - 1, p + 1))}
              disabled={page >= table.getPageCount() - 1}
              className="px-3 py-1.5 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              aria-label="Next page"
            >
              Next
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
