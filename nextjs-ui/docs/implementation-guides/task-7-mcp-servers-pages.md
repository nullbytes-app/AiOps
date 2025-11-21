# Task 7: MCP Servers Pages - Implementation Guide

**Created:** 2025-11-19
**Story:** 4-core-pages-configuration
**Author:** Dev Agent (Amelia)
**Research Source:** Context7 MCP (React Hook Form + Model Context Protocol documentation)

---

## Overview

This guide provides complete specifications for implementing the MCP Servers configuration pages following 2025 best practices researched via Context7 MCP.

**Acceptance Criteria:** AC-4 (MCP Servers Page) from Story 4
**Estimated Effort:** 7 hours
**Files to Create:** 11 files (3 pages + 8 components)

---

## Research Findings (Context7 MCP - 2025 Best Practices)

### React Hook Form Patterns

**1. Conditional Fields with `watch()`**
```typescript
const serverType = watch('type', 'http');

// Show URL field only for HTTP/SSE
{serverType === 'http' || serverType === 'sse' && (
  <Input {...register('connection_config.url')} />
)}

// Show command field only for stdio
{serverType === 'stdio' && (
  <Input {...register('connection_config.command')} />
)}
```

**2. Dynamic Field Arrays with `useFieldArray()`**
```typescript
const { fields, append, remove } = useFieldArray({
  control,
  name: 'connection_config.env'
});

// Add environment variable
<button onClick={() => append({ key: '', value: '' })}>
  Add Variable
</button>

// Render env vars
{fields.map((field, index) => (
  <div key={field.id}>
    <Input {...register(`connection_config.env.${index}.key`)} />
    <Input {...register(`connection_config.env.${index}.value`)} />
    <button onClick={() => remove(index)}>Delete</button>
  </div>
))}
```

### MCP Server Types (from Model Context Protocol docs)

**HTTP Server (Stateless)**
- Uses POST requests for MCP operations
- No session management
- Best for simple, stateless tools
- Configuration: `{ url: string, headers?: Record<string, string> }`

**SSE Server (Server-Sent Events)**
- Uses GET for SSE notifications
- POST for requests
- DELETE for session termination
- Session-based communication
- Configuration: `{ url: string, sessionIdGenerator: () => string }`

**stdio Server (Command-Line)**
- Spawns child process
- Communicates via stdin/stdout
- Best for local tools and scripts
- Configuration: `{ command: string, args?: string[], env?: EnvVar[], cwd?: string }`

---

## Architecture

### Directory Structure

```
nextjs-ui/
├── app/dashboard/mcp-servers/
│   ├── page.tsx                    # List page
│   ├── [id]/
│   │   └── page.tsx                # Detail page (3 tabs)
│   └── new/
│       └── page.tsx                # Create page
│
├── components/mcp-servers/
│   ├── McpServerTable.tsx          # Table with filters
│   ├── McpServerForm.tsx           # Main form with conditional fields
│   ├── ConnectionConfig.tsx        # HTTP/SSE URL configuration
│   ├── StdioConfig.tsx             # stdio command configuration
│   ├── EnvironmentVariables.tsx   # Env vars with useFieldArray
│   ├── TestConnection.tsx          # Test connection component
│   ├── ToolsList.tsx               # Discovered tools table
│   └── HealthLogs.tsx              # Health check history
│
└── lib/
    ├── validations/mcp-servers.ts  # ✅ Already exists
    ├── hooks/useMCPServers.ts      # ✅ Already exists
    └── api/mcp-servers.ts          # ✅ Already exists
```

---

## Component Specifications

### 1. McpServerTable.tsx

**Purpose:** Display MCP servers with type and status filters

**Props:**
```typescript
interface McpServerTableProps {
  // No props - uses useMCPServers hook internally
}
```

**Features:**
- Table columns: Server Name, Type (badge), Status (badge), Tools Count, Last Health Check
- Filter by type: All, HTTP, SSE, stdio (dropdown)
- Filter by status: All, Healthy, Unhealthy (tabs or dropdown)
- Search by server name (real-time)
- Pagination (20 servers per page)
- Actions: Edit, Test Connection, View Tools, Delete

**Type Badges:**
- HTTP: Blue badge with "HTTP" text
- SSE: Purple badge with "SSE" text
- stdio: Green badge with "stdio" text

