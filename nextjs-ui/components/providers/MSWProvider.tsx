'use client'

/**
 * MSW Provider Component
 *
 * This provider conditionally initializes the Mock Service Worker
 * in development mode to intercept and mock API requests.
 *
 * Features:
 * - Only runs in browser (client-side)
 * - Only initializes in development mode
 * - Shows loading state while worker initializes
 * - Handles initialization errors gracefully
 */

import { useEffect, useState } from 'react'

export function MSWProvider({ children }: { children: React.ReactNode }) {
  const [mswReady, setMswReady] = useState(
    // In production, SSR, or E2E tests, MSW is not needed
    () =>
      process.env.NODE_ENV !== 'development' ||
      typeof window === 'undefined' ||
      process.env.NEXT_PUBLIC_E2E_TEST === 'true'
  )

  useEffect(() => {
    // Skip MSW initialization in production, SSR, or E2E tests
    if (
      process.env.NODE_ENV !== 'development' ||
      typeof window === 'undefined' ||
      process.env.NEXT_PUBLIC_E2E_TEST === 'true'
    ) {
      return
    }

    // Dynamically import MSW worker to avoid including it in production bundle
    async function initMSW() {
      try {
        const { startMSW } = await import('@/mocks/browser')
        await startMSW()
        setMswReady(true)
      } catch (error) {
        console.error('[MSW] Failed to initialize:', error)
        // Set ready anyway to not block the app
        setMswReady(true)
      }
    }

    initMSW()
  }, [])

  // Show loading state while MSW initializes in development
  if (!mswReady) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-4 border-accent-blue/20 border-t-accent-blue mx-auto mb-4"></div>
          <p className="text-sm text-gray-600">Initializing development environment...</p>
        </div>
      </div>
    )
  }

  return <>{children}</>
}
