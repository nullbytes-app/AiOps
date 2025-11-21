/**
 * Queue Task List Component
 *
 * Table displaying tasks in queue with:
 * - Columns: Task ID (truncated with copy), Agent Name, Status, Queued At, Priority, Actions
 * - Status badges (pending=blue, processing=yellow, failed=red, completed=green)
 * - Cancel action (operator+ only, pending/processing only)
 * - Pagination (20 tasks per page)
 * - Empty state
 *
 * Reference: Story 5, AC-1
 */

'use client';

import { useState } from 'react';
import { useSession } from 'next-auth/react';
import { formatDistanceToNow, parseISO } from 'date-fns';
import { Copy, X, Check, Loader2 } from 'lucide-react';
import { useQueueTasks, useCancelTask, type QueueTask } from '@/lib/hooks/useQueue';
import { toast } from 'sonner';

/**
 * Check if user can cancel tasks
 */
const canCancelTasks = (role?: string): boolean => {
  return role === 'tenant_admin' || role === 'operator';
};

/**
 * Get badge color for task status
 */
const getStatusBadge = (status: QueueTask['status']) => {
  const badges = {
    pending: 'bg-accent-blue/20 text-accent-blue',
    processing: 'bg-accent-orange/20 text-accent-orange',
    failed: 'bg-accent-red/20 text-accent-red',
    completed: 'bg-accent-green/20 text-accent-green',
  };
  return badges[status] || 'bg-gray-200 text-gray-700';
};

/**
 * Get badge for priority level
 */
const getPriorityBadge = (priority: number) => {
  if (priority === 1) return <span className="text-xs font-medium text-accent-red">High</span>;
  if (priority === 3) return <span className="text-xs font-medium text-text-secondary">Low</span>;
  return <span className="text-xs font-medium text-text-primary">Normal</span>;
};

/**
 * Copy text to clipboard
 */
const copyToClipboard = async (text: string) => {
  try {
    await navigator.clipboard.writeText(text);
    toast.success('Copied to clipboard');
  } catch {
    toast.error('Failed to copy');
  }
};

export function TaskList() {
  const { data: session } = useSession();
  const [page, setPage] = useState(1);
  const { data, isLoading, error } = useQueueTasks(page, 20);
  const cancelMutation = useCancelTask();

  const canCancel = canCancelTasks(session?.user?.role);

  if (isLoading) {
    return (
      <div className="glass-card p-6">
        <h3 className="text-h4 font-semibold text-text-primary mb-4">Task Queue</h3>
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-16 bg-white/20 rounded-lg animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="glass-card p-6">
        <h3 className="text-h4 font-semibold text-text-primary mb-4">Task Queue</h3>
        <p className="text-sm text-accent-red">Failed to load tasks</p>
      </div>
    );
  }

  if (data.tasks.length === 0) {
    return (
      <div className="glass-card p-6">
        <h3 className="text-h4 font-semibold text-text-primary mb-4">Task Queue</h3>
        <div className="text-center py-12">
          <Check className="w-12 h-12 text-accent-green mx-auto mb-3" />
          <p className="text-lg font-medium text-text-primary">
            Queue is empty. All tasks processed! 🎉
          </p>
        </div>
      </div>
    );
  }

  const handleCancel = (taskId: string) => {
    if (!confirm('Cancel this task? This action cannot be undone.')) {
      return;
    }
    cancelMutation.mutate(taskId);
  };

  return (
    <div className="glass-card p-6">
      <h3 className="text-h4 font-semibold text-text-primary mb-4">
        Task Queue ({data.total} tasks)
      </h3>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full" role="table" aria-label="Queue tasks">
          <thead>
            <tr className="border-b border-white/20">
              <th className="text-left py-3 px-2 text-xs font-semibold text-text-secondary uppercase">
                Task ID
              </th>
              <th className="text-left py-3 px-2 text-xs font-semibold text-text-secondary uppercase">
                Agent Name
              </th>
              <th className="text-left py-3 px-2 text-xs font-semibold text-text-secondary uppercase">
                Status
              </th>
              <th className="text-left py-3 px-2 text-xs font-semibold text-text-secondary uppercase">
                Queued At
              </th>
              <th className="text-left py-3 px-2 text-xs font-semibold text-text-secondary uppercase">
                Priority
              </th>
              {canCancel && (
                <th className="text-left py-3 px-2 text-xs font-semibold text-text-secondary uppercase">
                  Actions
                </th>
              )}
            </tr>
          </thead>
          <tbody>
            {data.tasks.map((task) => (
              <tr
                key={task.id}
                className="border-b border-white/10 hover:bg-white/10 transition-colors"
              >
                {/* Task ID with Copy */}
                <td className="py-3 px-2">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-mono text-text-primary">
                      {task.id.slice(0, 8)}...
                    </span>
                    <button
                      onClick={() => copyToClipboard(task.id)}
                      className="p-1 hover:bg-white/20 rounded transition-colors"
                      aria-label="Copy task ID"
                    >
                      <Copy className="w-3 h-3 text-text-secondary" />
                    </button>
                  </div>
                </td>

                {/* Agent Name */}
                <td className="py-3 px-2">
                  <span className="text-sm text-text-primary">{task.agent_name}</span>
                </td>

                {/* Status Badge */}
                <td className="py-3 px-2">
                  <span
                    className={`px-2 py-1 rounded-md text-xs font-medium ${getStatusBadge(
                      task.status
                    )}`}
                  >
                    {task.status}
                  </span>
                </td>

                {/* Queued At (Relative Time) */}
                <td className="py-3 px-2">
                  <span className="text-sm text-text-secondary">
                    {formatDistanceToNow(parseISO(task.queued_at), { addSuffix: true })}
                  </span>
                </td>

                {/* Priority */}
                <td className="py-3 px-2">{getPriorityBadge(task.priority)}</td>

                {/* Actions (Cancel) */}
                {canCancel && (
                  <td className="py-3 px-2">
                    {(task.status === 'pending' || task.status === 'processing') && (
                      <button
                        onClick={() => handleCancel(task.id)}
                        disabled={cancelMutation.isPending}
                        className="p-2 text-accent-red hover:bg-accent-red/10 rounded transition-colors disabled:opacity-50"
                        aria-label="Cancel task"
                      >
                        {cancelMutation.isPending ? (
                          <Loader2 className="w-4 h-4 animate-spin" />
                        ) : (
                          <X className="w-4 h-4" />
                        )}
                      </button>
                    )}
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {data.pages > 1 && (
        <div className="flex items-center justify-between mt-4 pt-4 border-t border-white/20">
          <p className="text-sm text-text-secondary">
            Page {page} of {data.pages}
          </p>
          <div className="flex gap-2">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
              className="px-3 py-1 text-sm bg-white/20 hover:bg-white/30 rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Previous
            </button>
            <button
              onClick={() => setPage((p) => Math.min(data.pages, p + 1))}
              disabled={page === data.pages}
              className="px-3 py-1 text-sm bg-white/20 hover:bg-white/30 rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
