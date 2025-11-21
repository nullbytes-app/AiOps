# AI Agents Platform - Design System Overview

**Version:** 1.0.0
**Last Updated:** 2025-01-17
**Status:** Extracted from existing design iterations
**Design Style:** Liquid Glass / Glassmorphism with Neural Network Theme

---

## Overview

This design system defines the visual language for the AI Agents Platform Next.js UI migration. It emphasizes modern glassmorphism aesthetics with subtle animations, creating a premium, professional feel suitable for enterprise operations teams.

**Design Philosophy:**
- **Glass Morphism:** Translucent surfaces with backdrop blur for depth
- **Subtle Animation:** Gentle, purposeful motion that enhances UX without distraction
- **Neural Network Theme:** Abstract particle systems and node networks conveying AI/ML sophistication
- **Light Theme First:** Primary design in light mode with carefully chosen gradients

---

## Design Tokens

Complete design tokens are available in `design-tokens.json` following the W3C Design Tokens standard.

### Color Palette

**Background Gradients:**
- Gradient 1: Soft pink (#fff5f7) → Light blue (#f0f9ff) → Pale yellow (#fefce8)
- Gradient 2: Sky blue (#e0f2fe) → Light blue (#f0f9ff) → Amber (#fef3c7)

**Accent Colors:**
- **Blue (#3b82f6):** Primary actions, links, information states
- **Purple (#8b5cf6):** Secondary highlights, hover states, glow effects
- **Green (#10b981):** Success states, positive metrics
- **Orange (#f59e0b):** Warning states, attention indicators
- **Cyan (#00d4ff):** Data flow particles, dynamic elements

**Text Colors:**
- Primary: #1f2937 (dark gray)
- Secondary: #6b7280 (medium gray)

---

## Typography

**Font Family:** Inter (Google Fonts)
**Weights Available:** 300 (Light), 400 (Regular), 500 (Medium), 600 (Semibold), 700 (Bold)

**Type Scale:**
| Element | Size | Weight | Usage |
|---------|------|--------|-------|
| H1 | 2.5rem (40px) | 700 | Dashboard page titles |
| H2 | 2rem (32px) | 600 | Section headers |
| H3 | 1.5rem (24px) | 600 | Card titles, widget headers |
| Body | 1rem (16px) | 400 | Body text, descriptions |
| Caption | 0.875rem (14px) | 400 | Labels, secondary info |
| Small | 0.75rem (12px) | 400 | Metadata, timestamps |

---

## Spacing System

Based on 4px base unit (0.25rem):

| Token | Value | Pixels | Usage |
|-------|-------|--------|-------|
| xs | 0.25rem | 4px | Tight spacing, badges |
| sm | 0.5rem | 8px | Icon margins, compact layouts |
| md | 1rem | 16px | Standard spacing, padding |
| lg | 1.5rem | 24px | Card padding, section spacing |
| xl | 2rem | 32px | Large padding, page margins |
| 2xl | 3rem | 48px | Section gaps |
| 3xl | 4rem | 64px | Major layout divisions |

---

## Components

### Glass Card

**Visual Properties:**
- Background: `rgba(255, 255, 255, 0.75)` with backdrop blur (32px)
- Border: 2px solid white
- Border Radius: 24px
- Shadow: Layered (outer + inset highlight)
- Backdrop Filter: `blur(32px) saturate(180%) brightness(1.1)`

**Animation:**
- Entrance: Elastic bounce-in (800ms)
- Idle: Gentle ambient sway (6s infinite)
- Hover: 3D perspective lift with increased shadow

**Variants:**
- Default: Standard glass appearance
- Glow Accent: Adds breathing purple glow effect

**Usage:**
- Metric cards
- Data tables
- Form containers
- Modal dialogs

### Button

**Variants:**
| Variant | Background | Text Color | Border | Usage |
|---------|------------|------------|--------|-------|
| Primary | Blue (#3b82f6) | White | None | Primary actions |
| Secondary | Glass (0.5 opacity) | Primary text | 1px solid | Secondary actions |
| Ghost | Transparent | Primary text | None | Tertiary actions |
| Danger | Orange (#f59e0b) | White | None | Destructive actions |
| Disabled | Gray (0.3 opacity) | Gray text | None | Disabled state |

**States:**
- Default: Base styling
- Hover: Slight scale (1.02x) + subtle shadow
- Active: Scale down (0.98x) + ripple effect
- Focus: 2px purple outline
- Loading: Spinner + disabled appearance

### Input Fields

**Properties:**
- Height: 40px (md), 48px (lg)
- Border: 1px solid glass border, 2px on focus
- Border Radius: 12px
- Padding: 0.75rem 1rem
- Font: Body size, regular weight

**States:**
- Default: Light glass background
- Focus: Purple border + subtle glow
- Error: Orange border + error message below
- Disabled: Reduced opacity + cursor not-allowed

---

## Animation System

### Duration Scale
- **Instant (100ms):** Immediate feedback (button press)
- **Fast (150ms):** Quick transitions (hover effects)
- **Base (300ms):** Standard transitions (color, opacity)
- **Moderate (450ms):** Glass card interactions
- **Slow (800ms):** Entrance animations
- **Very Slow (6s+):** Ambient, decorative animations

### Easing Functions
- **Standard:** `cubic-bezier(0.4, 0.0, 0.2, 1)` - Most transitions
- **Elastic:** `cubic-bezier(0.68, -0.6, 0.32, 1.6)` - Bounce entrances
- **Ease In-Out:** Default easing for smooth motion

### Key Animations

**elasticBounceIn:**
- Duration: 800ms
- Effect: Scale + rotate + translateY entrance
- Usage: Card entrance, modal appearance

**ambientSway:**
- Duration: 6s (infinite)
- Effect: Subtle X/Y translation
- Usage: Idle card animation

**glowBreathe:**
- Duration: 3s (infinite)
- Effect: Pulsing shadow glow
- Usage: Accent/focus states

**particleDrift:**
- Duration: Variable (6-20s)
- Effect: Neural network particle movement
- Usage: Background decorative layer

---

## Effects

### Glassmorphism
- Backdrop Blur: 32px
- Saturation: 180%
- Brightness: 1.1
- Background: Semi-transparent white (0.75 alpha)
- Border: Solid white (1.0 alpha)

### Shadows
| Level | Usage | CSS Value |
|-------|-------|-----------|
| Small | Buttons, inputs | `0 1px 3px rgba(0,0,0,0.1)` |
| Medium | Cards (default) | `0 8px 32px rgba(0,0,0,0.08)` |
| Large | Cards (hover) | `0 16px 48px rgba(0,0,0,0.12)` |
| Inset | Glass highlight | `inset 0 1px 0 rgba(255,255,255,1)` |
| Glow | Focus/accent | `0 0 40px rgba(139,92,246,0.4)` |

---

## Responsive Breakpoints

| Breakpoint | Min Width | Target Devices | Layout |
|------------|-----------|----------------|--------|
| Mobile | 0px | Phones | Single column, bottom nav |
| Tablet | 768px | Tablets | 2-column grid, collapsible sidebar |
| Desktop | 1024px | Laptops, desktops | Sidebar + content area |
| Wide | 1440px | Large monitors | Max-width container (1400px) |

---

## Accessibility

### Color Contrast
- All text colors meet WCAG 2.1 AA standards against light backgrounds
- Primary text (#1f2937) on light bg: 16.8:1 contrast ratio
- Accent colors verified for sufficient contrast when used for text

### Motion
- All animations respect `prefers-reduced-motion` media query
- Decorative animations (particles, ambient sway) disabled when motion is reduced
- Essential animations (entrance, feedback) simplified to fade-only

### Keyboard Navigation
- All interactive elements (buttons, inputs, links) are focusable
- Focus states use 2px purple outline with 2px offset
- Tab order follows logical reading flow

---

## Dark Mode (Future Enhancement)

**Status:** Not yet implemented
**Planned Approach:**
- Invert background gradients (dark base with subtle color accents)
- Increase glass opacity to 0.85 for better contrast
- Adjust text colors: Primary → #f9fafb, Secondary → #d1d5db
- Maintain accent colors with slight brightness adjustments

---

## Component Library Status

### ✅ Designed & Implemented (in HTML mockups)
1. Glass Card (with variants)
2. Metric Cards (4 accent colors)
3. Dashboard Header
4. Button (primary style visible)

### 📝 Designed (needs extraction)
5. Navigation sidebar
6. Top header bar
7. Grid layouts (metric cards)

### ⏳ To Be Designed (Story 0 requirement: 20+ components)
8. Input (text, textarea, select)
9. Checkbox, Radio, Switch
10. Modal/Dialog
11. Toast notification
12. Dropdown menu
13. Table
14. Pagination
15. Badge
16. Avatar
17. Progress bar
18. Skeleton loader
19. Breadcrumbs
20. Tabs
21. Tooltip
22. Alert/Banner

---

## Empty State Patterns

### Welcome State
**Usage:** First-time user experience
**Pattern:**
```
[Icon: Centered, large, accent color]
Get started by creating your first [entity]
[Primary CTA Button]
```

### Zero State
**Usage:** No items in a list or table
**Pattern:**
```
[Icon: Medium size, secondary color]
No [items] yet. [Action] will appear here after [trigger].
[Secondary CTA Button or Link]
```

### Error State
**Usage:** Failed to load content
**Pattern:**
```
[Icon: Alert symbol, orange]
Failed to load [content type]
[Error details in caption text]
[Retry Button]
```

---

## Design Files & Assets

### Existing Design Iterations
- **Location:** `.superdesign/design_iterations/`
- **Files:**
  - `ai_ops_dashboard_1.html` - Initial concept
  - `ai_ops_dashboard_1_2.html` - Refinement #1
  - `ai_ops_dashboard_1_3.html` - Neural network theme
  - `ai_ops_dashboard_1_4.html` - Latest (Liquid Glass Premium)

### Design Tokens
- **Location:** `docs/design-system/design-tokens.json`
- **Format:** W3C Design Tokens (JSON)
- **Usage:** Import into Figma, Tailwind config, or CSS-in-JS

### Figma Project
- **Status:** 🔴 Not yet created (Story 0 requirement)
- **Required:** Complete Figma project with all 20+ components
- **Import:** Use existing HTML mockups as reference

---

## Next Steps (Story 0 Completion)

### Design System Tasks Remaining:
1. ✅ ~~Extract design tokens from HTML~~ (DONE)
2. ✅ ~~Document existing components~~ (DONE)
3. ⏳ Create Figma project with all screens
4. ⏳ Design remaining 15 components
5. ⏳ Export Figma design tokens (verify consistency with JSON)
6. ⏳ Create component usage guidelines

### Non-Design Tasks:
7. ⏳ Conduct 5-8 user interviews
8. ⏳ Create 5 user personas
9. ⏳ Document user research findings
10. ⏳ Write 6 ADRs (technical decisions)

---

## References

- **Glassmorphism Guide:** https://hype4.academy/tools/glassmorphism-generator
- **Design Tokens Standard:** https://tr.designtokens.org/format/
- **Inter Font:** https://fonts.google.com/specimen/Inter
- **WCAG 2.1 Guidelines:** https://www.w3.org/WAI/WCAG21/quickref/

---

**Document Maintained By:** Sally (UX Designer) & Bob (Scrum Master)
**For Questions:** Refer to Story 0 in `docs/sprint-artifacts/`
