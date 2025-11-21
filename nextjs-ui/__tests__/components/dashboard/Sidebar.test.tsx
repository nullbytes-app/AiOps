import { render, screen } from '@testing-library/react'
import { Sidebar } from '@/components/dashboard/Sidebar'
import { usePathname } from 'next/navigation'

// Mock next/navigation
jest.mock('next/navigation', () => ({
  usePathname: jest.fn(),
}))

describe('Sidebar', () => {
  beforeEach(() => {
    ;(usePathname as jest.Mock).mockReturnValue('/dashboard')
  })

  describe('rendering', () => {
    it('renders sidebar element', () => {
      const { container } = render(<Sidebar />)
      const sidebar = container.querySelector('aside')
      expect(sidebar).toBeInTheDocument()
    })

    it('applies glassmorphism styles', () => {
      const { container } = render(<Sidebar />)
      const sidebar = container.querySelector('aside')
      expect(sidebar).toHaveClass('glass-card')
    })

    it('has correct dimensions', () => {
      const { container } = render(<Sidebar />)
      const sidebar = container.querySelector('aside')
      expect(sidebar).toHaveClass('w-64')
      expect(sidebar).toHaveClass('h-[calc(100vh-120px)]')
    })

    it('is scrollable', () => {
      const { container } = render(<Sidebar />)
      const sidebar = container.querySelector('aside')
      expect(sidebar).toHaveClass('overflow-y-auto')
    })
  })

  describe('navigation categories', () => {
    it('renders Monitoring category', () => {
      render(<Sidebar />)
      expect(screen.getByText(/monitoring/i)).toBeInTheDocument()
    })

    it('renders Configuration category', () => {
      render(<Sidebar />)
      expect(screen.getByText(/configuration/i)).toBeInTheDocument()
    })

    it('renders Operations category', () => {
      render(<Sidebar />)
      expect(screen.getByText(/operations/i)).toBeInTheDocument()
    })

    it('renders Tools category', () => {
      const { container } = render(<Sidebar />)
      // Find the category header (h3 element) with "Tools"
      const toolsCategory = Array.from(container.querySelectorAll('h3')).find(
        h3 => h3.textContent?.toLowerCase() === 'tools'
      )
      expect(toolsCategory).toBeInTheDocument()
    })

    it('applies uppercase styling to categories', () => {
      render(<Sidebar />)
      const category = screen.getByText(/monitoring/i)
      expect(category).toHaveClass('uppercase')
      expect(category).toHaveClass('text-xs')
      expect(category).toHaveClass('font-semibold')
    })
  })

  describe('monitoring navigation items', () => {
    it('renders Dashboard link', () => {
      render(<Sidebar />)
      expect(screen.getByRole('link', { name: /dashboard/i })).toHaveAttribute('href', '/dashboard')
    })

    it('renders System Health link', () => {
      render(<Sidebar />)
      expect(screen.getByRole('link', { name: /system health/i })).toHaveAttribute('href', '/dashboard/health')
    })

    it('renders Agent Metrics link', () => {
      render(<Sidebar />)
      expect(screen.getByRole('link', { name: /agent metrics/i })).toHaveAttribute('href', '/dashboard/agents')
    })

    it('renders Ticket Processing link', () => {
      render(<Sidebar />)
      expect(screen.getByRole('link', { name: /ticket processing/i })).toHaveAttribute('href', '/dashboard/tickets')
    })
  })

  describe('configuration navigation items', () => {
    it('renders Tenants link', () => {
      render(<Sidebar />)
      expect(screen.getByRole('link', { name: /tenants/i })).toHaveAttribute('href', '/dashboard/tenants')
    })

    it('renders Agents link', () => {
      render(<Sidebar />)
      expect(screen.getByRole('link', { name: /^agents$/i })).toHaveAttribute('href', '/dashboard/agents-config')
    })

    it('renders Prompts link', () => {
      render(<Sidebar />)
      expect(screen.getByRole('link', { name: /prompts/i })).toHaveAttribute('href', '/dashboard/prompts')
    })

    it('renders Tools link', () => {
      render(<Sidebar />)
      expect(screen.getByRole('link', { name: /^tools$/i })).toHaveAttribute('href', '/dashboard/tools')
    })

    it('renders Plugins link', () => {
      render(<Sidebar />)
      expect(screen.getByRole('link', { name: /plugins/i })).toHaveAttribute('href', '/dashboard/plugins')
    })

    it('renders MCP Servers link', () => {
      render(<Sidebar />)
      expect(screen.getByRole('link', { name: /mcp servers/i })).toHaveAttribute('href', '/dashboard/mcp-servers')
    })

    it('renders Workflows link', () => {
      render(<Sidebar />)
      expect(screen.getByRole('link', { name: /workflows/i })).toHaveAttribute('href', '/dashboard/workflows')
    })
  })

  describe('operations navigation items', () => {
    it('renders Logs link', () => {
      render(<Sidebar />)
      expect(screen.getByRole('link', { name: /logs/i })).toHaveAttribute('href', '/dashboard/logs')
    })

    it('renders Audit Trail link', () => {
      render(<Sidebar />)
      expect(screen.getByRole('link', { name: /audit trail/i })).toHaveAttribute('href', '/dashboard/audit')
    })

    it('renders Settings link', () => {
      render(<Sidebar />)
      expect(screen.getByRole('link', { name: /settings/i })).toHaveAttribute('href', '/dashboard/settings')
    })
  })

  describe('tools navigation items', () => {
    it('renders API Playground link', () => {
      render(<Sidebar />)
      expect(screen.getByRole('link', { name: /api playground/i })).toHaveAttribute('href', '/dashboard/playground')
    })

    it('renders Testing link', () => {
      render(<Sidebar />)
      expect(screen.getByRole('link', { name: /testing/i })).toHaveAttribute('href', '/dashboard/testing')
    })
  })

  describe('active link highlighting', () => {
    it('highlights Dashboard link when on /dashboard', () => {
      ;(usePathname as jest.Mock).mockReturnValue('/dashboard')
      render(<Sidebar />)

      const dashboardLink = screen.getByRole('link', { name: /dashboard/i })
      expect(dashboardLink).toHaveClass('bg-accent-blue')
      expect(dashboardLink).toHaveClass('text-white')
      expect(dashboardLink).toHaveClass('shadow-md')
    })

    it('highlights Agent Metrics link when on /dashboard/agents', () => {
      ;(usePathname as jest.Mock).mockReturnValue('/dashboard/agents')
      render(<Sidebar />)

      const agentsLink = screen.getByRole('link', { name: /agent metrics/i })
      expect(agentsLink).toHaveClass('bg-accent-blue')
      expect(agentsLink).toHaveClass('text-white')
    })

    it('applies hover styles to non-active links', () => {
      ;(usePathname as jest.Mock).mockReturnValue('/dashboard')
      render(<Sidebar />)

      const agentsLink = screen.getByRole('link', { name: /agent metrics/i })
      expect(agentsLink).toHaveClass('hover:bg-white/50')
      expect(agentsLink).toHaveClass('text-text-primary')
    })
  })

  describe('icons', () => {
    it('renders icons for all navigation items', () => {
      const { container } = render(<Sidebar />)
      // Count all SVG icons (lucide-react renders as SVG)
      const icons = container.querySelectorAll('svg')
      // 4 Monitoring + 7 Configuration + 3 Operations + 2 Tools = 16 items
      expect(icons.length).toBe(16)
    })
  })

  describe('layout', () => {
    it('uses navigation element', () => {
      render(<Sidebar />)
      const nav = screen.getByRole('navigation')
      expect(nav).toBeInTheDocument()
    })

    it('applies spacing between sections', () => {
      const { container } = render(<Sidebar />)
      const nav = container.querySelector('nav')
      expect(nav).toHaveClass('space-y-6')
    })

    it('applies spacing between list items', () => {
      const { container } = render(<Sidebar />)
      const firstList = container.querySelector('ul')
      expect(firstList).toHaveClass('space-y-1')
    })
  })

  describe('accessibility', () => {
    it('uses semantic nav element', () => {
      render(<Sidebar />)
      expect(screen.getByRole('navigation')).toBeInTheDocument()
    })

    it('all links are keyboard accessible', () => {
      render(<Sidebar />)
      const links = screen.getAllByRole('link')
      // 16 total navigation items
      expect(links.length).toBe(16)
      links.forEach(link => {
        expect(link).toHaveAttribute('href')
      })
    })

    it('uses heading for categories', () => {
      const { container } = render(<Sidebar />)
      const headings = container.querySelectorAll('h3')
      expect(headings.length).toBe(4) // 4 categories
    })
  })

  describe('visual transitions', () => {
    it('applies transition classes to links', () => {
      render(<Sidebar />)
      const link = screen.getByRole('link', { name: /dashboard/i })
      expect(link).toHaveClass('transition-all')
      expect(link).toHaveClass('duration-fast')
    })
  })
})
