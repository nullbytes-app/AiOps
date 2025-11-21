"use client";

import { useRouter } from 'next/navigation';
import { DashboardLayout } from '@/components/dashboard/DashboardLayout';
import { AgentForm } from '@/components/agents/AgentForm';
import { useCreateAgent } from '@/lib/hooks/useAgents';
import { AgentFormData } from '@/lib/validations/agents';
import { ArrowLeft } from 'lucide-react';
import { Button } from '@/components/ui';

/**
 * Create Agent Page
 *
 * Form for creating a new agent
 * Reference: tech-spec Epic 3, Story 5
 */

export default function NewAgentPage() {
  const router = useRouter();
  const createAgentMutation = useCreateAgent();

  const handleSubmit = (data: AgentFormData) => {
    createAgentMutation.mutate(data, {
      onSuccess: (newAgent) => {
        router.push(`/dashboard/agents-config/${newAgent.id}`);
      },
    });
  };

  const handleCancel = () => {
    router.push('/dashboard/agents-config');
  };

  return (
    <DashboardLayout>
      <div className="max-w-3xl mx-auto space-y-6">
        {/* Back Button */}
        <Button
          variant="ghost"
          onClick={handleCancel}
          size="sm"
        >
          <ArrowLeft className="w-4 h-4 mr-2" />
          Back to Agents
        </Button>

        {/* Header */}
        <div className="glass-card p-6">
          <h2 className="text-h2 font-bold text-text-primary">Create New Agent</h2>
          <p className="text-sm text-text-secondary mt-1">
            Configure a new AI agent with custom LLM settings and behavior
          </p>
        </div>

        {/* Form */}
        <div className="glass-card p-6">
          <AgentForm
            onSubmit={handleSubmit}
            onCancel={handleCancel}
            isLoading={createAgentMutation.isPending}
            mode="create"
          />
        </div>
      </div>
    </DashboardLayout>
  );
}
