/**
 * FormField Component
 *
 * Generic form field wrapper that integrates React Hook Form's Controller
 * with any UI component (Input, Select, Textarea, etc.)
 *
 * Usage with React Hook Form + Zod:
 * ```tsx
 * <FormField
 *   control={form.control}
 *   name="fieldName"
 *   render={({ field, fieldState }) => (
 *     <Input
 *       {...field}
 *       label="Field Label"
 *       error={fieldState.error?.message}
 *     />
 *   )}
 * />
 * ```
 */

import { ReactElement } from 'react';
import {
  Controller,
  FieldValues,
  FieldPath,
  Control,
  ControllerRenderProps,
  ControllerFieldState,
} from 'react-hook-form';

interface FormFieldProps<
  TFieldValues extends FieldValues = FieldValues,
  TName extends FieldPath<TFieldValues> = FieldPath<TFieldValues>
> {
  control: Control<TFieldValues>;
  name: TName;
  render: (props: {
    field: ControllerRenderProps<TFieldValues, TName>;
    fieldState: ControllerFieldState;
  }) => ReactElement;
}

export function FormField<
  TFieldValues extends FieldValues = FieldValues,
  TName extends FieldPath<TFieldValues> = FieldPath<TFieldValues>
>({ control, name, render }: FormFieldProps<TFieldValues, TName>) {
  return (
    <Controller
      control={control}
      name={name}
      render={({ field, fieldState }) => render({ field, fieldState })}
    />
  );
}
