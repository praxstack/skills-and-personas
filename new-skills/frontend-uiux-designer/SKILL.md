---
name: frontend-uiux-designer
description: 'Frontend engineering plus UI/UX design for production interfaces. Use when building, designing, or reviewing web UIs, components, design systems, accessibility, responsive layouts, or visual hierarchy. Covers aesthetic direction, typography, color, motion, interaction states, WCAG compliance, and framework selection (React/Vue/Svelte, Tailwind/CSS-in-JS, Framer Motion/GSAP). Keywords: UI, UX, frontend, design, component, accessibility, a11y, WCAG, responsive, typography, color palette, motion, animation, design system, design tokens, Figma handoff, Core Web Vitals, visual design, interaction design.'
---

# Frontend + UI/UX Designer

**Audience:** Engineers and designers building production web interfaces.

**Goal:** Ship distinctive, accessible, performant interfaces — not generic AI-aesthetic defaults — with a coherent aesthetic point-of-view and measurable quality.

## Core Responsibilities

- **Commit to an aesthetic direction before coding.** Pick one extreme (brutally minimal, maximalist, editorial, industrial, retro-futuristic, etc.) and execute with precision. Intentionality beats intensity. Do not converge on safe defaults (Inter + purple gradient + rounded cards).
- **Own the full pipeline:** information architecture, visual hierarchy, component states (default/hover/active/focus/disabled/loading/error/success), motion, responsive behavior, accessibility, and implementation.
- **Enforce accessibility as a constraint, not a checkbox.** WCAG AA minimum, semantic HTML first, ARIA only when HTML cannot express intent. Keyboard navigation and screen reader announcements are not optional.
- **Translate research into decisions.** User interviews, usability tests (5 users catch ~85% of issues), analytics, A/B tests — all feed the design, not the other way around.
- **Deliver implementation-ready specs.** All states, all breakpoints, all edge cases (empty, error, loading, overflow, offline). Handoff is complete when a different engineer could build it without asking clarifying questions.

## Decision Framework

**Aesthetic direction (pick ONE conceptual axis, then execute):**
- Minimal/refined — restraint, precision, careful spacing, subtle details
- Maximalist — elaborate code, layered effects, dense typography, bold motion
- Editorial — asymmetric grids, strong typographic contrast, generous negative space
- Brutalist — raw HTML feel, system fonts used deliberately, monochrome + one accent

Match implementation complexity to vision. Minimalist needs more restraint, not less craft.

**Typography pairing:**
- **Contrast (serif + sans)** when you want classic, balanced, editorial feel
- **Concordant (same family, varying weights)** when the layout carries the personality
- **Conflict (two display faces)** only with strong visual hierarchy skill — otherwise it looks broken
- Body 16-18px minimum; line-length 50-75ch; line-height 1.5-1.75 body, 1.2-1.4 headings

**Color commitment:**
- Dominant color (60%) + supporting (30%) + accent (10%) — evenly-distributed palettes look timid
- Define CSS variables or design tokens; never hardcode hex in components
- Validate contrast at 4.5:1 normal text (AA), 7:1 for AAA/critical reading paths

**Motion budget:**
- Animate only `transform` and `opacity` (GPU) — avoid width/height/top/left (reflow)
- Durations: 100-200ms micro-interactions, 200-400ms state changes, 400-600ms page-level reveals
- One orchestrated moment (staggered page-load reveal) delights more than scattered micro-interactions
- `prefers-reduced-motion` collapses to 0.01ms — not optional

**Framework/stack selection:**
- **React + Next.js + Tailwind + shadcn/ui:** default production stack for most product UIs
- **Vue + Nuxt:** when team prefers it or SFC ergonomics matter
- **Svelte/SvelteKit:** when bundle size and compile-time optimization matter more than ecosystem
- **Headless (Radix, Headless UI) + custom styling:** when design is distinctive enough to not want opinionated components
- **MUI/Chakra/Ant:** only when speed-to-market matters more than distinctive look

**State management (pick by data lifecycle):**
- Local (`useState`) for component-internal
- Context/Provide for cross-tree config (theme, auth, i18n) — NOT for server data
- Server state — TanStack Query or SWR, never Redux
- Global UI state (Zustand or Jotai) only when actually shared; resist premature

## Quality Gates / Checkpoints

**Before implementation:**
- Aesthetic direction committed (can be stated in one sentence)
- All component states designed (including focus-visible, disabled, loading, error)
- Responsive behavior specified per breakpoint (not just "it reflows")
- Accessibility approach documented (keyboard flow, ARIA, screen reader copy)

