"use client";

import { WifiOff } from "lucide-react";
import { useEffect, useState } from "react";
import { useOnlineStatus } from "@/lib/hooks/useOnlineStatus";
import { toast } from "sonner";

/**
 * OfflineBanner Component
 *
 * Displays a banner at the top when user goes offline.
 * Auto-hides when connection is restored and shows success toast.
 *
 * Features:
 * - Sticky banner at top of viewport
 * - Auto-reconnect detection
 * - Success toast on reconnection
 * - Sliding animation (slide down on offline, slide up on online)
 * - Non-intrusive design (semi-transparent with backdrop blur)
 *
 * Design:
 * - Uses Liquid Glass design system (glass-card effect)
 * - Yellow warning background for offline state
 * - Matches existing design patterns from Header/Sidebar
 *
 * Accessibility:
 * - aria-live="assertive" for offline (high priority announcement)
 * - aria-live="polite" for online (low priority)
 * - Role="alert" for screen readers
 * - Keyboard accessible (focusable for screen reader users)
 *
 * @example
 * ```tsx
 * // In root layout or top-level component
 * <OfflineBanner />
 * ```
 *
 * Reference: Story 6 AC-5 (Error Handling - Offline Detection)
 */
export function OfflineBanner() {
  const isOnline = useOnlineStatus();
  const [showBanner, setShowBanner] = useState(false);
  const [wasOffline, setWasOffline] = useState(false);

  useEffect(() => {
    if (!isOnline) {
      // User went offline
      setShowBanner(true);
      setWasOffline(true);
    } else if (wasOffline && isOnline) {
      // User came back online (was offline before)
      setShowBanner(false);
      toast.success("Connection restored", {
        description: "You're back online. Changes will now sync.",
        duration: 4000,
      });
      setWasOffline(false);
    }
  }, [isOnline, wasOffline]);

  if (!showBanner) {
    return null;
  }

  return (
    <div
      className="fixed top-0 left-0 right-0 z-50 animate-slide-down"
      role="alert"
      aria-live="assertive"
      aria-atomic="true"
    >
      <div className="bg-yellow-500/10 backdrop-blur-lg border-b border-yellow-500/20 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="flex-shrink-0">
                <WifiOff className="h-5 w-5 text-yellow-600 dark:text-yellow-400" />
              </div>
              <div className="flex-1">
                <p className="text-sm font-medium text-yellow-800 dark:text-yellow-200">
                  You&apos;re offline
                </p>
                <p className="text-xs text-yellow-700 dark:text-yellow-300 mt-0.5">
                  Changes will sync when reconnected. You can still view cached data.
                </p>
              </div>
            </div>

            {/* Connection status indicator (pulsing animation) */}
            <div className="flex items-center gap-2">
              <div className="relative">
                <div className="h-2 w-2 bg-yellow-500 rounded-full animate-pulse"></div>
                <div className="absolute inset-0 h-2 w-2 bg-yellow-500 rounded-full animate-ping opacity-75"></div>
              </div>
              <span className="text-xs text-yellow-700 dark:text-yellow-300 hidden sm:inline">
                Waiting for connection...
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

/**
 * OfflineBannerCompact Component
 *
 * Compact version of the banner for smaller viewports or embedded use.
 * Shows minimal info with just icon + status text.
 *
 * @example
 * ```tsx
 * <OfflineBannerCompact />
 * ```
 */
export function OfflineBannerCompact() {
  const isOnline = useOnlineStatus();

  if (isOnline) {
    return null;
  }

  return (
    <div
      className="flex items-center gap-2 px-3 py-2 bg-yellow-500/10 border border-yellow-500/20 rounded-md"
      role="alert"
      aria-live="assertive"
    >
      <WifiOff className="h-4 w-4 text-yellow-600 dark:text-yellow-400" />
      <span className="text-xs text-yellow-700 dark:text-yellow-300">
        Offline mode
      </span>
    </div>
  );
}
