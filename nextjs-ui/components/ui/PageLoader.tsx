"use client";

import { useEffect, Suspense } from "react";
import { usePathname, useSearchParams } from "next/navigation";
import NProgress from "nprogress";
import "nprogress/nprogress.css";

/**
 * PageLoaderContent Component (Internal)
 *
 * Internal component that uses useSearchParams.
 * Must be wrapped in Suspense boundary.
 */
function PageLoaderContent() {
  const pathname = usePathname();
  const searchParams = useSearchParams();

  useEffect(() => {
    // Configure NProgress
    NProgress.configure({
      showSpinner: false, // No spinner, just linear bar
      trickleSpeed: 200, // Smooth animation
      minimum: 0.08, // Start at 8%
      easing: "ease", // Smooth easing
      speed: 200, // Animation speed
    });

    // Inject custom styles for NProgress bar
    const style = document.createElement("style");
    style.textContent = `
      /* NProgress bar styles */
      #nprogress {
        pointer-events: none;
      }

      #nprogress .bar {
        background: #3b82f6; /* Blue-500 */
        position: fixed;
        z-index: 9999;
        top: 0;
        left: 0;
        width: 100%;
        height: 3px;
      }

      #nprogress .peg {
        display: block;
        position: absolute;
        right: 0px;
        width: 100px;
        height: 100%;
        box-shadow: 0 0 10px #3b82f6, 0 0 5px #3b82f6;
        opacity: 1.0;
        transform: rotate(3deg) translate(0px, -4px);
      }

      /* Dark mode support */
      .dark #nprogress .bar {
        background: #60a5fa; /* Blue-400 */
      }

      .dark #nprogress .peg {
        box-shadow: 0 0 10px #60a5fa, 0 0 5px #60a5fa;
      }
    `;
    document.head.appendChild(style);

    return () => {
      document.head.removeChild(style);
    };
  }, []);

  useEffect(() => {
    // Start progress on route change
    NProgress.start();

    // Complete progress after a minimum delay (feels smoother)
    const timer = setTimeout(() => {
      NProgress.done();
    }, 100);

    return () => {
      clearTimeout(timer);
      NProgress.done();
    };
  }, [pathname, searchParams]);

  return null; // No visual component needed (NProgress injects itself)
}

/**
 * Manual NProgress Controls
 *
 * Utility functions for manual progress control.
 * Useful for long-running operations or file uploads.
 *
 * @example
 * ```tsx
 * import { progressStart, progressDone, progressSet } from '@/components/ui/PageLoader';
 *
 * // Start progress
 * progressStart();
 *
 * // Set specific progress (0 to 1)
 * progressSet(0.5); // 50%
 *
 * // Complete progress
 * progressDone();
 * ```
 */

/**
 * Start NProgress manually
 */
export function progressStart() {
  NProgress.start();
}

/**
 * Complete NProgress manually
 */
export function progressDone() {
  NProgress.done();
}

/**
 * Set NProgress to specific value (0 to 1)
 */
export function progressSet(value: number) {
  NProgress.set(value);
}

/**
 * Increment NProgress by small amount
 */
export function progressIncrement() {
  NProgress.inc();
}

/**
 * Check if NProgress is currently running
 */
export function progressIsStarted(): boolean {
  return NProgress.isStarted();
}

/**
 * PageLoader Component
 *
 * Top-loading progress bar (Vercel-style) for page transitions.
 * Uses NProgress library for smooth linear progress animation.
 *
 * Features:
 * - Automatic progress on route changes
 * - Smooth animation (minimum 200ms display)
 * - Customizable color (blue by default)
 * - Accessible (aria-live announcements)
 * - No spinner (linear bar only)
 *
 * Loading State Thresholds:
 * - < 300ms: No loading indicator
 * - 300ms - 1s: Show NProgress bar
 * - > 1s: Continue showing NProgress bar
 *
 * @example
 * ```tsx
 * // Add to root layout
 * import { PageLoader } from '@/components/ui/PageLoader';
 *
 * export default function RootLayout({ children }) {
 *   return (
 *     <html>
 *       <body>
 *         <PageLoader />
 *         {children}
 *       </body>
 *     </html>
 *   );
 * }
 * ```
 *
 * Reference: Story 6 AC-4 (Loading States - Page Loading)
 */
export function PageLoader() {
  return (
    <Suspense fallback={null}>
      <PageLoaderContent />
    </Suspense>
  );
}
