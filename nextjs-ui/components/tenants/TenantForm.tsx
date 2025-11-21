"use client";

import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import Image from 'next/image';
import { TenantFormData, tenantCreateSchema } from '@/lib/validations/tenants';
import { Form, FormField } from '@/components/forms';
import { Input, Textarea, Button } from '@/components/ui';
import { Tenant } from '@/lib/api/tenants';

/**
 * Tenant Form Component
 *
 * Reusable form for creating and editing tenants
 * Uses React Hook Form with Zod validation
 *
 * @example
 * ```tsx
 * <TenantForm
 *   onSubmit={handleSubmit}
 *   defaultValues={tenant}
 *   isLoading={isSubmitting}
 * />
 * ```
 */

interface TenantFormProps {
  /**
   * Form submission handler
   */
  onSubmit: (data: TenantFormData) => void;
  /**
   * Default values for editing existing tenant
   */
  defaultValues?: Partial<Tenant>;
  /**
   * Loading state for submit button
   */
  isLoading?: boolean;
  /**
   * Cancel button handler
   */
  onCancel?: () => void;
  /**
   * Form mode (create or edit)
   */
  mode?: 'create' | 'edit';
}

export function TenantForm({
  onSubmit,
  defaultValues,
  isLoading = false,
  onCancel,
  mode = 'create',
}: TenantFormProps) {
  const form = useForm<TenantFormData>({
    resolver: zodResolver(tenantCreateSchema),
    mode: 'onSubmit',  // Explicitly set validation mode
    reValidateMode: 'onChange',  // Re-validate on change after first submit
    defaultValues: {
      name: defaultValues?.name || '',
      description: defaultValues?.description || '',
      logo: defaultValues?.logo || '',
    },
  });

  // Use React Hook Form's isSubmitting for automatic double-submit prevention
  const isFormSubmitting = form.formState.isSubmitting || isLoading;

  // Helper to check if logo URL is valid and complete for preview
  const isValidLogoUrl = (url: string | undefined): boolean => {
    if (!url || url.trim().length === 0) return false;

    // Check for data URI (base64 images)
    if (url.startsWith('data:image/')) return true;

    // Check for complete HTTP(S) URL
    try {
      const parsed = new URL(url);
      return parsed.protocol === 'http:' || parsed.protocol === 'https:';
    } catch {
      return false;
    }
  };

  return (
    <Form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
      <FormField
        control={form.control}
        name="name"
        render={({ field, fieldState }) => (
          <Input
            {...field}
            label="Tenant Name"
            placeholder="Enter tenant name"
            error={fieldState.error?.message}
            helpText="A unique name for this tenant"
            required
          />
        )}
      />

      <FormField
        control={form.control}
        name="description"
        render={({ field, fieldState }) => (
          <Textarea
            {...field}
            label="Description"
            placeholder="Enter tenant description (optional)"
            error={fieldState.error?.message}
            helpText="Brief description of this tenant's purpose"
            rows={3}
          />
        )}
      />

      <FormField
        control={form.control}
        name="logo"
        render={({ field, fieldState }) => (
          <Input
            {...field}
            label="Logo URL"
            placeholder="https://example.com/logo.png or data:image/png;base64,..."
            error={fieldState.error?.message}
            helpText="URL or base64-encoded image (PNG, JPEG, GIF, WebP)"
          />
        )}
      />

      {/* Logo Preview */}
      {isValidLogoUrl(form.watch('logo')) && (
        <div className="glass-card p-4">
          <p className="text-sm font-medium text-text-secondary mb-2">
            Logo Preview
          </p>
          <div className="relative w-64 h-32">
            <Image
              src={form.watch('logo') || ''}
              alt="Tenant logo preview"
              fill
              className="object-contain rounded-lg"
              onError={(e) => {
                e.currentTarget.src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTAwIiBoZWlnaHQ9IjEwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwIiBoZWlnaHQ9IjEwMCIgZmlsbD0iI2VlZSIvPjx0ZXh0IHg9IjUwJSIgeT0iNTAlIiBmb250LWZhbWlseT0ic2Fucy1zZXJpZiIgZm9udC1zaXplPSIxNCIgZmlsbD0iIzk5OSIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZHk9Ii4zZW0iPkludmFsaWQ8L3RleHQ+PC9zdmc+';
              }}
              unoptimized
            />
          </div>
        </div>
      )}

      <div className="flex gap-3 justify-end pt-4 border-t border-white/20">
        {onCancel && (
          <Button
            type="button"
            variant="ghost"
            onClick={onCancel}
            disabled={isFormSubmitting}
          >
            Cancel
          </Button>
        )}
        <Button
          type="submit"
          variant="primary"
          isLoading={isFormSubmitting}
          disabled={isFormSubmitting}
        >
          {mode === 'create' ? 'Create Tenant' : 'Update Tenant'}
        </Button>
      </div>
    </Form>
  );
}
