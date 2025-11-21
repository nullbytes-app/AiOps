/**
 * Tenants API Functions
 *
 * API client functions for tenant CRUD operations
 * following REST conventions
 */

import { apiClient } from './client';
import type { TenantCreateData, TenantUpdateData } from '../validations';

/**
 * Tenant API Response Type
 */
export interface Tenant {
  id: string;
  tenant_id: string;
  name: string;
  description?: string;
  logo?: string;
  agent_count?: number;
  created_at: string;
  updated_at: string;
}

/**
 * List all tenants
 */
export const getTenants = async (): Promise<Tenant[]> => {
  const response = await apiClient.get<Tenant[]>('/api/v1/tenants');
  return response.data;
};

/**
 * Get single tenant by ID
 */
export const getTenant = async (id: string): Promise<Tenant> => {
  const response = await apiClient.get<Tenant>(`/api/v1/tenants/${id}`);
  return response.data;
};

/**
 * Create new tenant
 */
export const createTenant = async (data: TenantCreateData): Promise<Tenant> => {
  const response = await apiClient.post<Tenant>('/api/v1/tenants', data);
  return response.data;
};

/**
 * Update existing tenant
 */
export const updateTenant = async (
  id: string,
  data: TenantUpdateData
): Promise<Tenant> => {
  const response = await apiClient.put<Tenant>(`/api/v1/tenants/${id}`, data);
  return response.data;
};

/**
 * Delete tenant
 */
export const deleteTenant = async (id: string): Promise<void> => {
  await apiClient.delete(`/api/v1/tenants/${id}`);
};
