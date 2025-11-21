"use client";

import { useRouter } from 'next/navigation';
import { DashboardLayout } from '@/components/dashboard/DashboardLayout';
import { TenantForm } from '@/components/tenants/TenantForm';
import { useCreateTenant } from '@/lib/hooks/useTenants';
import { TenantCreateData } from '@/lib/validations/tenants';
import { ArrowLeft } from 'lucide-react';
import { Button } from '@/components/ui';

/**
 * Create Tenant Page
 *
 * Form for creating a new tenant
 * Reference: tech-spec Epic 3, Story 4
 */

export default function NewTenantPage() {
  const router = useRouter();
  const createTenantMutation = useCreateTenant();

  const handleSubmit = (data: TenantCreateData) => {
    createTenantMutation.mutate(data, {
      onSuccess: (newTenant) => {
        router.push(`/dashboard/tenants/${newTenant.id}`);
      },
    });
  };

  const handleCancel = () => {
    router.push('/dashboard/tenants');
  };

  return (
    <DashboardLayout>
      <div className="max-w-2xl mx-auto space-y-6">
        {/* Back Button */}
        <Button
          variant="ghost"
          onClick={handleCancel}
          size="sm"
        >
          <ArrowLeft className="w-4 h-4 mr-2" />
          Back to Tenants
        </Button>

        {/* Header */}
        <div className="glass-card p-6">
          <h2 className="text-h2 font-bold text-text-primary">Create New Tenant</h2>
          <p className="text-sm text-text-secondary mt-1">
            Add a new tenant organization to the system
          </p>
        </div>

        {/* Form */}
        <div className="glass-card p-6">
          <TenantForm
            onSubmit={handleSubmit}
            onCancel={handleCancel}
            isLoading={createTenantMutation.isPending}
            mode="create"
          />
        </div>
      </div>
    </DashboardLayout>
  );
}
