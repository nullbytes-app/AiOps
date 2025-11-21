/**
 * Form Component
 *
 * Wrapper for React Hook Form with Zod validation
 * Provides form context and handles submission
 *
 * Usage:
 * ```tsx
 * const form = useForm({
 *   resolver: zodResolver(schema),
 *   defaultValues: { name: '' }
 * });
 *
 * <Form onSubmit={form.handleSubmit(onSubmit)}>
 *   <FormField
 *     control={form.control}
 *     name="name"
 *     render={({ field, fieldState }) => (
 *       <Input {...field} error={fieldState.error?.message} />
 *     )}
 *   />
 *   <Button type="submit">Submit</Button>
 * </Form>
 * ```
 */

import { FormHTMLAttributes, ReactNode } from 'react';
import { cn } from '@/lib/utils/cn';

interface FormProps extends FormHTMLAttributes<HTMLFormElement> {
  children: ReactNode;
  className?: string;
}

export function Form({ children, className, onSubmit, ...props }: FormProps) {
  return (
    <form
      onSubmit={onSubmit}
      className={cn('space-y-6', className)}
      {...props}
    >
      {children}
    </form>
  );
}
