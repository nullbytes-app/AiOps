/**
 * Execution Detail Modal Component
 *
 * 3-tab modal displaying execution details with syntax-highlighted JSON
 * using @uiw/react-json-view. Tabs: Input, Output, Metadata/Logs
 */

import { Fragment } from 'react';
import { X, Clock, AlertCircle, CheckCircle, Loader2 } from 'lucide-react';
import JsonView from '@uiw/react-json-view';
import { darkTheme } from '@uiw/react-json-view/dark';
import { lightTheme } from '@uiw/react-json-view/light';
import { formatDistanceToNow, format } from 'date-fns';
import { Modal } from '@/components/ui/Modal';
import { Tabs } from '@/components/ui/Tabs';
import { Badge } from '@/components/ui/Badge';
import { Loading } from '@/components/ui/Loading';
import { useExecutionDetail, type ExecutionStatus } from '@/lib/hooks/useExecutions';

interface ExecutionDetailModalProps {
  executionId: string | null;
  onClose: () => void;
  isDarkMode?: boolean;
}

const STATUS_ICONS: Record<ExecutionStatus, React.ReactNode> = {
  completed: <CheckCircle className="h-5 w-5 text-green-500" />,
  failed: <AlertCircle className="h-5 w-5 text-red-500" />,
  processing: <Loader2 className="h-5 w-5 text-blue-500 animate-spin" />,
  pending: <Clock className="h-5 w-5 text-neutral-400" />,
  cancelled: <X className="h-5 w-5 text-orange-500" />,
};

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
  if (ms < 60000) return `${(ms / 1000).toFixed(2)}s`;
  return `${(ms / 60000).toFixed(2)}m`;
}

