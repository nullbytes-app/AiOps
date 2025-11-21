"use client";

import { ReactNode } from "react";
import { Header } from "./Header";
import { Sidebar } from "./Sidebar";
import { Footer } from "./Footer";
import { MobileBottomNav } from "./MobileBottomNav";

interface DashboardLayoutProps {
  children: ReactNode;
}

/**
 * Dashboard Layout Shell
 *
 * Combines Header, Sidebar, Footer, and Mobile Bottom Nav into a cohesive layout
 * Uses Liquid Glass design with glassmorphic cards
 *
 * Layout structure:
 * Desktop (≥768px):
 * - Header (top, full width)
 * - Sidebar (left, scrollable)
 * - Main content area (right side, scrollable)
 * - Footer (bottom, full width)
 *
 * Mobile (<768px):
 * - Header (top, full width)
 * - Main content area (full width, scrollable)
 * - Mobile Bottom Nav (fixed bottom, 5 key items)
 * - Footer (hidden on mobile to save space)
 *
 * Reference: tech-spec Section 2.3.1
 */
export function DashboardLayout({ children }: DashboardLayoutProps) {
  return (
    <div className="min-h-screen p-6 pb-24 md:pb-6">
      <Header />
      <div className="flex">
        <Sidebar />
        <main className="flex-1">
          {children}
        </main>
      </div>
      <Footer />
      <MobileBottomNav />
    </div>
  );
}
