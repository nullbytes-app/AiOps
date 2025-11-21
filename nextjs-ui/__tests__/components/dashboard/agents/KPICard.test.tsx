/**
 * KPICard Component Tests
 *
 * Tests for the Key Performance Indicator card displaying metrics with trends.
 * Following 2025 Testing Library best practices.
 */

import React from 'react'
import { screen } from '@testing-library/react'
import { renderWithProviders } from '../../../utils/test-utils'
import { KPICard } from '@/components/dashboard/agents/KPICard'

describe('KPICard', () => {
  describe('Value Display', () => {
    it('displays metric title and value', () => {
      renderWithProviders(
        <KPICard title="Total Executions" value={1250} format="number" />
      )

      expect(screen.getByText('Total Executions')).toBeInTheDocument()
      expect(screen.getByText('1,250')).toBeInTheDocument()
    })

    it('displays percentage values with decimals when specified', () => {
      renderWithProviders(
        <KPICard title="Success Rate" value={94.4} format="percentage" decimals={1} />
      )

      expect(screen.getByText('94.4%')).toBeInTheDocument()
    })

    it('displays percentage values without decimals by default', () => {
      renderWithProviders(
        <KPICard title="Success Rate" value={94.4} format="percentage" />
      )

      expect(screen.getByText('94%')).toBeInTheDocument()
    })

    it('displays currency values with decimals when specified', () => {
      renderWithProviders(
        <KPICard title="Avg Cost" value={0.0124} format="currency" decimals={4} />
      )

      expect(screen.getByText('$0.0124')).toBeInTheDocument()
    })

    it('displays currency values without decimals by default', () => {
      renderWithProviders(
        <KPICard title="Avg Cost" value={0.0124} format="currency" />
      )

      expect(screen.getByText('$0')).toBeInTheDocument()
    })

    it('displays large numbers with locale-specific formatting', () => {
      renderWithProviders(
        <KPICard title="Total Runs" value={1234567} format="number" />
      )

      // toLocaleString() formats based on system locale
      const formattedValue = (1234567).toLocaleString()
      expect(screen.getByText(formattedValue)).toBeInTheDocument()
    })
  })

  describe('Trend Indicator', () => {
    it('displays positive trend with green arrow up', () => {
      renderWithProviders(
        <KPICard
          title="Executions"
          value={1250}
          format="number"
          changePercent={12.5}
        />
      )

      expect(screen.getByText('+12.5%')).toBeInTheDocument()
      expect(screen.getByLabelText(/increased by 12.5%/i)).toBeInTheDocument()

      // Check for TrendingUp icon (lucide-react renders as SVG)
      const trendElement = screen.getByLabelText(/increased by 12.5%/i)
      expect(trendElement).toHaveClass('text-success')
    })

    it('displays negative trend with red arrow down', () => {
      renderWithProviders(
        <KPICard
          title="Success Rate"
          value={88.5}
          format="percentage"
          changePercent={-5.2}
        />
      )

      expect(screen.getByText('-5.2%')).toBeInTheDocument()
      expect(screen.getByLabelText(/decreased by 5.2%/i)).toBeInTheDocument()

      const trendElement = screen.getByLabelText(/decreased by 5.2%/i)
      expect(trendElement).toHaveClass('text-destructive')
    })

    it('displays neutral trend with no change', () => {
      renderWithProviders(
        <KPICard
          title="Avg Latency"
          value={2340}
          format="number"
          changePercent={0}
        />
      )

      expect(screen.getByText('0.0%')).toBeInTheDocument()
      expect(screen.getByLabelText(/no change/i)).toBeInTheDocument()

      const trendElement = screen.getByLabelText(/no change/i)
      expect(trendElement).toHaveClass('text-muted-foreground')
    })

    it('does not display trend when changePercent not provided', () => {
      renderWithProviders(
        <KPICard title="Total Cost" value={15.45} format="currency" decimals={2} />
      )

      expect(screen.queryByText(/\+/)).not.toBeInTheDocument()
      expect(screen.queryByText(/%$/)).not.toBeInTheDocument()
    })

    it('displays supporting info when trend is present', () => {
      renderWithProviders(
        <KPICard
          title="Total Executions"
          value={1250}
          format="number"
          changePercent={12.5}
        />
      )

      expect(screen.getByText(/vs\. previous 24h/i)).toBeInTheDocument()
    })

    it('displays "period" for percentage format', () => {
      renderWithProviders(
        <KPICard
          title="Success Rate"
          value={94.4}
          format="percentage"
          decimals={1}
          changePercent={2.1}
        />
      )

      expect(screen.getByText(/vs\. previous period/i)).toBeInTheDocument()
    })
  })

  describe('Loading State', () => {
    it('displays loading placeholder when loading is true', () => {
      renderWithProviders(
        <KPICard
          title="Total Executions"
          value={1250}
          format="number"
          loading={true}
        />
      )

      expect(screen.getByText('--')).toBeInTheDocument()
      expect(screen.queryByText('1,250')).not.toBeInTheDocument()
    })

    it('hides trend indicator when loading', () => {
      renderWithProviders(
        <KPICard
          title="Total Executions"
          value={1250}
          format="number"
          changePercent={12.5}
          loading={true}
        />
      )

      expect(screen.queryByText('+12.5%')).not.toBeInTheDocument()
    })
  })

  describe('Accessibility', () => {
    it('has aria-label with formatted value', () => {
      renderWithProviders(
        <KPICard title="Total Executions" value={1250} format="number" />
      )

      expect(screen.getByLabelText(/total executions: 1,250/i)).toBeInTheDocument()
    })

    it('includes trend information in aria-label', () => {
      renderWithProviders(
        <KPICard
          title="Success Rate"
          value={94.4}
          format="percentage"
          decimals={1}
          changePercent={2.1}
        />
      )

      expect(screen.getByLabelText(/increased by 2.1%/i)).toBeInTheDocument()
    })
  })

  describe('Edge Cases', () => {
    it('handles zero value correctly', () => {
      renderWithProviders(
        <KPICard title="Failures" value={0} format="number" />
      )

      expect(screen.getByText('0')).toBeInTheDocument()
    })

    it('handles very small currency values with decimals', () => {
      renderWithProviders(
        <KPICard title="Cost per Run" value={0.0001} format="currency" decimals={4} />
      )

      expect(screen.getByText('$0.0001')).toBeInTheDocument()
    })

    it('handles very large numbers', () => {
      renderWithProviders(
        <KPICard title="Total Runs" value={999999999} format="number" />
      )

      const formattedValue = (999999999).toLocaleString()
      expect(screen.getByText(formattedValue)).toBeInTheDocument()
    })

    it('handles string values', () => {
      renderWithProviders(
        <KPICard title="Status" value="Healthy" format="number" />
      )

      expect(screen.getByText('Healthy')).toBeInTheDocument()
    })

    it('handles undefined changePercent', () => {
      renderWithProviders(
        <KPICard
          title="Total Executions"
          value={1250}
          format="number"
          changePercent={undefined}
        />
      )

      expect(screen.queryByLabelText(/increased/i)).not.toBeInTheDocument()
      expect(screen.queryByLabelText(/decreased/i)).not.toBeInTheDocument()
    })
  })
})
