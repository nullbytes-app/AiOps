"use client";

import { useSession, signOut } from "next-auth/react";
import { Menu } from "@headlessui/react";
import { ChevronDown, LogOut, Settings, User } from "lucide-react";
import { TenantSwitcher } from "@/components/tenant/TenantSwitcher";
import { ThemeToggle } from "@/components/ui/ThemeToggle";

/**
 * Dashboard Header Component
 *
 * Features:
 * - Logo/Brand (left)
 * - Tenant Switcher (center)
 * - Theme Toggle + User Menu (right)
 *
 * Reference: tech-spec Section 2.3.1
 */
export function Header() {
  const { data: session } = useSession();

  return (
    <header className="glass-card h-16 flex items-center justify-between px-6 mb-6">
      {/* Logo */}
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-accent-blue to-accent-purple flex items-center justify-center text-white font-bold">
          AI
        </div>
        <h1 className="text-xl font-semibold text-text-primary">
          AI Agents Platform
        </h1>
      </div>

      {/* Tenant Switcher */}
      <TenantSwitcher />

      {/* Right Section: Theme Toggle + User Menu */}
      <div className="flex items-center gap-3">
        <ThemeToggle />

        {/* User Menu */}
        <Menu as="div" className="relative">
        <Menu.Button className="flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-white/50 transition-colors duration-fast">
          <div className="w-8 h-8 rounded-full bg-accent-purple/20 flex items-center justify-center">
            <User className="w-5 h-5 text-accent-purple" />
          </div>
          <span className="text-sm font-medium text-text-primary">
            {session?.user?.name || "User"}
          </span>
          <ChevronDown className="w-4 h-4 text-text-secondary" />
        </Menu.Button>

        <Menu.Items className="absolute right-0 mt-2 w-48 glass-card py-2 shadow-lg focus:outline-none z-50">
          <Menu.Item>
            {({ active }) => (
              <button
                className={`${
                  active ? "bg-white/50" : ""
                } flex items-center gap-2 w-full px-4 py-2 text-sm text-text-primary transition-colors duration-fast`}
              >
                <Settings className="w-4 h-4" />
                Settings
              </button>
            )}
          </Menu.Item>
          <Menu.Item>
            {({ active }) => (
              <button
                onClick={() => signOut({ callbackUrl: "/login" })}
                className={`${
                  active ? "bg-white/50" : ""
                } flex items-center gap-2 w-full px-4 py-2 text-sm text-text-primary transition-colors duration-fast`}
              >
                <LogOut className="w-4 h-4" />
                Logout
              </button>
            )}
          </Menu.Item>
        </Menu.Items>
        </Menu>
      </div>
    </header>
  );
}
