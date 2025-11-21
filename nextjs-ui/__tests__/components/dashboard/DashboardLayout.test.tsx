import { render, screen } from '@testing-library/react'
import { DashboardLayout } from '@/components/dashboard/DashboardLayout'
import { useSession } from 'next-auth/react'
import { usePathname } from 'next/navigation'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

// Mock next-auth
jest.mock('next-auth/react')

// Mock next/navigation
jest.mock('next/navigation', () => ({
  usePathname: jest.fn(),
}))


function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  })
  const Wrapper = ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  )
  Wrapper.displayName = 'TestQueryWrapper'
  return Wrapper
}

describe('DashboardLayout', () => {
  beforeEach(() => {
    jest.clearAllMocks()
    ;(useSession as jest.Mock).mockReturnValue({
      data: {
        user: {
          name: 'John Doe',
          email: 'john@example.com',
        },
        accessToken: 'test-token',
      },
      status: 'authenticated',
    })
    ;(usePathname as jest.Mock).mockReturnValue('/dashboard')
    ;(global.fetch as jest.Mock).mockImplementation(() => new Promise(() => {}))
  })

  describe('layout structure', () => {
    it('renders main container', () => {
      const { container } = render(
        <DashboardLayout>
          <div>Test Content</div>
        </DashboardLayout>,
        { wrapper: createWrapper() }
      )

      const mainContainer = container.querySelector('.min-h-screen')
      expect(mainContainer).toBeInTheDocument()
    })

    it('applies correct padding to container', () => {
      const { container } = render(
        <DashboardLayout>
          <div>Test Content</div>
        </DashboardLayout>,
        { wrapper: createWrapper() }
      )

      const mainContainer = container.querySelector('.min-h-screen')
      expect(mainContainer).toHaveClass('p-6')
    })

    it('uses flexbox layout for sidebar and content', () => {
      const { container } = render(
        <DashboardLayout>
          <div>Test Content</div>
        </DashboardLayout>,
        { wrapper: createWrapper() }
      )

      const flexContainer = container.querySelector('.flex')
      expect(flexContainer).toBeInTheDocument()
    })
  })

  describe('header', () => {
    it('renders Header component', () => {
      render(
        <DashboardLayout>
          <div>Test Content</div>
        </DashboardLayout>,
        { wrapper: createWrapper() }
      )

      // Header contains "AI Agents Platform"
      expect(screen.getByText('AI Agents Platform')).toBeInTheDocument()
    })
  })

  describe('sidebar', () => {
    it('renders Sidebar component', () => {
      render(
        <DashboardLayout>
          <div>Test Content</div>
        </DashboardLayout>,
        { wrapper: createWrapper() }
      )

      // Sidebar contains navigation categories
      expect(screen.getByText(/monitoring/i)).toBeInTheDocument()
      expect(screen.getByText(/configuration/i)).toBeInTheDocument()
    })
  })

  describe('main content area', () => {
    it('renders children in main element', () => {
      render(
        <DashboardLayout>
          <div data-testid="test-content">Test Content</div>
        </DashboardLayout>,
        { wrapper: createWrapper() }
      )

      const content = screen.getByTestId('test-content')
      expect(content).toBeInTheDocument()
      expect(content.textContent).toBe('Test Content')
    })

    it('main element is flex-1', () => {
      const { container } = render(
        <DashboardLayout>
          <div>Test Content</div>
        </DashboardLayout>,
        { wrapper: createWrapper() }
      )

      const main = container.querySelector('main')
      expect(main).toHaveClass('flex-1')
    })

    it('renders complex children correctly', () => {
      render(
        <DashboardLayout>
          <div>
            <h1>My Dashboard Page</h1>
            <p>Welcome to the dashboard</p>
            <button>Click me</button>
          </div>
        </DashboardLayout>,
        { wrapper: createWrapper() }
      )

      expect(screen.getByText('My Dashboard Page')).toBeInTheDocument()
      expect(screen.getByText('Welcome to the dashboard')).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /click me/i })).toBeInTheDocument()
    })
  })

  describe('footer', () => {
    it('renders Footer component', () => {
      render(
        <DashboardLayout>
          <div>Test Content</div>
        </DashboardLayout>,
        { wrapper: createWrapper() }
      )

      // Footer contains copyright and version
      expect(screen.getByText(/All rights reserved/i)).toBeInTheDocument()
      expect(screen.getByText('v1.0.0')).toBeInTheDocument()
    })
  })

  describe('component integration', () => {
    it('renders all layout components together', () => {
      const { container } = render(
        <DashboardLayout>
          <div>Test Content</div>
        </DashboardLayout>,
        { wrapper: createWrapper() }
      )

      // Header
      expect(screen.getByRole('banner')).toBeInTheDocument()

      // Navigation elements (Sidebar + MobileBottomNav)
      const navElements = screen.getAllByRole('navigation')
      expect(navElements.length).toBeGreaterThanOrEqual(1)

      // Main content
      const main = container.querySelector('main')
      expect(main).toBeInTheDocument()

      // Footer
      expect(screen.getByRole('contentinfo')).toBeInTheDocument()
    })
  })

  describe('semantic HTML', () => {
    it('uses semantic header element', () => {
      render(
        <DashboardLayout>
          <div>Test Content</div>
        </DashboardLayout>,
        { wrapper: createWrapper() }
      )

      expect(screen.getByRole('banner')).toBeInTheDocument()
    })

    it('uses semantic nav elements', () => {
      render(
        <DashboardLayout>
          <div>Test Content</div>
        </DashboardLayout>,
        { wrapper: createWrapper() }
      )

      const navElements = screen.getAllByRole('navigation')
      expect(navElements.length).toBeGreaterThanOrEqual(1)
    })

    it('uses semantic main element', () => {
      const { container } = render(
        <DashboardLayout>
          <div>Test Content</div>
        </DashboardLayout>,
        { wrapper: createWrapper() }
      )

      const main = container.querySelector('main')
      expect(main).toBeInTheDocument()
      expect(main?.tagName).toBe('MAIN')
    })

    it('uses semantic footer element', () => {
      render(
        <DashboardLayout>
          <div>Test Content</div>
        </DashboardLayout>,
        { wrapper: createWrapper() }
      )

      expect(screen.getByRole('contentinfo')).toBeInTheDocument()
    })
  })

  describe('children rendering', () => {
    it('renders text children', () => {
      render(
        <DashboardLayout>
          Plain text content
        </DashboardLayout>,
        { wrapper: createWrapper() }
      )

      expect(screen.getByText('Plain text content')).toBeInTheDocument()
    })

    it('renders multiple children', () => {
      render(
        <DashboardLayout>
          <>
            <div>First child</div>
            <div>Second child</div>
          </>
        </DashboardLayout>,
        { wrapper: createWrapper() }
      )

      expect(screen.getByText('First child')).toBeInTheDocument()
      expect(screen.getByText('Second child')).toBeInTheDocument()
    })

    it('renders nested component trees', () => {
      const NestedComponent = () => (
        <div>
          <h1>Nested</h1>
          <ul>
            <li>Item 1</li>
            <li>Item 2</li>
          </ul>
        </div>
      )

      render(
        <DashboardLayout>
          <NestedComponent />
        </DashboardLayout>,
        { wrapper: createWrapper() }
      )

      expect(screen.getByText('Nested')).toBeInTheDocument()
      expect(screen.getByText('Item 1')).toBeInTheDocument()
      expect(screen.getByText('Item 2')).toBeInTheDocument()
    })
  })
})
