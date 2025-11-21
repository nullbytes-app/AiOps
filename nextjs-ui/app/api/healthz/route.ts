/**
 * Health Check Endpoint
 *
 * Simple endpoint that returns 200 OK to verify the Next.js server is running.
 * Used by Playwright's webServer configuration to detect when dev server is ready.
 */

import { NextResponse } from 'next/server'

export async function GET() {
  return NextResponse.json(
    {
      status: 'ok',
      timestamp: new Date().toISOString(),
    },
    { status: 200 }
  )
}
