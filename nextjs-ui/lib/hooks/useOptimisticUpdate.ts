import { useMutation, useQueryClient, type UseMutationOptions } from "@tanstack/react-query";
import { toast } from "@/components/ui/Toast";

/**
 * Optimistic Update Configuration
 */
interface OptimisticUpdateOptions<TData, TVariables, TContext> {
  /**
   * Query key to invalidate after mutation
   */
  queryKey: string[];
  /**
   * Success toast message
   */
  successMessage?: string;
  /**
   * Error toast message
   */
  errorMessage?: string;
  /**
   * Show undo button on success (5s window)
   */
  showUndo?: boolean;
  /**
   * Undo callback function
   */
  onUndo?: (variables: TVariables) => void | Promise<void>;
  /**
   * Retry button on error
   */
  showRetry?: boolean;
  /**
   * Custom mutation options
   */
  mutationOptions?: UseMutationOptions<TData, Error, TVariables, TContext>;
  /**
   * Optimistic update function (updates cache immediately)
   */
  optimisticUpdate?: (variables: TVariables) => void;
  /**
   * Rollback function (reverts optimistic update on error)
   */
  rollback?: (context: TContext) => void;
}

/**
 * useOptimisticUpdate Hook
 *
 * TanStack Query mutation hook with optimistic updates, undo, and retry.
 *
 * Features:
 * - Optimistic UI updates (immediate cache update)
 * - Automatic rollback on error
 * - Undo button (5s window)
 * - Retry button on error
 * - Success/error toasts
 * - Query invalidation
 *
 * Optimistic UI Patterns:
 * - **Create:** Add new item to list immediately, show loading badge
 * - **Update:** Update item immediately, revert on error
 * - **Delete:** Fade out item, show undo toast, remove after 5s
 * - **Rollback on error:** Restore previous state, show error toast with retry
 *
 * @example
 * ```tsx
 * // Delete agent with undo
 * const deleteAgent = useOptimisticUpdate({
 *   mutationFn: (id: string) => api.deleteAgent(id),
 *   queryKey: ['agents'],
 *   successMessage: 'Agent deleted',
 *   showUndo: true,
 *   onUndo: async (id) => {
 *     await api.createAgent({ id, ...previousData });
 *   },
 *   optimisticUpdate: (id) => {
 *     queryClient.setQueryData(['agents'], (old) =>
 *       old.filter((agent) => agent.id !== id)
 *     );
 *   },
 *   rollback: (context) => {
 *     queryClient.setQueryData(['agents'], context.previousData);
 *   },
 * });
 *
 * // Update agent with retry
 * const updateAgent = useOptimisticUpdate({
 *   mutationFn: (agent: Agent) => api.updateAgent(agent),
 *   queryKey: ['agents', agent.id],
 *   successMessage: 'Agent updated',
 *   errorMessage: 'Failed to update agent',
 *   showRetry: true,
 *   optimisticUpdate: (agent) => {
 *     queryClient.setQueryData(['agents', agent.id], agent);
 *   },
 * });
 * ```
 *
 * Reference: Story 6 AC-4 (Loading States - Optimistic UI Updates)
 */