**Status Badges:**
- Healthy: Green success badge with CheckCircle icon
- Unhealthy: Red destructive badge with XCircle icon
- Unknown: Gray default badge with HelpCircle icon

**Implementation Pattern:**
```typescript
'use client';

import { useMCPServers } from '@/lib/hooks/useMCPServers';
import { Table, TableHeader, TableRow, TableHead, TableBody, TableCell } from '@/components/ui/Table';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';

export function McpServerTable() {
  const { data, isLoading } = useMCPServers();
  const [typeFilter, setTypeFilter] = useState<'all' | 'http' | 'sse' | 'stdio'>('all');
  const [statusFilter, setStatusFilter] = useState<'all' | 'healthy' | 'unhealthy'>('all');

  // Filter logic
  const filtered = data?.filter(server => {
    if (typeFilter !== 'all' && server.type !== typeFilter) return false;
    if (statusFilter !== 'all' && server.status !== statusFilter) return false;
    return true;
  });

  return (
    <div>
      {/* Filters */}
      <div className="flex gap-4 mb-6">
        <select value={typeFilter} onChange={(e) => setTypeFilter(e.target.value)}>
          <option value="all">All Types</option>
          <option value="http">HTTP</option>
          <option value="sse">SSE</option>
          <option value="stdio">stdio</option>
        </select>
        <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
          <option value="all">All Status</option>
          <option value="healthy">Healthy</option>
          <option value="unhealthy">Unhealthy</option>
        </select>
      </div>

      {/* Table */}
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Server Name</TableHead>
            <TableHead>Type</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>Tools Count</TableHead>
            <TableHead>Last Health Check</TableHead>
            <TableHead>Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {filtered?.map(server => (
            <TableRow key={server.id}>
              <TableCell>{server.name}</TableCell>
              <TableCell>
                <Badge variant={getTypeBadgeVariant(server.type)}>
                  {server.type.toUpperCase()}
                </Badge>
              </TableCell>
              <TableCell>
                <Badge variant={getStatusBadgeVariant(server.status)}>
                  {server.status}
                </Badge>
              </TableCell>
              <TableCell>{server.tools_count}</TableCell>
              <TableCell>{formatRelativeTime(server.last_health_check)}</TableCell>
              <TableCell>
                <Button size="sm" variant="ghost">Edit</Button>
                <Button size="sm" variant="ghost">Test</Button>
                <Button size="sm" variant="ghost">Delete</Button>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
```

---

### 2. McpServerForm.tsx

**Purpose:** Main form with conditional fields based on server type

**Props:**
```typescript
interface McpServerFormProps {
  server?: MCPServer; // For edit mode
  onSuccess?: () => void;
}
```

**Features:**
- Server type selection (radio buttons: HTTP, SSE, stdio)
- Conditional field rendering based on type using `watch()`
- HTTP/SSE: Shows ConnectionConfig component
- stdio: Shows StdioConfig component
- Form validation with Zod
- Optimistic updates on submit

**Key Pattern - Conditional Rendering:**
```typescript
'use client';

import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { mcpServerSchema, MCPServerFormData } from '@/lib/validations/mcp-servers';

export function McpServerForm({ server, onSuccess }: McpServerFormProps) {
  const { register, control, handleSubmit, watch, formState: { errors } } = useForm<MCPServerFormData>({
    resolver: zodResolver(mcpServerSchema),
    defaultValues: server || {
      type: 'http',
      health_check_enabled: true,
      is_active: true,
    }
  });

  // 2025 Best Practice: watch() for conditional fields
  const serverType = watch('type');

  const onSubmit = async (data: MCPServerFormData) => {
    // Submit logic
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
      {/* Name */}
      <Input
        label="Server Name *"
        {...register('name')}
        error={errors.name?.message}
      />

      {/* Type Selection */}
      <div>
        <label className="block text-sm font-medium mb-2">Server Type *</label>
        <div className="flex gap-4">
          <label className="flex items-center gap-2">
            <input type="radio" value="http" {...register('type')} />
            HTTP
          </label>
          <label className="flex items-center gap-2">
            <input type="radio" value="sse" {...register('type')} />
            SSE
          </label>
          <label className="flex items-center gap-2">
            <input type="radio" value="stdio" {...register('type')} />
            stdio
          </label>
        </div>
      </div>

      {/* Conditional Connection Config */}
      {(serverType === 'http' || serverType === 'sse') && (
        <ConnectionConfig control={control} errors={errors} />
      )}

      {serverType === 'stdio' && (
        <StdioConfig control={control} errors={errors} />
      )}

      {/* Submit */}
      <Button type="submit">
        {server ? 'Update Server' : 'Create Server'}
      </Button>
    </form>
  );
}
```

