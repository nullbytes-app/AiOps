'use client';

/**
 * Prompt Editor Page (/prompts/[id])
 * Split-pane layout: Editor (60%) + Preview (40%)
 * Features: CodeMirror editor, variable extraction, preview rendering
 */

import { useParams, useRouter } from 'next/navigation';
import { useSession } from 'next-auth/react';
import { useState, useEffect } from 'react';
import { ArrowLeft, Trash2 } from 'lucide-react';
import { usePrompt, useUpdatePrompt, useDeletePrompt } from '@/lib/hooks/usePrompts';
import { PromptEditor } from '@/components/prompts/PromptEditor';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Label } from '@/components/ui/Label';
import { Textarea } from '@/components/ui/Textarea';
import { Loading } from '@/components/ui/Loading';
import { ConfirmDialog } from '@/components/ui/ConfirmDialog';

export default function PromptDetailPage() {
  const params = useParams();
  const router = useRouter();
  const { data: session } = useSession();
  const id = params.id as string;

  const { data: prompt, isLoading, error } = usePrompt(id);
  const updateMutation = useUpdatePrompt();
  const deleteMutation = useDeletePrompt();

  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [templateText, setTemplateText] = useState('');
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [hasChanges, setHasChanges] = useState(false);

  const userRole = session?.user?.role || 'viewer';
  const canEdit = ['tenant_admin', 'developer'].includes(userRole);

  // Initialize form when prompt loads
  useEffect(() => {
    if (prompt) {
      setName(prompt.name);
      setDescription(prompt.description || '');
      setTemplateText(prompt.template_text);
    }
  }, [prompt]);

  // Track changes
  useEffect(() => {
    if (prompt) {
      const changed =
        name !== prompt.name ||
        description !== (prompt.description || '') ||
        templateText !== prompt.template_text;
      setHasChanges(changed);
    }
  }, [name, description, templateText, prompt]);

  const handleSave = async () => {
    await updateMutation.mutateAsync({
      id,
      data: {
        name,
        description: description || undefined,
        template_text: templateText,
      },
    });
    setHasChanges(false);
  };

  const handleRevert = () => {
    if (prompt) {
      setName(prompt.name);
      setDescription(prompt.description || '');
      setTemplateText(prompt.template_text);
      setHasChanges(false);
    }
  };

  const handleDelete = async () => {
    await deleteMutation.mutateAsync(id);
    router.push('/dashboard/prompts');
  };

  if (isLoading) {
    return (
      <div className="p-6">
        <Loading size="lg" text="Loading prompt..." />
      </div>
    );
  }

  if (error || !prompt) {
    return (
      <div className="p-6">
        <div className="bg-red-50 border border-red-200 rounded-md p-4">
          <p className="text-sm text-red-800">
            Failed to load prompt: {error ? (error as Error).message : 'Not found'}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 h-screen flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => router.push('/dashboard/prompts')}
          >
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back
          </Button>
          <h1 className="text-2xl font-bold text-gray-900">Edit Prompt</h1>
        </div>
        {canEdit && (
          <Button
            variant="danger"
            size="sm"
            onClick={() => setShowDeleteDialog(true)}
          >
            <Trash2 className="h-4 w-4 mr-2" />
            Delete
          </Button>
        )}
      </div>

      {/* Metadata Fields */}
      {canEdit ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
          <div>
            <Label htmlFor="name">Prompt Name *</Label>
            <Input
              id="name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g., Ticket Enhancer Prompt"
            />
          </div>
          <div>
            <Label htmlFor="description">Description</Label>
            <Textarea
              id="description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Optional description"
              rows={1}
            />
          </div>
        </div>
      ) : (
        <div className="mb-4 p-4 bg-gray-50 rounded-md">
          <h2 className="text-lg font-semibold">{prompt.name}</h2>
          {prompt.description && (
            <p className="text-sm text-gray-600 mt-1">{prompt.description}</p>
          )}
          <p className="text-xs text-gray-500 mt-2">
            Read-only view (no edit permission)
          </p>
        </div>
      )}

      {/* Editor */}
      <div className="flex-1 overflow-hidden">
        {canEdit ? (
          <PromptEditor
            value={templateText}
            onChange={setTemplateText}
            onSave={handleSave}
            onRevert={hasChanges ? handleRevert : undefined}
            isSubmitting={updateMutation.isPending}
          />
        ) : (
          <div className="border border-gray-200 rounded-md p-4 bg-gray-50 h-full overflow-auto">
            <pre className="text-sm text-gray-900 whitespace-pre-wrap font-mono">
              {prompt.template_text}
            </pre>
          </div>
        )}
      </div>

      {/* Delete Confirmation Dialog */}
      <ConfirmDialog
        isOpen={showDeleteDialog}
        onClose={() => setShowDeleteDialog(false)}
        title="Delete Prompt"
        description={`Are you sure you want to delete "${prompt.name}"? This action cannot be undone.`}
        confirmLabel="Delete Prompt"
        onConfirm={handleDelete}
        confirmVariant="danger"
        isLoading={deleteMutation.isPending}
      />
    </div>
  );
}
