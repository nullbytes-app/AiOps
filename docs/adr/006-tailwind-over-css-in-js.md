# ADR 006: Tailwind CSS Over CSS-in-JS for Styling

**Status:** Accepted
**Date:** 2025-01-17
**Deciders:** Ravi (Product Owner), Architecture Team
**Technical Story:** Story 0 - User Research & Design Preparation

---

## Context

The Next.js UI needs a styling solution for:
- **Glassmorphism design:** Backdrop blur, transparency, shadows
- **Responsive layouts:** 4 breakpoints (mobile, tablet, desktop, wide)
- **Dark mode:** Light theme primary, dark mode secondary
- **Component variants:** Buttons (5 variants), cards (3 variants)
- **Design tokens:** Integration with `design-tokens.json`
- **Performance:** Fast builds, small bundle size

**Candidates Evaluated:**
1. **Tailwind CSS** - Utility-first CSS framework
2. **Styled Components** - CSS-in-JS library
3. **Emotion** - CSS-in-JS library (similar to styled-components)
4. **CSS Modules** - Scoped CSS files
5. **Plain CSS** - Traditional stylesheets

---

## Decision

We will use **Tailwind CSS** as the primary styling solution for the Next.js UI.

---

## Rationale

### Why Tailwind CSS?

**1. Design Token Integration:**

Tailwind config maps directly to our `design-tokens.json`:
```javascript
// tailwind.config.ts
import designTokens from './docs/design-system/design-tokens.json'

export default {
  theme: {
    extend: {
      colors: {
        glass: {
          bg: designTokens.colors.glass.bg.value,
          border: designTokens.colors.glass.border.value
        },
        accent: {
          blue: designTokens.colors.accent.blue.value,
          purple: designTokens.colors.accent.purple.value,
          // ... all accent colors
        }
      },
      spacing: {
        xs: designTokens.spacing.xs.value,
        sm: designTokens.spacing.sm.value,
        // ... all spacing values
      },
      borderRadius: {
        glass: designTokens.borderRadius.xl.value
      }
    }
  }
}
```

**Result:** Design tokens → Tailwind classes (`bg-glass-bg`, `text-accent-purple`, `rounded-glass`)

**2. Zero Runtime Overhead:**

Tailwind is **build-time only**:
- No JavaScript runtime (unlike styled-components)
- CSS generated at build time, shipped as static file
- No style calculation on client (instant page load)

**Comparison:**
```
Tailwind CSS: 0KB runtime JavaScript
Styled Components: ~13KB runtime JavaScript
Emotion: ~11KB runtime JavaScript
```

**3. Glassmorphism Support:**

Tailwind's arbitrary values handle complex styles:
```tsx
<div className="
  bg-white/75
  backdrop-blur-[32px]
  backdrop-saturate-[180%]
  backdrop-brightness-110
  border-2 border-white
  rounded-[24px]
  shadow-[0_8px_32px_rgba(0,0,0,0.08)]
">
  Glass card
</div>
```

**4. Responsive Design:**

Breakpoints built-in:
```tsx
<div className="
  grid
  grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4
  gap-4 lg:gap-6
  p-4 lg:p-8
">
  Responsive grid
</div>
```

**5. Dark Mode:**

Toggle dark mode with `dark:` prefix:
```tsx
<div className="
  bg-white dark:bg-gray-900
  text-gray-900 dark:text-white
  border-gray-200 dark:border-gray-700
">
  Auto dark mode
</div>
```

**6. Performance:**

Tailwind uses **PurgeCSS** to remove unused styles:
- Development: Full Tailwind CSS (~3MB uncompressed)
- Production: Only used classes (~10-20KB gzipped)

**Comparison (production bundle):**
```
Tailwind CSS: 12KB gzipped (purged)
Styled Components: 13KB runtime + 20KB styles = 33KB
CSS Modules: 15KB (all modules)
```

**7. Developer Experience:**

- **IntelliSense:** VSCode autocompletes classes (`bg-[autocomplete]`)
- **No naming:** No need to name classes (`.card-header`, `.button-primary`)
- **Consistency:** Utility classes enforce design system
- **Fast iteration:** Change classes in JSX, no context switching to CSS files

**8. Maintainability:**

All styles colocated with components:
```tsx
// Component + styles in one place
function GlassCard({ children }) {
  return (
    <div className="bg-glass-bg backdrop-blur-md rounded-glass p-6 shadow-md">
      {children}
    </div>
  )
}
```

No orphaned CSS files when components are deleted.

### Why Not Styled Components?

**Styled Components Strengths:**
- Dynamic styling based on props
- Scoped styles (no global namespace)
- Full CSS syntax support

