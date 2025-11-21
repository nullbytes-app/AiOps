'use client';

/**
 * System Prompts Page (/prompts)
 * Card grid layout displaying all prompt templates
 * RBAC: tenant_admin + developer (full CRUD), operator + viewer (read-only)
 */

import { useSession } from 'next-auth/react';
import Link from 'next/link';
import { Plus } from 'lucide-react';
import { usePrompts } from '@/lib/hooks/usePrompts';
import { PromptCards } from '@/components/prompts/PromptCards';
import { Button } from '@/components/ui/Button';
import { Loading } from '@/components/ui/Loading';

export default function PromptsPage() {
  const { data: session } = useSession();
  const { data: prompts, isLoading, error } = usePrompts();

  const userRole = session?.user?.role || 'viewer';
  const canEdit = ['tenant_admin', 'developer'].includes(userRole);

  if (isLoading) {
    return (
      <div className="p-6">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-bold">System Prompts</h1>
        </div>
        <Loading size="lg" text="Loading prompts..." />
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6">
        <div className="bg-red-50 border border-red-200 rounded-md p-4">
          <p className="text-sm text-red-800">
            Failed to load prompts: {(error as Error).message}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">System Prompts</h1>
          <p className="text-sm text-gray-500 mt-1">
            Manage LLM prompt templates with variable substitution
          </p>
        </div>
        {canEdit && (
          <Link href="/dashboard/prompts/new">
            <Button>
              <Plus className="h-4 w-4 mr-2" />
              Create Prompt
            </Button>
          </Link>
        )}
      </div>

      <PromptCards prompts={prompts || []} canEdit={canEdit} />
    </div>
  );
}
