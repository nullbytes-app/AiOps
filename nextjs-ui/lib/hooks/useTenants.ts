/**
 * Tenants React Query Hooks
 *
 * Custom hooks for tenant CRUD operations using TanStack Query v5
 * with optimistic updates and error handling
 *
 * @see https://tanstack.com/query/latest/docs/react/overview
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import {
  getTenants,
  getTenant,
  createTenant,
  updateTenant,
  deleteTenant,
  type Tenant
} from '../api/tenants';
import type { TenantCreateData, TenantUpdateData } from '../validations';

/**
 * Query keys for cache management
 */
export const tenantKeys = {
  all: ['tenants'] as const,
  lists: () => [...tenantKeys.all, 'list'] as const,
  list: (filters?: Record<string, unknown>) => [...tenantKeys.lists(), filters] as const,
  details: () => [...tenantKeys.all, 'detail'] as const,
  detail: (id: string) => [...tenantKeys.details(), id] as const,
};

/**
 * Fetch all tenants
 */
export const useTenants = () => {
  return useQuery({
    queryKey: tenantKeys.lists(),
    queryFn: getTenants,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
};

/**
 * Fetch single tenant by ID
 */
export const useTenant = (id: string, enabled: boolean = true) => {
  return useQuery({
    queryKey: tenantKeys.detail(id),
    queryFn: () => getTenant(id),
    enabled: enabled && !!id,
    staleTime: 5 * 60 * 1000,
  });
};

/**
 * Create new tenant with optimistic update
 */
export const useCreateTenant = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: createTenant,
    onMutate: async (newTenant: TenantCreateData) => {
      // Cancel outgoing refetches
      await queryClient.cancelQueries({ queryKey: tenantKeys.lists() });

      // Snapshot previous value
      const previousTenants = queryClient.getQueryData<Tenant[]>(tenantKeys.lists());

      // Optimistically update cache
      queryClient.setQueryData<Tenant[]>(tenantKeys.lists(), (old = []) => [
        ...old,
        {
          ...newTenant,
          id: 'temp-' + Date.now(),
          tenant_id: 'temp-tenant-id',
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        } as Tenant,
      ]);

      return { previousTenants };
    },
    onError: (error, _newTenant, context) => {
      // Rollback on error
      if (context?.previousTenants) {
        queryClient.setQueryData(tenantKeys.lists(), context.previousTenants);
      }
      toast.error('Failed to create tenant', {
        description: error instanceof Error ? error.message : 'An error occurred',
      });
    },
    onSuccess: () => {
      // Invalidate and refetch
      queryClient.invalidateQueries({ queryKey: tenantKeys.lists() });
      toast.success('Tenant created successfully');
    },
  });
};

/**
 * Update tenant with optimistic update
 */
export const useUpdateTenant = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: TenantUpdateData }) =>
      updateTenant(id, data),
    onMutate: async ({ id, data }) => {
      await queryClient.cancelQueries({ queryKey: tenantKeys.detail(id) });
      await queryClient.cancelQueries({ queryKey: tenantKeys.lists() });

      const previousTenant = queryClient.getQueryData<Tenant>(tenantKeys.detail(id));
      const previousTenants = queryClient.getQueryData<Tenant[]>(tenantKeys.lists());

      // Optimistically update detail
      if (previousTenant) {
        queryClient.setQueryData<Tenant>(tenantKeys.detail(id), {
          ...previousTenant,
          ...data,
          updated_at: new Date().toISOString(),
        });
      }

      // Optimistically update list
      if (previousTenants) {
        queryClient.setQueryData<Tenant[]>(tenantKeys.lists(), (old = []) =>
          old.map((tenant) =>
            tenant.id === id
              ? { ...tenant, ...data, updated_at: new Date().toISOString() }
              : tenant
          )
        );
      }

      return { previousTenant, previousTenants };
    },
    onError: (error, { id }, context) => {
      if (context?.previousTenant) {
        queryClient.setQueryData(tenantKeys.detail(id), context.previousTenant);
      }
      if (context?.previousTenants) {
        queryClient.setQueryData(tenantKeys.lists(), context.previousTenants);
      }
      toast.error('Failed to update tenant', {
        description: error instanceof Error ? error.message : 'An error occurred',
      });
    },
    onSuccess: (_data, { id }) => {
      queryClient.invalidateQueries({ queryKey: tenantKeys.detail(id) });
      queryClient.invalidateQueries({ queryKey: tenantKeys.lists() });
      toast.success('Tenant updated successfully');
    },
  });
};

/**
 * Delete tenant with optimistic update
 */
export const useDeleteTenant = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: deleteTenant,
    onMutate: async (id: string) => {
      await queryClient.cancelQueries({ queryKey: tenantKeys.lists() });

      const previousTenants = queryClient.getQueryData<Tenant[]>(tenantKeys.lists());

      // Optimistically remove from cache
      queryClient.setQueryData<Tenant[]>(tenantKeys.lists(), (old = []) =>
        old.filter((tenant) => tenant.id !== id)
      );

      return { previousTenants };
    },
    onError: (error, _id, context) => {
      if (context?.previousTenants) {
        queryClient.setQueryData(tenantKeys.lists(), context.previousTenants);
      }
      toast.error('Failed to delete tenant', {
        description: error instanceof Error ? error.message : 'An error occurred',
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: tenantKeys.lists() });
      toast.success('Tenant deleted successfully');
    },
  });
};
