"use client";

import { useEffect } from "react";
import { AlertTriangle, RefreshCw, Home } from "lucide-react";

/**
 * Error Component (Next.js App Router Convention)
 *
 * Global error boundary for Next.js App Router.
 * Catches errors in page components and layouts.
 *
 * Features:
 * - Automatic error catching in App Router
 * - User-friendly error UI
 * - Reset functionality (re-renders component)
 * - Navigation back to home
 * - Error logging (dev mode)
 *
 * Note: This file must be placed in /app directory.
 * For nested routes, place error.tsx in the route folder.
 *
 * Reference: Story 6 AC-5 (Error Handling - Global Error Boundary)
 * https://nextjs.org/docs/app/api-reference/file-conventions/error
 */
export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // Log error to console in development
    if (process.env.NODE_ENV === "development") {
      console.error("App Router Error:", error);
    }

    // TODO: Log to error tracking service (Sentry, LogRocket, etc.)
    // logErrorToService(error);
  }, [error]);

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center p-4">
      <div className="max-w-2xl w-full glass-card border-2 border-red-500 dark:border-red-600 rounded-2xl p-8">
        {/* Error Icon */}
        <div className="flex justify-center mb-6">
          <div className="p-4 bg-red-100 dark:bg-red-900/20 rounded-full">
            <AlertTriangle size={48} className="text-red-600 dark:text-red-400" />
          </div>
        </div>

        {/* Error Title */}
        <h1 className="text-2xl font-bold text-center text-gray-900 dark:text-white mb-4">
          Something went wrong
        </h1>

        {/* Error Message */}
        <p className="text-center text-gray-600 dark:text-gray-400 mb-6">
          We encountered an unexpected error. Please try again.
        </p>

        {/* Error Details (Dev Mode Only) */}
        {process.env.NODE_ENV === "development" && (
          <div className="mb-6 p-4 bg-gray-100 dark:bg-gray-800 rounded-lg border border-gray-300 dark:border-gray-700">
            <div className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
              Error Details (Development Only):
            </div>
            <div className="text-xs font-mono text-red-600 dark:text-red-400 whitespace-pre-wrap break-words">
              {error.message}
            </div>
            {error.digest && (
              <div className="mt-2 text-xs text-gray-500 dark:text-gray-400">
                Error Digest: {error.digest}
              </div>
            )}
            {error.stack && (
              <details className="mt-2">
                <summary className="text-xs text-gray-500 dark:text-gray-400 cursor-pointer hover:text-gray-700 dark:hover:text-gray-300">
                  Stack Trace
                </summary>
                <pre className="mt-2 text-xs text-gray-600 dark:text-gray-400 whitespace-pre-wrap break-words max-h-64 overflow-auto">
                  {error.stack}
                </pre>
              </details>
            )}
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
          {/* Try Again (Reset) */}
          <button
            onClick={reset}
            className="flex items-center gap-2 px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition-colors"
          >
            <RefreshCw size={18} />
            Try Again
          </button>

          {/* Go Home */}
          <button
            onClick={() => (window.location.href = "/")}
            className="flex items-center gap-2 px-6 py-3 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-900 dark:text-white font-medium rounded-lg border border-gray-300 dark:border-gray-600 transition-colors"
          >
            <Home size={18} />
            Go Home
          </button>
        </div>

        {/* Help Text */}
        <p className="text-center text-xs text-gray-500 dark:text-gray-400 mt-6">
          If this problem persists, please contact support.
        </p>
      </div>
    </div>
  );
}
