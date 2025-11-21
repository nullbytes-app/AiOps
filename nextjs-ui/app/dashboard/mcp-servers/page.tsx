/**
 * MCP Servers List Page
 *
 * Displays all MCP servers with filtering, CRUD operations, and connection testing.
 */

'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { Plus, AlertCircle, RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { McpServerTable } from '@/components/mcp-servers/McpServerTable';
import { useMCPServers, useDeleteMCPServer, useTestMCPServerConnection } from '@/lib/hooks/useMCPServers';
import { toast } from 'sonner';

/**
 * Loading State Component
 */
function LoadingState() {
  return (
    <div className="space-y-6">
      <div className="animate-pulse space-y-4">
        <div className="h-8 bg-white/50 rounded w-1/4" />
        <div className="h-64 bg-white/50 rounded" />
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
        Failed to Load MCP Servers
      </h2>
      <p className="text-muted-foreground mb-6 max-w-md text-center">
        We couldn&apos;t fetch the MCP servers data. Please check your connection and try again.
      </p>
      <Button onClick={onRetry} className="gap-2">
        <RefreshCw className="h-4 w-4" />
        Retry
      </Button>
    </div>
  );
}

/**
 * Confirm Delete Dialog
 */
function ConfirmDeleteDialog({
  isOpen,
  serverName,
  onConfirm,
  onCancel,
}: {
  isOpen: boolean;
  serverName: string;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="glass-card p-6 max-w-md w-full mx-4">
        <h3 className="text-lg font-semibold text-text-primary mb-2">
          Delete MCP Server
        </h3>
        <p className="text-text-secondary mb-6">
          Are you sure you want to delete <strong>{serverName}</strong>? This action cannot be undone.
        </p>
        <div className="flex items-center justify-end gap-3">
          <Button variant="secondary" onClick={onCancel}>
            Cancel
          </Button>
          <Button variant="primary" onClick={onConfirm} className="bg-destructive hover:bg-destructive/90">
            Delete
          </Button>
        </div>
      </div>
    </div>
  );
}

/**
 * MCP Servers List Page
 */
export default function McpServersPage() {
  const { data: servers, isLoading, isError, refetch } = useMCPServers();
  const deleteMutation = useDeleteMCPServer();
  const testMutation = useTestMCPServerConnection();

  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [serverToDelete, setServerToDelete] = useState<{ id: string; name: string } | null>(null);

  /**
   * Handle delete server
   */
  const handleDelete = (id: string) => {
    const server = servers?.find((s) => s.id === id);
    if (server) {
      setServerToDelete({ id, name: server.name });
      setDeleteDialogOpen(true);
    }
  };

  /**
   * Confirm delete
   */
  const confirmDelete = async () => {
    if (serverToDelete) {
      try {
        await deleteMutation.mutateAsync(serverToDelete.id);
        toast.success(`Deleted ${serverToDelete.name}`);
      } catch {
        // Error toast handled by mutation
      }
      setDeleteDialogOpen(false);
      setServerToDelete(null);
    }
  };

  /**
   * Handle test connection
   */
  const handleTest = async (id: string) => {
    try {
      await testMutation.mutateAsync({ server_id: id });
    } catch {
      // Error toast handled by mutation
    }
  };

  // Loading state
  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-foreground">MCP Servers</h1>
            <p className="text-muted-foreground mt-2">
              Manage Model Context Protocol server connections
            </p>
          </div>
        </div>
        <LoadingState />
      </div>
    );
  }

  // Error state
  if (isError) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-foreground">MCP Servers</h1>
            <p className="text-muted-foreground mt-2">
              Manage Model Context Protocol server connections
            </p>
          </div>
        </div>
        <ErrorState onRetry={refetch} />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-foreground">MCP Servers</h1>
          <p className="text-muted-foreground mt-2">
            Manage Model Context Protocol server connections
          </p>
        </div>
        <Link href="/dashboard/mcp-servers/new">
          <Button className="gap-2">
            <Plus className="h-4 w-4" />
            Add Server
          </Button>
        </Link>
      </div>

      {/* MCP Servers Table */}
      <McpServerTable
        servers={servers || []}
        onDelete={handleDelete}
        onTest={handleTest}
      />

      {/* Delete Confirmation Dialog */}
      <ConfirmDeleteDialog
        isOpen={deleteDialogOpen}
        serverName={serverToDelete?.name || ''}
        onConfirm={confirmDelete}
        onCancel={() => {
          setDeleteDialogOpen(false);
          setServerToDelete(null);
        }}
      />
    </div>
  );
}
