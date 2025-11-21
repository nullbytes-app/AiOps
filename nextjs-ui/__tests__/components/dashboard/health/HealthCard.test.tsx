/**
 * HealthCard Component Tests
 *
 * Tests for the health status card presentational component.
 * Following 2025 Testing Library best practices: test behavior, not implementation.
 */

import React from 'react'
import { screen } from '@testing-library/react'
import { renderWithProviders } from '../../../utils/test-utils'
import { HealthCard } from '@/components/dashboard/health/HealthCard'
import { ComponentHealth } from '@/lib/api/health'

describe('HealthCard', () => {
  const mockHealthyStatus: ComponentHealth = {
    status: 'healthy',
    uptime: 86400,
    response_time_ms: 45,
    details: {
      active_workers: 5,
      total_workers: 10,
    },
  }

  const mockDegradedStatus: ComponentHealth = {
    status: 'degraded',
    uptime: 3600,
    response_time_ms: 450,
  }

  const mockDownStatus: ComponentHealth = {
    status: 'down',
    uptime: 0,
    response_time_ms: 0,
  }

  describe('Rendering', () => {
    it('displays component title', () => {
      renderWithProviders(
        <HealthCard title="API Server" health={mockHealthyStatus} />
      )

      expect(screen.getByText('API Server')).toBeInTheDocument()
    })

    it('displays icon when provided', () => {
      const TestIcon = () => <svg data-testid="test-icon" />

      renderWithProviders(
        <HealthCard
          title="API Server"
          health={mockHealthyStatus}
          icon={<TestIcon />}
        />
      )

      expect(screen.getByTestId('test-icon')).toBeInTheDocument()
    })
  })

  describe('Status Display', () => {
    it('displays healthy status with correct styling', () => {
      renderWithProviders(
        <HealthCard title="API Server" health={mockHealthyStatus} />
      )

      const statusBadge = screen.getByText(/healthy/i)
      expect(statusBadge).toBeInTheDocument()
      expect(statusBadge).toHaveClass('bg-accent-green')
    })

    it('displays degraded status with warning styling', () => {
      renderWithProviders(
        <HealthCard title="API Server" health={mockDegradedStatus} />
      )

      const statusBadge = screen.getByText(/degraded/i)
      expect(statusBadge).toBeInTheDocument()
      expect(statusBadge).toHaveClass('bg-accent-orange')
    })

    it('displays down status with error styling', () => {
      renderWithProviders(
        <HealthCard title="API Server" health={mockDownStatus} />
      )

      const statusBadge = screen.getByText(/down/i)
      expect(statusBadge).toBeInTheDocument()
      expect(statusBadge).toHaveClass('bg-red-600')
    })

    it('capitalizes status text', () => {
      renderWithProviders(
        <HealthCard title="API Server" health={mockHealthyStatus} />
      )

      expect(screen.getByText('Healthy')).toBeInTheDocument()
    })
  })

  describe('Metrics Display', () => {
    it('displays uptime in hours', () => {
      renderWithProviders(
        <HealthCard title="API Server" health={mockHealthyStatus} />
      )

      expect(screen.getByText('Uptime')).toBeInTheDocument()
      expect(screen.getByText('24h')).toBeInTheDocument() // 86400 seconds = 24 hours
    })

    it('displays response time in milliseconds', () => {
      renderWithProviders(
        <HealthCard title="API Server" health={mockHealthyStatus} />
      )

      expect(screen.getByText('Response Time')).toBeInTheDocument()
      expect(screen.getByText('45ms')).toBeInTheDocument()
    })

    it('does not display uptime when undefined', () => {
      const healthWithoutUptime: ComponentHealth = {
        status: 'healthy',
        response_time_ms: 45,
      }

      renderWithProviders(
        <HealthCard title="API Server" health={healthWithoutUptime} />
      )

      expect(screen.queryByText('Uptime')).not.toBeInTheDocument()
    })

    it('does not display response time when undefined', () => {
      const healthWithoutResponseTime: ComponentHealth = {
        status: 'healthy',
        uptime: 86400,
      }

      renderWithProviders(
        <HealthCard title="API Server" health={healthWithoutResponseTime} />
      )

      expect(screen.queryByText('Response Time')).not.toBeInTheDocument()
    })
  })

  describe('Additional Details', () => {
    it('displays details when provided', () => {
      renderWithProviders(
        <HealthCard title="Workers" health={mockHealthyStatus} />
      )

      expect(screen.getByText('Active Workers')).toBeInTheDocument()
      expect(screen.getByText('5')).toBeInTheDocument()
      expect(screen.getByText('Total Workers')).toBeInTheDocument()
      expect(screen.getByText('10')).toBeInTheDocument()
    })

    it('formats detail keys correctly', () => {
      const healthWithDetails: ComponentHealth = {
        status: 'healthy',
        details: {
          cpu_usage_percent: 35.2,
          memory_usage_mb: 512,
        },
      }

      renderWithProviders(
        <HealthCard title="API Server" health={healthWithDetails} />
      )

      // Underscores should be replaced with spaces and capitalized
      expect(screen.getByText('Cpu Usage Percent')).toBeInTheDocument()
      expect(screen.getByText('Memory Usage Mb')).toBeInTheDocument()
    })

    it('does not display details section when details is undefined', () => {
      const healthWithoutDetails: ComponentHealth = {
        status: 'healthy',
        uptime: 86400,
        response_time_ms: 45,
      }

      renderWithProviders(
        <HealthCard title="API Server" health={healthWithoutDetails} />
      )

      // Details section should not be present
      const detailsSection = screen.queryByText(/Active Workers/i)
      expect(detailsSection).not.toBeInTheDocument()
    })
  })

  describe('Last Updated Timestamp', () => {
    it('displays last updated time when provided', () => {
      const timestamp = new Date().toISOString()

      renderWithProviders(
        <HealthCard
          title="API Server"
          health={mockHealthyStatus}
          lastUpdated={timestamp}
        />
      )

      expect(screen.getByText(/Updated/i)).toBeInTheDocument()
      expect(screen.getByText(/ago/i)).toBeInTheDocument()
    })

    it('does not display timestamp when not provided', () => {
      renderWithProviders(
        <HealthCard title="API Server" health={mockHealthyStatus} />
      )

      expect(screen.queryByText(/Updated/i)).not.toBeInTheDocument()
    })
  })

  describe('Accessibility', () => {
    it('status badge has aria-live for screen reader updates', () => {
      renderWithProviders(
        <HealthCard title="API Server" health={mockHealthyStatus} />
      )

      const statusBadge = screen.getByTestId('status-badge')
      expect(statusBadge).toHaveAttribute('aria-live', 'polite')
    })
  })

  describe('Edge Cases', () => {
    it('handles zero uptime correctly', () => {
      renderWithProviders(<HealthCard title="API Server" health={mockDownStatus} />)

      expect(screen.getByText('Uptime')).toBeInTheDocument()
      expect(screen.getByText('0h')).toBeInTheDocument()
    })

    it('handles zero response time correctly', () => {
      renderWithProviders(<HealthCard title="API Server" health={mockDownStatus} />)

      expect(screen.getByText('Response Time')).toBeInTheDocument()
      expect(screen.getByText('0ms')).toBeInTheDocument()
    })

    it('handles large uptime values', () => {
      const healthWithLargeUptime: ComponentHealth = {
        status: 'healthy',
        uptime: 2592000, // 30 days in seconds
        response_time_ms: 45,
      }

      renderWithProviders(
        <HealthCard title="API Server" health={healthWithLargeUptime} />
      )

      expect(screen.getByText('720h')).toBeInTheDocument() // 30 days = 720 hours
    })
  })
})
