'use client';

/**
 * Create Prompt Page (/prompts/new)
 * Form for creating new prompt template
 * Fields: Name (required), Description (optional), Template (CodeMirror)
 */

import { useRouter } from 'next/navigation';
import { useSession } from 'next-auth/react';
import { useState, useEffect } from 'react';
import { ArrowLeft } from 'lucide-react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useCreatePrompt } from '@/lib/hooks/usePrompts';
import { PromptEditor } from '@/components/prompts/PromptEditor';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Label } from '@/components/ui/Label';
import { Textarea } from '@/components/ui/Textarea';

const createPromptSchema = z.object({
  name: z.string().min(1, 'Name is required').max(100, 'Name too long'),
  description: z.string().max(500, 'Description too long').catch(''),
  template_text: z.string().min(1, 'Template is required'),
});

type CreatePromptForm = z.infer<typeof createPromptSchema>;

const DEFAULT_TEMPLATE = `# System Prompt Template
# Available variables: {{agent_name}}, {{ticket_id}}, {{user_name}}

You are {{agent_name}}, an AI assistant helping with ticket {{ticket_id}}.`;

export default function NewPromptPage() {
  const router = useRouter();
  const { data: session } = useSession();
  const createMutation = useCreatePrompt();

  const [templateText, setTemplateText] = useState(DEFAULT_TEMPLATE);

  const userRole = session?.user?.role || 'viewer';
  const canCreate = ['tenant_admin', 'developer'].includes(userRole);

  const {
    register,
    handleSubmit,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm<CreatePromptForm>({
    resolver: zodResolver(createPromptSchema),
    defaultValues: {
      name: '',
      description: '',
      template_text: DEFAULT_TEMPLATE,
    },
  });

  // Sync CodeMirror value with form
  useEffect(() => {
    setValue('template_text', templateText);
  }, [templateText, setValue]);

  // Redirect if no permission
  useEffect(() => {
    if (session && !canCreate) {
      router.push('/dashboard/prompts');
    }
  }, [session, canCreate, router]);

  const onSubmit = async (data: CreatePromptForm) => {
    const result = await createMutation.mutateAsync(data);
    router.push(`/dashboard/prompts/${result.id}`);
  };

  if (!canCreate) {
    return (
      <div className="p-6">
        <div className="bg-yellow-50 border border-yellow-200 rounded-md p-4">
          <p className="text-sm text-yellow-800">
            You do not have permission to create prompts.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 h-screen flex flex-col">
      <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col h-full">
        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <Button
              variant="ghost"
              size="sm"
              type="button"
              onClick={() => router.push('/dashboard/prompts')}
            >
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back
            </Button>
            <h1 className="text-2xl font-bold text-gray-900">Create Prompt</h1>
          </div>
          <Button type="submit" disabled={isSubmitting}>
            {isSubmitting ? 'Creating...' : 'Create Prompt'}
          </Button>
        </div>

        {/* Metadata Fields */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
          <div>
            <Label htmlFor="name">Prompt Name *</Label>
            <Input
              id="name"
              {...register('name')}
              placeholder="e.g., Ticket Enhancer Prompt"
            />
            {errors.name && (
              <p className="text-sm text-red-600 mt-1">{errors.name.message}</p>
            )}
          </div>
          <div>
            <Label htmlFor="description">Description</Label>
            <Textarea
              id="description"
              {...register('description')}
              placeholder="Optional description"
              rows={1}
            />
            {errors.description && (
              <p className="text-sm text-red-600 mt-1">
                {errors.description.message}
              </p>
            )}
          </div>
        </div>

        {/* Editor */}
        <div className="flex-1 overflow-hidden">
          <PromptEditor
            value={templateText}
            onChange={setTemplateText}
            onSave={handleSubmit(onSubmit)}
            isSubmitting={isSubmitting}
          />
          {errors.template_text && (
            <p className="text-sm text-red-600 mt-2">
              {errors.template_text.message}
            </p>
          )}
        </div>
      </form>
    </div>
  );
}
