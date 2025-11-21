# AI Agents - Next.js UI

Modern Next.js 14.2.15 dashboard for managing AI agents, LLM providers, MCP servers, and tenants.

**Project Status:** Active Development
**Current Story:** 4-core-pages-configuration
**Progress:** 8/11 tasks complete (73%)

---

## Tech Stack

- **Framework:** Next.js 14.2.15 (App Router)
- **Language:** TypeScript 5.x
- **Styling:** Tailwind CSS 3.4.1
- **UI Components:** shadcn/ui + Radix UI
- **Forms:** React Hook Form 7.51.0 + Zod 3.22.4
- **State Management:** TanStack Query 5.x
- **Testing:** Jest + React Testing Library + Playwright
- **Mocking:** MSW (Mock Service Worker) 2.6.5

---

## Getting Started

### Prerequisites

- Node.js 18+ (recommended: 20.x)
- npm 9+

### Installation

```bash
# Install dependencies
npm install

# Run development server
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) (or 3001 during E2E tests) to view the dashboard.

### Environment Variables

Create a `.env.local` file (see `.env.example` for template):

```bash
# API Configuration
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1

# Authentication
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=your-secret-key

# E2E Testing (optional)
NEXT_PUBLIC_E2E_TEST=false
```

---

## Available Scripts

### Development

```bash
npm run dev          # Start dev server (http://localhost:3000)
npm run build        # Production build
npm run start        # Start production server
npm run lint         # Run ESLint
npm run type-check   # Run TypeScript compiler check
```

### Testing

```bash
# Unit & Component Tests (Jest + RTL)
npm test                    # Run all unit/component tests
npm run test:watch          # Watch mode
npm run test:coverage       # Generate coverage report

# E2E Tests (Playwright)
npm run test:e2e            # Run E2E tests (headless)
npm run test:e2e:ui         # Run E2E tests with UI
npm run test:e2e:debug      # Debug mode

# Storybook
npm run storybook           # Start Storybook dev server
npm run build-storybook     # Build static Storybook
```

### Test Coverage Targets

- **Unit/Component Tests:** >80% coverage
- **E2E Tests:** Critical user flows (CRUD operations, form validation)

---

## E2E Testing Infrastructure (Updated: 2025-11-19)

### Status: ✅ Infrastructure Complete, Test Implementation Pending

The Playwright E2E testing infrastructure is fully functional and ready for test implementation.

### Key Features

1. **Fast Dev Server Startup**: Reduced from 120s timeout → ~2s actual startup
2. **Health Check Endpoint**: `/api/healthz` for reliable server detection
3. **Port Management**: Next.js on port 3001 (avoids Docker conflict on 3000)
4. **Auth Bypass**: Automatic authentication bypass in E2E mode
5. **Route Mocking**: Playwright-based API mocking (replaces MSW for E2E)
6. **MSW Build Fix**: Runtime-only imports prevent webpack bundling issues

### Running E2E Tests

```bash
# Run all E2E tests (headless)
npm run test:e2e

# Run specific test file
npx playwright test e2e/dashboard-navigation.spec.ts

# Debug mode (step through tests)
npm run test:e2e:debug

# UI mode (interactive)
npm run test:e2e:ui
```

### Current Test Results

- **Status:** Infrastructure Working ✅
- **Passing:** 7 tests (navigation, basic page rendering)
- **Failing:** 43 tests (expected - pages need full implementation)
- **Infrastructure:** Fully functional

### E2E Test Helpers

All E2E tests use helpers from `e2e/helpers.ts`:

```typescript
import { gotoAndWaitForReady, waitForDashboardHeader } from './helpers'

test('navigate to dashboard', async ({ page }) => {
  await gotoAndWaitForReady(page, '/dashboard')
  await waitForDashboardHeader(page, 'Health Dashboard')
  // ... assertions
})
```

### Files Modified (E2E Infrastructure)

1. `app/api/healthz/route.ts` - Health check endpoint (created)
2. `e2e/helpers.ts` - Playwright route mocking helpers (created)
3. `playwright.config.ts` - Port 3001 + healthz endpoint
4. `middleware.ts` - E2E auth bypass using `NEXT_PUBLIC_E2E_TEST` flag
5. `mocks/browser.ts` - Function constructor for runtime-only MSW imports
6. `components/providers/MSWProvider.tsx` - Skip MSW in E2E mode
7. All 5 E2E test files updated with new helpers

### Next Steps for E2E Tests

- ⏸️ Write configuration CRUD E2E tests (tenants, agents, providers, MCP servers)
- ⏸️ Write form validation E2E tests
- ⏸️ Run axe-core accessibility audits
- ⏸️ Implement missing page features to fix failing tests

---

## Project Structure

```
nextjs-ui/
├── app/                          # Next.js App Router
│   ├── api/                      # API routes
│   │   ├── auth/                 # NextAuth.js configuration
│   │   └── healthz/              # Health check endpoint (E2E)
│   ├── dashboard/                # Main dashboard pages
│   │   ├── agents/               # Agent management
│   │   ├── llm-providers/        # LLM provider configuration
│   │   ├── mcp-servers/          # MCP server management
│   │   ├── tenants/              # Tenant management
│   │   ├── health/               # Health monitoring
│   │   ├── agent-metrics/        # Agent performance metrics
│   │   └── ticket-processing/    # Ticket processing dashboard
│   └── layout.tsx                # Root layout
│
├── components/                   # React components
│   ├── ui/                       # shadcn/ui base components
│   ├── forms/                    # Form components
│   ├── agents/                   # Agent-specific components
│   ├── llm-providers/            # Provider components
│   ├── mcp-servers/              # MCP server components
│   ├── tenants/                  # Tenant components
│   └── providers/                # Context providers (MSW, QueryClient)
│
├── lib/                          # Utilities & business logic
│   ├── api/                      # API client functions
│   ├── hooks/                    # Custom React hooks (TanStack Query)
│   ├── validations/              # Zod schemas
│   └── utils.ts                  # Utility functions
│
├── mocks/                        # MSW mock handlers (dev only)
│   ├── handlers/                 # API endpoint handlers
│   └── browser.ts                # MSW worker setup
│
├── e2e/                          # Playwright E2E tests
│   ├── helpers.ts                # E2E test helpers
│   ├── dashboard-navigation.spec.ts
│   ├── health-dashboard.spec.ts
│   ├── agent-metrics.spec.ts
│   ├── ticket-processing.spec.ts
│   └── accessibility.spec.ts
│
├── __tests__/                    # Jest unit/component tests
│   ├── components/               # Component tests
│   ├── lib/                      # Utility tests
│   └── pages/                    # Page tests
│
└── docs/                         # Documentation
    └── implementation-guides/    # Task implementation guides
