"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  BarChart3,
  Bot,
  Cpu,
  FileText,
  Layers,
  MessageSquare,
  Settings,
  Shield,
  Workflow,
  Database,
  Package,
  Terminal,
  TestTube,
  HeartPulse,
  Ticket,
  Activity,
} from "lucide-react";
import { ReactNode } from "react";

interface NavItem {
  label: string;
  href: string;
  icon: ReactNode;
}

interface NavCategory {
  category: string;
  items: NavItem[];
}

/**
 * Dashboard Sidebar Navigation
 *
 * Navigation structure follows tech-spec Section 1.3:
 * - Monitoring (4 pages)
 * - Configuration (5 pages)
 * - Operations (3 pages)
 * - Tools (2 pages)
 *
 * Reference: tech-spec Section 2.3.1
 */

const navigationData: NavCategory[] = [
  {
    category: "Monitoring",
    items: [
      { label: "Dashboard", href: "/dashboard", icon: <BarChart3 className="w-5 h-5" /> },
      { label: "System Health", href: "/dashboard/health", icon: <HeartPulse className="w-5 h-5" /> },
      { label: "Agent Metrics", href: "/dashboard/agents", icon: <Bot className="w-5 h-5" /> },
      { label: "Agent Performance", href: "/dashboard/agent-performance", icon: <Activity className="w-5 h-5" /> },
      { label: "Ticket Processing", href: "/dashboard/tickets", icon: <Ticket className="w-5 h-5" /> },
    ],
  },
  {
    category: "Configuration",
    items: [
      { label: "Tenants", href: "/dashboard/tenants", icon: <Shield className="w-5 h-5" /> },
      { label: "Agents", href: "/dashboard/agents-config", icon: <Bot className="w-5 h-5" /> },
      { label: "Prompts", href: "/dashboard/prompts", icon: <MessageSquare className="w-5 h-5" /> },
      { label: "Tools", href: "/dashboard/tools", icon: <Cpu className="w-5 h-5" /> },
      { label: "Plugins", href: "/dashboard/plugins", icon: <Package className="w-5 h-5" /> },
      { label: "MCP Servers", href: "/dashboard/mcp-servers", icon: <Database className="w-5 h-5" /> },
      { label: "Workflows", href: "/dashboard/workflows", icon: <Layers className="w-5 h-5" /> },
    ],
  },
  {
    category: "Operations",
    items: [
      { label: "Logs", href: "/dashboard/logs", icon: <FileText className="w-5 h-5" /> },
      { label: "Audit Trail", href: "/dashboard/audit", icon: <Workflow className="w-5 h-5" /> },
      { label: "Settings", href: "/dashboard/settings", icon: <Settings className="w-5 h-5" /> },
    ],
  },
  {
    category: "Tools",
    items: [
      { label: "API Playground", href: "/dashboard/playground", icon: <Terminal className="w-5 h-5" /> },
      { label: "Testing", href: "/dashboard/testing", icon: <TestTube className="w-5 h-5" /> },
    ],
  },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="hidden md:block w-64 glass-card p-6 mr-6 h-[calc(100vh-120px)] overflow-y-auto">
      <nav className="space-y-6">
        {navigationData.map((section) => (
          <div key={section.category}>
            <h3 className="text-xs font-semibold text-text-secondary uppercase tracking-wider mb-3">
              {section.category}
            </h3>
            <ul className="space-y-1">
              {section.items.map((item) => {
                const isActive = pathname === item.href;
                return (
                  <li key={item.href}>
                    <Link
                      href={item.href}
                      className={`flex items-center gap-3 px-3 py-2 rounded-lg transition-all duration-fast ${
                        isActive
                          ? "bg-accent-blue text-white shadow-md"
                          : "text-text-primary hover:bg-white/50"
                      }`}
                    >
                      {item.icon}
                      <span className="text-sm font-medium">{item.label}</span>
                    </Link>
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
      </nav>
    </aside>
  );
}
