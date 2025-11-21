'use client';

import { useState } from 'react';
import { usePlugins, useTogglePluginStatus, useDeletePlugin } from '@/lib/hooks/usePlugins';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Input } from '@/components/ui/Input';
import { Card } from '@/components/ui/Card';
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from '@/components/ui/Table';
import { Dialog } from '@headlessui/react';
import { Plus, Search, Edit, TestTube, FileText, Trash2, Power, PowerOff } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { formatDistanceToNow } from 'date-fns';
import type { Plugin } from '@/lib/api/plugins';

export default function PluginsPage() {
  const router = useRouter();
  const { data: plugins, isLoading, error } = usePlugins();
  const toggleStatus = useTogglePluginStatus();
  const deletePlugin = useDeletePlugin();

  const [searchQuery, setSearchQuery] = useState('');
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [pluginToDelete, setPluginToDelete] = useState<Plugin | null>(null);

  // Filter plugins by search query
  const filteredPlugins = plugins?.filter((plugin) =>
    plugin.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  // Handle status toggle with optimistic update
  const handleToggleStatus = (plugin: Plugin) => {
    const newStatus = plugin.status === 'active' ? 'inactive' : 'active';
    toggleStatus.mutate({ id: plugin.id, status: newStatus });
  };

  // Handle delete confirmation
  const handleDeleteClick = (plugin: Plugin) => {
    setPluginToDelete(plugin);
    setDeleteDialogOpen(true);
  };

  const handleDeleteConfirm = () => {
    if (pluginToDelete) {
      deletePlugin.mutate(pluginToDelete.id, {
        onSuccess: () => {
          setDeleteDialogOpen(false);
          setPluginToDelete(null);
        },
      });
    }
  };

  // Loading state
  if (isLoading) {
    return (
      <div className="p-6">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-2xl font-bold">Plugins</h1>
        </div>
        <Card className="p-6">
          <div className="space-y-4">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="h-16 bg-muted animate-pulse rounded" />
            ))}
          </div>
        </Card>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="p-6">
        <Card className="p-6">
          <p className="text-destructive">Failed to load plugins: {error.message}</p>
        </Card>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold">Plugins</h1>
          <p className="text-muted-foreground">
            Manage external system integrations (webhooks and polling)
          </p>
        </div>
        <Button onClick={() => router.push('/dashboard/plugins/new')}>
          <Plus className="h-4 w-4 mr-2" />
          Add Plugin
        </Button>
      </div>

      {/* Search Bar */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input
          type="search"
          placeholder="Search plugins by name..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="pl-10"
        />
      </div>

      {/* Plugins Table */}
      <Card>
        {!filteredPlugins || filteredPlugins.length === 0 ? (
          <div className="p-12 text-center">
            <FileText className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
            <h3 className="text-lg font-semibold mb-2">
              {searchQuery ? 'No plugins found' : 'No plugins configured'}
            </h3>
            <p className="text-muted-foreground mb-4">
              {searchQuery
                ? 'Try adjusting your search query'
                : 'Add a plugin to sync external data'}
            </p>
            {!searchQuery && (
              <Button onClick={() => router.push('/dashboard/plugins/new')}>
                <Plus className="h-4 w-4 mr-2" />
                Add Your First Plugin
              </Button>
            )}
          </div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Plugin Name</TableHead>
                <TableHead>Type</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Last Sync</TableHead>
                <TableHead>Sync Frequency</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredPlugins.map((plugin) => (
                <TableRow
                  key={plugin.id}
                  className="cursor-pointer hover:bg-muted/50"
                  onClick={() => router.push(`/dashboard/plugins/${plugin.id}`)}
                >
                  <TableCell className="font-medium">
                    {plugin.name}
                  </TableCell>
                  <TableCell>
                    <Badge variant={plugin.type === 'webhook' ? 'default' : 'info'}>
                      {plugin.type === 'webhook' ? 'Webhook' : 'Polling'}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleToggleStatus(plugin);
                      }}
                      className="flex items-center gap-2"
                      disabled={toggleStatus.isPending}
                    >
                      <Badge variant={plugin.status === 'active' ? 'success' : 'default'}>
                        {plugin.status === 'active' ? (
                          <Power className="h-3 w-3 mr-1" />
                        ) : (
                          <PowerOff className="h-3 w-3 mr-1" />
                        )}
                        {plugin.status}
                      </Badge>
                    </button>
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {plugin.last_sync
                      ? formatDistanceToNow(new Date(plugin.last_sync), { addSuffix: true })
                      : 'Never'}
                  </TableCell>
                  <TableCell className="text-muted-foreground">{plugin.sync_frequency}</TableCell>
                  <TableCell>
                    <div className="flex justify-end gap-2">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={(e) => {
                          e.stopPropagation();
                          router.push(`/dashboard/plugins/${plugin.id}?tab=test`);
                        }}
                        title="Test Connection"
                      >
                        <TestTube className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={(e) => {
                          e.stopPropagation();
                          router.push(`/dashboard/plugins/${plugin.id}?tab=logs`);
                        }}
                        title="View Logs"
                      >
                        <FileText className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={(e) => {
                          e.stopPropagation();
                          router.push(`/dashboard/plugins/${plugin.id}`);
                        }}
                        title="Edit"
                      >
                        <Edit className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDeleteClick(plugin);
                        }}
                        title="Delete"
                        className="text-destructive hover:text-destructive"
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </Card>

      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteDialogOpen} onClose={() => setDeleteDialogOpen(false)}>
        <div className="fixed inset-0 bg-black/30 z-40" aria-hidden="true" />
        <div className="fixed inset-0 flex items-center justify-center p-4 z-50">
          <Dialog.Panel className="bg-background border rounded-lg p-6 max-w-md w-full">
            <Dialog.Title className="text-lg font-semibold mb-2">Delete Plugin?</Dialog.Title>
            <Dialog.Description className="text-muted-foreground mb-4">
              Are you sure you want to delete <strong>{pluginToDelete?.name}</strong>? This will stop
              all syncing for this plugin. Past sync data will be retained.
            </Dialog.Description>
            <div className="flex justify-end gap-3">
              <Button variant="secondary" onClick={() => setDeleteDialogOpen(false)}>
                Cancel
              </Button>
              <Button
                variant="danger"
                onClick={handleDeleteConfirm}
                disabled={deletePlugin.isPending}
              >
                {deletePlugin.isPending ? 'Deleting...' : 'Delete Plugin'}
              </Button>
            </div>
          </Dialog.Panel>
        </div>
      </Dialog>
    </div>
  );
}