---

### 3. ConnectionConfig.tsx

**Purpose:** HTTP/SSE connection configuration fields

**Props:**
```typescript
interface ConnectionConfigProps {
  control: Control<MCPServerFormData>;
  errors: FieldErrors<MCPServerFormData>;
}
```

**Fields:**
- URL (required, validated as URL)
- Timeout (number, 30-300 seconds, default 30)
- Headers (optional, key-value pairs)

**Implementation:**
```typescript
'use client';

import { Control, FieldErrors, useFormContext } from 'react-hook-form';
import { Input } from '@/components/ui/Input';

export function ConnectionConfig({ control, errors }: ConnectionConfigProps) {
  const { register } = useFormContext();

  return (
    <div className="space-y-4 border-l-4 border-accent-blue pl-4">
      <h3 className="font-semibold">HTTP/SSE Connection</h3>

      <Input
        label="Server URL *"
        placeholder="https://mcp-server.example.com"
        {...register('connection_config.url')}
        error={errors.connection_config?.url?.message}
      />

      <Input
        label="Timeout (seconds)"
        type="number"
        defaultValue={30}
        {...register('connection_config.timeout', { valueAsNumber: true })}
        error={errors.connection_config?.timeout?.message}
      />
    </div>
  );
}
```

---

### 4. StdioConfig.tsx

**Purpose:** stdio command configuration with environment variables

**Props:**
```typescript
interface StdioConfigProps {
  control: Control<MCPServerFormData>;
  errors: FieldErrors<MCPServerFormData>;
}
```

**Fields:**
- Command (required, text input)
- Arguments (optional, space-separated or array)
- Working Directory (optional, file path)
- Environment Variables (EnvironmentVariables component)

**Implementation:**
```typescript
'use client';

import { Input } from '@/components/ui/Input';
import { EnvironmentVariables } from './EnvironmentVariables';

export function StdioConfig({ control, errors }: StdioConfigProps) {
  const { register } = useFormContext();

  return (
    <div className="space-y-4 border-l-4 border-accent-green pl-4">
      <h3 className="font-semibold">stdio Configuration</h3>

      <Input
        label="Command *"
        placeholder="npx @modelcontextprotocol/server-filesystem"
        {...register('connection_config.command')}
        error={errors.connection_config?.command?.message}
      />

      <Input
        label="Working Directory"
        placeholder="/path/to/working/directory"
        {...register('connection_config.cwd')}
        error={errors.connection_config?.cwd?.message}
      />

      <EnvironmentVariables control={control} errors={errors} />
    </div>
  );
}
```

---

### 5. EnvironmentVariables.tsx

**Purpose:** Dynamic environment variables management using `useFieldArray()`

**Props:**
```typescript
interface EnvironmentVariablesProps {
  control: Control<MCPServerFormData>;
  errors: FieldErrors<MCPServerFormData>;
}
```

**Features:**
- Add/remove environment variables dynamically
- Key validation: uppercase with underscores (e.g., API_KEY)
- Value masking for sensitive data (Eye/EyeOff toggle)
- Each field has unique ID via `useFieldArray`

