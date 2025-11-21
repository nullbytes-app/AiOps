/**
 * Audit Logs Page
 *
 * Displays authentication and general audit logs with tab navigation.
 * Tab indicators show count of records in the last 24 hours.
 *
 * Access: super_admin + tenant_admin only (RBAC enforced)
 */

'use client';

import { useState } from 'react';
import { Tabs, TabItem } from '@/components/ui/Tabs';
import { AuthAuditTable } from '@/components/audit-logs/AuthAuditTable';
import { GeneralAuditTable } from '@/components/audit-logs/GeneralAuditTable';
import { useAuthAuditLogs, useGeneralAuditLogs } from '@/lib/hooks/useAudit';
import { ShieldCheck, ClipboardList } from 'lucide-react';

/**
 * Audit Logs page component
 *
 * Features:
 * - Dual tab navigation: Auth Events / General Audit
 * - Tab badges showing 24h record counts
 * - Advanced filtering per tab
 * - jsondiffpatch diff modal for changes
 * - RBAC: Only super_admin + tenant_admin
 */
export default function AuditLogsPage() {
  const [selectedIndex, setSelectedIndex] = useState(0);

  // Fetch 24h counts for tab badges
  const { data: authData } = useAuthAuditLogs({ limit: 1 });
  const { data: generalData } = useGeneralAuditLogs({ limit: 1 });

  // Get 24h counts for badge display
  const authCount = authData?.count_24h || 0;
  const generalCount = generalData?.count_24h || 0;

  const tabs: TabItem[] = [
    {
      key: 'auth',
      label: authCount > 0 ? `Auth Events (${authCount})` : 'Auth Events',
      icon: <ShieldCheck className="h-5 w-5" />,
      content: <AuthAuditTable />,
    },
    {
      key: 'general',
      label:
        generalCount > 0
          ? `General Audit (${generalCount})`
          : 'General Audit',
      icon: <ClipboardList className="h-5 w-5" />,
      content: <GeneralAuditTable />,
    },
  ];

  return (
    <div className="space-y-6 p-6">
      {/* Page Header */}
      <div>
        <h1 className="text-3xl font-bold text-foreground">Audit Logs</h1>
        <p className="text-muted-foreground mt-1">
          Track authentication events and system changes
        </p>
      </div>

      {/* Info Banner */}
      <div className="bg-muted/30 border border-border rounded-lg p-4">
        <p className="text-sm text-muted-foreground">
          Audit logs track all authentication events and system changes. Use
          the filters to narrow down your search. Click{' '}
          <span className="font-medium">View Changes</span> to see detailed
          diffs of updates.
        </p>
      </div>

      {/* Tabs */}
      <Tabs
        tabs={tabs}
        selectedIndex={selectedIndex}
        onChange={setSelectedIndex}
        variant="pills"
      />
    </div>
  );
}
