/**
 * Health Logs Component
 *
 * Displays health check history for an MCP server with auto-refresh
 */

'use client';

import React from 'react';
import { useMCPServerHealthLogs } from '@/lib/hooks/useMCPServers';
import { Activity, CheckCircle, XCircle, RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui/Button';

interface HealthLogsProps {
  serverId: string;
  limit?: number;
}

export function HealthLogs({ serverId, limit = 10 }: HealthLogsProps) {
  const { data: logs, isLoading, isError, refetch, isFetching } = useMCPServerHealthLogs(
    serverId,
    limit
  );

  if (isLoading) {
    return (
      <div className="glass-card p-12 text-center">
        <div className="animate-pulse space-y-3">
          <div className="h-4 bg-white/50 rounded w-3/4 mx-auto" />
          <div className="h-4 bg-white/50 rounded w-1/2 mx-auto" />
          <div className="h-4 bg-white/50 rounded w-2/3 mx-auto" />
        </div>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="glass-card p-12 text-center">
        <XCircle className="h-12 w-12 text-destructive mx-auto mb-4" />
        <h3 className="text-lg font-semibold text-text-primary mb-2">
          Failed to Load Health Logs
        </h3>
        <p className="text-text-secondary mb-6">
          There was an error loading the health check history.
        </p>
        <Button onClick={() => refetch()} variant="secondary" className="gap-2">
          <RefreshCw className="h-4 w-4" />
          Retry
        </Button>
      </div>
    );
  }

  if (!logs || logs.length === 0) {
    return (
      <div className="glass-card p-12 text-center">
        <Activity className="h-12 w-12 text-text-secondary mx-auto mb-4" />
        <h3 className="text-lg font-semibold text-text-primary mb-2">
          No Health Checks Yet
        </h3>
        <p className="text-text-secondary">
          Health check logs will appear here once the server has been monitored.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-text-primary">
          Health Check History
        </h3>
        <Button
          onClick={() => refetch()}
          variant="secondary"
          size="sm"
          disabled={isFetching}
          className="gap-2"
        >
          <RefreshCw className={`h-4 w-4 ${isFetching ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      <div className="space-y-2">
        {logs.map((log) => (
          <div key={log.id} className="glass-card p-4">
            <div className="flex items-start gap-4">
              {/* Status Icon */}
              <div className="flex-shrink-0 mt-0.5">
                {log.status === 'healthy' ? (
                  <div className="w-10 h-10 rounded-lg bg-green-100 flex items-center justify-center">
                    <CheckCircle className="h-5 w-5 text-green-600" />
                  </div>
                ) : (
                  <div className="w-10 h-10 rounded-lg bg-red-100 flex items-center justify-center">
                    <XCircle className="h-5 w-5 text-red-600" />
                  </div>
                )}
              </div>

              {/* Log Details */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between gap-4">
                  <h4
                    className={`text-sm font-semibold ${
                      log.status === 'healthy' ? 'text-green-700' : 'text-red-700'
                    }`}
                  >
                    {log.status === 'healthy' ? 'Healthy' : 'Unhealthy'}
                  </h4>
                  <span className="text-xs text-text-secondary">
                    {new Date(log.checked_at).toLocaleString()}
                  </span>
                </div>

                {log.response_time_ms !== null && log.response_time_ms !== undefined && (
                  <p className="text-sm text-text-secondary mt-1">
                    Response time: {log.response_time_ms}ms
                  </p>
                )}

                {log.error && (
                  <div className="mt-2 p-2 bg-red-50 border border-red-200 rounded">
                    <p className="text-xs text-red-800 font-mono">{log.error}</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Auto-refresh Notice */}
      <p className="text-xs text-text-secondary text-center">
        Auto-refreshes every 60 seconds • Showing last {limit} checks
      </p>
    </div>
  );
}
