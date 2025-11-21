"use client";

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/Table";
import { Progress } from "@/components/ui/Progress";
import { formatCurrency } from "@/lib/utils/budget";
import type { BudgetAgentSpendDTO } from "@/types/costs";

interface AgentBreakdownTableProps {
  /** Array of agent spend data */
  agents: BudgetAgentSpendDTO[];

  /** Optional custom className for the table container */
  className?: string;
}

/**
 * AgentBreakdownTable Component
 *
 * Displays agent-level breakdown of spend within a tenant's budget.
 * Shows agent name, spend amount, percentage of tenant total,
 * and visual mini progress bar.
 *
 * Agents are sorted by spend (highest first) for prioritization.
 *
 * @param agents - Array of agent spend data
 * @param className - Optional custom classes for table container
 *
 * @example
 * ```tsx
 * const agents = [
 *   {
 *     agent_id: "agent-123",
 *     agent_name: "Customer Support Agent",
 *     spent_amount: 3200.00,
 *     percentage_of_tenant: 67.37,
 *   },
 *   {
 *     agent_id: "agent-456",
 *     agent_name: "Sales Assistant",
 *     spent_amount: 1550.50,
 *     percentage_of_tenant: 32.63,
 *   },
 * ];
 *
 * <AgentBreakdownTable agents={agents} />
 * ```
 */
export function AgentBreakdownTable({
  agents,
  className,
}: AgentBreakdownTableProps) {
  // Handle empty state
  if (agents.length === 0) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        <p className="text-sm">No agent data available</p>
      </div>
    );
  }

  // Sort agents by spend (highest first)
  const sortedAgents = [...agents].sort(
    (a, b) => b.spent_amount - a.spent_amount
  );

  return (
    <div className={className}>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="w-[40%]">Agent Name</TableHead>
            <TableHead className="w-[30%] text-right">Spend</TableHead>
            <TableHead className="w-[30%]">% of Tenant Total</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {sortedAgents.map((agent) => (
            <TableRow key={agent.agent_id}>
              {/* Agent Name */}
              <TableCell className="font-medium">
                {agent.agent_name}
              </TableCell>

              {/* Spend Amount */}
              <TableCell className="text-right tabular-nums">
                {formatCurrency(agent.spent_amount)}
              </TableCell>

              {/* Percentage with mini progress bar */}
              <TableCell>
                <div className="space-y-1">
                  <div className="flex justify-between items-center text-xs text-muted-foreground">
                    <span>{agent.percentage_of_tenant.toFixed(1)}%</span>
                  </div>
                  <Progress
                    value={agent.percentage_of_tenant}
                    className="h-1.5"
                    indicatorClassName="bg-accent-blue"
                    aria-label={`${agent.agent_name}: ${agent.percentage_of_tenant.toFixed(1)}% of tenant spend`}
                  />
                </div>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
