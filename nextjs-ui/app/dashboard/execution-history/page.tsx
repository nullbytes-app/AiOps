/**
 * Execution History Page
 *
 * Main page for viewing agent execution history with advanced filtering,
 * sorting, pagination, detail modal, and CSV export
 */

'use client';

import { useState } from 'react';
import { Download, RefreshCw } from 'lucide-react';
import { useTheme } from 'next-themes';
import { ExecutionFilters } from '@/components/execution-history/ExecutionFilters';
import { ExecutionTable } from '@/components/execution-history/ExecutionTable';
import { ExecutionDetailModal } from '@/components/execution-history/ExecutionDetailModal';
import { Button } from '@/components/ui/Button';
import { Loading } from '@/components/ui/Loading';
import { EmptyState } from '@/components/ui/EmptyState';
import {
  useExecutions,
  useExportExecutions,
  type ExecutionFilters as IExecutionFilters,
  type AgentExecution,
} from '@/lib/hooks/useExecutions';
import type { SortingState } from '@tanstack/react-table';

export default function ExecutionHistoryPage() {
  const { theme } = useTheme();
  const isDarkMode = theme === 'dark';

  // Filter & Pagination State
  const [filters, setFilters] = useState<IExecutionFilters>({
    page: 1,
    limit: 50,
  });

  // Sorting State (client-side only, API handles server-side if needed)
  const [sorting, setSorting] = useState<SortingState>([
    { id: 'started_at', desc: true }, // Default: newest first
  ]);

  // Detail Modal State
  const [selectedExecutionId, setSelectedExecutionId] = useState<string | null>(null);

  // Fetch executions
  const { data, isLoading, isError, error, refetch } = useExecutions(filters);
  const exportMutation = useExportExecutions();

  const handleFiltersChange = (newFilters: IExecutionFilters) => {
    setFilters(newFilters);
  };

  const handleRowClick = (execution: AgentExecution) => {
    setSelectedExecutionId(execution.id);
  };

  const handleCloseModal = () => {
    setSelectedExecutionId(null);
  };

  const handleExport = () => {
    exportMutation.mutate(filters);
  };

  const handleRefresh = () => {
    refetch();
  };

  const handlePageChange = (newPage: number) => {
    setFilters({ ...filters, page: newPage });
  };

  const handleLimitChange = (newLimit: number) => {
    setFilters({ ...filters, limit: newLimit, page: 1 });
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-neutral-900 dark:text-white">
            Execution History
          </h1>
          <p className="text-neutral-600 dark:text-neutral-400 mt-1">
            View and analyze agent execution records
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button
            variant="secondary"
            onClick={handleRefresh}
            disabled={isLoading}
          >
            <RefreshCw className={`h-4 w-4 mr-2 ${isLoading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
          <Button
            variant="primary"
            onClick={handleExport}
            disabled={exportMutation.isPending || isLoading || !data?.executions.length}
          >
            <Download className="h-4 w-4 mr-2" />
            {exportMutation.isPending ? 'Exporting...' : 'Export CSV'}
          </Button>
        </div>
      </div>

      {/* Filters */}
      <ExecutionFilters filters={filters} onFiltersChange={handleFiltersChange} />

      {/* Loading State */}
      {isLoading && (
        <div className="flex items-center justify-center py-16">
          <Loading />
        </div>
      )}

      {/* Error State */}
      {isError && (
        <EmptyState
          icon="error"
          title="Failed to load executions"
          description={error instanceof Error ? error.message : 'An error occurred'}
        />
      )}

      {/* Table */}
      {!isLoading && !isError && data && (
        <>
          <ExecutionTable
            executions={data.executions}
            onRowClick={handleRowClick}
            sorting={sorting}
            onSortingChange={setSorting}
          />

          {/* Pagination */}
          {data.pages > 1 && (
            <div className="flex items-center justify-between pt-4">
              <div className="flex items-center gap-2">
                <span className="text-sm text-neutral-600 dark:text-neutral-400">
                  Showing {(data.page - 1) * filters.limit! + 1} to{' '}
                  {Math.min(data.page * filters.limit!, data.total)} of {data.total} executions
                </span>
                <select
                  value={filters.limit}
                  onChange={(e) => handleLimitChange(Number(e.target.value))}
                  className="ml-4 px-3 py-1.5 text-sm border border-neutral-300 dark:border-neutral-600 rounded-md bg-white dark:bg-neutral-800 text-neutral-900 dark:text-white"
                >
                  <option value={25}>25 per page</option>
                  <option value={50}>50 per page</option>
                  <option value={100}>100 per page</option>
                </select>
              </div>

              <div className="flex items-center gap-2">
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => handlePageChange(data.page - 1)}
                  disabled={data.page === 1}
                >
                  Previous
                </Button>

                {/* Page Numbers */}
                <div className="flex items-center gap-1">
                  {Array.from({ length: Math.min(data.pages, 7) }, (_, i) => {
                    let pageNum: number;
                    if (data.pages <= 7) {
                      pageNum = i + 1;
                    } else if (data.page <= 4) {
                      pageNum = i + 1;
                    } else if (data.page >= data.pages - 3) {
                      pageNum = data.pages - 6 + i;
                    } else {
                      pageNum = data.page - 3 + i;
                    }

                    return (
                      <button
                        key={pageNum}
                        onClick={() => handlePageChange(pageNum)}
                        className={`px-3 py-1 text-sm rounded-md transition-colors ${
                          pageNum === data.page
                            ? 'bg-primary-500 text-white'
                            : 'text-neutral-700 dark:text-neutral-300 hover:bg-neutral-100 dark:hover:bg-neutral-700'
                        }`}
                      >
                        {pageNum}
                      </button>
                    );
                  })}
                </div>

                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => handlePageChange(data.page + 1)}
                  disabled={data.page === data.pages}
                >
                  Next
                </Button>
              </div>
            </div>
          )}
        </>
      )}

      {/* Detail Modal */}
      <ExecutionDetailModal
        executionId={selectedExecutionId}
        onClose={handleCloseModal}
        isDarkMode={isDarkMode}
      />
    </div>
  );
}
