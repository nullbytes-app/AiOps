/**
 * API client for System Prompt Templates
 * Handles CRUD operations for prompt templates with variable substitution
 */

import { apiClient } from './client';

export interface PromptTemplate {
  id: string;
  tenant_id: string;
  name: string;
  description: string | null;
  template_text: string;
  variables: string[]; // Extracted from template_text
  created_at: string;
  updated_at: string;
}

export interface PromptVersion {
  id: string;
  template_id: string;
  version_number: number;
  template_text: string;
  created_by: string;
  created_at: string;
}

export interface CreatePromptRequest {
  name: string;
  description?: string;
  template_text: string;
}

export interface UpdatePromptRequest {
  name?: string;
  description?: string;
  template_text?: string;
}

export interface TestPromptRequest {
  template_text: string;
  variables: Record<string, string>;
}

export interface TestPromptResponse {
  rendered_text: string;
}

/**
 * List all prompt templates for current tenant
 */
export async function listPrompts(): Promise<PromptTemplate[]> {
  const response = await apiClient.get<PromptTemplate[]>('/api/v1/prompts');
  return response.data;
}

/**
 * Get single prompt template by ID
 */
export async function getPrompt(id: string): Promise<PromptTemplate> {
  const response = await apiClient.get<PromptTemplate>(`/api/v1/prompts/${id}`);
  return response.data;
}

/**
 * Create new prompt template
 */
export async function createPrompt(
  data: CreatePromptRequest
): Promise<PromptTemplate> {
  const response = await apiClient.post<PromptTemplate>('/api/v1/prompts', data);
  return response.data;
}

/**
 * Update existing prompt template (creates new version)
 */
export async function updatePrompt(
  id: string,
  data: UpdatePromptRequest
): Promise<PromptTemplate> {
  const response = await apiClient.put<PromptTemplate>(
    `/api/v1/prompts/${id}`,
    data
  );
  return response.data;
}

/**
 * Soft-delete prompt template
 */
export async function deletePrompt(id: string): Promise<void> {
  await apiClient.delete(`/api/v1/prompts/${id}`);
}

/**
 * Test prompt with sample variables for preview
 */
export async function testPrompt(
  data: TestPromptRequest
): Promise<TestPromptResponse> {
  const response = await apiClient.post<TestPromptResponse>(
    '/api/v1/prompts/test',
    data
  );
  return response.data;
}

/**
 * Get version history for a prompt
 */
export async function getPromptVersions(id: string): Promise<PromptVersion[]> {
  const response = await apiClient.get<PromptVersion[]>(
    `/api/v1/prompts/${id}/versions`
  );
  return response.data;
}

/**
 * Revert prompt to a previous version
 */
export async function revertPromptVersion(
  id: string,
  version: number
): Promise<PromptTemplate> {
  const response = await apiClient.post<PromptTemplate>(
    `/api/v1/prompts/${id}/versions/${version}/revert`
  );
  return response.data;
}

/**
 * Extract variables from template text
 * Matches {{variable_name}} pattern
 */
export function extractVariables(template: string): string[] {
  const regex = /\{\{(\w+)\}\}/g;
  const matches = Array.from(template.matchAll(regex));
  return Array.from(new Set(matches.map((m) => m[1]))); // Deduplicate
}
