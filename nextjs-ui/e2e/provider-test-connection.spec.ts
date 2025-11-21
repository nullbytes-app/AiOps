/**
 * LLM Provider & Test Connection E2E Tests
 *
 * Tests provider CRUD, test connection flow, and model discovery
 * Following Playwright v1.51.0 best practices (2025)
 *
 * Story: 4-core-pages-configuration
 * AC-3: LLM Providers Page (/configuration/llm-providers)
 */

import { test, expect, Page, Route } from '@playwright/test'

test.describe.configure({ mode: 'parallel' })

test.describe('LLM Provider Management', () => {
  const mockProviders = [
    {
      id: 'openai-1',
      name: 'OpenAI Production',
      type: 'openai',
      api_key: 'sk-*********************abc123',
      status: 'healthy',
      last_test: '2025-01-18T10:30:00Z',
      models_count: 8,
      created_at: '2025-01-01T00:00:00Z',
    },
    {
      id: 'anthropic-1',
      name: 'Anthropic Claude',
      type: 'anthropic',
      api_key: 'sk-ant-***************xyz789',
      status: 'healthy',
      last_test: '2025-01-18T09:15:00Z',
      models_count: 5,
      created_at: '2025-01-05T00:00:00Z',
    },
    {
      id: 'litellm-1',
      name: 'LiteLLM Gateway',
      type: 'litellm',
      base_url: 'https://litellm.example.com',
      api_key: 'sk-*********************def456',
      status: 'unhealthy',
      last_test: '2025-01-18T08:00:00Z',
      models_count: 0,
      created_at: '2025-01-10T00:00:00Z',
    },
  ]

  test.beforeEach(async ({ page }) => {
    // Mock providers list
    await page.route('**/api/v1/llm-providers', async (route: Route) => {
      if (route.request().method() === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ data: mockProviders, total: 3 }),
        })
      }
    })

    await page.goto('/dashboard/llm-providers')
    await expect(page.getByRole('heading', { name: /llm providers/i, level: 1 })).toBeVisible()
  })

  test('displays provider cards in grid layout', async ({ page }) => {
    // Verify card grid (not table)
    await expect(page.getByText('OpenAI Production')).toBeVisible()
    await expect(page.getByText('Anthropic Claude')).toBeVisible()
    await expect(page.getByText('LiteLLM Gateway')).toBeVisible()

    // Verify provider details on cards
    const openaiCard = page.locator('[data-provider-id="openai-1"]').or(
      page.locator('.provider-card').filter({ hasText: 'OpenAI Production' })
    )
    await expect(openaiCard).toBeVisible()

    // Verify status badges
    await expect(page.getByText(/healthy/i).first()).toBeVisible()
    await expect(page.getByText(/unhealthy/i).first()).toBeVisible()

    // Verify models count
    await expect(page.getByText(/8 models/i).or(page.getByText(/8/i))).toBeVisible()
  })

  test('filters providers by status', async ({ page }) => {
    // Verify all providers visible initially
    await expect(page.getByText('OpenAI Production')).toBeVisible()
    await expect(page.getByText('LiteLLM Gateway')).toBeVisible()

    // Click status filter
    const statusFilter = page.getByLabel(/filter by status/i).or(page.locator('select').filter({ hasText: /all/i }))
    await statusFilter.click()
    await page.getByRole('option', { name: /healthy/i }).click()

    // Verify only healthy providers shown
    await expect(page.getByText('OpenAI Production')).toBeVisible()
    await expect.soft(page.getByText('LiteLLM Gateway')).not.toBeVisible()

    // Filter unhealthy
    await statusFilter.click()
    await page.getByRole('option', { name: /unhealthy/i }).click()

    await expect(page.getByText('LiteLLM Gateway')).toBeVisible()
    await expect.soft(page.getByText('OpenAI Production')).not.toBeVisible()
  })

  test('creates provider with required test connection flow', async ({ page }) => {
    const newProvider = {
      name: 'XAI Grok',
      type: 'openai',
      api_key: 'xai-abc123def456ghi789',
    }

    // Mock test connection endpoint (must succeed before creation)
    let testConnectionCalled = false
    await page.route('**/api/v1/llm-providers/test-connection', async (route: Route) => {
      if (route.request().method() === 'POST') {
        testConnectionCalled = true
        const payload = route.request().postDataJSON()

        // Simulate delay
        await new Promise((resolve) => setTimeout(resolve, 800))

        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            message: 'Connection successful',
            models_discovered: 6,
          }),
        })
      }
    })

    // Mock POST provider (should only succeed after test connection)
    await page.route('**/api/v1/llm-providers', async (route: Route) => {
      if (route.request().method() === 'POST') {
        const payload = route.request().postDataJSON()

        // Verify test connection was called first
        expect(testConnectionCalled).toBe(true)

        await route.fulfill({
          status: 201,
          contentType: 'application/json',
          body: JSON.stringify({
            id: 'xai-1',
            ...payload,
            status: 'healthy',
            models_count: 6,
            created_at: new Date().toISOString(),
          }),
        })
      }
    })

    // Click Add Provider
    await page.getByRole('button', { name: /add provider/i }).click()

    // Fill form
    await page.getByLabel(/provider name/i).fill(newProvider.name)

    // Select type
    await page.getByLabel(/provider type/i).click()
    await page.getByRole('option', { name: /openai/i, exact: true }).click()

    // Verify base_url field is hidden for openai type
    await expect(page.getByLabel(/base url/i)).not.toBeVisible()

    // Fill API key (should be password input with show/hide toggle)
    const apiKeyInput = page.getByLabel(/api key/i)
    await expect(apiKeyInput).toHaveAttribute('type', 'password')
    await apiKeyInput.fill(newProvider.api_key)

    // Verify Show/Hide toggle
    const showToggle = page.getByRole('button', { name: /show api key/i }).or(
      page.getByRole('button', { name: /toggle api key visibility/i })
    )
    await showToggle.click()
    await expect(apiKeyInput).toHaveAttribute('type', 'text')
    await showToggle.click()
    await expect(apiKeyInput).toHaveAttribute('type', 'password')

    // Verify Create button is disabled until test connection succeeds
    const createButton = page.getByRole('button', { name: /create provider/i, exact: true })
    await expect(createButton).toBeDisabled()

    // Click Test Connection
    const testButton = page.getByRole('button', { name: /test connection/i })
    await expect(testButton).toBeEnabled()
    await testButton.click()

    // Verify loading state
    await expect(page.getByText(/testing connection/i)).toBeVisible()

    // Verify success message
    await expect(page.getByText(/connection successful/i)).toBeVisible({ timeout: 3000 })
    await expect(page.getByText(/6 models discovered/i).or(page.getByText(/discovered 6 models/i))).toBeVisible()

    // Now Create button should be enabled
    await expect(createButton).toBeEnabled()

    // Submit form
    await createButton.click()

    // Verify success
    await expect(page.getByText(/provider created successfully/i)).toBeVisible({ timeout: 5000 })

    // Verify new provider appears in grid
    await expect(page.getByText('XAI Grok')).toBeVisible()
  })

  test('shows base_url field conditionally for litellm type', async ({ page }) => {
    await page.getByRole('button', { name: /add provider/i }).click()

    // Initially select openai (no base_url)
    await page.getByLabel(/provider type/i).click()
    await page.getByRole('option', { name: /openai/i, exact: true }).click()

    await expect(page.getByLabel(/base url/i)).not.toBeVisible()

    // Switch to litellm (requires base_url)
    await page.getByLabel(/provider type/i).click()
    await page.getByRole('option', { name: /litellm/i }).click()

    await expect(page.getByLabel(/base url/i)).toBeVisible()

    // Verify base_url is required
    await page.getByRole('button', { name: /test connection/i }).click()
    await expect(page.getByText(/base url is required/i).or(page.getByText(/required/i))).toBeVisible()
  })

  test('handles test connection failures gracefully', async ({ page }) => {
    await page.route('**/api/v1/llm-providers/test-connection', async (route: Route) => {
      await route.fulfill({
        status: 401,
        contentType: 'application/json',
        body: JSON.stringify({
          success: false,
          error: 'Invalid API key',
        }),
      })
    })

    await page.getByRole('button', { name: /add provider/i }).click()

    await page.getByLabel(/provider name/i).fill('Test Provider')
    await page.getByLabel(/provider type/i).click()
    await page.getByRole('option', { name: /openai/i, exact: true }).click()
    await page.getByLabel(/api key/i).fill('invalid-key')

    await page.getByRole('button', { name: /test connection/i }).click()

    // Verify error message
    await expect(
      page.getByText(/invalid api key/i).or(page.getByText(/connection failed/i))
    ).toBeVisible({ timeout: 3000 })

    // Create button should remain disabled
    await expect(page.getByRole('button', { name: /create provider/i, exact: true })).toBeDisabled()
  })

  test('navigates to provider detail with Models tab', async ({ page }) => {
    // Mock provider detail
    await page.route('**/api/v1/llm-providers/openai-1', async (route: Route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockProviders[0]),
      })
    })

    // Mock models list
    await page.route('**/api/v1/llm-providers/openai-1/models', async (route: Route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          models: ['gpt-4', 'gpt-4-turbo', 'gpt-3.5-turbo', 'gpt-4o', 'gpt-4o-mini'],
        }),
      })
    })

    // Click on provider card
    await page.getByText('OpenAI Production').click()

    // Verify URL
    await expect(page).toHaveURL(/\/dashboard\/llm-providers\/openai-1/)

    // Verify tabs exist
    await expect(page.getByRole('tab', { name: /overview/i })).toBeVisible()
    await expect(page.getByRole('tab', { name: /models/i })).toBeVisible()

    // Click Models tab
    await page.getByRole('tab', { name: /models/i }).click()

    // Verify models displayed
    await expect(page.getByText('gpt-4')).toBeVisible()
    await expect(page.getByText('gpt-4-turbo')).toBeVisible()
    await expect(page.getByText('gpt-3.5-turbo')).toBeVisible()

    // Verify Refresh Models button exists
    await expect(page.getByRole('button', { name: /refresh models/i })).toBeVisible()
  })

  test('refreshes models list in Models tab', async ({ page }) => {
    let refreshCount = 0
    const initialModels = ['gpt-4', 'gpt-3.5-turbo']
    const updatedModels = ['gpt-4', 'gpt-4-turbo', 'gpt-3.5-turbo', 'gpt-4o']

    await page.route('**/api/v1/llm-providers/openai-1', async (route: Route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockProviders[0]),
      })
    })

    await page.route('**/api/v1/llm-providers/openai-1/models', async (route: Route) => {
      refreshCount++
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          models: refreshCount === 1 ? initialModels : updatedModels,
        }),
      })
    })

    await page.goto('/dashboard/llm-providers/openai-1')
    await page.getByRole('tab', { name: /models/i }).click()

    // Verify initial models
    await expect(page.getByText('gpt-4')).toBeVisible()
    await expect(page.getByText('gpt-3.5-turbo')).toBeVisible()
    await expect.soft(page.getByText('gpt-4o')).not.toBeVisible()

    // Click Refresh
    await page.getByRole('button', { name: /refresh models/i }).click()

    // Verify loading state
    await expect(page.getByText(/refreshing/i).or(page.getByRole('progressbar'))).toBeVisible()

    // Verify updated models appear
    await expect(page.getByText('gpt-4o')).toBeVisible({ timeout: 3000 })
    await expect(page.getByText('gpt-4-turbo')).toBeVisible()
  })

  test('edits provider and re-tests connection', async ({ page }) => {
    await page.route('**/api/v1/llm-providers/openai-1', async (route: Route) => {
      if (route.request().method() === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(mockProviders[0]),
        })
      } else if (route.request().method() === 'PUT') {
        const payload = route.request().postDataJSON()
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ id: 'openai-1', ...payload, updated_at: new Date().toISOString() }),
        })
      }
    })

    await page.route('**/api/v1/llm-providers/test-connection', async (route: Route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ success: true, message: 'Connection successful', models_discovered: 10 }),
      })
    })

    // Navigate to provider detail
    await page.goto('/dashboard/llm-providers/openai-1')

    // Click Edit button
    await page.getByRole('button', { name: /edit/i }).click()

    // Update name
    const nameInput = page.getByLabel(/provider name/i)
    await nameInput.clear()
    await nameInput.fill('OpenAI Production (Updated)')

    // Test connection again
    await page.getByRole('button', { name: /test connection/i }).click()
    await expect(page.getByText(/connection successful/i)).toBeVisible({ timeout: 3000 })

    // Update provider
    await page.getByRole('button', { name: /update provider/i }).click()

    await expect(page.getByText(/provider updated successfully/i)).toBeVisible({ timeout: 5000 })
  })

  test('deletes provider with confirmation', async ({ page }) => {
    await page.route('**/api/v1/llm-providers/openai-1', async (route: Route) => {
      if (route.request().method() === 'DELETE') {
        await route.fulfill({ status: 204 })
      }
    })

    const providerCard = page.locator('[data-provider-id="openai-1"]').or(
      page.locator('.provider-card').filter({ hasText: 'OpenAI Production' })
    )
    await providerCard.getByRole('button', { name: /delete/i }).click()

    // Verify warning dialog
    const dialog = page.getByRole('dialog')
    await expect(dialog).toBeVisible()
    await expect(dialog.getByText(/delete openai production/i)).toBeVisible()
    await expect(dialog.getByText(/agents using this provider will fail/i).or(dialog.getByText(/cannot be undone/i))).toBeVisible()

    // Confirm
    await dialog.getByRole('button', { name: /delete provider/i }).click()

    await expect(page.getByText(/provider deleted/i)).toBeVisible({ timeout: 5000 })
  })

  test('displays empty state when no providers exist', async ({ page }) => {
    await page.route('**/api/v1/llm-providers', async (route: Route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ data: [], total: 0 }),
      })
    })

    await page.reload()

    await expect(page.getByText(/no llm providers configured/i)).toBeVisible()
    await expect(page.getByText(/add your first provider/i)).toBeVisible()
    await expect(page.getByRole('button', { name: /add provider/i })).toBeVisible()
  })

  test('validates provider form fields', async ({ page }) => {
    await page.getByRole('button', { name: /add provider/i }).click()

    // Submit empty form
    await page.getByRole('button', { name: /test connection/i }).click()

    // Verify validation errors
    await expect(page.getByText(/provider name is required/i).or(page.getByText(/name must be at least 3 characters/i))).toBeVisible()
    await expect(page.getByText(/api key is required/i)).toBeVisible()

    // Fill name too short
    await page.getByLabel(/provider name/i).fill('AB')
    await page.getByLabel(/api key/i).click() // Trigger blur
    await expect(page.getByText(/name must be at least 3 characters/i)).toBeVisible()

    // Fill valid name
    await page.getByLabel(/provider name/i).fill('Valid Provider Name')
    await page.getByLabel(/api key/i).click()
    await expect(page.getByText(/name must be at least 3 characters/i)).not.toBeVisible()
  })

  test('masks API key in provider list cards', async ({ page }) => {
    // Verify API keys are masked in list view
    const openaiCard = page.locator('[data-provider-id="openai-1"]').or(
      page.locator('.provider-card').filter({ hasText: 'OpenAI Production' })
    )

    // Should show masked key like "sk-***...abc123"
    await expect(openaiCard.getByText(/sk-\*+/)).toBeVisible()

    // Should NOT show full API key in plain text
    await expect.soft(openaiCard.getByText(/sk-[a-zA-Z0-9]{20,}/)).not.toBeVisible()
  })
})
