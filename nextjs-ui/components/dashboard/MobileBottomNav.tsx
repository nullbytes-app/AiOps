'use client'

/**
 * Mobile Bottom Navigation Component
 *
 * Features:
 * - Fixed bottom navigation for mobile viewport (<768px)
 * - 5 most important navigation items
 * - Large touch targets (48px minimum)
 * - Active state highlighting
 * - Glassmorphic design matching Liquid Glass aesthetic
 * - Icon-only labels for space efficiency
 *
 * Reference: tech-spec Section 2.3.1
 */

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { BarChart3, Bot, Settings, Workflow, Layers } from 'lucide-react'

interface NavItem {
  label: string
  href: string
  icon: React.ReactNode
}

const mobileNavItems: NavItem[] = [
  {
    label: 'Dashboard',
    href: '/dashboard',
    icon: <BarChart3 className="w-6 h-6" />,
  },
  {
    label: 'Agents',
    href: '/dashboard/agents',
    icon: <Bot className="w-6 h-6" />,
  },
  {
    label: 'Executions',
    href: '/dashboard/executions',
    icon: <Workflow className="w-6 h-6" />,
  },
  {
    label: 'Workflows',
    href: '/dashboard/workflows',
    icon: <Layers className="w-6 h-6" />,
  },
  {
    label: 'Settings',
    href: '/dashboard/settings',
    icon: <Settings className="w-6 h-6" />,
  },
]

export function MobileBottomNav() {
  const pathname = usePathname()

  return (
    <nav
      className="
        fixed bottom-0 left-0 right-0 z-50
        md:hidden
        glass-card border-t border-white/20
        px-2 pb-safe
      "
      aria-label="Mobile navigation"
    >
      <ul className="flex items-center justify-around h-16">
        {mobileNavItems.map((item) => {
          const isActive = pathname === item.href
          return (
            <li key={item.href} className="flex-1">
              <Link
                href={item.href}
                className={`
                  flex flex-col items-center justify-center gap-1
                  h-full min-h-[48px] px-2
                  rounded-lg transition-all duration-200
                  ${
                    isActive
                      ? 'bg-accent-blue text-white'
                      : 'text-text-secondary hover:bg-white/30 dark:hover:bg-gray-800/30'
                  }
                `}
                aria-current={isActive ? 'page' : undefined}
              >
                <span aria-hidden="true">{item.icon}</span>
                <span
                  className={`text-[10px] font-medium ${
                    isActive ? 'text-white' : 'text-text-secondary'
                  }`}
                >
                  {item.label}
                </span>
              </Link>
            </li>
          )
        })}
      </ul>
    </nav>
  )
}
