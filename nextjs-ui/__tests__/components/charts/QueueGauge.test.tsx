/**
 * QueueGauge Component Tests
 *
 * Tests for the circular gauge displaying queue depth with color-coded thresholds.
 * Following 2025 Testing Library best practices.
 */

import React from 'react'
import { screen } from '@testing-library/react'
import { renderWithProviders } from '../../utils/test-utils'
import { QueueGauge } from '@/components/charts/QueueGauge'

// Mock Recharts
jest.mock('recharts', () => {
  const OriginalModule = jest.requireActual('recharts')
  return {
    ...OriginalModule,
    ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
      <div data-testid="responsive-container">{children}</div>
    ),
  }
})

describe('QueueGauge', () => {
  describe('Color Coding (Percentage-based)', () => {
    it('displays green color for queue depth ≤50% (healthy)', () => {
      // 25/200 = 12.5%
      const { container } = renderWithProviders(<QueueGauge queueDepth={25} />)

      const gaugeValue = screen.getByText('25')
      expect(gaugeValue).toBeInTheDocument()

      // Check for green color styling
      const valueElement = container.querySelector('[style*="color"]')
      expect(valueElement).toHaveStyle({ color: 'hsl(var(--success))' })
    })

    it('displays green color at exactly 50% threshold', () => {
      // 100/200 = 50%
      const { container } = renderWithProviders(<QueueGauge queueDepth={100} />)

      const gaugeValue = screen.getByText('100')
      expect(gaugeValue).toBeInTheDocument()

      const valueElement = container.querySelector('[style*="color"]')
      expect(valueElement).toHaveStyle({ color: 'hsl(var(--success))' })
    })

    it('displays yellow color for queue depth 51-75% (warning)', () => {
      // 130/200 = 65%
      const { container } = renderWithProviders(<QueueGauge queueDepth={130} />)

      const gaugeValue = screen.getByText('130')
      expect(gaugeValue).toBeInTheDocument()

      const valueElement = container.querySelector('[style*="color"]')
      expect(valueElement).toHaveStyle({ color: 'hsl(var(--warning))' })
    })

    it('displays red color for queue depth >75% (critical)', () => {
      // 160/200 = 80%
      const { container } = renderWithProviders(<QueueGauge queueDepth={160} />)

      const gaugeValue = screen.getByText('160')
      expect(gaugeValue).toBeInTheDocument()

      const valueElement = container.querySelector('[style*="color"]')
      expect(valueElement).toHaveStyle({ color: 'hsl(var(--destructive))' })
    })
  })

  describe('Value Display', () => {
    it('displays queue depth value', () => {
      renderWithProviders(<QueueGauge queueDepth={42} />)

      expect(screen.getByText('42')).toBeInTheDocument()
    })

    it('displays "Jobs in Queue" label', () => {
      renderWithProviders(<QueueGauge queueDepth={42} />)

      expect(screen.getByText('Jobs in Queue')).toBeInTheDocument()
    })

    it('handles zero queue depth', () => {
      renderWithProviders(<QueueGauge queueDepth={0} />)

      expect(screen.getByText('0')).toBeInTheDocument()
    })

    it('handles very large queue depth', () => {
      renderWithProviders(<QueueGauge queueDepth={999} />)

      expect(screen.getByText('999')).toBeInTheDocument()
    })
  })

  describe('Max Capacity', () => {
    it('uses default max capacity of 200', () => {
      const { container } = renderWithProviders(<QueueGauge queueDepth={100} />)

      // Should calculate as 50% (100/200)
      // Green color (≤50%)
      expect(screen.getByText('100')).toBeInTheDocument()
      const valueElement = container.querySelector('[style*="color"]')
      expect(valueElement).toHaveStyle({ color: 'hsl(var(--success))' })
    })

    it('uses custom max capacity when provided', () => {
      const { container } = renderWithProviders(
        <QueueGauge queueDepth={150} maxCapacity={300} />
      )

      // Should calculate as 50% (150/300)
      expect(screen.getByText('150')).toBeInTheDocument()
      const valueElement = container.querySelector('[style*="color"]')
      expect(valueElement).toHaveStyle({ color: 'hsl(var(--success))' })
    })

    it('caps percentage at 100% when queue exceeds max capacity', () => {
      const { container } = renderWithProviders(
        <QueueGauge queueDepth={250} maxCapacity={200} />
      )

      // Should display 250 and calculate as 100% (250/200 = 125%, capped at 100%)
      expect(screen.getByText('250')).toBeInTheDocument()

      // At 100%, should be red (>75%)
      const valueElement = container.querySelector('[style*="color"]')
      expect(valueElement).toHaveStyle({ color: 'hsl(var(--destructive))' })
    })
  })

  describe('Accessibility', () => {
    it('renders ResponsiveContainer for fluid sizing', () => {
      renderWithProviders(<QueueGauge queueDepth={42} />)

      expect(screen.getByTestId('responsive-container')).toBeInTheDocument()
    })

    it('displays queue depth value prominently', () => {
      renderWithProviders(<QueueGauge queueDepth={75} />)

      // Value should be large and bold
      const valueElement = screen.getByText('75')
      expect(valueElement).toHaveClass('text-4xl', 'font-bold')
    })

    it('has descriptive label for context', () => {
      renderWithProviders(<QueueGauge queueDepth={42} />)

      expect(screen.getByText('Jobs in Queue')).toHaveClass('text-sm')
    })
  })

  describe('Edge Cases', () => {
    it('handles exact threshold at 75% correctly', () => {
      // 150/200 = 75%
      const { container } = renderWithProviders(<QueueGauge queueDepth={150} />)

      const valueElement = container.querySelector('[style*="color"]')
      // At exactly 75%, should still be yellow (>75% means strictly greater)
      expect(valueElement).toHaveStyle({ color: 'hsl(var(--warning))' })
    })

    it('handles exact threshold at 76% correctly', () => {
      // 152/200 = 76%
      const { container } = renderWithProviders(<QueueGauge queueDepth={152} />)

      const valueElement = container.querySelector('[style*="color"]')
      // At 76%, should be red (>75%)
      expect(valueElement).toHaveStyle({ color: 'hsl(var(--destructive))' })
    })

    it('handles exact threshold at 51% correctly', () => {
      // 102/200 = 51%
      const { container } = renderWithProviders(<QueueGauge queueDepth={102} />)

      const valueElement = container.querySelector('[style*="color"]')
      // At 51%, should be yellow (>50%)
      expect(valueElement).toHaveStyle({ color: 'hsl(var(--warning))' })
    })
  })
})
