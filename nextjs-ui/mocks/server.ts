/**
 * MSW Server for Node.js (Jest/Testing)
 *
 * This server is used in Jest tests to intercept and mock API requests.
 * Based on MSW 2.x best practices (2025).
 */

import { setupServer } from 'msw/node'
import { handlers } from './handlers'

/**
 * Create MSW server with all handlers
 *
 * Usage in tests:
 * beforeAll(() => server.listen())
 * afterEach(() => server.resetHandlers())
 * afterAll(() => server.close())
 */
export const server = setupServer(...handlers)

// Enable helpful warnings in development
if (process.env.NODE_ENV === 'development') {
  server.events.on('request:start', ({ request }) => {
    console.log('MSW intercepted:', request.method, request.url)
  })
}
