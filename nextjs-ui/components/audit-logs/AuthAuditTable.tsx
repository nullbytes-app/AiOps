/**
 * Auth Audit Table Component
 *
 * Displays authentication events (login, logout, password changes, failed attempts)
 * with filtering by date range, user email, event type, and success status.
 */

'use client';

import { useState } from 'react';
import { useAuthAuditLogs, AuthAuditFilters } from '@/lib/hooks/useAudit';
import { AuthAuditLog } from '@/lib/api/audit';
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
import { CheckCircle, XCircle, Search } from 'lucide-react';
import { Loading } from '@/components/ui/Loading';

const EVENT_TYPE_OPTIONS = [
  { value: '', label: 'All Events' },
  { value: 'login', label: 'Login' },
  { value: 'logout', label: 'Logout' },
  { value: 'password_change', label: 'Password Change' },
  { value: 'password_reset', label: 'Password Reset' },
  { value: 'failed_login', label: 'Failed Login' },
  { value: 'account_locked', label: 'Account Locked' },
];

const SUCCESS_OPTIONS = [
  { value: '', label: 'All' },
  { value: 'true', label: 'Success' },
  { value: 'false', label: 'Failed' },
];

interface AuthAuditTableProps {
  /** Initial filters */
  initialFilters?: Partial<AuthAuditFilters>;
}

/**
 * Table component for authentication audit logs
 *
 * @example
 * ```tsx
 * <AuthAuditTable initialFilters={{ event_type: 'login' }} />
 * ```
 */
export function AuthAuditTable({ initialFilters = {} }: AuthAuditTableProps) {
  const [filters, setFilters] = useState<AuthAuditFilters>({
    page: 1,
    limit: 100,
    ...initialFilters,
  });

  const { data, isLoading, error } = useAuthAuditLogs(filters);

  // Update filter handler
  const updateFilter = (
    key: keyof AuthAuditFilters,
    value: string | number | boolean | null
  ) => {
    setFilters((prev) => ({
      ...prev,
      [key]: value,
      page: 1, // Reset to first page when filtering
    }));
  };

  // Event type badge color
  const getEventTypeColor = (
    eventType: string
  ): 'success' | 'default' | 'warning' | 'error' => {
    const colors: Record<string, 'success' | 'default' | 'warning' | 'error'> =
      {
        login: 'success',
        logout: 'default',
        password_change: 'warning',
        password_reset: 'warning',
        failed_login: 'error',
        account_locked: 'error',
      };
    return colors[eventType] || 'default';
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

        {/* Event Type Filter */}
        <div className="w-48">
          <label className="block text-sm font-medium text-foreground mb-1">
            Event Type
          </label>
          <Select
            value={filters.event_type || ''}
            onChange={(e) => updateFilter('event_type', e.target.value)}
            options={EVENT_TYPE_OPTIONS}
          />
        </div>

        {/* Success Filter */}
        <div className="w-32">
          <label className="block text-sm font-medium text-foreground mb-1">
            Status
          </label>
          <Select
            value={
              filters.success === null || filters.success === undefined
                ? ''
                : filters.success.toString()
            }
            onChange={(e) =>
              updateFilter(
                'success',
                e.target.value === '' ? null : e.target.value === 'true'
              )
            }
            options={SUCCESS_OPTIONS}
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
            <p className="font-medium">Failed to load auth audit logs</p>
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
                  <TableHead>Event Type</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>IP Address</TableHead>
                  <TableHead>User Agent</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.logs.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={6} className="text-center py-8">
                      <p className="text-muted-foreground">
                        No authentication events found
                      </p>
                    </TableCell>
                  </TableRow>
                ) : (
                  data.logs.map((log: AuthAuditLog) => (
                    <TableRow key={log.id}>
                      <TableCell>
                        <span className="text-sm text-foreground">
                          {new Date(log.created_at).toLocaleString()}
                        </span>
                      </TableCell>
                      <TableCell>
                        <span className="text-sm font-medium text-foreground">
                          {log.user_email || 'Unknown'}
                        </span>
                      </TableCell>
                      <TableCell>
                        <Badge variant={getEventTypeColor(log.event_type)}>
                          {log.event_type.replace(/_/g, ' ')}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        {log.success ? (
                          <div className="flex items-center space-x-1 text-green-600">
                            <CheckCircle className="h-5 w-5" />
                            <span className="text-sm font-medium">Success</span>
                          </div>
                        ) : (
                          <div className="flex items-center space-x-1 text-destructive">
                            <XCircle className="h-5 w-5" />
                            <span className="text-sm font-medium">Failed</span>
                          </div>
                        )}
                      </TableCell>
                      <TableCell>
                        <span className="text-sm font-mono text-muted-foreground">
                          {log.ip_address}
                        </span>
                      </TableCell>
                      <TableCell>
                        <span className="text-sm text-muted-foreground truncate max-w-xs block">
                          {log.user_agent}
                        </span>
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
    </div>
  );
}
