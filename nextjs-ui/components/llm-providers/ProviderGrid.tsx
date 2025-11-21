/**
 * Provider Grid Component
 *
 * Displays LLM providers in a responsive grid layout
 * - 3 columns on desktop
 * - 2 columns on tablet
 * - 1 column on mobile
 */

'use client';

import React from 'react';
import { ProviderCard } from './ProviderCard';
import type { LLMProvider } from '@/lib/api/llm-providers';
import { EmptyState } from '@/components/ui/EmptyState';
import { Zap } from 'lucide-react';

interface ProviderGridProps {
  providers: LLMProvider[];
  onTest?: (id: string) => void;
  onDelete?: (id: string) => void;
}

/**
 * Provider Grid Component
 *
 * AC-3 Requirement: Card grid layout with responsive breakpoints
 */
export function ProviderGrid({ providers, onTest, onDelete }: ProviderGridProps) {
  if (providers.length === 0) {
    return (
      <EmptyState
        icon={<Zap className="w-12 h-12" />}
        title="No LLM Providers Connected"
        description="Add a provider to enable AI agent capabilities. Supports OpenAI, Anthropic, Azure OpenAI, and custom LiteLLM providers."
      />
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      {providers.map((provider) => (
        <ProviderCard
          key={provider.id}
          provider={provider}
          onTest={onTest}
          onDelete={onDelete}
        />
      ))}
    </div>
  );
}
