/**
 * MSW Handlers for Audit API
 *
 * Mock handlers for auth and general audit log endpoints.
 */

import { http, HttpResponse } from 'msw';
import type { AuthAuditLog, GeneralAuditLog } from '@/lib/api/audit';

/**
 * Generate mock auth audit logs
 */
function generateAuthAuditLogs(): AuthAuditLog[] {
  const eventTypes: AuthAuditLog['event_type'][] = [
    'login',
    'logout',
    'password_change',
    'password_reset',
    'failed_login',
    'account_locked',
  ];

  const users = [
    'john.doe@example.com',
    'jane.smith@example.com',
    'admin@example.com',
    'user@example.com',
  ];

  const logs: AuthAuditLog[] = [];
  const now = new Date();

  for (let i = 0; i < 50; i++) {
    const eventType =
      eventTypes[Math.floor(Math.random() * eventTypes.length)];
    const user = users[Math.floor(Math.random() * users.length)];
    const success =
      eventType === 'failed_login' || eventType === 'account_locked'
        ? false
        : Math.random() > 0.1; // 10% failure rate for other events

    const createdAt = new Date(now.getTime() - i * 3600000); // 1 hour intervals

    logs.push({
      id: `auth-log-${i + 1}`,
      user_id: success ? `user-${i + 1}` : null,
      user_email: user,
      event_type: eventType,
      success,
      ip_address: `192.168.1.${Math.floor(Math.random() * 255)}`,
      user_agent:
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
      created_at: createdAt.toISOString(),
    });
  }

  return logs.sort(
    (a, b) =>
      new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
  );
}

/**
 * Generate mock general audit logs
 */
function generateGeneralAuditLogs(): GeneralAuditLog[] {
  const actions: GeneralAuditLog['action'][] = ['create', 'update', 'delete'];
  const entityTypes: GeneralAuditLog['entity_type'][] = [
    'agent',
    'tenant',
    'mcp_server',
    'plugin',
    'prompt',
    'tool',
  ];

  const users = [
    'john.doe@example.com',
    'jane.smith@example.com',
    'admin@example.com',
  ];

  const tenants = [
    { id: 'tenant-1', name: 'Acme Corp' },
    { id: 'tenant-2', name: 'TechCorp Inc' },
    { id: 'tenant-3', name: 'StartupXYZ' },
  ];

  const logs: GeneralAuditLog[] = [];
  const now = new Date();

  for (let i = 0; i < 100; i++) {
    const action = actions[Math.floor(Math.random() * actions.length)];
    const entityType =
      entityTypes[Math.floor(Math.random() * entityTypes.length)];
    const user = users[Math.floor(Math.random() * users.length)];
    const tenant = tenants[Math.floor(Math.random() * tenants.length)];

    const createdAt = new Date(now.getTime() - i * 1800000); // 30 min intervals

    // Generate sample old/new values
    const oldValue =
      action === 'create'
        ? null
        : {
            name: `Old ${entityType} ${i}`,
            description: 'Previous description',
            status: 'active',
            config: { setting1: 'old_value' },
          };

    const newValue =
      action === 'delete'
        ? null
        : {
            name: `New ${entityType} ${i}`,
            description: 'Updated description',
            status: 'active',
            config: { setting1: 'new_value', setting2: 'added' },
          };

    logs.push({
      id: `general-log-${i + 1}`,
      user_id: `user-${Math.floor(Math.random() * 10) + 1}`,
      user_email: user,
      tenant_id: tenant.id,
      tenant_name: tenant.name,
      action,
      entity_type: entityType,
      entity_id: `${entityType}-${i + 1}`,
      old_value: oldValue,
      new_value: newValue,
      created_at: createdAt.toISOString(),
    });
  }

  return logs.sort(
    (a, b) =>
      new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
  );
}

// Generate mock data
const authAuditLogs = generateAuthAuditLogs();
const generalAuditLogs = generateGeneralAuditLogs();

/**
 * Filter auth audit logs
 */
function filterAuthLogs(
  logs: AuthAuditLog[],
  filters: Record<string, string>
): AuthAuditLog[] {
  let filtered = [...logs];

  if (filters.user_email) {
    filtered = filtered.filter((log) =>
      log.user_email?.toLowerCase().includes(filters.user_email.toLowerCase())
    );
  }

  if (filters.event_type) {
    filtered = filtered.filter((log) => log.event_type === filters.event_type);
  }

  if (filters.success !== undefined && filters.success !== '') {
    const successFilter = filters.success === 'true';
    filtered = filtered.filter((log) => log.success === successFilter);
  }

  if (filters.date_from) {
    const dateFrom = new Date(filters.date_from);
    filtered = filtered.filter(
      (log) => new Date(log.created_at) >= dateFrom
    );
  }

  if (filters.date_to) {
    const dateTo = new Date(filters.date_to);
    dateTo.setHours(23, 59, 59, 999); // End of day
    filtered = filtered.filter((log) => new Date(log.created_at) <= dateTo);
  }

  return filtered;
}

/**
 * Filter general audit logs
 */