export function useOptimisticUpdate<TData = unknown, TVariables = void, TContext = unknown>({
  queryKey,
  successMessage,
  errorMessage,
  showUndo = false,
  onUndo,
  showRetry = true,
  mutationOptions,
  optimisticUpdate,
  rollback,
}: OptimisticUpdateOptions<TData, TVariables, TContext>) {
  const queryClient = useQueryClient();

  const mutation = useMutation<TData, Error, TVariables, TContext>({
    ...mutationOptions,

    // Before mutation (optimistic update)
    onMutate: async (variables) => {
      // Cancel outgoing refetches
      await queryClient.cancelQueries({ queryKey });

      // Snapshot previous value
      const previousData = queryClient.getQueryData(queryKey);

      // Optimistic update
      if (optimisticUpdate) {
        optimisticUpdate(variables);
      }

      // Call custom onMutate if provided
      if (mutationOptions?.onMutate) {
        await mutationOptions.onMutate(variables);
      }

      // Return context with previous data for rollback
      return { previousData, variables } as TContext;
    },

    // On success
    onSuccess: (data, variables, context) => {
      // Invalidate and refetch
      queryClient.invalidateQueries({ queryKey });

      // Show success toast
      if (successMessage) {
        toast.success(successMessage, {
          ...(showUndo && onUndo
            ? {
                action: {
                  label: "Undo",
                  onClick: async () => {
                    try {
                      await onUndo(variables);
                      queryClient.invalidateQueries({ queryKey });
                      toast.success("Action undone");
                    } catch {
                      toast.error("Failed to undo action");
                    }
                  },
                },
              }
            : {}),
        });
      }

      // Call custom onSuccess if provided
      if (mutationOptions?.onSuccess) {
        mutationOptions.onSuccess(data, variables, context);
      }
    },

    // On error (rollback)
    onError: (error, variables, context) => {
      // Rollback optimistic update
      if (context && rollback) {
        rollback(context);
      } else if (context && typeof context === 'object' && context !== null && 'previousData' in context) {
        // Default rollback: restore previous data
        queryClient.setQueryData(queryKey, (context as { previousData: unknown }).previousData);
      }

      // Show error toast with retry button
      const message = errorMessage || error.message || "An error occurred";
      toast.error(message, {
        description: showRetry ? "You can try again." : undefined,
        ...(showRetry
          ? {
              action: {
                label: "Retry",
                onClick: () => {
                  mutation.mutate(variables);
                },
              },
            }
          : {}),
      });

      // Call custom onError if provided
      if (mutationOptions?.onError) {
        mutationOptions.onError(error, variables, context);
      }
    },

    // On settled (cleanup)
    onSettled: (data, error, variables, context) => {
      // Call custom onSettled if provided
      if (mutationOptions?.onSettled) {
        mutationOptions.onSettled(data, error, variables, context);
      }
    },
  });

  return mutation;
}

/**
 * useOptimisticCreate Hook
 *
 * Specialized hook for optimistic create operations.
 * Adds new item to list immediately with loading badge.
 *
 * @example
 * ```tsx
 * const createAgent = useOptimisticCreate({
 *   mutationFn: (agent: Agent) => api.createAgent(agent),
 *   queryKey: ['agents'],
 *   successMessage: 'Agent created',
 * });
 * ```
 */
export function useOptimisticCreate<TData = unknown, TVariables = void>(
  options: Omit<OptimisticUpdateOptions<TData, TVariables, unknown>, "showUndo" | "onUndo">
) {
  return useOptimisticUpdate({
    ...options,
    showUndo: false,
    showRetry: true,
  });
}

/**
 * useOptimisticDelete Hook
 *
 * Specialized hook for optimistic delete operations.
 * Removes item immediately with undo option (5s window).
 *
 * @example
 * ```tsx
 * const deleteAgent = useOptimisticDelete({
 *   mutationFn: (id: string) => api.deleteAgent(id),
 *   queryKey: ['agents'],
 *   successMessage: 'Agent deleted',
 *   onUndo: (id) => api.restoreAgent(id),
 * });
 * ```
 */
export function useOptimisticDelete<TData = unknown, TVariables = void>(
  options: Omit<OptimisticUpdateOptions<TData, TVariables, unknown>, "showUndo">
) {
  return useOptimisticUpdate({
    ...options,
    showUndo: true, // Always show undo for deletes
    showRetry: false, // No retry for deletes
  });
}

/**
 * useOptimisticUpdate Hook
 *
 * Specialized hook for optimistic update operations.
 * Updates item immediately, reverts on error with retry.
 *
 * @example
 * ```tsx
 * const updateAgent = useOptimisticUpdate({
 *   mutationFn: (agent: Agent) => api.updateAgent(agent),
 *   queryKey: ['agents', agent.id],
 *   successMessage: 'Agent updated',
 *   errorMessage: 'Failed to update agent',
 * });
 * ```
 */
export function useOptimisticUpdateItem<TData = unknown, TVariables = void>(
  options: Omit<OptimisticUpdateOptions<TData, TVariables, unknown>, "showUndo">
) {
  return useOptimisticUpdate({
    ...options,
    showUndo: false,
    showRetry: true, // Always show retry for updates
  });
}
