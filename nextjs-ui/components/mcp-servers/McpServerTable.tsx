/**
 * MCP Server Table Component
 *
 * Displays list of MCP servers with filtering, status indicators,
 * and action buttons (edit, delete, test connection).
 */

'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { Database, Edit, Trash2, TestTube, CheckCircle, XCircle, AlertCircle } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import type { MCPServer } from '@/lib/api/mcp-servers';

interface McpServerTableProps {
  servers: MCPServer[];
  onDelete: (id: string) => void;
  onTest: (id: string) => void;
}

export function McpServerTable({ servers, onDelete, onTest }: McpServerTableProps) {
  const [typeFilter, setTypeFilter] = useState<string>('all');
  const [statusFilter, setStatusFilter] = useState<string>('all');

  // Filter servers
  const filteredServers = servers.filter((server) => {
    const matchesType = typeFilter === 'all' || server.type === typeFilter;
    const matchesStatus =
      statusFilter === 'all' ||
      (statusFilter === 'active' && server.is_active) ||
      (statusFilter === 'inactive' && !server.is_active) ||
      (statusFilter === 'healthy' && server.health_status === 'healthy') ||
      (statusFilter === 'unhealthy' && server.health_status === 'unhealthy');
    return matchesType && matchesStatus;
  });

  /**
   * Get status badge component
   */
  function getStatusBadge(server: MCPServer) {
    if (!server.is_active) {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-1 rounded-md text-xs font-medium bg-gray-100 text-gray-700">
          <AlertCircle className="h-3 w-3" />
          Inactive
        </span>
      );
    }

    if (server.health_status === 'healthy') {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-1 rounded-md text-xs font-medium bg-green-100 text-green-700">
          <CheckCircle className="h-3 w-3" />
          Healthy
        </span>
      );
    }

    if (server.health_status === 'unhealthy') {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-1 rounded-md text-xs font-medium bg-red-100 text-red-700">
          <XCircle className="h-3 w-3" />
          Unhealthy
        </span>
      );
    }

    return (
      <span className="inline-flex items-center gap-1 px-2 py-1 rounded-md text-xs font-medium bg-yellow-100 text-yellow-700">
        <AlertCircle className="h-3 w-3" />
        Unknown
      </span>
    );
  }

  /**
   * Get server type badge
   */
  function getTypeBadge(type: string) {
    const colors = {
      http: 'bg-blue-100 text-blue-700',
      sse: 'bg-purple-100 text-purple-700',
      stdio: 'bg-green-100 text-green-700',
    };

    return (
      <span className={`inline-flex items-center px-2 py-1 rounded-md text-xs font-medium ${colors[type as keyof typeof colors] || 'bg-gray-100 text-gray-700'}`}>
        {type.toUpperCase()}
      </span>
    );
  }

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <label htmlFor="type-filter" className="text-sm font-medium text-text-primary">
            Type:
          </label>
          <select
            id="type-filter"
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            className="px-3 py-1.5 rounded-lg border border-border bg-white text-sm focus:outline-none focus:ring-2 focus:ring-accent-blue"
          >
            <option value="all">All</option>
            <option value="http">HTTP</option>
            <option value="sse">SSE</option>
            <option value="stdio">stdio</option>
          </select>
        </div>

        <div className="flex items-center gap-2">
          <label htmlFor="status-filter" className="text-sm font-medium text-text-primary">
            Status:
          </label>
          <select
            id="status-filter"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-3 py-1.5 rounded-lg border border-border bg-white text-sm focus:outline-none focus:ring-2 focus:ring-accent-blue"
          >
            <option value="all">All</option>
            <option value="active">Active</option>
            <option value="inactive">Inactive</option>
            <option value="healthy">Healthy</option>
            <option value="unhealthy">Unhealthy</option>
          </select>
        </div>

        <div className="ml-auto text-sm text-text-secondary">
          Showing {filteredServers.length} of {servers.length} servers
        </div>
      </div>

      {/* Table */}
      {filteredServers.length === 0 ? (
        <div className="glass-card p-12 text-center">
          <Database className="h-12 w-12 text-text-secondary mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-text-primary mb-2">No MCP Servers Found</h3>
          <p className="text-text-secondary">
            {servers.length === 0
              ? 'Get started by creating your first MCP server.'
              : 'No servers match the current filters.'}
          </p>
        </div>
      ) : (
        <div className="glass-card overflow-hidden">
          <table className="w-full">
            <thead className="bg-white/50 border-b border-border">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-semibold text-text-secondary uppercase tracking-wider">
                  Name
                </th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-text-secondary uppercase tracking-wider">
                  Type
                </th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-text-secondary uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-text-secondary uppercase tracking-wider">
                  Tools
                </th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-text-secondary uppercase tracking-wider">
                  Last Check
                </th>
                <th className="px-6 py-3 text-right text-xs font-semibold text-text-secondary uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {filteredServers.map((server) => (
                <tr key={server.id} className="hover:bg-white/30 transition-colors">
                  <td className="px-6 py-4">
                    <Link
                      href={`/dashboard/mcp-servers/${server.id}`}
                      className="font-medium text-accent-blue hover:underline"
                    >
                      {server.name}
                    </Link>
                    {server.description && (
                      <p className="text-sm text-text-secondary mt-1">{server.description}</p>
                    )}
                  </td>
                  <td className="px-6 py-4">{getTypeBadge(server.type)}</td>
                  <td className="px-6 py-4">{getStatusBadge(server)}</td>
                  <td className="px-6 py-4">
                    <span className="text-sm text-text-primary">{server.tools_count || 0}</span>
                  </td>
                  <td className="px-6 py-4">
                    {server.last_health_check ? (
                      <span className="text-sm text-text-secondary">
                        {new Date(server.last_health_check).toLocaleDateString()}
                      </span>
                    ) : (
                      <span className="text-sm text-text-secondary">—</span>
                    )}
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center justify-end gap-2">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => onTest(server.id)}
                        className="gap-1"
                        aria-label={`Test connection for ${server.name}`}
                      >
                        <TestTube className="h-4 w-4" />
                        Test
                      </Button>
                      <Link href={`/dashboard/mcp-servers/${server.id}/edit`}>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="gap-1"
                          aria-label={`Edit ${server.name}`}
                        >
                          <Edit className="h-4 w-4" />
                          Edit
                        </Button>
                      </Link>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => onDelete(server.id)}
                        className="gap-1 text-destructive hover:text-destructive hover:bg-destructive/10"
                        aria-label={`Delete ${server.name}`}
                      >
                        <Trash2 className="h-4 w-4" />
                        Delete
                      </Button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
