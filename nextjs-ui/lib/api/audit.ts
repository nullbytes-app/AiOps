/**
 * Audit API Client
 *
 * Provides API methods for fetching auth and general audit logs.
 * Supports filtering by date range, user, event type, action, entity type.
 *
 * Backend endpoints (to be implemented in FastAPI):
 * - GET /api/v1/audit/auth - Auth audit logs
 * - GET /api/v1/audit/general - General CRUD audit logs
 * - GET /api/v1/audit/general/{id}/diff - Diff for specific audit entry
 */

import { apiClient } from './client';

// ============================================================================
// Types & Interfaces
// ============================================================================

/**
 * Auth audit log entry (login, logout, password change, etc.)
 */
export interface AuthAuditLog {
  id: string;
  user_id: string | null;
  user_email: string | null;
  event_type: 'login' | 'logout' | 'password_change' | 'password_reset' | 'failed_login' | 'account_locked';
  success: boolean;
  ip_address: string;
  user_agent: string;
  created_at: string; // ISO 8601
}

/**
 * General audit log entry (CRUD operations)
 */
export interface GeneralAuditLog {
  id: string;
  user_id: string;
  user_email: string;
  tenant_id: string;
  tenant_name: string;
  action: 'create' | 'update' | 'delete';
  entity_type: 'agent' | 'tenant' | 'mcp_server' | 'plugin' | 'prompt' | 'tool';
  entity_id: string;
  old_value: Record<string, unknown> | null;
  new_value: Record<string, unknown> | null;
  created_at: string; // ISO 8601
}

/**
 * Auth audit filters
 */
export interface AuthAuditFilters {
  page?: number;
  limit?: number;
  date_from?: string; // ISO 8601 date
  date_to?: string; // ISO 8601 date
  user_email?: string; // Search by email
  event_type?: string; // Filter by event type
  success?: boolean | null; // Filter by success (null = all)
}

/**
 * General audit filters
 */
export interface GeneralAuditFilters {
  page?: number;
  limit?: number;
  date_from?: string; // ISO 8601 date
  date_to?: string; // ISO 8601 date
  user_email?: string; // Search by email
  tenant_id?: string; // Filter by tenant (super_admin only)
  action?: string; // Filter by action
  entity_type?: string; // Filter by entity type
}

/**
 * Paginated response for auth audit logs
 */
export interface AuthAuditResponse {
  logs: AuthAuditLog[];
  total: number;
  page: number;
  pages: number;
  count_24h: number; // Count for tab badge
}

/**
 * Paginated response for general audit logs
 */
export interface GeneralAuditResponse {
  logs: GeneralAuditLog[];
  total: number;
  page: number;
  pages: number;
  count_24h: number; // Count for tab badge
}

/**
 * Audit diff response
 */
export interface AuditDiff {
  id: string;
  action: 'create' | 'update' | 'delete';
  entity_type: string;
  entity_id: string;
  user_email: string;
  created_at: string;
  old_value: Record<string, unknown> | null;
  new_value: Record<string, unknown> | null;
  changes: Record<string, unknown>; // Computed diff
}

// ============================================================================
// API Methods
// ============================================================================

/**
 * Fetch auth audit logs (login, logout, etc.)
 */
export async function getAuthAuditLogs(filters: AuthAuditFilters = {}): Promise<AuthAuditResponse> {
  const params = new URLSearchParams();

  if (filters.page) params.append('page', filters.page.toString());
  if (filters.limit) params.append('limit', filters.limit.toString());
  if (filters.date_from) params.append('date_from', filters.date_from);
  if (filters.date_to) params.append('date_to', filters.date_to);
  if (filters.user_email) params.append('user_email', filters.user_email);
  if (filters.event_type) params.append('event_type', filters.event_type);
  if (filters.success !== null && filters.success !== undefined) {
    params.append('success', filters.success.toString());
  }

  const response = await apiClient.get<AuthAuditResponse>(
    `/audit/auth?${params.toString()}`
  );
  return response.data;
}

/**
 * Fetch general audit logs (CRUD operations)
 */
export async function getGeneralAuditLogs(
  filters: GeneralAuditFilters = {}
): Promise<GeneralAuditResponse> {
  const params = new URLSearchParams();

  if (filters.page) params.append('page', filters.page.toString());
  if (filters.limit) params.append('limit', filters.limit.toString());
  if (filters.date_from) params.append('date_from', filters.date_from);
  if (filters.date_to) params.append('date_to', filters.date_to);
  if (filters.user_email) params.append('user_email', filters.user_email);
  if (filters.tenant_id) params.append('tenant_id', filters.tenant_id);
  if (filters.action) params.append('action', filters.action);
  if (filters.entity_type) params.append('entity_type', filters.entity_type);

  const response = await apiClient.get<GeneralAuditResponse>(
    `/audit/general?${params.toString()}`
  );
  return response.data;
}

/**
 * Fetch audit diff for specific audit entry
 */
export async function getAuditDiff(id: string): Promise<AuditDiff> {
  const response = await apiClient.get<AuditDiff>(`/audit/general/${id}/diff`);
  return response.data;
}
