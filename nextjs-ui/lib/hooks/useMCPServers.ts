/**
 * MCP Servers React Query Hooks
 *
 * Custom hooks for MCP server CRUD operations, connection testing, and health logs
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import {
  getMCPServers,
  getMCPServer,
  createMCPServer,
  updateMCPServer,
  deleteMCPServer,
  testMCPServerConnection,
  getMCPServerHealthLogs,
} from '../api/mcp-servers';
import type { MCPServerUpdateData, MCPServerCreateData, MCPTestConnectionInput } from '../validations';

export const mcpServerKeys = {
  all: ['mcp-servers'] as const,
  lists: () => [...mcpServerKeys.all, 'list'] as const,
  details: () => [...mcpServerKeys.all, 'detail'] as const,
  detail: (id: string) => [...mcpServerKeys.details(), id] as const,
  healthLogs: (id: string) => [...mcpServerKeys.detail(id), 'health-logs'] as const,
};

export const useMCPServers = () => {
  return useQuery({
    queryKey: mcpServerKeys.lists(),
    queryFn: getMCPServers,
    staleTime: 5 * 60 * 1000,
  });
};

export const useMCPServer = (id: string, enabled: boolean = true) => {
  return useQuery({
    queryKey: mcpServerKeys.detail(id),
    queryFn: () => getMCPServer(id),
    enabled: enabled && !!id,
    staleTime: 5 * 60 * 1000,
  });
};

export const useMCPServerHealthLogs = (id: string, limit: number = 10) => {
  return useQuery({
    queryKey: [...mcpServerKeys.healthLogs(id), limit],
    queryFn: () => getMCPServerHealthLogs(id, limit),
    enabled: !!id,
    staleTime: 1 * 60 * 1000, // 1 minute (fresher data for health logs)
  });
};

export const useCreateMCPServer = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: MCPServerCreateData) => createMCPServer(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: mcpServerKeys.lists() });
      toast.success('MCP server created successfully');
    },
    onError: (error) => {
      toast.error('Failed to create MCP server', {
        description: error instanceof Error ? error.message : 'An error occurred',
      });
    },
  });
};

export const useUpdateMCPServer = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: MCPServerUpdateData }) =>
      updateMCPServer(id, data),
    onSuccess: (_data, { id }) => {
      queryClient.invalidateQueries({ queryKey: mcpServerKeys.detail(id) });
      queryClient.invalidateQueries({ queryKey: mcpServerKeys.lists() });
      toast.success('MCP server updated successfully');
    },
    onError: (error) => {
      toast.error('Failed to update MCP server', {
        description: error instanceof Error ? error.message : 'An error occurred',
      });
    },
  });
};

export const useDeleteMCPServer = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: deleteMCPServer,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: mcpServerKeys.lists() });
      toast.success('MCP server deleted successfully');
    },
    onError: (error) => {
      toast.error('Failed to delete MCP server', {
        description: error instanceof Error ? error.message : 'An error occurred',
      });
    },
  });
};

export const useTestMCPServerConnection = () => {
  return useMutation({
    mutationFn: (data: MCPTestConnectionInput) => testMCPServerConnection(data),
    onSuccess: () => {
      toast.success('Connection test completed');
    },
    onError: (error) => {
      toast.error('Connection test failed', {
        description: error instanceof Error ? error.message : 'An error occurred',
      });
    },
  });
};
