"use client";

import { useEffect, useState } from "react";
import { WifiOff } from "lucide-react";
import { useOnlineStatusWithCallback } from "@/lib/hooks/useOnlineStatus";
import { toast } from "@/components/ui/Toast";

/**
 * OfflineBanner Component
 *
 * Banner displayed at top of page when user is offline.
 * Auto-hides when connection is restored.
 *
 * Features:
 * - Displays at top of viewport (sticky)
 * - Shows offline icon and message
 * - Auto-hides on reconnection with success toast
 * - Slide-in/out animation
 * - High z-index (above all content)
 *
 * Offline Mode Behavior:
 * - Banner at top: "You're offline. Changes will sync when reconnected."
 * - Disable network-dependent actions: Create, update, delete buttons grayed out
 * - Enable read-only mode: User can still view cached data
 * - Auto-reconnect: Hide banner when connection restored, show success toast
 *
 * @example
 * ```tsx
 * // Add to root layout or main app wrapper
 * import { OfflineBanner } from '@/components/offline/OfflineBanner';
 *
 * export default function Layout({ children }) {
 *   return (
 *     <>
 *       <OfflineBanner />
 *       {children}
 *     </>
 *   );
 * }
 * ```
 *
 * Reference: Story 6 AC-5 (Error Handling - Offline Detection)
 */
export function OfflineBanner() {
  const [showBanner, setShowBanner] = useState(false);
  const [hasBeenOffline, setHasBeenOffline] = useState(false);

  const isOnline = useOnlineStatusWithCallback({
    onOnline: () => {
      // Only show reconnection toast if user was previously offline
      if (hasBeenOffline) {
        toast.success("Connection restored", {
          description: "You're back online. Changes will now sync.",
        });
        setHasBeenOffline(false);
      }
      setShowBanner(false);
    },
    onOffline: () => {
      setShowBanner(true);
      setHasBeenOffline(true);
    },
  });

  // Check initial online status
  useEffect(() => {
    if (!isOnline) {
      setShowBanner(true);
      setHasBeenOffline(true);
    }
  }, [isOnline]);

  if (!showBanner) return null;

  return (
    <div
      className="fixed top-0 left-0 right-0 z-[10000] bg-yellow-500 dark:bg-yellow-600 text-white shadow-lg"
      role="alert"
      aria-live="assertive"
      aria-atomic="true"
    >
      <div className="max-w-7xl mx-auto px-4 py-3">
        <div className="flex items-center justify-between gap-4">
          {/* Offline Icon + Message */}
          <div className="flex items-center gap-3">
            <WifiOff size={20} className="flex-shrink-0" />
            <div>
              <div className="font-semibold text-sm">You&apos;re offline</div>
              <div className="text-xs opacity-90">
                Changes will sync when you&apos;re back online.
              </div>
            </div>
          </div>

          {/* Checking Connection Indicator */}
          <div className="flex items-center gap-2 text-xs">
            <div className="animate-pulse">●</div>
            <span>Checking connection...</span>
          </div>
        </div>
      </div>
    </div>
  );
}

/**
 * useOfflineMode Hook
 *
 * Hook to check if user is offline and disable network actions.
 * Returns both offline status and helper functions.
 *
 * @example
 * ```tsx
 * function CreateButton() {
 *   const { isOffline, disableIfOffline } = useOfflineMode();
 *
 *   return (
 *     <button
 *       disabled={disableIfOffline()}
 *       onClick={handleCreate}
 *       className={isOffline ? 'opacity-50 cursor-not-allowed' : ''}
 *     >
 *       Create Agent
 *     </button>
 *   );
 * }
 * ```
 */
export function useOfflineMode() {
  const isOnline = useOnlineStatusWithCallback({
    onOffline: () => {
      toast.warning("You're offline", {
        description: "This action requires an internet connection.",
      });
    },
  });

  const isOffline = !isOnline;

  /**
   * Returns true if offline (for disabled prop)
   */
  const disableIfOffline = () => isOffline;

  /**
   * Shows offline toast and returns false if offline
   */
  const checkOnline = (): boolean => {
    if (isOffline) {
      toast.warning("You're offline", {
        description: "This action requires an internet connection.",
      });
      return false;
    }
    return true;
  };

  return {
    isOnline,
    isOffline,
    disableIfOffline,
    checkOnline,
  };
}
