import { cn } from '@/lib/utils/cn'

describe('cn utility function', () => {
  it('merges single className', () => {
    expect(cn('text-red-500')).toBe('text-red-500')
  })

  it('merges multiple classNames', () => {
    const result = cn('text-red-500', 'bg-blue-500')
    expect(result).toContain('text-red-500')
    expect(result).toContain('bg-blue-500')
  })

  it('handles conditional classes', () => {
    expect(cn('base-class', true && 'active-class')).toContain('active-class')
    expect(cn('base-class', false && 'hidden-class')).not.toContain('hidden-class')
  })

  it('handles undefined and null values', () => {
    expect(cn('base', undefined, null, 'end')).not.toContain('undefined')
    expect(cn('base', undefined, null, 'end')).not.toContain('null')
  })

  it('deduplicates conflicting Tailwind classes', () => {
    const result = cn('px-4', 'px-6')
    // tailwind-merge should keep only the last px-* class
    expect(result).toBe('px-6')
  })

  it('handles object syntax for conditional classes', () => {
    const result = cn({
      'text-red-500': true,
      'text-blue-500': false,
    })
    expect(result).toContain('text-red-500')
    expect(result).not.toContain('text-blue-500')
  })

  it('handles array of classes', () => {
    const result = cn(['text-sm', 'font-bold'])
    expect(result).toContain('text-sm')
    expect(result).toContain('font-bold')
  })

  it('combines all input types', () => {
    const result = cn(
      'base-class',
      ['array-class'],
      { 'conditional-class': true },
      undefined,
      'final-class'
    )
    expect(result).toContain('base-class')
    expect(result).toContain('array-class')
    expect(result).toContain('conditional-class')
    expect(result).toContain('final-class')
  })

  it('handles empty input', () => {
    expect(cn()).toBe('')
  })

  it('resolves Tailwind conflicts correctly', () => {
    // When same property has multiple values, last one wins
    expect(cn('p-4', 'p-8')).toBe('p-8')
    expect(cn('bg-red-500', 'bg-blue-500')).toBe('bg-blue-500')
  })
})
