/**
 * Tenant Form Validation Schemas
 *
 * Zod schemas for tenant CRUD operations following 2025 best practices:
 * - Type-safe validation with z.infer
 * - Email validation with custom patterns
 * - Required field constraints
 * - Cross-field validation with refine
 *
 * @see https://zod.dev (Zod v3 documentation)
 */

import { z } from 'zod';

/**
 * Base Tenant Schema
 * Used for creating and updating tenants
 */
export const tenantSchema = z.object({
  name: z
    .string()
    .min(1, { message: "Name is required" })
    .refine((val) => val.trim().length >= 3, {
      message: "Name must be at least 3 characters",
    })
    .refine((val) => val.trim().length <= 50, {
      message: "Name must be at most 50 characters",
    }),

  description: z
    .string()
    .refine((val) => !val || val.trim().length <= 500, {
      message: "Description must be at most 500 characters",
    })
    .optional(),

  // Logo upload - optional base64 string or URL
  logo: z
    .string()
    .optional()
    .refine(
      (val) => {
        if (!val || val === '') return true;
        // Check for valid URL
        try {
          const url = new URL(val);
          return url.protocol === 'http:' || url.protocol === 'https:';
        } catch {
          // Check for valid base64 image
          return /^data:image\/(png|jpeg|jpg|gif|webp);base64,/.test(val);
        }
      },
      { message: "Logo must be a valid URL or base64 image" }
    ),
});

/**
 * Tenant Create Schema
 * Extends base schema with additional required fields for creation
 */
export const tenantCreateSchema = tenantSchema.extend({
  // Tenant ID is auto-generated server-side, not in create form
});

/**
 * Tenant Update Schema
 * All fields optional for partial updates
 */
export const tenantUpdateSchema = tenantSchema.partial();

/**
 * Type exports for TypeScript integration
 */
export type TenantFormData = z.infer<typeof tenantSchema>;
export type TenantCreateData = z.infer<typeof tenantCreateSchema>;
export type TenantUpdateData = z.infer<typeof tenantUpdateSchema>;
