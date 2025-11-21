"use client";

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { DashboardLayout } from '@/components/dashboard/DashboardLayout';
import { TenantsTable } from '@/components/tenants/TenantsTable';
import { Button, EmptyState, ConfirmDialog } from '@/components/ui';
import { useTenants, useDeleteTenant } from '@/lib/hooks/useTenants';
import { Tenant } from '@/lib/api/tenants';
import { Plus, Building2 } from 'lucide-react';

/**
 * Tenants List Page
 *
 * Displays all tenants with CRUD operations
 * Reference: tech-spec Epic 3, Story 4
 */

export default function TenantsPage() {
  const router = useRouter();
  const { data: tenants = [], isLoading } = useTenants();
  const deleteTenantMutation = useDeleteTenant();

  const [tenantToDelete, setTenantToDelete] = useState<Tenant | null>(null);

  const handleEdit = (tenant: Tenant) => {
    router.push(`/dashboard/tenants/${tenant.id}`);
  };

  const handleDelete = (tenant: Tenant) => {
    setTenantToDelete(tenant);
  };

  const confirmDelete = async () => {
    if (!tenantToDelete) return;

    deleteTenantMutation.mutate(tenantToDelete.id, {
      onSuccess: () => {
        setTenantToDelete(null);
      },
    });
  };

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-h1 font-bold text-text-primary">Tenants</h1>
            <p className="text-sm text-text-secondary mt-1">
              Manage tenant organizations and their configurations
            </p>
          </div>
          <Button
            variant="primary"
            onClick={() => router.push('/dashboard/tenants/new')}
          >
            <Plus className="w-4 h-4 mr-2" />
            New Tenant
          </Button>
        </div>

        {/* Content */}
        {!isLoading && tenants.length === 0 ? (
          <EmptyState
            icon={<Building2 className="w-12 h-12" />}
            title="No tenants found"
            description="Get started by creating your first tenant organization"
            action={
              <Button onClick={() => router.push('/dashboard/tenants/new')}>
                <Plus className="w-4 h-4 mr-2" />
                Create Tenant
              </Button>
            }
          />
        ) : (
          <TenantsTable
            tenants={tenants}
            onEdit={handleEdit}
            onDelete={handleDelete}
            isLoading={isLoading}
          />
        )}

        {/* Delete Confirmation Dialog */}
        <ConfirmDialog
          isOpen={!!tenantToDelete}
          onClose={() => setTenantToDelete(null)}
          onConfirm={confirmDelete}
          title="Delete Tenant"
          description={`Are you sure you want to delete "${tenantToDelete?.name}"? This action cannot be undone and will affect ${tenantToDelete?.agent_count || 0} associated agents.`}
          confirmLabel="Delete"
          confirmVariant="danger"
          isLoading={deleteTenantMutation.isPending}
        />
      </div>
    </DashboardLayout>
  );
}
