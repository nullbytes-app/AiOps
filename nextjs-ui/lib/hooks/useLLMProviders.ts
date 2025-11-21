/**
 * LLM Providers React Query Hooks
 *
 * Custom hooks for LLM provider CRUD operations and connection testing
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import {
  getLLMProviders,
  getLLMProvider,
  createLLMProvider,
  updateLLMProvider,
  deleteLLMProvider,
  testLLMProviderConnection,
  getLLMProviderModels,
} from '../api/llm-providers';
import type { LLMProviderUpdateData } from '../validations';

export const llmProviderKeys = {
  all: ['llm-providers'] as const,
  lists: () => [...llmProviderKeys.all, 'list'] as const,
  details: () => [...llmProviderKeys.all, 'detail'] as const,
  detail: (id: string) => [...llmProviderKeys.details(), id] as const,
  models: (id: string) => [...llmProviderKeys.all, 'models', id] as const,
};

export const useLLMProviders = () => {
  return useQuery({
    queryKey: llmProviderKeys.lists(),
    queryFn: getLLMProviders,
    staleTime: 5 * 60 * 1000,
  });
};

export const useLLMProvider = (id: string, enabled: boolean = true) => {
  return useQuery({
    queryKey: llmProviderKeys.detail(id),
    queryFn: () => getLLMProvider(id),
    enabled: enabled && !!id,
    staleTime: 5 * 60 * 1000,
  });
};

export const useCreateLLMProvider = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: createLLMProvider,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: llmProviderKeys.lists() });
      toast.success('LLM provider created successfully');
    },
    onError: (error) => {
      toast.error('Failed to create LLM provider', {
        description: error instanceof Error ? error.message : 'An error occurred',
      });
    },
  });
};

export const useUpdateLLMProvider = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: LLMProviderUpdateData }) =>
      updateLLMProvider(id, data),
    onSuccess: (_data, { id }) => {
      queryClient.invalidateQueries({ queryKey: llmProviderKeys.detail(id) });
      queryClient.invalidateQueries({ queryKey: llmProviderKeys.lists() });
      toast.success('LLM provider updated successfully');
    },
    onError: (error) => {
      toast.error('Failed to update LLM provider', {
        description: error instanceof Error ? error.message : 'An error occurred',
      });
    },
  });
};

export const useDeleteLLMProvider = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: deleteLLMProvider,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: llmProviderKeys.lists() });
      toast.success('LLM provider deleted successfully');
    },
    onError: (error) => {
      toast.error('Failed to delete LLM provider', {
        description: error instanceof Error ? error.message : 'An error occurred',
      });
    },
  });
};

export const useTestLLMProviderConnection = () => {
  return useMutation({
    mutationFn: testLLMProviderConnection,
    onError: (error) => {
      toast.error('Connection test failed', {
        description: error instanceof Error ? error.message : 'An error occurred',
      });
    },
  });
};

export const useLLMProviderModels = (id: string, enabled: boolean = true) => {
  return useQuery({
    queryKey: llmProviderKeys.models(id),
    queryFn: () => getLLMProviderModels(id),
    enabled: enabled && !!id,
    staleTime: 5 * 60 * 1000,
  });
};
