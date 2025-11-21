/**
 * E2E Test Helpers
 *
 * Common utilities for Playwright E2E tests
 * Uses Playwright route mocking instead of MSW for E2E tests
 */

import { Page, expect, Route } from '@playwright/test'

/**
 * Setup API mocks using Playwright's route interception
 * This replaces MSW for E2E testing
 */
export async function setupAPIMocks(page: Page) {
  // Mock health status endpoint - matches backend URL (localhost:8000)
  await page.route('**/api/v1/health', async (route: Route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        api: { status: 'healthy', response_time_ms: 12, uptime: 99.9 },
        workers: { status: 'healthy', response_time_ms: 8, details: { active_workers: 5 } },
        database: { status: 'healthy', response_time_ms: 15, uptime: 99.99 },
        redis: { status: 'healthy', response_time_ms: 5, uptime: 99.95 },
        timestamp: new Date().toISOString(),
      }),
    })
  })

  // Mock agent metrics endpoint - matches AgentMetrics interface
  await page.route('**/api/v1/metrics/agents**', async (route: Route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        total_executions: 1234,
        successful_executions: 1168,
        failed_executions: 66,
        total_cost: 39.35,
        hourly_breakdown: Array.from({ length: 24 }, (_, i) => ({
          hour: new Date(Date.now() - (23 - i) * 60 * 60 * 1000).toISOString(),
          success_count: Math.floor(Math.random() * 90) + 15,
          failure_count: Math.floor(Math.random() * 10) + 1,
        })),
        agent_breakdown: [
          { agent_name: 'Ticket Enhancer', total_runs: 523, success_rate: 96.2, avg_latency_ms: 245, total_cost: 12.45 },
          { agent_name: 'Code Reviewer', total_runs: 412, success_rate: 92.8, avg_latency_ms: 312, total_cost: 18.23 },
          { agent_name: 'Documentation Generator', total_runs: 299, success_rate: 94.1, avg_latency_ms: 189, total_cost: 8.67 },
        ],
      }),
    })
  })

  // Mock ticket/queue metrics endpoint - matches TicketMetrics interface
  await page.route('**/api/v1/metrics/queue', async (route: Route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        queue_depth: 42,
        processing_rate_per_hour: 87,
        error_rate_percentage: 2.3,
        recent_tickets: [
          { ticket_id: 'TKT-001', status: 'success', processing_time_ms: 1245, timestamp: new Date().toISOString() },
          { ticket_id: 'TKT-002', status: 'pending', processing_time_ms: 0, timestamp: new Date().toISOString() },
          { ticket_id: 'TKT-003', status: 'success', processing_time_ms: 892, timestamp: new Date().toISOString() },
        ],
      }),
    })
  })

  // Mock agents endpoints
  await page.route('**/api/v1/agents', async (route: Route) => {
    if (route.request().method() === 'GET') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          data: [
            {
              id: '1',
              name: 'Ticket Enhancer',
              type: 'Webhook-Triggered',
              status: 'active',
              tools_count: 5,
              last_run: '2025-01-18T10:30:00Z',
            },
            {
              id: '2',
              name: 'Context Gatherer',
              type: 'Task-Based',
              status: 'inactive',
              tools_count: 3,
              last_run: '2025-01-17T15:20:00Z',
            },
          ],
          total: 2,
        }),
      })
    } else {
      await route.continue()
    }
  })

  await page.route('**/api/v1/agents/**', async (route: Route) => {
    const url = route.request().url()
    if (url.includes('/agents/1')) {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: '1',
          name: 'Ticket Enhancer',
          type: 'Webhook-Triggered',
          status: 'active',
          system_prompt: 'You are a helpful ticket enhancement agent.',
          llm_config: { model: 'gpt-4', temperature: 0.7 },
          tools: [],
        }),
      })
    } else {
      await route.continue()
    }
  })

  // Mock tenants endpoints
  await page.route('**/api/v1/tenants**', async (route: Route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        data: [
          { id: '1', name: 'Acme Corp', description: 'Main tenant', agent_count: 5 },
          { id: '2', name: 'TechStart Inc', description: 'Startup tenant', agent_count: 3 },
        ],
        total: 2,
      }),
    })
  })

  // Mock LLM providers endpoints
  await page.route('**/api/v1/llm-providers**', async (route: Route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        data: [
          {
            id: '1',
            name: 'OpenAI Production',
            type: 'openai',
            model_count: 15,
            status: 'healthy',
          },
          {
            id: '2',
            name: 'Anthropic',
            type: 'anthropic',
            model_count: 8,
            status: 'healthy',
          },
        ],
      }),
    })
  })

  // Mock MCP servers endpoints
  await page.route('**/api/v1/mcp-servers**', async (route: Route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        data: [
          {
            id: '1',
            name: 'Filesystem Server',
            type: 'stdio',
            status: 'healthy',
            tools_count: 8,
          },
          {
            id: '2',
            name: 'GitHub MCP',
            type: 'HTTP',
            status: 'healthy',
            tools_count: 12,
          },
        ],
      }),
    })
  })

  // Mock tools endpoints
  await page.route('**/api/v1/tools**', async (route: Route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        tools: [
          { id: '1', name: 'search', description: 'Search the web' },
          { id: '2', name: 'calculate', description: 'Perform calculations' },
        ],
      }),
    })
  })

  // Mock plugins endpoints
  await page.route('**/api/v1/plugins**', async (route: Route) => {
    const url = route.request().url()
    if (url.includes('/logs')) {
      // Plugin logs endpoint
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          logs: [
            {
              id: '1',
              plugin_id: '1',
              timestamp: '2025-01-18T10:00:00Z',
              status: 'success',
              records_synced: 45,
              duration_ms: 234,
            },
          ],
        }),
      })
    } else if (url.match(/\/plugins\/\d+$/)) {
      // Plugin detail endpoint
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          plugin: {
            id: '1',
            name: 'ServiceDesk Plus',
            type: 'webhook',
            status: 'active',
            last_sync: '2025-01-18T10:00:00Z',
            sync_frequency: '5min',
            config: {
              webhook: {
                endpoint_url: 'http://localhost:3001/api/v1/webhooks/plugins/1',
                hmac_secret: 'secret123',
              },
            },
            created_at: '2025-01-15T08:00:00Z',
            updated_at: '2025-01-18T10:00:00Z',
            sync_logs: [],
          },
        }),
      })
    } else {
      // Plugin list endpoint
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          plugins: [
            {
              id: '1',
              name: 'ServiceDesk Plus',
              type: 'webhook',
              status: 'active',
              last_sync: '2025-01-18T10:00:00Z',
              sync_frequency: '5min',
              config: {},
              created_at: '2025-01-15T08:00:00Z',
              updated_at: '2025-01-18T10:00:00Z',
            },
          ],
        }),
      })
    }
  })

  // Mock executions endpoints
  await page.route('**/api/v1/executions**', async (route: Route) => {
    const url = route.request().url()
    if (url.includes('/export')) {
      // Export endpoint
      await route.fulfill({
        status: 200,
        contentType: 'text/csv',
        body: 'id,agent,status\n1,Ticket Enhancer,success',
      })
    } else if (url.match(/\/executions\/\d+$/)) {
      // Execution detail endpoint
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: '1',
          agent_id: '1',
          agent_name: 'Ticket Enhancer',
          status: 'success',
          started_at: '2025-01-18T10:00:00Z',
          completed_at: '2025-01-18T10:02:00Z',
          input_data: { message: 'Test' },
          output_data: { result: 'Success' },
          error: null,
          metrics: { duration_ms: 2000, tokens_used: 150, cost: 0.05 },
        }),
      })
    } else {
      // Execution list endpoint
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          executions: [
            {
              id: '1',
              agent_name: 'Ticket Enhancer',
              status: 'success',
              started_at: '2025-01-18T10:00:00Z',
              duration_ms: 2000,
              cost: 0.05,
            },
          ],
          total: 1,
          page: 1,
          page_size: 20,
        }),
      })
    }
  })

  // Mock prompts endpoints
  await page.route('**/api/v1/prompts**', async (route: Route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([
        {
          id: '1',
          name: 'ticket_enhancer',
          content: 'You are a helpful ticket enhancement agent.',
          variables: ['ticket_id', 'description'],
          created_at: '2025-01-15T08:00:00Z',
          updated_at: '2025-01-18T10:00:00Z',
        },
      ]),
    })
  })

  // Mock audit endpoints
  await page.route('**/api/v1/audit/auth**', async (route: Route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        events: [],
        total: 0,
        page: 1,
        page_size: 20,
      }),
    })
  })

  await page.route('**/api/v1/audit/general**', async (route: Route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        events: [],
        total: 0,
        page: 1,
        page_size: 20,
      }),
    })
  })

  // Mock agent options endpoint (used by executions page)
  await page.route('**/api/v1/agents/options', async (route: Route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([
        { id: '1', name: 'Ticket Enhancer' },
        { id: '2', name: 'Context Gatherer' },
      ]),
    })
  })
}

