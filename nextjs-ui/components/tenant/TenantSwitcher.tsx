"use client";

import { useState, useEffect } from "react";
import { useSession } from "next-auth/react";
import { Listbox } from "@headlessui/react";
import { ChevronDown, Check, Search } from "lucide-react";
import { useQuery } from "@tanstack/react-query";

interface Tenant {
  id: string;
  name: string;
  slug: string;
}

interface UserRole {
  role: string;
  tenant_id: string;
}

/**
 * Tenant Switcher Component
 *
 * Features:
 * - Glassmorphic dropdown with Headless UI
 * - Search/filter tenants
 * - Fetches user role on-demand per tenant (tech-spec Section 2.1.1)
 * - Stores selected tenant in Zustand (client-side state)
 *
 * API Integration:
 * - GET /api/v1/tenants - list user's accessible tenants
 * - GET /api/v1/users/me/role?tenant_id={id} - fetch role for tenant
 *
 * Reference: tech-spec Section 2.3.4
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export function TenantSwitcher() {
  const { data: session } = useSession();
  const [selectedTenant, setSelectedTenant] = useState<Tenant | null>(null);
  const [searchQuery, setSearchQuery] = useState("");

  // Fetch user's accessible tenants
  const { data: tenants = [], isLoading } = useQuery<Tenant[]>({
    queryKey: ["tenants"],
    queryFn: async () => {
      const response = await fetch(`${API_BASE_URL}/api/v1/tenants`, {
        headers: {
          Authorization: `Bearer ${session?.accessToken}`,
        },
      });
      if (!response.ok) throw new Error("Failed to fetch tenants");
      return response.json();
    },
    enabled: !!session?.accessToken,
  });

  // Set first tenant as default when loaded
  useEffect(() => {
    if (tenants.length > 0 && !selectedTenant) {
      setSelectedTenant(tenants[0]);
    }
  }, [tenants, selectedTenant]);

  // Fetch role for selected tenant
  const { data: userRole } = useQuery<UserRole>({
    queryKey: ["userRole", selectedTenant?.id],
    queryFn: async () => {
      const response = await fetch(
        `${API_BASE_URL}/api/v1/users/me/role?tenant_id=${selectedTenant?.id}`,
        {
          headers: {
            Authorization: `Bearer ${session?.accessToken}`,
          },
        }
      );
      if (!response.ok) throw new Error("Failed to fetch user role");
      return response.json();
    },
    enabled: !!selectedTenant && !!session?.accessToken,
  });

  // Filter tenants by search query
  const filteredTenants = tenants.filter((tenant) =>
    tenant.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  if (isLoading || !selectedTenant) {
    return (
      <div className="w-64 h-10 glass-card animate-pulse rounded-lg"></div>
    );
  }

  return (
    <Listbox value={selectedTenant} onChange={setSelectedTenant}>
      <div className="relative">
        <Listbox.Button className="glass-card w-64 px-4 py-2 flex items-center justify-between hover:shadow-lg transition-shadow duration-moderate cursor-pointer">
          <div className="flex flex-col items-start">
            <span className="text-sm font-medium text-text-primary">
              {selectedTenant.name}
            </span>
            {userRole && (
              <span className="text-small text-text-secondary capitalize">
                {userRole.role.replace("_", " ")}
              </span>
            )}
          </div>
          <ChevronDown className="w-4 h-4 text-text-secondary" />
        </Listbox.Button>

        <Listbox.Options className="absolute mt-2 w-64 glass-card shadow-lg max-h-80 overflow-auto focus:outline-none z-50">
          {/* Search Input */}
          <div className="p-3 border-b border-white/50">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-text-secondary" />
              <input
                type="text"
                placeholder="Search tenants..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-3 py-2 rounded-lg bg-white/50 border border-white/50 text-sm focus:outline-none focus:ring-2 focus:ring-accent-blue"
              />
            </div>
          </div>

          {/* Tenant Options */}
          <div className="p-2">
            {filteredTenants.length === 0 ? (
              <div className="px-3 py-2 text-sm text-text-secondary">
                No tenants found
              </div>
            ) : (
              filteredTenants.map((tenant) => (
                <Listbox.Option
                  key={tenant.id}
                  value={tenant}
                  className={({ active }) =>
                    `flex items-center justify-between px-3 py-2 rounded-lg cursor-pointer transition-colors duration-fast ${
                      active ? "bg-white/50" : ""
                    }`
                  }
                >
                  {({ selected }) => (
                    <>
                      <span
                        className={`text-sm ${
                          selected
                            ? "font-semibold text-accent-blue"
                            : "font-medium text-text-primary"
                        }`}
                      >
                        {tenant.name}
                      </span>
                      {selected && (
                        <Check className="w-4 h-4 text-accent-blue" />
                      )}
                    </>
                  )}
                </Listbox.Option>
              ))
            )}
          </div>
        </Listbox.Options>
      </div>
    </Listbox>
  );
}
