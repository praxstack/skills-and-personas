---
name: frontend-excellence-standards
description: 'Principal-engineer standards reference for frontend UI, aesthetics, accessibility, and performance. Use when super-mode-core loads this for frontend-heavy work, or when a skill needs the canonical frontend discipline without owning the rules. Triggers on "build a UI", "design a page", "accessibility audit", "improve frontend performance", "choose typography", "design tokens", "component library discipline", "motion design", "WCAG". Thin dispatch skill — the actual rules live in the canonical frontend-pe/references/design-rules.md; this skill wraps them with a quality-gate checklist for super-mode orchestration. Not for: standalone user invocation (use frontend-pe, frontend-uiux-designer, or ultrathink-frontend depending on scope). This is an internal domain reference loaded by super-mode-core.'
---

# Frontend Excellence Standards

**Audience:** `super-mode-core` loading this as the frontend domain reference; or any skill that needs the frontend quality-gate checklist without owning the shared rules.

**Goal:** Provide a single quality-gate checklist that enforces the canonical frontend rules when a super-mode orchestration touches frontend work. Do NOT duplicate the rules themselves — delegate to the canonical source.

## Shared discipline (load this first — it is the whole standard)

**MANDATORY:** Read `../frontend-pe/references/design-rules.md` in full. It is the canonical source for:
- Banned defaults (Inter/Roboto/Arial/system-ui, purple-on-white, evenly-distributed palettes, flat backgrounds by default, template symmetry, scattered micro-interactions, aesthetic convergence)
- UI library discipline (Shadcn/Radix/MUI/Headless UI — style primitives, do not rebuild)
- Typography discipline (display + body pairing, modular scale, letter-spacing rules)
- Color discipline (dominant + accent, OKLCH neutral scale, WCAG AA minimum)
- Motion discipline (one hero moment, `transform`/`opacity`, spring physics, reduced-motion respect)
- Layout discipline (asymmetry with intent, semantic HTML)
- Accessibility native (keyboard, focus states, ARIA, reduced-motion)
- Performance discipline (Core Web Vitals as concrete targets, measure don't guess)

This skill does not restate those rules. If you see frontend rules repeated here, the repetition is a bug to be fixed.

## Quality-Gate Checklist (super-mode use)

When super-mode-core invokes this reference, run the following checklist against the frontend deliverable before signing off. Each item maps to a rule in `design-rules.md` — if any item fails, the skill responsible for producing the frontend work (frontend-pe, frontend-uiux-designer, etc.) must fix it.

**Before any code ships:**

1. **Aesthetic commitment statement** present (1-2 sentences naming direction + differentiator).
2. **Typography pair** named with specific families and rationale (no system-font fallbacks unless brief-mandated).
3. **Color palette** expressed as CSS variables with dominant / accent / surface / text roles.
4. **Hero motion moment** described with implementation approach and reduced-motion fallback.
5. **UI library primitives used** where a library is present — no bespoke modals/dropdowns/forms built from scratch.
6. **Semantic HTML** used for structure (`<main>`, `<nav>`, `<article>`, `<section>`) before ARIA is added.
7. **Keyboard navigation** traverses every interactive element; visible focus states on all focusable elements.
8. **Contrast ratios** hit WCAG AA minimum (4.5:1 body, 3:1 UI) or AAA where feasible.
9. **`prefers-reduced-motion`** respected for every non-essential animation.
10. **Performance claims are measured**, not asserted. State what was measured and what was not.
11. **Bundle impact stated** for any new dependency.
12. **No forbidden `localStorage` / `sessionStorage`** in artifact-rendered contexts.
13. **Aesthetic differs** from the immediately-prior generation (no convergence on the current "tasteful Tailwind" look).

If any gate fails, the super-mode orchestrator sends the work back to the producing skill with the specific gate that failed.

## Why this skill exists

This skill is the super-mode-core loader target for frontend work. It does NOT author frontend code; it enforces the canonical rules on work produced by frontend-pe / frontend-uiux-designer / ultrathink-frontend / frontend-design-excellence. Keeping the rules in one place (`design-rules.md`) and the quality gate in another (this skill) means the rules can evolve without requiring edits to five skills simultaneously.
