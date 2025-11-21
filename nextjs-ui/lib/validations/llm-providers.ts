/**
 * LLM Provider Form Validation Schemas
 *
 * Zod schemas for LLM provider CRUD operations with API key validation
 * following 2025 best practices
 *
 * @see https://zod.dev (Zod v3 documentation)
 */

import { z } from 'zod';

/**
 * Provider Type Enum
 */
export const providerTypeEnum = z.enum([
  'openai',
  'anthropic',
  'openrouter',
  'custom'
]);

/**
 * Model Configuration Schema
 * For defining available models in a provider
 */
export const modelConfigSchema = z.object({
  id: z.string()
    .min(1, { message: "Model ID is required" }),

  name: z.string()
    .min(1, { message: "Model name is required" }),

  context_window: z.number()
    .int()
    .positive()
    .optional(),

  max_tokens: z.number()
    .int()
    .positive()
    .optional(),
});

/**
 * Base LLM Provider Schema
 */
export const llmProviderSchema = z.object({
  name: z.string()
    .min(2, { message: "Provider name must be at least 2 characters" })
    .max(100, { message: "Provider name must not exceed 100 characters" }),

  type: providerTypeEnum,

  // API Key - required, masked in display
  api_key: z.string()
    .min(10, { message: "API key must be at least 10 characters" })
    .regex(/^[a-zA-Z0-9_\-\.]+$/, {
      message: "API key contains invalid characters"
    }),

  // Base URL - optional for custom providers
  base_url: z.string()
    .url({ message: "Base URL must be a valid URL" })
    .optional()
    .or(z.literal('')),

  // Available models
  models: z.array(modelConfigSchema)
    .min(1, { message: "At least one model must be configured" })
    .optional(),

  // Default model for this provider
  default_model: z.string()
    .optional(),

  // Active status
  is_active: z.boolean(),
}).refine(
  (data) => {
    // If custom type, base_url is required
    if (data.type === 'custom') {
      return !!data.base_url && data.base_url.length > 0;
    }
    return true;
  },
  {
    message: "Base URL is required for custom providers",
    path: ["base_url"]
  }
).refine(
  (data) => {
    // If default_model is set, it must exist in models array
    if (data.default_model && data.models?.length && data.models.length > 0) {
      return data.models.some(m => m.id === data.default_model);
    }
    return true;
  },
  {
    message: "Default model must be one of the configured models",
    path: ["default_model"]
  }
);

/**
 * LLM Provider Create Schema
 */
export const llmProviderCreateSchema = llmProviderSchema;

/**
 * LLM Provider Update Schema
 * All fields optional except models must have at least one if present
 */
export const llmProviderUpdateSchema = llmProviderSchema.partial();

/**
 * Test Connection Schema
 * For testing provider connectivity
 */
export const testConnectionSchema = z.object({
  provider_id: z.string().uuid({ message: "Invalid provider ID" }),
  test_prompt: z.string()
    .default("Hello, this is a test message."),
});

/**
 * Type exports
 */
export type ProviderType = z.infer<typeof providerTypeEnum>;
export type ModelConfig = z.infer<typeof modelConfigSchema>;
export type LLMProviderFormData = z.infer<typeof llmProviderSchema>;
export type LLMProviderCreateData = z.infer<typeof llmProviderCreateSchema>;
export type LLMProviderUpdateData = z.infer<typeof llmProviderUpdateSchema>;
export type TestConnectionInput = z.infer<typeof testConnectionSchema>;