**Before code review:**
- Contrast checked on every text/bg pair
- Keyboard-navigable end-to-end with visible focus indicators
- Tested with screen reader (VoiceOver on macOS, NVDA on Windows)
- `prefers-reduced-motion` respected
- Cross-browser tested (Chrome, Firefox, Safari, iOS Safari, Chrome Mobile)
- Core Web Vitals: LCP <2.5s, INP <200ms, CLS <0.1
- Images have explicit width/height or aspect-ratio (no CLS)
- Bundle size reviewed; no accidental library imports

**Architecture sign-off:** For significant UI, get engineering review of framework choice, state model, and performance budget BEFORE building. Catching architecture issues in code review is too late.

## Anti-Patterns

- **NEVER remove focus outlines without replacing them.** `outline: none` with no alternative breaks keyboard users silently. Always provide a visible focus-visible style.
- **NEVER animate `width`, `height`, `top`, `left`.** Triggers layout. Use `transform: translate()` and `scale()`.
- **NEVER use `<div onClick>` for interactive elements.** Use `<button>` or `<a>` — gets keyboard, focus, and screen reader support for free.
- **NEVER rely on color alone to convey information.** Colorblind users and grayscale contexts will miss it. Add icons, text, or patterns.
- **NEVER use hover-only interactions on touch.** No hover on mobile; design for touch + mouse equivalence.
- **NEVER ship generic AI-aesthetic defaults:** Inter + Space Grotesk, purple gradients on white, predictable bento grids. Make unexpected choices.
- **NEVER mix icon styles** (line + filled + duotone) within one interface. Consistent stroke weight or don't ship.
- **NEVER use `tabindex > 0`.** Disrupts natural tab order. Use `tabindex="0"` or `"-1"` only.
- **NEVER bypass semantic HTML for ARIA.** `role="button"` on a div is a fallback for when you cannot use a `<button>` — which is almost never.
- **NEVER lift state prematurely.** Props drilling through 2 levels is fine. Global state for a modal's open/close is over-engineering.
- **NEVER skip empty/error/loading states.** A design that only shows the happy path is half-done.

## Standard Workflow

1. **Discovery:** Understand users (goals, context, mental models), competitors, success metrics. 15 minutes of research prevents 15 hours of rework.
2. **Concept:** Commit to aesthetic direction. Sketch low-fi structure. Define IA and user flows including edge cases.
3. **Design:** High-fidelity with ALL states. Responsive at key breakpoints. Motion specified (duration + easing + what animates).
4. **Engineering review (CHECKPOINT):** Feasibility, performance, a11y approach, framework fit. Get sign-off before building.
5. **Implement:** Build components with full states. Test keyboard and screen reader as you go, not at the end. Measure performance continuously.
6. **Handoff spec:** Design rationale, component API, interactions, breakpoints, a11y notes, edge cases, content guidelines.
7. **QA:** Cross-browser, cross-device, assistive tech, performance budget, visual regression.
8. **Iterate:** Measure against defined metrics (task success, time on task, satisfaction, Core Web Vitals). Revise based on data.

## Deliverables Contract

**Design proposal must include:**
- One-sentence aesthetic direction
- Target users and success metrics (measurable)
- All component states with visuals
- Responsive behavior per breakpoint (not "it's responsive")
- Motion spec (duration, easing, trigger) for each animation
- Accessibility plan (keyboard flow, ARIA, screen reader copy)
- Edge cases: empty, error, loading, overflow, offline

**Implementation PR must include:**
- All states implemented and tested
- Keyboard navigation working end-to-end
- Contrast verified (automated + manual)
- Screen reader tested (record which one)
- Core Web Vitals measured, not assumed
- Cross-browser tested with explicit list
- Deviations from design documented with reason

## References

- `references/design-systems.md` — design tokens, atomic design, component API patterns. CONDITIONAL (loading when building/extending a design system).
- `references/accessibility-wcag.md` — WCAG 2.1 POUR checklist, ARIA patterns, screen reader copy, focus management. MANDATORY for any interactive UI.
- `references/frontend-stacks.md` — framework selection matrix, state management decision tree, styling approach tradeoffs. CONDITIONAL (loading when picking stack).
- `references/interaction-design.md` — state matrix, Fitts/Hick/Miller laws applied, motion principles, easing curves. CONDITIONAL (loading when designing interactions).
- `references/user-research.md` — interview protocols, usability testing, persona templates, JTBD framing. CONDITIONAL (loading when conducting research).
