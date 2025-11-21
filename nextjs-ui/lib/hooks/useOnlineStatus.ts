"use client";

import { useState, useEffect } from "react";

/**
 * useOnlineStatus Hook
 *
 * Detects online/offline status using navigator.onLine API.
 * Listens to 'online' and 'offline' events for real-time updates.
 *
 * Features:
 * - Real-time online/offline detection
 * - Auto-reconnect detection
 * - Works in all modern browsers
 * - SSR-safe (returns true on server)
 *
 * Use Cases:
 * - Display offline banner
 * - Disable network-dependent actions
 * - Enable read-only mode
 * - Show reconnection notifications
 *
 * @example
 * ```tsx
 * function MyComponent() {
 *   const isOnline = useOnlineStatus();
 *
 *   if (!isOnline) {
 *     return <OfflineBanner />;
 *   }
 *
 *   return <YourContent />;
 * }
 * ```
 *
 * Reference: Story 6 AC-5 (Error Handling - Offline Detection)
 */
export function useOnlineStatus(): boolean {
  // Default to true for SSR (server-side rendering)
  const [isOnline, setIsOnline] = useState<boolean>(() => {
    if (typeof window === "undefined") return true;
    return navigator.onLine;
  });

  useEffect(() => {
    // Only run in browser environment
    if (typeof window === "undefined") return;

    // Handler for online event
    const handleOnline = () => {
      setIsOnline(true);
    };

    // Handler for offline event
    const handleOffline = () => {
      setIsOnline(false);
    };

    // Add event listeners
    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);

    // Cleanup
    return () => {
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
    };
  }, []);

  return isOnline;
}

/**
 * useOnlineStatusWithCallback Hook
 *
 * Extended version with callbacks for online/offline transitions.
 * Useful for triggering side effects when connection status changes.
 *
 * @example
 * ```tsx
 * const isOnline = useOnlineStatusWithCallback({
 *   onOnline: () => {
 *     toast.success("Connection restored");
 *     // Sync pending changes
 *     syncPendingData();
 *   },
 *   onOffline: () => {
 *     toast.warning("You're offline. Changes will sync when reconnected.");
 *   },
 * });
 * ```
 */
export function useOnlineStatusWithCallback(options?: {
  onOnline?: () => void;
  onOffline?: () => void;
}): boolean {
  const [isOnline, setIsOnline] = useState<boolean>(() => {
    if (typeof window === "undefined") return true;
    return navigator.onLine;
  });

  useEffect(() => {
    if (typeof window === "undefined") return;

    const handleOnline = () => {
      setIsOnline(true);
      options?.onOnline?.();
    };

    const handleOffline = () => {
      setIsOnline(false);
      options?.onOffline?.();
    };

    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);

    return () => {
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
    };
  }, [options]);

  return isOnline;
}