**Styled Components Limitations:**
- **13KB runtime JavaScript** (Tailwind = 0KB)
- **Slower SSR:** Styles must be extracted and injected during SSR
- **Flash of Unstyled Content (FOUC):** Styles load after JavaScript
- **More boilerplate:** Must create styled component for each element
- **Debugging:** Generated class names are hashed (`sc-abc123`)

**Verdict:** Runtime overhead and SSR complexity outweigh benefits.

### Why Not Emotion?

**Emotion Strengths:**
- Similar to styled-components
- Slightly smaller bundle (11KB vs 13KB)

**Emotion Limitations:**
- **Same runtime overhead as styled-components**
- **Same SSR complexity**
- **Less Next.js integration** (styled-components has official Next.js plugin)

**Verdict:** Same issues as styled-components, less ecosystem support.

### Why Not CSS Modules?

**CSS Modules Strengths:**
- Scoped styles (no global namespace)
- No runtime overhead
- Traditional CSS syntax

**CSS Modules Limitations:**
- **No design token integration:** Must duplicate tokens in CSS variables
- **Context switching:** Edit JSX → switch to CSS file → edit styles → switch back
- **More files:** Each component needs `.module.css` file
- **No dynamic styling:** Can't style based on props (need inline styles)
- **Larger bundle:** All modules bundled (no tree-shaking like Tailwind)

**Verdict:** More files, more manual work, larger bundle.

---

## Alternatives Considered

### Alternative 1: Styled Components
- **Pros:** Dynamic styling, full CSS syntax, scoped styles
- **Cons:** 13KB runtime, SSR complexity, FOUC risk
- **Rejected because:** Runtime overhead unacceptable for performance budget

### Alternative 2: Emotion
- **Pros:** Similar to styled-components, smaller bundle
- **Cons:** 11KB runtime, SSR complexity, less ecosystem support
- **Rejected because:** Same issues as styled-components

### Alternative 3: CSS Modules
- **Pros:** Scoped styles, no runtime, traditional CSS
- **Cons:** More files, no design tokens, larger bundle, no dynamic styling
- **Rejected because:** More manual work, less maintainable

### Alternative 4: Plain CSS
- **Pros:** Zero dependencies, maximum flexibility
- **Cons:** Global namespace, no scoping, no design tokens, manual breakpoints
- **Rejected because:** Too primitive, high risk of CSS conflicts

### Alternative 5: Tailwind + Styled Components (Hybrid)
- **Pros:** Best of both worlds (Tailwind for utilities, styled-components for complex components)
- **Cons:** Two styling systems (confusing), 13KB runtime overhead, more complexity
- **Rejected because:** Complexity outweighs benefits, Tailwind alone is sufficient

---

## Consequences

### Positive

1. **Performance:**
   - 0KB runtime JavaScript (vs 13KB for styled-components)
   - 12KB production CSS bundle (purged)
   - Instant page loads (no style calculation on client)

2. **Design System Consistency:**
   - Design tokens → Tailwind config → utility classes
   - Impossible to use off-system values (enforces design system)
   - Autocomplete suggests only valid design tokens

3. **Developer Productivity:**
   - No context switching (styles in JSX)
   - Fast iteration (change class, see result)
   - IntelliSense autocomplete

4. **Maintainability:**
   - Delete component → styles automatically removed
   - No orphaned CSS files
   - No naming conflicts (utility classes)

5. **Responsive + Dark Mode:**
   - Breakpoints built-in (`sm:`, `lg:`, `xl:`)
   - Dark mode toggle (`dark:`)
   - No media query boilerplate

### Negative

1. **Long Class Names:**
   - Utility-first → many classes per element
   - Example: `className="bg-white/75 backdrop-blur-md border-2 border-white rounded-[24px] p-6 shadow-md"`
   - **Impact:** Verbose JSX, harder to read
   - **Mitigation:** Extract to components, use `@apply` for repeated patterns

2. **Learning Curve:**
   - Team must learn Tailwind class names
   - Estimated: 2-3 days to become proficient
   - **Mitigation:** Cheat sheet, IntelliSense, team training

3. **Custom Styles:**
   - Complex animations require arbitrary values or `@layer` directive
   - Example: Particle system animation needs custom `@keyframes`
   - **Mitigation:** Use Tailwind for 95%, custom CSS for complex animations

4. **Purge CSS Risk:**
   - Dynamic class names not purged correctly
   - Example: `className={isActive ? 'bg-blue-500' : 'bg-gray-500'}` ✅ works
   - Example: `className={active-${color}-500}` ❌ doesn't work (class not in source)
   - **Mitigation:** Use Tailwind's safelist, avoid string interpolation for classes

---

## Implementation Notes

### Installation

```bash
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
```

### Configuration

