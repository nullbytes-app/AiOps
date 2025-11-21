/**
 * LLM Provider Form Component
 *
 * Create/edit form for LLM providers with:
 * - Name, Type, Base URL, API Key fields
 * - API key masking with show/hide toggle
 * - Test connection before submit
 * - Validation with Zod
 */

'use client';

import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { Button } from '@/components/ui/Button';
import { TestConnection } from './TestConnection';
import { Eye, EyeOff, Loader2 } from 'lucide-react';
import { llmProviderSchema, type LLMProviderFormData } from '@/lib/validations/llm-providers';

interface ProviderFormProps {
  onSubmit: (data: LLMProviderFormData) => Promise<void>;
  onCancel?: () => void;
  defaultValues?: Partial<LLMProviderFormData>;
  isLoading?: boolean;
  mode?: 'create' | 'edit';
}

/**
 * Provider Form Component
 *
 * AC-3 Requirement: Provider configuration form with test connection
 */
export function ProviderForm({
  onSubmit,
  onCancel,
  defaultValues,
  isLoading,
  mode = 'create',
}: ProviderFormProps) {
  const [showApiKey, setShowApiKey] = useState(false);
  const [testResult, setTestResult] = useState<{
    success: boolean;
    response_time_ms: number;
    models_found: number;
    models?: string[];
    error?: string;
  } | null>(null);
  const [isTesting, setIsTesting] = useState(false);
  const [hasTestedSuccessfully, setHasTestedSuccessfully] = useState(mode === 'edit');

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<LLMProviderFormData>({
    resolver: zodResolver(llmProviderSchema),
    defaultValues: defaultValues || {
      type: 'openai',
      models: [],
      is_active: true,
    },
  });

  const selectedType = watch('type');
  const needsBaseUrl = selectedType === 'custom';

  const handleTestConnection = async () => {
    setIsTesting(true);
    setTestResult(null);

    try {
      // Mock test - will be replaced with actual API call
      await new Promise((resolve) => setTimeout(resolve, 1500));

      const mockResult = {
        success: true,
        response_time_ms: 245,
        models_found: 15,
        models: [
          'gpt-4-turbo-preview',
          'gpt-4',
          'gpt-3.5-turbo',
          'gpt-3.5-turbo-16k',
        ],
      };

      setTestResult(mockResult);
      setHasTestedSuccessfully(true);
      return mockResult;
    } catch {
      const errorResult = {
        success: false,
        response_time_ms: 0,
        models_found: 0,
        error: 'Invalid API key or connection timeout',
      };
      setTestResult(errorResult);
      setHasTestedSuccessfully(false);
      return errorResult;
    } finally {
      setIsTesting(false);
    }
  };

  const handleFormSubmit = async (data: LLMProviderFormData) => {
    await onSubmit(data);
  };

  return (
    <form onSubmit={handleSubmit(handleFormSubmit)} className="space-y-6">
      {/* Name Field */}
      <div>
        <label htmlFor="name" className="block text-sm font-medium text-text-primary mb-2">
          Provider Name *
        </label>
        <input
          id="name"
          type="text"
          {...register('name')}
          placeholder="e.g., OpenAI Production"
          className="w-full px-4 py-2 bg-glass-surface border border-glass-border rounded-lg focus:outline-none focus:ring-2 focus:ring-accent-primary/50 text-text-primary placeholder:text-text-tertiary"
          aria-invalid={errors.name ? 'true' : 'false'}
          aria-describedby={errors.name ? 'name-error' : undefined}
        />
        {errors.name && (
          <p id="name-error" className="text-sm text-destructive mt-1">
            {errors.name.message}
          </p>
        )}
      </div>

      {/* Type Field */}
      <div>
        <label htmlFor="type" className="block text-sm font-medium text-text-primary mb-2">
          Provider Type *
        </label>
        <select
          id="type"
          {...register('type')}
          className="w-full px-4 py-2 bg-glass-surface border border-glass-border rounded-lg focus:outline-none focus:ring-2 focus:ring-accent-primary/50 text-text-primary"
          aria-describedby={errors.type ? 'type-error' : undefined}
        >
          <option value="openai">OpenAI</option>
          <option value="anthropic">Anthropic</option>
          <option value="azure_openai">Azure OpenAI</option>
          <option value="custom_litellm">Custom LiteLLM</option>
        </select>
        {errors.type && (
          <p id="type-error" className="text-sm text-destructive mt-1">
            {errors.type.message}
          </p>
        )}
      </div>

      {/* Base URL Field (conditional) */}
      {needsBaseUrl && (
        <div>
          <label htmlFor="base_url" className="block text-sm font-medium text-text-primary mb-2">
            Base URL *
          </label>
          <input
            id="base_url"
            type="url"
            {...register('base_url')}
            placeholder="https://api.example.com/v1"
            className="w-full px-4 py-2 bg-glass-surface border border-glass-border rounded-lg focus:outline-none focus:ring-2 focus:ring-accent-primary/50 text-text-primary placeholder:text-text-tertiary"
            aria-describedby={errors.base_url ? 'base-url-error' : undefined}
          />
          {errors.base_url && (
            <p id="base-url-error" className="text-sm text-destructive mt-1">
              {errors.base_url.message}
            </p>
          )}
        </div>
      )}

      {/* API Key Field with Show/Hide Toggle */}
      <div>
        <label htmlFor="api_key" className="block text-sm font-medium text-text-primary mb-2">
          API Key *
        </label>
        <div className="relative">
          <input
            id="api_key"
            type={showApiKey ? 'text' : 'password'}
            {...register('api_key')}
            placeholder={mode === 'edit' ? '••••••••last4' : 'sk-...'}
            className="w-full px-4 py-2 pr-12 bg-glass-surface border border-glass-border rounded-lg focus:outline-none focus:ring-2 focus:ring-accent-primary/50 text-text-primary placeholder:text-text-tertiary font-mono text-sm"
            aria-invalid={errors.api_key ? 'true' : 'false'}
            aria-describedby={errors.api_key ? 'api-key-error' : undefined}
          />
          <button
            type="button"
            onClick={() => setShowApiKey(!showApiKey)}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-text-secondary hover:text-text-primary transition-colors"
            aria-label={showApiKey ? 'Hide API key' : 'Show API key'}
          >
            {showApiKey ? (
              <EyeOff className="w-5 h-5" />
            ) : (
              <Eye className="w-5 h-5" />
            )}
          </button>
        </div>
        {errors.api_key && (
          <p id="api-key-error" className="text-sm text-destructive mt-1">
            {errors.api_key.message}
          </p>
        )}
      </div>

      {/* Test Connection */}
      <div className="border-t border-glass-border pt-6">
        <h4 className="text-sm font-semibold text-text-primary mb-4">
          Verify Connection
        </h4>
        <TestConnection
          onTest={handleTestConnection}
          isLoading={isTesting}
          result={testResult}
        />
        {!hasTestedSuccessfully && mode === 'create' && (
          <p className="text-xs text-text-secondary mt-2">
            * Test connection must succeed before you can save this provider
          </p>
        )}
      </div>

      {/* Form Actions */}
      <div className="flex gap-4 pt-6 border-t border-glass-border">
        {onCancel && (
          <Button
            type="button"
            variant="ghost"
            onClick={onCancel}
            disabled={isSubmitting}
          >
            Cancel
          </Button>
        )}
        <Button
          type="submit"
          disabled={isSubmitting || isLoading || (!hasTestedSuccessfully && mode === 'create')}
          className="gap-2"
        >
          {isSubmitting || isLoading ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              {mode === 'create' ? 'Creating...' : 'Updating...'}
            </>
          ) : (
            <>{mode === 'create' ? 'Create Provider' : 'Update Provider'}</>
          )}
        </Button>
      </div>
    </form>
  );
}
