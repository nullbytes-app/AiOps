/**
 * Stdio Configuration Component
 *
 * Form fields for configuring stdio-based MCP servers
 * (command, args, environment variables, working directory)
 */

'use client';

import React from 'react';
import { Control } from 'react-hook-form';
import { Input } from '@/components/ui/Input';
import { FormField } from '@/components/forms/FormField';
import { EnvironmentVariables } from './EnvironmentVariables';
import { Terminal } from 'lucide-react';
import type { MCPServerCreateData } from '@/lib/validations';

interface StdioConfigProps {
  control: Control<MCPServerCreateData>;
}

export function StdioConfig({ control }: StdioConfigProps) {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-2">
        <Terminal className="h-5 w-5 text-accent-blue" />
        <h3 className="text-lg font-semibold text-text-primary">
          Stdio Configuration
        </h3>
      </div>

      {/* Command */}
      <FormField
        control={control}
        name="connection_config.command"
        render={({ field, fieldState }) => (
          <Input
            {...field}
            label="Command"
            placeholder="npx"
            error={fieldState.error?.message}
            helpText="The command to execute (e.g., npx, python, node)"
            required
          />
        )}
      />

      {/* Arguments */}
      <FormField
        control={control}
        name="connection_config.args"
        render={({ field, fieldState }) => (
          <Input
            {...field}
            value={Array.isArray(field.value) ? field.value.join(' ') : field.value || ''}
            onChange={(e) => {
              const args = e.target.value.split(' ').filter((arg) => arg.trim() !== '');
              field.onChange(args);
            }}
            label="Arguments"
            placeholder="-y @modelcontextprotocol/server-filesystem /path/to/allowed/files"
            error={fieldState.error?.message}
            helpText="Space-separated command arguments"
          />
        )}
      />

      {/* Working Directory */}
      <FormField
        control={control}
        name="connection_config.cwd"
        render={({ field, fieldState }) => (
          <Input
            {...field}
            label="Working Directory"
            placeholder="/path/to/working/directory"
            error={fieldState.error?.message}
            helpText="Optional working directory for the process"
          />
        )}
      />

      {/* Environment Variables */}
      <EnvironmentVariables control={control} name="connection_config.env" />

      {/* Info Box */}
      <div className="glass-card p-4 bg-blue-50 border border-blue-200">
        <h4 className="text-sm font-semibold text-blue-900 mb-2">Stdio Server Info</h4>
        <ul className="text-sm text-blue-800 space-y-1 list-disc list-inside">
          <li>The server will be started as a subprocess</li>
          <li>Communication happens via stdin/stdout</li>
          <li>The process is managed by the AI Agents platform</li>
          <li>Environment variables are passed to the subprocess</li>
        </ul>
      </div>
    </div>
  );
}
