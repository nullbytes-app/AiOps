'use client';

/**
 * ImportConfig - Form for configuring tool import
 * Fields: Name prefix, Base URL, Auth type, Auth credentials
 */

import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import type { AuthConfig } from '@/lib/api/tools';
import { Button } from '../ui/Button';
import { Input } from '../ui/Input';
import { Label } from '../ui/Label';
import { Select } from '../ui/Select';

const importConfigSchema = z.object({
  name_prefix: z.string().max(50, 'Prefix too long').catch(''),
  base_url: z.string().url('Invalid URL').min(1, 'Base URL is required'),
  auth_type: z.enum(['none', 'api_key', 'bearer', 'basic']),
  api_key_name: z.string().catch(''),
  api_key_location: z.enum(['header', 'query']).catch('header'),
  api_key_value: z.string().catch(''),
  bearer_token: z.string().catch(''),
  basic_username: z.string().catch(''),
  basic_password: z.string().catch(''),
});

type ImportConfigForm = z.infer<typeof importConfigSchema>;

interface ImportConfigProps {
  onSubmit: (config: {
    namePrefix?: string;
    baseUrl: string;
    authConfig: AuthConfig;
  }) => void;
  isLoading?: boolean;
}

export function ImportConfig({ onSubmit, isLoading = false }: ImportConfigProps) {
  const {
    register,
    handleSubmit,
    watch,
    formState: { errors, isValid },
  } = useForm<ImportConfigForm>({
    resolver: zodResolver(importConfigSchema),
    defaultValues: {
      name_prefix: '',
      base_url: '',
      auth_type: 'none',
      api_key_name: 'X-API-Key',
      api_key_location: 'header',
      api_key_value: '',
      bearer_token: '',
      basic_username: '',
      basic_password: '',
    },
    mode: 'onChange',
  });

  const authType = watch('auth_type');

  const handleFormSubmit = (data: ImportConfigForm) => {
    const authConfig: AuthConfig = {
      type: data.auth_type,
    };

    if (data.auth_type === 'api_key') {
      authConfig.api_key_name = data.api_key_name;
      authConfig.api_key_location = data.api_key_location;
      authConfig.api_key_value = data.api_key_value;
    } else if (data.auth_type === 'bearer') {
      authConfig.bearer_token = data.bearer_token;
    } else if (data.auth_type === 'basic') {
      authConfig.basic_username = data.basic_username;
      authConfig.basic_password = data.basic_password;
    }

    onSubmit({
      namePrefix: data.name_prefix || undefined,
      baseUrl: data.base_url,
      authConfig,
    });
  };

  return (
    <form onSubmit={handleSubmit(handleFormSubmit)} className="space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Name Prefix */}
        <div>
          <Label htmlFor="name_prefix">Tool Name Prefix (Optional)</Label>
          <Input
            id="name_prefix"
            {...register('name_prefix')}
            placeholder="e.g., jira_"
            disabled={isLoading}
          />
          <p className="text-xs text-gray-500 mt-1">
            Prefix added to operation IDs (e.g., jira_createIssue)
          </p>
          {errors.name_prefix && (
            <p className="text-sm text-red-600 mt-1">{errors.name_prefix.message}</p>
          )}
        </div>

        {/* Base URL */}
        <div>
          <Label htmlFor="base_url">Base URL *</Label>
          <Input
            id="base_url"
            {...register('base_url')}
            placeholder="https://api.example.com/v1"
            disabled={isLoading}
          />
          <p className="text-xs text-gray-500 mt-1">
            API base URL for tool execution
          </p>
          {errors.base_url && (
            <p className="text-sm text-red-600 mt-1">{errors.base_url.message}</p>
          )}
        </div>
      </div>

      {/* Auth Type */}
      <div>
        <Label htmlFor="auth_type">Authentication Type</Label>
        <Select
          id="auth_type"
          {...register('auth_type')}
          disabled={isLoading}
          options={[
            { value: 'none', label: 'None' },
            { value: 'api_key', label: 'API Key' },
            { value: 'bearer', label: 'Bearer Token' },
            { value: 'basic', label: 'Basic Auth' },
          ]}
        />
      </div>

      {/* API Key Auth Fields */}
      {authType === 'api_key' && (
        <div className="space-y-3 p-4 bg-gray-50 rounded-md">
          <p className="text-sm font-medium text-gray-700">API Key Configuration</p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div>
              <Label htmlFor="api_key_name">Key Name</Label>
              <Input
                id="api_key_name"
                {...register('api_key_name')}
                placeholder="X-API-Key"
                disabled={isLoading}
              />
            </div>
            <div>
              <Label htmlFor="api_key_location">Location</Label>
              <Select
                id="api_key_location"
                {...register('api_key_location')}
                disabled={isLoading}
                options={[
                  { value: 'header', label: 'Header' },
                  { value: 'query', label: 'Query Parameter' },
                ]}
              />
            </div>
          </div>
          <div>
            <Label htmlFor="api_key_value">API Key Value</Label>
            <Input
              id="api_key_value"
              type="password"
              {...register('api_key_value')}
              placeholder="Enter API key"
              disabled={isLoading}
            />
          </div>
        </div>
      )}

      {/* Bearer Token Auth Fields */}
      {authType === 'bearer' && (
        <div className="space-y-3 p-4 bg-gray-50 rounded-md">
          <p className="text-sm font-medium text-gray-700">Bearer Token Configuration</p>
          <div>
            <Label htmlFor="bearer_token">Bearer Token</Label>
            <Input
              id="bearer_token"
              type="password"
              {...register('bearer_token')}
              placeholder="Enter bearer token"
              disabled={isLoading}
            />
          </div>
        </div>
      )}

      {/* Basic Auth Fields */}
      {authType === 'basic' && (
        <div className="space-y-3 p-4 bg-gray-50 rounded-md">
          <p className="text-sm font-medium text-gray-700">Basic Authentication</p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div>
              <Label htmlFor="basic_username">Username</Label>
              <Input
                id="basic_username"
                {...register('basic_username')}
                placeholder="Enter username"
                disabled={isLoading}
              />
            </div>
            <div>
              <Label htmlFor="basic_password">Password</Label>
              <Input
                id="basic_password"
                type="password"
                {...register('basic_password')}
                placeholder="Enter password"
                disabled={isLoading}
              />
            </div>
          </div>
        </div>
      )}

      {/* Submit Button */}
      <div className="flex justify-end pt-4 border-t border-gray-200">
        <Button type="submit" disabled={!isValid || isLoading}>
          {isLoading ? 'Importing...' : 'Import Tools'}
        </Button>
      </div>
    </form>
  );
}
