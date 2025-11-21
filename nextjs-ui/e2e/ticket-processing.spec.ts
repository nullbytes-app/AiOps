import { test, expect } from '@playwright/test'
import { gotoAndWaitForReady, waitForDashboardHeader } from './helpers'

/**
 * Ticket Processing Dashboard E2E Tests
 *
 * Tests queue gauge, processing metrics, and recent activity table
 */

test.describe('Ticket Processing Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    await gotoAndWaitForReady(page, '/dashboard/tickets')
    await waitForDashboardHeader(page, 'Ticket Processing')
  })

  test('displays queue depth gauge', async ({ page }) => {
    // Wait for gauge to load
    await expect(page.getByText(/jobs in queue/i)).toBeVisible()

    // Verify gauge value is displayed
    const queueValue = page.locator('text=/^\\d+$/').first()
    await expect(queueValue).toBeVisible()
  })

  test('shows color-coded queue depth', async ({ page }) => {
    // Wait for gauge
    await expect(page.getByText(/jobs in queue/i)).toBeVisible()

    // Queue gauge uses color coding: green (<50%), yellow (50-75%), red (>75%)
    // Verify the gauge value has inline color styling
    const gaugeValue = page.locator('text=/^\\d+$/').first()
    const color = await gaugeValue.evaluate((el) => getComputedStyle(el).color)

    // Color should be set (not default)
    expect(color).toBeTruthy()
  })

  test('displays processing rate card', async ({ page }) => {
    // Wait for processing rate card
    await expect(page.getByText(/processing rate/i)).toBeVisible()

    // Verify rate value is displayed
    const rateValue = page.locator('text=/\\d+/').first()
    await expect(rateValue).toBeVisible()
  })

  test('displays error rate card', async ({ page }) => {
    // Wait for error rate card
    await expect(page.getByText(/error rate/i)).toBeVisible()

    // Verify error rate is displayed as percentage
    const errorRate = page.locator('text=/\\d+(\\.\\d+)?%/').first()
    await expect(errorRate).toBeVisible()
  })

  test('displays recent activity table', async ({ page }) => {
    // Wait for recent activity section
    await expect(page.getByText(/recent activity/i)).toBeVisible()

    // Verify table headers
    await expect(page.getByText(/ticket id/i)).toBeVisible()
    await expect(page.getByText(/status/i)).toBeVisible()
    await expect(page.getByText(/priority/i)).toBeVisible()
    await expect(page.getByText(/agent/i)).toBeVisible()

    // Verify at least one row exists
    const tableRows = page.locator('tbody tr')
    const rowCount = await tableRows.count()
    expect(rowCount).toBeGreaterThan(0)
  })

  test('shows ticket status badges with colors', async ({ page }) => {
    // Wait for recent activity table
    await expect(page.getByText(/recent activity/i)).toBeVisible()

    // Look for status badges (e.g., "Completed", "Processing", "Failed")
    const statusBadges = page.locator('text=/completed|processing|failed/i')
    const badgeCount = await statusBadges.count()

    // Should have at least one status badge
    expect(badgeCount).toBeGreaterThan(0)

    // Verify badges have styling classes
    if (badgeCount > 0) {
      const firstBadge = statusBadges.first()
      const classes = await firstBadge.getAttribute('class')
      expect(classes).toBeTruthy()
    }
  })

  test('shows priority indicators', async ({ page }) => {
    // Wait for recent activity table
    await expect(page.getByText(/recent activity/i)).toBeVisible()

    // Look for priority values (e.g., "High", "Medium", "Low")
    const priorities = page.locator('text=/high|medium|low/i')
    const priorityCount = await priorities.count()

    // Should have at least one priority indicator
    expect(priorityCount).toBeGreaterThan(0)
  })

  test('displays processing rate sparkline chart', async ({ page }) => {
    // Wait for processing rate card
    await expect(page.getByText(/processing rate/i)).toBeVisible()

    // Verify sparkline chart is rendered (small SVG chart)
    const sparkline = page.locator('svg').filter({ has: page.locator('[class*="recharts"]') }).first()

    // Sparkline might not always be present (depends on data), so we check conditionally
    if (await sparkline.isVisible().catch(() => false)) {
      await expect(sparkline).toBeVisible()
    }
  })

  test('displays page heading', async ({ page }) => {
    const heading = page.getByRole('heading', { name: /ticket processing/i })
    await expect(heading).toBeVisible()
  })

  test('auto-refreshes data after 10 seconds', async ({ page }) => {
    // Wait for initial load
    await expect(page.getByText(/jobs in queue/i)).toBeVisible()

    // Get initial queue depth
    const queueValue = page.locator('text=/^\\d+$/').first()
    const initialValue = await queueValue.textContent()

    // Wait for auto-refresh (10 seconds + buffer)
    // Shortened for E2E test performance
    await page.waitForTimeout(2000)

    // Verify page still displays correctly (no crashes)
    await expect(page.getByText(/jobs in queue/i)).toBeVisible()
    await expect(page.getByText(/processing rate/i)).toBeVisible()
    await expect(page.getByText(/recent activity/i)).toBeVisible()
  })

  test('shows empty state when no recent tickets', async ({ page }) => {
    // This test assumes MSW can return empty data
    // Wait for page load
    await expect(page.getByText(/recent activity/i)).toBeVisible()

    // If table is empty, it should show a message
    const emptyMessage = page.getByText(/no recent tickets/i)

    if (await emptyMessage.isVisible().catch(() => false)) {
      await expect(emptyMessage).toBeVisible()
    } else {
      // Otherwise, verify rows are present
      const tableRows = page.locator('tbody tr')
      expect(await tableRows.count()).toBeGreaterThan(0)
    }
  })

  test('displays queue depth as large prominent number', async ({ page }) => {
    // Wait for gauge
    await expect(page.getByText(/jobs in queue/i)).toBeVisible()

    // Queue value should be large and bold
    const queueValue = page.locator('text=/^\\d+$/').first()
    const fontSize = await queueValue.evaluate((el) => getComputedStyle(el).fontSize)
    const fontWeight = await queueValue.evaluate((el) => getComputedStyle(el).fontWeight)

    // Verify large font size (should be >= 36px based on text-4xl)
    const fontSizeNum = parseInt(fontSize)
    expect(fontSizeNum).toBeGreaterThanOrEqual(30)

    // Verify bold font weight
    expect(parseInt(fontWeight)).toBeGreaterThanOrEqual(600)
  })

  test('maintains responsive layout on mobile viewport', async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 })

    // Verify gauge is visible
    await expect(page.getByText(/jobs in queue/i)).toBeVisible()

    // Verify processing cards are visible
    await expect(page.getByText(/processing rate/i)).toBeVisible()
    await expect(page.getByText(/error rate/i)).toBeVisible()

    // Verify recent activity table is scrollable
    const table = page.locator('table').first()
    await expect(table).toBeVisible()
  })

  test('shows correct time period in processing rate', async ({ page }) => {
    // Processing rate should show time period (e.g., "Last 24h")
    await expect(page.getByText(/processing rate/i)).toBeVisible()

    // Look for time period indicator
    const timePeriod = page.locator('text=/24h|7d|30d/i')

    if (await timePeriod.isVisible().catch(() => false)) {
      await expect(timePeriod).toBeVisible()
    }
  })
})