/**
 * Navigate to a page and wait for it to be fully loaded
 * Sets up API mocks before navigation
 *
 * BEST PRACTICE: Avoids networkidle (unreliable for SPAs) in favor of:
 * 1. domcontentloaded - wait for DOM to be ready
 * 2. Web-first assertions in tests for specific elements
 *
 * Reference: https://playwright.dev/docs/best-practices
 */
export async function gotoAndWaitForReady(page: Page, url: string) {
  // Setup API mocks before navigation
  await setupAPIMocks(page)

  // Navigate to the page with 'domcontentloaded' strategy
  // This is more reliable than 'networkidle' for React/Next.js apps
  await page.goto(url, { waitUntil: 'domcontentloaded' })

  // Wait for React hydration to complete
  // Next.js 14 App Router doesn't use #__next, check body instead
  await expect(page.locator('body')).toBeVisible({ timeout: 5000 })

  // Additional wait for React Query providers to initialize
  await page.waitForTimeout(500)
}

/**
 * Wait for MSW-specific loading (now a no-op since we disabled MSW)
 * Kept for backwards compatibility with existing tests
 */
export async function waitForMSWReady(page: Page) {
  // MSW is disabled in E2E tests
  // Wait for React app to be ready instead of networkidle (unreliable for SPAs)
  await expect(page.locator('body')).toBeVisible({ timeout: 5000 })
  await page.waitForTimeout(300)
}

/**
 * Wait for dashboard header to be visible
 * This indicates the page has fully rendered
 */
export async function waitForDashboardHeader(page: Page, headerText: string) {
  await expect(page.getByRole('heading', { name: new RegExp(headerText, 'i'), level: 1 })).toBeVisible({
    timeout: 10000,
  })
}
