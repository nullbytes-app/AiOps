'use client';

import { useForm, Controller } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Label } from '@/components/ui/Label';
import { Select } from '@/components/ui/Select';
import { Textarea } from '@/components/ui/Textarea';
import { Card } from '@/components/ui/Card';
import { Eye, EyeOff } from 'lucide-react';
import { useState } from 'react';

// Zod schema with conditional validation based on plugin type
const pluginSchema = z
  .object({
    name: z.string().min(1, 'Name is required').max(100, 'Name must be less than 100 characters'),
    type: z.enum(['webhook', 'polling'], { message: 'Type is required' }),
    description: z.string().catch(''),
    // Webhook-specific fields
    webhook_hmac_secret: z.string().catch(''),
    // Polling-specific fields
    polling_interval: z.string().catch('5min'),
    polling_api_endpoint: z.string().url('Invalid URL').catch(''),
    polling_auth_type: z.enum(['none', 'api_key', 'bearer', 'basic']).catch('none'),
    polling_api_key_name: z.string().catch(''),
    polling_api_key_value: z.string().catch(''),
    polling_bearer_token: z.string().catch(''),
    polling_basic_username: z.string().catch(''),
    polling_basic_password: z.string().catch(''),
  })
  .refine(
    (data) => {
      // Webhook: hmac_secret required
      if (data.type === 'webhook') {
        return data.webhook_hmac_secret.length > 0;
      }
      return true;
    },
    {
      message: 'HMAC secret is required for webhook plugins',
      path: ['webhook_hmac_secret'],
    }
  )
  .refine(
    (data) => {
      // Polling: api_endpoint required
      if (data.type === 'polling') {
        return data.polling_api_endpoint.length > 0;
      }
      return true;
    },
    {
      message: 'API endpoint is required for polling plugins',
      path: ['polling_api_endpoint'],
    }
  )
  .refine(
    (data) => {
      // Polling with API key: key name and value required
      if (data.type === 'polling' && data.polling_auth_type === 'api_key') {
        return data.polling_api_key_name.length > 0 && data.polling_api_key_value.length > 0;
      }
      return true;
    },
    {
      message: 'API key name and value are required',
      path: ['polling_api_key_value'],
    }
  )
  .refine(
    (data) => {
      // Polling with Bearer: token required
      if (data.type === 'polling' && data.polling_auth_type === 'bearer') {
        return data.polling_bearer_token.length > 0;
      }
      return true;
    },
    {
      message: 'Bearer token is required',
      path: ['polling_bearer_token'],
    }
  )
  .refine(
    (data) => {
      // Polling with Basic: username and password required
      if (data.type === 'polling' && data.polling_auth_type === 'basic') {
        return data.polling_basic_username.length > 0 && data.polling_basic_password.length > 0;
      }
      return true;
    },
    {
      message: 'Username and password are required',
      path: ['polling_basic_password'],
    }
  );

export type PluginFormData = z.infer<typeof pluginSchema>;

interface PluginFormProps {
  initialData?: Partial<PluginFormData>;
  onSubmit: (data: PluginFormData) => void;
  onCancel: () => void;
  isSubmitting?: boolean;
  mode?: 'create' | 'edit';
  generatedWebhookUrl?: string; // For webhook plugins in edit mode
}

