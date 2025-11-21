/**
 * Agents React Query Hooks
 *
 * Custom hooks for agent CRUD operations, tool assignment, and testing
 * using TanStack Query v5 with optimistic updates
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import {
  getAgents,
  getAgent,
  createAgent,
  updateAgent,
  deleteAgent,
  testAgent,
  assignTools,
} from '../api/agents';
import type { AgentUpdateData, AgentTestInput } from '../validations';

/**
 * Query keys for cache management
 */
export const agentKeys = {
  all: ['agents'] as const,
  lists: () => [...agentKeys.all, 'list'] as const,
  list: (filters?: Record<string, unknown>) => [...agentKeys.lists(), filters] as const,
  details: () => [...agentKeys.all, 'detail'] as const,
  detail: (id: string) => [...agentKeys.details(), id] as const,
};

/**
 * Fetch all agents
 */
export const useAgents = () => {
  return useQuery({
    queryKey: agentKeys.lists(),
    queryFn: getAgents,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
};

/**
 * Fetch single agent by ID
 */
export const useAgent = (id: string, enabled: boolean = true) => {
  return useQuery({
    queryKey: agentKeys.detail(id),
    queryFn: () => getAgent(id),
    enabled: enabled && !!id,
    staleTime: 5 * 60 * 1000,
  });
};

/**
 * Create new agent
 */
export const useCreateAgent = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: createAgent,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: agentKeys.lists() });
      toast.success('Agent created successfully');
    },
    onError: (error) => {
      toast.error('Failed to create agent', {
        description: error instanceof Error ? error.message : 'An error occurred',
      });
    },
  });
};

/**
 * Update agent
 */
export const useUpdateAgent = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: AgentUpdateData }) =>
      updateAgent(id, data),
    onSuccess: (_data, { id }) => {
      queryClient.invalidateQueries({ queryKey: agentKeys.detail(id) });
      queryClient.invalidateQueries({ queryKey: agentKeys.lists() });
      toast.success('Agent updated successfully');
    },
    onError: (error) => {
      toast.error('Failed to update agent', {
        description: error instanceof Error ? error.message : 'An error occurred',
      });
    },
  });
};

/**
 * Delete agent
 */
export const useDeleteAgent = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: deleteAgent,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: agentKeys.lists() });
      toast.success('Agent deleted successfully');
    },
    onError: (error) => {
      toast.error('Failed to delete agent', {
        description: error instanceof Error ? error.message : 'An error occurred',
      });
    },
  });
};

/**
 * Test agent execution
 */
export const useTestAgent = () => {
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: AgentTestInput }) =>
      testAgent(id, data),
    onError: (error) => {
      toast.error('Agent test failed', {
        description: error instanceof Error ? error.message : 'An error occurred',
      });
    },
  });
};

/**
 * Assign tools to agent
 */
export const useAssignTools = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, toolIds }: { id: string; toolIds: string[] }) =>
      assignTools(id, toolIds),
    onSuccess: (_data, { id }) => {
      queryClient.invalidateQueries({ queryKey: agentKeys.detail(id) });
      toast.success('Tools assigned successfully');
    },
    onError: (error) => {
      toast.error('Failed to assign tools', {
        description: error instanceof Error ? error.message : 'An error occurred',
      });
    },
  });
};
