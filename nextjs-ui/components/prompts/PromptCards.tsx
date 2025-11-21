'use client';

/**
 * PromptCards - Card grid layout for prompt templates
 * Displays: name, description, variable count, last updated
 * Layout: 2 columns desktop, 1 mobile
 */

import { formatDistanceToNow } from 'date-fns';
import { Edit, FileText } from 'lucide-react';
import Link from 'next/link';
import type { PromptTemplate } from '@/lib/api/prompts';
import { Badge } from '../ui/Badge';
import { Button } from '../ui/Button';
import { Card } from '../ui/Card';

interface PromptCardsProps {
  prompts: PromptTemplate[];
  canEdit: boolean;
}

export function PromptCards({ prompts, canEdit }: PromptCardsProps) {
  if (prompts.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center">
        <FileText className="h-12 w-12 text-gray-400 mb-4" />
        <h3 className="text-lg font-semibold text-gray-900 mb-2">
          No prompts yet
        </h3>
        <p className="text-sm text-gray-500 mb-4">
          Create your first prompt template to get started.
        </p>
        {canEdit && (
          <Link href="/dashboard/prompts/new">
            <Button>Create Prompt</Button>
          </Link>
        )}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {prompts.map((prompt) => (
        <Card key={prompt.id} className="p-6 hover:shadow-md transition-shadow">
          <div className="flex items-start justify-between mb-3">
            <h3 className="text-lg font-semibold text-gray-900 truncate flex-1">
              {prompt.name}
            </h3>
            {canEdit && (
              <Link href={`/dashboard/prompts/${prompt.id}`}>
                <Button variant="ghost" size="sm">
                  <Edit className="h-4 w-4" />
                </Button>
              </Link>
            )}
          </div>

          <p className="text-sm text-gray-600 mb-4 line-clamp-2">
            {prompt.description || 'No description provided'}
          </p>

          <div className="flex items-center justify-between text-xs text-gray-500">
            <div className="flex items-center gap-2">
              <Badge variant="info">
                {prompt.variables.length} variable
                {prompt.variables.length !== 1 ? 's' : ''}
              </Badge>
            </div>
            <span>
              Updated{' '}
              {formatDistanceToNow(new Date(prompt.updated_at), {
                addSuffix: true,
              })}
            </span>
          </div>
        </Card>
      ))}
    </div>
  );
}
