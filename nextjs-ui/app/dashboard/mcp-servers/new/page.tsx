/**
 * Create MCP Server Page
 *
 * Form for creating a new MCP server configuration
 */

'use client';

import React from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { ArrowLeft } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { McpServerForm } from '@/components/mcp-servers/McpServerForm';
import { useCreateMCPServer } from '@/lib/hooks/useMCPServers';
import type { MCPServerCreateData } from '@/lib/validations';

/**
 * Create MCP Server Page
 */
export default function CreateMcpServerPage() {
  const router = useRouter();
  const createMutation = useCreateMCPServer();

  const handleSubmit = async (data: MCPServerCreateData) => {
    await createMutation.mutateAsync(data);
    router.push('/dashboard/mcp-servers');
  };

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
        <div>
          <h1 className="text-3xl font-bold text-foreground">Create MCP Server</h1>
          <p className="text-muted-foreground mt-2">
            Configure a new Model Context Protocol server connection
          </p>
        </div>
      </div>

      {/* Form */}
      <McpServerForm
        onSubmit={handleSubmit}
        isSubmitting={createMutation.isPending}
        submitLabel="Create Server"
      />
    </div>
  );
}
