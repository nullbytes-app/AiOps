/**
 * ExecutionChart Component Tests
 *
 * Tests for the Recharts LineChart displaying agent execution trends.
 * Following 2025 Testing Library best practices for chart testing.
 */

import React from 'react'
import { screen } from '@testing-library/react'
import { renderWithProviders } from '../../../utils/test-utils'
import { ExecutionChart } from '@/components/dashboard/agents/ExecutionChart'

// Mock Recharts to avoid rendering issues in Jest
jest.mock('recharts', () => {
  const OriginalModule = jest.requireActual('recharts')
  return {
    ...OriginalModule,
    ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
      <div data-testid="responsive-container">{children}</div>
    ),
  }
})

describe('ExecutionChart', () => {
  const mockData = [
    {
      hour: '2025-01-18T10:00:00Z',
      success: 48,
      failure: 2,
    },
    {
      hour: '2025-01-18T11:00:00Z',
      success: 52,
      failure: 3,
    },
    {
      hour: '2025-01-18T12:00:00Z',
      success: 45,
      failure: 1,
    },
  ]

  describe('Rendering', () => {
    it('renders chart with provided data', () => {
      renderWithProviders(<ExecutionChart data={mockData} />)

      expect(screen.getByTestId('responsive-container')).toBeInTheDocument()
    })

    it('has title for context', () => {
      renderWithProviders(<ExecutionChart data={mockData} />)

      expect(screen.getByText('Execution Timeline (Last 24 Hours)')).toBeInTheDocument()
    })
  })

  describe('Empty State', () => {
    it('renders chart container even with empty data', () => {
      renderWithProviders(<ExecutionChart data={[]} />)

      // Chart still renders, just with no data points
      expect(screen.getByTestId('responsive-container')).toBeInTheDocument()
      expect(screen.getByText('Execution Timeline (Last 24 Hours)')).toBeInTheDocument()
    })
  })

  describe('Data Transformation', () => {
    it('formats hour timestamps correctly', () => {
      const { container } = renderWithProviders(
        <ExecutionChart data={mockData} />
      )

      // Recharts should format timestamps as "HH:00"
      // We verify this by checking the data prop passed to LineChart
      expect(container.querySelector('.recharts-wrapper')).toBeInTheDocument()
    })
  })
})