function filterGeneralLogs(
  logs: GeneralAuditLog[],
  filters: Record<string, string>
): GeneralAuditLog[] {
  let filtered = [...logs];

  if (filters.user_email) {
    filtered = filtered.filter((log) =>
      log.user_email.toLowerCase().includes(filters.user_email.toLowerCase())
    );
  }

  if (filters.action) {
    filtered = filtered.filter((log) => log.action === filters.action);
  }

  if (filters.entity_type) {
    filtered = filtered.filter(
      (log) => log.entity_type === filters.entity_type
    );
  }

  if (filters.tenant_id) {
    filtered = filtered.filter((log) => log.tenant_id === filters.tenant_id);
  }

  if (filters.date_from) {
    const dateFrom = new Date(filters.date_from);
    filtered = filtered.filter(
      (log) => new Date(log.created_at) >= dateFrom
    );
  }

  if (filters.date_to) {
    const dateTo = new Date(filters.date_to);
    dateTo.setHours(23, 59, 59, 999); // End of day
    filtered = filtered.filter((log) => new Date(log.created_at) <= dateTo);
  }

  return filtered;
}

/**
 * Count logs in last 24 hours
 */
function count24h(logs: { created_at: string }[]): number {
  const now = new Date();
  const yesterday = new Date(now.getTime() - 24 * 3600000);
  return logs.filter((log) => new Date(log.created_at) >= yesterday).length;
}

/**
 * Audit API handlers
 */
export const auditHandlers = [
  /**
   * GET /api/v1/audit/auth
   * Fetch auth audit logs with filters
   */
  http.get('/api/v1/audit/auth', ({ request }) => {
    const url = new URL(request.url);
    const page = parseInt(url.searchParams.get('page') || '1');
    const limit = parseInt(url.searchParams.get('limit') || '100');

    // Extract filters
    const filters: Record<string, string> = {};
    url.searchParams.forEach((value, key) => {
      if (key !== 'page' && key !== 'limit') {
        filters[key] = value;
      }
    });

    // Filter logs
    const filtered = filterAuthLogs(authAuditLogs, filters);

    // Paginate
    const total = filtered.length;
    const pages = Math.ceil(total / limit);
    const start = (page - 1) * limit;
    const end = start + limit;
    const logs = filtered.slice(start, end);

    return HttpResponse.json(
      {
        logs,
        total,
        page,
        pages,
        count_24h: count24h(authAuditLogs),
      },
      { status: 200 }
    );
  }),

  /**
   * GET /api/v1/audit/general
   * Fetch general audit logs with filters
   */
  http.get('/api/v1/audit/general', ({ request }) => {
    const url = new URL(request.url);
    const page = parseInt(url.searchParams.get('page') || '1');
    const limit = parseInt(url.searchParams.get('limit') || '100');

    // Extract filters
    const filters: Record<string, string> = {};
    url.searchParams.forEach((value, key) => {
      if (key !== 'page' && key !== 'limit') {
        filters[key] = value;
      }
    });

    // Filter logs
    const filtered = filterGeneralLogs(generalAuditLogs, filters);

    // Paginate
    const total = filtered.length;
    const pages = Math.ceil(total / limit);
    const start = (page - 1) * limit;
    const end = start + limit;
    const logs = filtered.slice(start, end);

    return HttpResponse.json(
      {
        logs,
        total,
        page,
        pages,
        count_24h: count24h(generalAuditLogs),
      },
      { status: 200 }
    );
  }),

  /**
   * GET /api/v1/audit/general/:id/diff
   * Fetch audit diff for specific entry
   */
  http.get('/api/v1/audit/general/:id/diff', ({ params }) => {
    const { id } = params;
    const log = generalAuditLogs.find((l) => l.id === id);

    if (!log) {
      return HttpResponse.json(
        { error: 'Audit log not found' },
        { status: 404 }
      );
    }

    // Compute simple changes
    const changes: Record<string, any> = {};
    if (log.old_value && log.new_value) {
      const oldKeys = Object.keys(log.old_value);
      const newKeys = Object.keys(log.new_value);

      // Added fields
      newKeys.forEach((key) => {
        if (!oldKeys.includes(key)) {
          changes[key] = { added: (log.new_value as any)[key] };
        }
      });

      // Removed fields
      oldKeys.forEach((key) => {
        if (!newKeys.includes(key)) {
          changes[key] = { removed: (log.old_value as any)[key] };
        }
      });

      // Modified fields
      oldKeys.forEach((key) => {
        if (
          newKeys.includes(key) &&
          JSON.stringify((log.old_value as any)[key]) !==
            JSON.stringify((log.new_value as any)[key])
        ) {
          changes[key] = {
            old: (log.old_value as any)[key],
            new: (log.new_value as any)[key],
          };
        }
      });
    }

    return HttpResponse.json(
      {
        id: log.id,
        action: log.action,
        entity_type: log.entity_type,
        entity_id: log.entity_id,
        user_email: log.user_email,
        created_at: log.created_at,
        old_value: log.old_value,
        new_value: log.new_value,
        changes,
      },
      { status: 200 }
    );
  }),
];
