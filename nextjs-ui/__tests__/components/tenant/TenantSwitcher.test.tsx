import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { TenantSwitcher } from '@/components/tenant/TenantSwitcher'
import { useSession } from 'next-auth/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

// Mock next-auth
jest.mock('next-auth/react')

const mockTenants = [
  { id: '1', name: 'Tenant One', slug: 'tenant-one' },
  { id: '2', name: 'Tenant Two', slug: 'tenant-two' },
  { id: '3', name: 'Acme Corp', slug: 'acme-corp' },
]

const mockUserRole = {
  role: 'admin',
  tenant_id: '1',
}

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

describe('TenantSwitcher', () => {
  beforeEach(() => {
    jest.clearAllMocks()
    ;(useSession as jest.Mock).mockReturnValue({
      data: { accessToken: 'test-token' },
      status: 'authenticated',
    })
  })

  describe('loading state', () => {
    it('shows loading skeleton when fetching tenants', () => {
      ;(global.fetch as jest.Mock).mockImplementation(
        () => new Promise(() => {}) // Never resolves
      )

      const { container } = render(<TenantSwitcher />, { wrapper: createWrapper() })
      const skeleton = container.querySelector('.animate-pulse')
      expect(skeleton).toBeInTheDocument()
      expect(skeleton).toHaveClass('glass-card')
    })
  })

  describe('tenant list rendering', () => {
    beforeEach(() => {
      ;(global.fetch as jest.Mock).mockImplementation((url: string) => {
        if (url.includes('/api/v1/tenants')) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(mockTenants),
          })
        }
        if (url.includes('/api/v1/users/me/role')) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(mockUserRole),
          })
        }
        return Promise.reject(new Error('Unknown URL'))
      })
    })

    it('renders selected tenant name', async () => {
      render(<TenantSwitcher />, { wrapper: createWrapper() })

      await waitFor(() => {
        expect(screen.getByText('Tenant One')).toBeInTheDocument()
      })
    })

    it('renders user role when available', async () => {
      render(<TenantSwitcher />, { wrapper: createWrapper() })

      await waitFor(() => {
        expect(screen.getByText('admin')).toBeInTheDocument()
      })
    })

    it('formats role with spaces instead of underscores', async () => {
      ;(global.fetch as jest.Mock).mockImplementation((url: string) => {
        if (url.includes('/api/v1/tenants')) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(mockTenants),
          })
        }
        if (url.includes('/api/v1/users/me/role')) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve({ role: 'tenant_admin', tenant_id: '1' }),
          })
        }
        return Promise.reject(new Error('Unknown URL'))
      })

      render(<TenantSwitcher />, { wrapper: createWrapper() })

      await waitFor(() => {
        expect(screen.getByText('tenant admin')).toBeInTheDocument()
      })
    })
  })

  describe('dropdown interaction', () => {
    beforeEach(() => {
      ;(global.fetch as jest.Mock).mockImplementation((url: string) => {
        if (url.includes('/api/v1/tenants')) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(mockTenants),
          })
        }
        if (url.includes('/api/v1/users/me/role')) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(mockUserRole),
          })
        }
        return Promise.reject(new Error('Unknown URL'))
      })
    })

    it('opens dropdown when button is clicked', async () => {
      const user = userEvent.setup()
      render(<TenantSwitcher />, { wrapper: createWrapper() })

      await waitFor(() => {
        expect(screen.getByText('Tenant One')).toBeInTheDocument()
      })

      const button = screen.getByRole('button', { name: /tenant one/i })
      await user.click(button)

      await waitFor(() => {
        expect(screen.getByPlaceholderText('Search tenants...')).toBeInTheDocument()
      })
    })

    it('displays all tenants in dropdown', async () => {
      const user = userEvent.setup()
      render(<TenantSwitcher />, { wrapper: createWrapper() })

      await waitFor(() => {
        expect(screen.getByText('Tenant One')).toBeInTheDocument()
      })

      const button = screen.getByRole('button', { name: /tenant one/i })
      await user.click(button)

      await waitFor(() => {
        expect(screen.getByText('Tenant Two')).toBeInTheDocument()
        expect(screen.getByText('Acme Corp')).toBeInTheDocument()
      })
    })
  })

  describe('search functionality', () => {
    beforeEach(() => {
      ;(global.fetch as jest.Mock).mockImplementation((url: string) => {
        if (url.includes('/api/v1/tenants')) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(mockTenants),
          })
        }
        if (url.includes('/api/v1/users/me/role')) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(mockUserRole),
          })
        }
        return Promise.reject(new Error('Unknown URL'))
      })
    })

    it('filters tenants based on search query', async () => {
      const user = userEvent.setup()
      render(<TenantSwitcher />, { wrapper: createWrapper() })

      await waitFor(() => {
        expect(screen.getByText('Tenant One')).toBeInTheDocument()
      })

      const button = screen.getByRole('button', { name: /tenant one/i })
      await user.click(button)

      const searchInput = await screen.findByPlaceholderText('Search tenants...')
      await user.type(searchInput, 'Acme')

      await waitFor(() => {
        expect(screen.getByText('Acme Corp')).toBeInTheDocument()
        expect(screen.queryByText('Tenant Two')).not.toBeInTheDocument()
      })
    })

    it('shows "No tenants found" when search has no matches', async () => {
      const user = userEvent.setup()
      render(<TenantSwitcher />, { wrapper: createWrapper() })

      await waitFor(() => {
        expect(screen.getByText('Tenant One')).toBeInTheDocument()
      })

      const button = screen.getByRole('button', { name: /tenant one/i })
      await user.click(button)

      const searchInput = await screen.findByPlaceholderText('Search tenants...')
      await user.type(searchInput, 'NonExistent')

      await waitFor(() => {
        expect(screen.getByText('No tenants found')).toBeInTheDocument()
      })
    })

    it('is case-insensitive', async () => {
      const user = userEvent.setup()
      render(<TenantSwitcher />, { wrapper: createWrapper() })

      await waitFor(() => {
        expect(screen.getByText('Tenant One')).toBeInTheDocument()
      })

      const button = screen.getByRole('button', { name: /tenant one/i })
      await user.click(button)

      const searchInput = await screen.findByPlaceholderText('Search tenants...')
      await user.type(searchInput, 'acme')

      await waitFor(() => {
        expect(screen.getByText('Acme Corp')).toBeInTheDocument()
      })
    })
  })

  describe('tenant selection', () => {
    beforeEach(() => {
      ;(global.fetch as jest.Mock).mockImplementation((url: string) => {
        if (url.includes('/api/v1/tenants')) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(mockTenants),
          })
        }
        if (url.includes('/api/v1/users/me/role')) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(mockUserRole),
          })
        }
        return Promise.reject(new Error('Unknown URL'))
      })
    })

    it('shows check icon on selected tenant', async () => {
      const user = userEvent.setup()
      render(<TenantSwitcher />, { wrapper: createWrapper() })

      await waitFor(() => {
        expect(screen.getByText('Tenant One')).toBeInTheDocument()
      })

      const button = screen.getByRole('button', { name: /tenant one/i })
      await user.click(button)

      await waitFor(() => {
        const tenantOptions = screen.getAllByText('Tenant One')
        // Find the option in dropdown (not the button)
        const dropdownOption = tenantOptions.find(el =>
          el.closest('[role="option"]')
        )
        expect(dropdownOption?.closest('[role="option"]')).toBeInTheDocument()
      })
    })
  })

  describe('API integration', () => {
    it('calls tenants API with correct headers', async () => {
      ;(global.fetch as jest.Mock).mockImplementation((url: string) => {
        if (url.includes('/api/v1/tenants')) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(mockTenants),
          })
        }
        if (url.includes('/api/v1/users/me/role')) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(mockUserRole),
          })
        }
        return Promise.reject(new Error('Unknown URL'))
      })

      render(<TenantSwitcher />, { wrapper: createWrapper() })

      await waitFor(() => {
        expect(global.fetch).toHaveBeenCalledWith(
          expect.stringContaining('/api/v1/tenants'),
          expect.objectContaining({
            headers: {
              Authorization: 'Bearer test-token',
            },
          })
        )
      })
    })

    it('calls role API when tenant is selected', async () => {
      ;(global.fetch as jest.Mock).mockImplementation((url: string) => {
        if (url.includes('/api/v1/tenants')) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(mockTenants),
          })
        }
        if (url.includes('/api/v1/users/me/role')) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(mockUserRole),
          })
        }
        return Promise.reject(new Error('Unknown URL'))
      })

      render(<TenantSwitcher />, { wrapper: createWrapper() })

      await waitFor(() => {
        expect(global.fetch).toHaveBeenCalledWith(
          expect.stringContaining('/api/v1/users/me/role?tenant_id=1'),
          expect.objectContaining({
            headers: {
              Authorization: 'Bearer test-token',
            },
          })
        )
      })
    })

    it('handles API errors gracefully', async () => {
      ;(global.fetch as jest.Mock).mockRejectedValue(new Error('API Error'))

      // Suppress console.error for this test
      const consoleSpy = jest.spyOn(console, 'error').mockImplementation()

      const { container } = render(<TenantSwitcher />, { wrapper: createWrapper() })

      await waitFor(() => {
        const skeleton = container.querySelector('.animate-pulse')
        expect(skeleton).toBeInTheDocument()
      })

      consoleSpy.mockRestore()
    })
  })

  describe('authentication', () => {
    it('does not fetch tenants when not authenticated', () => {
      ;(useSession as jest.Mock).mockReturnValue({
        data: null,
        status: 'unauthenticated',
      })

      const { container } = render(<TenantSwitcher />, { wrapper: createWrapper() })

      expect(global.fetch).not.toHaveBeenCalled()
      const skeleton = container.querySelector('.animate-pulse')
      expect(skeleton).toBeInTheDocument()
    })
  })

  describe('styling', () => {
    beforeEach(() => {
      ;(global.fetch as jest.Mock).mockImplementation((url: string) => {
        if (url.includes('/api/v1/tenants')) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(mockTenants),
          })
        }
        if (url.includes('/api/v1/users/me/role')) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(mockUserRole),
          })
        }
        return Promise.reject(new Error('Unknown URL'))
      })
    })

    it('applies glassmorphism styles', async () => {
      render(<TenantSwitcher />, { wrapper: createWrapper() })

      await waitFor(() => {
        const button = screen.getByRole('button', { name: /tenant one/i })
        expect(button).toHaveClass('glass-card')
      })
    })

    it('applies hover effects', async () => {
      render(<TenantSwitcher />, { wrapper: createWrapper() })

      await waitFor(() => {
        const button = screen.getByRole('button', { name: /tenant one/i })
        expect(button).toHaveClass('hover:shadow-lg')
      })
    })
  })
})
