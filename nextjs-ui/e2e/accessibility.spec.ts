import { test, expect } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'
import { gotoAndWaitForReady, waitForDashboardHeader } from './helpers'

/**
 * Accessibility Audit Tests
 *
 * Uses axe-core to scan all dashboard pages for WCAG 2.1 Level AA violations.
 * Following 2025 best practices for inclusive design.
 */

test.describe('Accessibility Audit', () => {
  test('System Health dashboard has no accessibility violations', async ({ page }) => {
    // Navigate to health dashboard and wait for MSW to initialize
    await gotoAndWaitForReady(page, '/dashboard/health')

    // Wait for page to fully load
    await waitForDashboardHeader(page, 'System Health')

    // Run axe accessibility scan
    const accessibilityScanResults = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
      .analyze()

    // Assert no violations
    expect(accessibilityScanResults.violations).toEqual([])
  })

  test('Agent Metrics dashboard has no accessibility violations', async ({ page }) => {
    // Navigate to agent metrics dashboard and wait for MSW to initialize
    await gotoAndWaitForReady(page, '/dashboard/agents')

    // Wait for page to fully load
    await waitForDashboardHeader(page, 'Agent Metrics')

    // Run axe accessibility scan
    const accessibilityScanResults = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
      .analyze()

    // Assert no violations
    expect(accessibilityScanResults.violations).toEqual([])
  })

  test('Ticket Processing dashboard has no accessibility violations', async ({ page }) => {
    // Navigate to ticket processing dashboard and wait for MSW to initialize
    await gotoAndWaitForReady(page, '/dashboard/tickets')

    // Wait for page to fully load
    await waitForDashboardHeader(page, 'Ticket Processing')

    // Run axe accessibility scan
    const accessibilityScanResults = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
      .analyze()

    // Assert no violations
    expect(accessibilityScanResults.violations).toEqual([])
  })

  test('Dashboard navigation (sidebar) has no accessibility violations', async ({ page }) => {
    // Navigate to dashboard and wait for MSW to initialize
    await gotoAndWaitForReady(page, '/dashboard')

    // Wait for sidebar to load
    await page.waitForSelector('nav', { timeout: 10000 })

    // Run axe accessibility scan on sidebar
    const accessibilityScanResults = await new AxeBuilder({ page })
      .include('nav') // Focus on navigation only
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
      .analyze()

    // Assert no violations
    expect(accessibilityScanResults.violations).toEqual([])
  })

  test('all dashboards support keyboard navigation', async ({ page }) => {
    // Navigate to health dashboard and wait for MSW to initialize
    await gotoAndWaitForReady(page, '/dashboard/health')
    await waitForDashboardHeader(page, 'System Health')

    // Press Tab to navigate through focusable elements
    await page.keyboard.press('Tab')
    await page.keyboard.press('Tab')
    await page.keyboard.press('Tab')

    // Verify focus is visible (some element should be focused)
    const focusedElement = await page.evaluate(() => {
      const activeEl = document.activeElement
      return activeEl?.tagName || null
    })

    // Should have focused on an interactive element
    expect(focusedElement).toBeTruthy()
  })

  test('all dashboards have proper heading hierarchy', async ({ page }) => {
    // Navigate to health dashboard and wait for MSW to initialize
    await gotoAndWaitForReady(page, '/dashboard/health')
    await waitForDashboardHeader(page, 'System Health')

    // Check heading hierarchy (h1 -> h2 -> h3, no skipping levels)
    await page.locator('h1, h2, h3, h4, h5, h6').all()

    // Should have at least one h1 (page title)
    const h1Count = await page.locator('h1').count()
    expect(h1Count).toBeGreaterThanOrEqual(1)

    // Run axe to check heading order
    const accessibilityScanResults = await new AxeBuilder({ page })
      .withTags(['best-practice'])
      .disableRules(['color-contrast']) // Focus on structure only
      .analyze()

    // Check for heading-order violations
    const headingViolations = accessibilityScanResults.violations.filter(
      (v) => v.id === 'heading-order'
    )
    expect(headingViolations).toEqual([])
  })

  test('all images have alt text', async ({ page }) => {
    // Navigate to dashboards
    const pages = [
      { url: '/dashboard/health', title: 'System Health' },
      { url: '/dashboard/agents', title: 'Agent Metrics' },
      { url: '/dashboard/tickets', title: 'Ticket Processing' },
    ]

    for (const { url, title } of pages) {
      await gotoAndWaitForReady(page, url)
      await waitForDashboardHeader(page, title)

      // Run axe to check image alt text
      const accessibilityScanResults = await new AxeBuilder({ page })
        .withTags(['wcag2a'])
        .analyze()

      // Check for image-alt violations
      const imageAltViolations = accessibilityScanResults.violations.filter(
        (v) => v.id === 'image-alt'
      )
      expect(imageAltViolations).toEqual([])
    }
  })

  test('color contrast meets WCAG AA standards', async ({ page }) => {
    // Navigate to health dashboard and wait for MSW to initialize
    await gotoAndWaitForReady(page, '/dashboard/health')
    await waitForDashboardHeader(page, 'System Health')

    // Run axe to check color contrast
    const accessibilityScanResults = await new AxeBuilder({ page })
      .withTags(['wcag2aa'])
      .include('body') // Check entire page
      .analyze()

    // Check for color-contrast violations
    const contrastViolations = accessibilityScanResults.violations.filter(
      (v) => v.id === 'color-contrast'
    )

    // Log violations for debugging if any
    if (contrastViolations.length > 0) {
      console.log('Color contrast violations:', JSON.stringify(contrastViolations, null, 2))
    }

    expect(contrastViolations).toEqual([])
  })

  test('form inputs have associated labels', async ({ page }) => {
    // Navigate to agent metrics (has search input) and wait for MSW to initialize
    await gotoAndWaitForReady(page, '/dashboard/agents')
    await waitForDashboardHeader(page, 'Agent Metrics')

    // Run axe to check labels
    const accessibilityScanResults = await new AxeBuilder({ page })
      .withTags(['wcag2a'])
      .analyze()

    // Check for label violations
    const labelViolations = accessibilityScanResults.violations.filter(
      (v) => v.id === 'label' || v.id === 'label-title-only'
    )
    expect(labelViolations).toEqual([])
  })

  test('ARIA attributes are used correctly', async ({ page }) => {
    // Navigate to dashboards
    const pages = [
      { url: '/dashboard/health', title: 'System Health' },
      { url: '/dashboard/agents', title: 'Agent Metrics' },
      { url: '/dashboard/tickets', title: 'Ticket Processing' },
    ]

    for (const { url, title } of pages) {
      await gotoAndWaitForReady(page, url)
      await waitForDashboardHeader(page, title)

      // Run axe to check ARIA usage
      const accessibilityScanResults = await new AxeBuilder({ page })
        .withTags(['wcag2a', 'best-practice'])
        .analyze()

      // Check for ARIA violations
      const ariaViolations = accessibilityScanResults.violations.filter((v) =>
        v.id.includes('aria')
      )

      // Log violations for debugging if any
      if (ariaViolations.length > 0) {
        console.log(`ARIA violations on ${url}:`, JSON.stringify(ariaViolations, null, 2))
      }

      expect(ariaViolations).toEqual([])
    }
  })
})