**Implementation (2025 Best Practice):**
```typescript
'use client';

import { useFieldArray, Control, FieldErrors } from 'react-hook-form';
import { Input } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';
import { X, Plus, Eye, EyeOff } from 'lucide-react';
import { useState } from 'react';

export function EnvironmentVariables({ control, errors }: EnvironmentVariablesProps) {
  const { fields, append, remove } = useFieldArray({
    control,
    name: 'connection_config.env'
  });

  const [visibleValues, setVisibleValues] = useState<Set<string>>(new Set());

  const toggleVisibility = (id: string) => {
    setVisibleValues(prev => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <label className="text-sm font-medium">Environment Variables</label>
        <Button
          type="button"
          size="sm"
          variant="secondary"
          onClick={() => append({ key: '', value: '' })}
          className="gap-2"
        >
          <Plus className="h-4 w-4" />
          Add Variable
        </Button>
      </div>

      {fields.length === 0 && (
        <p className="text-sm text-muted-foreground">
          No environment variables. Click "Add Variable" to add one.
        </p>
      )}

      <div className="space-y-3">
        {fields.map((field, index) => {
          const isVisible = visibleValues.has(field.id);

          return (
            <div key={field.id} className="flex gap-2 items-start">
              <Input
                placeholder="API_KEY"
                {...register(`connection_config.env.${index}.key`)}
                error={errors.connection_config?.env?.[index]?.key?.message}
                className="flex-1"
              />

              <div className="relative flex-1">
                <Input
                  type={isVisible ? 'text' : 'password'}
                  placeholder="secret-value"
                  {...register(`connection_config.env.${index}.value`)}
                  error={errors.connection_config?.env?.[index]?.value?.message}
                />
                <button
                  type="button"
                  onClick={() => toggleVisibility(field.id)}
                  className="absolute right-2 top-1/2 -translate-y-1/2"
                >
                  {isVisible ? (
                    <EyeOff className="h-4 w-4 text-muted-foreground" />
                  ) : (
                    <Eye className="h-4 w-4 text-muted-foreground" />
                  )}
                </button>
              </div>

              <Button
                type="button"
                size="sm"
                variant="ghost"
                onClick={() => remove(index)}
                className="mt-1"
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
          );
        })}
      </div>
    </div>
  );
}
```

---

### 6. TestConnection.tsx

**Purpose:** Test MCP server connection and discover tools

**Props:**
```typescript
interface TestConnectionProps {
  serverId?: string; // For existing servers
  serverConfig?: Partial<MCPServerFormData>; // For new servers
}
```

**Features:**
- "Test Connection & Discover Tools" button
- Loading state during test
- Success: Shows response time, tools found count, expandable tool list
- Failure: Shows error message with troubleshooting hints

**API Response:**
```typescript
interface TestConnectionResponse {
  success: boolean;
  response_time_ms: number;
  tools_found: number;
  tools: Array<{
    name: string;
    description: string;
    parameters: string[];
  }>;
  error?: string;
}
```

**Implementation:**
```typescript
'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/Button';
import { Zap, CheckCircle, XCircle, ChevronDown, ChevronUp } from 'lucide-react';
import { testMCPConnection } from '@/lib/api/mcp-servers';

export function TestConnection({ serverId, serverConfig }: TestConnectionProps) {
  const [testing, setTesting] = useState(false);
  const [result, setResult] = useState<TestConnectionResponse | null>(null);
  const [expanded, setExpanded] = useState(false);

  const handleTest = async () => {
    setTesting(true);
    setResult(null);

    try {
      const response = await testMCPConnection(serverId || serverConfig);
      setResult(response);
    } catch (error) {
      setResult({
        success: false,
        response_time_ms: 0,
        tools_found: 0,
        tools: [],
        error: error instanceof Error ? error.message : 'Connection failed'
      });
    } finally {
      setTesting(false);
    }
  };

  return (
    <div className="space-y-4">
      <Button
        onClick={handleTest}
        disabled={testing}
        variant="secondary"
        className="gap-2"
      >
        {testing ? (
          <>
            <Zap className="h-4 w-4 animate-pulse" />
            Testing connection...
          </>
        ) : (
          <>
            <Zap className="h-4 w-4" />
            Test Connection & Discover Tools
          </>
        )}
      </Button>

      {result && (
        <div className={`border rounded-lg p-4 ${
          result.success ? 'border-success bg-success/10' : 'border-destructive bg-destructive/10'
        }`}>
          {result.success ? (
            <>
              <div className="flex items-center gap-2 mb-3">
                <CheckCircle className="h-5 w-5 text-success" />
                <span className="font-semibold text-success">Connected successfully</span>
              </div>

              <div className="grid grid-cols-2 gap-4 text-sm mb-3">
                <div>
                  <span className="text-muted-foreground">Response Time:</span>
                  <span className="ml-2 font-medium">{result.response_time_ms}ms</span>
                </div>
                <div>
                  <span className="text-muted-foreground">Tools Found:</span>
                  <span className="ml-2 font-medium">{result.tools_found}</span>
                </div>
              </div>

              {result.tools.length > 0 && (
                <div>
                  <button
                    onClick={() => setExpanded(!expanded)}
                    className="flex items-center gap-2 text-sm font-medium"
                  >
                    {expanded ? (
                      <ChevronUp className="h-4 w-4" />
                    ) : (
                      <ChevronDown className="h-4 w-4" />
                    )}
                    Tool List Preview
                  </button>

                  {expanded && (
                    <div className="mt-2 space-y-2">
                      {result.tools.map((tool, i) => (
                        <div key={i} className="text-sm bg-background/50 p-2 rounded">
                          <div className="font-medium">{tool.name}</div>
                          <div className="text-muted-foreground">{tool.description}</div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </>
          ) : (
            <>
              <div className="flex items-center gap-2 mb-2">
                <XCircle className="h-5 w-5 text-destructive" />
                <span className="font-semibold text-destructive">Connection failed</span>
              </div>
              <p className="text-sm">{result.error}</p>
            </>
          )}
        </div>
      )}
    </div>
  );
}
```

