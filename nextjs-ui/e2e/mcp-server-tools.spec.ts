/**
 * MCP Server & Tool Discovery E2E Tests
 *
 * Tests MCP server CRUD, connection testing, and tool discovery
 * Following Playwright v1.51.0 best practices (2025)
 *
 * Story: 4-core-pages-configuration
 * AC-4: MCP Servers Page (/configuration/mcp-servers)
 */

import { test, expect, Page, Route } from '@playwright/test'

test.describe.configure({ mode: 'parallel' })

test.describe('MCP Server Management', () => {
  const mockMcpServers = [
    {
      id: 'mcp-1',
      name: 'Filesystem MCP',
      description: 'Read and write files',
      transport_type: 'stdio',
      command: 'npx',
      args: ['-y', '@modelcontextprotocol/server-filesystem', '/tmp'],
      env_vars: {},
      status: 'connected',
      tools_count: 12,
      last_connected: '2025-01-18T10:30:00Z',
      created_at: '2025-01-01T00:00:00Z',
    },
    {
      id: 'mcp-2',
      name: 'GitHub MCP',
      description: 'Interact with GitHub API',
      transport_type: 'sse',
      url: 'https://github-mcp.example.com',
      api_key: 'ghp_***************abc123',
      status: 'connected',
      tools_count: 8,
      last_connected: '2025-01-18T09:15:00Z',
      created_at: '2025-01-05T00:00:00Z',
    },
    {
      id: 'mcp-3',
      name: 'Database MCP',
      description: 'Query databases',
      transport_type: 'stdio',
      command: 'python',
      args: ['-m', 'mcp_server_db'],
      env_vars: { DB_HOST: 'localhost', DB_PORT: '5432' },
      status: 'disconnected',
      tools_count: 0,
      last_connected: null,
      created_at: '2025-01-10T00:00:00Z',
    },
  ]

  test.beforeEach(async ({ page }) => {
    // Mock MCP servers list
    await page.route('**/api/v1/mcp-servers', async (route: Route) => {
      if (route.request().method() === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ data: mockMcpServers, total: 3 }),
        })
      }
    })

    await page.goto('/dashboard/mcp-servers')
    await expect(page.getByRole('heading', { name: /mcp servers/i, level: 1 })).toBeVisible()
  })

  test('displays MCP servers in table format', async ({ page }) => {
    // Verify table headers
    await expect(page.getByRole('columnheader', { name: /server name/i })).toBeVisible()
    await expect(page.getByRole('columnheader', { name: /transport/i })).toBeVisible()
    await expect(page.getByRole('columnheader', { name: /status/i })).toBeVisible()
    await expect(page.getByRole('columnheader', { name: /tools/i })).toBeVisible()
    await expect(page.getByRole('columnheader', { name: /actions/i })).toBeVisible()

    // Verify server rows
    const filesystemRow = page.getByRole('row').filter({ hasText: 'Filesystem MCP' })
    await expect(filesystemRow).toBeVisible()
    await expect(filesystemRow.getByText('stdio')).toBeVisible()
    await expect(filesystemRow.getByText(/connected/i)).toBeVisible()
    await expect(filesystemRow.getByText('12')).toBeVisible() // tools count

    const githubRow = page.getByRole('row').filter({ hasText: 'GitHub MCP' })
    await expect(githubRow).toBeVisible()
    await expect(githubRow.getByText('sse')).toBeVisible()
    await expect(githubRow.getByText(/connected/i)).toBeVisible()
  })

  test('creates MCP server with stdio transport', async ({ page }) => {
    const newServer = {
      name: 'Brave Search MCP',
      description: 'Search the web using Brave',
      transport_type: 'stdio',
      command: 'npx',
      args: ['-y', '@modelcontextprotocol/server-brave-search'],
      env_vars: { BRAVE_API_KEY: 'BSA_abc123' },
    }

    // Mock test connection endpoint
    let testConnectionCalled = false
    await page.route('**/api/v1/mcp-servers/test-connection', async (route: Route) => {
      if (route.request().method() === 'POST') {
        testConnectionCalled = true
        await new Promise((resolve) => setTimeout(resolve, 1000))

        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            message: 'Connected successfully',
            tools_discovered: [
              { name: 'brave_search', description: 'Search using Brave' },
              { name: 'brave_local_search', description: 'Local search' },
            ],
          }),
        })
      }
    })

    // Mock POST MCP server
    await page.route('**/api/v1/mcp-servers', async (route: Route) => {
      if (route.request().method() === 'POST') {
        expect(testConnectionCalled).toBe(true)

        const payload = route.request().postDataJSON()
        await route.fulfill({
          status: 201,
          contentType: 'application/json',
          body: JSON.stringify({
            id: 'mcp-4',
            ...payload,
            status: 'connected',
            tools_count: 2,
            created_at: new Date().toISOString(),
          }),
        })
      }
    })

    // Click Add MCP Server
    await page.getByRole('button', { name: /add mcp server/i }).click()

    // Fill basic info
    await page.getByLabel(/server name/i).fill(newServer.name)
    await page.getByLabel(/description/i).fill(newServer.description)

    // Select transport type
    await page.getByLabel(/transport type/i).click()
    await page.getByRole('option', { name: /stdio/i }).click()

    // Verify stdio-specific fields appear
    await expect(page.getByLabel(/command/i)).toBeVisible()
    await expect(page.getByLabel(/arguments/i).or(page.getByLabel(/args/i))).toBeVisible()

    // Fill stdio fields
    await page.getByLabel(/command/i).fill(newServer.command)

    // Fill args (could be array input or text area)
    const argsInput = page.getByLabel(/arguments/i).or(page.getByLabel(/args/i))
    await argsInput.fill(newServer.args.join(' '))

    // Add environment variables
    await page.getByRole('button', { name: /add environment variable/i }).click()
    await page.getByLabel(/key/i).fill('BRAVE_API_KEY')
    await page.getByLabel(/value/i).fill('BSA_abc123')

    // Test Connection
    const testButton = page.getByRole('button', { name: /test connection/i })
    await testButton.click()

    // Verify loading state
    await expect(page.getByText(/testing connection/i)).toBeVisible()

    // Verify success with tools discovered
    await expect(page.getByText(/connected successfully/i)).toBeVisible({ timeout: 3000 })
    await expect(page.getByText(/2 tools discovered/i).or(page.getByText(/discovered 2 tools/i))).toBeVisible()

    // Verify tools list displayed
    await expect(page.getByText('brave_search')).toBeVisible()
    await expect(page.getByText('brave_local_search')).toBeVisible()

    // Create button should be enabled after successful test
    const createButton = page.getByRole('button', { name: /create server/i, exact: true })
    await expect(createButton).toBeEnabled()
    await createButton.click()

    // Verify success
    await expect(page.getByText(/mcp server created successfully/i)).toBeVisible({ timeout: 5000 })
  })

  test('creates MCP server with SSE transport', async ({ page }) => {
    const newServer = {
      name: 'Slack MCP',
      description: 'Interact with Slack',
      transport_type: 'sse',
      url: 'https://slack-mcp.example.com',
      api_key: 'xoxb-slack-token-123',
    }

    await page.route('**/api/v1/mcp-servers/test-connection', async (route: Route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          message: 'Connected successfully',
          tools_discovered: [
            { name: 'send_message', description: 'Send Slack message' },
            { name: 'list_channels', description: 'List channels' },
          ],
        }),
      })
    })

    await page.route('**/api/v1/mcp-servers', async (route: Route) => {
      if (route.request().method() === 'POST') {
        const payload = route.request().postDataJSON()
        await route.fulfill({
          status: 201,
          contentType: 'application/json',
          body: JSON.stringify({
            id: 'mcp-5',
            ...payload,
            status: 'connected',
            tools_count: 2,
            created_at: new Date().toISOString(),
          }),
        })
      }
    })

    await page.getByRole('button', { name: /add mcp server/i }).click()

    await page.getByLabel(/server name/i).fill(newServer.name)
    await page.getByLabel(/description/i).fill(newServer.description)

    // Select SSE transport
    await page.getByLabel(/transport type/i).click()
    await page.getByRole('option', { name: /sse/i }).click()

    // Verify SSE-specific fields appear
    await expect(page.getByLabel(/url/i)).toBeVisible()
    await expect(page.getByLabel(/api key/i)).toBeVisible()

    // Verify stdio fields are hidden
    await expect(page.getByLabel(/command/i)).not.toBeVisible()

    // Fill SSE fields
    await page.getByLabel(/url/i).fill(newServer.url)
    await page.getByLabel(/api key/i).fill(newServer.api_key)

    // Test and create
    await page.getByRole('button', { name: /test connection/i }).click()
    await expect(page.getByText(/connected successfully/i)).toBeVisible({ timeout: 3000 })

    await page.getByRole('button', { name: /create server/i, exact: true }).click()
    await expect(page.getByText(/mcp server created successfully/i)).toBeVisible({ timeout: 5000 })
  })

  test('handles test connection failures', async ({ page }) => {
    await page.route('**/api/v1/mcp-servers/test-connection', async (route: Route) => {
      await route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({
          success: false,
          error: 'Failed to connect: Connection timeout',
        }),
      })
    })

    await page.getByRole('button', { name: /add mcp server/i }).click()

    await page.getByLabel(/server name/i).fill('Test Server')
    await page.getByLabel(/transport type/i).click()
    await page.getByRole('option', { name: /stdio/i }).click()
    await page.getByLabel(/command/i).fill('invalid-command')

    await page.getByRole('button', { name: /test connection/i }).click()

    // Verify error message
    await expect(
      page.getByText(/connection timeout/i).or(page.getByText(/failed to connect/i))
    ).toBeVisible({ timeout: 3000 })

    // Create button should remain disabled
    await expect(page.getByRole('button', { name: /create server/i, exact: true })).toBeDisabled()
  })

  test('navigates to server detail with Tools tab', async ({ page }) => {
    const mockTools = [
      { name: 'read_file', description: 'Read file contents', schema: {} },
      { name: 'write_file', description: 'Write to file', schema: {} },
      { name: 'list_directory', description: 'List directory contents', schema: {} },
    ]

    // Mock server detail
    await page.route('**/api/v1/mcp-servers/mcp-1', async (route: Route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockMcpServers[0]),
      })
    })

    // Mock tools list
    await page.route('**/api/v1/mcp-servers/mcp-1/tools', async (route: Route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ tools: mockTools }),
      })
    })

    // Click on server name
    await page.getByText('Filesystem MCP').click()

    // Verify URL
    await expect(page).toHaveURL(/\/dashboard\/mcp-servers\/mcp-1/)

    // Verify tabs
    await expect(page.getByRole('tab', { name: /overview/i })).toBeVisible()
    await expect(page.getByRole('tab', { name: /tools/i })).toBeVisible()

    // Click Tools tab
    await page.getByRole('tab', { name: /tools/i }).click()

    // Verify tools displayed
    await expect(page.getByText('read_file')).toBeVisible()
    await expect(page.getByText('write_file')).toBeVisible()
    await expect(page.getByText('list_directory')).toBeVisible()
    await expect(page.getByText('Read file contents')).toBeVisible()

    // Verify Refresh Tools button
    await expect(page.getByRole('button', { name: /refresh tools/i })).toBeVisible()
  })

  test('refreshes tools list', async ({ page }) => {
    let refreshCount = 0
    const initialTools = [{ name: 'read_file', description: 'Read files', schema: {} }]
    const updatedTools = [
      { name: 'read_file', description: 'Read files', schema: {} },
      { name: 'write_file', description: 'Write files', schema: {} },
      { name: 'delete_file', description: 'Delete files', schema: {} },
    ]

    await page.route('**/api/v1/mcp-servers/mcp-1', async (route: Route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockMcpServers[0]),
      })
    })

    await page.route('**/api/v1/mcp-servers/mcp-1/tools', async (route: Route) => {
      refreshCount++
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          tools: refreshCount === 1 ? initialTools : updatedTools,
        }),
      })
    })

    await page.goto('/dashboard/mcp-servers/mcp-1')
    await page.getByRole('tab', { name: /tools/i }).click()

    // Verify initial tools
    await expect(page.getByText('read_file')).toBeVisible()
    await expect.soft(page.getByText('write_file')).not.toBeVisible()

    // Click Refresh
    await page.getByRole('button', { name: /refresh tools/i }).click()

    // Verify updated tools
    await expect(page.getByText('write_file')).toBeVisible({ timeout: 3000 })
    await expect(page.getByText('delete_file')).toBeVisible()
  })

  test('filters servers by status', async ({ page }) => {
    // Verify all servers visible initially
    await expect(page.getByText('Filesystem MCP')).toBeVisible()
    await expect(page.getByText('Database MCP')).toBeVisible()

    // Filter by connected
    const statusFilter = page.getByLabel(/filter by status/i).or(page.locator('select').filter({ hasText: /all/i }))
    await statusFilter.click()
    await page.getByRole('option', { name: /connected/i }).click()

    // Verify only connected servers shown
    await expect(page.getByText('Filesystem MCP')).toBeVisible()
    await expect.soft(page.getByText('Database MCP')).not.toBeVisible()

    // Filter by disconnected
    await statusFilter.click()
    await page.getByRole('option', { name: /disconnected/i }).click()

    await expect(page.getByText('Database MCP')).toBeVisible()
    await expect.soft(page.getByText('Filesystem MCP')).not.toBeVisible()
  })

  test('deletes MCP server with confirmation', async ({ page }) => {
    await page.route('**/api/v1/mcp-servers/mcp-1', async (route: Route) => {
      if (route.request().method() === 'DELETE') {
        await route.fulfill({ status: 204 })
      }
    })

    const serverRow = page.getByRole('row').filter({ hasText: 'Filesystem MCP' })
    await serverRow.getByRole('button', { name: /delete/i }).click()

    // Verify warning dialog
    const dialog = page.getByRole('dialog')
    await expect(dialog).toBeVisible()
    await expect(dialog.getByText(/delete filesystem mcp/i)).toBeVisible()
    await expect(dialog.getByText(/agents using tools from this server will fail/i).or(dialog.getByText(/cannot be undone/i))).toBeVisible()

    // Confirm
    await dialog.getByRole('button', { name: /delete server/i }).click()

    await expect(page.getByText(/mcp server deleted/i)).toBeVisible({ timeout: 5000 })
  })

  test('displays empty state when no servers exist', async ({ page }) => {
    await page.route('**/api/v1/mcp-servers', async (route: Route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ data: [], total: 0 }),
      })
    })

    await page.reload()

    await expect(page.getByText(/no mcp servers configured/i)).toBeVisible()
    await expect(page.getByText(/add your first mcp server/i)).toBeVisible()
    await expect(page.getByRole('button', { name: /add mcp server/i })).toBeVisible()
  })

  test('validates MCP server form fields', async ({ page }) => {
    await page.getByRole('button', { name: /add mcp server/i }).click()

    // Submit empty form
    await page.getByRole('button', { name: /test connection/i }).click()

    // Verify validation errors
    await expect(page.getByText(/server name is required/i).or(page.getByText(/name must be at least 3 characters/i))).toBeVisible()

    // Select stdio, verify command required
    await page.getByLabel(/transport type/i).click()
    await page.getByRole('option', { name: /stdio/i }).click()
    await page.getByRole('button', { name: /test connection/i }).click()

    await expect(page.getByText(/command is required/i)).toBeVisible()

    // Switch to SSE, verify URL required
    await page.getByLabel(/transport type/i).click()
    await page.getByRole('option', { name: /sse/i }).click()
    await page.getByRole('button', { name: /test connection/i }).click()

    await expect(page.getByText(/url is required/i)).toBeVisible()
  })

  test('displays status indicators correctly', async ({ page }) => {
    // Verify connected status (green/success badge)
    const filesystemRow = page.getByRole('row').filter({ hasText: 'Filesystem MCP' })
    const connectedBadge = filesystemRow.locator('.badge, .status-indicator').filter({ hasText: /connected/i })
    await expect(connectedBadge).toBeVisible()

    // Verify disconnected status (red/error badge)
    const dbRow = page.getByRole('row').filter({ hasText: 'Database MCP' })
    const disconnectedBadge = dbRow.locator('.badge, .status-indicator').filter({ hasText: /disconnected/i })
    await expect(disconnectedBadge).toBeVisible()
  })

  test('edits MCP server and re-tests connection', async ({ page }) => {
    await page.route('**/api/v1/mcp-servers/mcp-1', async (route: Route) => {
      if (route.request().method() === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(mockMcpServers[0]),
        })
      } else if (route.request().method() === 'PUT') {
        const payload = route.request().postDataJSON()
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ id: 'mcp-1', ...payload, updated_at: new Date().toISOString() }),
        })
      }
    })

    await page.route('**/api/v1/mcp-servers/test-connection', async (route: Route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          message: 'Connected successfully',
          tools_discovered: [{ name: 'new_tool', description: 'New tool' }],
        }),
      })
    })

    await page.goto('/dashboard/mcp-servers/mcp-1')

    // Click Edit
    await page.getByRole('button', { name: /edit/i }).click()

    // Update description
    const descInput = page.getByLabel(/description/i)
    await descInput.clear()
    await descInput.fill('Updated filesystem MCP server')

    // Re-test connection
    await page.getByRole('button', { name: /test connection/i }).click()
    await expect(page.getByText(/connected successfully/i)).toBeVisible({ timeout: 3000 })

    // Update server
    await page.getByRole('button', { name: /update server/i }).click()
    await expect(page.getByText(/mcp server updated successfully/i)).toBeVisible({ timeout: 5000 })
  })
})
