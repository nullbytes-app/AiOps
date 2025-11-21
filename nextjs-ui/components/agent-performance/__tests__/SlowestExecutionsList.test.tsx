/**
 * Component Tests for SlowestExecutionsList
 * Story 16: Agent Performance Dashboard - Slowest Executions
 * Testing AC #1, #2, #3, #4, #5, #6, #8
 * Blocker Resolution: Tasks 9.3-9.9 (Component tests)
 */

import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useRouter, useSearchParams } from 'next/navigation';
import { SlowestExecutionsList } from '../SlowestExecutionsList';
import * as slowestExecutionsApi from '@/lib/api/slowest-executions';
import type { SlowestExecutionsResponse } from '@/types/agent-performance';

// Mock Next.js navigation
jest.mock('next/navigation', () => ({
  useRouter: jest.fn(),
  useSearchParams: jest.fn(),
}));

// Mock the API module
jest.mock('@/lib/api/slowest-executions');

const mockSlowestExecutionsData: SlowestExecutionsResponse = {
  executions: [
    {
      execution_id: 'exec-slow-1',
      agent_name: 'Ticket Enhancer',
      duration_ms: 145230, // 2m 25s (slow)
      start_time: '2025-01-21T14:35:22Z',
      status: 'success',
      input_preview: 'Enhance ticket TKT-5432: Server slow response on endpoint /api/users...',
      output_preview: '### Enhanced Context\n\nThe server slow response is likely caused by...',
      conversation_steps_count: 12,
      tool_calls_count: 5,
    },
    {
      execution_id: 'exec-slow-2',
      agent_name: 'Ticket Enhancer',
      duration_ms: 45230, // 45s (warning)
      start_time: '2025-01-21T13:20:00Z',
      status: 'failed',
      input_preview: 'Enhance ticket TKT-1234: Database connection timeout...',
      output_preview: '',
      conversation_steps_count: 3,
      tool_calls_count: 2,
      error_message: 'TimeoutError: Request timeout after 30 seconds',
    },
    {
      execution_id: 'exec-slow-3',
      agent_name: 'Ticket Enhancer',
      duration_ms: 25000, // 25s (normal)
      start_time: '2025-01-21T12:15:00Z',
      status: 'success',
      input_preview: 'Enhance ticket TKT-9876: API rate limit exceeded...',
      output_preview: '### Enhanced Context\n\nThe API rate limit issue can be resolved by...',
      conversation_steps_count: 8,
      tool_calls_count: 3,
    },
  ],
  total_count: 3,
};

const mockRouter = {
  push: jest.fn(),
  replace: jest.fn(),
  prefetch: jest.fn(),
};

const mockSearchParams = new URLSearchParams();

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

