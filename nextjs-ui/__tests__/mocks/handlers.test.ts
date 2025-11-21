/**
 * MSW Handlers Tests
 *
 * Tests for MSW request handlers to verify they return correct mock responses.
 */

import { http, HttpResponse } from 'msw'
import { setupServer } from 'msw/node'
import { handlers } from '@/mocks/handlers'

// Setup MSW server for Node.js test environment
const server = setupServer(...handlers)

describe('MSW Handlers', () => {
  // Start server before all tests
  beforeAll(() => server.listen())

  // Reset handlers after each test to ensure test isolation
  afterEach(() => server.resetHandlers())

  // Close server after all tests
  afterAll(() => server.close())

  describe('POST /api/v1/auth/login', () => {
    it('returns 400 when email is missing', async () => {
      const response = await fetch('/api/v1/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ password: 'password123' }),
      })

      expect(response.status).toBe(400)
      const data = await response.json()
      expect(data.error).toBe('Email and password are required')
    })

    it('returns 400 when password is missing', async () => {
      const response = await fetch('/api/v1/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: 'test@example.com' }),
      })

      expect(response.status).toBe(400)
      const data = await response.json()
      expect(data.error).toBe('Email and password are required')
    })

    it('returns 401 for invalid credentials', async () => {
      const response = await fetch('/api/v1/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: 'fail@example.com',
          password: 'wrongpassword',
        }),
      })

      expect(response.status).toBe(401)
      const data = await response.json()
      expect(data.error).toBe('Invalid credentials')
    })

    it('returns access token and user data for valid credentials', async () => {
      const response = await fetch('/api/v1/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: 'john.doe@example.com',
          password: 'password123',
        }),
      })

      expect(response.status).toBe(200)
      const data = await response.json()
      expect(data).toHaveProperty('accessToken')
      expect(data).toHaveProperty('refreshToken')
      expect(data).toHaveProperty('user')
      expect(data).toHaveProperty('expiresIn')
      expect(data.user.email).toBe('john.doe@example.com')
      expect(data.user.name).toBe('John Doe')
      expect(data.expiresIn).toBe(3600)
    })
  })

  describe('GET /api/v1/users/me/tenants', () => {
    it('returns 401 when Authorization header is missing', async () => {
      const response = await fetch('/api/v1/users/me/tenants')

      expect(response.status).toBe(401)
      const data = await response.json()
      expect(data.error).toBe('Unauthorized')
    })

    it('returns 401 when Authorization header is invalid', async () => {
      const response = await fetch('/api/v1/users/me/tenants', {
        headers: { Authorization: 'InvalidToken' },
      })

      expect(response.status).toBe(401)
      const data = await response.json()
      expect(data.error).toBe('Unauthorized')
    })

    it('returns tenant list with valid authorization', async () => {
      const response = await fetch('/api/v1/users/me/tenants', {
        headers: { Authorization: 'Bearer mock-token-123' },
      })

      expect(response.status).toBe(200)
      const data = await response.json()
      expect(data).toHaveProperty('tenants')
      expect(data).toHaveProperty('total')
      expect(Array.isArray(data.tenants)).toBe(true)
      expect(data.tenants.length).toBe(3)
      expect(data.total).toBe(3)
      expect(data.tenants[0].name).toBe('Acme Corporation')
    })
  })

  describe('GET /api/v1/users/me/role', () => {
    it('returns 401 when Authorization header is missing', async () => {
      const response = await fetch('/api/v1/users/me/role')

      expect(response.status).toBe(401)
      const data = await response.json()
      expect(data.error).toBe('Unauthorized')
    })

    it('returns user role and permissions with valid authorization', async () => {
      const response = await fetch('/api/v1/users/me/role', {
        headers: { Authorization: 'Bearer mock-token-123' },
      })

      expect(response.status).toBe(200)
      const data = await response.json()
      expect(data).toHaveProperty('role')
      expect(data).toHaveProperty('permissions')
      expect(data.role).toBe('admin')
      expect(Array.isArray(data.permissions)).toBe(true)
      expect(data.permissions.length).toBeGreaterThan(0)
      expect(data.permissions).toContain('users:read')
      expect(data.permissions).toContain('users:write')
    })
  })

  describe('POST /api/v1/tenants/switch', () => {
    it('returns 401 without authorization', async () => {
      const response = await fetch('/api/v1/tenants/switch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tenantId: 'tenant-1' }),
      })

      expect(response.status).toBe(401)
    })

    it('returns 404 for non-existent tenant', async () => {
      const response = await fetch('/api/v1/tenants/switch', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: 'Bearer mock-token-123',
        },
        body: JSON.stringify({ tenantId: 'non-existent' }),
      })

      expect(response.status).toBe(404)
      const data = await response.json()
      expect(data.error).toBe('Tenant not found')
    })

    it('successfully switches to valid tenant', async () => {
      const response = await fetch('/api/v1/tenants/switch', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: 'Bearer mock-token-123',
        },
        body: JSON.stringify({ tenantId: 'tenant-2' }),
      })

      expect(response.status).toBe(200)
      const data = await response.json()
      expect(data.success).toBe(true)
      expect(data.tenant.id).toBe('tenant-2')
      expect(data.tenant.name).toBe('TechCorp Inc')
    })
  })

  describe('GET /api/v1/users/me', () => {
    it('returns 401 without authorization', async () => {
      const response = await fetch('/api/v1/users/me')

      expect(response.status).toBe(401)
    })

    it('returns current user with valid authorization', async () => {
      const response = await fetch('/api/v1/users/me', {
        headers: { Authorization: 'Bearer mock-token-123' },
      })

      expect(response.status).toBe(200)
      const data = await response.json()
      expect(data).toHaveProperty('id')
      expect(data).toHaveProperty('email')
      expect(data).toHaveProperty('name')
      expect(data).toHaveProperty('role')
      expect(data.email).toBe('john.doe@example.com')
      expect(data.name).toBe('John Doe')
      expect(data.role).toBe('admin')
    })
  })

  describe('Handler Override', () => {
    it('allows overriding handlers for specific tests', async () => {
      // Override the login handler to simulate server error
      server.use(
        http.post('/api/v1/auth/login', () => {
          return HttpResponse.json({ error: 'Server error' }, { status: 500 })
        })
      )

      const response = await fetch('/api/v1/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: 'test@example.com',
          password: 'password',
        }),
      })

      expect(response.status).toBe(500)
      const data = await response.json()
      expect(data.error).toBe('Server error')
    })
  })
})
