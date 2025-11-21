/**
 * New LLM Provider Page
 *
 * Create a new LLM provider with form validation and test connection
 */

'use client';

import React from 'react';
import { useRouter } from 'next/navigation';
import { DashboardLayout } from '@/components/dashboard/DashboardLayout';
import { ProviderForm } from '@/components/llm-providers/ProviderForm';
import { Button } from '@/components/ui/Button';
import { useCreateLLMProvider } from '@/lib/hooks/useLLMProviders';
import { ArrowLeft } from 'lucide-react';
import { toast } from 'sonner';
import type { LLMProviderFormData } from '@/lib/validations/llm-providers';

export default function NewProviderPage() {
  const router = useRouter();
  const createProviderMutation = useCreateLLMProvider();

  const handleSubmit = async (data: LLMProviderFormData) => {
    try {
      await createProviderMutation.mutateAsync(data);
      toast.success('Provider created successfully');
      router.push('/dashboard/llm-providers');
    } catch (error) {
      toast.error(`Failed to create provider: ${error instanceof Error ? error.message : 'Unknown error'}`);
      throw error;
    }
  };

  return (
    <DashboardLayout>
      <div className="max-w-2xl mx-auto space-y-6">
        {/* Header */}
        <Button variant="ghost" onClick={() => router.back()} size="sm">
          <ArrowLeft className="w-4 h-4 mr-2" />
          Back
        </Button>

        <div className="glass-card p-8">
          <h1 className="text-2xl font-bold text-text-primary mb-6">
            Add LLM Provider
          </h1>
          <ProviderForm
            onSubmit={handleSubmit}
            onCancel={() => router.back()}
            isLoading={createProviderMutation.isPending}
            mode="create"
          />
        </div>
      </div>
    </DashboardLayout>
  );
}
