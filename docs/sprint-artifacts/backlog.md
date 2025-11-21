# Product Backlog - Technical Improvements

**Project:** AI Agents - Next.js UI Migration
**Last Updated:** 2025-01-18
**Managed By:** Dev Agent (Amelia) + Scrum Master (Bob)

---

## Post-Merge Improvements from Story Reviews

### Story 3: Core Monitoring Pages - Post-Merge Items

**Review Date:** 2025-01-18
**Reviewer:** Dev Agent (Amelia)
**Status:** Approved - 3 non-blocking improvements identified

---

#### 1. Fix Jest Configuration to Exclude E2E Tests

**Type:** Bug Fix / Configuration
**Priority:** Low
**Estimated Effort:** 5 minutes
**Story ID:** 3-core-pages-monitoring
**Created From:** Code Review 2025-01-18

**Description:**
Jest is currently picking up E2E tests from the `/e2e` folder, causing 39 test failures when running `npm test`. E2E tests should only run via Playwright (`npm run test:e2e`), not Jest.

**Current State:**
- `npm test` shows 408 passing / 450 total (39 E2E failures)
- E2E tests fail in Jest context because they expect Playwright runtime

**Desired State:**
- Jest ignores `/e2e` folder completely
- `npm test` shows only unit/component tests
- Clean separation: Jest for unit tests, Playwright for E2E

**Technical Details:**
- **File:** `nextjs-ui/jest.config.js`
- **Current:** Missing `testPathIgnorePatterns` config
- **Fix:** Add `testPathIgnorePatterns: ['/node_modules/', '/e2e/']`

**Implementation:**
```javascript
// nextjs-ui/jest.config.js
const nextJest = require('next/jest')

const createJestConfig = nextJest({
  dir: './',
})

const customJestConfig = {
  setupFilesAfterEnv: ['<rootDir>/jest.setup.js'],
  testEnvironment: 'jest-environment-jsdom',
  testPathIgnorePatterns: ['/node_modules/', '/e2e/'], // ← ADD THIS LINE
  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/$1',
  },
  collectCoverageFrom: [
    'app/**/*.{js,jsx,ts,tsx}',
    'components/**/*.{js,jsx,ts,tsx}',
    'lib/**/*.{js,jsx,ts,tsx}',
    '!**/*.d.ts',
    '!**/node_modules/**',
  ],
  coverageThresholds: {
    global: {
      branches: 70,
      functions: 70,
      lines: 70,
      statements: 70,
    },
  },
}

module.exports = createJestConfig(customJestConfig)
```

**Acceptance Criteria:**
- [ ] `testPathIgnorePatterns: ['/node_modules/', '/e2e/']` added to jest.config.js
- [ ] `npm test` runs without E2E test failures
- [ ] Test count decreases from 450 to ~411 (only unit/component tests)
- [ ] `npm run test:e2e` still runs Playwright tests correctly

**References:**
- Jest docs: https://jestjs.io/docs/configuration#testpathignorepatterns-arraystring
- Code review: Story 3 (3-core-pages-monitoring.md)

---

#### 2. Enable TypeScript noUncheckedIndexedAccess (Optional Enhancement)

**Type:** Enhancement / Type Safety
**Priority:** Optional
**Estimated Effort:** 1-2 hours
**Story ID:** 3-core-pages-monitoring
**Created From:** Code Review 2025-01-18

**Description:**
Enable `noUncheckedIndexedAccess: true` in TypeScript config for safer array and object access. This prevents undefined access errors by forcing null checks before accessing array elements or object properties.

**Current State:**
- TypeScript allows unchecked array access like `data[0]` without verifying array length
- Potential runtime errors if array is empty

**Desired State:**
- TypeScript enforces null checks: `const first = data[0]` → type is `T | undefined`
- Forces safe access patterns: `data.length > 0 ? data[0] : null`

**Benefits:**
- Prevents undefined access errors in production
- Catches potential bugs at compile time
- Aligns with modern TypeScript best practices (2025)

