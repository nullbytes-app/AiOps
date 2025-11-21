"use client";

import { Component, ReactNode } from "react";
import { AlertTriangle, RefreshCw, Github, Copy } from "lucide-react";
import { toast } from "@/components/ui/Toast";

interface ErrorBoundaryProps {
  children: ReactNode;
  /**
   * Custom fallback UI (optional)
   */
  fallback?: (error: Error, reset: () => void) => ReactNode;
  /**
   * Error callback for logging (e.g., Sentry)
   */
  onError?: (error: Error, errorInfo: React.ErrorInfo) => void;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

/**
 * ErrorBoundary Component
 *
 * Global error boundary that catches unhandled React errors.
 * Displays user-friendly error UI with recovery options.
 *
 * Features:
 * - Catches all unhandled React errors
 * - Displays error icon, message, and stack trace (dev mode only)
 * - Actions: Reload page, Report issue, Copy error
 * - Fallback UI: Minimal layout (no sidebar, just header + error content)
 * - Error logging callback for Sentry integration
 *
 * Recovery Actions:
 * - **Reload page:** Refreshes the entire page
 * - **Report issue:** Opens GitHub issue template with error details
 * - **Copy error:** Copies error message + stack trace to clipboard
 *
 * @example
 * ```tsx
 * // Wrap app or page sections
 * <ErrorBoundary
 *   onError={(error, errorInfo) => {
 *     // Log to Sentry or other service
 *     console.error('Error caught:', error, errorInfo);
 *   }}
 * >
 *   <YourComponent />
 * </ErrorBoundary>
 * ```
 *
 * Reference: Story 6 AC-5 (Error Handling - Global Error Boundary)
 */
export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    // Call onError callback for logging
    if (this.props.onError) {
      this.props.onError(error, errorInfo);
    }

    // Log to console in development
    if (process.env.NODE_ENV === "development") {
      console.error("ErrorBoundary caught:", error, errorInfo);
    }
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null });
  };

  handleReload = () => {
    window.location.reload();
  };

  handleCopyError = () => {
    if (!this.state.error) return;

    const errorText = `Error: ${this.state.error.message}\n\nStack Trace:\n${this.state.error.stack}`;
    navigator.clipboard.writeText(errorText);
    toast.success("Error details copied to clipboard");
  };

  handleReportIssue = () => {
    if (!this.state.error) return;

    const title = encodeURIComponent(`Bug Report: ${this.state.error.message}`);
    const body = encodeURIComponent(
      `**Describe the bug**\nAn error occurred in the application.\n\n**Error Message**\n\`\`\`\n${this.state.error.message}\n\`\`\`\n\n**Stack Trace**\n\`\`\`\n${this.state.error.stack}\n\`\`\`\n\n**Browser**\n${navigator.userAgent}\n\n**Steps to Reproduce**\n1. [Step 1]\n2. [Step 2]\n3. [Step 3]`
    );
    const githubUrl = `https://github.com/YOUR_ORG/YOUR_REPO/issues/new?title=${title}&body=${body}`;
    window.open(githubUrl, "_blank");
  };

  render() {
    if (this.state.hasError && this.state.error) {
      // Use custom fallback if provided
      if (this.props.fallback) {
        return this.props.fallback(this.state.error, this.handleReset);
      }

      // Default error UI
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
              We encountered an unexpected error. Our team has been notified.
            </p>

            {/* Error Details (Dev Mode Only) */}
            {process.env.NODE_ENV === "development" && (
              <div className="mb-6 p-4 bg-gray-100 dark:bg-gray-800 rounded-lg border border-gray-300 dark:border-gray-700">
                <div className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
                  Error Details (Development Only):
                </div>
                <div className="text-xs font-mono text-red-600 dark:text-red-400 whitespace-pre-wrap break-words">
                  {this.state.error.message}
                </div>
                {this.state.error.stack && (
                  <details className="mt-2">
                    <summary className="text-xs text-gray-500 dark:text-gray-400 cursor-pointer hover:text-gray-700 dark:hover:text-gray-300">
                      Stack Trace
                    </summary>
                    <pre className="mt-2 text-xs text-gray-600 dark:text-gray-400 whitespace-pre-wrap break-words">
                      {this.state.error.stack}
                    </pre>
                  </details>
                )}
              </div>
            )}

            {/* Action Buttons */}
            <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
              {/* Reload Page */}
              <button
                onClick={this.handleReload}
                className="flex items-center gap-2 px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition-colors"
              >
                <RefreshCw size={18} />
                Reload Page
              </button>

              {/* Report Issue */}
              <button
                onClick={this.handleReportIssue}
                className="flex items-center gap-2 px-6 py-3 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-900 dark:text-white font-medium rounded-lg border border-gray-300 dark:border-gray-600 transition-colors"
              >
                <Github size={18} />
                Report Issue
              </button>

              {/* Copy Error */}
              <button
                onClick={this.handleCopyError}
                className="flex items-center gap-2 px-6 py-3 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-900 dark:text-white font-medium rounded-lg border border-gray-300 dark:border-gray-600 transition-colors"
              >
                <Copy size={18} />
                Copy Error
              </button>
            </div>

            {/* Help Text */}
            <p className="text-center text-xs text-gray-500 dark:text-gray-400 mt-6">
              If this problem persists, please contact support with the error details.
            </p>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
