/**
 * MobileBottomNav Component Tests
 *
 * Tests for the mobile bottom navigation component.
 */

import React from 'react'
import { render, screen } from '@testing-library/react'
import { MobileBottomNav } from '@/components/dashboard/MobileBottomNav'
import { usePathname } from 'next/navigation'

jest.mock('next/navigation')

describe('MobileBottomNav', () => {
  const mockUsePathname = usePathname as jest.MockedFunction<typeof usePathname>

  beforeEach(() => {
    mockUsePathname.mockReturnValue('/dashboard')
  })

  it('renders mobile navigation bar', () => {
    render(<MobileBottomNav />)
    const nav = screen.getByRole('navigation', { name: /mobile navigation/i })
    expect(nav).toBeInTheDocument()
  })

  it('has fixed bottom positioning', () => {
    render(<MobileBottomNav />)
    const nav = screen.getByRole('navigation')
    expect(nav).toHaveClass('fixed')
    expect(nav).toHaveClass('bottom-0')
  })

  it('is only visible on mobile (hidden on md+)', () => {
    render(<MobileBottomNav />)
    const nav = screen.getByRole('navigation')
    expect(nav).toHaveClass('md:hidden')
  })

  it('has glassmorphic styling', () => {
    render(<MobileBottomNav />)
    const nav = screen.getByRole('navigation')
    expect(nav).toHaveClass('glass-card')
  })

  it('renders all 5 navigation items', () => {
    render(<MobileBottomNav />)

    expect(screen.getByText('Dashboard')).toBeInTheDocument()
    expect(screen.getByText('Agents')).toBeInTheDocument()
    expect(screen.getByText('Executions')).toBeInTheDocument()
    expect(screen.getByText('Workflows')).toBeInTheDocument()
    expect(screen.getByText('Settings')).toBeInTheDocument()
  })

  it('renders all navigation links with correct hrefs', () => {
    render(<MobileBottomNav />)

    const dashboardLink = screen.getByRole('link', { name: /dashboard/i })
    const agentsLink = screen.getByRole('link', { name: /agents/i })
    const executionsLink = screen.getByRole('link', { name: /executions/i })
    const workflowsLink = screen.getByRole('link', { name: /workflows/i })
    const settingsLink = screen.getByRole('link', { name: /settings/i })

    expect(dashboardLink).toHaveAttribute('href', '/dashboard')
    expect(agentsLink).toHaveAttribute('href', '/dashboard/agents')
    expect(executionsLink).toHaveAttribute('href', '/dashboard/executions')
    expect(workflowsLink).toHaveAttribute('href', '/dashboard/workflows')
    expect(settingsLink).toHaveAttribute('href', '/dashboard/settings')
  })

  it('highlights active page (Dashboard)', () => {
    mockUsePathname.mockReturnValue('/dashboard')
    render(<MobileBottomNav />)

    const dashboardLink = screen.getByRole('link', { name: /dashboard/i })
    expect(dashboardLink).toHaveClass('bg-accent-blue')
    expect(dashboardLink).toHaveAttribute('aria-current', 'page')
  })

  it('highlights active page (Agents)', () => {
    mockUsePathname.mockReturnValue('/dashboard/agents')
    render(<MobileBottomNav />)

    const agentsLink = screen.getByRole('link', { name: /agents/i })
    expect(agentsLink).toHaveClass('bg-accent-blue')
    expect(agentsLink).toHaveAttribute('aria-current', 'page')
  })

  it('does not highlight inactive pages', () => {
    mockUsePathname.mockReturnValue('/dashboard')
    render(<MobileBottomNav />)

    const agentsLink = screen.getByRole('link', { name: /agents/i })
    expect(agentsLink).not.toHaveClass('bg-accent-blue')
    expect(agentsLink).not.toHaveAttribute('aria-current')
  })

  it('has large touch targets (min 48px)', () => {
    render(<MobileBottomNav />)

    const dashboardLink = screen.getByRole('link', { name: /dashboard/i })
    expect(dashboardLink).toHaveClass('min-h-[48px]')
  })

  it('has proper spacing between items', () => {
    const { container } = render(<MobileBottomNav />)

    const list = container.querySelector('ul')
    expect(list).toHaveClass('justify-around')
  })

  it('renders icons for all navigation items', () => {
    render(<MobileBottomNav />)

    // Each link should have an SVG icon (lucide-react renders SVG)
    const links = screen.getAllByRole('link')
    links.forEach((link) => {
      const svg = link.querySelector('svg')
      expect(svg).toBeInTheDocument()
    })
  })

  it('has transition effects on links', () => {
    render(<MobileBottomNav />)

    const dashboardLink = screen.getByRole('link', { name: /dashboard/i })
    expect(dashboardLink).toHaveClass('transition-all')
    expect(dashboardLink).toHaveClass('duration-200')
  })

  it('has hover effects on inactive links', () => {
    mockUsePathname.mockReturnValue('/some-other-page')
    render(<MobileBottomNav />)

    const dashboardLink = screen.getByRole('link', { name: /dashboard/i })
    expect(dashboardLink.className).toMatch(/hover:bg-white/)
  })

  it('uses proper semantic HTML structure', () => {
    const { container } = render(<MobileBottomNav />)

    const nav = screen.getByRole('navigation')
    const list = container.querySelector('ul')
    const listItems = container.querySelectorAll('li')

    expect(nav).toBeInTheDocument()
    expect(list).toBeInTheDocument()
    expect(listItems.length).toBe(5)
  })

  it('has z-index to appear above other content', () => {
    render(<MobileBottomNav />)
    const nav = screen.getByRole('navigation')
    expect(nav).toHaveClass('z-50')
  })

  it('renders small text for labels', () => {
    const { container } = render(<MobileBottomNav />)

    const labels = container.querySelectorAll('.text-\\[10px\\]')
    expect(labels.length).toBe(5) // One for each navigation item
  })
})
