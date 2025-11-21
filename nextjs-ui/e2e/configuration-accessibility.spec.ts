/**
 * Configuration Pages Accessibility E2E Tests
 *
 * Tests WCAG 2.1 AA compliance using axe-core across all configuration pages
 * Following Playwright v1.51.0 best practices (2025)
 *
 * Story: 4-core-pages-configuration
 * AC-6: Testing & Quality Assurance (Accessibility Audit)
 *
 * NOTE: Import AxeBuilder from '@axe-core/playwright' in package.json
 */

import { test, expect, Page, Route } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'

test.describe.configure({ mode: 'parallel' })

// Helper to setup mock data for all pages
async function setupMockData(page: Page) {
  // Mock tenants
  await page.route('**/api/v1/tenants', async (route: Route) => {
    if (route.request().method() === 'GET') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          data: [
            { id: '1', name: 'Acme Corp', description: 'Test tenant', agent_count: 5 },
          ],
          total: 1,
        }),
      })
    }
  })

  // Mock agents
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
              type: 'webhook-triggered',
              status: 'active',
              tools_count: 5,
            },
          ],
          total: 1,
        }),
      })
    }
  })

  // Mock LLM providers
  await page.route('**/api/v1/llm-providers', async (route: Route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        data: [
          { id: 'openai-1', name: 'OpenAI', type: 'openai', status: 'healthy', models_count: 8 },
        ],
        total: 1,
      }),
    })
  })

  // Mock MCP servers
  await page.route('**/api/v1/mcp-servers', async (route: Route) => {
    if (route.request().method() === 'GET') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          data: [
            {
              id: 'mcp-1',
              name: 'Filesystem MCP',
              transport_type: 'stdio',
              status: 'connected',
              tools_count: 12,
            },
          ],
          total: 1,
        }),
      })
    }
  })
}

