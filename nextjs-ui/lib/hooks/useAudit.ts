/**
 * React Query hooks for audit logs
 *
 * Provides hooks for fetching auth and general audit logs with filters,
 * and for fetching audit diffs.
 */

import { useQuery, UseQueryResult } from '@tanstack/react-query';
import {
  getAuthAuditLogs,
  getGeneralAuditLogs,
  getAuditDiff,
  AuthAuditFilters,
  GeneralAuditFilters,
  AuthAuditResponse,
  GeneralAuditResponse,
  AuditDiff,
} from '../api/audit';

// Re-export filter types for convenience
export type { AuthAuditFilters, GeneralAuditFilters };

/**
 * Hook for fetching auth audit logs with filters
 *
 * @param filters - Auth audit filters (date range, user, event type, success)
 * @returns React Query result with auth audit logs
 *
 * @example
 * ```tsx
 * const { data, isLoading } = useAuthAuditLogs({
 *   page: 1,
 *   limit: 100,
 *   date_from: '2025-01-01',
 *   event_type: 'login',
 * });
 * ```
 */
export function useAuthAuditLogs(
  filters: AuthAuditFilters = {}
): UseQueryResult<AuthAuditResponse, Error> {
  return useQuery({
    queryKey: ['audit', 'auth', filters],
    queryFn: () => getAuthAuditLogs(filters),
    staleTime: 30000, // 30 seconds (recent audit logs)
    gcTime: 60000, // 1 minute cache time
  });
}

/**
 * Hook for fetching general audit logs with filters
 *
 * @param filters - General audit filters (date range, user, action, entity type)
 * @returns React Query result with general audit logs
 *
 * @example
 * ```tsx
 * const { data, isLoading } = useGeneralAuditLogs({
 *   page: 1,
 *   limit: 100,
 *   action: 'update',
 *   entity_type: 'agent',
 * });
 * ```
 */
export function useGeneralAuditLogs(
  filters: GeneralAuditFilters = {}
): UseQueryResult<GeneralAuditResponse, Error> {
  return useQuery({
    queryKey: ['audit', 'general', filters],
    queryFn: () => getGeneralAuditLogs(filters),
    staleTime: 30000, // 30 seconds
    gcTime: 60000, // 1 minute cache time
  });
}

/**
 * Hook for fetching audit diff for specific entry
 *
 * @param id - Audit log entry ID
 * @returns React Query result with audit diff
 *
 * @example
 * ```tsx
 * const { data, isLoading } = useAuditDiff(auditLogId);
 * // data contains old_value, new_value, and computed changes
 * ```
 */
export function useAuditDiff(id: string | null): UseQueryResult<AuditDiff, Error> {
  return useQuery({
    queryKey: ['audit', 'diff', id],
    queryFn: () => getAuditDiff(id!),
    enabled: !!id, // Only fetch when ID is provided
    staleTime: 60000, // 1 minute (diffs don't change)
    gcTime: 300000, // 5 minutes cache time
  });
}
