// Learn more: https://github.com/testing-library/jest-dom
import '@testing-library/jest-dom'
import { TextEncoder, TextDecoder } from 'util'
import { BroadcastChannel } from 'worker_threads'
import { ReadableStream, WritableStream, TransformStream } from 'stream/web'
import 'whatwg-fetch'

// Polyfill TextEncoder and TextDecoder for MSW (MUST be before MSW import)
global.TextEncoder = TextEncoder
global.TextDecoder = TextDecoder

// Polyfill BroadcastChannel for MSW WebSocket support
global.BroadcastChannel = BroadcastChannel

// Polyfill streams for MSW
global.ReadableStream = ReadableStream
global.WritableStream = WritableStream
global.TransformStream = TransformStream

// Mock ResizeObserver for headlessui/react
global.ResizeObserver = class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}

// Global fetch mock for tests that need direct fetch mocking
// Use beforeEach in tests to reset mock state
// Spy on global.fetch to allow mockImplementation and mockRejectedValue
global.fetch = (() => {
  const mockFn = jest.fn()
  // Set default implementation to prevent undefined errors
  mockFn.mockResolvedValue({
    ok: true,
    json: async () => ({}),
  })
  return mockFn
})()

// MSW Server Lifecycle (2025 best practices)
// TEMPORARILY DISABLED: MSW conflicts with legacy fetch mocking in some tests
// TODO: Migrate all tests to use MSW instead of direct fetch mocking
// Import MSW server dynamically AFTER polyfills are set
// let server

// beforeAll(async () => {
//   // Dynamically import server after polyfills are set
//   const { server: mswServer } = await import('./mocks/server')
//   server = mswServer

//   // Start MSW server before all tests
//   server.listen({ onUnhandledRequest: 'warn' })
// })

// afterEach(() => {
//   // Reset handlers after each test to ensure test isolation
//   if (server) {
//     server.resetHandlers()
//   }
// })

// afterAll(() => {
//   // Close MSW server after all tests
//   if (server) {
//     server.close()
//   }
// })
