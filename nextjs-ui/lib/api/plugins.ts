// API client for plugins endpoints
import { apiClient } from './client';

export interface Plugin {
  id: string;
  name: string;
  type: 'webhook' | 'polling';
  status: 'active' | 'inactive';
  last_sync: string;
  sync_frequency: string;
  config: {
    webhook?: {
      endpoint_url: string;
      hmac_secret: string;
    };
    polling?: {
      interval: string;
      api_endpoint: string;
      auth_type: 'none' | 'api_key' | 'bearer' | 'basic';
      auth_config: Record<string, string>;
    };
  };
  created_at: string;
  updated_at: string;
}

export interface SyncLog {
  id: string;
  plugin_id: string;
  timestamp: string;
  status: 'success' | 'failed';
  records_synced: number;
  duration_ms: number;
  error_message?: string;
}

export interface PluginDetail extends Plugin {
  sync_logs: SyncLog[];
}

export interface TestConnectionResult {
  success: boolean;
  message: string;
  details: {
    status_code?: number;
    response_time_ms?: number;
    records_preview?: unknown[];
  };
}

export interface CreatePluginRequest {
  name: string;
  type: 'webhook' | 'polling';
  description?: string;
  config: {
    webhook?: {
      hmac_secret: string;
    };
    polling?: {
      interval: string;
      api_endpoint: string;
      auth_type: 'none' | 'api_key' | 'bearer' | 'basic';
      auth_config: Record<string, string>;
    };
  };
}

export interface UpdatePluginRequest extends CreatePluginRequest {
  status?: 'active' | 'inactive';
}

// List all plugins for current tenant
export async function listPlugins(): Promise<Plugin[]> {
  const response = await apiClient.get<{ plugins: Plugin[] }>('/api/v1/plugins');
  return response.data.plugins;
}

// Get plugin details with sync logs
export async function getPluginDetail(id: string): Promise<PluginDetail> {
  const response = await apiClient.get<{ plugin: PluginDetail }>(`/api/v1/plugins/${id}`);
  return response.data.plugin;
}

// Create new plugin
export async function createPlugin(data: CreatePluginRequest): Promise<Plugin> {
  const response = await apiClient.post<{ plugin: Plugin }>('/api/v1/plugins', data);
  return response.data.plugin;
}

// Update plugin configuration
export async function updatePlugin(id: string, data: UpdatePluginRequest): Promise<Plugin> {
  const response = await apiClient.put<{ plugin: Plugin }>(`/api/v1/plugins/${id}`, data);
  return response.data.plugin;
}

// Toggle plugin status (active/inactive)
export async function togglePluginStatus(id: string, status: 'active' | 'inactive'): Promise<Plugin> {
  const response = await apiClient.patch<{ plugin: Plugin }>(`/api/v1/plugins/${id}/status`, { status });
  return response.data.plugin;
}

// Delete plugin
export async function deletePlugin(id: string): Promise<void> {
  await apiClient.delete(`/api/v1/plugins/${id}`);
}

// Test plugin connection
export async function testPluginConnection(id: string): Promise<TestConnectionResult> {
  const response = await apiClient.post<TestConnectionResult>(`/api/v1/plugins/${id}/test`);
  return response.data;
}

// Get sync logs for plugin (separate endpoint with pagination)
export async function getPluginSyncLogs(pluginId: string, limit = 50): Promise<SyncLog[]> {
  const response = await apiClient.get<{ logs: SyncLog[] }>(`/api/v1/plugins/${pluginId}/logs`, {
    params: { limit }
  });
  return response.data.logs;
}