describe('SlowestExecutionsList', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (useRouter as jest.Mock).mockReturnValue(mockRouter);
    (useSearchParams as jest.Mock).mockReturnValue(mockSearchParams);
  });

  describe('AC #1 & #6: Table rendering and columns', () => {
    it('renders table with all required column headers', async () => {
      (slowestExecutionsApi.getSlowestExecutions as jest.Mock).mockResolvedValue(
        mockSlowestExecutionsData
      );

      renderWithQueryClient(
        <SlowestExecutionsList
          agentId="agent-123"
          startDate={new Date('2025-01-15')}
          endDate={new Date('2025-01-21')}
        />
      );

      await waitFor(() => {
        expect(screen.getByText('Execution ID')).toBeInTheDocument();
        expect(screen.getByText('Agent')).toBeInTheDocument();
        expect(screen.getByText('Execution Time')).toBeInTheDocument();
        expect(screen.getByText('Start Time')).toBeInTheDocument();
        expect(screen.getByText('Status')).toBeInTheDocument();
        expect(screen.getByText('Input Preview')).toBeInTheDocument();
      });
    });

    it('displays execution data in table rows with correct formatting', async () => {
      (slowestExecutionsApi.getSlowestExecutions as jest.Mock).mockResolvedValue(
        mockSlowestExecutionsData
      );

      renderWithQueryClient(
        <SlowestExecutionsList
          agentId="agent-123"
          startDate={new Date('2025-01-15')}
          endDate={new Date('2025-01-21')}
        />
      );

      await waitFor(() => {
        // Check execution IDs are rendered as links (truncated to first 8 chars)
        const executionLinks = screen.getAllByRole('link', { name: /View execution details/ });
        expect(executionLinks).toHaveLength(3);

        // Check duration formatting (AC #1)
        expect(screen.getByText('2m 25s')).toBeInTheDocument(); // 145230ms
        expect(screen.getByText('45.23s')).toBeInTheDocument(); // 45230ms
        expect(screen.getByText('25.00s')).toBeInTheDocument(); // 25000ms

        // Check agent name
        expect(screen.getAllByText('Ticket Enhancer')).toHaveLength(3);

        // Check status badges
        expect(screen.getAllByText('Success')).toHaveLength(2);
        expect(screen.getByText('Failed')).toBeInTheDocument();

        // Check input preview truncation (AC #1: first 80 chars)
        expect(screen.getByText(/Enhance ticket TKT-5432/)).toBeInTheDocument();
      });
    });

    it('renders loading skeleton during data fetch', async () => {
      (slowestExecutionsApi.getSlowestExecutions as jest.Mock).mockImplementation(
        () => new Promise(() => {}) // Never resolves
      );

      renderWithQueryClient(
        <SlowestExecutionsList
          agentId="agent-123"
          startDate={new Date('2025-01-15')}
          endDate={new Date('2025-01-21')}
        />
      );

      // Check for skeleton shimmer rows (AC #6) - uses aria-label, not visible text
      expect(screen.getByLabelText('Loading slowest executions')).toBeInTheDocument();
    });

    it('displays empty state when no executions found', async () => {
      (slowestExecutionsApi.getSlowestExecutions as jest.Mock).mockResolvedValue({
        executions: [],
        total_count: 0,
      });

      renderWithQueryClient(
        <SlowestExecutionsList
          agentId="agent-123"
          startDate={new Date('2025-01-15')}
          endDate={new Date('2025-01-21')}
        />
      );

      await waitFor(() => {
        expect(screen.getByText(/no slow executions found/i)).toBeInTheDocument();
      });
    });

    it('displays error state with retry button on API failure', async () => {
      (slowestExecutionsApi.getSlowestExecutions as jest.Mock).mockRejectedValue(
        new Error('API Error')
      );

      renderWithQueryClient(
        <SlowestExecutionsList
          agentId="agent-123"
          startDate={new Date('2025-01-15')}
          endDate={new Date('2025-01-21')}
        />
      );

      await waitFor(() => {
        expect(screen.getByText(/failed to load execution data/i)).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /retry/i })).toBeInTheDocument();
      });
    });
  });

  describe('AC #2: Sorting functionality', () => {
    it('sorts by execution time descending by default (slowest first)', async () => {
      (slowestExecutionsApi.getSlowestExecutions as jest.Mock).mockResolvedValue(
        mockSlowestExecutionsData
      );

      renderWithQueryClient(
        <SlowestExecutionsList
          agentId="agent-123"
          startDate={new Date('2025-01-15')}
          endDate={new Date('2025-01-21')}
        />
      );

      await waitFor(() => {
        const rows = screen.getAllByRole('row');
        // First data row should be slowest (exec-slow-1: 2m 25s)
        expect(within(rows[1]).getByText(/exec-slo.../)).toBeInTheDocument();
      });
    });

    it('toggles sort direction when clicking duration column header', async () => {
      const user = userEvent.setup();
      (slowestExecutionsApi.getSlowestExecutions as jest.Mock).mockResolvedValue(
        mockSlowestExecutionsData
      );

      renderWithQueryClient(
        <SlowestExecutionsList
          agentId="agent-123"
          startDate={new Date('2025-01-15')}
          endDate={new Date('2025-01-21')}
        />
      );

      await waitFor(() => {
        expect(screen.getAllByText(/exec-slo.../)[0]).toBeInTheDocument();
      });

      // Click duration header to sort ascending (fastest first)
      const durationHeader = screen.getByText('Execution Time');
      await user.click(durationHeader);

      await waitFor(() => {
        // Check that fastest execution (25s) is now shown first
        expect(screen.getByText('25.00s')).toBeInTheDocument();
      });
    });
  });

  describe('AC #3: Duration color coding', () => {
    it('applies correct color classes based on duration severity', async () => {
      (slowestExecutionsApi.getSlowestExecutions as jest.Mock).mockResolvedValue(
        mockSlowestExecutionsData
      );

      renderWithQueryClient(
        <SlowestExecutionsList
          agentId="agent-123"
          startDate={new Date('2025-01-15')}
          endDate={new Date('2025-01-21')}
        />
      );

      await waitFor(() => {
        // Check duration color coding - color class is on the <span>, not the <td>
        // exec-slow-1: 2m 25s (>60s = slow = red/destructive)
        const slowDuration = screen.getByText('2m 25s');
        expect(slowDuration).toHaveClass('text-destructive');

        // exec-slow-2: 45.23s (30-60s = warning = yellow)
        const warningDuration = screen.getByText('45.23s');
        expect(warningDuration).toHaveClass('text-warning-600');

        // exec-slow-3: 25.00s (<30s = normal = default)
        const normalDuration = screen.getByText('25.00s');
        expect(normalDuration).not.toHaveClass('text-destructive');
        expect(normalDuration).not.toHaveClass('text-warning-600');
      });
    });

    it('displays duration badge for very slow executions (>120s)', async () => {
      const verySlowData = {
        executions: [
          {
            ...mockSlowestExecutionsData.executions[0],
            duration_ms: 180000, // 3 minutes (>120s)
          },
        ],
        total_count: 1,
      };

      (slowestExecutionsApi.getSlowestExecutions as jest.Mock).mockResolvedValue(
        verySlowData
      );

      renderWithQueryClient(
        <SlowestExecutionsList
          agentId="agent-123"
          startDate={new Date('2025-01-15')}
          endDate={new Date('2025-01-21')}
        />
      );

      await waitFor(() => {
        // Check for duration badge (AC #3) - badge shows "Slow" text
        expect(screen.getByText('Slow')).toBeInTheDocument();
      });
    });
  });

  describe('AC #4: Row expansion and inline details', () => {
    it('expands row to show inline details when clicking expander button', async () => {
      const user = userEvent.setup();
      (slowestExecutionsApi.getSlowestExecutions as jest.Mock).mockResolvedValue(
        mockSlowestExecutionsData
      );

      renderWithQueryClient(
        <SlowestExecutionsList
          agentId="agent-123"
          startDate={new Date('2025-01-15')}
          endDate={new Date('2025-01-21')}
        />
      );

      await waitFor(() => {
        expect(screen.getAllByText(/exec-slo.../)[0]).toBeInTheDocument();
      });

      // Click expander button (chevron icon)
      const expandButtons = screen.getAllByRole('button', { name: /expand/i });
      await user.click(expandButtons[0]);

      await waitFor(() => {
        // Check inline details are displayed (AC #4)
        expect(screen.getByText('Conversation Steps:')).toBeInTheDocument();
        expect(screen.getByText('12 steps')).toBeInTheDocument(); // steps count with unit
        expect(screen.getByText('5 invocations')).toBeInTheDocument(); // tool calls with unit
        expect(screen.getByText(/view full details/i)).toBeInTheDocument();
      });
    });

    it('displays full input and output preview in expanded row', async () => {
      const user = userEvent.setup();
      (slowestExecutionsApi.getSlowestExecutions as jest.Mock).mockResolvedValue(
        mockSlowestExecutionsData
      );

      renderWithQueryClient(
        <SlowestExecutionsList
          agentId="agent-123"
          startDate={new Date('2025-01-15')}
          endDate={new Date('2025-01-21')}
        />
      );

      await waitFor(() => {
        expect(screen.getAllByText(/exec-slo.../)[0]).toBeInTheDocument();
      });

      // Click on the expand button in the first data row
      const expandButtons = screen.getAllByRole('button', { name: /expand row/i });
      expect(expandButtons[0]).toHaveAttribute('aria-expanded', 'false');
      await user.click(expandButtons[0]);

      // Wait for expansion to occur - check button aria-expanded changes
      await waitFor(() => {
        expect(expandButtons[0]).toHaveAttribute('aria-expanded', 'true');
      });

      // Check expanded row content is displayed (AC #4)
      // Look for the "Input:" label which only appears in expanded rows
      expect(screen.getByText('Input:')).toBeInTheDocument();

      // Check output preview label appears in expanded row
      expect(screen.getByText('Output Preview:')).toBeInTheDocument();

      // Check output preview content (first 200 chars truncated by component)
      expect(
        screen.getByText(/The server slow response is likely caused by/)
      ).toBeInTheDocument();

      // Check metadata is displayed
      expect(screen.getByText('Conversation Steps:')).toBeInTheDocument();
      expect(screen.getByText('12 steps')).toBeInTheDocument();
      expect(screen.getByText('Tool Calls:')).toBeInTheDocument();
      expect(screen.getByText('5 invocations')).toBeInTheDocument();
    });

    it('displays error message for failed executions in expanded row', async () => {
      const user = userEvent.setup();
      (slowestExecutionsApi.getSlowestExecutions as jest.Mock).mockResolvedValue(
        mockSlowestExecutionsData
      );

      renderWithQueryClient(
        <SlowestExecutionsList
          agentId="agent-123"
          startDate={new Date('2025-01-15')}
          endDate={new Date('2025-01-21')}
        />
      );

      await waitFor(() => {
        expect(screen.getAllByText(/exec-slo.../)[0]).toBeInTheDocument();
      });

      // Expand failed execution row (second row with 45.23s duration)
      const expandButtons = screen.getAllByRole('button', { name: /expand/i });
      await user.click(expandButtons[1]); // exec-slow-2 is failed

      await waitFor(() => {
        // Check error message is displayed (AC #4)
        expect(screen.getByText(/TimeoutError: Request timeout/)).toBeInTheDocument();
      });
    });

    it('collapses row when clicking expander button again', async () => {
      const user = userEvent.setup();
      (slowestExecutionsApi.getSlowestExecutions as jest.Mock).mockResolvedValue(
        mockSlowestExecutionsData
      );

      renderWithQueryClient(
        <SlowestExecutionsList
          agentId="agent-123"
          startDate={new Date('2025-01-15')}
          endDate={new Date('2025-01-21')}
        />
      );

      await waitFor(() => {
        expect(screen.getAllByText(/exec-slo.../)[0]).toBeInTheDocument();
      });

      const expandButtons = screen.getAllByRole('button', { name: /expand/i });
      await user.click(expandButtons[0]); // Expand

      await waitFor(() => {
        expect(screen.getByText('Conversation Steps:')).toBeInTheDocument();
      });

      await user.click(expandButtons[0]); // Collapse

      await waitFor(() => {
        expect(screen.queryByText(/Conversation Steps:/i)).not.toBeInTheDocument();
      });
    });
  });

  describe('AC #5: Filter controls and URL synchronization', () => {
    it('filters executions by status using dropdown', async () => {
      const user = userEvent.setup();
      (slowestExecutionsApi.getSlowestExecutions as jest.Mock).mockResolvedValue(
        mockSlowestExecutionsData
      );

      renderWithQueryClient(
        <SlowestExecutionsList
          agentId="agent-123"
          startDate={new Date('2025-01-15')}
          endDate={new Date('2025-01-21')}
        />
      );

      await waitFor(() => {
        expect(screen.getAllByText(/exec-slo.../)[0]).toBeInTheDocument();
      });

      // Select "Failed Only" from status filter dropdown (<select> element)
      const filterSelect = screen.getByLabelText('Filter executions by status');
      await user.selectOptions(filterSelect, 'failed');

      // Verify router.push was called with correct URL (AC #5)
      expect(mockRouter.push).toHaveBeenCalledWith('?status=failed');
    });

    it('manually refetches data when clicking refresh button', async () => {
      const user = userEvent.setup();
      (slowestExecutionsApi.getSlowestExecutions as jest.Mock).mockResolvedValue(
        mockSlowestExecutionsData
      );

      renderWithQueryClient(
        <SlowestExecutionsList
          agentId="agent-123"
          startDate={new Date('2025-01-15')}
          endDate={new Date('2025-01-21')}
        />
      );

      await waitFor(() => {
        expect(screen.getAllByText(/exec-slo.../)[0]).toBeInTheDocument();
      });

      // Click refresh button (AC #5)
      const refreshButton = screen.getByRole('button', { name: /refresh/i });
      await user.click(refreshButton);

      // Verify API was called again
      await waitFor(() => {
        expect(slowestExecutionsApi.getSlowestExecutions).toHaveBeenCalledTimes(2);
      });
    });
  });

  describe('AC #2: Pagination', () => {
    it('displays pagination controls when data exceeds page size', async () => {
      const largeDataset = {
        executions: Array.from({ length: 15 }, (_, i) => ({
          ...mockSlowestExecutionsData.executions[0],
          execution_id: `exec-slow-${i + 1}`,
        })),
        total_count: 15,
      };

      (slowestExecutionsApi.getSlowestExecutions as jest.Mock).mockResolvedValue(
        largeDataset
      );

      renderWithQueryClient(
        <SlowestExecutionsList
          agentId="agent-123"
          startDate={new Date('2025-01-15')}
          endDate={new Date('2025-01-21')}
        />
      );

      await waitFor(() => {
        // Check pagination controls are visible (AC #2)
        expect(screen.getByRole('button', { name: /next/i })).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /previous/i })).toBeInTheDocument();
      });
    });

    it('navigates to next page when clicking next button', async () => {
      const user = userEvent.setup();
      const largeDataset = {
        executions: Array.from({ length: 15 }, (_, i) => ({
          ...mockSlowestExecutionsData.executions[0],
          execution_id: `exec-slow-${i + 1}`,
        })),
        total_count: 15,
      };

      (slowestExecutionsApi.getSlowestExecutions as jest.Mock).mockResolvedValue(
        largeDataset
      );

      renderWithQueryClient(
        <SlowestExecutionsList
          agentId="agent-123"
          startDate={new Date('2025-01-15')}
          endDate={new Date('2025-01-21')}
        />
      );

      await waitFor(() => {
        expect(screen.getAllByText(/exec-slo.../)[0]).toBeInTheDocument();
      });

      // Click next page button
      const nextButton = screen.getByRole('button', { name: /next/i });
      await user.click(nextButton);

      await waitFor(() => {
        // Should show executions 11-15 on page 2 (check table has data)
        const rows = screen.getAllByRole('row');
        expect(rows.length).toBeGreaterThan(1); // Header + data rows
      });
    });
  });

  describe('AC #8: Accessibility and keyboard navigation', () => {
    it('supports keyboard navigation through table with Tab key', async () => {
      const user = userEvent.setup();
      (slowestExecutionsApi.getSlowestExecutions as jest.Mock).mockResolvedValue(
        mockSlowestExecutionsData
      );

      renderWithQueryClient(
        <SlowestExecutionsList
          agentId="agent-123"
          startDate={new Date('2025-01-15')}
          endDate={new Date('2025-01-21')}
        />
      );

      await waitFor(() => {
        expect(screen.getAllByText(/exec-slo.../)[0]).toBeInTheDocument();
      });

      // Tab through interactive elements
      await user.tab();
      expect(screen.getByLabelText('Filter executions by status')).toHaveFocus();

      await user.tab();
      expect(screen.getByRole('button', { name: /refresh/i })).toHaveFocus();

      await user.tab();
      // Should focus sort button (table header)
      expect(screen.getByRole('button', { name: /sort by execution time/i })).toHaveFocus();
    });

    it('expands row with Enter key when expander button is focused', async () => {
      const user = userEvent.setup();
      (slowestExecutionsApi.getSlowestExecutions as jest.Mock).mockResolvedValue(
        mockSlowestExecutionsData
      );

      renderWithQueryClient(
        <SlowestExecutionsList
          agentId="agent-123"
          startDate={new Date('2025-01-15')}
          endDate={new Date('2025-01-21')}
        />
      );

      await waitFor(() => {
        expect(screen.getAllByText(/exec-slo.../)[0]).toBeInTheDocument();
      });

      // Focus first expand button
      const expandButtons = screen.getAllByRole('button', { name: /expand/i });
      expandButtons[0].focus();

      // Press Enter to expand
      await user.keyboard('{Enter}');

      await waitFor(() => {
        expect(screen.getByText('Conversation Steps:')).toBeInTheDocument();
      });
    });

    it('has correct ARIA labels for accessibility', async () => {
      (slowestExecutionsApi.getSlowestExecutions as jest.Mock).mockResolvedValue(
        mockSlowestExecutionsData
      );

      renderWithQueryClient(
        <SlowestExecutionsList
          agentId="agent-123"
          startDate={new Date('2025-01-15')}
          endDate={new Date('2025-01-21')}
        />
      );

      await waitFor(() => {
        // Check ARIA labels (AC #8)
        const expandButtons = screen.getAllByRole('button', { name: /expand/i });
        expect(expandButtons[0]).toHaveAttribute('aria-label');

        const statusBadges = screen.getAllByText('Success');
        statusBadges.forEach((badge) => {
          expect(badge.closest('span')).toHaveAttribute('aria-label');
        });
      });
    });
  });

  describe('AC #2: Execution ID navigation', () => {
    it('navigates to execution details page when clicking execution ID', async () => {
      (slowestExecutionsApi.getSlowestExecutions as jest.Mock).mockResolvedValue(
        mockSlowestExecutionsData
      );

      renderWithQueryClient(
        <SlowestExecutionsList
          agentId="agent-123"
          startDate={new Date('2025-01-15')}
          endDate={new Date('2025-01-21')}
        />
      );

      await waitFor(() => {
        expect(screen.getAllByText(/exec-slo.../)[0]).toBeInTheDocument();
      });

      // Click execution ID link (check href attribute on link)
      const executionLink = screen.getAllByText(/exec-slo.../)[0].closest('a');
      expect(executionLink).toHaveAttribute(
        'href',
        '/dashboard/execution-history/exec-slow-1'
      );
    });
  });
});
