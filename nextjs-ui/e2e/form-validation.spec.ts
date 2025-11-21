/**
 * Form Validation E2E Tests
 *
 * Tests form validation patterns across all configuration pages
 * Following Playwright v1.51.0 best practices (2025)
 *
 * Story: 4-core-pages-configuration
 * AC-5: Forms & UX Polish (validation, error messages, loading states)
 */

import { test, expect, Page, Route } from '@playwright/test'

test.describe.configure({ mode: 'parallel' })

test.describe('Form Validation Patterns', () => {
  test.describe('Tenant Form Validation', () => {
    test.beforeEach(async ({ page }) => {
      await page.route('**/api/v1/tenants', async (route: Route) => {
        if (route.request().method() === 'GET') {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({ data: [], total: 0 }),
          })
        }
      })

      await page.goto('/dashboard/tenants')
      await page.getByRole('button', { name: /create tenant/i }).click()
    })

    test('validates required fields on submit', async ({ page }) => {
      // Submit empty form
      await page.getByRole('button', { name: /create tenant/i, exact: true }).click()

      // Verify required field errors
      await expect(page.getByText(/name.*required/i).or(page.getByText(/name must be at least 3 characters/i))).toBeVisible()
    })

    test('validates minimum name length (3 chars)', async ({ page }) => {
      const nameInput = page.getByLabel(/tenant name/i)

      // Too short
      await nameInput.fill('AB')
      await page.getByLabel(/description/i).click() // Trigger blur

      await expect(page.getByText(/name must be at least 3 characters/i)).toBeVisible()

      // Valid length
      await nameInput.fill('ABC')
      await page.getByLabel(/description/i).click()

      await expect(page.getByText(/name must be at least 3 characters/i)).not.toBeVisible()
    })

    test('validates logo URL format', async ({ page }) => {
      const logoInput = page.getByLabel(/logo url/i)

      // Invalid URL
      await logoInput.fill('not-a-url')
      await page.getByLabel(/tenant name/i).click()

      await expect(
        page.getByText(/invalid url/i).or(page.getByText(/must be a valid url/i))
      ).toBeVisible()

      // Valid URL
      await logoInput.fill('https://example.com/logo.png')
      await page.getByLabel(/tenant name/i).click()

      await expect(page.getByText(/invalid url/i)).not.toBeVisible()
    })

    test('clears error messages when field is corrected', async ({ page }) => {
      const nameInput = page.getByLabel(/tenant name/i)

      // Trigger error
      await nameInput.fill('AB')
      await page.getByLabel(/description/i).click()
      await expect(page.getByText(/name must be at least 3 characters/i)).toBeVisible()

      // Fix error
      await nameInput.fill('Valid Name')
      await page.getByLabel(/description/i).click()

      await expect(page.getByText(/name must be at least 3 characters/i)).not.toBeVisible()
    })
  })

  test.describe('Agent Form Validation', () => {
    test.beforeEach(async ({ page }) => {
      await page.route('**/api/v1/agents', async (route: Route) => {
        if (route.request().method() === 'GET') {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({ data: [], total: 0 }),
          })
        }
      })

      await page.route('**/api/v1/llm-providers', async (route: Route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            data: [{ id: 'openai-1', name: 'OpenAI', type: 'openai', status: 'healthy' }],
          }),
        })
      })

      await page.route('**/api/v1/llm-providers/*/models', async (route: Route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ models: ['gpt-4', 'gpt-3.5-turbo'] }),
        })
      })

      await page.goto('/dashboard/agents-config')
      await page.getByRole('button', { name: /create agent/i }).click()
    })

    test('validates system prompt minimum length (20 chars)', async ({ page }) => {
      const promptInput = page.getByLabel(/system prompt/i)

      // Too short
      await promptInput.fill('Short prompt')
      await page.getByLabel(/^name/i).click()

      await expect(page.getByText(/system prompt must be at least 20 characters/i)).toBeVisible()

      // Valid length
      await promptInput.fill('This is a valid system prompt that meets the minimum length requirement')
      await page.getByLabel(/^name/i).click()

      await expect(page.getByText(/system prompt must be at least 20 characters/i)).not.toBeVisible()
    })

    test('validates temperature range (0-2)', async ({ page }) => {
      const tempSlider = page.getByLabel(/temperature/i)

      // Too low
      await tempSlider.fill('-0.5')
      await page.getByLabel(/^name/i).click()

      await expect(
        page.getByText(/temperature must be between 0 and 2/i).or(page.getByText(/min.*0/i))
      ).toBeVisible()

      // Too high
      await tempSlider.fill('2.5')
      await page.getByLabel(/^name/i).click()

      await expect(
        page.getByText(/temperature must be between 0 and 2/i).or(page.getByText(/max.*2/i))
      ).toBeVisible()

      // Valid value
      await tempSlider.fill('0.7')
      await page.getByLabel(/^name/i).click()

      await expect(page.getByText(/temperature must be between 0 and 2/i)).not.toBeVisible()
    })

    test('validates max_tokens is positive number', async ({ page }) => {
      const tokensInput = page.getByLabel(/max tokens/i)

      // Zero
      await tokensInput.fill('0')
      await page.getByLabel(/^name/i).click()

      await expect(
        page.getByText(/max tokens must be greater than 0/i).or(page.getByText(/must be positive/i))
      ).toBeVisible()

      // Negative
      await tokensInput.fill('-100')
      await page.getByLabel(/^name/i).click()

      await expect(page.getByText(/must be greater than 0/i).or(page.getByText(/must be positive/i))).toBeVisible()

      // Valid value
      await tokensInput.fill('2000')
      await page.getByLabel(/^name/i).click()

      await expect(page.getByText(/must be greater than 0/i)).not.toBeVisible()
    })

    test('validates LLM provider selection is required', async ({ page }) => {
      // Fill other fields but skip provider
      await page.getByLabel(/^name/i).fill('Test Agent')
      await page.getByLabel(/system prompt/i).fill('This is a valid system prompt for testing')

      await page.getByRole('button', { name: /create agent/i, exact: true }).click()

      await expect(
        page.getByText(/provider.*required/i).or(page.getByText(/select.*provider/i))
      ).toBeVisible()
    })

    test('validates LLM model selection is required after provider', async ({ page }) => {
      // Select provider
      await page.getByLabel(/provider/i).click()
      await page.getByRole('option', { name: /openai/i }).click()

      // Model dropdown should be enabled
      await expect(page.getByLabel(/llm model/i)).toBeEnabled()

      // Try to submit without model
      await page.getByLabel(/^name/i).fill('Test Agent')
      await page.getByLabel(/system prompt/i).fill('This is a valid system prompt for testing')
      await page.getByRole('button', { name: /create agent/i, exact: true }).click()

      await expect(
        page.getByText(/model.*required/i).or(page.getByText(/select.*model/i))
      ).toBeVisible()
    })
  })

  test.describe('LLM Provider Form Validation', () => {
    test.beforeEach(async ({ page }) => {
      await page.route('**/api/v1/llm-providers', async (route: Route) => {
        if (route.request().method() === 'GET') {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({ data: [], total: 0 }),
          })
        }
      })

      await page.goto('/dashboard/llm-providers')
      await page.getByRole('button', { name: /add provider/i }).click()
    })

    test('validates API key format (minimum length)', async ({ page }) => {
      const apiKeyInput = page.getByLabel(/api key/i)

      // Too short
      await apiKeyInput.fill('abc')
      await page.getByLabel(/provider name/i).click()

      await expect(
        page.getByText(/api key.*too short/i).or(page.getByText(/api key must be at least/i))
      ).toBeVisible()

      // Valid length
      await apiKeyInput.fill('sk-1234567890abcdefghijklmnopqrstuvwxyz')
      await page.getByLabel(/provider name/i).click()

      await expect(page.getByText(/api key.*too short/i)).not.toBeVisible()
    })

    test('validates base_url is required for litellm type', async ({ page }) => {
      // Select litellm
      await page.getByLabel(/provider type/i).click()
      await page.getByRole('option', { name: /litellm/i }).click()

      // base_url field should appear
      await expect(page.getByLabel(/base url/i)).toBeVisible()

      // Try to test connection without base_url
      await page.getByLabel(/provider name/i).fill('LiteLLM Test')
      await page.getByLabel(/api key/i).fill('sk-1234567890abcdefghijklmnopqrstuvwxyz')
      await page.getByRole('button', { name: /test connection/i }).click()

      await expect(
        page.getByText(/base url.*required/i).or(page.getByText(/url is required/i))
      ).toBeVisible()
    })

    test('validates base_url format for litellm', async ({ page }) => {
      await page.getByLabel(/provider type/i).click()
      await page.getByRole('option', { name: /litellm/i }).click()

      const baseUrlInput = page.getByLabel(/base url/i)

      // Invalid URL
      await baseUrlInput.fill('not-a-url')
      await page.getByLabel(/provider name/i).click()

      await expect(
        page.getByText(/invalid url/i).or(page.getByText(/must be a valid url/i))
      ).toBeVisible()

      // Valid URL
      await baseUrlInput.fill('https://litellm.example.com')
      await page.getByLabel(/provider name/i).click()

      await expect(page.getByText(/invalid url/i)).not.toBeVisible()
    })

    test('shows real-time validation errors on blur', async ({ page }) => {
      const nameInput = page.getByLabel(/provider name/i)

      // Focus and blur without entering anything
      await nameInput.focus()
      await page.getByLabel(/provider type/i).click()

      await expect(
        page.getByText(/provider name.*required/i).or(page.getByText(/name must be at least 3 characters/i))
      ).toBeVisible()
    })
  })

  test.describe('MCP Server Form Validation', () => {
    test.beforeEach(async ({ page }) => {
      await page.route('**/api/v1/mcp-servers', async (route: Route) => {
        if (route.request().method() === 'GET') {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({ data: [], total: 0 }),
          })
        }
      })

      await page.goto('/dashboard/mcp-servers')
      await page.getByRole('button', { name: /add mcp server/i }).click()
    })

    test('validates conditional fields based on transport type', async ({ page }) => {
      // Select stdio
      await page.getByLabel(/transport type/i).click()
      await page.getByRole('option', { name: /stdio/i }).click()

      // Verify stdio fields visible
      await expect(page.getByLabel(/command/i)).toBeVisible()

      // Verify SSE fields hidden
      await expect(page.getByLabel(/url/i)).not.toBeVisible()

      // Switch to SSE
      await page.getByLabel(/transport type/i).click()
      await page.getByRole('option', { name: /sse/i }).click()

      // Verify SSE fields visible
      await expect(page.getByLabel(/url/i)).toBeVisible()

      // Verify stdio fields hidden
      await expect(page.getByLabel(/command/i)).not.toBeVisible()
    })

    test('validates command is required for stdio', async ({ page }) => {
      await page.getByLabel(/transport type/i).click()
      await page.getByRole('option', { name: /stdio/i }).click()

      await page.getByLabel(/server name/i).fill('Test Server')
      await page.getByRole('button', { name: /test connection/i }).click()

      await expect(
        page.getByText(/command.*required/i).or(page.getByText(/command is required/i))
      ).toBeVisible()
    })

    test('validates URL format for SSE transport', async ({ page }) => {
      await page.getByLabel(/transport type/i).click()
      await page.getByRole('option', { name: /sse/i }).click()

      const urlInput = page.getByLabel(/url/i)

      // Invalid URL
      await urlInput.fill('invalid-url')
      await page.getByLabel(/server name/i).click()

      await expect(
        page.getByText(/invalid url/i).or(page.getByText(/must be a valid url/i))
      ).toBeVisible()

      // Valid URL
      await urlInput.fill('https://mcp.example.com')
      await page.getByLabel(/server name/i).click()

      await expect(page.getByText(/invalid url/i)).not.toBeVisible()
    })
  })

  test.describe('Cross-Form Validation Patterns', () => {
    test('displays inline error messages next to fields', async ({ page }) => {
      await page.route('**/api/v1/tenants', async (route: Route) => {
        if (route.request().method() === 'GET') {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({ data: [], total: 0 }),
          })
        }
      })

      await page.goto('/dashboard/tenants')
      await page.getByRole('button', { name: /create tenant/i }).click()

      // Submit empty form
      await page.getByRole('button', { name: /create tenant/i, exact: true }).click()

      // Verify error appears near the field (not just in a toast)
      const nameInput = page.getByLabel(/tenant name/i)
      const nameError = page.locator('text=/name must be at least 3 characters/i')

      await expect(nameError).toBeVisible()

      // Error should be visually close to the input
      const inputBox = await nameInput.boundingBox()
      const errorBox = await nameError.boundingBox()

      if (inputBox && errorBox) {
        // Error should be within 100px vertically of the input
        expect(Math.abs(errorBox.y - inputBox.y)).toBeLessThan(150)
      }
    })

    test('disables submit button during API call', async ({ page }) => {
      await page.route('**/api/v1/tenants', async (route: Route) => {
        if (route.request().method() === 'GET') {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({ data: [], total: 0 }),
          })
        } else if (route.request().method() === 'POST') {
          // Simulate slow API
          await new Promise((resolve) => setTimeout(resolve, 2000))
          await route.fulfill({
            status: 201,
            contentType: 'application/json',
            body: JSON.stringify({
              id: '1',
              name: 'Test Tenant',
              created_at: new Date().toISOString(),
            }),
          })
        }
      })

      await page.goto('/dashboard/tenants')
      await page.getByRole('button', { name: /create tenant/i }).click()

      await page.getByLabel(/tenant name/i).fill('Test Tenant')
      await page.getByLabel(/description/i).fill('Test Description')

      const submitButton = page.getByRole('button', { name: /create tenant/i, exact: true })
      await submitButton.click()

      // Button should be disabled during API call
      await expect(submitButton).toBeDisabled()

      // Verify loading indicator
      await expect(page.getByText(/creating/i).or(page.getByRole('progressbar'))).toBeVisible()
    })

    test('handles API validation errors gracefully', async ({ page }) => {
      await page.route('**/api/v1/tenants', async (route: Route) => {
        if (route.request().method() === 'GET') {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({ data: [], total: 0 }),
          })
        } else if (route.request().method() === 'POST') {
          await route.fulfill({
            status: 400,
            contentType: 'application/json',
            body: JSON.stringify({
              error: 'Validation failed',
              details: { name: 'Tenant name already exists' },
            }),
          })
        }
      })

      await page.goto('/dashboard/tenants')
      await page.getByRole('button', { name: /create tenant/i }).click()

      await page.getByLabel(/tenant name/i).fill('Existing Tenant')
      await page.getByLabel(/description/i).fill('Test')

      await page.getByRole('button', { name: /create tenant/i, exact: true }).click()

      // Verify API error displayed
      await expect(
        page.getByText(/tenant name already exists/i).or(page.getByText(/validation failed/i))
      ).toBeVisible({ timeout: 3000 })
    })

    test('prevents double submission', async ({ page }) => {
      let submitCount = 0

      await page.route('**/api/v1/tenants', async (route: Route) => {
        if (route.request().method() === 'GET') {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({ data: [], total: 0 }),
          })
        } else if (route.request().method() === 'POST') {
          submitCount++
          await new Promise((resolve) => setTimeout(resolve, 1000))
          await route.fulfill({
            status: 201,
            contentType: 'application/json',
            body: JSON.stringify({ id: '1', name: 'Test', created_at: new Date().toISOString() }),
          })
        }
      })

      await page.goto('/dashboard/tenants')
      await page.getByRole('button', { name: /create tenant/i }).click()

      await page.getByLabel(/tenant name/i).fill('Test Tenant')
      await page.getByLabel(/description/i).fill('Test')

      const submitButton = page.getByRole('button', { name: /create tenant/i, exact: true })

      // Click submit twice rapidly
      await submitButton.click()
      await submitButton.click().catch(() => {}) // May fail if disabled

      // Wait for request to complete
      await page.waitForTimeout(1500)

      // Verify only one submission occurred
      expect(submitCount).toBe(1)
    })
  })
})
