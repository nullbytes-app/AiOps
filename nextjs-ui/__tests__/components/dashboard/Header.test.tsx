import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Header } from '@/components/dashboard/Header'
import { useSession, signOut } from 'next-auth/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

// Mock next-auth
jest.mock('next-auth/react')

// Mock TenantSwitcher component
jest.mock('@/components/tenant/TenantSwitcher', () => ({
  TenantSwitcher: () => <div data-testid="tenant-switcher">Tenant Switcher</div>,
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

describe('Header', () => {
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
  })

  describe('layout', () => {
    it('renders header element', () => {
      render(<Header />, { wrapper: createWrapper() })
      const header = screen.getByRole('banner')
      expect(header).toBeInTheDocument()
    })

    it('applies glassmorphism styles', () => {
      render(<Header />, { wrapper: createWrapper() })
      const header = screen.getByRole('banner')
      expect(header).toHaveClass('glass-card')
    })

    it('has correct height and spacing', () => {
      render(<Header />, { wrapper: createWrapper() })
      const header = screen.getByRole('banner')
      expect(header).toHaveClass('h-16')
      expect(header).toHaveClass('px-6')
      expect(header).toHaveClass('mb-6')
    })
  })

  describe('logo section', () => {
    it('renders logo with gradient', () => {
      const { container } = render(<Header />, { wrapper: createWrapper() })
      const logo = container.querySelector('.bg-gradient-to-br')
      expect(logo).toBeInTheDocument()
      expect(logo).toHaveClass('from-accent-blue')
      expect(logo).toHaveClass('to-accent-purple')
    })

    it('displays "AI" text in logo', () => {
      render(<Header />, { wrapper: createWrapper() })
      expect(screen.getByText('AI')).toBeInTheDocument()
    })

    it('renders platform title', () => {
      render(<Header />, { wrapper: createWrapper() })
      expect(screen.getByText('AI Agents Platform')).toBeInTheDocument()
    })

    it('applies correct styles to title', () => {
      render(<Header />, { wrapper: createWrapper() })
      const title = screen.getByText('AI Agents Platform')
      expect(title).toHaveClass('text-xl')
      expect(title).toHaveClass('font-semibold')
      expect(title).toHaveClass('text-text-primary')
    })
  })

  describe('tenant switcher', () => {
    it('renders TenantSwitcher component', () => {
      render(<Header />, { wrapper: createWrapper() })
      expect(screen.getByTestId('tenant-switcher')).toBeInTheDocument()
    })
  })

  describe('user menu', () => {
    it('renders user avatar', () => {
      const { container } = render(<Header />, { wrapper: createWrapper() })
      const avatar = container.querySelector('.bg-accent-purple\\/20')
      expect(avatar).toBeInTheDocument()
    })

    it('displays user name from session', () => {
      render(<Header />, { wrapper: createWrapper() })
      expect(screen.getByText('John Doe')).toBeInTheDocument()
    })

    it('displays "User" when no name in session', () => {
      ;(useSession as jest.Mock).mockReturnValue({
        data: {
          user: {},
          accessToken: 'test-token',
        },
        status: 'authenticated',
      })

      render(<Header />, { wrapper: createWrapper() })
      expect(screen.getByText('User')).toBeInTheDocument()
    })

    it('shows chevron down icon', () => {
      const { container } = render(<Header />, { wrapper: createWrapper() })
      // Lucide icons render as SVG
      const chevron = container.querySelector('svg')
      expect(chevron).toBeInTheDocument()
    })
  })

  describe('user menu dropdown', () => {
    it('opens dropdown when user menu is clicked', async () => {
      const user = userEvent.setup()
      render(<Header />, { wrapper: createWrapper() })

      const menuButton = screen.getByRole('button', { name: /john doe/i })
      await user.click(menuButton)

      await waitFor(() => {
        expect(screen.getByText('Settings')).toBeInTheDocument()
        expect(screen.getByText('Logout')).toBeInTheDocument()
      })
    })

    it('renders Settings menu item', async () => {
      const user = userEvent.setup()
      render(<Header />, { wrapper: createWrapper() })

      const menuButton = screen.getByRole('button', { name: /john doe/i })
      await user.click(menuButton)

      await waitFor(() => {
        const settingsButton = screen.getByText('Settings')
        expect(settingsButton).toBeInTheDocument()
      })
    })

    it('renders Logout menu item', async () => {
      const user = userEvent.setup()
      render(<Header />, { wrapper: createWrapper() })

      const menuButton = screen.getByRole('button', { name: /john doe/i })
      await user.click(menuButton)

      await waitFor(() => {
        const logoutButton = screen.getByText('Logout')
        expect(logoutButton).toBeInTheDocument()
      })
    })

    it('calls signOut when Logout is clicked', async () => {
      const user = userEvent.setup()
      const mockSignOut = jest.fn()
      ;(signOut as jest.Mock).mockImplementation(mockSignOut)

      render(<Header />, { wrapper: createWrapper() })

      const menuButton = screen.getByRole('button', { name: /john doe/i })
      await user.click(menuButton)

      const logoutButton = await screen.findByText('Logout')
      await user.click(logoutButton)

      expect(mockSignOut).toHaveBeenCalledWith({ callbackUrl: '/login' })
    })

    it('applies glassmorphism to dropdown', async () => {
      const user = userEvent.setup()
      render(<Header />, { wrapper: createWrapper() })

      const menuButton = screen.getByRole('button', { name: /john doe/i })
      await user.click(menuButton)

      await waitFor(() => {
        const dropdown = screen.getByRole('menu')
        expect(dropdown).toHaveClass('glass-card')
      })
    })

    it('applies hover effects to menu items', async () => {
      const user = userEvent.setup()
      render(<Header />, { wrapper: createWrapper() })

      const menuButton = screen.getByRole('button', { name: /john doe/i })
      await user.click(menuButton)

      await waitFor(() => {
        const settingsButton = screen.getByText('Settings').closest('button')
        expect(settingsButton).toHaveClass('transition-colors')
        expect(settingsButton).toHaveClass('duration-fast')
      })
    })
  })

  describe('responsive behavior', () => {
    it('uses flexbox layout for header', () => {
      render(<Header />, { wrapper: createWrapper() })
      const header = screen.getByRole('banner')
      expect(header).toHaveClass('flex')
      expect(header).toHaveClass('items-center')
      expect(header).toHaveClass('justify-between')
    })

    it('has proper spacing between sections', () => {
      const { container } = render(<Header />, { wrapper: createWrapper() })
      const logoSection = container.querySelector('.flex.items-center.gap-3')
      expect(logoSection).toBeInTheDocument()
    })
  })

  describe('accessibility', () => {
    it('has semantic header element', () => {
      render(<Header />, { wrapper: createWrapper() })
      expect(screen.getByRole('banner')).toBeInTheDocument()
    })

    it('user menu button is keyboard accessible', async () => {
      render(<Header />, { wrapper: createWrapper() })
      const menuButton = screen.getByRole('button', { name: /john doe/i })
      expect(menuButton).toBeInTheDocument()
    })

    it('dropdown menu items are keyboard accessible', async () => {
      const user = userEvent.setup()
      render(<Header />, { wrapper: createWrapper() })

      const menuButton = screen.getByRole('button', { name: /john doe/i })
      await user.click(menuButton)

      await waitFor(() => {
        const settingsItem = screen.getByRole('menuitem', { name: /settings/i })
        expect(settingsItem).toBeInTheDocument()
      })
    })
  })

  describe('visual design', () => {
    it('applies correct z-index to dropdown', async () => {
      const user = userEvent.setup()
      render(<Header />, { wrapper: createWrapper() })

      const menuButton = screen.getByRole('button', { name: /john doe/i })
      await user.click(menuButton)

      await waitFor(() => {
        const dropdown = screen.getByRole('menu')
        expect(dropdown).toHaveClass('z-50')
      })
    })

    it('applies shadow effects', async () => {
      const user = userEvent.setup()
      render(<Header />, { wrapper: createWrapper() })

      const menuButton = screen.getByRole('button', { name: /john doe/i })
      await user.click(menuButton)

      await waitFor(() => {
        const dropdown = screen.getByRole('menu')
        expect(dropdown).toHaveClass('shadow-lg')
      })
    })

    it('uses correct text colors', () => {
      render(<Header />, { wrapper: createWrapper() })
      const userName = screen.getByText('John Doe')
      expect(userName).toHaveClass('text-text-primary')
    })
  })

  describe('icons', () => {
    it('renders Settings icon', async () => {
      const user = userEvent.setup()
      render(<Header />, { wrapper: createWrapper() })

      const menuButton = screen.getByRole('button', { name: /john doe/i })
      await user.click(menuButton)

      await waitFor(() => {
        const settingsButton = screen.getByText('Settings').closest('button')
        // Check that the button contains an icon (SVG element)
        const icon = settingsButton?.querySelector('svg')
        expect(icon).toBeInTheDocument()
      })
    })

    it('renders Logout icon', async () => {
      const user = userEvent.setup()
      render(<Header />, { wrapper: createWrapper() })

      const menuButton = screen.getByRole('button', { name: /john doe/i })
      await user.click(menuButton)

      await waitFor(() => {
        const logoutButton = screen.getByText('Logout').closest('button')
        // Check that the button contains an icon (SVG element)
        const icon = logoutButton?.querySelector('svg')
        expect(icon).toBeInTheDocument()
      })
    })

    it('renders User icon in avatar', () => {
      const { container } = render(<Header />, { wrapper: createWrapper() })
      const userIcon = container.querySelector('.text-accent-purple')
      expect(userIcon).toBeInTheDocument()
    })
  })
})
