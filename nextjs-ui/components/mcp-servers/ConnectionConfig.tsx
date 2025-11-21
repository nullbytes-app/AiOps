/**
 * HTTP/SSE Connection Configuration Component
 *
 * Form fields for configuring HTTP and SSE MCP servers
 * (URL, headers, timeout)
 */

'use client';

import React from 'react';
import { Control, useWatch } from 'react-hook-form';
import { Input } from '@/components/ui/Input';
import { Textarea } from '@/components/ui/Textarea';
import { FormField } from '@/components/forms/FormField';
import { Globe } from 'lucide-react';
import type { MCPServerCreateData } from '@/lib/validations';

interface ConnectionConfigProps {
  control: Control<MCPServerCreateData>;
}

export function ConnectionConfig({ control }: ConnectionConfigProps) {
  const serverType = useWatch({ control, name: 'type' });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-2">
        <Globe className="h-5 w-5 text-accent-blue" />
        <h3 className="text-lg font-semibold text-text-primary">
          {serverType === 'sse' ? 'SSE' : 'HTTP'} Connection
        </h3>
      </div>

      {/* URL */}
      <FormField
        control={control}
        name="connection_config.url"
        render={({ field, fieldState }) => (
          <Input
            {...field}
            label="Server URL"
            placeholder={
              serverType === 'sse'
                ? 'https://api.example.com/sse'
                : 'https://api.example.com/mcp'
            }
            error={fieldState.error?.message}
            helpText={
              serverType === 'sse'
                ? 'SSE endpoint URL for Server-Sent Events connection'
                : 'HTTP POST endpoint URL for stateless requests'
            }
            required
          />
        )}
      />

      {/* Headers (JSON) */}
      <FormField
        control={control}
        name="connection_config.headers"
        render={({ field, fieldState }) => (
          <Textarea
            {...field}
            value={
              typeof field.value === 'object' && field.value !== null
                ? JSON.stringify(field.value, null, 2)
                : field.value || ''
            }
            onChange={(e) => {
              try {
                const parsed = e.target.value ? JSON.parse(e.target.value) : {};
                field.onChange(parsed);
              } catch {
                field.onChange(e.target.value);
              }
            }}
            label="Headers (JSON)"
            placeholder='{"Authorization": "Bearer token", "Content-Type": "application/json"}'
            error={fieldState.error?.message}
            helpText="Optional HTTP headers as JSON object"
            rows={3}
          />
        )}
      />

      {/* Timeout */}
      <FormField
        control={control}
        name="connection_config.timeout"
        render={({ field, fieldState }) => (
          <Input
            {...field}
            type="number"
            label="Timeout (ms)"
            placeholder="30000"
            error={fieldState.error?.message}
            helpText="Connection timeout in milliseconds (default: 30000)"
            min={1000}
            max={300000}
          />
        )}
      />

      {/* Info Box */}
      <div className="glass-card p-4 bg-blue-50 border border-blue-200">
        <h4 className="text-sm font-semibold text-blue-900 mb-2">
          {serverType === 'sse' ? 'SSE Server Info' : 'HTTP Server Info'}
        </h4>
        <ul className="text-sm text-blue-800 space-y-1 list-disc list-inside">
          {serverType === 'sse' ? (
            <>
              <li>Maintains persistent connection for real-time updates</li>
              <li>Uses Server-Sent Events (SSE) protocol</li>
              <li>Supports session management and streaming responses</li>
            </>
          ) : (
            <>
              <li>Stateless POST requests to the endpoint</li>
              <li>Each request is independent</li>
              <li>Simple HTTP-based communication</li>
            </>
          )}
        </ul>
      </div>
    </div>
  );
}
