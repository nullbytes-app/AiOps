/**
 * Environment Variables Component
 *
 * Dynamic form field array for managing environment variables
 * Uses React Hook Form's useFieldArray for add/remove functionality
 */

'use client';

import React from 'react';
import { useFieldArray, Control, FieldPath } from 'react-hook-form';
import { Plus, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { FormField } from '@/components/forms/FormField';
import type { MCPServerCreateData } from '@/lib/validations';

interface EnvironmentVariablesProps {
  control: Control<MCPServerCreateData>;
  name: string;
}

export function EnvironmentVariables({ control, name }: EnvironmentVariablesProps) {
  const { fields, append, remove } = useFieldArray({
    control,
    name: name as 'connection_config.env',
  });

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <label className="block text-sm font-medium text-text-primary">
          Environment Variables
        </label>
        <Button
          type="button"
          variant="secondary"
          size="sm"
          onClick={() => append({ key: '', value: '' })}
          className="gap-2"
        >
          <Plus className="h-4 w-4" />
          Add Variable
        </Button>
      </div>

      {fields.length === 0 ? (
        <div className="glass-card p-6 text-center">
          <p className="text-sm text-text-secondary">
            No environment variables configured. Click &quot;Add Variable&quot; to add one.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {fields.map((field, index) => (
            <div key={field.id} className="glass-card p-4">
              <div className="flex items-start gap-3">
                <div className="flex-1 grid grid-cols-2 gap-3">
                  <FormField
                    control={control}
                    name={`${name}.${index}.key` as FieldPath<MCPServerCreateData>}
                    render={({ field, fieldState }) => (
                      <Input
                        value={typeof field.value === 'string' ? field.value : ''}
                        onChange={field.onChange}
                        onBlur={field.onBlur}
                        ref={field.ref}
                        label="Key"
                        placeholder="API_KEY"
                        error={fieldState.error?.message}
                        aria-label={`Environment variable key ${index + 1}`}
                      />
                    )}
                  />
                  <FormField
                    control={control}
                    name={`${name}.${index}.value` as FieldPath<MCPServerCreateData>}
                    render={({ field, fieldState }) => (
                      <Input
                        value={typeof field.value === 'string' ? field.value : ''}
                        onChange={field.onChange}
                        onBlur={field.onBlur}
                        ref={field.ref}
                        label="Value"
                        placeholder="your-api-key-here"
                        type="password"
                        error={fieldState.error?.message}
                        aria-label={`Environment variable value ${index + 1}`}
                      />
                    )}
                  />
                </div>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => remove(index)}
                  className="mt-6 text-destructive hover:text-destructive hover:bg-destructive/10"
                  aria-label={`Remove environment variable ${index + 1}`}
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}

      <p className="text-xs text-text-secondary">
        Environment variables will be passed to the MCP server process. Keys must be uppercase with underscores (e.g., API_KEY, DATABASE_URL).
      </p>
    </div>
  );
}
