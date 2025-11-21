/**
 * AgentTable Component Tests
 *
 * Tests for the sortable, searchable, paginated agent performance table.
 * Following 2025 Testing Library best practices.
 */

import React from 'react'
import { screen, within } from '@testing-library/react'
import { renderWithProviders, userEvent } from '../../../utils/test-utils'
import { AgentTable } from '@/components/dashboard/agents/AgentTable'

describe('AgentTable', () => {
  const mockData = [
    {
      agent_name: 'ticket-enhancer',
      total_runs: 850,
      success_rate: 0.96,
      avg_latency_ms: 2340,
      total_cost: 10.23,
    },
    {
      agent_name: 'context-gatherer',
      total_runs: 400,
      success_rate: 0.92,
      avg_latency_ms: 1820,
      total_cost: 5.22,
    },
    {
      agent_name: 'prompt-optimizer',
      total_runs: 150,
      success_rate: 0.98,
      avg_latency_ms: 980,
      total_cost: 2.45,
    },
  ]

  describe('Rendering', () => {
    it('renders table with all columns', () => {
      renderWithProviders(<AgentTable data={mockData} />)

      // Check column headers
      expect(screen.getByText('Agent Name')).toBeInTheDocument()
      expect(screen.getByText('Total Runs')).toBeInTheDocument()
      expect(screen.getByText('Success Rate')).toBeInTheDocument()
      expect(screen.getByText('Avg Latency')).toBeInTheDocument()
      expect(screen.getByText('Total Cost')).toBeInTheDocument()
    })

    it('renders all agent rows', () => {
      renderWithProviders(<AgentTable data={mockData} />)

      expect(screen.getByText('ticket-enhancer')).toBeInTheDocument()
      expect(screen.getByText('context-gatherer')).toBeInTheDocument()
      expect(screen.getByText('prompt-optimizer')).toBeInTheDocument()
    })

    it('formats success rate as percentage with one decimal', () => {
      renderWithProviders(<AgentTable data={mockData} />)

      expect(screen.getByText('96.0%')).toBeInTheDocument()
      expect(screen.getByText('92.0%')).toBeInTheDocument()
      expect(screen.getByText('98.0%')).toBeInTheDocument()
    })

    it('formats cost with 4 decimal places', () => {
      renderWithProviders(<AgentTable data={mockData} />)

      expect(screen.getByText('$10.2300')).toBeInTheDocument()
      expect(screen.getByText('$5.2200')).toBeInTheDocument()
      expect(screen.getByText('$2.4500')).toBeInTheDocument()
    })

    it('formats latency with "ms" suffix', () => {
      renderWithProviders(<AgentTable data={mockData} />)

      // No space between number and "ms"
      expect(screen.getByText('2,340ms')).toBeInTheDocument()
      expect(screen.getByText('1,820ms')).toBeInTheDocument()
      expect(screen.getByText('980ms')).toBeInTheDocument()
    })
  })

  describe('Sorting', () => {
    it('sorts by agent name ascending when header clicked', async () => {
      const user = userEvent.setup()
      renderWithProviders(<AgentTable data={mockData} />)

      const nameHeader = screen.getByText('Agent Name')
      await user.click(nameHeader)

      const rows = screen.getAllByRole('row').slice(1) // Skip header row
      const firstRowName = within(rows[0]).getByText(/context-gatherer/i)
      expect(firstRowName).toBeInTheDocument()
    })

    it('sorts by total runs ascending when header clicked first time', async () => {
      const user = userEvent.setup()
      renderWithProviders(<AgentTable data={mockData} />)

      const runsHeader = screen.getByText('Total Runs')
      await user.click(runsHeader)

      // First click sorts ascending (smallest first)
      const rows = screen.getAllByRole('row').slice(1)
      const firstRowRuns = within(rows[0]).getByText('150')
      expect(firstRowRuns).toBeInTheDocument()
    })

    it('reverses sort order on second click', async () => {
      const user = userEvent.setup()
      renderWithProviders(<AgentTable data={mockData} />)

      const runsHeader = screen.getByText('Total Runs')

      // First click: ascending (smallest first)
      await user.click(runsHeader)
      let rows = screen.getAllByRole('row').slice(1)
      expect(within(rows[0]).getByText('150')).toBeInTheDocument()

      // Second click: descending (largest first)
      await user.click(runsHeader)
      rows = screen.getAllByRole('row').slice(1)
      expect(within(rows[0]).getByText('850')).toBeInTheDocument()
    })
  })

  describe('Search Filter', () => {
    it('displays search input', () => {
      renderWithProviders(<AgentTable data={mockData} />)

      const searchInput = screen.getByPlaceholderText(/search agents/i)
      expect(searchInput).toBeInTheDocument()
    })

    it('filters agents by name when search term entered', async () => {
      const user = userEvent.setup()
      renderWithProviders(<AgentTable data={mockData} />)

      const searchInput = screen.getByPlaceholderText(/search agents/i)
      await user.type(searchInput, 'enhancer')

      // Should only show ticket-enhancer
      expect(screen.getByText('ticket-enhancer')).toBeInTheDocument()
      expect(screen.queryByText('context-gatherer')).not.toBeInTheDocument()
      expect(screen.queryByText('prompt-optimizer')).not.toBeInTheDocument()
    })

    it('shows all agents when search is cleared', async () => {
      const user = userEvent.setup()
      renderWithProviders(<AgentTable data={mockData} />)

      const searchInput = screen.getByPlaceholderText(/search agents/i)
      await user.type(searchInput, 'enhancer')
      await user.clear(searchInput)

      // Should show all agents again
      expect(screen.getByText('ticket-enhancer')).toBeInTheDocument()
      expect(screen.getByText('context-gatherer')).toBeInTheDocument()
      expect(screen.getByText('prompt-optimizer')).toBeInTheDocument()
    })

    it('displays "no results" message when search has no matches', async () => {
      const user = userEvent.setup()
      renderWithProviders(<AgentTable data={mockData} />)

      const searchInput = screen.getByPlaceholderText(/search agents/i)
      await user.type(searchInput, 'nonexistent-agent')

      expect(screen.getByText(/no agents found matching "nonexistent-agent"/i)).toBeInTheDocument()
    })
  })

  describe('Pagination', () => {
    const largeDataset = Array.from({ length: 25 }, (_, i) => ({
      agent_name: `agent-${i + 1}`,
      total_runs: (i + 1) * 100,
      success_rate: 0.9 + i * 0.001,
      avg_latency_ms: 1000 + i * 100,
      total_cost: i + 1,
    }))

    it('displays 10 rows per page by default', () => {
      renderWithProviders(<AgentTable data={largeDataset} />)

      const rows = screen.getAllByRole('row').slice(1) // Exclude header
      expect(rows).toHaveLength(10)
    })

    it('navigates to next page when next button clicked', async () => {
      const user = userEvent.setup()
      renderWithProviders(<AgentTable data={largeDataset} />)

      // First page should show agent-1
      expect(screen.getByText('agent-1')).toBeInTheDocument()

      const nextButton = screen.getByRole('button', { name: /next/i })
      await user.click(nextButton)

      // Second page should show agent-11
      expect(screen.getByText('agent-11')).toBeInTheDocument()
      expect(screen.queryByText('agent-1')).not.toBeInTheDocument()
    })

    it('disables previous button on first page', () => {
      renderWithProviders(<AgentTable data={largeDataset} />)

      const prevButton = screen.getByRole('button', { name: /previous/i })
      expect(prevButton).toBeDisabled()
    })

    it('disables next button on last page', async () => {
      const user = userEvent.setup()
      renderWithProviders(<AgentTable data={largeDataset} />)

      const nextButton = screen.getByRole('button', { name: /next/i })

      // Click next twice to reach page 3 (last page with 25 items)
      await user.click(nextButton)
      await user.click(nextButton)

      expect(nextButton).toBeDisabled()
    })
  })

  describe('Empty State', () => {
    it('displays empty state when no data provided', () => {
      renderWithProviders(<AgentTable data={[]} />)

      expect(screen.getByText(/no agent data available/i)).toBeInTheDocument()
    })

    it('displays search-specific empty message when search has no results', async () => {
      const user = userEvent.setup()
      renderWithProviders(<AgentTable data={mockData} />)

      const searchInput = screen.getByPlaceholderText(/search agents/i)
      await user.type(searchInput, 'nonexistent')

      expect(screen.getByText(/no agents found matching "nonexistent"/i)).toBeInTheDocument()
    })
  })

  describe('Accessibility', () => {
    it('has proper table structure', () => {
      renderWithProviders(<AgentTable data={mockData} />)

      const table = screen.getByRole('table')
      expect(table).toBeInTheDocument()
    })

    it('has sortable column headers with aria-labels', () => {
      renderWithProviders(<AgentTable data={mockData} />)

      expect(screen.getByLabelText(/sort by agent name/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/sort by total runs/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/sort by success rate/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/sort by average latency/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/sort by total cost/i)).toBeInTheDocument()
    })

    it('has search input with aria-label', () => {
      renderWithProviders(<AgentTable data={mockData} />)

      const searchInput = screen.getByLabelText(/search agents by name/i)
      expect(searchInput).toBeInTheDocument()
    })

    it('has pagination buttons with aria-labels', async () => {
      const largeDataset = Array.from({ length: 25 }, (_, i) => ({
        agent_name: `agent-${i + 1}`,
        total_runs: (i + 1) * 100,
        success_rate: 0.9 + i * 0.001,
        avg_latency_ms: 1000 + i * 100,
        total_cost: i + 1,
      }))

      renderWithProviders(<AgentTable data={largeDataset} />)

      expect(screen.getByLabelText(/previous page/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/next page/i)).toBeInTheDocument()
    })
  })
})