export function ExecutionDetailModal({ executionId, onClose, isDarkMode = false }: ExecutionDetailModalProps) {
  const { data: execution, isLoading, error } = useExecutionDetail(executionId);

  if (!executionId) return null;

  return (
    <Modal isOpen={!!executionId} onClose={onClose} size="xl">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <h2 className="text-2xl font-bold text-neutral-900 dark:text-white">
            Execution Details
          </h2>
          {execution && (
            <Badge variant={STATUS_COLORS[execution.status]} size="md">
              {STATUS_ICONS[execution.status]}
              <span className="ml-2">{execution.status}</span>
            </Badge>
          )}
        </div>
        <button
          onClick={onClose}
          className="text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-200 transition-colors"
        >
          <X className="h-6 w-6" />
        </button>
      </div>

      {isLoading && (
        <div className="flex items-center justify-center py-16">
          <Loading />
        </div>
      )}

      {error && (
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <AlertCircle className="h-12 w-12 text-red-500 mb-4" />
          <p className="text-lg font-medium text-neutral-900 dark:text-white">
            Failed to load execution details
          </p>
          <p className="text-sm text-neutral-600 dark:text-neutral-400 mt-2">
            {error instanceof Error ? error.message : 'An error occurred'}
          </p>
        </div>
      )}

      {execution && (
        <>
          {/* Summary Header */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6 p-4 rounded-lg bg-neutral-50 dark:bg-neutral-800">
            <div>
              <div className="text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase mb-1">
                Execution ID
              </div>
              <div className="text-sm font-mono text-neutral-900 dark:text-white truncate">
                {execution.id.slice(0, 12)}...
              </div>
            </div>
            <div>
              <div className="text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase mb-1">
                Agent
              </div>
              <div className="text-sm font-medium text-neutral-900 dark:text-white">
                {execution.agent_name}
              </div>
            </div>
            <div>
              <div className="text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase mb-1">
                Duration
              </div>
              <div className="text-sm text-neutral-900 dark:text-white tabular-nums">
                {formatDuration(execution.duration_ms)}
              </div>
            </div>
            <div>
              <div className="text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase mb-1">
                Started
              </div>
              <div className="text-sm text-neutral-900 dark:text-white">
                {formatDistanceToNow(new Date(execution.started_at), { addSuffix: true })}
              </div>
              <div className="text-xs text-neutral-500 dark:text-neutral-400">
                {format(new Date(execution.started_at), 'MMM d, HH:mm:ss')}
              </div>
            </div>
          </div>

          {/* Error Message (if failed) */}
          {execution.status === 'failed' && execution.error_message && (
            <div className="mb-6 p-4 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800">
              <div className="flex items-start gap-3">
                <AlertCircle className="h-5 w-5 text-red-600 dark:text-red-400 mt-0.5 flex-shrink-0" />
                <div>
                  <div className="text-sm font-medium text-red-900 dark:text-red-200 mb-1">
                    Error Message
                  </div>
                  <div className="text-sm text-red-700 dark:text-red-300 font-mono whitespace-pre-wrap">
                    {execution.error_message}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Tabs */}
          <Tabs
            tabs={[
              {
                key: 'input',
                label: 'Input',
                content: (
                  <div className="rounded-lg border border-neutral-200 dark:border-neutral-700 overflow-hidden">
                    <JsonView
                      value={execution.input}
                      style={isDarkMode ? darkTheme : lightTheme}
                      displayDataTypes={false}
                      collapsed={2}
                      enableClipboard
                    />
                  </div>
                ),
              },
              {
                key: 'output',
                label: 'Output',
                content: (
                  <div className="rounded-lg border border-neutral-200 dark:border-neutral-700 overflow-hidden">
                    {execution.output ? (
                      <JsonView
                        value={execution.output}
                        style={isDarkMode ? darkTheme : lightTheme}
                        displayDataTypes={false}
                        collapsed={2}
                        enableClipboard
                      />
                    ) : (
                      <div className="flex flex-col items-center justify-center py-16 text-center">
                        <div className="text-neutral-400 dark:text-neutral-600">
                          <p className="text-lg font-medium">No output available</p>
                          <p className="text-sm">
                            {execution.status === 'completed'
                              ? 'Execution completed without output'
                              : 'Execution has not completed yet'}
                          </p>
                        </div>
                      </div>
                    )}
                  </div>
                ),
              },
              {
                key: 'metadata',
                label: 'Metadata & Logs',
                content: (
                  <div className="space-y-4">
                    {/* Metadata Section */}
                    <div>
                      <h3 className="text-sm font-semibold text-neutral-900 dark:text-white mb-2">
                        Metadata
                      </h3>
                      <div className="rounded-lg border border-neutral-200 dark:border-neutral-700 overflow-hidden">
                        <JsonView
                          value={execution.metadata}
                          style={isDarkMode ? darkTheme : lightTheme}
                          displayDataTypes={false}
                          collapsed={1}
                          enableClipboard
                        />
                      </div>
                    </div>

                    {/* Logs Section */}
                    {execution.logs && execution.logs.length > 0 && (
                      <div>
                        <h3 className="text-sm font-semibold text-neutral-900 dark:text-white mb-2">
                          Execution Logs ({execution.logs.length})
                        </h3>
                        <div className="space-y-2 max-h-96 overflow-y-auto">
                          {execution.logs.map((log, index) => (
                            <div
                              key={index}
                              className={`p-3 rounded-lg border text-sm font-mono ${
                                log.level === 'error'
                                  ? 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800 text-red-900 dark:text-red-200'
                                  : log.level === 'warning'
                                  ? 'bg-orange-50 dark:bg-orange-900/20 border-orange-200 dark:border-orange-800 text-orange-900 dark:text-orange-200'
                                  : 'bg-neutral-50 dark:bg-neutral-800 border-neutral-200 dark:border-neutral-700 text-neutral-900 dark:text-white'
                              }`}
                            >
                              <div className="flex items-start justify-between gap-2 mb-1">
                                <span className="font-semibold uppercase text-xs">
                                  {log.level}
                                </span>
                                <span className="text-xs text-neutral-500 dark:text-neutral-400">
                                  {format(new Date(log.timestamp), 'HH:mm:ss.SSS')}
                                </span>
                              </div>
                              <div className="whitespace-pre-wrap">{log.message}</div>
                              {log.context && (
                                <details className="mt-2">
                                  <summary className="cursor-pointer text-xs text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-white">
                                    View Context
                                  </summary>
                                  <div className="mt-2 p-2 rounded bg-white dark:bg-neutral-900 border border-neutral-200 dark:border-neutral-700">
                                    <JsonView
                                      value={log.context}
                                      style={isDarkMode ? darkTheme : lightTheme}
                                      displayDataTypes={false}
                                      collapsed={1}
                                      enableClipboard={false}
                                    />
                                  </div>
                                </details>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                ),
              },
            ]}
            variant="pills"
          />
        </>
      )}
    </Modal>
  );
}
