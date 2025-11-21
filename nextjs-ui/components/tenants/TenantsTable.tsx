"use client";

import Image from 'next/image';
import { Tenant } from '@/lib/api/tenants';
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/Table';
import { Button, Badge } from '@/components/ui';
import { Edit, Trash2, Users } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';

/**
 * Tenants Table Component
 *
 * Displays list of tenants with actions (edit, delete)
 */

interface TenantsTableProps {
  tenants: Tenant[];
  onEdit: (tenant: Tenant) => void;
  onDelete: (tenant: Tenant) => void;
  isLoading?: boolean;
}

export function TenantsTable({
  tenants,
  onEdit,
  onDelete,
  isLoading = false,
}: TenantsTableProps) {
  if (isLoading) {
    return (
      <div className="glass-card p-12 text-center">
        <div className="inline-block w-8 h-8 border-4 border-accent-blue border-t-transparent rounded-full animate-spin" />
        <p className="mt-4 text-text-secondary">Loading tenants...</p>
      </div>
    );
  }

  return (
    <div className="glass-card overflow-hidden">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Name</TableHead>
            <TableHead>Description</TableHead>
            <TableHead>Agents</TableHead>
            <TableHead>Created</TableHead>
            <TableHead className="text-right">Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {tenants.map((tenant) => (
            <TableRow key={tenant.id}>
              <TableCell>
                <div className="flex items-center gap-3">
                  {tenant.logo && (
                    <div className="relative w-8 h-8 flex-shrink-0">
                      <Image
                        src={tenant.logo}
                        alt={`${tenant.name} logo`}
                        fill
                        className="rounded object-cover"
                        onError={(e) => {
                          e.currentTarget.style.display = 'none';
                        }}
                        unoptimized
                      />
                    </div>
                  )}
                  <div>
                    <div className="font-medium text-text-primary">
                      {tenant.name}
                    </div>
                    <div className="text-xs text-text-secondary">
                      {tenant.tenant_id}
                    </div>
                  </div>
                </div>
              </TableCell>
              <TableCell>
                <div className="max-w-md truncate text-text-secondary">
                  {tenant.description || '—'}
                </div>
              </TableCell>
              <TableCell>
                <Badge variant="info">
                  <Users className="w-3 h-3 mr-1" />
                  {tenant.agent_count || 0}
                </Badge>
              </TableCell>
              <TableCell>
                <div className="text-sm text-text-secondary">
                  {formatDistanceToNow(new Date(tenant.created_at), {
                    addSuffix: true,
                  })}
                </div>
              </TableCell>
              <TableCell>
                <div className="flex gap-2 justify-end">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => onEdit(tenant)}
                    title="Edit tenant"
                  >
                    <Edit className="w-4 h-4" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => onDelete(tenant)}
                    title="Delete tenant"
                  >
                    <Trash2 className="w-4 h-4 text-red-500" />
                  </Button>
                </div>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
