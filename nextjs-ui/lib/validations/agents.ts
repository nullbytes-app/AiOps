/**
 * Agent Form Validation Schemas
 *
 * Zod schemas for agent CRUD operations with LLM configuration
 * following 2025 best practices
 *
 * @see https://zod.dev (Zod v3 documentation)
 */

import { z } from 'zod';

/**
 * Agent Type Enum
 */
export const agentTypeEnum = z.enum([
  'conversational',
  'tool_based',
  'langgraph',
  'custom'
]);

/**
 * Cognitive Architecture Enum
 */
export const cognitiveArchitectureEnum = z.enum([
  'react',
  'single_step',
  'plan_and_solve'
]);

/**
 * LLM Configuration Schema
 * Nested object for LLM provider settings
 */
export const llmConfigSchema = z.object({
  provider_id: z
    .string()
    .min(1, { message: "LLM provider is required" })
    .uuid({ message: "Invalid LLM provider" }),

  model: z
    .string()
    .min(1, { message: "Model is required" }),

  temperature: z.number()
    .min(0, { message: "Temperature must be at least 0" })
    .max(2, { message: "Temperature must not exceed 2" }),

  max_tokens: z.number()
    .int({ message: "Max tokens must be an integer" })
    .positive({ message: "Max tokens must be positive" })
    .max(128000, { message: "Max tokens must not exceed 128000" })
    .optional(),

  top_p: z.number()
    .min(0, { message: "Top P must be at least 0" })
    .max(1, { message: "Top P must not exceed 1" })
    .optional(),
});

/**
 * Base Agent Schema
 */
export const agentSchema = z.object({
  name: z
    .string()
    .min(1, { message: "Name is required" })
    .refine((val) => val.trim().length >= 2, {
      message: "Agent name must be at least 2 characters",
    })
    .refine((val) => val.trim().length <= 100, {
      message: "Agent name must not exceed 100 characters",
    }),

  type: agentTypeEnum,

  description: z.string()
    .max(500, { message: "Description must not exceed 500 characters" })
    .optional(),

  system_prompt: z
    .string()
    .min(1, { message: "System prompt is required" })
    .refine((val) => val.trim().length >= 10, {
      message: "System prompt must be at least 10 characters" })
    .refine((val) => val.trim().length <= 10000, {
      message: "System prompt must not exceed 10000 characters",
    }),

  llm_config: llmConfigSchema,

  // Tool IDs assigned to this agent (managed in Tool Assignment UI)
  tool_ids: z.array(z.string().uuid()),

  // Status active/inactive
  is_active: z.boolean(),

  // Cognitive architecture (execution strategy)
  cognitive_architecture: cognitiveArchitectureEnum.catch('react'),
});

/**
 * Agent Create Schema
 */
export const agentCreateSchema = agentSchema;

/**
 * Agent Update Schema
 * All fields optional for partial updates except tool_ids
 */
export const agentUpdateSchema = agentSchema.partial();

/**
 * Agent Test Input Schema
 * For testing agents in sandbox
 */
export const agentTestSchema = z.object({
  message: z.string()
    .min(1, { message: "Test message is required" })
    .max(2000, { message: "Test message must not exceed 2000 characters" }),

  context: z.record(z.string(), z.any())
    .optional(),
});

/**
 * Type exports
 */
export type AgentType = z.infer<typeof agentTypeEnum>;
export type LLMConfig = z.infer<typeof llmConfigSchema>;
export type AgentFormData = z.infer<typeof agentSchema>;
export type AgentCreateData = z.infer<typeof agentCreateSchema>;
export type AgentUpdateData = z.infer<typeof agentUpdateSchema>;
export type AgentTestInput = z.infer<typeof agentTestSchema>;
export type CognitiveArchitecture = z.infer<typeof cognitiveArchitectureEnum>;