---

### 7. ToolsList.tsx

**Purpose:** Display tools exposed by MCP server

**Props:**
```typescript
interface ToolsListProps {
  serverId: string;
}
```

**Features:**
- Table of discovered tools
- Columns: Tool Name, Description, Parameters
- "Refresh Tools" button (triggers tool discovery)
- Empty state: "No tools discovered. Check server configuration."

**Implementation:**
```typescript
'use client';

import { useQuery } from '@tanstack/react-query';
import { getServerTools } from '@/lib/api/mcp-servers';
import { Table, TableHeader, TableRow, TableHead, TableBody, TableCell } from '@/components/ui/Table';
import { Button } from '@/components/ui/Button';
import { RefreshCw } from 'lucide-react';

export function ToolsList({ serverId }: ToolsListProps) {
  const { data, isLoading, refetch, isFetching } = useQuery({
    queryKey: ['mcp-server-tools', serverId],
    queryFn: () => getServerTools(serverId),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  if (isLoading) {
    return <div className="animate-pulse">Loading tools...</div>;
  }

  if (!data || data.length === 0) {
    return (
      <div className="text-center py-12">
        <p className="text-muted-foreground mb-4">
          No tools discovered. Check server configuration.
        </p>
        <Button onClick={() => refetch()} variant="secondary" size="sm">
          <RefreshCw className="h-4 w-4 mr-2" />
          Refresh Tools
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h3 className="text-lg font-semibold">Discovered Tools ({data.length})</h3>
        <Button
          onClick={() => refetch()}
          disabled={isFetching}
          variant="secondary"
          size="sm"
          className="gap-2"
        >
          <RefreshCw className={`h-4 w-4 ${isFetching ? 'animate-spin' : ''}`} />
          Refresh Tools
        </Button>
      </div>

      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Tool Name</TableHead>
            <TableHead>Description</TableHead>
            <TableHead>Parameters</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {data.map((tool, i) => (
            <TableRow key={i}>
              <TableCell className="font-medium">{tool.name}</TableCell>
              <TableCell>{tool.description}</TableCell>
              <TableCell>
                <code className="text-xs bg-muted px-2 py-1 rounded">
                  {tool.parameters.join(', ')}
                </code>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
```

---

### 8. HealthLogs.tsx

**Purpose:** Display health check history with auto-refresh

**Props:**
```typescript
interface HealthLogsProps {
  serverId: string;
}
```

**Features:**
- Table of last 50 health check results
- Columns: Timestamp, Status, Response Time, Error (if any)
- Auto-refresh every 30 seconds
- Manual refresh button

