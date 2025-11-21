/**
 * Agent Selector Component
 * Dropdown for selecting an agent to view performance metrics
 * Following 2025 shadcn/ui Select patterns
 */

'use client';

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useAgents } from '@/hooks/useAgents';

interface AgentSelectorProps {
  value: string | null;
  onChange: (agentId: string) => void;
}

export function AgentSelector({ value, onChange }: AgentSelectorProps) {
  const { data, isLoading, error } = useAgents();

  if (isLoading) {
    return <div className="h-10 w-64 bg-gray-200 animate-pulse rounded-md" />;
  }

  if (error) {
    return <div className="text-sm text-red-600">Failed to load agents</div>;
  }

  const agents = data?.data || [];

  return (
    <Select value={value || undefined} onValueChange={onChange}>
      <SelectTrigger className="w-64">
        <SelectValue placeholder="Select an agent..." />
      </SelectTrigger>
      <SelectContent>
        {agents.map((agent) => (
          <SelectItem key={agent.id} value={agent.id}>
            {agent.name}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
