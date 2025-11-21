/**
 * AgentTable Component
 *
 * Sortable, paginated table showing individual agent performance metrics.
 * Follows 2025 accessibility and UX best practices.
 */

'use client';

import React, { useState, useMemo } from 'react';
import { AgentPerformance } from '@/lib/api/metrics';
import { ArrowUpDown, ArrowUp, ArrowDown, Search } from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';

export interface AgentTableProps {
  data: AgentPerformance[];
  className?: string;
}

type SortKey = keyof AgentPerformance;
type SortDirection = 'asc' | 'desc' | null;

const ROWS_PER_PAGE = 10;

/**
 * Format currency with specified decimals
 */
function formatCurrency(value: number, decimals: number = 2): string {
  return `$${value.toFixed(decimals)}`;
}

/**
 * Format latency in milliseconds
 */
function formatLatency(ms: number): string {
  return `${ms.toLocaleString()}ms`;
}

/**
 * Format success rate as percentage
 */
function formatSuccessRate(rate: number): string {
  return `${(rate * 100).toFixed(1)}%`;
}

/**
 * Sort icon component
 */
function SortIcon({ direction }: { direction: SortDirection }) {
  if (direction === 'asc') {
    return <ArrowUp className="h-4 w-4" aria-hidden="true" />;
  }
  if (direction === 'desc') {
    return <ArrowDown className="h-4 w-4" aria-hidden="true" />;
  }
  return <ArrowUpDown className="h-4 w-4" aria-hidden="true" />;
}

/**
 * AgentTable Component
 *
 * Displays agent performance data in a sortable, searchable table.
 *
 * @example
 * ```tsx
 * const { data } = useAgentMetrics('24h');
 *
 * <AgentTable data={data.tableData} />
 * ```
 */
