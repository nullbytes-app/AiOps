// React Query hooks for plugins with optimistic updates
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useToast } from '@/hooks/use-toast';
import * as pluginsApi from '@/lib/api/plugins';

// Query key factory
const pluginKeys = {
  all: ['plugins'] as const,
  lists: () => [...pluginKeys.all, 'list'] as const,
  list: () => [...pluginKeys.lists()] as const,
  details: () => [...pluginKeys.all, 'detail'] as const,
  detail: (id: string) => [...pluginKeys.details(), id] as const,
  logs: (id: string) => [...pluginKeys.all, 'logs', id] as const,
};

// List all plugins
export function usePlugins() {
  return useQuery({
    queryKey: pluginKeys.list(),
    queryFn: pluginsApi.listPlugins,
    staleTime: 30000, // 30 seconds
  });
}

// Get plugin details with sync logs
export function usePluginDetail(id: string) {
  return useQuery({
    queryKey: pluginKeys.detail(id),
    queryFn: () => pluginsApi.getPluginDetail(id),
    enabled: !!id,
    staleTime: 10000, // 10 seconds
  });
}

// Get sync logs with auto-refresh
export function usePluginSyncLogs(pluginId: string, limit = 50) {
  return useQuery({
    queryKey: pluginKeys.logs(pluginId),
    queryFn: () => pluginsApi.getPluginSyncLogs(pluginId, limit),
    enabled: !!pluginId,
    refetchInterval: 30000, // Auto-refresh every 30 seconds
    staleTime: 25000,
  });
}

// Create plugin mutation
export function useCreatePlugin() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: pluginsApi.createPlugin,
    onSuccess: (newPlugin) => {
      // Invalidate and refetch plugin list
      queryClient.invalidateQueries({ queryKey: pluginKeys.lists() });
      toast({
        title: 'Plugin created',
        description: `${newPlugin.name} has been created successfully.`,
      });
    },
    onError: (error: Error) => {
      toast({
        variant: 'destructive',
        title: 'Failed to create plugin',
        description: error.message,
      });
    },
  });
}

// Update plugin mutation
export function useUpdatePlugin(id: string) {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: (data: pluginsApi.UpdatePluginRequest) => pluginsApi.updatePlugin(id, data),
    onSuccess: (updatedPlugin) => {
      // Update cache for both list and detail
      queryClient.invalidateQueries({ queryKey: pluginKeys.lists() });
      queryClient.invalidateQueries({ queryKey: pluginKeys.detail(id) });
      toast({
        title: 'Plugin updated',
        description: `${updatedPlugin.name} has been updated successfully.`,
      });
    },
    onError: (error: Error) => {
      toast({
        variant: 'destructive',
        title: 'Failed to update plugin',
        description: error.message,
      });
    },
  });
}

// Toggle plugin status with optimistic update
export function useTogglePluginStatus() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: ({ id, status }: { id: string; status: 'active' | 'inactive' }) =>
      pluginsApi.togglePluginStatus(id, status),
    onMutate: async ({ id, status }) => {
      // Cancel outgoing refetches
      await queryClient.cancelQueries({ queryKey: pluginKeys.lists() });

      // Snapshot previous value
      const previousPlugins = queryClient.getQueryData(pluginKeys.list());

      // Optimistically update to new value
      queryClient.setQueryData<pluginsApi.Plugin[]>(pluginKeys.list(), (old) =>
        old ? old.map((plugin) => (plugin.id === id ? { ...plugin, status } : plugin)) : []
      );

      // Return context with snapshot
      return { previousPlugins };
    },
    onError: (error: Error, _variables, context) => {
      // Rollback on error
      if (context?.previousPlugins) {
        queryClient.setQueryData(pluginKeys.list(), context.previousPlugins);
      }
      toast({
        variant: 'destructive',
        title: 'Failed to update plugin status',
        description: error.message,
      });
    },
    onSuccess: (updatedPlugin) => {
      toast({
        title: `Plugin ${updatedPlugin.status === 'active' ? 'activated' : 'deactivated'}`,
        description: `${updatedPlugin.name} is now ${updatedPlugin.status}.`,
      });
    },
    onSettled: () => {
      // Always refetch after error or success
      queryClient.invalidateQueries({ queryKey: pluginKeys.lists() });
    },
  });
}

// Delete plugin mutation
export function useDeletePlugin() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: pluginsApi.deletePlugin,
    onSuccess: (_data, deletedId) => {
      // Remove from cache
      queryClient.invalidateQueries({ queryKey: pluginKeys.lists() });
      queryClient.removeQueries({ queryKey: pluginKeys.detail(deletedId) });
      toast({
        title: 'Plugin deleted',
        description: 'Plugin has been deleted successfully.',
      });
    },
    onError: (error: Error) => {
      toast({
        variant: 'destructive',
        title: 'Failed to delete plugin',
        description: error.message,
      });
    },
  });
}

// Test plugin connection mutation
export function useTestPluginConnection() {
  const { toast } = useToast();

  return useMutation({
    mutationFn: pluginsApi.testPluginConnection,
    onSuccess: (result) => {
      if (result.success) {
        toast({
          title: 'Connection successful',
          description: result.message,
        });
      } else {
        toast({
          variant: 'destructive',
          title: 'Connection failed',
          description: result.message,
        });
      }
    },
    onError: (error: Error) => {
      toast({
        variant: 'destructive',
        title: 'Test failed',
        description: error.message,
      });
    },
  });
}
