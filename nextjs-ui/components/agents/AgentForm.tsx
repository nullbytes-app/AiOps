"use client";

import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { AgentFormData, agentCreateSchema, agentTypeEnum, cognitiveArchitectureEnum } from '@/lib/validations/agents';
import { Form, FormField } from '@/components/forms';
import { Input, Textarea, Button, Select } from '@/components/ui';
import { Agent } from '@/lib/api/agents';
import { useLLMProviders } from '@/lib/hooks/useLLMProviders';

/**
 * Agent Form Component
 *
 * Reusable form for creating and editing agents
 * with LLM configuration
 */

interface AgentFormProps {
  onSubmit: (data: AgentFormData) => void;
  defaultValues?: Partial<Agent>;
  isLoading?: boolean;
  onCancel?: () => void;
  mode?: 'create' | 'edit';
}

export function AgentForm({
  onSubmit,
  defaultValues,
  isLoading = false,
  onCancel,
  mode = 'create',
}: AgentFormProps) {
  const { data: llmProviders = [] } = useLLMProviders();

  const form = useForm<AgentFormData>({
    resolver: zodResolver(agentCreateSchema),
    defaultValues: {
      name: defaultValues?.name || '',
      type: defaultValues?.type || 'conversational',
      description: defaultValues?.description || '',
      system_prompt: defaultValues?.system_prompt || '',
      llm_config: defaultValues?.llm_config || {
        provider_id: '',
        model: '',
        temperature: 0.7,
        max_tokens: undefined,
        top_p: undefined,
      },
      tool_ids: defaultValues?.tool_ids || [],
      is_active: defaultValues?.is_active ?? true,
      cognitive_architecture: (defaultValues?.cognitive_architecture || 'react') as 'react' | 'single_step' | 'plan_and_solve',
    },
  });

  const selectedProvider = llmProviders.find(
    (p) => p.id === form.watch('llm_config.provider_id')
  );

  return (
    <Form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
      {/* Basic Info */}
      <div className="space-y-4">
        <h3 className="text-lg font-semibold text-text-primary">Basic Information</h3>

        <FormField
          control={form.control}
          name="name"
          render={({ field, fieldState }) => (
            <Input
              {...field}
              label="Agent Name"
              placeholder="Customer Support Agent"
              error={fieldState.error?.message}
              required
            />
          )}
        />

        <FormField
          control={form.control}
          name="type"
          render={({ field, fieldState }) => (
            <Select
              {...field}
              label="Agent Type"
              error={fieldState.error?.message}
              options={agentTypeEnum.options.map((type) => ({
                value: type,
                label: type.charAt(0).toUpperCase() + type.slice(1).replace('_', ' '),
              }))}
              required
            />
          )}
        />

        <FormField
          control={form.control}
          name="description"
          render={({ field, fieldState }) => (
            <Textarea
              {...field}
              label="Description"
              placeholder="Brief description of the agent's purpose"
              error={fieldState.error?.message}
              rows={2}
            />
          )}
        />
      </div>

      {/* Cognitive Architecture */}
      <div className="space-y-4 pt-4 border-t border-white/20">
        <h3 className="text-lg font-semibold text-text-primary">Cognitive Architecture</h3>

        <FormField
          control={form.control}
          name="cognitive_architecture"
          render={({ field, fieldState }) => (
            <Select
              {...field}
              label="Execution Strategy"
              error={fieldState.error?.message}
              options={cognitiveArchitectureEnum.options.map((arch) => ({
                value: arch,
                label: arch === 'react' ? 'ReAct (Reasoning + Acting)' :
                  arch === 'single_step' ? 'Single Step (Zero-shot)' :
                    'Plan and Solve',
              }))}
              helpText="How the agent processes and executes tasks"
              required
            />
          )}
        />
      </div>

      {/* LLM Configuration */}
      <div className="space-y-4 pt-4 border-white/20">
        <h3 className="text-lg font-semibold text-text-primary">LLM Configuration</h3>

        <FormField
          control={form.control}
          name="llm_config.provider_id"
          render={({ field, fieldState }) => (
            <Select
              {...field}
              label="LLM Provider"
              error={fieldState.error?.message}
              options={llmProviders.map((provider) => ({
                value: provider.id,
                label: provider.name,
              }))}
              placeholder="Select a provider"
              required
            />
          )}
        />

        <FormField
          control={form.control}
          name="llm_config.model"
          render={({ field, fieldState }) => (
            selectedProvider?.models && selectedProvider.models.length > 0 ? (
              <Select
                {...field}
                label="Model"
                error={fieldState.error?.message}
                options={selectedProvider.models.map((model) => ({
                  value: model.id,
                  label: model.name,
                }))}
                placeholder="Select a model"
                required
              />
            ) : (
              <Input
                {...field}
                label="Model"
                placeholder="gpt-4, claude-3-opus-20240229, etc."
                error={fieldState.error?.message}
                helpText={!selectedProvider ? "Select a provider first" : "Enter model name"}
                required
              />
            )
          )}
        />

        <div className="grid grid-cols-3 gap-4">
          <FormField
            control={form.control}
            name="llm_config.temperature"
            render={({ field, fieldState }) => (
              <Input
                {...field}
                type="number"
                label="Temperature"
                placeholder="0.7"
                error={fieldState.error?.message}
                min={0}
                max={2}
                step={0.1}
                onChange={(e) => {
                  const value = e.target.value === '' ? 0 : parseFloat(e.target.value);
                  field.onChange(value);
                }}
                value={field.value ?? ''}
              />
            )}
          />

          <FormField
            control={form.control}
            name="llm_config.max_tokens"
            render={({ field, fieldState }) => (
              <Input
                {...field}
                type="number"
                label="Max Tokens"
                placeholder="4096"
                error={fieldState.error?.message}
                min={1}
                max={128000}
                onChange={(e) => field.onChange(e.target.value ? parseInt(e.target.value) : undefined)}
                value={field.value || ''}
              />
            )}
          />

          <FormField
            control={form.control}
            name="llm_config.top_p"
            render={({ field, fieldState }) => (
              <Input
                {...field}
                type="number"
                label="Top P"
                placeholder="1.0"
                error={fieldState.error?.message}
                min={0}
                max={1}
                step={0.1}
                onChange={(e) => field.onChange(e.target.value ? parseFloat(e.target.value) : undefined)}
                value={field.value || ''}
              />
            )}
          />
        </div>
      </div>

      {/* System Prompt */}
      <div className="space-y-4 pt-4 border-t border-white/20">
        <h3 className="text-lg font-semibold text-text-primary">System Prompt</h3>

        <FormField
          control={form.control}
          name="system_prompt"
          render={({ field, fieldState }) => (
            <Textarea
              {...field}
              label="System Prompt"
              placeholder="You are a helpful assistant..."
              error={fieldState.error?.message}
              rows={8}
              helpText="Instructions that define the agent's behavior and personality"
              required
            />
          )}
        />
      </div>

      {/* Form Actions */}
      <div className="flex gap-3 justify-end pt-4 border-t border-white/20">
        {onCancel && (
          <Button
            type="button"
            variant="ghost"
            onClick={onCancel}
            disabled={isLoading}
          >
            Cancel
          </Button>
        )}
        <Button
          type="submit"
          variant="primary"
          isLoading={isLoading}
        >
          {mode === 'create' ? 'Create Agent' : 'Update Agent'}
        </Button>
      </div>
    </Form>
  );
}
