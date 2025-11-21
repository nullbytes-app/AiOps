'use client';

import { use, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import {
  usePluginDetail,
  useUpdatePlugin,
  usePluginSyncLogs,
  useTestPluginConnection,
} from '@/lib/hooks/usePlugins';
import { PluginForm, type PluginFormData } from '@/components/plugins/PluginForm';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Tabs } from '@/components/ui/Tabs';
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from '@/components/ui/Table';
import { ArrowLeft, RefreshCw, PlayCircle, CheckCircle, XCircle } from 'lucide-react';
import { format } from 'date-fns';
import type { UpdatePluginRequest } from '@/lib/api/plugins';

interface PluginDetailPageProps {
  params: Promise<{
    id: string;
  }>;
}

export default function PluginDetailPage({ params }: PluginDetailPageProps) {
  const { id } = use(params);
  const router = useRouter();
  const searchParams = useSearchParams();
  const initialTab = searchParams?.get('tab') || 'config';

  const { data: plugin, isLoading, error } = usePluginDetail(id);
  const updatePlugin = useUpdatePlugin(id);
  const { data: syncLogs, isLoading: logsLoading } = usePluginSyncLogs(id);
  const testConnection = useTestPluginConnection();

  // Map tab names to indices
  const tabMap: Record<string, number> = { config: 0, logs: 1, test: 2 };
  const initialTabIndex = tabMap[initialTab] || 0;

  const [activeTabIndex, setActiveTabIndex] = useState(initialTabIndex);
  const [isEditMode, setIsEditMode] = useState(false);
  const [testResult, setTestResult] = useState<{
    success: boolean;
    message: string;
    details?: Record<string, unknown>;
  } | null>(null);

  // Handle form submission
  const handleSubmit = (data: PluginFormData) => {
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

    const payload: UpdatePluginRequest = {
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

    updatePlugin.mutate(payload, {
      onSuccess: () => {
        setIsEditMode(false);
      },
    });
  };

  // Handle test connection
  const handleTestConnection = () => {
    testConnection.mutate(id, {
      onSuccess: (result) => {
        setTestResult(result);
      },
    });
  };

  // Loading state
  if (isLoading) {
    return (
      <div className="p-6">
        <Card className="p-6">
          <div className="h-96 flex items-center justify-center">
            <RefreshCw className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        </Card>
      </div>
    );
  }

  // Error state
  if (error || !plugin) {
    return (
      <div className="p-6">
        <Card className="p-6">
          <p className="text-destructive">Failed to load plugin: {error?.message || 'Not found'}</p>
        </Card>
      </div>
    );
  }

  // Flatten config for form
  const formData = {
    name: plugin.name,
    type: plugin.type,
    description: '',
    webhook_hmac_secret: plugin.config.webhook?.hmac_secret || '',
    polling_interval: plugin.config.polling?.interval || '5min',
    polling_api_endpoint: plugin.config.polling?.api_endpoint || '',
    polling_auth_type: plugin.config.polling?.auth_type || 'none',
    polling_api_key_name: (plugin.config.polling?.auth_config as Record<string, string>)?.key_name || '',
    polling_api_key_value: (plugin.config.polling?.auth_config as Record<string, string>)?.key_value || '',
    polling_bearer_token: (plugin.config.polling?.auth_config as Record<string, string>)?.token || '',
    polling_basic_username: (plugin.config.polling?.auth_config as Record<string, string>)?.username || '',
    polling_basic_password: (plugin.config.polling?.auth_config as Record<string, string>)?.password || '',
  };

  const generatedWebhookUrl =
    plugin.type === 'webhook'
      ? `${typeof window !== 'undefined' ? window.location.origin : ''}/api/v1/webhooks/plugins/${plugin.id}`
      : undefined;

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="sm" onClick={() => router.back()}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div>
            <h1 className="text-2xl font-bold">{plugin.name}</h1>
            <div className="flex items-center gap-2 mt-1">
              <Badge variant={plugin.type === 'webhook' ? 'default' : 'info'}>
                {plugin.type}
              </Badge>
              <Badge variant={plugin.status === 'active' ? 'success' : 'default'}>
                {plugin.status}
              </Badge>
            </div>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <Tabs
        selectedIndex={activeTabIndex}
        onChange={setActiveTabIndex}
        tabs={[
          {
            key: 'config',
            label: 'Configuration',
            content: (
              <div className="space-y-6">
                {/* Edit Mode Toggle */}
                {!isEditMode ? (
                  <div className="flex justify-end">
                    <Button onClick={() => setIsEditMode(true)}>Edit Configuration</Button>
                  </div>
                ) : null}

                {/* Read-Only Display or Edit Form */}
                {isEditMode ? (
                  <PluginForm
                    initialData={formData}
                    onSubmit={handleSubmit}
                    onCancel={() => setIsEditMode(false)}
                    isSubmitting={updatePlugin.isPending}
                    mode="edit"
                    generatedWebhookUrl={generatedWebhookUrl}
                  />
                ) : (
                  <Card className="p-6">
                    <h3 className="text-lg font-semibold mb-4">Configuration Details</h3>
                    <dl className="space-y-4">
                      <div>
                        <dt className="text-sm font-medium text-muted-foreground">Plugin Name</dt>
                        <dd className="mt-1 text-sm">{plugin.name}</dd>
                      </div>
                      <div>
                        <dt className="text-sm font-medium text-muted-foreground">Type</dt>
                        <dd className="mt-1 text-sm">{plugin.type}</dd>
                      </div>
                      {plugin.type === 'webhook' && generatedWebhookUrl && (
                        <div>
                          <dt className="text-sm font-medium text-muted-foreground">
                            Webhook Endpoint URL
                          </dt>
                          <dd className="mt-1 text-sm font-mono break-all">{generatedWebhookUrl}</dd>
                        </div>
                      )}
                      {plugin.type === 'polling' && (
                        <>
                          <div>
                            <dt className="text-sm font-medium text-muted-foreground">
                              Polling Interval
                            </dt>
                            <dd className="mt-1 text-sm">{plugin.config.polling?.interval}</dd>
                          </div>
                          <div>
                            <dt className="text-sm font-medium text-muted-foreground">
                              API Endpoint
                            </dt>
                            <dd className="mt-1 text-sm font-mono break-all">
                              {plugin.config.polling?.api_endpoint}
                            </dd>
                          </div>
                          <div>
                            <dt className="text-sm font-medium text-muted-foreground">
                              Authentication Type
                            </dt>
                            <dd className="mt-1 text-sm">{plugin.config.polling?.auth_type}</dd>
                          </div>
                        </>
                      )}
                    </dl>
                  </Card>
                )}
              </div>
            ),
          },
          {
            key: 'logs',
            label: 'Sync Logs',
            content: (
              <Card>
                <div className="p-4 border-b">
                  <div className="flex items-center justify-between">
                    <h3 className="text-lg font-semibold">Last 50 Sync Attempts</h3>
                    <p className="text-sm text-muted-foreground">Auto-refresh every 30 seconds</p>
                  </div>
                </div>

                {logsLoading ? (
                  <div className="p-6 flex items-center justify-center">
                    <RefreshCw className="h-6 w-6 animate-spin text-muted-foreground" />
                  </div>
                ) : !syncLogs || syncLogs.length === 0 ? (
                  <div className="p-12 text-center">
                    <p className="text-muted-foreground">No sync logs yet</p>
                  </div>
                ) : (
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Timestamp</TableHead>
                        <TableHead>Status</TableHead>
                        <TableHead>Records Synced</TableHead>
                        <TableHead>Duration</TableHead>
                        <TableHead>Error Message</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {syncLogs.map((log) => (
                        <TableRow key={log.id}>
                          <TableCell className="font-mono text-sm">
                            {format(new Date(log.timestamp), 'yyyy-MM-dd HH:mm:ss')}
                          </TableCell>
                          <TableCell>
                            <Badge variant={log.status === 'success' ? 'success' : 'error'}>
                              {log.status === 'success' ? (
                                <CheckCircle className="h-3 w-3 mr-1" />
                              ) : (
                                <XCircle className="h-3 w-3 mr-1" />
                              )}
                              {log.status}
                            </Badge>
                          </TableCell>
                          <TableCell>{log.records_synced}</TableCell>
                          <TableCell className="text-muted-foreground">{log.duration_ms}ms</TableCell>
                          <TableCell className="text-sm text-destructive">
                            {log.error_message || '—'}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                )}
              </Card>
            ),
          },
          {
            key: 'test',
            label: 'Test Connection',
            content: (
              <Card className="p-6">
                <h3 className="text-lg font-semibold mb-4">Test Plugin Connection</h3>
                <p className="text-sm text-muted-foreground mb-6">
                  {plugin.type === 'webhook'
                    ? 'Test if the webhook endpoint can receive and validate requests.'
                    : 'Test if the polling endpoint is accessible and returns data.'}
                </p>

                <Button
                  onClick={handleTestConnection}
                  disabled={testConnection.isPending}
                  className="mb-6"
                >
                  {testConnection.isPending ? (
                    <>
                      <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                      Testing...
                    </>
                  ) : (
                    <>
                      <PlayCircle className="h-4 w-4 mr-2" />
                      Run Test
                    </>
                  )}
                </Button>

                {/* Test Results */}
                {testResult && (
                  <Card className={`p-4 ${testResult.success ? 'border-success' : 'border-destructive'}`}>
                    <div className="flex items-start gap-3">
                      {testResult.success ? (
                        <CheckCircle className="h-5 w-5 text-success mt-0.5" />
                      ) : (
                        <XCircle className="h-5 w-5 text-destructive mt-0.5" />
                      )}
                      <div className="flex-1">
                        <h4 className="font-semibold mb-1">
                          {testResult.success ? 'Connection Successful' : 'Connection Failed'}
                        </h4>
                        <p className="text-sm text-muted-foreground mb-3">{testResult.message}</p>

                        {testResult.details && (
                          <dl className="space-y-2">
                            {('status_code' in testResult.details && testResult.details.status_code) ? (
                              <div className="flex gap-2">
                                <dt className="text-sm font-medium text-muted-foreground min-w-[120px]">
                                  Status Code:
                                </dt>
                                <dd className="text-sm">{String(testResult.details.status_code)}</dd>
                              </div>
                            ) : null}
                            {('response_time_ms' in testResult.details && testResult.details.response_time_ms !== undefined) ? (
                              <div className="flex gap-2">
                                <dt className="text-sm font-medium text-muted-foreground min-w-[120px]">
                                  Response Time:
                                </dt>
                                <dd className="text-sm">{String(testResult.details.response_time_ms)}ms</dd>
                              </div>
                            ) : null}
                            {('records_preview' in testResult.details && testResult.details.records_preview) ? (
                              <div>
                                <dt className="text-sm font-medium text-muted-foreground mb-1">
                                  Records Preview:
                                </dt>
                                <dd className="text-sm font-mono bg-muted p-2 rounded max-h-48 overflow-auto">
                                  {JSON.stringify(testResult.details.records_preview, null, 2)}
                                </dd>
                              </div>
                            ) : null}
                          </dl>
                        )}
                      </div>
                    </div>
                  </Card>
                )}
              </Card>
            ),
          },
        ]}
      />
    </div>
  );
}