**Trade-offs:**
- Requires updating existing code with null checks
- May increase code verbosity slightly
- Minimal impact on developer velocity

**Technical Details:**
- **File:** `nextjs-ui/tsconfig.json`
- **Change:** Add `"noUncheckedIndexedAccess": true` to `compilerOptions`

**Implementation:**
```json
{
  "compilerOptions": {
    "target": "ES2017",
    "lib": ["dom", "dom.iterable", "esnext"],
    "allowJs": true,
    "skipLibCheck": true,
    "strict": true,
    "noUncheckedIndexedAccess": true,  // ← ADD THIS LINE
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "plugins": [{ "name": "next" }],
    "paths": {
      "@/*": ["./*"]
    }
  }
}
```

**Acceptance Criteria:**
- [ ] `noUncheckedIndexedAccess: true` added to tsconfig.json
- [ ] All TypeScript compilation errors resolved
- [ ] Null checks added where needed (e.g., `data[0]` → `data.length > 0 ? data[0] : null`)
- [ ] `npm run build` succeeds
- [ ] All tests still pass

**Estimated Code Changes:**
- Likely 10-20 files affected (charts, tables, array transformations)
- Pattern: `arr[0]` → `arr[0] ?? defaultValue` or `arr.length > 0 ? arr[0] : null`

**References:**
- TypeScript docs: https://www.typescriptlang.org/tsconfig#noUncheckedIndexedAccess
- Code review: Story 3 (3-core-pages-monitoring.md)

---

#### 3. Add React Error Boundaries to Chart Components (Optional Enhancement)

**Type:** Enhancement / Resilience
**Priority:** Optional
**Estimated Effort:** 2-3 hours
**Story ID:** 3-core-pages-monitoring
**Created From:** Code Review 2025-01-18

**Description:**
Wrap Recharts components in React Error Boundaries to prevent full page crashes if a chart throws an unexpected error. Improves production resilience by isolating chart failures.

**Current State:**
- Charts (LineChart, QueueGauge, ExecutionChart) render without error boundaries
- If Recharts throws an error, the entire page crashes (white screen)
- User loses access to all dashboard functionality

**Desired State:**
- Charts wrapped in error boundaries with fallback UI
- Chart errors display user-friendly error message
- Rest of dashboard remains functional
- Error logged to monitoring service (e.g., Sentry, DataDog)

