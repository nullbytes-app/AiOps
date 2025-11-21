/**
 * Test Connection Component
 *
 * Tests LLM provider connection and displays results:
 * - Response time
 * - Models found
 * - Success/failure status
 */

'use client';

import React from 'react';
import { Button } from '@/components/ui/Button';
import { CheckCircle2, XCircle, Loader2, Zap } from 'lucide-react';

interface TestConnectionResult {
  success: boolean;
  response_time_ms: number;
  models_found: number;
  models?: string[];
  error?: string;
}

interface TestConnectionProps {
  onTest: () => Promise<TestConnectionResult>;
  isLoading?: boolean;
  result?: TestConnectionResult | null;
}

/**
 * Test Connection Component
 *
 * AC-3 Requirement: Test connection functionality with response display
 */
export function TestConnection({ onTest, isLoading, result }: TestConnectionProps) {
  const [isExpanded, setIsExpanded] = React.useState(false);

  return (
    <div className="space-y-4">
      {/* Test Button */}
      <Button
        onClick={onTest}
        disabled={isLoading}
        variant="secondary"
        className="gap-2"
      >
        {isLoading ? (
          <>
            <Loader2 className="w-4 h-4 animate-spin" />
            Testing connection...
          </>
        ) : (
          <>
            <Zap className="w-4 h-4" />
            Test Connection
          </>
        )}
      </Button>

      {/* Test Result */}
      {result && (
        <div
          className={`border rounded-lg p-4 ${
            result.success
              ? 'border-success/30 bg-success/10'
              : 'border-destructive/30 bg-destructive/10'
          }`}
        >
          <div className="flex items-start gap-3">
            {result.success ? (
              <CheckCircle2 className="w-5 h-5 text-success flex-shrink-0 mt-0.5" />
            ) : (
              <XCircle className="w-5 h-5 text-destructive flex-shrink-0 mt-0.5" />
            )}
            <div className="flex-1">
              <h4 className={`font-semibold mb-2 ${result.success ? 'text-success' : 'text-destructive'}`}>
                {result.success ? 'Connection Successful' : 'Connection Failed'}
              </h4>

              {result.success ? (
                <div className="space-y-2">
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <span className="text-text-secondary">Response Time:</span>
                      <span className="ml-2 font-medium text-text-primary">
                        {result.response_time_ms}ms
                      </span>
                    </div>
                    <div>
                      <span className="text-text-secondary">Models Found:</span>
                      <span className="ml-2 font-medium text-text-primary">
                        {result.models_found}
                      </span>
                    </div>
                  </div>

                  {result.models && result.models.length > 0 && (
                    <div>
                      <button
                        onClick={() => setIsExpanded(!isExpanded)}
                        className="text-sm text-accent-primary hover:underline"
                      >
                        {isExpanded ? 'Hide' : 'Show'} model list
                      </button>
                      {isExpanded && (
                        <div className="mt-2 p-3 bg-background/50 rounded border border-glass-border">
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-1">
                            {result.models.slice(0, 10).map((model) => (
                              <div
                                key={model}
                                className="text-xs font-mono text-text-secondary"
                              >
                                • {model}
                              </div>
                            ))}
                          </div>
                          {result.models.length > 10 && (
                            <div className="text-xs text-text-tertiary mt-2">
                              ...and {result.models.length - 10} more
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ) : (
                <p className="text-sm text-destructive/90">
                  {result.error || 'Unable to connect to provider'}
                </p>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
