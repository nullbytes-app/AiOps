import { z } from 'zod';

const tenantSchema = z.object({
  name: z
    .string({ required_error: "Name is required" })
    .min(1, "Name is required")
    .trim()
    .min(3, "Name must be at least 3 characters")
    .max(50, "Name must be at most 50 characters"),
  
  description: z.string().optional(),
  logo: z.string().optional()
});

// Test 1: Empty name
console.log('\n=== Test 1: Empty name ===');
try {
  tenantSchema.parse({ name: '', description: '', logo: '' });
  console.log('FAIL: Should have thrown error');
} catch (err) {
  console.log('✓ Validation error:', err.errors[0].message);
}

// Test 2: Name with just spaces
console.log('\n=== Test 2: Name with spaces ===');
try {
  tenantSchema.parse({ name: '   ', description: '', logo: '' });
  console.log('FAIL: Should have thrown error');
} catch (err) {
  console.log('✓ Validation error:', err.errors[0].message);
}

// Test 3: Name too short after trim
console.log('\n=== Test 3: Name "AB" ===');
try {
  tenantSchema.parse({ name: 'AB', description: '', logo: '' });
  console.log('FAIL: Should have thrown error');
} catch (err) {
  console.log('✓ Validation error:', err.errors[0].message);
}

// Test 4: Valid name
console.log('\n=== Test 4: Valid name "Valid Tenant" ===');
try {
  const result = tenantSchema.parse({ name: 'Valid Tenant', description: '', logo: '' });
  console.log('✓ SUCCESS:', result);
} catch (err) {
  console.log('FAIL:', err.errors[0].message);
}
