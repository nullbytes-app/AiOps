/**
 * LLM Providers API Functions
 *
 * API client functions for LLM provider CRUD operations
 * including test connection functionality
 */

import { apiClient } from './client';
import type {
  LLMProviderCreateData,
  LLMProviderUpdateData,
  TestConnectionInput,
  ModelConfig
} from '../validations';

/**
 * LLM Provider API Response Type
 */
export interface LLMProvider {
  id: string;
  name: string;
  type: 'openai' | 'anthropic' | 'openrouter' | 'custom';
  api_key: string; // Masked in response (last 4 chars only)
  base_url?: string;
  models: ModelConfig[];
  default_model?: string;
  is_active: boolean;
  status?: 'healthy' | 'unhealthy' | 'unknown';
  created_at: string;
  updated_at: string;
}

/**
 * Test Connection Response Type
 */
export interface TestConnectionResponse {
  success: boolean;
  response_time_ms: number;
  models_discovered?: ModelConfig[];
  error?: string;
}

/**
 * List all LLM providers
 */
export const getLLMProviders = async (): Promise<LLMProvider[]> => {
  const response = await apiClient.get<LLMProvider[]>('/api/v1/llm-providers');
  return response.data;
};

/**
 * Get single LLM provider by ID
 */
export const getLLMProvider = async (id: string): Promise<LLMProvider> => {
  const response = await apiClient.get<LLMProvider>(`/api/v1/llm-providers/${id}`);
  return response.data;
};

/**
 * Create new LLM provider
 */
export const createLLMProvider = async (
  data: LLMProviderCreateData
): Promise<LLMProvider> => {
  const response = await apiClient.post<LLMProvider>('/api/v1/llm-providers', data);
  return response.data;
};

/**
 * Update existing LLM provider
 */
export const updateLLMProvider = async (
  id: string,
  data: LLMProviderUpdateData
): Promise<LLMProvider> => {
  const response = await apiClient.put<LLMProvider>(
    `/api/v1/llm-providers/${id}`,
    data
  );
  return response.data;
};

/**
 * Delete LLM provider
 */
export const deleteLLMProvider = async (id: string): Promise<void> => {
  await apiClient.delete(`/api/v1/llm-providers/${id}`);
};

/**
 * Test connection to LLM provider
 */
export const testLLMProviderConnection = async (
  data: TestConnectionInput
): Promise<TestConnectionResponse> => {
  const response = await apiClient.post<TestConnectionResponse>(
    `/api/v1/llm-providers/${data.provider_id}/test-connection`,
    { test_prompt: data.test_prompt }
  );
  return response.data;
};

/**
 * Get models for a specific LLM provider
 */
export const getLLMProviderModels = async (id: string): Promise<ModelConfig[]> => {
  const response = await apiClient.get<{ models: ModelConfig[] }>(
    `/api/v1/llm-providers/${id}/models`
  );
  return response.data.models;
};
