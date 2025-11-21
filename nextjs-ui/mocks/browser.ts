/**
 * MSW Browser Worker Setup
 *
 * This file configures the Mock Service Worker for browser environments.
 * The worker intercepts network requests and returns mocked responses
 * based on the handlers defined in ./handlers.ts
 *
 * Note: This file uses runtime-only dynamic imports that webpack cannot analyze
 */

import { handlers } from './handlers'

/**
 * Start the MSW worker in development mode
 * Uses runtime-only dynamic import to prevent webpack from bundling MSW
 */
export async function startMSW() {
  if (typeof window === 'undefined') {
    return
  }

  try {
    // Use Function constructor for truly runtime-only import that webpack can't analyze
    // This prevents webpack from trying to resolve 'msw/browser' during build
    const importMSW = new Function('specifier', 'return import(specifier)')
    const { setupWorker } = await importMSW('msw/browser')
    const worker = setupWorker(...handlers)

    await worker.start({
      onUnhandledRequest: 'bypass', // Don't warn about unhandled requests
      serviceWorker: {
        url: '/mockServiceWorker.js',
      },
    })
    console.log('[MSW] Mock Service Worker started successfully')
  } catch (error) {
    console.error('[MSW] Failed to start Mock Service Worker:', error)
  }
}