```

---

## Features Implemented

### Configuration Pages ✅
- **Tenants:** CRUD operations, agent count, delete confirmation
- **Agents:** CRUD, tool assignment, test sandbox, LLM configuration
- **LLM Providers:** CRUD, test connection, model discovery
- **MCP Servers:** CRUD, server type selection (HTTP/SSE/stdio), test connection, tool discovery, health logs

### Monitoring Dashboards ✅
- **Health Dashboard:** Service status grid, recent tickets, real-time updates
- **Agent Metrics:** Execution stats, success rate, response time charts
- **Ticket Processing:** Queue depth, processing rate, 24h trend chart

### Form Validation ✅
- Zod schemas for all entities
- React Hook Form integration
- Real-time validation
- Optimistic updates with TanStack Query

### UX Patterns ✅
- Conditional form fields (watch())
- Dynamic field arrays (useFieldArray() for env vars)
- Confirmation dialogs
- Empty states
- Loading skeletons
- Toast notifications

---

## Architecture Patterns

### Data Fetching

**TanStack Query** for all API calls:

```typescript
// lib/hooks/useAgents.ts
export const useAgents = () => {
  return useQuery({
    queryKey: ['agents'],
    queryFn: getAgents,
    staleTime: 5 * 60 * 1000, // 5 minutes
  })
}

export const useCreateAgent = () => {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: createAgent,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['agents'] })
      toast.success('Agent created successfully')
    },
  })
}
```

### Form Validation

**Zod + React Hook Form:**

```typescript
// lib/validations/agents.ts
export const agentSchema = z.object({
  name: z.string().min(1, 'Name is required'),
  description: z.string().optional(),
  llm_config: llmConfigSchema,
  tools: z.array(z.string()).default([]),
})

// components/agents/AgentForm.tsx
const form = useForm({
  resolver: zodResolver(agentSchema),
  defaultValues: agent || {},
})
```

### Conditional Forms

**React Hook Form watch():**

```typescript
const serverType = watch('type')

{serverType === 'http' && <ConnectionConfig />}
{serverType === 'stdio' && <StdioConfig />}
```

---

## Development Workflow

### Adding a New Feature

1. **Create Zod Schema** (`lib/validations/`)
2. **Create API Client** (`lib/api/`)
3. **Create React Hooks** (`lib/hooks/`)
4. **Build Components** (`components/`)
5. **Create Pages** (`app/dashboard/`)
6. **Write Tests** (`__tests__/` + `e2e/`)

### Before Committing

```bash
npm run lint           # Fix linting issues
npm run type-check     # Ensure TypeScript compiles
npm test               # Run unit tests
npm run build          # Verify production build
```

---

## Known Issues & Limitations

1. **MSW in E2E Tests:** Disabled to avoid webpack bundling issues. Use Playwright route mocking instead.
2. **Port Conflict:** Docker uses 3000, Next.js uses 3001 during E2E tests.
3. **Auth Bypass:** E2E tests bypass authentication using `NEXT_PUBLIC_E2E_TEST=true` flag.

---

## Resources

- [Next.js Documentation](https://nextjs.org/docs)
- [TanStack Query Docs](https://tanstack.com/query/latest)
- [React Hook Form Docs](https://react-hook-form.com/)
- [Zod Documentation](https://zod.dev/)
- [Playwright Docs](https://playwright.dev/)
- [shadcn/ui Components](https://ui.shadcn.com/)

---

## Contributing

See `docs/sprint-artifacts/` for current sprint stories and implementation guides.

**Current Story:** [4-core-pages-configuration.md](../docs/sprint-artifacts/4-core-pages-configuration.md)
**Handoff Doc:** [4-core-pages-configuration-handoff.md](../docs/sprint-artifacts/4-core-pages-configuration-handoff.md)

---

**Built with ❤️ by the AI Agents Team**
