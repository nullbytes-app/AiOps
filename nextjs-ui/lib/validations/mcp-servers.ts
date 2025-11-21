/**
 * MCP Server Form Validation Schemas
 *
 * Zod schemas for MCP server CRUD operations with conditional validation
 * based on server type (HTTP, SSE, stdio)
 * following 2025 best practices
 *
 * @see https://zod.dev (Zod v3 documentation)
 */

import { z } from 'zod';

/**
 * MCP Server Type Enum
 */
export const mcpServerTypeEnum = z.enum([
  'http',
  'sse',
  'stdio'
]);

/**
 * Environment Variable Schema
 * For stdio servers that need env vars
 */
export const envVarSchema = z.object({
  key: z.string()
    .min(1, { message: "Environment variable key is required" })
    .regex(/^[A-Z_][A-Z0-9_]*$/, {
      message: "Key must be uppercase with underscores (e.g., API_KEY)"
    }),

  value: z.string()
    .min(1, { message: "Environment variable value is required" }),
});

/**
 * HTTP/SSE Connection Config Schema
 */
export const httpConnectionSchema = z.object({
  url: z.string()
    .url({ message: "Server URL must be a valid URL" }),

  headers: z.record(z.string(), z.string())
    .optional(),

  timeout: z.number()
    .int()
    .positive()
    .max(300000) // 5 minutes max
    .default(30000), // 30 seconds default
});

/**
 * Stdio Connection Config Schema
 */
export const stdioConnectionSchema = z.object({
  command: z.string()
    .min(1, { message: "Command is required for stdio servers" }),

  args: z.array(z.string()).optional().default([]),

  env: z.array(envVarSchema).optional().default([]),

  cwd: z.string()
    .optional(),
});

/**
 * Base MCP Server Schema with discriminated union for connection config
 */
export const mcpServerSchema = z.object({
  name: z.string()
    .min(2, { message: "Server name must be at least 2 characters" })
    .max(100, { message: "Server name must not exceed 100 characters" }),

  type: mcpServerTypeEnum,

  description: z.string()
    .max(500, { message: "Description must not exceed 500 characters" })
    .optional(),

  // Connection config is a discriminated union based on type
  connection_config: z.union([
    httpConnectionSchema,
    stdioConnectionSchema
  ]),

  // Health check enabled
  health_check_enabled: z.boolean()
    .default(true),

  // Active status
  is_active: z.boolean()
    .default(true),
}).refine(
  (data) => {
    // Validate connection_config matches server type
    if (data.type === 'http' || data.type === 'sse') {
      return 'url' in data.connection_config;
    } else if (data.type === 'stdio') {
      return 'command' in data.connection_config;
    }
    return false;
  },
  {
    message: "Connection configuration must match server type",
    path: ["connection_config"]
  }
);

/**
 * Helper schemas for different server types
 * These make form rendering easier
 */
export const httpMcpServerSchema = z.object({
  name: z.string()
    .min(2, { message: "Server name must be at least 2 characters" })
    .max(100, { message: "Server name must not exceed 100 characters" }),
  type: z.literal('http'),
  description: z.string()
    .max(500, { message: "Description must not exceed 500 characters" })
    .optional(),
  connection_config: httpConnectionSchema,
  health_check_enabled: z.boolean().default(true),
  is_active: z.boolean().default(true),
});

export const sseMcpServerSchema = z.object({
  name: z.string()
    .min(2, { message: "Server name must be at least 2 characters" })
    .max(100, { message: "Server name must not exceed 100 characters" }),
  type: z.literal('sse'),
  description: z.string()
    .max(500, { message: "Description must not exceed 500 characters" })
    .optional(),
  connection_config: httpConnectionSchema,
  health_check_enabled: z.boolean().default(true),
  is_active: z.boolean().default(true),
});

export const stdioMcpServerSchema = z.object({
  name: z.string()
    .min(2, { message: "Server name must be at least 2 characters" })
    .max(100, { message: "Server name must not exceed 100 characters" }),
  type: z.literal('stdio'),
  description: z.string()
    .max(500, { message: "Description must not exceed 500 characters" })
    .optional(),
  connection_config: stdioConnectionSchema,
  health_check_enabled: z.boolean().default(true),
  is_active: z.boolean().default(true),
});

/**
 * MCP Server Create Schema
 */
export const mcpServerCreateSchema = mcpServerSchema;

/**
 * MCP Server Update Schema
 * All fields optional for partial updates
 */
export const mcpServerUpdateSchema = mcpServerSchema.partial();

/**
 * Test Connection Schema
 * For testing MCP server connectivity
 */
export const mcpTestConnectionSchema = z.object({
  server_id: z.string().uuid({ message: "Invalid server ID" }),
});

/**
 * Type exports
 */
export type MCPServerType = z.infer<typeof mcpServerTypeEnum>;
export type EnvVar = z.infer<typeof envVarSchema>;
export type HTTPConnectionConfig = z.infer<typeof httpConnectionSchema>;
export type StdioConnectionConfig = z.infer<typeof stdioConnectionSchema>;
export type MCPServerFormData = z.infer<typeof mcpServerSchema>;
export type HTTPMCPServerData = z.infer<typeof httpMcpServerSchema>;
export type SSEMCPServerData = z.infer<typeof sseMcpServerSchema>;
export type StdioMCPServerData = z.infer<typeof stdioMcpServerSchema>;
export type MCPServerCreateData = z.infer<typeof mcpServerCreateSchema>;
export type MCPServerUpdateData = z.infer<typeof mcpServerUpdateSchema>;
export type MCPTestConnectionInput = z.infer<typeof mcpTestConnectionSchema>;
