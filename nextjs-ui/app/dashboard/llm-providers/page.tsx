/**
 * LLM Providers List Page
 *
 * Displays all LLM providers in a card grid layout with:
 * - Provider cards (3 columns desktop, 1 mobile)
 * - Status filter (All, Healthy, Unhealthy)
 * - Add Provider button
 * - Test connection and delete actions
 */

'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { DashboardLayout } from '@/components/dashboard/DashboardLayout';
import { ProviderGrid } from '@/components/llm-providers/ProviderGrid';
import { Button, ConfirmDialog, Loading } from '@/components/ui';
import { useLLMProviders, useDeleteLLMProvider } from '@/lib/hooks/useLLMProviders';
import { Plus } from 'lucide-react';
import { toast } from 'sonner';

export default function LLMProvidersPage() {
  const router = useRouter();
  const { data: providers, isLoading } = useLLMProviders();
  const deleteProviderMutation = useDeleteLLMProvider();

  const [statusFilter, setStatusFilter] = useState<'all' | 'healthy' | 'unhealthy'>('all');
  const [deleteDialogState, setDeleteDialogState] = useState<{
    isOpen: boolean;
    providerId: string | null;
    providerName: string;
  }>({
    isOpen: false,
    providerId: null,
    providerName: '',
  });

  const handleTest = (id: string) => {
    // Navigate to detail page with test tab
    router.push(`/dashboard/llm-providers/${id}?tab=test`);
  };

  const handleDelete = (id: string) => {
    const provider = providers?.find((p) => p.id === id);
    if (provider) {
      setDeleteDialogState({
        isOpen: true,
        providerId: id,
        providerName: provider.name,
      });
    }
  };

  const confirmDelete = () => {
    if (deleteDialogState.providerId) {
      deleteProviderMutation.mutate(deleteDialogState.providerId, {
        onSuccess: () => {
          toast.success('Provider deleted successfully');
          setDeleteDialogState({ isOpen: false, providerId: null, providerName: '' });
        },
        onError: (error) => {
          toast.error(`Failed to delete provider: ${error.message}`);
        },
      });
    }
  };

  // Filter providers by status
  const filteredProviders = providers?.filter((provider) => {
    if (statusFilter === 'all') return true;
    return provider.status === statusFilter;
  }) || [];

  if (isLoading) {
    return (
      <DashboardLayout>
        <div className="flex items-center justify-center min-h-[400px]">
          <Loading />
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-h1 font-bold text-text-primary">
              LLM Providers
            </h1>
            <p className="text-sm text-text-secondary mt-1">
              Manage AI model providers and configurations
            </p>
          </div>
          <Button onClick={() => router.push('/dashboard/llm-providers/new')} className="gap-2">
            <Plus className="w-4 h-4" />
            Add Provider
          </Button>
        </div>

        {/* Filters */}
        <div className="glass-card p-4">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-text-primary">Filter by status:</span>
            <div className="flex gap-2">
              {(['all', 'healthy', 'unhealthy'] as const).map((filter) => (
                <button
                  key={filter}
                  onClick={() => setStatusFilter(filter)}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                    statusFilter === filter
                      ? 'bg-accent-primary text-white'
                      : 'bg-glass-surface text-text-secondary hover:bg-glass-surface-hover'
                  }`}
                >
                  {filter.charAt(0).toUpperCase() + filter.slice(1)}
                </button>
              ))}
            </div>
            <span className="text-sm text-text-tertiary ml-auto">
              {filteredProviders.length} provider{filteredProviders.length !== 1 ? 's' : ''}
            </span>
          </div>
        </div>

        {/* Provider Grid */}
        <ProviderGrid
          providers={filteredProviders}
          onTest={handleTest}
          onDelete={handleDelete}
        />

        {/* Delete Confirmation Dialog */}
        <ConfirmDialog
          isOpen={deleteDialogState.isOpen}
          onClose={() => setDeleteDialogState({ isOpen: false, providerId: null, providerName: '' })}
          onConfirm={confirmDelete}
          title={`Delete ${deleteDialogState.providerName}?`}
          description="Agents using this provider will fail until reassigned to another provider. This action cannot be undone."
          confirmLabel="Delete Provider"
          confirmVariant="danger"
          isLoading={deleteProviderMutation.isPending}
        />
      </div>
    </DashboardLayout>
  );
}
