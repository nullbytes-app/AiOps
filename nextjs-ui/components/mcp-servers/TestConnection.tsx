/**
 * Test Connection Component
 *
 * Tests MCP server connection and displays discovered tools
 */

'use client';

import React, { useState } from 'react';
import { Button } from '@/components/ui/Button';
import { TestTube, Loader2, CheckCircle, XCircle, AlertCircle } from 'lucide-react';
import { useTestMCPServerConnection } from '@/lib/hooks/useMCPServers';
import type { ToolDiscoveryResponse } from '@/lib/api/mcp-servers';

interface TestConnectionProps {
  serverId: string;
}

export function TestConnection({ serverId }: TestConnectionProps) {
  const [testResult, setTestResult] = useState<ToolDiscoveryResponse | null>(null);
  const testConnection = useTestMCPServerConnection();

  const handleTest = async () => {
    setTestResult(null);
    try {
      const result = await testConnection.mutateAsync({ server_id: serverId });
      setTestResult(result);
    } catch (error) {
      setTestResult({
        success: false,
        tools: [],
        error: error instanceof Error ? error.message : 'Connection test failed',
      });
    }
  };

  return (
    <div className="glass-card p-6 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold text-text-primary">Test Connection</h3>
          <p className="text-sm text-text-secondary mt-1">
            Test the server connection and discover available tools
          </p>
        </div>
        <Button
          onClick={handleTest}
          disabled={testConnection.isPending}
          className="gap-2"
        >
          {testConnection.isPending ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <TestTube className="h-4 w-4" />
          )}
          Run Test
        </Button>
      </div>

      {/* Test Result */}
      {testResult && (
        <div className="mt-4 space-y-4">
          {/* Status Banner */}
          <div
            className={`p-4 rounded-lg border ${
              testResult.success
                ? 'bg-green-50 border-green-200'
                : 'bg-red-50 border-red-200'
            }`}
          >
            <div className="flex items-center gap-3">
              {testResult.success ? (
                <CheckCircle className="h-5 w-5 text-green-600 flex-shrink-0" />
              ) : (
                <XCircle className="h-5 w-5 text-red-600 flex-shrink-0" />
              )}
              <div className="flex-1">
                <h4
                  className={`text-sm font-semibold ${
                    testResult.success ? 'text-green-900' : 'text-red-900'
                  }`}
                >
                  {testResult.success
                    ? 'Connection Successful'
                    : 'Connection Failed'}
                </h4>
                {testResult.error && (
                  <p className="text-sm text-red-800 mt-1">{testResult.error}</p>
                )}
              </div>
            </div>
          </div>

          {/* Discovered Tools */}
          {testResult.success && testResult.tools && testResult.tools.length > 0 && (
            <div>
              <h4 className="text-sm font-semibold text-text-primary mb-3">
                Discovered Tools ({testResult.tools.length})
              </h4>
              <div className="space-y-2">
                {testResult.tools.map((tool, index) => (
                  <div key={index} className="glass-card p-4">
                    <div className="flex items-start gap-3">
                      <div className="flex-shrink-0">
                        <div className="w-8 h-8 rounded-lg bg-accent-blue/10 flex items-center justify-center">
                          <TestTube className="h-4 w-4 text-accent-blue" />
                        </div>
                      </div>
                      <div className="flex-1 min-w-0">
                        <h5 className="text-sm font-semibold text-text-primary">
                          {tool.name}
                        </h5>
                        {tool.description && (
                          <p className="text-sm text-text-secondary mt-1">
                            {tool.description}
                          </p>
                        )}
                        {tool.input_schema && (
                          <details className="mt-2">
                            <summary className="text-xs text-accent-blue cursor-pointer hover:underline">
                              View Input Schema
                            </summary>
                            <pre className="mt-2 p-2 bg-white/50 rounded text-xs overflow-x-auto">
                              {JSON.stringify(tool.input_schema, null, 2)}
                            </pre>
                          </details>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* No Tools Found */}
          {testResult.success && (!testResult.tools || testResult.tools.length === 0) && (
            <div className="glass-card p-6 text-center">
              <AlertCircle className="h-12 w-12 text-yellow-500 mx-auto mb-3" />
              <h4 className="text-sm font-semibold text-text-primary mb-1">
                No Tools Discovered
              </h4>
              <p className="text-sm text-text-secondary">
                The server connected successfully but did not expose any tools.
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
