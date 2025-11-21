/**
 * Agent Test Sandbox Component
 *
 * Provides an interface to test agent execution with:
 * - Input message textarea
 * - Execute test button with loading state
 * - JSON response display with syntax highlighting
 * - Execution metadata (duration, tokens, cost)
 * - Error handling
 *
 * Uses @uiw/react-json-view for modern JSON visualization (2025 best practice)
 */

'use client';

import React, { useState } from 'react';
import { Button } from '@/components/ui/Button';
import { Loader2, PlayCircle, AlertCircle, CheckCircle2 } from 'lucide-react';
import JsonView from '@uiw/react-json-view';
import { lightTheme } from '@uiw/react-json-view/light';
import { darkTheme } from '@uiw/react-json-view/dark';
import { useTestAgent } from '@/lib/hooks/useTestAgent';

interface TestSandboxProps {
  agentId: string;
}

/**
 * Test Sandbox Component
 *
 * AC-2 Requirement: Test Sandbox Tab
 * - Input field for test message
 * - Execute button with loading state
 * - JSON output with syntax highlighting
 * - Execution metadata display
 * - Error handling
 */
export function TestSandbox({ agentId }: TestSandboxProps) {
  const [message, setMessage] = useState('');
  const testMutation = useTestAgent();

  const handleExecuteTest = async () => {
    if (!message.trim()) {
      return;
    }

    try {
      await testMutation.mutateAsync({
        agentId,
        data: { message },
      });
    } catch (err) {
      // Error handled by mutation
      console.error('Test execution failed:', err);
    }
  };

  // Determine theme based on system preference (TODO: Use actual theme from context)
  const isDarkMode = false; // Will be replaced with actual theme detection
  const jsonTheme = isDarkMode ? darkTheme : lightTheme;

  const testResult = testMutation.data;
  const error = testMutation.error?.message;
  const isLoading = testMutation.isPending;

  return (
    <div className="space-y-6">
      {/* Test Input Section */}
      <div>
        <label
          htmlFor="test-message"
          className="block text-sm font-medium text-text-primary mb-2"
        >
          Test Message
          <span className="text-text-secondary ml-2">(required)</span>
        </label>
        <textarea
          id="test-message"
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          rows={4}
          placeholder="Enter a message to test this agent..."
          className="w-full px-4 py-3 bg-glass-surface border border-glass-border rounded-lg focus:outline-none focus:ring-2 focus:ring-accent-primary/50 text-text-primary placeholder:text-text-tertiary resize-y"
          aria-label="Test message input"
          disabled={isLoading}
        />
        {message.length > 0 && (
          <div className="mt-1 text-xs text-text-secondary">
            {message.length} characters
          </div>
        )}
      </div>

      {/* Execute Button */}
      <div className="flex gap-3">
        <Button
          onClick={handleExecuteTest}
          disabled={isLoading || !message.trim()}
          className="gap-2"
          size="lg"
        >
          {isLoading ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              Testing agent...
            </>
          ) : (
            <>
              <PlayCircle className="h-4 w-4" />
              Execute Test
            </>
          )}
        </Button>

        {testResult && (
          <Button
            onClick={() => {
              testMutation.reset();
              setMessage('');
            }}
            variant="ghost"
          >
            Clear Results
          </Button>
        )}
      </div>

      {/* Error State */}
      {error && (
        <div
          className="border border-destructive/30 bg-destructive/10 rounded-lg p-4"
          role="alert"
          aria-live="assertive"
        >
          <div className="flex items-start gap-3">
            <AlertCircle className="h-5 w-5 text-destructive flex-shrink-0 mt-0.5" />
            <div>
              <h3 className="font-semibold text-destructive mb-1">Test Failed</h3>
              <p className="text-sm text-destructive/90">{error}</p>
            </div>
          </div>
        </div>
      )}

      {/* Success State with Results */}
      {testResult && !error && (
        <div className="space-y-4">
          {/* Success Banner */}
          <div className="border border-success/30 bg-success/10 rounded-lg p-4">
            <div className="flex items-center gap-2 text-success">
              <CheckCircle2 className="h-5 w-5" />
              <span className="font-semibold">Test Completed Successfully</span>
            </div>
          </div>

          {/* Execution Metadata */}
          <div className="glass-card rounded-lg p-6">
            <h3 className="text-sm font-semibold text-text-primary mb-4 uppercase tracking-wide">
              Execution Metadata
            </h3>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
              <div>
                <div className="text-xs text-text-secondary mb-1">Execution Time</div>
                <div className="text-lg font-semibold text-text-primary">
                  {testResult.execution_time_ms}
                  <span className="text-sm font-normal text-text-secondary ml-1">ms</span>
                </div>
              </div>
              <div>
                <div className="text-xs text-text-secondary mb-1">Status</div>
                <div className="text-sm font-medium text-success">
                  {testResult.message || 'Success'}
                </div>
              </div>
              <div>
                <div className="text-xs text-text-secondary mb-1">Metadata Keys</div>
                <div className="text-sm font-medium text-text-primary">
                  {Object.keys(testResult.metadata || {}).length}
                </div>
              </div>
            </div>
          </div>

          {/* Agent Response with JSON Syntax Highlighting */}
          <div className="glass-card rounded-lg p-6">
            <h3 className="text-sm font-semibold text-text-primary mb-4 uppercase tracking-wide">
              Agent Response
            </h3>
            <div className="bg-background/50 rounded-lg p-4 overflow-auto max-h-[600px]">
              <JsonView
                value={testResult.output as object}
                collapsed={2}
                style={{
                  ...jsonTheme,
                  '--w-rjv-font-family': 'ui-monospace, monospace',
                  '--w-rjv-background-color': 'transparent',
                  '--w-rjv-border-left': '1px solid var(--glass-border)',
                } as React.CSSProperties}
                enableClipboard={true}
                displayDataTypes={false}
              />
            </div>
          </div>
        </div>
      )}

      {/* Empty State */}
      {!testResult && !error && !isLoading && (
        <div className="glass-card rounded-lg p-12 text-center">
          <div className="text-4xl mb-4" role="img" aria-label="Test tube">
            🧪
          </div>
          <h3 className="text-lg font-semibold text-text-primary mb-2">
            Ready to Test
          </h3>
          <p className="text-sm text-text-secondary max-w-md mx-auto">
            Enter a test message above and click &quot;Execute Test&quot; to see how this agent
            responds. The response will be displayed below with execution metrics.
          </p>
        </div>
      )}
    </div>
  );
}
