"use client";

/**
 * Dashboard Footer Component
 *
 * Displays:
 * - Copyright information
 * - Version number
 * - Quick links
 *
 * Reference: tech-spec Section 2.3.1
 */
export function Footer() {
  return (
    <footer className="hidden md:block glass-card mt-6 px-6 py-4">
      <div className="flex items-center justify-between text-sm text-text-secondary">
        <div>
          © {new Date().getFullYear()} AI Agents Platform. All rights reserved.
        </div>
        <div className="flex items-center gap-6">
          <span>v1.0.0</span>
          <a
            href="/docs"
            className="hover:text-accent-blue transition-colors duration-fast"
          >
            Documentation
          </a>
          <a
            href="/support"
            className="hover:text-accent-blue transition-colors duration-fast"
          >
            Support
          </a>
        </div>
      </div>
    </footer>
  );
}
