/**
 * Operations / Queue Management Page
 *
 * Real-time queue management dashboard with:
 * - Queue status metrics (4 glassmorphic cards)
 * - Pause/Resume controls (tenant_admin + operator only)
 * - Queue depth chart (last 60 minutes, 10s refresh)
 * - Task list table (pagination, cancel actions)
 *
 * Real-time updates: 3s for status, 10s for chart, 5s for tasks
 * RBAC: All roles can view, only tenant_admin+operator can pause/cancel
 *
 * Reference: Story 5, AC-1
 */

'use client';

import { DashboardLayout } from '@/components/dashboard/DashboardLayout';
import { QueueStatus } from '@/components/operations/QueueStatus';
import { QueuePauseToggle } from '@/components/operations/QueuePauseToggle';
import { QueueDepthChart } from '@/components/operations/QueueDepthChart';
import { TaskList } from '@/components/operations/TaskList';

export default function OperationsPage() {
  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Page Header */}
        <div className="flex items-center justify-between">
          <h2 className="text-h2 font-bold text-text-primary">Queue Management</h2>
          <QueuePauseToggle />
        </div>

        {/* Queue Status Cards */}
        <QueueStatus />

        {/* Queue Depth Chart */}
        <QueueDepthChart />

        {/* Task List */}
        <TaskList />
      </div>
    </DashboardLayout>
  );
}
