/**
 * LLM Provider Detail Page
 *
 * View and edit provider with 2 tabs:
 * 1. Configuration - Provider settings and test connection
 * 2. Models - Available models list
 */

'use client';

import React, { useState } from 'react';
import { useRouter, useParams, useSearchParams } from 'next/navigation';
import { DashboardLayout } from '@/components/dashboard/DashboardLayout';
import { ProviderForm } from '@/components/llm-providers/ProviderForm';
import { ModelList } from '@/components/llm-providers/ModelList';
import { Button, Loading, Badge, ConfirmDialog, Tabs } from '@/components/ui';
import {
  useLLMProvider,
  useUpdateLLMProvider,
  useDeleteLLMProvider,
  useLLMProviderModels,
} from '@/lib/hooks/useLLMProviders';
import { ArrowLeft, Trash2, Settings, Zap } from 'lucide-react';
import { toast } from 'sonner';
import type { LLMProviderFormData } from '@/lib/validations/llm-providers';

export default function ProviderDetailPage() {
  const router = useRouter();
  const params = useParams();
  const searchParams = useSearchParams();
  const providerId = params.id as string;
  const defaultTab = searchParams.get('tab') || 'configuration';

  const { data: provider, isLoading } = useLLMProvider(providerId);
  const { data: models } = useLLMProviderModels(providerId);
  const updateProviderMutation = useUpdateLLMProvider();
  const deleteProviderMutation = useDeleteLLMProvider();

  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);

  const handleSubmit = async (data: LLMProviderFormData) => {
    try {
      await updateProviderMutation.mutateAsync({ id: providerId, data });
      toast.success('Provider updated successfully');
    } catch (error) {
      toast.error(`Failed to update provider: ${error instanceof Error ? error.message : 'Unknown error'}`);
      throw error;
    }
  };

  const handleDelete = () => {
    deleteProviderMutation.mutate(providerId, {
      onSuccess: () => {
        toast.success('Provider deleted successfully');
        router.push('/dashboard/llm-providers');
      },
      onError: (error) => {
        toast.error(`Failed to delete provider: ${error.message}`);
      },
    });
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

  if (!provider) {
    return (
      <DashboardLayout>
        <div className="glass-card p-12 text-center">
          <h3 className="text-lg font-semibold text-text-primary mb-2">
            Provider not found
          </h3>
          <p className="text-text-secondary mb-6">
            The provider you&apos;re looking for doesn&apos;t exist or has been deleted.
          </p>
          <Button onClick={() => router.push('/dashboard/llm-providers')}>
            Back to Providers
          </Button>
        </div>
      </DashboardLayout>
    );
  }

  const statusColors = {
    healthy: 'success',
    unhealthy: 'error',
    unknown: 'default',
  } as const;

  return (
    <DashboardLayout>
      <div className="max-w-4xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <Button variant="ghost" onClick={() => router.back()} size="sm">
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back to Providers
          </Button>
          <Button
            variant="danger"
            size="sm"
            onClick={() => setIsDeleteDialogOpen(true)}
          >
            <Trash2 className="w-4 h-4 mr-2" />
            Delete Provider
          </Button>
        </div>

        {/* Provider Info */}
        <div className="glass-card p-6">
          <div className="flex items-start justify-between">
            <div>
              <h2 className="text-h2 font-bold text-text-primary">
                {provider.name}
              </h2>
              <p className="text-sm text-text-secondary mt-1 capitalize">
                {provider.type.replace('_', ' ')}
              </p>
            </div>
            <Badge variant={statusColors[provider.status as keyof typeof statusColors] || 'default'}>
              {provider.status}
            </Badge>
          </div>
        </div>

        {/* Tabbed Content */}
        <Tabs
          defaultIndex={defaultTab === 'models' ? 1 : 0}
          variant="underline"
          className="w-full"
          tabs={[
            {
              key: 'configuration',
              label: 'Configuration',
              icon: <Settings className="w-4 h-4" />,
              content: (
                <div className="glass-card p-6">
                  <h3 className="text-lg font-semibold text-text-primary mb-4">
                    Edit Provider
                  </h3>
                  <ProviderForm
                    onSubmit={handleSubmit}
                    onCancel={() => router.back()}
                    defaultValues={provider}
                    isLoading={updateProviderMutation.isPending}
                    mode="edit"
                  />
                </div>
              ),
            },
            {
              key: 'models',
              label: `Models (${models?.length || 0})`,
              icon: <Zap className="w-4 h-4" />,
              content: (
                <div className="glass-card p-6">
                  <ModelList
                    models={models || []}
                    isLoading={false}
                    onRefresh={() => toast.info('Model refresh coming soon')}
                  />
                </div>
              ),
            },
          ]}
        />

        {/* Delete Confirmation Dialog */}
        <ConfirmDialog
          isOpen={isDeleteDialogOpen}
          onClose={() => setIsDeleteDialogOpen(false)}
          onConfirm={handleDelete}
          title="Delete Provider"
          description={`Are you sure you want to delete "${provider.name}"? Agents using this provider will fail until reassigned to another provider.`}
          confirmLabel="Delete"
          confirmVariant="danger"
          isLoading={deleteProviderMutation.isPending}
        />
      </div>
    </DashboardLayout>
  );
}
