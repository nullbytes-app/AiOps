/**
 * Execution Filters Component
 *
 * Advanced filter form for execution history with date range,
 * status, agent selection, and search input
 */

import { useState, useEffect } from 'react';
import { Search, Calendar, Filter, X } from 'lucide-react';
import { useAgentOptions, type ExecutionFilters, type ExecutionStatus } from '@/lib/hooks/useExecutions';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { Button } from '@/components/ui/Button';

interface ExecutionFiltersProps {
  filters: ExecutionFilters;
  onFiltersChange: (filters: ExecutionFilters) => void;
}

const STATUS_OPTIONS: { value: ExecutionStatus; label: string }[] = [
  { value: 'pending', label: 'Pending' },
  { value: 'processing', label: 'Processing' },
  { value: 'completed', label: 'Completed' },
  { value: 'failed', label: 'Failed' },
  { value: 'cancelled', label: 'Cancelled' },
];

export function ExecutionFilters({ filters, onFiltersChange }: ExecutionFiltersProps) {
  const { data: agentOptions = [] } = useAgentOptions();

  // Local state for debounced search
  const [searchInput, setSearchInput] = useState(filters.search || '');

  // Debounce search input (500ms)
  useEffect(() => {
    const timer = setTimeout(() => {
      if (searchInput !== filters.search) {
        onFiltersChange({ ...filters, search: searchInput, page: 1 });
      }
    }, 500);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchInput]);

  const handleStatusChange = (statusValue: string) => {
    let newStatus: ExecutionStatus[] = [...(filters.status || [])];
    const status = statusValue as ExecutionStatus;

    if (newStatus.includes(status)) {
      newStatus = newStatus.filter((s) => s !== status);
    } else {
      newStatus.push(status);
    }

    onFiltersChange({ ...filters, status: newStatus, page: 1 });
  };

  const handleAgentChange = (value: string) => {
    onFiltersChange({ ...filters, agent_id: value || undefined, page: 1 });
  };

  const handleDateChange = (field: 'date_from' | 'date_to', value: string) => {
    onFiltersChange({ ...filters, [field]: value || undefined, page: 1 });
  };

  const handleReset = () => {
    setSearchInput('');
    onFiltersChange({
      page: 1,
      limit: filters.limit,
    });
  };

  const hasActiveFilters = !!(
    filters.search ||
    filters.date_from ||
    filters.date_to ||
    (filters.status && filters.status.length > 0) ||
    filters.agent_id
  );

  return (
    <div className="space-y-4 rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-800 p-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Filter className="h-5 w-5 text-neutral-500" />
          <h3 className="text-sm font-semibold text-neutral-900 dark:text-white">Filters</h3>
        </div>
        {hasActiveFilters && (
          <Button
            variant="ghost"
            size="sm"
            onClick={handleReset}
            className="text-sm text-neutral-600 hover:text-neutral-900 dark:text-neutral-400 dark:hover:text-white"
          >
            <X className="h-4 w-4 mr-1" />
            Reset
          </Button>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Search */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-neutral-400" />
          <Input
            type="text"
            placeholder="Search executions..."
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            className="pl-10"
          />
        </div>

        {/* Agent Filter */}
        <Select
          value={filters.agent_id || ''}
          onChange={(e) => handleAgentChange(e.target.value)}
          options={[
            { value: '', label: 'All Agents' },
            ...agentOptions.map((agent) => ({
              value: agent.id,
              label: agent.name,
            })),
          ]}
        />

        {/* Date From */}
        <div className="relative">
          <Calendar className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-neutral-400 pointer-events-none" />
          <Input
            type="datetime-local"
            placeholder="From date"
            value={filters.date_from ? filters.date_from.slice(0, 16) : ''}
            onChange={(e) => handleDateChange('date_from', e.target.value ? new Date(e.target.value).toISOString() : '')}
            className="pl-10"
          />
        </div>

        {/* Date To */}
        <div className="relative">
          <Calendar className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-neutral-400 pointer-events-none" />
          <Input
            type="datetime-local"
            placeholder="To date"
            value={filters.date_to ? filters.date_to.slice(0, 16) : ''}
            onChange={(e) => handleDateChange('date_to', e.target.value ? new Date(e.target.value).toISOString() : '')}
            className="pl-10"
          />
        </div>
      </div>

      {/* Status Checkboxes */}
      <div>
        <label className="text-xs font-medium text-neutral-700 dark:text-neutral-300 mb-2 block">
          Status
        </label>
        <div className="flex flex-wrap gap-2">
          {STATUS_OPTIONS.map((option) => {
            const isActive = filters.status?.includes(option.value) ?? false;
            return (
              <button
                key={option.value}
                type="button"
                onClick={() => handleStatusChange(option.value)}
                className={`px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${
                  isActive
                    ? 'bg-primary-500 text-white'
                    : 'bg-neutral-100 text-neutral-700 hover:bg-neutral-200 dark:bg-neutral-700 dark:text-neutral-300 dark:hover:bg-neutral-600'
                }`}
              >
                {option.label}
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
