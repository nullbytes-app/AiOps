/**
 * Execution Table Component
 *
 * Sortable, paginated table using TanStack Table v8 with status badges,
 * duration formatting, and click-to-view-details functionality
 */

import { useMemo } from 'react';
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  flexRender,
  type ColumnDef,
  type SortingState,
  type OnChangeFn,
} from '@tanstack/react-table';
import { ArrowUpDown, ArrowUp, ArrowDown, Eye } from 'lucide-react';
import { formatDistanceToNow, format } from 'date-fns';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import type { AgentExecution, ExecutionStatus } from '@/lib/hooks/useExecutions';

interface ExecutionTableProps {
  executions: AgentExecution[];
  onRowClick: (execution: AgentExecution) => void;
  sorting?: SortingState;
  onSortingChange?: OnChangeFn<SortingState>;
}

const STATUS_COLORS: Record<ExecutionStatus, 'success' | 'warning' | 'error' | 'info' | 'default'> = {
  completed: 'success',
  processing: 'info',
  pending: 'default',
  failed: 'error',
  cancelled: 'warning',
};

function formatDuration(ms: number | null): string {
  if (!ms) return 'N/A';
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
  return `${(ms / 60000).toFixed(1)}m`;
}

export function ExecutionTable({ executions, onRowClick, sorting = [], onSortingChange }: ExecutionTableProps) {
  const columns = useMemo<ColumnDef<AgentExecution>[]>(
    () => [
      {
        accessorKey: 'id',
        header: 'Execution ID',
        cell: ({ row }) => (
          <div className="font-mono text-xs text-neutral-600 dark:text-neutral-400 truncate max-w-[120px]">
            {row.original.id.slice(0, 8)}
          </div>
        ),
        size: 120,
      },
      {
        accessorKey: 'agent_name',
        header: ({ column }) => (
          <button
            onClick={() => column.toggleSorting()}
            className="flex items-center gap-1 hover:text-neutral-900 dark:hover:text-white transition-colors"
          >
            Agent
            {column.getIsSorted() === 'asc' ? (
              <ArrowUp className="h-4 w-4" />
            ) : column.getIsSorted() === 'desc' ? (
              <ArrowDown className="h-4 w-4" />
            ) : (
              <ArrowUpDown className="h-4 w-4 opacity-40" />
            )}
          </button>
        ),
        cell: ({ row }) => (
          <div className="font-medium text-neutral-900 dark:text-white">
            {row.original.agent_name}
          </div>
        ),
      },
      {
        accessorKey: 'status',
        header: ({ column }) => (
          <button
            onClick={() => column.toggleSorting()}
            className="flex items-center gap-1 hover:text-neutral-900 dark:hover:text-white transition-colors"
          >
            Status
            {column.getIsSorted() === 'asc' ? (
              <ArrowUp className="h-4 w-4" />
            ) : column.getIsSorted() === 'desc' ? (
              <ArrowDown className="h-4 w-4" />
            ) : (
              <ArrowUpDown className="h-4 w-4 opacity-40" />
            )}
          </button>
        ),
        cell: ({ row }) => (
          <Badge variant={STATUS_COLORS[row.original.status]} size="sm">
            {row.original.status}
          </Badge>
        ),
      },
      {
        accessorKey: 'duration_ms',
        header: ({ column }) => (
          <button
            onClick={() => column.toggleSorting()}
            className="flex items-center gap-1 hover:text-neutral-900 dark:hover:text-white transition-colors"
          >
            Duration
            {column.getIsSorted() === 'asc' ? (
              <ArrowUp className="h-4 w-4" />
            ) : column.getIsSorted() === 'desc' ? (
              <ArrowDown className="h-4 w-4" />
            ) : (
              <ArrowUpDown className="h-4 w-4 opacity-40" />
            )}
          </button>
        ),
        cell: ({ row }) => (
          <div className="text-neutral-700 dark:text-neutral-300 tabular-nums">
            {formatDuration(row.original.duration_ms)}
          </div>
        ),
      },
      {
        accessorKey: 'started_at',
        header: ({ column }) => (
          <button
            onClick={() => column.toggleSorting()}
            className="flex items-center gap-1 hover:text-neutral-900 dark:hover:text-white transition-colors"
          >
            Started
            {column.getIsSorted() === 'asc' ? (
              <ArrowUp className="h-4 w-4" />
            ) : column.getIsSorted() === 'desc' ? (
              <ArrowDown className="h-4 w-4" />
            ) : (
              <ArrowUpDown className="h-4 w-4 opacity-40" />
            )}
          </button>
        ),
        cell: ({ row }) => {
          const date = new Date(row.original.started_at);
          return (
            <div className="text-sm">
              <div className="text-neutral-900 dark:text-white">
                {formatDistanceToNow(date, { addSuffix: true })}
              </div>
              <div className="text-xs text-neutral-500 dark:text-neutral-400">
                {format(date, 'MMM d, HH:mm:ss')}
              </div>
            </div>
          );
        },
      },
      {
        id: 'actions',
        header: '',
        cell: ({ row }) => (
          <Button
            variant="ghost"
            size="sm"
            onClick={(e) => {
              e.stopPropagation();
              onRowClick(row.original);
            }}
            className="text-neutral-600 hover:text-neutral-900 dark:text-neutral-400 dark:hover:text-white"
          >
            <Eye className="h-4 w-4 mr-1" />
            View
          </Button>
        ),
        size: 80,
      },
    ],
    [onRowClick]
  );

  const table = useReactTable({
    data: executions,
    columns,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    state: {
      sorting,
    },
    onSortingChange: onSortingChange,
    enableSortingRemoval: false, // Cycle between asc/desc only
  });

  if (executions.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center">
        <div className="text-neutral-400 dark:text-neutral-600 mb-2">
          <Eye className="h-12 w-12 mx-auto mb-4" />
          <p className="text-lg font-medium">No executions found</p>
          <p className="text-sm">Try adjusting your filters</p>
        </div>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-neutral-200 dark:border-neutral-700">
      <table className="w-full">
        <thead className="bg-neutral-50 dark:bg-neutral-800 border-b border-neutral-200 dark:border-neutral-700">
          {table.getHeaderGroups().map((headerGroup) => (
            <tr key={headerGroup.id}>
              {headerGroup.headers.map((header) => (
                <th
                  key={header.id}
                  className="px-4 py-3 text-left text-xs font-semibold text-neutral-700 dark:text-neutral-300 uppercase tracking-wider"
                  style={{ width: header.column.columnDef.size }}
                >
                  {header.isPlaceholder
                    ? null
                    : flexRender(header.column.columnDef.header, header.getContext())}
                </th>
              ))}
            </tr>
          ))}
        </thead>
        <tbody className="bg-white dark:bg-neutral-900 divide-y divide-neutral-200 dark:divide-neutral-700">
          {table.getRowModel().rows.map((row) => (
            <tr
              key={row.id}
              onClick={() => onRowClick(row.original)}
              className="hover:bg-neutral-50 dark:hover:bg-neutral-800 cursor-pointer transition-colors"
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
  );
}
