/**
 * Provider Card Component
 *
 * Displays an LLM provider in a card format with:
 * - Provider logo/icon
 * - Provider name
 * - Model count badge
 * - Status badge (Healthy/Unhealthy/Unknown)
 * - Action buttons (Edit, Test, Delete)
 */

'use client';

import React from 'react';
import Link from 'next/link';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Edit, TestTube, Trash2, Zap } from 'lucide-react';
import type { LLMProvider } from '@/lib/api/llm-providers';

interface ProviderCardProps {
  provider: LLMProvider;
  onTest?: (id: string) => void;
  onDelete?: (id: string) => void;
}

/**
 * Provider Card Component
 *
 * AC-3 Requirement: Card grid layout with provider information
 */
export function ProviderCard({ provider, onTest, onDelete }: ProviderCardProps) {
  const statusColors: Record<string, 'success' | 'error' | 'default'> = {
    healthy: 'success',
    unhealthy: 'error',
    unknown: 'default',
  };

  const providerIcons: Record<string, string> = {
    openai: '🤖',
    anthropic: '🧠',
    azure_openai: '☁️',
    custom_litellm: '⚡',
    custom: '⚙️',
    openrouter: '🔀',
  };

  return (
    <div className="glass-card p-6 hover:shadow-lg transition-shadow duration-300">
      {/* Header with Logo and Status */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="text-4xl" role="img" aria-label={`${provider.type} icon`}>
            {providerIcons[provider.type] || '📦'}
          </div>
          <div>
            <h3 className="text-lg font-semibold text-text-primary">
              {provider.name}
            </h3>
            <p className="text-xs text-text-secondary capitalize">
              {provider.type.replace('_', ' ')}
            </p>
          </div>
        </div>
        <Badge variant={statusColors[provider.status || 'unknown'] || 'default'}>
          {provider.status || 'unknown'}
        </Badge>
      </div>

      {/* Model Count */}
      <div className="mb-4">
        <div className="flex items-center gap-2 text-text-secondary">
          <Zap className="w-4 h-4" />
          <span className="text-sm">
            {provider.models?.length || 0} model{(provider.models?.length || 0) !== 1 ? 's' : ''}
          </span>
        </div>
      </div>

      {/* Actions */}
      <div className="flex gap-2">
        <Link href={`/dashboard/llm-providers/${provider.id}`} className="flex-1">
          <Button variant="secondary" size="sm" className="w-full gap-2">
            <Edit className="w-4 h-4" />
            Edit
          </Button>
        </Link>
        <Button
          variant="secondary"
          size="sm"
          onClick={() => onTest?.(provider.id)}
          className="gap-2"
        >
          <TestTube className="w-4 h-4" />
          Test
        </Button>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => onDelete?.(provider.id)}
          className="text-destructive hover:bg-destructive/10"
        >
          <Trash2 className="w-4 h-4" />
        </Button>
      </div>
    </div>
  );
}