**Implementation:**
```typescript
'use client';

import { useQuery } from '@tanstack/react-query';
import { getServerHealthLogs } from '@/lib/api/mcp-servers';
import { Table, TableHeader, TableRow, TableHead, TableBody, TableCell } from '@/components/ui/Table';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { RefreshCw } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';

export function HealthLogs({ serverId }: HealthLogsProps) {
  const { data, isLoading, refetch, isFetching } = useQuery({
    queryKey: ['mcp-server-health-logs', serverId],
    queryFn: () => getServerHealthLogs(serverId),
    refetchInterval: 30000, // Auto-refresh every 30 seconds
    staleTime: 10000, // Consider stale after 10 seconds
  });

  if (isLoading) {
    return <div className="animate-pulse">Loading health logs...</div>;
  }

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h3 className="text-lg font-semibold">Health Check History (Last 50)</h3>
        <div className="flex items-center gap-3">
          {isFetching && (
            <span className="text-sm text-muted-foreground">Updating...</span>
          )}
          <Button
            onClick={() => refetch()}
            disabled={isFetching}
            variant="secondary"
            size="sm"
            className="gap-2"
          >
            <RefreshCw className={`h-4 w-4 ${isFetching ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>
      </div>

      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Timestamp</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>Response Time</TableHead>
            <TableHead>Error</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {data?.map((log, i) => (
            <TableRow key={i}>
              <TableCell>
                {formatDistanceToNow(new Date(log.timestamp), { addSuffix: true })}
              </TableCell>
              <TableCell>
                <Badge variant={log.status === 'healthy' ? 'success' : 'destructive'}>
                  {log.status}
                </Badge>
              </TableCell>
              <TableCell>{log.response_time_ms}ms</TableCell>
              <TableCell>
                {log.error ? (
                  <span className="text-sm text-destructive">{log.error}</span>
                ) : (
                  <span className="text-sm text-muted-foreground">-</span>
                )}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>

      <p className="text-xs text-muted-foreground text-center">
        Auto-refreshes every 30 seconds
      </p>
    </div>
  );
}
```

---

## Page Implementations

### 1. List Page (`app/dashboard/mcp-servers/page.tsx`)

**Features:**
- Uses McpServerTable component
- "Add MCP Server" button (top-right)
- Empty state when no servers

**Implementation:**
```typescript
'use client';

import { McpServerTable } from '@/components/mcp-servers/McpServerTable';
import { Button } from '@/components/ui/Button';
import { Plus } from 'lucide-react';
import Link from 'next/link';
import { useMCPServers } from '@/lib/hooks/useMCPServers';

export default function MCPServersPage() {
  const { data, isLoading } = useMCPServers();

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-foreground">MCP Servers</h1>
          <p className="text-muted-foreground mt-2">
            Manage Model Context Protocol servers and tools
          </p>
        </div>
        <Link href="/dashboard/mcp-servers/new">
          <Button className="gap-2">
            <Plus className="h-4 w-4" />
            Add MCP Server
          </Button>
        </Link>
      </div>

      {/* Empty State */}
      {!isLoading && data?.length === 0 ? (
        <div className="text-center py-24">
          <div className="text-6xl mb-4" role="img" aria-label="Server">
            🖥️
          </div>
          <h2 className="text-2xl font-bold text-foreground mb-2">
            No MCP Servers Configured
          </h2>
          <p className="text-muted-foreground max-w-md mx-auto mb-6">
            Connect servers to enable additional tools for your agents.
            MCP servers provide standardized access to external data and functionality.
          </p>
          <Link href="/dashboard/mcp-servers/new">
            <Button className="gap-2">
              <Plus className="h-4 w-4" />
              Add Your First Server
            </Button>
          </Link>
        </div>
      ) : (
        <McpServerTable />
      )}
    </div>
  );
}
```

---

### 2. Detail Page (`app/dashboard/mcp-servers/[id]/page.tsx`)

**Features:**
- 3 tabs: Configuration, Tools, Health Logs
- Breadcrumbs: Configuration > MCP Servers > [Server Name]

**Implementation:**
```typescript
'use client';

import { useMCPServer } from '@/lib/hooks/useMCPServers';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/Tabs';
import { McpServerForm } from '@/components/mcp-servers/McpServerForm';
import { ToolsList } from '@/components/mcp-servers/ToolsList';
import { HealthLogs } from '@/components/mcp-servers/HealthLogs';
import { Badge } from '@/components/ui/Badge';
import { Settings, Wrench, Activity } from 'lucide-react';

export default function MCPServerDetailPage({ params }: { params: { id: string } }) {
  const { data: server, isLoading } = useMCPServer(params.id);

  if (isLoading) {
    return <div className="animate-pulse">Loading server...</div>;
  }

  if (!server) {
    return <div>Server not found</div>;
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <div className="text-sm text-muted-foreground mb-2">
          Configuration &gt; MCP Servers &gt; {server.name}
        </div>
        <div className="flex items-center gap-3">
          <h1 className="text-3xl font-bold text-foreground">{server.name}</h1>
          <Badge variant={server.type === 'http' ? 'default' : server.type === 'sse' ? 'secondary' : 'success'}>
            {server.type.toUpperCase()}
          </Badge>
          <Badge variant={server.status === 'healthy' ? 'success' : 'destructive'}>
            {server.status}
          </Badge>
        </div>
      </div>

      {/* Tabs */}
      <Tabs defaultValue="configuration">
        <TabsList>
          <TabsTrigger value="configuration" className="gap-2">
            <Settings className="h-4 w-4" />
            Configuration
          </TabsTrigger>
          <TabsTrigger value="tools" className="gap-2">
            <Wrench className="h-4 w-4" />
            Tools ({server.tools_count})
          </TabsTrigger>
          <TabsTrigger value="health" className="gap-2">
            <Activity className="h-4 w-4" />
            Health Logs
          </TabsTrigger>
        </TabsList>

        <TabsContent value="configuration" className="mt-6">
          <McpServerForm server={server} />
        </TabsContent>

        <TabsContent value="tools" className="mt-6">
          <ToolsList serverId={params.id} />
        </TabsContent>

        <TabsContent value="health" className="mt-6">
          <HealthLogs serverId={params.id} />
        </TabsContent>
      </Tabs>
    </div>
  );
}
```

---

### 3. Create Page (`app/dashboard/mcp-servers/new/page.tsx`)

**Implementation:**
```typescript
'use client';

import { McpServerForm } from '@/components/mcp-servers/McpServerForm';
import { useRouter } from 'next/navigation';

export default function NewMCPServerPage() {
  const router = useRouter();

  const handleSuccess = () => {
    router.push('/dashboard/mcp-servers');
  };

  return (
    <div className="space-y-6 max-w-3xl">
      <div>
        <div className="text-sm text-muted-foreground mb-2">
          Configuration &gt; MCP Servers &gt; New Server
        </div>
        <h1 className="text-3xl font-bold text-foreground">Add MCP Server</h1>
        <p className="text-muted-foreground mt-2">
          Connect a new Model Context Protocol server to enable additional tools
        </p>
      </div>

      <McpServerForm onSuccess={handleSuccess} />
    </div>
  );
}
```

---

## Testing Strategy

### Component Tests

**1. McpServerForm.test.tsx**
```typescript
describe('McpServerForm', () => {
  it('shows HTTP fields when HTTP type selected', () => {
    render(<McpServerForm />);
    fireEvent.click(screen.getByLabelText('HTTP'));
    expect(screen.getByLabelText('Server URL')).toBeInTheDocument();
    expect(screen.queryByLabelText('Command')).not.toBeInTheDocument();
  });

  it('shows stdio fields when stdio type selected', () => {
    render(<McpServerForm />);
    fireEvent.click(screen.getByLabelText('stdio'));
    expect(screen.getByLabelText('Command')).toBeInTheDocument();
    expect(screen.queryByLabelText('Server URL')).not.toBeInTheDocument();
  });

  it('validates environment variable keys', async () => {
    // Test uppercase with underscores validation
  });
});
```

**2. EnvironmentVariables.test.tsx**
```typescript
describe('EnvironmentVariables', () => {
  it('adds new environment variable', () => {
    render(<EnvironmentVariables />);
    fireEvent.click(screen.getByText('Add Variable'));
    expect(screen.getAllByPlaceholderText('API_KEY')).toHaveLength(1);
  });

  it('removes environment variable', () => {
    // Test remove functionality
  });

  it('toggles value visibility', () => {
    // Test Eye/EyeOff icon toggle
  });
});
```

### E2E Tests

**e2e/mcp-server-crud.spec.ts**
```typescript
test('create HTTP MCP server', async ({ page }) => {
  await page.goto('/dashboard/mcp-servers/new');

  // Fill form
  await page.fill('[name="name"]', 'Test HTTP Server');
  await page.click('[value="http"]');
  await page.fill('[name="connection_config.url"]', 'https://mcp.example.com');

  // Test connection
  await page.click('text=Test Connection');
  await expect(page.locator('text=Connected successfully')).toBeVisible();

  // Submit
  await page.click('text=Create Server');
  await expect(page).toHaveURL('/dashboard/mcp-servers');
});

test('create stdio MCP server with env vars', async ({ page }) => {
  await page.goto('/dashboard/mcp-servers/new');

  // Fill form
  await page.fill('[name="name"]', 'Test stdio Server');
  await page.click('[value="stdio"]');
  await page.fill('[name="connection_config.command"]', 'npx mcp-server');

  // Add env var
  await page.click('text=Add Variable');
  await page.fill('[name="connection_config.env.0.key"]', 'API_KEY');
  await page.fill('[name="connection_config.env.0.value"]', 'secret');

  // Submit
  await page.click('text=Create Server');
  await expect(page).toHaveURL('/dashboard/mcp-servers');
});
```

---

## API Integration

All API functions already exist in `lib/api/mcp-servers.ts`:

```typescript
// ✅ Already implemented
export const getMCPServers = async (): Promise<MCPServer[]>;
export const getMCPServer = async (id: string): Promise<MCPServer>;
export const createMCPServer = async (data: MCPServerCreateData): Promise<MCPServer>;
export const updateMCPServer = async (id: string, data: MCPServerUpdateData): Promise<MCPServer>;
export const deleteMCPServer = async (id: string): Promise<void>;
export const testMCPConnection = async (data: any): Promise<TestConnectionResponse>;
export const getServerTools = async (id: string): Promise<Tool[]>;
export const getServerHealthLogs = async (id: string): Promise<HealthLog[]>;
```

---

## Accessibility Checklist

- [ ] All forms have proper `<label>` elements
- [ ] Error messages linked with `aria-describedby`
- [ ] Radio buttons have visible focus states
- [ ] Environment variable add/remove accessible via keyboard
- [ ] Table headers use proper `<th>` tags
- [ ] Status badges have sufficient color contrast (4.5:1)
- [ ] Test connection results announced to screen readers
- [ ] Health logs auto-refresh doesn't disrupt screen reader flow

---

## Implementation Checklist

**Pages (3 files):**
- [ ] `app/dashboard/mcp-servers/page.tsx`
- [ ] `app/dashboard/mcp-servers/[id]/page.tsx`
- [ ] `app/dashboard/mcp-servers/new/page.tsx`

**Components (8 files):**
- [ ] `components/mcp-servers/McpServerTable.tsx`
- [ ] `components/mcp-servers/McpServerForm.tsx`
- [ ] `components/mcp-servers/ConnectionConfig.tsx`
- [ ] `components/mcp-servers/StdioConfig.tsx`
- [ ] `components/mcp-servers/EnvironmentVariables.tsx`
- [ ] `components/mcp-servers/TestConnection.tsx`
- [ ] `components/mcp-servers/ToolsList.tsx`
- [ ] `components/mcp-servers/HealthLogs.tsx`

**Validation:**
- [x] Zod schemas exist (already completed)
- [x] API hooks exist (already completed)

**Testing:**
- [ ] Component tests (6 test files)
- [ ] E2E tests (2 test files)
- [ ] Accessibility audit (axe-core)

---

## Estimated Timeline

- **Component Development:** 5 hours
- **Testing:** 2 hours
- **Total:** 7 hours

---

## Notes

This implementation follows all 2025 best practices researched via Context7 MCP:

1. **Conditional Fields**: Using `watch()` from React Hook Form
2. **Dynamic Arrays**: Using `useFieldArray()` for environment variables
3. **MCP Server Types**: Supporting HTTP (stateless), SSE (session-based), stdio (command-line)
4. **Type Safety**: Full TypeScript with Zod validation
5. **Optimistic Updates**: TanStack Query mutations
6. **Accessibility**: WCAG 2.1 AA compliance
7. **Auto-Refresh**: Health logs refresh every 30 seconds

---

**Created by:** Dev Agent (Amelia)
**Date:** 2025-11-19
**Research Source:** Context7 MCP (React Hook Form + Model Context Protocol)
**Story:** 4-core-pages-configuration (Task 7)