**tailwind.config.ts:**
```typescript
import type { Config } from 'tailwindcss'
import designTokens from './docs/design-system/design-tokens.json'

const config: Config = {
  content: [
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}'
  ],
  darkMode: 'class',  // Toggle with <html class="dark">
  theme: {
    extend: {
      colors: {
        glass: {
          bg: 'rgba(255, 255, 255, 0.75)',
          border: 'rgba(255, 255, 255, 1)',
          shadow: 'rgba(0, 0, 0, 0.08)'
        },
        accent: {
          blue: designTokens.colors.accent.blue.value,
          purple: designTokens.colors.accent.purple.value,
          green: designTokens.colors.accent.green.value,
          orange: designTokens.colors.accent.orange.value
        }
      },
      spacing: {
        xs: '0.25rem',  // 4px
        sm: '0.5rem',   // 8px
        md: '1rem',     // 16px
        lg: '1.5rem',   // 24px
        xl: '2rem',     // 32px
        '2xl': '3rem',  // 48px
        '3xl': '4rem'   // 64px
      },
      borderRadius: {
        glass: '24px'
      },
      backdropBlur: {
        glass: '32px'
      }
    }
  },
  plugins: []
}

export default config
```

**Global CSS:**
```css
/* src/styles/globals.css */
@tailwind base;
@tailwind components;
@tailwind utilities;

/* Custom glassmorphism component */
@layer components {
  .glass-card {
    @apply bg-glass-bg backdrop-blur-[32px] backdrop-saturate-[180%] backdrop-brightness-110 border-2 border-glass-border rounded-glass shadow-md;
  }

  .glass-button {
    @apply bg-glass-bg backdrop-blur-md rounded-lg px-4 py-2 border border-glass-border hover:bg-white/90 transition-all;
  }
}

/* Custom animations (can't be done with Tailwind alone) */
@layer utilities {
  @keyframes ambient-sway {
    0%, 100% { transform: translate(0, 0); }
    25% { transform: translate(-2px, -3px); }
    50% { transform: translate(2px, 1px); }
    75% { transform: translate(-1px, 3px); }
  }

  .animate-ambient-sway {
    animation: ambient-sway 6s ease-in-out infinite;
  }
}
```

### Component Examples

**Glass Card Component:**
```tsx
// src/components/ui/GlassCard.tsx
interface GlassCardProps {
  children: React.ReactNode
  className?: string
}

export function GlassCard({ children, className = '' }: GlassCardProps) {
  return (
    <div className={`glass-card ${className}`}>
      {children}
    </div>
  )
}

// Usage:
<GlassCard className="p-6 hover:shadow-lg">
  <h3 className="text-xl font-semibold mb-2">Metric Title</h3>
  <p className="text-4xl font-bold text-accent-blue">1,234</p>
</GlassCard>
```

**Responsive Layout:**
```tsx
<div className="
  grid
  grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4
  gap-4 lg:gap-6
  p-4 lg:p-8
">
  {/* Responsive metric cards */}
  <GlassCard>...</GlassCard>
  <GlassCard>...</GlassCard>
  <GlassCard>...</GlassCard>
  <GlassCard>...</GlassCard>
</div>
```

### Best Practices

1. **Extract Components:** Avoid repeating long class strings
   ```tsx
   // Bad
   <button className="bg-accent-blue text-white px-4 py-2 rounded-lg hover:bg-blue-600">Click</button>

   // Good
   <Button variant="primary">Click</Button>
   ```

2. **Use @apply Sparingly:** Only for repeated patterns, not single-use
   ```css
   /* Good: Repeated 10+ times */
   .glass-card { @apply bg-glass-bg backdrop-blur-md ... }

   /* Bad: Used once */
   .hero-title { @apply text-4xl font-bold ... }  /* Just use inline classes */
   ```

3. **Avoid String Interpolation:** PurgeCSS can't detect dynamic classes
   ```tsx
   // Bad (PurgeCSS removes these)
   <div className={`text-${color}-500`} />

   // Good (PurgeCSS keeps these)
   <div className={color === 'blue' ? 'text-blue-500' : 'text-gray-500'} />
   ```

4. **Use Arbitrary Values for One-Offs:**
   ```tsx
   <div className="backdrop-blur-[32px] shadow-[0_8px_32px_rgba(0,0,0,0.08)]">
   ```

---

## References

- [Tailwind CSS Documentation](https://tailwindcss.com/docs)
- [Next.js + Tailwind CSS Guide](https://tailwindcss.com/docs/guides/nextjs)
- [Tailwind UI Components](https://tailwindui.com/) (paid, but good reference)
- [Headless UI](https://headlessui.com/) (unstyled components for Tailwind)

---

## Related Decisions

- **ADR 001:** Next.js framework (provides CSS integration)
- **Story 0:** Design system (provides design tokens)
- **Story 2:** Next.js setup (install and configure Tailwind)

---

**Decision Made By:** Ravi (Product Owner)
**Reviewed By:** Architecture Team
**Supersedes:** None
**Superseded By:** None
