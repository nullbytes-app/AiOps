/**
 * MCP Server Form Component
 *
 * Conditional form that renders different config fields based on server type
 * Uses React Hook Form watch() for type-based conditional rendering
 */

'use client';

import React from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { mcpServerCreateSchema } from '@/lib/validations/mcp-servers';
import type { MCPServerCreateData } from '@/lib/validations';
import { Input } from '@/components/ui/Input';
import { Textarea } from '@/components/ui/Textarea';
import { Button } from '@/components/ui/Button';
import { FormField } from '@/components/forms/FormField';
import { ConnectionConfig } from './ConnectionConfig';
import { StdioConfig } from './StdioConfig';
import { Database, Loader2 } from 'lucide-react';

interface McpServerFormProps {
  defaultValues?: Partial<MCPServerCreateData>;
  onSubmit: (data: MCPServerCreateData) => Promise<void>;
  isSubmitting?: boolean;
  submitLabel?: string;
}

export function McpServerForm({
  defaultValues,
  onSubmit,
  isSubmitting = false,
  submitLabel = 'Create Server',
}: McpServerFormProps) {
  const form = useForm<MCPServerCreateData>({
    // @ts-expect-error - Zod type inference issue with default values
    resolver: zodResolver(mcpServerCreateSchema),
    defaultValues: defaultValues || {
      name: '',
      type: 'http',
      description: '',
      health_check_enabled: true,
      is_active: true,
      connection_config: {
        url: '',
        timeout: 30000,
        headers: {},
      },
    },
  });

  const serverType = form.watch('type');

  const handleSubmit = async (data: MCPServerCreateData) => {
    try {
      await onSubmit(data);
      form.reset();
    } catch (error) {
      console.error('Form submission error:', error);
    }
  };

  return (
    // @ts-expect-error - Zod type inference issue with default values
    <form onSubmit={form.handleSubmit(handleSubmit)} className="space-y-6">
      {/* Basic Information */}
      <div className="glass-card p-6 space-y-6">
        <div className="flex items-center gap-2 mb-4">
          <Database className="h-5 w-5 text-accent-blue" />
          <h3 className="text-lg font-semibold text-text-primary">Basic Information</h3>
        </div>

        {/* Name */}
        <FormField
          // @ts-expect-error - react-hook-form type inference issue
          control={form.control}
          name="name"
          render={({ field, fieldState }) => (
            <Input
              {...field}
              label="Server Name"
              placeholder="My MCP Server"
              error={fieldState.error?.message}
              helpText="A unique, descriptive name for this MCP server"
              required
            />
          )}
        />

        {/* Type */}
        <FormField
          // @ts-expect-error - react-hook-form type inference issue
          control={form.control}
          name="type"
          render={({ field, fieldState }) => (
            <div className="space-y-2">
              <label className="block text-sm font-medium text-text-primary">
                Server Type <span className="text-destructive">*</span>
              </label>
              <select
                {...field}
                className="w-full px-4 py-2 rounded-lg border border-border bg-white text-text-primary focus:outline-none focus:ring-2 focus:ring-accent-blue"
              >
                <option value="http">HTTP (Stateless)</option>
                <option value="sse">SSE (Server-Sent Events)</option>
                <option value="stdio">stdio (Command-line)</option>
              </select>
              {fieldState.error && (
                <p className="text-sm text-destructive">{fieldState.error.message}</p>
              )}
              <p className="text-xs text-text-secondary">
                {serverType === 'http' && 'Stateless POST requests to HTTP endpoint'}
                {serverType === 'sse' && 'Persistent connection using Server-Sent Events'}
                {serverType === 'stdio' && 'Local subprocess communication via stdin/stdout'}
              </p>
            </div>
          )}
        />

        {/* Description */}
        <FormField
          // @ts-expect-error - react-hook-form type inference issue
          control={form.control}
          name="description"
          render={({ field, fieldState }) => (
            <Textarea
              {...field}
              label="Description"
              placeholder="Brief description of what this server does"
              error={fieldState.error?.message}
              rows={3}
            />
          )}
        />

        {/* Health Check Enabled */}
        <FormField
          // @ts-expect-error - react-hook-form type inference issue
          control={form.control}
          name="health_check_enabled"
          render={({ field }) => (
            <label className="flex items-center gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={field.value}
                onChange={field.onChange}
                className="w-5 h-5 rounded border-border text-accent-blue focus:ring-2 focus:ring-accent-blue"
              />
              <div>
                <span className="text-sm font-medium text-text-primary">
                  Enable Health Checks
                </span>
                <p className="text-xs text-text-secondary">
                  Periodically check server availability and log health status
                </p>
              </div>
            </label>
          )}
        />

        {/* Is Active */}
        <FormField
          // @ts-expect-error - react-hook-form type inference issue
          control={form.control}
          name="is_active"
          render={({ field }) => (
            <label className="flex items-center gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={field.value}
                onChange={field.onChange}
                className="w-5 h-5 rounded border-border text-accent-blue focus:ring-2 focus:ring-accent-blue"
              />
              <div>
                <span className="text-sm font-medium text-text-primary">Active</span>
                <p className="text-xs text-text-secondary">
                  Server is active and available for agent use
                </p>
              </div>
            </label>
          )}
        />
      </div>

      {/* Conditional Connection Configuration */}
      <div className="glass-card p-6">
        {serverType === 'stdio' ? (
          // @ts-expect-error - Zod type inference issue with control prop
          <StdioConfig control={form.control} />
        ) : (
          // @ts-expect-error - Zod type inference issue with control prop
          <ConnectionConfig control={form.control} />
        )}
      </div>

      {/* Submit Button */}
      <div className="flex items-center justify-end gap-3">
        <Button
          type="button"
          variant="secondary"
          onClick={() => form.reset()}
          disabled={isSubmitting}
        >
          Reset
        </Button>
        <Button type="submit" disabled={isSubmitting} className="gap-2">
          {isSubmitting && <Loader2 className="h-4 w-4 animate-spin" />}
          {submitLabel}
        </Button>
      </div>
    </form>
  );
}
