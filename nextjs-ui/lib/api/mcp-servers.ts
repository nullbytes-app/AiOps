/**
 * MCP Servers API Functions
 *
 * API client functions for MCP server CRUD operations
 * including health check and tool discovery
 */

import { apiClient } from './client';
import type {
  MCPServerCreateData,
  MCPServerUpdateData,
  MCPTestConnectionInput,
  HTTPConnectionConfig,
  StdioConnectionConfig
} from '../validations';

/**
 * MCP Server API Response Type
 */
export interface MCPServer {
  id: string;
  name: string;
  type: 'http' | 'sse' | 'stdio';
  description?: string;
  connection_config: HTTPConnectionConfig | StdioConnectionConfig;
  health_check_enabled: boolean;
  is_active: boolean;
  tools_count?: number;
  health_status?: 'healthy' | 'unhealthy' | 'unknown';
  last_health_check?: string;
  created_at: string;
  updated_at: string;
}

/**
 * Tool Discovery Response Type
 */
export interface ToolDiscoveryResponse {
  success: boolean;
  tools: Array<{
    name: string;
    description?: string;
    input_schema: Record<string, unknown>;
  }>;
  error?: string;
}

/**
 * Health Check Log Entry
 */
export interface HealthCheckLog {
  id: string;
  server_id: string;
  status: 'healthy' | 'unhealthy';
  response_time_ms?: number;
  error?: string;
  checked_at: string;
}

/**
 * List all MCP servers
 */
export const getMCPServers = async (): Promise<MCPServer[]> => {
  const response = await apiClient.get<MCPServer[]>('/api/v1/mcp-servers');
  return response.data;
};

/**
 * Get single MCP server by ID
 */
export const getMCPServer = async (id: string): Promise<MCPServer> => {
  const response = await apiClient.get<MCPServer>(`/api/v1/mcp-servers/${id}`);
  return response.data;
};

/**
 * Create new MCP server
 */
export const createMCPServer = async (
  data: MCPServerCreateData
): Promise<MCPServer> => {
  const response = await apiClient.post<MCPServer>('/api/v1/mcp-servers', data);
  return response.data;
};

/**
 * Update existing MCP server
 */
export const updateMCPServer = async (
  id: string,
  data: MCPServerUpdateData
): Promise<MCPServer> => {
  const response = await apiClient.put<MCPServer>(
    `/api/v1/mcp-servers/${id}`,
    data
  );
  return response.data;
};

/**
 * Delete MCP server
 */
export const deleteMCPServer = async (id: string): Promise<void> => {
  await apiClient.delete(`/api/v1/mcp-servers/${id}`);
};

/**
 * Test connection and discover tools
 */
export const testMCPServerConnection = async (
  data: MCPTestConnectionInput
): Promise<ToolDiscoveryResponse> => {
  const response = await apiClient.post<ToolDiscoveryResponse>(
    `/api/v1/mcp-servers/${data.server_id}/test-connection`
  );
  return response.data;
};

/**
 * Get health check logs for a server
 */
export const getMCPServerHealthLogs = async (
  serverId: string,
  limit: number = 10
): Promise<HealthCheckLog[]> => {
  const response = await apiClient.get<HealthCheckLog[]>(
    `/api/v1/mcp-servers/${serverId}/health-logs`,
    { params: { limit } }
  );
  return response.data;
};
