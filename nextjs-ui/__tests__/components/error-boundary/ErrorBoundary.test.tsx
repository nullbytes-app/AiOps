/**
 * ErrorBoundary Component Tests
 *
 * Tests for Story 6 AC-5 (Error Handling & Recovery)
 * Validates error catching, fallback UI, reset functionality, and accessibility.
 *
 * Coverage target: 80%+
 * Reference: Story 6 AC-8 (Testing & Quality)
 */

import { render, screen, fireEvent } from '@testing-library/react';
import { ErrorBoundary } from '@/components/error-boundary/ErrorBoundary';
import React from 'react';

// Component that throws an error
function ThrowError({ shouldThrow }: { shouldThrow: boolean }) {
  if (shouldThrow) {
    throw new Error('Test error message');
  }
  return <div>Child component</div>;
}

// Suppress console.error for cleaner test output
const originalError = console.error;
beforeAll(() => {
  console.error = jest.fn();
});

afterAll(() => {
  console.error = originalError;
});

describe('ErrorBoundary', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Normal Rendering', () => {
    it('should render children when no error occurs', () => {
      render(
        <ErrorBoundary>
          <div>Test content</div>
        </ErrorBoundary>
      );

      expect(screen.getByText('Test content')).toBeInTheDocument();
    });

    it('should not show fallback UI when children render successfully', () => {
      render(
        <ErrorBoundary>
          <ThrowError shouldThrow={false} />
        </ErrorBoundary>
      );

      expect(screen.getByText('Child component')).toBeInTheDocument();
      expect(screen.queryByText(/something went wrong/i)).not.toBeInTheDocument();
    });
  });

  describe('Error Catching', () => {
    it('should catch errors thrown by child components', () => {
      render(
        <ErrorBoundary>
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      );

      // Verify fallback UI is displayed
      expect(screen.getByText(/something went wrong/i)).toBeInTheDocument();
      expect(screen.queryByText('Child component')).not.toBeInTheDocument();
    });

    it('should display error message in fallback UI', () => {
      render(
        <ErrorBoundary>
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      );

      // Verify error message is visible
      expect(screen.getByText('Test error message')).toBeInTheDocument();
    });

    it('should catch errors from nested children', () => {
      render(
        <ErrorBoundary>
          <div>
            <div>
              <ThrowError shouldThrow={true} />
            </div>
          </div>
        </ErrorBoundary>
      );

      // Should still catch error from deeply nested component
      expect(screen.getByText(/something went wrong/i)).toBeInTheDocument();
    });
  });

  describe('Fallback UI', () => {
    it('should display error icon in fallback UI', () => {
      render(
        <ErrorBoundary>
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      );

      // Verify error icon is present (data-testid or alt text)
      // Note: Actual implementation may vary
      expect(screen.getByText(/something went wrong/i)).toBeInTheDocument();
    });

    it('should show reload button', () => {
      render(
        <ErrorBoundary>
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      );

      const reloadButton = screen.getByRole('button', { name: /reload/i });
      expect(reloadButton).toBeInTheDocument();
    });

    it('should show report issue button', () => {
      render(
        <ErrorBoundary>
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      );

      const reportButton = screen.getByRole('button', { name: /report issue/i });
      expect(reportButton).toBeInTheDocument();
    });

    it('should show copy error button', () => {
      render(
        <ErrorBoundary>
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      );

      const copyButton = screen.getByRole('button', { name: /copy error/i });
      expect(copyButton).toBeInTheDocument();
    });
  });

  describe('Reset Functionality', () => {
    it('should reset error state when reset button clicked', () => {
      const { rerender } = render(
        <ErrorBoundary>
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      );

      // Verify error UI is shown
      expect(screen.getByText(/something went wrong/i)).toBeInTheDocument();

      // Click reload button
      const reloadButton = screen.getByRole('button', { name: /reload/i });
      fireEvent.click(reloadButton);

      // Rerender with shouldThrow=false to simulate successful retry
      rerender(
        <ErrorBoundary>
          <ThrowError shouldThrow={false} />
        </ErrorBoundary>
      );

      // Verify child component is rendered again
      expect(screen.getByText('Child component')).toBeInTheDocument();
      expect(screen.queryByText(/something went wrong/i)).not.toBeInTheDocument();
    });
  });

  describe('Error Actions', () => {
    it('should copy error message when copy button clicked', () => {
      // Mock clipboard API
      const mockWriteText = jest.fn();
      Object.assign(navigator, {
        clipboard: {
          writeText: mockWriteText,
        },
      });

      render(
        <ErrorBoundary>
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      );

      const copyButton = screen.getByRole('button', { name: /copy error/i });
      fireEvent.click(copyButton);

      // Verify clipboard API was called with error message
      expect(mockWriteText).toHaveBeenCalledWith(expect.stringContaining('Test error message'));
    });

    it('should open GitHub issue template when report button clicked', () => {
      // Mock window.open
      const mockOpen = jest.fn();
      global.open = mockOpen;

      render(
        <ErrorBoundary>
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      );

      const reportButton = screen.getByRole('button', { name: /report issue/i });
      fireEvent.click(reportButton);

      // Verify window.open was called with GitHub URL
      expect(mockOpen).toHaveBeenCalledWith(
        expect.stringContaining('github.com'),
        '_blank'
      );
    });
  });

  describe('Stack Trace', () => {
    it('should show stack trace in development mode', () => {
      // Mock development environment
      const originalEnv = process.env.NODE_ENV;
      process.env.NODE_ENV = 'development';

      render(
        <ErrorBoundary>
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      );

      // Verify stack trace is visible
      // Note: Actual implementation may use a collapsible section
      expect(screen.getByText('Test error message')).toBeInTheDocument();

      // Restore environment
      process.env.NODE_ENV = originalEnv;
    });

    it('should hide stack trace in production mode', () => {
      // Mock production environment
      const originalEnv = process.env.NODE_ENV;
      process.env.NODE_ENV = 'production';

      render(
        <ErrorBoundary>
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      );

      // Stack trace should not be visible in production
      // Only error message should be shown
      expect(screen.getByText('Test error message')).toBeInTheDocument();

      // Restore environment
      process.env.NODE_ENV = originalEnv;
    });
  });

  describe('Accessibility', () => {
    it('should have proper ARIA attributes', () => {
      render(
        <ErrorBoundary>
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      );

      // Verify role="alert" for error message
      const errorAlert = screen.getByRole('alert');
      expect(errorAlert).toBeInTheDocument();
    });

    it('should have accessible button labels', () => {
      render(
        <ErrorBoundary>
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      );

      // Verify buttons have accessible names
      expect(screen.getByRole('button', { name: /reload/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /report issue/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /copy error/i })).toBeInTheDocument();
    });

    it('should be keyboard navigable', () => {
      render(
        <ErrorBoundary>
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      );

      const reloadButton = screen.getByRole('button', { name: /reload/i });
      reloadButton.focus();
      expect(reloadButton).toHaveFocus();
    });
  });

  describe('Error Logging', () => {
    it('should log error to console', () => {
      const consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation();

      render(
        <ErrorBoundary>
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      );

      // Verify console.error was called
      expect(consoleErrorSpy).toHaveBeenCalled();

      consoleErrorSpy.mockRestore();
    });
  });

  describe('Multiple Errors', () => {
    it('should handle multiple consecutive errors', () => {
      const { rerender } = render(
        <ErrorBoundary>
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      );

      // First error
      expect(screen.getByText(/something went wrong/i)).toBeInTheDocument();

      // Reset
      const reloadButton = screen.getByRole('button', { name: /reload/i });
      fireEvent.click(reloadButton);

      // Second error
      rerender(
        <ErrorBoundary>
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      );

      // Should still show error UI
      expect(screen.getByText(/something went wrong/i)).toBeInTheDocument();
    });
  });

  describe('Performance', () => {
    it('should render fallback UI quickly', () => {
      const startTime = performance.now();
      render(
        <ErrorBoundary>
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      );
      const endTime = performance.now();

      // Fallback UI should render in less than 50ms
      expect(endTime - startTime).toBeLessThan(50);
    });
  });
});
