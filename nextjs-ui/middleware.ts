import { withAuth } from "next-auth/middleware";
import { NextResponse, NextRequest } from "next/server";

/**
 * Next.js Middleware for Authentication
 *
 * Protects routes requiring authentication:
 * - /dashboard/* - All dashboard routes
 * - /api/* - All API routes except /api/auth/*
 *
 * Redirects unauthenticated users to /login
 *
 * In E2E test mode (NEXT_PUBLIC_E2E_TEST=true), authentication is bypassed
 * to allow tests to run without requiring a login session.
 *
 * Reference: tech-spec Section 2.1.3
 */

// In E2E test mode, bypass auth entirely
// Note: Use E2E_TEST (server-side var) not NEXT_PUBLIC_E2E_TEST (client-side only)
const isE2EMode = process.env.E2E_TEST === 'true';

export default isE2EMode
  ? function middleware(req: NextRequest) {
      return NextResponse.next();
    }
  : withAuth(
      function middleware(req) {
        // Additional middleware logic can be added here
        // For example: role-based access control, logging, etc.
        return NextResponse.next();
      },
      {
        callbacks: {
          authorized: ({ token }) => !!token,
        },
        pages: {
          signIn: "/login",
        },
      }
    );

// Configure which routes require authentication
export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - api/auth (NextAuth.js routes)
     * - api/health (health check endpoint for Docker)
     * - api/healthz (health check endpoint for E2E tests)
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     * - login (login page)
     * - / (home/landing page)
     */
    "/((?!api/auth|api/health|api/healthz|_next/static|_next/image|favicon.ico|login|^/$).*)",
  ],
};
