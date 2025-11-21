/**
 * Model List Component
 *
 * Displays available models from an LLM provider:
 * - Model ID
 * - Context window
 * - Cost per 1K tokens (input/output)
 */

'use client';

import React from 'react';
import { Button } from '@/components/ui/Button';
import { RefreshCw } from 'lucide-react';
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/Table';

interface Model {
  id: string;
  context_window?: number;
  cost_per_1k_input?: number;
  cost_per_1k_output?: number;
}

interface ModelListProps {
  models: Model[];
  isLoading?: boolean;
  onRefresh?: () => void;
}

/**
 * Model List Component
 *
 * AC-3 Requirement: Models tab with model details table
 */
export function ModelList({ models, isLoading, onRefresh }: ModelListProps) {
  if (models.length === 0) {
    return (
      <div className="text-center py-12">
        <p className="text-text-secondary mb-4">
          No models discovered yet. Click &quot;Refresh Models&quot; to discover available models.
        </p>
        {onRefresh && (
          <Button onClick={onRefresh} disabled={isLoading} className="gap-2">
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
            Refresh Models
          </Button>
        )}
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header with Refresh Button */}
      <div className="flex items-center justify-between">
        <div>
          <h4 className="text-sm font-semibold text-text-primary">
            Available Models ({models.length})
          </h4>
          <p className="text-xs text-text-secondary mt-1">
            Models discovered from this provider
          </p>
        </div>
        {onRefresh && (
          <Button
            onClick={onRefresh}
            disabled={isLoading}
            variant="secondary"
            size="sm"
            className="gap-2"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        )}
      </div>

      {/* Models Table */}
      <div className="glass-card rounded-lg overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Model ID</TableHead>
              <TableHead className="text-right">Context Window</TableHead>
              <TableHead className="text-right">Input Cost</TableHead>
              <TableHead className="text-right">Output Cost</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {models.map((model) => (
              <TableRow key={model.id}>
                <TableCell className="font-mono text-sm">{model.id}</TableCell>
                <TableCell className="text-right">
                  {model.context_window ? `${model.context_window.toLocaleString()} tokens` : 'N/A'}
                </TableCell>
                <TableCell className="text-right">
                  {model.cost_per_1k_input !== undefined ? `$${model.cost_per_1k_input.toFixed(4)} / 1K` : 'N/A'}
                </TableCell>
                <TableCell className="text-right">
                  {model.cost_per_1k_output !== undefined ? `$${model.cost_per_1k_output.toFixed(4)} / 1K` : 'N/A'}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
