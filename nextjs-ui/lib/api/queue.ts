/**
 * Queue Management API Functions
 *
 * API client functions for queue operations including
 * status monitoring, pause/resume controls, and task management
 */

import { apiClient } from './client';

/**
 * Queue Status Response Type
 */
export interface QueueStatus {
  depth: number;
  processing_rate: number; // tasks per minute
  avg_wait_time: number; // seconds
  failed_tasks_24h: number;
  is_paused: boolean;
}

/**
 * Queue Depth History Data Point
 */
export interface QueueDepthDataPoint {
  timestamp: string; // ISO 8601
  depth: number;
}

/**
 * Task in Queue
 */
export interface QueueTask {
  id: string;
  agent_name: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  queued_at: string; // ISO 8601
  priority: number; // 1=High, 2=Normal, 3=Low
  tenant_id: string;
}

/**
 * Paginated Task List Response
 */
export interface TaskListResponse {
  tasks: QueueTask[];
  total: number;
  page: number;
  pages: number;
}

/**
 * Get current queue status
 */
export const getQueueStatus = async (): Promise<QueueStatus> => {
  const response = await apiClient.get<QueueStatus>('/api/v1/queue/status');
  return response.data;
};

/**
 * Get queue depth history (last N minutes)
 */
export const getQueueDepthHistory = async (minutes: number = 60): Promise<QueueDepthDataPoint[]> => {
  const endTime = new Date();
  const startTime = new Date(endTime.getTime() - minutes * 60 * 1000);

  const response = await apiClient.get<QueueDepthDataPoint[]>('/api/v1/queue/metrics', {
    params: {
      start_time: startTime.toISOString(),
      end_time: endTime.toISOString(),
    },
  });
  return response.data;
};

/**
 * Get list of tasks in queue
 */
export const getQueueTasks = async (
  page: number = 1,
  limit: number = 20,
  status?: QueueTask['status']
): Promise<TaskListResponse> => {
  const response = await apiClient.get<TaskListResponse>('/api/v1/queue/tasks', {
    params: {
      page,
      limit,
      ...(status && { status }),
    },
  });
  return response.data;
};

/**
 * Pause queue processing
 */
export const pauseQueue = async (reason?: string): Promise<void> => {
  await apiClient.post('/api/v1/queue/pause', { reason });
};

/**
 * Resume queue processing
 */
export const resumeQueue = async (): Promise<void> => {
  await apiClient.post('/api/v1/queue/resume');
};

/**
 * Cancel a pending or processing task
 */
export const cancelTask = async (taskId: string): Promise<void> => {
  await apiClient.delete(`/api/v1/queue/tasks/${taskId}`);
};
