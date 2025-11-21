"use client";

import { useRouter, useParams } from 'next/navigation';
import Image from 'next/image';
import { DashboardLayout } from '@/components/dashboard/DashboardLayout';
import { TenantForm } from '@/components/tenants/TenantForm';
import { Button, Loading, Badge, ConfirmDialog } from '@/components/ui';
import { useTenant, useUpdateTenant, useDeleteTenant } from '@/lib/hooks/useTenants';
import { TenantUpdateData } from '@/lib/validations/tenants';
import { ArrowLeft, Trash2, Calendar, Users } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import { useState } from 'react';

/**
 * Tenant Detail/Edit Page
 *
 * View and edit tenant details
 * Reference: tech-spec Epic 3, Story 4
 */

export default function TenantDetailPage() {
  const router = useRouter();
  const params = useParams();
  const tenantId = params.id as string;

  const { data: tenant, isLoading } = useTenant(tenantId);
  const updateTenantMutation = useUpdateTenant();
  const deleteTenantMutation = useDeleteTenant();

  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);

  const handleSubmit = (data: TenantUpdateData) => {
    updateTenantMutation.mutate(
      { id: tenantId, data },
      {
        onSuccess: () => {
          // Stay on page after successful update
        },
      }
    );
  };

  const handleDelete = () => {
    deleteTenantMutation.mutate(tenantId, {
      onSuccess: () => {
        router.push('/dashboard/tenants');
      },
    });
  };

  const handleCancel = () => {
    router.push('/dashboard/tenants');
  };

  if (isLoading) {
    return (
      <DashboardLayout>
        <div className="flex items-center justify-center min-h-[400px]">
          <Loading />
        </div>
      </DashboardLayout>
    );
  }

  if (!tenant) {
    return (
      <DashboardLayout>
        <div className="glass-card p-12 text-center">
          <h3 className="text-lg font-semibold text-text-primary mb-2">
            Tenant not found
          </h3>
          <p className="text-text-secondary mb-6">
            The tenant you&apos;re looking for doesn&apos;t exist or has been deleted.
          </p>
          <Button onClick={() => router.push('/dashboard/tenants')}>
            Back to Tenants
          </Button>
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout>
      <div className="max-w-2xl mx-auto space-y-6">
        {/* Back Button */}
        <div className="flex items-center justify-between">
          <Button variant="ghost" onClick={handleCancel} size="sm">
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back to Tenants
          </Button>
          <Button
            variant="danger"
            size="sm"
            onClick={() => setIsDeleteDialogOpen(true)}
          >
            <Trash2 className="w-4 h-4 mr-2" />
            Delete Tenant
          </Button>
        </div>

        {/* Tenant Info */}
        <div className="glass-card p-6">
          <div className="flex items-start justify-between mb-4">
            <div className="flex items-center gap-4">
              {tenant.logo && (
                <div className="relative w-16 h-16 flex-shrink-0">
                  <Image
                    src={tenant.logo}
                    alt={`${tenant.name} logo`}
                    fill
                    className="rounded-lg object-cover"
                    onError={(e) => {
                      e.currentTarget.style.display = 'none';
                    }}
                    unoptimized
                  />
                </div>
              )}
              <div>
                <h2 className="text-h2 font-bold text-text-primary">
                  {tenant.name}
                </h2>
                <p className="text-sm text-text-secondary mt-1">
                  Tenant ID: {tenant.tenant_id}
                </p>
              </div>
            </div>
          </div>

          {/* Metadata */}
          <div className="grid grid-cols-2 gap-4 pt-4 border-t border-white/20">
            <div className="flex items-center gap-2 text-sm">
              <Users className="w-4 h-4 text-text-secondary" />
              <span className="text-text-secondary">Agents:</span>
              <Badge variant="info">{tenant.agent_count || 0}</Badge>
            </div>
            <div className="flex items-center gap-2 text-sm">
              <Calendar className="w-4 h-4 text-text-secondary" />
              <span className="text-text-secondary">Created:</span>
              <span className="text-text-primary">
                {formatDistanceToNow(new Date(tenant.created_at), {
                  addSuffix: true,
                })}
              </span>
            </div>
          </div>
        </div>

        {/* Edit Form */}
        <div className="glass-card p-6">
          <h3 className="text-lg font-semibold text-text-primary mb-4">
            Edit Tenant
          </h3>
          <TenantForm
            onSubmit={handleSubmit}
            onCancel={handleCancel}
            defaultValues={tenant}
            isLoading={updateTenantMutation.isPending}
            mode="edit"
          />
        </div>

        {/* Delete Confirmation Dialog */}
        <ConfirmDialog
          isOpen={isDeleteDialogOpen}
          onClose={() => setIsDeleteDialogOpen(false)}
          onConfirm={handleDelete}
          title="Delete Tenant"
          description={`Are you sure you want to delete "${tenant.name}"? This action cannot be undone and will affect ${tenant.agent_count || 0} associated agents.`}
          confirmLabel="Delete"
          confirmVariant="danger"
          isLoading={deleteTenantMutation.isPending}
        />
      </div>
    </DashboardLayout>
  );
}
