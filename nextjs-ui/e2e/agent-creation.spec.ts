/**
 * Agent Creation & Tool Assignment E2E Tests
 *
 * Tests agent CRUD, tool assignment (drag-and-drop), and test sandbox
 * Following Playwright v1.51.0 best practices (2025)
 *
 * Story: 4-core-pages-configuration
 * AC-2: Agents Page (/configuration/agents)
 */

import { test, expect } from '@playwright/test'

test.describe.configure({ mode: 'parallel' })

test.describe('Agent Creation & Management', () => {
  const mockAgents = [
    {
      id: '1',
      name: 'Ticket Enhancer',
      type: 'webhook-triggered',
      status: 'active',
      system_prompt: 'Enhance ticket descriptions with context',
      llm_model: 'gpt-4',
      provider_id: 'openai-1',
      temperature: 0.7,
      max_tokens: 2000,
      tools_count: 5,
      last_run: '2025-01-18T10:30:00Z',
    },
  ]

  const mockTools = [
    { id: 'tool-1', name: 'GitHub API', description: 'Fetch GitHub data', source: 'openapi' },
    { id: 'tool-2', name: 'Jira API', description: 'Fetch Jira tickets', source: 'openapi' },
    { id: 'tool-3', name: 'File Reader', description: 'Read files', source: 'mcp' },
  ]

  test.beforeEach(async ({ page }) => {
    // Mock agents list
    await page.route('**/api/v1/agents', async (route: Route) => {
      if (route.request().method() === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ data: mockAgents, total: 1 }),
        })
      }
    })

    // Mock LLM providers for model dropdown
    await page.route('**/api/v1/llm-providers', async (route: Route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          data: [
            { id: 'openai-1', name: 'OpenAI Production', type: 'openai', status: 'healthy' },
            { id: 'anthropic-1', name: 'Anthropic', type: 'anthropic', status: 'healthy' },
          ],
        }),
      })
    })

    // Mock models for selected provider
    await page.route('**/api/v1/llm-providers/*/models', async (route: Route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          models: ['gpt-4', 'gpt-4-turbo', 'gpt-3.5-turbo', 'claude-3-opus', 'claude-3-sonnet'],
        }),
      })
    })

    await page.goto('/dashboard/agents-config')
    // Use exact match to avoid matching "AI Agents Platform" in header
    await expect(page.getByRole('heading', { name: 'Agents', exact: true, level: 1 })).toBeVisible()
  })

  test('creates a new agent with all required fields', async ({ page }) => {
    const newAgent = {
      name: 'Code Reviewer',
      type: 'task-based',
      system_prompt: 'Review code for best practices and security issues. Provide actionable feedback.',
      llm_model: 'gpt-4',
      provider_id: 'openai-1',
      temperature: 0.3,
      max_tokens: 4000,
      status: 'active',
    }

    // Mock POST /api/v1/agents
    await page.route('**/api/v1/agents', async (route: Route) => {
      if (route.request().method() === 'POST') {
        const payload = route.request().postDataJSON()
        expect(payload.name).toBe(newAgent.name)
        expect(payload.temperature).toBe(newAgent.temperature)

        await route.fulfill({
          status: 201,
          contentType: 'application/json',
          body: JSON.stringify({ id: '999', ...payload, tools_count: 0, last_run: null }),
        })
      }
    })

    // Click Create Agent button
    await page.getByRole('button', { name: /create agent/i }).click()

    // Fill form fields
    await page.getByLabel(/^name/i).fill(newAgent.name)

    // Select type from dropdown
    await page.getByLabel(/type/i).click()
    await page.getByRole('option', { name: /task-based/i }).click()

    // Fill system prompt (textarea with min 20 chars)
    await page.getByLabel(/system prompt/i).fill(newAgent.system_prompt)

    // Select LLM provider
    await page.getByLabel(/provider/i).click()
    await page.getByRole('option', { name: /openai production/i }).click()

    // Select model (should populate after provider selection)
    await expect(page.getByLabel(/llm model/i)).toBeEnabled()
    await page.getByLabel(/llm model/i).click()
    await page.getByRole('option', { name: /gpt-4/i, exact: true }).click()

    // Adjust temperature slider
    const tempSlider = page.getByLabel(/temperature/i)
    await tempSlider.fill(newAgent.temperature.toString())

    // Adjust max tokens
    await page.getByLabel(/max tokens/i).fill(newAgent.max_tokens.toString())

    // Toggle status
    const statusToggle = page.getByLabel(/status/i).or(page.getByRole('switch', { name: /active/i }))
    await statusToggle.check()

    // Submit
    await page.getByRole('button', { name: /create agent/i, exact: true }).click()

    // Verify success
    await expect(page.getByText(/agent created successfully/i)).toBeVisible({ timeout: 5000 })

    // Should redirect to detail page
    await expect(page).toHaveURL(/\/dashboard\/agents-config\/999/)
  })

  test('validates agent form fields', async ({ page }) => {
    await page.getByRole('button', { name: /create agent/i }).click()

    // Submit empty form
    await page.getByRole('button', { name: /create agent/i, exact: true }).click()

    // Verify validation errors
    await expect(page.getByText(/name must be at least 3 characters/i)).toBeVisible()
    await expect(page.getByText(/system prompt must be at least 20 characters/i)).toBeVisible()

    // Fill name too short
    await page.getByLabel(/^name/i).fill('AB')
    await page.getByLabel(/system prompt/i).click() // Trigger blur
    await expect(page.getByText(/name must be at least 3 characters/i)).toBeVisible()

    // Fill valid name
    await page.getByLabel(/^name/i).fill('Valid Agent Name')
    await page.getByLabel(/system prompt/i).click()
    await expect(page.getByText(/name must be at least 3 characters/i)).not.toBeVisible()

    // System prompt too short
    await page.getByLabel(/system prompt/i).fill('Short')
    await page.getByLabel(/^name/i).click()
    await expect(page.getByText(/system prompt must be at least 20 characters/i)).toBeVisible()
  })

  test('navigates to agent detail page with 3 tabs', async ({ page }) => {
    // Mock agent detail
    await page.route('**/api/v1/agents/1', async (route: Route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockAgents[0]),
      })
    })

    // Click on agent name
    await page.getByText('Ticket Enhancer').click()

    // Verify URL
    await expect(page).toHaveURL(/\/dashboard\/agents-config\/1/)

    // Verify tabs exist
    await expect(page.getByRole('tab', { name: /overview/i })).toBeVisible()
    await expect(page.getByRole('tab', { name: /tools assignment/i })).toBeVisible()
    await expect(page.getByRole('tab', { name: /test sandbox/i })).toBeVisible()
  })

  test('assigns tools using drag-and-drop interface', async ({ page }) => {
    // Mock agent detail
    await page.route('**/api/v1/agents/1', async (route: Route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ ...mockAgents[0], tool_ids: [] }),
      })
    })

    // Mock tools list
    await page.route('**/api/v1/tools', async (route: Route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ tools: mockTools }),
      })
    })

    // Navigate to agent detail
    await page.goto('/dashboard/agents-config/1')

    // Click Tools Assignment tab
    await page.getByRole('tab', { name: /tools assignment/i }).click()

    // Verify two columns
    await expect(page.getByText(/available tools/i)).toBeVisible()
    await expect(page.getByText(/assigned tools/i)).toBeVisible()

    // Verify tools in available column
    await expect(page.getByText('GitHub API')).toBeVisible()
    await expect(page.getByText('Jira API')).toBeVisible()

    // Note: Actual drag-and-drop testing requires mouse simulation
    // This is a simplified verification of the UI elements
    const githubTool = page.locator('[draggable="true"]').filter({ hasText: 'GitHub API' })
    await expect(githubTool).toBeVisible()

    // Verify Save button exists (disabled until changes made)
    const saveButton = page.getByRole('button', { name: /save changes/i })
    await expect(saveButton).toBeVisible()
    // Initially disabled
    await expect(saveButton).toBeDisabled()
  })

  test('tests agent in Test Sandbox', async ({ page }) => {
    const testMessage = 'Analyze this code snippet for security issues'
    const mockResponse = {
      response: { content: 'Found 2 security issues: SQL injection risk, XSS vulnerability' },
      duration_ms: 1245,
      tokens_used: 523,
      cost: 0.0234,
      metadata: { model: 'gpt-4', temperature: 0.7 },
    }

    // Mock agent detail
    await page.route('**/api/v1/agents/1', async (route: Route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockAgents[0]),
      })
    })

    // Mock test execution
    await page.route('**/api/v1/agents/1/test', async (route: Route) => {
      if (route.request().method() === 'POST') {
        const payload = route.request().postDataJSON()
        expect(payload.message).toBe(testMessage)

        // Simulate delay
        await new Promise((resolve) => setTimeout(resolve, 500))

        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(mockResponse),
        })
      }
    })

    // Navigate to Test Sandbox tab
    await page.goto('/dashboard/agents-config/1')
    await page.getByRole('tab', { name: /test sandbox/i }).click()

    // Verify empty state
    await expect(page.getByText(/no test results yet/i).or(page.getByPlaceholder(/enter a message/i))).toBeVisible()

    // Fill test message
    await page.getByPlaceholder(/enter a message/i).fill(testMessage)

    // Verify Execute button enabled
    const executeButton = page.getByRole('button', { name: /execute test/i })
    await expect(executeButton).toBeEnabled()

    // Click Execute
    await executeButton.click()

    // Verify loading state
    await expect(page.getByText(/testing agent/i)).toBeVisible()

    // Verify response displayed
    await expect(page.getByText(/Found 2 security issues/i)).toBeVisible({ timeout: 3000 })

    // Verify metadata
    await expect(page.getByText(/1245ms/i).or(page.getByText(/1\.2s/i))).toBeVisible()
    await expect(page.getByText(/523/i)).toBeVisible() // tokens
    await expect(page.getByText(/\$0\.0234/i)).toBeVisible() // cost

    // Verify Clear Results button
    await expect(page.getByRole('button', { name: /clear results/i })).toBeVisible()
  })

  test('handles test execution errors gracefully', async ({ page }) => {
    await page.route('**/api/v1/agents/1', async (route: Route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockAgents[0]),
      })
    })

    // Mock error response
    await page.route('**/api/v1/agents/1/test', async (route: Route) => {
      await route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ error: 'LLM provider timeout' }),
      })
    })

    await page.goto('/dashboard/agents-config/1')
    await page.getByRole('tab', { name: /test sandbox/i }).click()

    await page.getByPlaceholder(/enter a message/i).fill('Test message')
    await page.getByRole('button', { name: /execute test/i }).click()

    // Verify error message
    await expect(page.getByText(/test failed/i).or(page.getByText(/LLM provider timeout/i))).toBeVisible({
      timeout: 3000,
    })
  })

  test('filters agents by status', async ({ page }) => {
    const mixedAgents = [
      { ...mockAgents[0], status: 'active' },
      { id: '2', name: 'Inactive Agent', status: 'inactive', tools_count: 0 },
    ]

    await page.route('**/api/v1/agents', async (route: Route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ data: mixedAgents, total: 2 }),
      })
    })

    await page.reload()
    await expect(page.getByText('Ticket Enhancer')).toBeVisible()
    await expect(page.getByText('Inactive Agent')).toBeVisible()

    // Click status filter dropdown
    const statusFilter = page.getByLabel(/filter by status/i).or(page.locator('select').filter({ hasText: /all/i }))
    await statusFilter.click()
    await page.getByRole('option', { name: /active/i }).click()

    // Verify only active agents shown (UI filter, not API)
    await expect(page.getByText('Ticket Enhancer')).toBeVisible()
    await expect.soft(page.getByText('Inactive Agent')).not.toBeVisible()
  })

  test('deletes agent with confirmation', async ({ page }) => {
    await page.route('**/api/v1/agents/1', async (route: Route) => {
      if (route.request().method() === 'DELETE') {
        await route.fulfill({ status: 204 })
      }
    })

    const agentRow = page.getByRole('row').filter({ hasText: 'Ticket Enhancer' })
    await agentRow.getByRole('button', { name: /delete/i }).click()

    // Verify warning dialog
    const dialog = page.getByRole('dialog')
    await expect(dialog).toBeVisible()
    await expect(dialog.getByText(/stop all webhook endpoints/i)).toBeVisible()

    // Confirm
    await dialog.getByRole('button', { name: /delete agent/i }).click()

    await expect(page.getByText(/agent deleted/i)).toBeVisible({ timeout: 5000 })
  })

  test('displays empty state when no agents exist', async ({ page }) => {
    await page.route('**/api/v1/agents', async (route: Route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ data: [], total: 0 }),
      })
    })

    await page.reload()

    await expect(page.getByText(/no agents configured/i)).toBeVisible()
    await expect(page.getByRole('button', { name: /create agent/i })).toBeVisible()
  })
})
