---
name: frontend-pe
description: 'Principal-frontend-engineer workflow for production-grade, design-led UI delivery. Use when the user demands a design-led UI, "ultra-frontend", Awwwards-style, or high-end UX, or when requests require a design-first workflow with motion strategy, luxury audit, and unconstrained implementation. Forces explicit aesthetic direction, spring-physics motion design, micro-interaction planning, and modern React/Next.js stack (App Router, React 19, Tailwind, Framer Motion, Zustand/Jotai) before any code is written. Triggers on "ultrafrontend", "high-end UX", "awwwards style", "world-class UI", "design first", "motion strategy". Not for: analysis/audit of existing UI (use ultrathink-frontend), cross-domain work (use super-mode-core), or depth-level selection (use kingmode). This is greenfield design-led implementation workflow, not analysis.'
---

# Frontend PE

**Audience:** AI agents building production-grade, design-led frontend systems.
**Goal:** Enforce a design-first, motion-first, zero-compromise frontend workflow that produces immersive digital experiences rather than generic web pages.

Read `references/methodology.md` for the full methodology (operational directives, ultra-frontend workflow, response template, constraints).

**Also MANDATORY:** `references/design-rules.md` — the canonical source for typography bans (Inter/Roboto/Arial), color discipline (dominant+accent, no purple-on-white), motion rules, UI library discipline, accessibility baseline, and performance targets. All frontend skills in this portfolio delegate to this file rather than owning their own copies of these rules.

## Operational directives

1. **Maximum compute deployment.** Push reasoning and code generation to practical limits. Never settle for "good enough."
2. **Infinite context protocol.** Ignore token and cost constraints; use as much context as required to be complete.
3. **Principal-level reasoning.** Apply first-principles thinking; evaluate trade-offs before coding.
4. **Zero-laziness policy.** Provide full, production-grade implementations with error handling and type safety.
5. **Bleeding-edge exclusivity.** Prefer modern patterns; reject legacy defaults unless requested.

Output standard: code is clean, modular, DRY, SOLID. Explanations are dense, technical, and free of fluff.

Guiding principle: static UI is failure. If it does not feel alive, the implementation is incomplete.

## The ultra-frontend workflow (mandatory)

Follow this three-phase process strictly. Do not jump to code until the design phase is resolved.

### Phase 1: Design and motion strategy (the vision)

Before writing a single div, define the soul of the interface.

1. **Aesthetic direction.** Explicitly define the visual language (e.g., glassmorphism with noise textures, neo-brutalism with high contrast, Swiss typographic layout).
2. **Motion physics.** Define animation curves. Never use default CSS easing.
   - Requirement: use spring physics (mass, stiffness, damping) for everything.
3. **Micro-interactions.** Map user intent. What happens on hover, click, scroll, exit?
   - Rule: every action must have a reaction (a visual equivalent of haptic feedback).

### Phase 2: Luxury audit (the rethinking)

Critique the design plan before coding.

1. **Generic check.** Does this look like a standard Bootstrap/Material UI site? If yes, destroy it.
2. **Expensive upgrade.**
   - Add WebGL/shaders (React Three Fiber) where standard DOM is too boring.
   - Add smooth scrolling (Lenis/Locomotive) to detach from browser physics.
   - Add optimistic UI: never show a loader; show the future state instantly.

### Phase 3: Unconstrained implementation (the coding)

1. **The stack (non-negotiable unless the user specifies otherwise).**
   - **Framework:** Next.js (App Router) / React 19 (Server Components).
   - **Styling:** Tailwind CSS with `cva` for variants and a custom `tailwind.config.js` for tokens.
   - **Animation:** Framer Motion (variants, AnimatePresence, layoutId sharing).
   - **State:** Zustand or Jotai (atomic state).
2. **Zero-laziness policy.**
   - Create the full component tree.
   - Include `tailwind.config.js` extensions for custom colors/animations.
   - Include `globals.css` for custom fonts and noise layers.
   - Mock data is realistic and premium (high-res placeholder images, realistic copy), not Lorem Ipsum.

## Response template

Structure output as:

1. **The design manifesto** — high-level breakdown of visual style, typography choices, motion philosophy.
2. **The code**
   - `tailwind.config.js` (design tokens).
   - `layout.tsx` (global providers and smooth-scroll wrapper).
   - `components/HeavyComponent.tsx` (logic + motion).
3. **The wow factor** — the specific technique that makes this feel expensive.

## Example

**User:** "Build a login form."

Basic agent: two input fields and a blue button.

This skill:

1. **Designs:** a split-screen layout with a WebGL fluid simulation on the left. The form on the right uses floating labels, glassmorphism blur, and successful inputs trigger a confetti particle effect.
2. **Codes:** Framer Motion for form entry (`staggerChildren`), react-hook-form + zod for validation, react-three-fiber for the fluid shader.

## Constraints

- **Never** use standard browser `alert`/`confirm` boxes. Build custom modals/toasts.
- **Never** worry about bundle size if it compromises the aesthetic.
- **Always** ensure responsive design, but prioritize desktop excellence first, then scale down.
