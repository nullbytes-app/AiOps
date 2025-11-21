'use client';

import { useRouter } from 'next/navigation';
import { useCreatePlugin } from '@/lib/hooks/usePlugins';
import { PluginForm } from '@/components/plugins/PluginForm';
import { ArrowLeft } from 'lucide-react';
import { Button } from '@/components/ui/Button';

export default function NewPluginPage() {
  const router = useRouter();
  const createPlugin = useCreatePlugin();

  const handleSubmit = (data: {
    name: string;
    type: 'webhook' | 'polling';
    description?: string;
    webhook_hmac_secret: string;
    polling_interval: string;
    polling_api_endpoint: string;
    polling_auth_type: 'none' | 'api_key' | 'bearer' | 'basic';
    polling_api_key_name: string;
    polling_api_key_value: string;
    polling_bearer_token: string;
    polling_basic_username: string;
    polling_basic_password: string;
  }) => {
    // Build auth_config based on auth type
    let authConfig: Record<string, string> = {};
    if (data.type === 'polling') {
      if (data.polling_auth_type === 'api_key') {
        authConfig = {
          key_name: data.polling_api_key_name,
          key_value: data.polling_api_key_value,
        };
      } else if (data.polling_auth_type === 'bearer') {
        authConfig = {
          token: data.polling_bearer_token,
        };
      } else if (data.polling_auth_type === 'basic') {
        authConfig = {
          username: data.polling_basic_username,
          password: data.polling_basic_password,
        };
      }
    }

    // Transform form data to API format
    const payload = {
      name: data.name,
      type: data.type,
      description: data.description,
      config:
        data.type === 'webhook'
          ? {
              webhook: {
                hmac_secret: data.webhook_hmac_secret,
              },
            }
          : {
              polling: {
                interval: data.polling_interval,
                api_endpoint: data.polling_api_endpoint,
                auth_type: data.polling_auth_type,
                auth_config: authConfig,
              },
            },
    };

    createPlugin.mutate(payload, {
      onSuccess: (newPlugin) => {
        router.push(`/dashboard/plugins/${newPlugin.id}`);
      },
    });
  };

  const handleCancel = () => {
    router.back();
  };

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="sm" onClick={() => router.back()}>
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <div>
          <h1 className="text-2xl font-bold">Add Plugin</h1>
          <p className="text-muted-foreground">
            Configure a new webhook or polling plugin for external system integration
          </p>
        </div>
      </div>

      {/* Form */}
      <PluginForm
        onSubmit={handleSubmit}
        onCancel={handleCancel}
        isSubmitting={createPlugin.isPending}
        mode="create"
      />
    </div>
  );
}
