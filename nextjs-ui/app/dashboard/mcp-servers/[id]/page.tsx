/**
 * MCP Server Detail Page
 *
 * Displays MCP server details with tabs for:
 * - Configuration (edit form)
 * - Tools (discovered tools list)
 * - Health (health check logs)
 */

'use client';

import React, { useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { ArrowLeft, Settings, Wrench, Activity, RefreshCw, AlertCircle } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { McpServerForm } from '@/components/mcp-servers/McpServerForm';
import { ToolsList } from '@/components/mcp-servers/ToolsList';
import { HealthLogs } from '@/components/mcp-servers/HealthLogs';
import { TestConnection } from '@/components/mcp-servers/TestConnection';
import { useMCPServer, useUpdateMCPServer } from '@/lib/hooks/useMCPServers';
import type { MCPServerCreateData } from '@/lib/validations';

type TabId = 'config' | 'tools' | 'health';

interface Tab {
  id: TabId;
  label: string;
  icon: React.ReactNode;
}

const tabs: Tab[] = [
  { id: 'config', label: 'Configuration', icon: <Settings className="h-4 w-4" /> },
  { id: 'tools', label: 'Tools', icon: <Wrench className="h-4 w-4" /> },
  { id: 'health', label: 'Health', icon: <Activity className="h-4 w-4" /> },
];

/**
 * Loading State Component
 */
function LoadingState() {
  return (
    <div className="space-y-6">
      <div className="animate-pulse space-y-4">
        <div className="h-8 bg-white/50 rounded w-1/3" />
        <div className="h-96 bg-white/50 rounded" />
      </div>
    </div>
  );
}

/**
 * Error State Component
 */
function ErrorState({ onRetry }: { onRetry: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center py-24">
      <AlertCircle className="h-16 w-16 text-destructive mb-4" />
      <h2 className="text-2xl font-bold text-foreground mb-2">
        Failed to Load MCP Server
      </h2>
      <p className="text-muted-foreground mb-6 max-w-md text-center">
        We couldn&apos;t fetch the MCP server details. Please check your connection and try again.
      </p>
      <Button onClick={onRetry} className="gap-2">
        <RefreshCw className="h-4 w-4" />
        Retry
      </Button>
    </div>
  );
}

/**
 * MCP Server Detail Page
 */
export default function McpServerDetailPage() {
  const params = useParams();
  const serverId = params.id as string;

  const [activeTab, setActiveTab] = useState<TabId>('config');

  const { data: server, isLoading, isError, refetch } = useMCPServer(serverId);
  const updateMutation = useUpdateMCPServer();

  /**
   * Handle form submission
   */
  const handleSubmit = async (data: MCPServerCreateData) => {
    await updateMutation.mutateAsync({ id: serverId, data });
  };

  // Loading state
  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <Link href="/dashboard/mcp-servers">
            <Button variant="ghost" size="sm" className="gap-2">
              <ArrowLeft className="h-4 w-4" />
              Back
            </Button>
          </Link>
          <h1 className="text-3xl font-bold text-foreground">MCP Server Details</h1>
        </div>
        <LoadingState />
      </div>
    );
  }

  // Error state
  if (isError || !server) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <Link href="/dashboard/mcp-servers">
            <Button variant="ghost" size="sm" className="gap-2">
              <ArrowLeft className="h-4 w-4" />
              Back
            </Button>
          </Link>
          <h1 className="text-3xl font-bold text-foreground">MCP Server Details</h1>
        </div>
        <ErrorState onRetry={refetch} />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Back Button & Header */}
      <div className="flex items-center gap-4">
        <Link href="/dashboard/mcp-servers">
          <Button variant="ghost" size="sm" className="gap-2">
            <ArrowLeft className="h-4 w-4" />
            Back
          </Button>
        </Link>
        <div className="flex-1">
          <h1 className="text-3xl font-bold text-foreground">{server.name}</h1>
          {server.description && (
            <p className="text-muted-foreground mt-2">{server.description}</p>
          )}
        </div>
        <div className="flex items-center gap-2">
          <span
            className={`inline-flex items-center px-3 py-1 rounded-md text-sm font-medium ${
              server.is_active
                ? 'bg-green-100 text-green-700'
                : 'bg-gray-100 text-gray-700'
            }`}
          >
            {server.is_active ? 'Active' : 'Inactive'}
          </span>
          <span className="inline-flex items-center px-3 py-1 rounded-md text-sm font-medium bg-blue-100 text-blue-700">
            {server.type.toUpperCase()}
          </span>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-border">
        <nav className="flex gap-4" role="tablist">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-4 py-3 border-b-2 transition-all ${
                activeTab === tab.id
                  ? 'border-accent-blue text-accent-blue font-semibold'
                  : 'border-transparent text-text-secondary hover:text-text-primary hover:border-border'
              }`}
              role="tab"
              aria-selected={activeTab === tab.id}
              aria-controls={`${tab.id}-panel`}
            >
              {tab.icon}
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Panels */}
      <div className="mt-6">
        {/* Configuration Tab */}
        {activeTab === 'config' && (
          <div role="tabpanel" id="config-panel" aria-labelledby="config-tab">
            <McpServerForm
              defaultValues={server}
              onSubmit={handleSubmit}
              isSubmitting={updateMutation.isPending}
              submitLabel="Update Server"
            />
          </div>
        )}

        {/* Tools Tab */}
        {activeTab === 'tools' && (
          <div role="tabpanel" id="tools-panel" aria-labelledby="tools-tab" className="space-y-6">
            <TestConnection serverId={serverId} />
            <ToolsList tools={[]} />
          </div>
        )}

        {/* Health Tab */}
        {activeTab === 'health' && (
          <div role="tabpanel" id="health-panel" aria-labelledby="health-tab">
            <HealthLogs serverId={serverId} limit={20} />
          </div>
        )}
      </div>
    </div>
  );
}
