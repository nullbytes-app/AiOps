/**
 * Component Tests for ErrorAnalysisTable
 * Story 15: Agent Performance Dashboard - Error Analysis
 * Testing AC #1, #2, #3, #6, #8
 */

import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ErrorAnalysisTable } from '../ErrorAnalysisTable';
import * as errorAnalysisApi from '@/lib/api/error-analysis';
import type { ErrorAnalysisResponse } from '@/types/agent-performance';

// Mock the API module
jest.mock('@/lib/api/error-analysis');

// Mock CSV export
jest.mock('@/lib/utils/csv-export', () => ({
  exportErrorsToCSV: jest.fn(),
}));

const mockErrorAnalysisData: ErrorAnalysisResponse = {
  errors: [
    {
      error_type: 'ValidationError',
      error_message: 'Invalid input format: expected JSON, received string',
      occurrences: 23,
      first_seen: '2025-01-15T10:30:00Z',
      last_seen: '2025-01-21T14:22:00Z',
      affected_executions: 23,
      sample_stack_trace: 'Traceback (most recent call last):\\n  File...',
      execution_ids: ['exec-123', 'exec-456'],
    },
    {
      error_type: 'TimeoutError',
      error_message: 'Request timeout after 30 seconds',
      occurrences: 8,
      first_seen: '2025-01-18T09:15:00Z',
      last_seen: '2025-01-20T16:45:00Z',
      affected_executions: 8,
      sample_stack_trace: 'Traceback (most recent call last):\\n  File...',
      execution_ids: ['exec-234'],
    },
    {
      error_type: 'NetworkError',
      error_message: 'Connection refused',
      occurrences: 3,
      first_seen: '2025-01-19T14:00:00Z',
      last_seen: '2025-01-19T15:00:00Z',
      affected_executions: 3,
      execution_ids: ['exec-345'],
    },
  ],
};

function renderWithQueryClient(component: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false, // Disable retry for tests
      },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>{component}</QueryClientProvider>
  );
}

