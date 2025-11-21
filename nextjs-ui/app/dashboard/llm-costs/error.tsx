/**
 * Error Boundary for LLM Cost Dashboard
 *
 * Next.js 14 App Router error.tsx boundary
 * Catches React errors and displays fallback UI
 */

'use client';

import React from 'react';
import { Button } from '@/components/ui/Button';
import { AlertCircle, RefreshCw } from 'lucide-react';

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  React.useEffect(() => {
    // Log error to console for debugging
    console.error('LLM Cost Dashboard error:', error);
  }, [error]);

  return (
    <div className="container mx-auto py-8">
      <div className="flex flex-col items-center justify-center py-24">
        <AlertCircle className="h-16 w-16 text-destructive mb-4" />
        <h2 className="text-2xl font-bold text-foreground mb-2">
          Something went wrong
        </h2>
        <p className="text-muted-foreground mb-2 max-w-md text-center">
          An error occurred while loading the LLM Cost Dashboard.
        </p>
        {error.message && (
          <p className="text-xs text-muted-foreground mb-6 font-mono max-w-lg text-center">
            {error.message}
          </p>
        )}
        <Button onClick={reset} className="gap-2">
          <RefreshCw className="h-4 w-4" />
          Try Again
        </Button>
      </div>
    </div>
  );
}
