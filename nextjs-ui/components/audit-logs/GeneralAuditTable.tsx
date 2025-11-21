/**
 * General Audit Table Component
 *
 * Displays CRUD operation audit logs (create, update, delete) across all entities
 * (agents, tenants, MCP servers, plugins, prompts, tools) with filtering and diff view.
 */

'use client';

import { useState } from 'react';
import { useGeneralAuditLogs, GeneralAuditFilters } from '@/lib/hooks/useAudit';
import { GeneralAuditLog } from '@/lib/api/audit';
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from '@/components/ui/Table';
import { Badge } from '@/components/ui/Badge';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { Button } from '@/components/ui/Button';
import { Search, Eye } from 'lucide-react';
import { Loading } from '@/components/ui/Loading';
import { AuditDiffModal } from './AuditDiffModal';

const ACTION_OPTIONS = [
  { value: '', label: 'All Actions' },
  { value: 'create', label: 'Create' },
  { value: 'update', label: 'Update' },
  { value: 'delete', label: 'Delete' },
];

const ENTITY_TYPE_OPTIONS = [
  { value: '', label: 'All Entities' },
  { value: 'agent', label: 'Agent' },
  { value: 'tenant', label: 'Tenant' },
  { value: 'mcp_server', label: 'MCP Server' },
  { value: 'plugin', label: 'Plugin' },
  { value: 'prompt', label: 'Prompt' },
  { value: 'tool', label: 'Tool' },
];

interface GeneralAuditTableProps {
  /** Initial filters */
  initialFilters?: Partial<GeneralAuditFilters>;
}

/**
 * Table component for general CRUD audit logs
 *
 * @example
 * ```tsx
 * <GeneralAuditTable initialFilters={{ action: 'update' }} />
 * ```
 */