export function PluginForm({
  initialData,
  onSubmit,
  onCancel,
  isSubmitting = false,
  mode = 'create',
  generatedWebhookUrl,
}: PluginFormProps) {
  const {
    register,
    handleSubmit,
    control,
    watch,
    formState: { errors, isDirty },
  } = useForm<PluginFormData>({
    resolver: zodResolver(pluginSchema),
    defaultValues: {
      name: initialData?.name || '',
      type: initialData?.type || 'webhook',
      description: initialData?.description || '',
      webhook_hmac_secret: initialData?.webhook_hmac_secret || '',
      polling_interval: initialData?.polling_interval || '5min',
      polling_api_endpoint: initialData?.polling_api_endpoint || '',
      polling_auth_type: initialData?.polling_auth_type || 'none',
      polling_api_key_name: initialData?.polling_api_key_name || '',
      polling_api_key_value: initialData?.polling_api_key_value || '',
      polling_bearer_token: initialData?.polling_bearer_token || '',
      polling_basic_username: initialData?.polling_basic_username || '',
      polling_basic_password: initialData?.polling_basic_password || '',
    },
  });

  // Watch type field for conditional rendering
  const pluginType = watch('type');
  const pollingAuthType = watch('polling_auth_type');

  // State for password visibility toggles
  const [showHmacSecret, setShowHmacSecret] = useState(false);
  const [showApiKeyValue, setShowApiKeyValue] = useState(false);
  const [showBearerToken, setShowBearerToken] = useState(false);
  const [showBasicPassword, setShowBasicPassword] = useState(false);

  // Copy to clipboard helper
  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
      {/* Basic Information */}
      <Card className="p-6">
        <h3 className="text-lg font-semibold mb-4">Basic Information</h3>

        <div className="space-y-4">
          {/* Name */}
          <div>
            <Label htmlFor="name">Plugin Name *</Label>
            <Input
              id="name"
              {...register('name')}
              placeholder="e.g., ServiceDesk Plus Sync"
              error={errors.name?.message}
            />
          </div>

          {/* Type */}
          <div>
            <Label htmlFor="type">Plugin Type *</Label>
            <Controller
              name="type"
              control={control}
              render={({ field }) => (
                <Select
                  {...field}
                  options={[
                    { value: 'webhook', label: 'Webhook (Push)' },
                    { value: 'polling', label: 'Polling (Pull)' },
                  ]}
                  error={errors.type?.message}
                />
              )}
            />
            <p className="text-sm text-muted-foreground mt-1">
              {pluginType === 'webhook'
                ? 'Webhook plugins receive data via HTTP POST requests'
                : 'Polling plugins fetch data at regular intervals'}
            </p>
          </div>

          {/* Description */}
          <div>
            <Label htmlFor="description">Description</Label>
            <Textarea
              id="description"
              {...register('description')}
              placeholder="Describe what this plugin does..."
              rows={3}
            />
          </div>
        </div>
      </Card>

      {/* Webhook Configuration */}
      {pluginType === 'webhook' && (
        <Card className="p-6">
          <h3 className="text-lg font-semibold mb-4">Webhook Configuration</h3>

          {/* Generated Webhook URL (edit mode only) */}
          {mode === 'edit' && generatedWebhookUrl && (
            <div className="mb-4">
              <Label>Webhook Endpoint URL</Label>
              <div className="flex gap-2 mt-1">
                <Input value={generatedWebhookUrl} readOnly className="font-mono text-sm" />
                <Button
                  type="button"
                  variant="secondary"
                  onClick={() => copyToClipboard(generatedWebhookUrl)}
                >
                  Copy
                </Button>
              </div>
              <p className="text-sm text-muted-foreground mt-1">
                Configure this URL in your external system to send webhook events
              </p>
            </div>
          )}

          {/* HMAC Secret */}
          <div>
            <Label htmlFor="webhook_hmac_secret">HMAC Secret *</Label>
            <div className="flex gap-2">
              <div className="relative flex-1">
                <Input
                  id="webhook_hmac_secret"
                  type={showHmacSecret ? 'text' : 'password'}
                  {...register('webhook_hmac_secret')}
                  placeholder="Enter HMAC secret for signature validation"
                  error={errors.webhook_hmac_secret?.message}
                  className="pr-10"
                />
                <button
                  type="button"
                  onClick={() => setShowHmacSecret(!showHmacSecret)}
                  className="absolute right-2 top-1/2 -translate-y-1/2"
                >
                  {showHmacSecret ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
            </div>
            <p className="text-sm text-muted-foreground mt-1">
              Used to validate webhook signatures (HMAC-SHA256)
            </p>
          </div>
        </Card>
      )}

      {/* Polling Configuration */}
      {pluginType === 'polling' && (
        <Card className="p-6">
          <h3 className="text-lg font-semibold mb-4">Polling Configuration</h3>

          <div className="space-y-4">
            {/* Polling Interval */}
            <div>
              <Label htmlFor="polling_interval">Polling Interval *</Label>
              <Controller
                name="polling_interval"
                control={control}
                render={({ field }) => (
                  <Select
                    {...field}
                    options={[
                      { value: '1min', label: 'Every 1 minute' },
                      { value: '5min', label: 'Every 5 minutes' },
                      { value: '15min', label: 'Every 15 minutes' },
                      { value: '30min', label: 'Every 30 minutes' },
                      { value: '1hour', label: 'Every 1 hour' },
                    ]}
                  />
                )}
              />
            </div>

            {/* API Endpoint */}
            <div>
              <Label htmlFor="polling_api_endpoint">API Endpoint URL *</Label>
              <Input
                id="polling_api_endpoint"
                type="url"
                {...register('polling_api_endpoint')}
                placeholder="https://api.example.com/v1/data"
                error={errors.polling_api_endpoint?.message}
              />
            </div>

            {/* Auth Type */}
            <div>
              <Label htmlFor="polling_auth_type">Authentication Type *</Label>
              <Controller
                name="polling_auth_type"
                control={control}
                render={({ field }) => (
                  <Select
                    {...field}
                    options={[
                      { value: 'none', label: 'None' },
                      { value: 'api_key', label: 'API Key (Header/Query)' },
                      { value: 'bearer', label: 'Bearer Token' },
                      { value: 'basic', label: 'Basic Auth' },
                    ]}
                  />
                )}
              />
            </div>

            {/* API Key Auth Fields */}
            {pollingAuthType === 'api_key' && (
              <div className="space-y-4 pl-4 border-l-2 border-accent">
                <div>
                  <Label htmlFor="polling_api_key_name">API Key Name *</Label>
                  <Input
                    id="polling_api_key_name"
                    {...register('polling_api_key_name')}
                    placeholder="e.g., X-API-Key, api_key"
                    error={errors.polling_api_key_name?.message}
                  />
                  <p className="text-sm text-muted-foreground mt-1">
                    Header name or query parameter name
                  </p>
                </div>
                <div>
                  <Label htmlFor="polling_api_key_value">API Key Value *</Label>
                  <div className="relative">
                    <Input
                      id="polling_api_key_value"
                      type={showApiKeyValue ? 'text' : 'password'}
                      {...register('polling_api_key_value')}
                      placeholder="Enter API key"
                      error={errors.polling_api_key_value?.message}
                      className="pr-10"
                    />
                    <button
                      type="button"
                      onClick={() => setShowApiKeyValue(!showApiKeyValue)}
                      className="absolute right-2 top-1/2 -translate-y-1/2"
                    >
                      {showApiKeyValue ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </button>
                  </div>
                </div>
              </div>
            )}

            {/* Bearer Token Auth Fields */}
            {pollingAuthType === 'bearer' && (
              <div className="pl-4 border-l-2 border-accent">
                <Label htmlFor="polling_bearer_token">Bearer Token *</Label>
                <div className="relative">
                  <Input
                    id="polling_bearer_token"
                    type={showBearerToken ? 'text' : 'password'}
                    {...register('polling_bearer_token')}
                    placeholder="Enter bearer token"
                    error={errors.polling_bearer_token?.message}
                    className="pr-10"
                  />
                  <button
                    type="button"
                    onClick={() => setShowBearerToken(!showBearerToken)}
                    className="absolute right-2 top-1/2 -translate-y-1/2"
                  >
                    {showBearerToken ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
              </div>
            )}

            {/* Basic Auth Fields */}
            {pollingAuthType === 'basic' && (
              <div className="space-y-4 pl-4 border-l-2 border-accent">
                <div>
                  <Label htmlFor="polling_basic_username">Username *</Label>
                  <Input
                    id="polling_basic_username"
                    {...register('polling_basic_username')}
                    placeholder="Enter username"
                    error={errors.polling_basic_username?.message}
                  />
                </div>
                <div>
                  <Label htmlFor="polling_basic_password">Password *</Label>
                  <div className="relative">
                    <Input
                      id="polling_basic_password"
                      type={showBasicPassword ? 'text' : 'password'}
                      {...register('polling_basic_password')}
                      placeholder="Enter password"
                      error={errors.polling_basic_password?.message}
                      className="pr-10"
                    />
                    <button
                      type="button"
                      onClick={() => setShowBasicPassword(!showBasicPassword)}
                      className="absolute right-2 top-1/2 -translate-y-1/2"
                    >
                      {showBasicPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
        </Card>
      )}

      {/* Form Actions */}
      <div className="flex justify-end gap-3">
        <Button type="button" variant="secondary" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="submit" disabled={isSubmitting || (mode === 'edit' && !isDirty)}>
          {isSubmitting ? 'Saving...' : mode === 'create' ? 'Create Plugin' : 'Save Changes'}
        </Button>
      </div>
    </form>
  );
}
