/**
 * Agents API Functions
 *
 * API client functions for agent CRUD operations
 * including LLM configuration and tool assignment
 */

import { apiClient } from './client';
import type {
  AgentCreateData,
  AgentUpdateData,
  AgentTestInput,
  LLMConfig
} from '../validations';

/**
 * Agent API Response Type
 */
export interface Agent {
  id: string;
  name: string;
  type: 'conversational' | 'tool_based' | 'langgraph' | 'custom';
  description?: string;
  system_prompt: string;
  llm_config: LLMConfig;
  tool_ids: string[];
  is_active: boolean;
  cognitive_architecture: 'react' | 'single_step' | 'plan_and_solve';
  tools_count?: number;
  last_run?: string;
  created_at: string;
  updated_at: string;
}

/**
 * Agent Test Response Type
 */
export interface AgentTestResponse {
  message: string;
  output: unknown;
  execution_time_ms: number;
  metadata: Record<string, unknown>;
}

/**
 * Paginated Agents Response Type
 */
interface AgentsResponse {
  items: Agent[];
  total: number;
  skip: number;
  limit: number;
}

/**
 * List all agents
 */
export const getAgents = async (): Promise<Agent[]> => {
  const response = await apiClient.get<AgentsResponse>('/api/v1/agents');
  return response.data.items;
};

/**
 * Get single agent by ID
 */
export const getAgent = async (id: string): Promise<Agent> => {
  const response = await apiClient.get<Agent>(`/api/v1/agents/${id}`);
  return response.data;
};

/**
 * Create new agent
 */
export const createAgent = async (data: AgentCreateData): Promise<Agent> => {
  const response = await apiClient.post<Agent>('/api/v1/agents', data);
  return response.data;
};

/**
 * Update existing agent
 */
export const updateAgent = async (
  id: string,
  data: AgentUpdateData
): Promise<Agent> => {
  const response = await apiClient.put<Agent>(`/api/v1/agents/${id}`, data);
  return response.data;
};

/**
 * Delete agent
 */
export const deleteAgent = async (id: string): Promise<void> => {
  await apiClient.delete(`/api/v1/agents/${id}`);
};

/**
 * Test agent execution
 */
export const testAgent = async (
  id: string,
  data: AgentTestInput
): Promise<AgentTestResponse> => {
  const response = await apiClient.post<AgentTestResponse>(
    `/api/v1/agents/${id}/test`,
    data
  );
  return response.data;
};

/**
 * Assign tools to agent
 */
export const assignTools = async (
  id: string,
  toolIds: string[]
): Promise<Agent> => {
  const response = await apiClient.put<Agent>(`/api/v1/agents/${id}/tools`, {
    tool_ids: toolIds,
  });
  return response.data;
};
