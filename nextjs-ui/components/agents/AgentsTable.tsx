"use client";

import { Agent } from '@/lib/api/agents';
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/Table';
import { Button, Badge } from '@/components/ui';
import { Edit, Trash2, Play } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';

/**
 * Agents Table Component
 *
 * Displays list of agents with actions
 */

interface AgentsTableProps {
  agents: Agent[];
  onEdit: (agent: Agent) => void;
  onDelete: (agent: Agent) => void;
  onTest?: (agent: Agent) => void;
  isLoading?: boolean;
}

export function AgentsTable({
  agents,
  onEdit,
  onDelete,
  onTest,
  isLoading = false,
}: AgentsTableProps) {
  if (isLoading) {
    return (
      <div className="glass-card p-12 text-center">
        <div className="inline-block w-8 h-8 border-4 border-accent-blue border-t-transparent rounded-full animate-spin" />
        <p className="mt-4 text-text-secondary">Loading agents...</p>
      </div>
    );
  }

  const getTypeColor = (type: string) => {
    const colors: Record<string, 'default' | 'success' | 'warning' | 'error' | 'info'> = {
      conversational: 'info',
      tool_based: 'success',
      langgraph: 'warning',
      custom: 'default',
    };
    return colors[type] || 'default';
  };

  return (
    <div className="glass-card overflow-hidden">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Name</TableHead>
            <TableHead>Type</TableHead>
            <TableHead>LLM Provider</TableHead>
            <TableHead>Tools</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>Created</TableHead>
            <TableHead className="text-right">Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {agents.map((agent) => (
            <TableRow key={agent.id}>
              <TableCell>
                <div>
                  <div className="font-medium text-text-primary">
                    {agent.name}
                  </div>
                  {agent.description && (
                    <div className="text-xs text-text-secondary truncate max-w-xs">
                      {agent.description}
                    </div>
                  )}
                </div>
              </TableCell>
              <TableCell>
                <Badge variant={getTypeColor(agent.type)}>
                  {agent.type.replace('_', ' ')}
                </Badge>
              </TableCell>
              <TableCell>
                <div className="text-sm text-text-secondary">
                  {agent.llm_config?.model || '—'}
                </div>
              </TableCell>
              <TableCell>
                <Badge variant="default">
                  {agent.tool_ids?.length || 0} tools
                </Badge>
              </TableCell>
              <TableCell>
                <Badge variant={agent.is_active ? 'success' : 'default'}>
                  {agent.is_active ? 'Active' : 'Inactive'}
                </Badge>
              </TableCell>
              <TableCell>
                <div className="text-sm text-text-secondary">
                  {formatDistanceToNow(new Date(agent.created_at), {
                    addSuffix: true,
                  })}
                </div>
              </TableCell>
              <TableCell>
                <div className="flex gap-2 justify-end">
                  {onTest && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => onTest(agent)}
                      title="Test agent"
                    >
                      <Play className="w-4 h-4" />
                    </Button>
                  )}
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => onEdit(agent)}
                    title="Edit agent"
                  >
                    <Edit className="w-4 h-4" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => onDelete(agent)}
                    title="Delete agent"
                  >
                    <Trash2 className="w-4 h-4 text-red-500" />
                  </Button>
                </div>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