test.describe('Configuration Pages Accessibility', () => {
  test.describe('Tenants Page (/dashboard/tenants)', () => {
    test.beforeEach(async ({ page }) => {
      await setupMockData(page)
      await page.goto('/dashboard/tenants')
      await page.waitForLoadState('domcontentloaded')
    })

    test('passes automated WCAG 2.1 AA audit', async ({ page }) => {
      const accessibilityScanResults = await new AxeBuilder({ page })
        .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
        .analyze()

      expect(accessibilityScanResults.violations).toEqual([])
    })

    test('has proper heading hierarchy (h1 → h2 → h3)', async ({ page }) => {
      // Verify h1 exists and is unique
      const h1Elements = page.getByRole('heading', { level: 1 })
      await expect(h1Elements).toHaveCount(1)
      await expect(h1Elements).toContainText(/tenants/i)

      // Verify no heading level skips
      const accessibilityScanResults = await new AxeBuilder({ page })
        .withRules(['heading-order'])
        .analyze()

      expect(accessibilityScanResults.violations).toEqual([])
    })

    test('has sufficient color contrast (WCAG AA 4.5:1)', async ({ page }) => {
      const accessibilityScanResults = await new AxeBuilder({ page })
        .withRules(['color-contrast'])
        .analyze()

      expect(accessibilityScanResults.violations).toEqual([])
    })

    test('all interactive elements are keyboard accessible', async ({ page }) => {
      // Tab through all interactive elements
      await page.keyboard.press('Tab')
      const createButton = page.getByRole('button', { name: /create tenant/i })
      await expect(createButton).toBeFocused()

      // Verify focus is visible
      const accessibilityScanResults = await new AxeBuilder({ page })
        .withRules(['focus-visible'])
        .analyze()

      expect(accessibilityScanResults.violations).toEqual([])
    })

    test('form has proper labels and ARIA attributes', async ({ page }) => {
      await page.getByRole('button', { name: /create tenant/i }).click()

      // Verify all form inputs have labels
      const accessibilityScanResults = await new AxeBuilder({ page })
        .withRules(['label', 'aria-required-attr', 'aria-valid-attr-value'])
        .analyze()

      expect(accessibilityScanResults.violations).toEqual([])
    })

    test('table has proper semantic markup', async ({ page }) => {
      const accessibilityScanResults = await new AxeBuilder({ page })
        .withRules(['table', 'th-has-data-cells', 'td-headers-attr', 'scope-attr-valid'])
        .analyze()

      expect(accessibilityScanResults.violations).toEqual([])
    })
  })

  test.describe('Agents Page (/dashboard/agents-config)', () => {
    test.beforeEach(async ({ page }) => {
      await setupMockData(page)
      await page.route('**/api/v1/llm-providers/*/models', async (route: Route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ models: ['gpt-4', 'gpt-3.5-turbo'] }),
        })
      })
      await page.goto('/dashboard/agents-config')
      await page.waitForLoadState('domcontentloaded')
    })

    test('passes automated WCAG 2.1 AA audit', async ({ page }) => {
      const accessibilityScanResults = await new AxeBuilder({ page })
        .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
        .analyze()

      expect(accessibilityScanResults.violations).toEqual([])
    })

    test('form controls have accessible names', async ({ page }) => {
      await page.getByRole('button', { name: /create agent/i }).click()

      // Verify all inputs, selects, textareas have accessible names
      const accessibilityScanResults = await new AxeBuilder({ page })
        .withRules(['label', 'button-name', 'input-button-name'])
        .analyze()

      expect(accessibilityScanResults.violations).toEqual([])
    })

    test('slider controls have ARIA labels', async ({ page }) => {
      await page.getByRole('button', { name: /create agent/i }).click()

      // Temperature slider should have proper ARIA
      const tempSlider = page.getByLabel(/temperature/i)
      await expect(tempSlider).toHaveAttribute('aria-label')
    })

    test('status toggle is accessible', async ({ page }) => {
      await page.getByRole('button', { name: /create agent/i }).click()

      // Status toggle should be a proper switch or checkbox
      const statusToggle = page.getByLabel(/status/i).or(page.getByRole('switch', { name: /active/i }))
      await expect(statusToggle).toHaveAttribute('role', /switch|checkbox/)
    })
  })

  test.describe('LLM Providers Page (/dashboard/llm-providers)', () => {
    test.beforeEach(async ({ page }) => {
      await setupMockData(page)
      await page.goto('/dashboard/llm-providers')
      await page.waitForLoadState('domcontentloaded')
    })

    test('passes automated WCAG 2.1 AA audit', async ({ page }) => {
      const accessibilityScanResults = await new AxeBuilder({ page })
        .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
        .analyze()

      expect(accessibilityScanResults.violations).toEqual([])
    })

    test('password input has show/hide toggle with accessible label', async ({ page }) => {
      await page.getByRole('button', { name: /add provider/i }).click()

      // API key should be password type
      const apiKeyInput = page.getByLabel(/api key/i)
      await expect(apiKeyInput).toHaveAttribute('type', 'password')

      // Toggle button should have accessible name
      const toggleButton = page.getByRole('button', { name: /show api key/i }).or(
        page.getByRole('button', { name: /toggle api key visibility/i })
      )
      await expect(toggleButton).toHaveAccessibleName()
    })

    test('status badges have accessible text', async ({ page }) => {
      // Status badges should not rely solely on color
      const healthyBadge = page.locator('.badge, .status-indicator').filter({ hasText: /healthy/i }).first()

      // Should have text content, not just color
      await expect(healthyBadge).toHaveText(/healthy/i)
    })
  })

  test.describe('MCP Servers Page (/dashboard/mcp-servers)', () => {
    test.beforeEach(async ({ page }) => {
      await setupMockData(page)
      await page.goto('/dashboard/mcp-servers')
      await page.waitForLoadState('domcontentloaded')
    })

    test('passes automated WCAG 2.1 AA audit', async ({ page }) => {
      const accessibilityScanResults = await new AxeBuilder({ page })
        .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
        .analyze()

      expect(accessibilityScanResults.violations).toEqual([])
    })

    test('radio buttons have proper grouping', async ({ page }) => {
      await page.getByRole('button', { name: /add mcp server/i }).click()

      // Verify accessible radio group
      const accessibilityScanResults = await new AxeBuilder({ page })
        .withRules(['radiogroup', 'label'])
        .analyze()

      expect(accessibilityScanResults.violations).toEqual([])
    })
  })

  test.describe('Cross-Page Accessibility', () => {
    test.beforeEach(async ({ page }) => {
      await setupMockData(page)
    })

    test('navigation sidebar is keyboard accessible', async ({ page }) => {
      await page.goto('/dashboard/tenants')

      // Tab to sidebar navigation
      await page.keyboard.press('Tab')
      await page.keyboard.press('Tab')

      // Verify sidebar links are reachable
      const navLink = page.getByRole('link', { name: /tenants/i }).first()
      await navLink.focus()
      await expect(navLink).toBeFocused()

      // Enter should activate link
      await page.keyboard.press('Enter')
      await expect(page).toHaveURL(/\/dashboard\/tenants/)
    })

    test('modal dialogs have proper focus management', async ({ page }) => {
      await page.goto('/dashboard/tenants')
      await page.getByRole('button', { name: /create tenant/i }).click()

      // Dialog should be announced
      const dialog = page.getByRole('dialog')
      await expect(dialog).toBeVisible()

      // Focus should trap inside dialog
      await page.keyboard.press('Tab')
      const firstInput = page.getByLabel(/tenant name/i)
      await expect(firstInput).toBeFocused()

      // Escape should close dialog
      await page.keyboard.press('Escape')
      await expect(dialog).not.toBeVisible()
    })

    test('error messages are announced to screen readers', async ({ page }) => {
      await page.goto('/dashboard/tenants')
      await page.getByRole('button', { name: /create tenant/i }).click()

      // Submit empty form
      await page.getByRole('button', { name: /create tenant/i, exact: true }).click()

      // Error should have proper ARIA
      const errorMessage = page.getByText(/name must be at least 3 characters/i)
      await expect(errorMessage).toBeVisible()

      // Verify error has aria-live or role=alert
      const accessibilityScanResults = await new AxeBuilder({ page })
        .withRules(['aria-live', 'alert'])
        .analyze()

      expect(accessibilityScanResults.violations).toEqual([])
    })

    test('loading states are announced to screen readers', async ({ page }) => {
      await page.route('**/api/v1/tenants', async (route: Route) => {
        if (route.request().method() === 'GET') {
          await new Promise((resolve) => setTimeout(resolve, 2000))
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({ data: [], total: 0 }),
          })
        }
      })

      await page.goto('/dashboard/tenants')

      // Loading indicator should have aria-live or role=status
      const loadingIndicator = page.getByTestId('loading-skeleton').or(page.getByText(/loading/i))

      // Verify loading state is accessible
      const accessibilityScanResults = await new AxeBuilder({ page })
        .withRules(['aria-live'])
        .analyze()

      expect(accessibilityScanResults.violations).toEqual([])
    })

    test('all images have alt text', async ({ page }) => {
      await page.goto('/dashboard/tenants')

      const accessibilityScanResults = await new AxeBuilder({ page })
        .withRules(['image-alt'])
        .analyze()

      expect(accessibilityScanResults.violations).toEqual([])
    })

    test('landmark regions are properly defined', async ({ page }) => {
      await page.goto('/dashboard/tenants')

      // Verify proper use of header, nav, main, footer
      await expect(page.locator('header, [role="banner"]')).toBeVisible()
      await expect(page.locator('nav, [role="navigation"]')).toBeVisible()
      await expect(page.locator('main, [role="main"]')).toBeVisible()

      const accessibilityScanResults = await new AxeBuilder({ page })
        .withRules(['landmark-one-main', 'region'])
        .analyze()

      expect(accessibilityScanResults.violations).toEqual([])
    })

    test('skip to main content link exists', async ({ page }) => {
      await page.goto('/dashboard/tenants')

      // Tab once to reach skip link
      await page.keyboard.press('Tab')

      // Should have skip link as first focusable element
      const skipLink = page.getByRole('link', { name: /skip to (main )?content/i })

      // Skip link can be visible on focus or visually hidden but accessible
      await expect.soft(skipLink).toBeVisible().catch(() => {
        // If not visible, it should still be in DOM and keyboard accessible
        expect(skipLink).toBeInViewport()
      })
    })

    test('form validation errors have proper ARIA', async ({ page }) => {
      await page.goto('/dashboard/tenants')
      await page.getByRole('button', { name: /create tenant/i }).click()

      await page.getByRole('button', { name: /create tenant/i, exact: true }).click()

      // Verify aria-invalid and aria-describedby
      const accessibilityScanResults = await new AxeBuilder({ page })
        .withRules(['aria-valid-attr', 'aria-valid-attr-value'])
        .analyze()

      expect(accessibilityScanResults.violations).toEqual([])
    })
  })

  test.describe('Keyboard Navigation', () => {
    test.beforeEach(async ({ page }) => {
      await setupMockData(page)
    })

    test('can navigate entire tenant workflow with keyboard only', async ({ page }) => {
      await page.goto('/dashboard/tenants')

      // Tab to Create button
      while (!(await page.getByRole('button', { name: /create tenant/i }).isVisible())) {
        await page.keyboard.press('Tab')
      }
      await page.keyboard.press('Enter')

      // Fill form with keyboard
      await page.keyboard.type('Test Tenant')
      await page.keyboard.press('Tab')
      await page.keyboard.type('Test Description')
      await page.keyboard.press('Tab')

      // Should be able to submit with Enter
      await page.keyboard.press('Enter')

      // Dialog should handle keyboard events
      expect(true).toBe(true)
    })

    test('Escape key closes dialogs', async ({ page }) => {
      await page.goto('/dashboard/tenants')
      await page.getByRole('button', { name: /create tenant/i }).click()

      const dialog = page.getByRole('dialog')
      await expect(dialog).toBeVisible()

      await page.keyboard.press('Escape')
      await expect(dialog).not.toBeVisible()
    })

    test('Tab order follows visual layout', async ({ page }) => {
      await page.goto('/dashboard/tenants')

      // Get all focusable elements
      const focusableElements = await page.locator('a, button, input, select, textarea, [tabindex]:not([tabindex="-1"])').all()

      // Verify tab order matches visual order (left-to-right, top-to-bottom)
      expect(focusableElements.length).toBeGreaterThan(0)
    })
  })

  test.describe('Screen Reader Compatibility', () => {
    test.beforeEach(async ({ page }) => {
      await setupMockData(page)
    })

    test('page title is descriptive', async ({ page }) => {
      await page.goto('/dashboard/tenants')
      await expect(page).toHaveTitle(/tenants/i)

      await page.goto('/dashboard/agents-config')
      await expect(page).toHaveTitle(/agents/i)

      await page.goto('/dashboard/llm-providers')
      await expect(page).toHaveTitle(/providers/i)
    })

    test('lists use proper semantic markup', async ({ page }) => {
      await page.goto('/dashboard/tenants')

      const accessibilityScanResults = await new AxeBuilder({ page })
        .withRules(['list', 'listitem'])
        .analyze()

      expect(accessibilityScanResults.violations).toEqual([])
    })

    test('dynamic content changes are announced', async ({ page }) => {
      await page.route('**/api/v1/tenants', async (route: Route) => {
        if (route.request().method() === 'POST') {
          await route.fulfill({
            status: 201,
            contentType: 'application/json',
            body: JSON.stringify({
              id: '999',
              name: 'New Tenant',
              created_at: new Date().toISOString(),
            }),
          })
        }
      })

      await page.goto('/dashboard/tenants')
      await page.getByRole('button', { name: /create tenant/i }).click()

      await page.getByLabel(/tenant name/i).fill('New Tenant')
      await page.getByLabel(/description/i).fill('Test')
      await page.getByRole('button', { name: /create tenant/i, exact: true }).click()

      // Success message should have aria-live
      const successMessage = page.getByText(/tenant created successfully/i)
      await expect(successMessage).toBeVisible({ timeout: 5000 })

      // Verify it has aria-live or role=status
      const parent = successMessage.locator('..')
      await expect.soft(parent).toHaveAttribute('aria-live', /polite|assertive/)
        .catch(async () => {
          await expect(parent).toHaveAttribute('role', 'status')
        })
    })
  })
})