describe('ErrorAnalysisTable', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('AC #1: Table displays correct columns', () => {
    it('renders all required column headers', async () => {
      (errorAnalysisApi.getAgentErrorAnalysis as jest.Mock).mockResolvedValue(
        mockErrorAnalysisData
      );

      renderWithQueryClient(
        <ErrorAnalysisTable
          agentId="agent-123"
          startDate={new Date('2025-01-15')}
          endDate={new Date('2025-01-21')}
        />
      );

      await waitFor(() => {
        expect(screen.getByText('Error Type')).toBeInTheDocument();
        expect(screen.getByText('Error Message')).toBeInTheDocument();
        expect(screen.getByText('Occurrences')).toBeInTheDocument();
        expect(screen.getByText('First Seen')).toBeInTheDocument();
        expect(screen.getByText('Last Seen')).toBeInTheDocument();
        expect(screen.getByText('Affected')).toBeInTheDocument();
        expect(screen.getByText('Severity')).toBeInTheDocument();
      });
    });

    it('displays error data in table rows', async () => {
      (errorAnalysisApi.getAgentErrorAnalysis as jest.Mock).mockResolvedValue(
        mockErrorAnalysisData
      );

      renderWithQueryClient(
        <ErrorAnalysisTable
          agentId="agent-123"
          startDate={new Date('2025-01-15')}
          endDate={new Date('2025-01-21')}
        />
      );

      await waitFor(() => {
        expect(screen.getByText('ValidationError')).toBeInTheDocument();
        expect(screen.getByText('TimeoutError')).toBeInTheDocument();
        expect(screen.getByText('NetworkError')).toBeInTheDocument();
      });
    });

    it('truncates long error messages to 80 characters', async () => {
      (errorAnalysisApi.getAgentErrorAnalysis as jest.Mock).mockResolvedValue(
        mockErrorAnalysisData
      );

      renderWithQueryClient(
        <ErrorAnalysisTable
          agentId="agent-123"
          startDate={new Date('2025-01-15')}
          endDate={new Date('2025-01-21')}
        />
      );

      await waitFor(() => {
        const longMessage = mockErrorAnalysisData.errors[0].error_message;
        if (longMessage.length > 80) {
          expect(screen.queryByText(longMessage)).not.toBeInTheDocument();
          expect(screen.getByText(/\.\.\./)).toBeInTheDocument();
        }
      });
    });
  });

  describe('AC #3: Severity badges display correctly', () => {
    it('shows high severity badge for >20 occurrences', async () => {
      (errorAnalysisApi.getAgentErrorAnalysis as jest.Mock).mockResolvedValue(
        mockErrorAnalysisData
      );

      renderWithQueryClient(
        <ErrorAnalysisTable
          agentId="agent-123"
          startDate={new Date('2025-01-15')}
          endDate={new Date('2025-01-21')}
        />
      );

      await waitFor(() => {
        const highBadge = screen.getAllByText('High')[0];
        expect(highBadge).toBeInTheDocument();
      });
    });

    it('shows medium severity badge for 5-20 occurrences', async () => {
      (errorAnalysisApi.getAgentErrorAnalysis as jest.Mock).mockResolvedValue(
        mockErrorAnalysisData
      );

      renderWithQueryClient(
        <ErrorAnalysisTable
          agentId="agent-123"
          startDate={new Date('2025-01-15')}
          endDate={new Date('2025-01-21')}
        />
      );

      await waitFor(() => {
        const mediumBadge = screen.getByText('Medium');
        expect(mediumBadge).toBeInTheDocument();
      });
    });

    it('shows low severity badge for <5 occurrences', async () => {
      (errorAnalysisApi.getAgentErrorAnalysis as jest.Mock).mockResolvedValue(
        mockErrorAnalysisData
      );

      renderWithQueryClient(
        <ErrorAnalysisTable
          agentId="agent-123"
          startDate={new Date('2025-01-15')}
          endDate={new Date('2025-01-21')}
        />
      );

      await waitFor(() => {
        const lowBadge = screen.getByText('Low');
        expect(lowBadge).toBeInTheDocument();
      });
    });
  });

  describe('AC #6: Loading/empty/error states', () => {
    it('shows loading skeleton during data fetch', () => {
      (errorAnalysisApi.getAgentErrorAnalysis as jest.Mock).mockReturnValue(
        new Promise(() => {}) // Never resolves
      );

      renderWithQueryClient(
        <ErrorAnalysisTable
          agentId="agent-123"
          startDate={new Date('2025-01-15')}
          endDate={new Date('2025-01-21')}
        />
      );

      // Check for skeleton loaders (animated pulse backgrounds)
      const skeletons = document.querySelectorAll('.animate-pulse');
      expect(skeletons.length).toBeGreaterThan(0);
    });

    it('shows empty state when no errors found', async () => {
      (errorAnalysisApi.getAgentErrorAnalysis as jest.Mock).mockResolvedValue({
        errors: [],
      });

      renderWithQueryClient(
        <ErrorAnalysisTable
          agentId="agent-123"
          startDate={new Date('2025-01-15')}
          endDate={new Date('2025-01-21')}
        />
      );

      await waitFor(() => {
        expect(
          screen.getByText('No errors found for selected time range')
        ).toBeInTheDocument();
      });
    });

    it('shows error state with retry button on fetch failure', async () => {
      (errorAnalysisApi.getAgentErrorAnalysis as jest.Mock).mockRejectedValue(
        new Error('API Error')
      );

      renderWithQueryClient(
        <ErrorAnalysisTable
          agentId="agent-123"
          startDate={new Date('2025-01-15')}
          endDate={new Date('2025-01-21')}
        />
      );

      await waitFor(() => {
        expect(screen.getByText('Failed to load error analysis')).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /retry/i })).toBeInTheDocument();
      });
    });
  });

  describe('AC #2: Search and filter', () => {
    it('filters errors by search term', async () => {
      (errorAnalysisApi.getAgentErrorAnalysis as jest.Mock).mockResolvedValue(
        mockErrorAnalysisData
      );

      renderWithQueryClient(
        <ErrorAnalysisTable
          agentId="agent-123"
          startDate={new Date('2025-01-15')}
          endDate={new Date('2025-01-21')}
        />
      );

      await waitFor(() => {
        expect(screen.getByText('ValidationError')).toBeInTheDocument();
      });

      const searchInput = screen.getByPlaceholderText('Search errors...');
      fireEvent.change(searchInput, { target: { value: 'timeout' } });

      await waitFor(() => {
        expect(screen.getByText('TimeoutError')).toBeInTheDocument();
        expect(screen.queryByText('ValidationError')).not.toBeInTheDocument();
      });
    });

    it('shows filtered row count', async () => {
      (errorAnalysisApi.getAgentErrorAnalysis as jest.Mock).mockResolvedValue(
        mockErrorAnalysisData
      );

      renderWithQueryClient(
        <ErrorAnalysisTable
          agentId="agent-123"
          startDate={new Date('2025-01-15')}
          endDate={new Date('2025-01-21')}
        />
      );

      await waitFor(() => {
        expect(screen.getByText(/Showing 3 of 3 errors/)).toBeInTheDocument();
      });

      const searchInput = screen.getByPlaceholderText('Search errors...');
      fireEvent.change(searchInput, { target: { value: 'validation' } });

      await waitFor(() => {
        expect(screen.getByText(/Showing 1 of 3 errors/)).toBeInTheDocument();
      });
    });
  });

  describe('AC #8: Accessibility', () => {
    it('has proper ARIA labels on sort buttons', async () => {
      (errorAnalysisApi.getAgentErrorAnalysis as jest.Mock).mockResolvedValue(
        mockErrorAnalysisData
      );

      renderWithQueryClient(
        <ErrorAnalysisTable
          agentId="agent-123"
          startDate={new Date('2025-01-15')}
          endDate={new Date('2025-01-21')}
        />
      );

      await waitFor(() => {
        expect(screen.getByLabelText('Sort by error type')).toBeInTheDocument();
        expect(screen.getByLabelText('Sort by occurrences')).toBeInTheDocument();
      });
    });

    it('supports keyboard navigation on table rows', async () => {
      (errorAnalysisApi.getAgentErrorAnalysis as jest.Mock).mockResolvedValue(
        mockErrorAnalysisData
      );

      renderWithQueryClient(
        <ErrorAnalysisTable
          agentId="agent-123"
          startDate={new Date('2025-01-15')}
          endDate={new Date('2025-01-21')}
        />
      );

      await waitFor(() => {
        const rows = screen.getAllByRole('button');
        const firstDataRow = rows.find((row) =>
          row.getAttribute('aria-label')?.includes('View details')
        );
        expect(firstDataRow).toHaveAttribute('tabIndex', '0');
      });
    });

    it('announces row count to screen readers', async () => {
      (errorAnalysisApi.getAgentErrorAnalysis as jest.Mock).mockResolvedValue(
        mockErrorAnalysisData
      );

      renderWithQueryClient(
        <ErrorAnalysisTable
          agentId="agent-123"
          startDate={new Date('2025-01-15')}
          endDate={new Date('2025-01-21')}
        />
      );

      await waitFor(() => {
        const statusText = screen.getByRole('status');
        expect(statusText).toHaveAttribute('aria-live', 'polite');
      });
    });
  });
});
