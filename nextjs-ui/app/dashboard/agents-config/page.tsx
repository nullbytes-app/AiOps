"use client";

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { DashboardLayout } from '@/components/dashboard/DashboardLayout';
import { AgentsTable } from '@/components/agents/AgentsTable';
import { Button, EmptyState, ConfirmDialog } from '@/components/ui';
import { useAgents, useDeleteAgent } from '@/lib/hooks/useAgents';
import { Agent } from '@/lib/api/agents';
import { Plus, Bot } from 'lucide-react';

/**
 * Agents List Page
 *
 * Displays all agents with CRUD operations
 * Reference: tech-spec Epic 3, Story 5
 */

export default function AgentsPage() {
  const router = useRouter();
  const { data: agents = [], isLoading } = useAgents();
  const deleteAgentMutation = useDeleteAgent();

  const [agentToDelete, setAgentToDelete] = useState<Agent | null>(null);

  const handleEdit = (agent: Agent) => {
    router.push(`/dashboard/agents-config/${agent.id}`);
  };

  const handleDelete = (agent: Agent) => {
    setAgentToDelete(agent);
  };

  const handleTest = (agent: Agent) => {
    router.push(`/dashboard/agents-config/${agent.id}?tab=test`);
  };

  const confirmDelete = async () => {
    if (!agentToDelete) return;

    deleteAgentMutation.mutate(agentToDelete.id, {
      onSuccess: () => {
        setAgentToDelete(null);
      },
    });
  };

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-h1 font-bold text-text-primary">Agents</h1>
            <p className="text-sm text-text-secondary mt-1">
              Manage AI agents with custom LLM configurations and tool assignments
            </p>
          </div>
          <Button
            variant="primary"
            onClick={() => router.push('/dashboard/agents-config/new')}
          >
            <Plus className="w-4 h-4 mr-2" />
            New Agent
          </Button>
        </div>

        {/* Content */}
        {!isLoading && agents.length === 0 ? (
          <EmptyState
            icon={<Bot className="w-12 h-12" />}
            title="No agents found"
            description="Get started by creating your first AI agent with custom LLM configuration"
            action={
              <Button onClick={() => router.push('/dashboard/agents-config/new')}>
                <Plus className="w-4 h-4 mr-2" />
                Create Agent
              </Button>
            }
          />
        ) : (
          <AgentsTable
            agents={agents}
            onEdit={handleEdit}
            onDelete={handleDelete}
            onTest={handleTest}
            isLoading={isLoading}
          />
        )}

        {/* Delete Confirmation Dialog */}
        <ConfirmDialog
          isOpen={!!agentToDelete}
          onClose={() => setAgentToDelete(null)}
          onConfirm={confirmDelete}
          title="Delete Agent"
          description={`Are you sure you want to delete "${agentToDelete?.name}"? This action cannot be undone and will affect any workflows using this agent.`}
          confirmLabel="Delete"
          confirmVariant="danger"
          isLoading={deleteAgentMutation.isPending}
        />
      </div>
    </DashboardLayout>
  );
}