export function AgentTable({ data, className = '' }: AgentTableProps) {
  const [sortKey, setSortKey] = useState<SortKey | null>(null);
  const [sortDirection, setSortDirection] = useState<SortDirection>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [currentPage, setCurrentPage] = useState(1);

  // Filter data based on search query
  const filteredData = useMemo(() => {
    if (!searchQuery.trim()) return data;

    const query = searchQuery.toLowerCase();
    return data.filter((agent) =>
      agent.agent_name.toLowerCase().includes(query)
    );
  }, [data, searchQuery]);

  // Sort filtered data
  const sortedData = useMemo(() => {
    if (!sortKey || !sortDirection) return filteredData;

    return [...filteredData].sort((a, b) => {
      const aValue = a[sortKey];
      const bValue = b[sortKey];

      if (typeof aValue === 'string' && typeof bValue === 'string') {
        return sortDirection === 'asc'
          ? aValue.localeCompare(bValue)
          : bValue.localeCompare(aValue);
      }

      if (typeof aValue === 'number' && typeof bValue === 'number') {
        return sortDirection === 'asc' ? aValue - bValue : bValue - aValue;
      }

      return 0;
    });
  }, [filteredData, sortKey, sortDirection]);

  // Paginate sorted data
  const paginatedData = useMemo(() => {
    const start = (currentPage - 1) * ROWS_PER_PAGE;
    const end = start + ROWS_PER_PAGE;
    return sortedData.slice(start, end);
  }, [sortedData, currentPage]);

  const totalPages = Math.ceil(sortedData.length / ROWS_PER_PAGE);

  // Handle column sort
  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      // Toggle direction: asc -> desc -> null -> asc
      if (sortDirection === 'asc') {
        setSortDirection('desc');
      } else if (sortDirection === 'desc') {
        setSortDirection(null);
        setSortKey(null);
      }
    } else {
      setSortKey(key);
      setSortDirection('asc');
    }
    setCurrentPage(1); // Reset to first page on sort
  };

  // Handle search
  const handleSearch = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchQuery(e.target.value);
    setCurrentPage(1); // Reset to first page on search
  };

  return (
    <Card className={`glass-card p-6 ${className}`}>
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-foreground">
          Agent Performance
        </h3>

        {/* Search Filter */}
        <div className="relative w-64">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            type="text"
            placeholder="Search agents..."
            value={searchQuery}
            onChange={handleSearch}
            className="pl-10"
            aria-label="Search agents by name"
          />
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full" role="table">
          <thead>
            <tr className="border-b border-border">
              <th className="text-left py-3 px-4">
                <button
                  onClick={() => handleSort('agent_name')}
                  className="flex items-center gap-2 font-semibold text-sm text-muted-foreground hover:text-foreground transition-colors"
                  aria-label={`Sort by agent name ${sortKey === 'agent_name' ? sortDirection : ''}`}
                >
                  Agent Name
                  <SortIcon direction={sortKey === 'agent_name' ? sortDirection : null} />
                </button>
              </th>
              <th className="text-right py-3 px-4">
                <button
                  onClick={() => handleSort('total_runs')}
                  className="flex items-center justify-end gap-2 font-semibold text-sm text-muted-foreground hover:text-foreground transition-colors w-full"
                  aria-label={`Sort by total runs ${sortKey === 'total_runs' ? sortDirection : ''}`}
                >
                  Total Runs
                  <SortIcon direction={sortKey === 'total_runs' ? sortDirection : null} />
                </button>
              </th>
              <th className="text-right py-3 px-4">
                <button
                  onClick={() => handleSort('success_rate')}
                  className="flex items-center justify-end gap-2 font-semibold text-sm text-muted-foreground hover:text-foreground transition-colors w-full"
                  aria-label={`Sort by success rate ${sortKey === 'success_rate' ? sortDirection : ''}`}
                >
                  Success Rate
                  <SortIcon direction={sortKey === 'success_rate' ? sortDirection : null} />
                </button>
              </th>
              <th className="text-right py-3 px-4">
                <button
                  onClick={() => handleSort('avg_latency_ms')}
                  className="flex items-center justify-end gap-2 font-semibold text-sm text-muted-foreground hover:text-foreground transition-colors w-full"
                  aria-label={`Sort by average latency ${sortKey === 'avg_latency_ms' ? sortDirection : ''}`}
                >
                  Avg Latency
                  <SortIcon direction={sortKey === 'avg_latency_ms' ? sortDirection : null} />
                </button>
              </th>
              <th className="text-right py-3 px-4">
                <button
                  onClick={() => handleSort('total_cost')}
                  className="flex items-center justify-end gap-2 font-semibold text-sm text-muted-foreground hover:text-foreground transition-colors w-full"
                  aria-label={`Sort by total cost ${sortKey === 'total_cost' ? sortDirection : ''}`}
                >
                  Total Cost
                  <SortIcon direction={sortKey === 'total_cost' ? sortDirection : null} />
                </button>
              </th>
            </tr>
          </thead>
          <tbody>
            {paginatedData.length === 0 ? (
              <tr>
                <td colSpan={5} className="text-center py-12 text-muted-foreground">
                  {searchQuery ? `No agents found matching "${searchQuery}"` : 'No agent data available'}
                </td>
              </tr>
            ) : (
              paginatedData.map((agent, index) => (
                <tr
                  key={`${agent.agent_name}-${index}`}
                  className="border-b border-border last:border-b-0 hover:bg-muted/50 transition-colors"
                >
                  <td className="py-3 px-4 font-medium text-foreground">
                    {agent.agent_name}
                  </td>
                  <td className="py-3 px-4 text-right text-foreground">
                    {agent.total_runs.toLocaleString()}
                  </td>
                  <td className="py-3 px-4 text-right">
                    <span
                      className={
                        agent.success_rate >= 0.95
                          ? 'text-success font-semibold'
                          : agent.success_rate >= 0.8
                          ? 'text-foreground'
                          : 'text-destructive font-semibold'
                      }
                    >
                      {formatSuccessRate(agent.success_rate)}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-right text-foreground">
                    {formatLatency(agent.avg_latency_ms)}
                  </td>
                  <td className="py-3 px-4 text-right text-foreground">
                    {formatCurrency(agent.total_cost, 4)}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between mt-6 pt-4 border-t border-border">
          <p className="text-sm text-muted-foreground">
            Showing {(currentPage - 1) * ROWS_PER_PAGE + 1} to{' '}
            {Math.min(currentPage * ROWS_PER_PAGE, sortedData.length)} of{' '}
            {sortedData.length} agents
          </p>

          <div className="flex gap-2">
            <Button
              variant="secondary"
              size="sm"
              onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
              disabled={currentPage === 1}
              aria-label="Previous page"
            >
              Previous
            </Button>
            <div className="flex items-center gap-1">
              {Array.from({ length: totalPages }, (_, i) => i + 1).map((page) => (
                <Button
                  key={page}
                  variant={currentPage === page ? 'primary' : 'ghost'}
                  size="sm"
                  onClick={() => setCurrentPage(page)}
                  aria-label={`Page ${page}`}
                  aria-current={currentPage === page ? 'page' : undefined}
                  className="w-10"
                >
                  {page}
                </Button>
              ))}
            </div>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
              disabled={currentPage === totalPages}
              aria-label="Next page"
            >
              Next
            </Button>
          </div>
        </div>
      )}
    </Card>
  );
}
