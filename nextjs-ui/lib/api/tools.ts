/**
 * API client for OpenAPI Tool Management
 * Handles tool import from OpenAPI specs
 */

import { apiClient } from './client';

export interface OpenAPIOperation {
  method: string; // 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'
  path: string;
  operationId: string;
  summary: string;
  description?: string;
  parameters: OpenAPIParameter[];
  requestBody?: Record<string, unknown>;
  responses?: Record<string, unknown>;
}

export interface OpenAPIParameter {
  name: string;
  in: 'query' | 'path' | 'header' | 'cookie';
  required: boolean;
  schema: Record<string, unknown>;
  description?: string;
}

export interface ParsedSpec {
  spec: Record<string, unknown>; // Full OpenAPI spec
  operations: OpenAPIOperation[];
}

export interface Tool {
  id: string;
  tenant_id: string;
  name: string;
  description: string | null;
  spec_json: Record<string, unknown>;
  base_url: string;
  auth_config: AuthConfig | null;
  created_at: string;
}

export interface AuthConfig {
  type: 'none' | 'api_key' | 'bearer' | 'basic';
  api_key_name?: string; // For API Key auth (header or query param name)
  api_key_location?: 'header' | 'query'; // Where to send API key
  api_key_value?: string; // The actual API key (encrypted server-side)
  bearer_token?: string; // Bearer token value
  basic_username?: string; // Basic auth username
  basic_password?: string; // Basic auth password
}

export interface ParseSpecRequest {
  spec_content: string; // Raw YAML or JSON content
  file_type: 'json' | 'yaml';
}

export interface ImportToolsRequest {
  spec: Record<string, unknown>;
  selected_operations: string[]; // Array of operationIds to import
  name_prefix?: string; // e.g., "jira_" → "jira_createIssue"
  base_url: string;
  auth_config: AuthConfig;
}

/**
 * Parse and validate OpenAPI spec
 */
export async function parseSpec(data: ParseSpecRequest): Promise<ParsedSpec> {
  const response = await apiClient.post<ParsedSpec>(
    '/api/v1/tools/parse',
    data
  );
  return response.data;
}

/**
 * Import tools from parsed spec
 */
export async function importTools(
  data: ImportToolsRequest
): Promise<{ imported_count: number; tool_ids: string[] }> {
  const response = await apiClient.post<{
    imported_count: number;
    tool_ids: string[];
  }>('/api/v1/tools', data);
  return response.data;
}

/**
 * List all imported tools
 */
export async function listTools(): Promise<Tool[]> {
  const response = await apiClient.get<Tool[]>('/api/v1/tools');
  return response.data;
}

/**
 * Get single tool by ID
 */
export async function getTool(id: string): Promise<Tool> {
  const response = await apiClient.get<Tool>(`/api/v1/tools/${id}`);
  return response.data;
}

/**
 * Delete imported tool
 */
export async function deleteTool(id: string): Promise<void> {
  await apiClient.delete(`/api/v1/tools/${id}`);
}
