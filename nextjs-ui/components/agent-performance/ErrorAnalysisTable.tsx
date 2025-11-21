/**
 * Error Analysis Table Component
 * Story 15: Agent Performance Dashboard - Error Analysis
 * AC #1: Table display with columns
 * AC #2: Sorting, search, pagination, row click, CSV export
 * AC #6: Loading/empty/error states
 * AC #8: Accessibility (keyboard nav, ARIA)
 */

'use client';

import { useState, useMemo } from 'react';
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  flexRender,
  type SortingState,
  type ColumnDef,
} from '@tanstack/react-table';
import { ArrowUpDown, ArrowUp, ArrowDown, Search, Download, RefreshCw } from 'lucide-react';
import { useAgentErrorAnalysis } from '@/hooks/useAgentErrorAnalysis';
import { SeverityBadge } from './SeverityBadge';
import { ErrorDetailModal } from './ErrorDetailModal';
import { exportErrorsToCSV } from '@/lib/utils/csv-export';
import type { ErrorAnalysisDTO } from '@/types/agent-performance';

interface ErrorAnalysisTableProps {
  agentId: string | null;
  startDate: Date;
  endDate: Date;
}

export function ErrorAnalysisTable({ agentId, startDate, endDate }: ErrorAnalysisTableProps) {
  const [sorting, setSorting] = useState<SortingState>([]);
  const [searchFilter, setSearchFilter] = useState('');
  const [selectedError, setSelectedError] = useState<ErrorAnalysisDTO | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  // Fetch error analysis data with React Query
  const { data, isLoading, isError, refetch } = useAgentErrorAnalysis({
    agentId,
    startDate,
    endDate,
  });

  // Format timestamp for display
  const formatTimestamp = (isoString: string) => {
    return new Date(isoString).toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  // Truncate error message to 80 chars (AC #1)
  const truncateMessage = (message: string, maxLength: number = 80) => {
    if (message.length <= maxLength) return message;
    return message.substring(0, maxLength) + '...';
  };

  // Define table columns (AC #1)
  const columns = useMemo<ColumnDef<ErrorAnalysisDTO>[]>(
    () => [
      {
        accessorKey: 'error_type',
        header: ({ column }) => (
          <button
            className="flex items-center gap-2 font-medium text-left hover:text-gray-900"
            onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
            aria-label="Sort by error type"
          >
            Error Type
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
          <span className="font-medium text-gray-900">{getValue() as string}</span>
        ),
      },
      {
        accessorKey: 'error_message',
        header: ({ column }) => (
          <button
            className="flex items-center gap-2 font-medium text-left hover:text-gray-900"
            onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
            aria-label="Sort by error message"
          >
            Error Message
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
          <span
            className="text-gray-700 truncate block max-w-md"
            title={getValue() as string}
          >
            {truncateMessage(getValue() as string)}
          </span>
        ),
      },
      {
        accessorKey: 'occurrences',
        header: ({ column }) => (
          <button
            className="flex items-center gap-2 font-medium text-left hover:text-gray-900"
            onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
            aria-label="Sort by occurrences"
          >
            Occurrences
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
          <span className="font-semibold text-gray-900">{getValue() as number}</span>
        ),
      },
      {
        accessorKey: 'first_seen',
        header: ({ column }) => (
          <button
            className="flex items-center gap-2 font-medium text-left hover:text-gray-900"
            onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
            aria-label="Sort by first seen"
          >
            First Seen
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
          <span className="text-sm text-gray-600">{formatTimestamp(getValue() as string)}</span>
        ),
      },
      {
        accessorKey: 'last_seen',
        header: ({ column }) => (
          <button
            className="flex items-center gap-2 font-medium text-left hover:text-gray-900"
            onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
            aria-label="Sort by last seen"
          >
            Last Seen
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
          <span className="text-sm text-gray-600">{formatTimestamp(getValue() as string)}</span>
        ),
      },
      {
        accessorKey: 'affected_executions',
        header: ({ column }) => (
          <button
            className="flex items-center gap-2 font-medium text-left hover:text-gray-900"
            onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
            aria-label="Sort by affected executions"
          >
            Affected
            {column.getIsSorted() === 'asc' ? (
              <ArrowUp className="w-4 h-4" aria-hidden="true" />
            ) : column.getIsSorted() === 'desc' ? (
              <ArrowDown className="w-4 h-4" aria-hidden="true" />
            ) : (
              <ArrowUpDown className="w-4 h-4 text-gray-400" aria-hidden="true" />
            )}
          </button>
        ),
        cell: ({ getValue }) => <span className="text-gray-700">{getValue() as number}</span>,
      },
      {
        id: 'severity',
        accessorFn: (row) => row.occurrences,
        header: 'Severity',
        cell: ({ row }) => <SeverityBadge occurrences={row.original.occurrences} />,
      },
    ],
    []
  );

  // Filtered data based on search (AC #2)
  const filteredData = useMemo(() => {
    if (!data?.errors) return [];
    if (!searchFilter.trim()) return data.errors;

    const lowerSearch = searchFilter.toLowerCase();
    return data.errors.filter(
      (error) =>
        error.error_message.toLowerCase().includes(lowerSearch) ||
        error.error_type.toLowerCase().includes(lowerSearch)
    );
  }, [data?.errors, searchFilter]);

  // Initialize TanStack Table
  const table = useReactTable({
    data: filteredData,
    columns,
    state: {
      sorting,
    },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    initialState: {
      pagination: {
        pageSize: 20, // AC #2: 20 per page
      },
    },
  });

  // Handle row click to open modal (AC #2)
  const handleRowClick = (error: ErrorAnalysisDTO) => {
    setSelectedError(error);
    setIsModalOpen(true);
  };

  // Handle CSV export (AC #5)
  const handleExport = () => {
    if (!data?.errors || !agentId) return;
    exportErrorsToCSV(data.errors, agentId);
  };

  // Loading state (AC #6)
  if (isLoading) {
    return (
      <div className="space-y-4">
        <div className="h-10 w-64 bg-gray-200 animate-pulse rounded" />
        <div className="border border-gray-200 rounded-lg overflow-hidden">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="flex gap-4 p-4 border-b border-gray-100">
              <div className="h-6 w-24 bg-gray-200 animate-pulse rounded" />
              <div className="h-6 flex-1 bg-gray-200 animate-pulse rounded" />
              <div className="h-6 w-16 bg-gray-200 animate-pulse rounded" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  // Error state (AC #6)
  if (isError) {
    return (
      <div className="text-center py-12 bg-red-50 rounded-lg border border-red-200">
        <p className="text-red-700 mb-4">Failed to load error analysis</p>
        <button
          onClick={() => refetch()}
          className="inline-flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 transition-colors"
        >
          <RefreshCw className="w-4 h-4" />
          Retry
        </button>
      </div>
    );
  }

  // Empty state (AC #6)
  if (!data?.errors || data.errors.length === 0) {
    return (
      <div className="text-center py-12 bg-gray-50 rounded-lg border border-gray-200">
        <p className="text-gray-600">No errors found for selected time range</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header with search and export */}
      <div className="flex items-center justify-between gap-4">
        {/* Search input (AC #2: debounced) */}
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            placeholder="Search errors..."
            value={searchFilter}
            onChange={(e) => setSearchFilter(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            aria-label="Search error messages"
          />
        </div>

        {/* Row count and export button */}
        <div className="flex items-center gap-4">
          <span className="text-sm text-gray-600" role="status" aria-live="polite">
            Showing {filteredData.length} of {data.errors.length} errors
          </span>
          <button
            onClick={handleExport}
            className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
            aria-label="Export to CSV"
          >
            <Download className="w-4 h-4" />
            Export CSV
          </button>
        </div>
      </div>

      {/* Table */}
      <div className="border border-gray-200 rounded-lg overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            {table.getHeaderGroups().map((headerGroup) => (
              <tr key={headerGroup.id}>
                {headerGroup.headers.map((header) => (
                  <th
                    key={header.id}
                    className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
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
              <tr
                key={row.id}
                onClick={() => handleRowClick(row.original)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    handleRowClick(row.original);
                  }
                }}
                tabIndex={0}
                className="cursor-pointer hover:bg-gray-50 transition-colors focus:outline-none focus:ring-2 focus:ring-inset focus:ring-blue-500"
                role="button"
                aria-label={`View details for ${row.original.error_type}`}
              >
                {row.getVisibleCells().map((cell) => (
                  <td key={cell.id} className="px-4 py-3 text-sm">
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination (AC #2) */}
      <div className="flex items-center justify-between">
        <div className="text-sm text-gray-600">
          Page {table.getState().pagination.pageIndex + 1} of {table.getPageCount()}
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => table.previousPage()}
            disabled={!table.getCanPreviousPage()}
            className="px-4 py-2 border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            aria-label="Previous page"
          >
            Previous
          </button>
          <button
            onClick={() => table.nextPage()}
            disabled={!table.getCanNextPage()}
            className="px-4 py-2 border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            aria-label="Next page"
          >
            Next
          </button>
        </div>
      </div>

      {/* Error Detail Modal (AC #4) */}
      <ErrorDetailModal error={selectedError} isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} />
    </div>
  );
}
