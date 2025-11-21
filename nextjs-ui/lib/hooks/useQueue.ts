/**
 * Queue Management React Query Hooks
 *
 * Custom hooks for queue operations with real-time polling
 * using TanStack Query v5 with optimistic updates
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import {
  getQueueStatus,
  getQueueDepthHistory,
  getQueueTasks,
  pauseQueue,
  resumeQueue,
  cancelTask,
  type QueueTask,
} from '../api/queue';

// Re-export QueueTask type for use in components
export type { QueueTask };

/**
 * Query keys for cache management
 */
export const queueKeys = {
  all: ['queue'] as const,
  status: () => [...queueKeys.all, 'status'] as const,
  depthHistory: (minutes: number) => [...queueKeys.all, 'depth-history', minutes] as const,
  tasks: () => [...queueKeys.all, 'tasks'] as const,
  taskList: (page: number, limit: number, status?: QueueTask['status']) =>
    [...queueKeys.tasks(), { page, limit, status }] as const,
};

/**
 * Fetch queue status with 3-second polling
 */
export const useQueueStatus = () => {
  return useQuery({
    queryKey: queueKeys.status(),
    queryFn: getQueueStatus,
    refetchInterval: 3000, // 3 seconds for real-time feel
    staleTime: 2000, // Consider stale after 2 seconds
    refetchOnWindowFocus: true,
  });
};

/**
 * Fetch queue depth history with 10-second polling
 */
export const useQueueDepthHistory = (minutes: number = 60) => {
  return useQuery({
    queryKey: queueKeys.depthHistory(minutes),
    queryFn: () => getQueueDepthHistory(minutes),
    refetchInterval: 10000, // 10 seconds for chart data
    staleTime: 8000,
    refetchOnWindowFocus: true,
  });
};

/**
 * Fetch queue tasks with pagination
 */
export const useQueueTasks = (
  page: number = 1,
  limit: number = 20,
  status?: QueueTask['status']
) => {
  return useQuery({
    queryKey: queueKeys.taskList(page, limit, status),
    queryFn: () => getQueueTasks(page, limit, status),
    refetchInterval: 5000, // 5 seconds for task list
    staleTime: 4000,
  });
};

/**
 * Pause queue with optimistic update
 */
export const usePauseQueue = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: pauseQueue,
    onMutate: async () => {
      // Cancel outgoing refetches
      await queryClient.cancelQueries({ queryKey: queueKeys.status() });

      // Snapshot previous value
      const previousStatus = queryClient.getQueryData(queueKeys.status());

      // Optimistically update to paused
      queryClient.setQueryData(queueKeys.status(), (old: unknown) => {
        if (!old || typeof old !== 'object') return old;
        return { ...old, is_paused: true };
      });

      return { previousStatus };
    },
    onError: (error, _variables, context) => {
      // Rollback on error
      if (context?.previousStatus) {
        queryClient.setQueryData(queueKeys.status(), context.previousStatus);
      }
      toast.error('Failed to pause queue', {
        description: error instanceof Error ? error.message : 'An error occurred',
      });
    },
    onSuccess: () => {
      toast.success('Queue paused successfully');
    },
    onSettled: () => {
      // Refetch to ensure consistency
      queryClient.invalidateQueries({ queryKey: queueKeys.status() });
    },
  });
};

/**
 * Resume queue with optimistic update
 */
export const useResumeQueue = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: resumeQueue,
    onMutate: async () => {
      await queryClient.cancelQueries({ queryKey: queueKeys.status() });

      const previousStatus = queryClient.getQueryData(queueKeys.status());

      // Optimistically update to resumed
      queryClient.setQueryData(queueKeys.status(), (old: unknown) => {
        if (!old || typeof old !== 'object') return old;
        return { ...old, is_paused: false };
      });

      return { previousStatus };
    },
    onError: (error, _variables, context) => {
      if (context?.previousStatus) {
        queryClient.setQueryData(queueKeys.status(), context.previousStatus);
      }
      toast.error('Failed to resume queue', {
        description: error instanceof Error ? error.message : 'An error occurred',
      });
    },
    onSuccess: () => {
      toast.success('Queue resumed successfully');
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: queueKeys.status() });
    },
  });
};

/**
 * Cancel task with optimistic update
 */
export const useCancelTask = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: cancelTask,
    onMutate: async (taskId: string) => {
      // Cancel outgoing refetches for task lists
      await queryClient.cancelQueries({ queryKey: queueKeys.tasks() });

      // Snapshot previous values
      const previousTasks = queryClient.getQueriesData({ queryKey: queueKeys.tasks() });

      // Optimistically remove task from all cached task lists
      queryClient.setQueriesData({ queryKey: queueKeys.tasks() }, (old: unknown) => {
        if (!old || typeof old !== 'object' || !('tasks' in old)) return old;
        const oldData = old as { tasks: QueueTask[]; total: number };
        return {
          ...oldData,
          tasks: oldData.tasks.filter((task: QueueTask) => task.id !== taskId),
          total: oldData.total - 1,
        };
      });

      return { previousTasks };
    },
    onError: (error, _taskId, context) => {
      // Rollback all task list caches
      if (context?.previousTasks) {
        context.previousTasks.forEach(([queryKey, data]) => {
          queryClient.setQueryData(queryKey, data);
        });
      }
      toast.error('Failed to cancel task', {
        description: error instanceof Error ? error.message : 'An error occurred',
      });
    },
    onSuccess: () => {
      toast.success('Task cancelled successfully');
    },
    onSettled: () => {
      // Refetch all task lists to ensure consistency
      queryClient.invalidateQueries({ queryKey: queueKeys.tasks() });
      // Also update queue depth
      queryClient.invalidateQueries({ queryKey: queueKeys.status() });
    },
  });
};
