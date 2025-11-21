import type { Metadata } from "next";
import "./globals.css";
import { MSWProvider } from "@/components/providers/MSWProvider";
import { SessionProvider } from "@/components/providers/SessionProvider";
import { ReactQueryProvider } from "@/components/providers/ReactQueryProvider";
import { ThemeProvider } from "@/components/providers/ThemeProvider";
import { ToastProvider } from "@/components/providers/ToastProvider";
import { KeyboardShortcutsProvider } from "@/components/providers/KeyboardShortcutsProvider";
import { PageLoader } from "@/components/ui/PageLoader";
import { OfflineBanner } from "@/components/error-boundary/OfflineBanner";

export const metadata: Metadata = {
  title: "AI Agents Platform",
  description: "Enterprise AI Agents Management Platform with Liquid Glass Design",
};

/**
 * Root Layout with Nested Providers
 *
 * Provider hierarchy (outer to inner):
 * 1. MSWProvider - Mock Service Worker (development only)
 * 2. SessionProvider - NextAuth authentication state
 * 3. ReactQueryProvider - Server state management (React Query)
 * 4. ThemeProvider - Client-side theme state (light/dark mode)
 * 5. ToastProvider - Notification system (Sonner)
 * 6. KeyboardShortcutsProvider - Command palette (⌘K) + shortcuts (Story 6 AC-1 & AC-2)
 *
 * Reference: tech-spec Section 2.1.2
 */
export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased">
        <PageLoader />
        <OfflineBanner />
        <MSWProvider>
          <SessionProvider>
            <ReactQueryProvider>
              <ThemeProvider>
                <ToastProvider>
                  <KeyboardShortcutsProvider>{children}</KeyboardShortcutsProvider>
                </ToastProvider>
              </ThemeProvider>
            </ReactQueryProvider>
          </SessionProvider>
        </MSWProvider>
      </body>
    </html>
  );
}