**Benefits:**
- Improved production resilience
- Better user experience during failures
- Isolated failures (one broken chart doesn't break entire page)
- Error tracking and monitoring

**Technical Details:**
- **Files to Update:**
  - Create `components/charts/ChartErrorBoundary.tsx`
  - Update `components/charts/LineChart.tsx`
  - Update `components/charts/QueueGauge.tsx`
  - Update `components/dashboard/agents/ExecutionChart.tsx`

**Implementation:**

**1. Create Error Boundary Component**

`components/charts/ChartErrorBoundary.tsx`:
```typescript
'use client';

import React, { Component, ReactNode } from 'react';
import { AlertCircle, RefreshCw } from 'lucide-react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
  onError?: (error: Error, errorInfo: React.ErrorInfo) => void;
}

interface State {
  hasError: boolean;
  error?: Error;
}

export class ChartErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    // Log error to monitoring service
    console.error('Chart Error:', error, errorInfo);

    // Call optional error handler
    this.props.onError?.(error, errorInfo);

    // TODO: Send to Sentry/DataDog
    // Sentry.captureException(error, { extra: errorInfo });
  }

  handleReset = () => {
    this.setState({ hasError: false, error: undefined });
  };

  render() {
    if (this.state.hasError) {
      // Custom fallback if provided
      if (this.props.fallback) {
        return this.props.fallback;
      }

      // Default fallback UI
      return (
        <div className="flex flex-col items-center justify-center p-8 bg-muted/20 rounded-lg border border-destructive/20">
          <AlertCircle className="h-12 w-12 text-destructive mb-4" />
          <h3 className="text-lg font-semibold mb-2">Chart Error</h3>
          <p className="text-sm text-muted-foreground mb-4 text-center max-w-md">
            Unable to render chart. Please try refreshing or contact support if the issue persists.
          </p>
          <button
            onClick={this.handleReset}
            className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90"
          >
            <RefreshCw className="h-4 w-4" />
            Retry
          </button>
          {process.env.NODE_ENV === 'development' && this.state.error && (
            <details className="mt-4 text-xs text-muted-foreground">
              <summary className="cursor-pointer">Error Details (dev only)</summary>
              <pre className="mt-2 p-2 bg-muted rounded text-xs overflow-auto max-w-md">
                {this.state.error.message}
                {'\n'}
                {this.state.error.stack}
              </pre>
            </details>
          )}
        </div>
      );
    }

    return this.props.children;
  }
}
```

**2. Update Chart Components**

Example for `components/charts/LineChart.tsx`:
```typescript
import { ChartErrorBoundary } from './ChartErrorBoundary';

export function LineChart({ data, lines, ... }: LineChartProps) {
  return (
    <ChartErrorBoundary>
      <ResponsiveContainer width="100%" height={height}>
        {/* existing chart code */}
      </ResponsiveContainer>
    </ChartErrorBoundary>
  );
}
```

**Acceptance Criteria:**
- [ ] `ChartErrorBoundary` component created with fallback UI
- [ ] All chart components wrapped in error boundary:
  - [ ] `components/charts/LineChart.tsx`
  - [ ] `components/charts/QueueGauge.tsx`
  - [ ] `components/dashboard/agents/ExecutionChart.tsx`
- [ ] Error boundary displays user-friendly message
- [ ] Retry button resets error state
- [ ] Error details visible in development mode
- [ ] Tests added for error boundary:
  - [ ] Catches chart errors
  - [ ] Displays fallback UI
  - [ ] Retry button resets state
- [ ] Optional: Error logging to monitoring service (Sentry/DataDog)

**Testing Strategy:**
```typescript
// __tests__/components/charts/ChartErrorBoundary.test.tsx
import { render, screen, fireEvent } from '@testing-library/react';
import { ChartErrorBoundary } from '@/components/charts/ChartErrorBoundary';

const ThrowError = () => {
  throw new Error('Test chart error');
};

describe('ChartErrorBoundary', () => {
  it('catches errors and displays fallback UI', () => {
    render(
      <ChartErrorBoundary>
        <ThrowError />
      </ChartErrorBoundary>
    );

    expect(screen.getByText('Chart Error')).toBeInTheDocument();
    expect(screen.getByText(/Unable to render chart/)).toBeInTheDocument();
  });

  it('resets error state when retry button clicked', () => {
    const { rerender } = render(
      <ChartErrorBoundary>
        <ThrowError />
      </ChartErrorBoundary>
    );

    const retryButton = screen.getByText('Retry');
    fireEvent.click(retryButton);

    // After reset, should render children again
    rerender(
      <ChartErrorBoundary>
        <div>Chart content</div>
      </ChartErrorBoundary>
    );

    expect(screen.getByText('Chart content')).toBeInTheDocument();
  });
});
```

**References:**
- React Error Boundaries: https://react.dev/reference/react/Component#catching-rendering-errors-with-an-error-boundary
- Code review: Story 3 (3-core-pages-monitoring.md)

---

## Backlog Management Notes

**Priority Levels:**
- **High:** Blocks production or causes critical issues
- **Medium:** Important but not blocking
- **Low:** Nice to have, minor fixes
- **Optional:** Enhancements that can be deferred indefinitely

**Effort Estimates:**
- Based on developer time for implementation + testing + review
- Does not include deployment time

**Workflow:**
1. Items added to backlog during code reviews
2. Scrum Master (Bob) prioritizes items
3. Dev Agent (Amelia) picks items based on priority + capacity
4. Items moved to sprint when work begins
5. Items marked done when implemented and tested

---

**Generated By:** Dev Agent (Amelia)
**Workflow:** Code Review (Story 3: Core Monitoring Pages)
**Date:** 2025-01-18
