/**
 * MSW Request Handlers
 *
 * Mock API handlers for development and testing.
 * These handlers intercept network requests and return mock responses.
 */

import { http, HttpResponse } from 'msw'
import { healthHandlers } from './handlers/health'
import { metricsHandlers } from './handlers/metrics'
import { configurationHandlers } from './handlers/configuration'
import { auditHandlers } from './handlers/audit'

/**
 * Mock user data
 */
const mockUser = {
  id: 'user-123',
  email: 'john.doe@example.com',
  name: 'John Doe',
  role: 'admin',
  tenantId: 'tenant-1',
  createdAt: '2024-01-01T00:00:00Z',
}

/**
 * Mock tenant data
 */
const mockTenants = [
  {
    id: 'tenant-1',
    name: 'Acme Corporation',
    slug: 'acme',
    plan: 'enterprise',
    isActive: true,
    createdAt: '2024-01-01T00:00:00Z',
  },
  {
    id: 'tenant-2',
    name: 'TechCorp Inc',
    slug: 'techcorp',
    plan: 'professional',
    isActive: true,
    createdAt: '2024-01-15T00:00:00Z',
  },
  {
    id: 'tenant-3',
    name: 'StartupXYZ',
    slug: 'startupxyz',
    plan: 'starter',
    isActive: true,
    createdAt: '2024-02-01T00:00:00Z',
  },
]

/**
 * Request handlers for API endpoints
 */
export const handlers = [
  // Health monitoring endpoints
  ...healthHandlers,

  // Metrics endpoints (agent execution and ticket processing)
  ...metricsHandlers,

  // Configuration endpoints (tenants, agents, LLM providers, MCP servers)
  ...configurationHandlers,

  // Audit endpoints (auth and general audit logs)
  ...auditHandlers,

  /**
   * POST /api/v1/auth/login
   * Mock login endpoint
   */
  http.post('/api/v1/auth/login', async ({ request }) => {
    const body = (await request.json()) as { email: string; password: string }

    // Simulate authentication validation
    if (!body.email || !body.password) {
      return HttpResponse.json(
        { error: 'Email and password are required' },
        { status: 400 }
      )
    }

    // Simulate failed login for specific test email
    if (body.email === 'fail@example.com') {
      return HttpResponse.json(
        { error: 'Invalid credentials' },
        { status: 401 }
      )
    }

    // Successful login response
    return HttpResponse.json(
      {
        accessToken: 'mock-access-token-123',
        refreshToken: 'mock-refresh-token-456',
        user: mockUser,
        expiresIn: 3600,
      },
      { status: 200 }
    )
  }),

  /**
   * GET /api/v1/users/me/tenants
   * Mock endpoint to fetch user's tenants
   */
  http.get('/api/v1/users/me/tenants', ({ request }) => {
    const authHeader = request.headers.get('Authorization')

    // Simulate unauthorized access
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      return HttpResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    // Return mock tenants
    return HttpResponse.json(
      {
        tenants: mockTenants,
        total: mockTenants.length,
      },
      { status: 200 }
    )
  }),

  /**
   * GET /api/v1/users/me/role
   * Mock endpoint to fetch user's role for a specific tenant
   */
  http.get('/api/v1/users/me/role', ({ request }) => {
    const authHeader = request.headers.get('Authorization')

    // Simulate unauthorized access
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      return HttpResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    // Get tenant_id from query params
    const url = new URL(request.url)
    const tenant_id = url.searchParams.get('tenant_id') || mockUser.tenantId

    // Return mock user role for the tenant
    return HttpResponse.json(
      {
        role: mockUser.role,
        tenant_id: tenant_id,
        permissions: [
          'users:read',
          'users:write',
          'tenants:read',
          'tenants:write',
          'agents:read',
          'agents:write',
          'workflows:read',
          'workflows:write',
        ],
      },
      { status: 200 }
    )
  }),

  /**
   * POST /api/v1/tenants/switch
   * Mock endpoint to switch active tenant
   */
  http.post('/api/v1/tenants/switch', async ({ request }) => {
    const authHeader = request.headers.get('Authorization')

    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      return HttpResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const body = (await request.json()) as { tenantId: string }

    const tenant = mockTenants.find((t) => t.id === body.tenantId)

    if (!tenant) {
      return HttpResponse.json({ error: 'Tenant not found' }, { status: 404 })
    }

    return HttpResponse.json(
      {
        success: true,
        tenant,
      },
      { status: 200 }
    )
  }),

  /**
   * GET /api/v1/users/me
   * Mock endpoint to fetch current user
   */
  http.get('/api/v1/users/me', ({ request }) => {
    const authHeader = request.headers.get('Authorization')

    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      return HttpResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    return HttpResponse.json(mockUser, { status: 200 })
  }),
]
