"use client";

import { ReactNode } from "react";
import { Toaster } from "sonner";

interface ToastProviderProps {
  children: ReactNode;
}

/**
 * Toast notification provider (Sonner)
 *
 * Provides toast notifications for:
 * - Success messages
 * - Error alerts
 * - Info notifications
 * - Loading states
 * - Action buttons (undo/retry)
 *
 * Usage: import { toast } from '@/components/ui/Toast'
 *
 * Reference: tech-spec Section 2.3.3, Story 6 AC-3
 */
export function ToastProvider({ children }: ToastProviderProps) {
  return (
    <>
      {children}
      <Toaster
        position="top-right"
        expand={true}
        richColors={false} // We use custom styling via Toast.tsx wrapper
        closeButton={false} // We handle close button in Toast.tsx
        duration={4000}
        visibleToasts={3}
        toastOptions={{
          className: "glass-card",
        }}
      />
    </>
  );
}