export function GeneralAuditTable({
  initialFilters = {},
}: GeneralAuditTableProps) {
  const [filters, setFilters] = useState<GeneralAuditFilters>({
    page: 1,
    limit: 100,
    ...initialFilters,
  });

  const [selectedDiffId, setSelectedDiffId] = useState<string | null>(null);

  const { data, isLoading, error } = useGeneralAuditLogs(filters);

  // Update filter handler
  const updateFilter = (
    key: keyof GeneralAuditFilters,
    value: string | number
  ) => {
    setFilters((prev) => ({
      ...prev,
      [key]: value,
      page: 1, // Reset to first page when filtering
    }));
  };

  // Action badge color
  const getActionColor = (
    action: string
  ): 'success' | 'warning' | 'error' => {
    const colors: Record<string, 'success' | 'warning' | 'error'> = {
      create: 'success',
      update: 'warning',
      delete: 'error',
    };
    return colors[action] || 'default' as 'success';
  };

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="flex flex-wrap items-end gap-4 p-4 bg-muted/30 border border-border rounded-lg">
        {/* User Email Search */}
        <div className="flex-1 min-w-[200px]">
          <label className="block text-sm font-medium text-foreground mb-1">
            Search User
          </label>
          <Input
            type="text"
            placeholder="Email address..."
            value={filters.user_email || ''}
            onChange={(e) => updateFilter('user_email', e.target.value)}
            icon={<Search className="h-5 w-5" />}
          />
        </div>

        {/* Action Filter */}
        <div className="w-40">
          <label className="block text-sm font-medium text-foreground mb-1">
            Action
          </label>
          <Select
            value={filters.action || ''}
            onChange={(e) => updateFilter('action', e.target.value)}
            options={ACTION_OPTIONS}
          />
        </div>

        {/* Entity Type Filter */}
        <div className="w-48">
          <label className="block text-sm font-medium text-foreground mb-1">
            Entity Type
          </label>
          <Select
            value={filters.entity_type || ''}
            onChange={(e) => updateFilter('entity_type', e.target.value)}
            options={ENTITY_TYPE_OPTIONS}
          />
        </div>

        {/* Date Range */}
        <div className="flex items-end space-x-2">
          <div>
            <label className="block text-sm font-medium text-foreground mb-1">
              From
            </label>
            <Input
              type="date"
              value={filters.date_from || ''}
              onChange={(e) => updateFilter('date_from', e.target.value)}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-foreground mb-1">
              To
            </label>
            <Input
              type="date"
              value={filters.date_to || ''}
              onChange={(e) => updateFilter('date_to', e.target.value)}
            />
          </div>
        </div>

        {/* Clear Filters */}
        <Button
          variant="ghost"
          size="sm"
          onClick={() =>
            setFilters({
              page: 1,
              limit: 100,
            })
          }
        >
          Clear Filters
        </Button>
      </div>

      {/* Table */}
      <div className="border border-border rounded-lg bg-card">
        {isLoading && (
          <div className="flex items-center justify-center py-12">
            <Loading size="lg" />
          </div>
        )}

        {error && (
          <div className="text-destructive text-center py-8">
            <p className="font-medium">Failed to load audit logs</p>
            <p className="text-sm text-muted-foreground mt-1">
              {error.message}
            </p>
          </div>
        )}

        {!isLoading && !error && data && (
          <>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Timestamp</TableHead>
                  <TableHead>User</TableHead>
                  <TableHead>Tenant</TableHead>
                  <TableHead>Action</TableHead>
                  <TableHead>Entity Type</TableHead>
                  <TableHead>Entity ID</TableHead>
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.logs.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={7} className="text-center py-8">
                      <p className="text-muted-foreground">
                        No audit logs found
                      </p>
                    </TableCell>
                  </TableRow>
                ) : (
                  data.logs.map((log: GeneralAuditLog) => (
                    <TableRow key={log.id}>
                      <TableCell>
                        <span className="text-sm text-foreground">
                          {new Date(log.created_at).toLocaleString()}
                        </span>
                      </TableCell>
                      <TableCell>
                        <span className="text-sm font-medium text-foreground">
                          {log.user_email}
                        </span>
                      </TableCell>
                      <TableCell>
                        <span className="text-sm text-muted-foreground">
                          {log.tenant_name}
                        </span>
                      </TableCell>
                      <TableCell>
                        <Badge variant={getActionColor(log.action)}>
                          {log.action}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <span className="text-sm font-medium text-foreground capitalize">
                          {log.entity_type.replace(/_/g, ' ')}
                        </span>
                      </TableCell>
                      <TableCell>
                        <span className="text-sm font-mono text-muted-foreground">
                          {log.entity_id.substring(0, 8)}...
                        </span>
                      </TableCell>
                      <TableCell>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setSelectedDiffId(log.id)}
                          disabled={log.action === 'delete' && !log.old_value}
                        >
                          <Eye className="h-4 w-4 mr-1" />
                          View Changes
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>

            {/* Pagination */}
            {data.pages > 1 && (
              <div className="flex items-center justify-between px-6 py-4 border-t border-border">
                <div className="text-sm text-muted-foreground">
                  Showing page {data.page} of {data.pages} ({data.total} total
                  records)
                </div>
                <div className="flex items-center space-x-2">
                  <Button
                    variant="secondary"
                    size="sm"
                    disabled={data.page === 1}
                    onClick={() => updateFilter('page', data.page - 1)}
                  >
                    Previous
                  </Button>
                  <Button
                    variant="secondary"
                    size="sm"
                    disabled={data.page === data.pages}
                    onClick={() => updateFilter('page', data.page + 1)}
                  >
                    Next
                  </Button>
                </div>
              </div>
            )}
          </>
        )}
      </div>

      {/* Diff Modal */}
      <AuditDiffModal
        auditLogId={selectedDiffId}
        isOpen={!!selectedDiffId}
        onClose={() => setSelectedDiffId(null)}
      />
    </div>
  );
}
