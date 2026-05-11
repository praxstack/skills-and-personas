---
name: frontend-excellence-standards
description: 'Principal-engineer standards for frontend UI, aesthetics, accessibility, and performance. Use when building or reviewing components, pages, design systems, motion work, or any customer-facing interface. Triggers on "build a UI", "design a page", "accessibility audit", "improve frontend performance", "choose typography", "design tokens", "component library discipline", "motion design", "WCAG". Covers design commitment, typography discipline, color palette strategy, motion, layout asymmetry, atmospheric backgrounds, UI library discipline, accessibility (semantic HTML, ARIA, keyboard, contrast), frontend performance, and coding standards. Loaded by super-mode-core for frontend-heavy work.'
---

# Frontend Excellence Standards

**Audience:** Frontend engineers and designers shipping production interfaces — from marketing pages to complex product surfaces — where visual intentionality, accessibility, and performance all matter.

**Goal:** Deliver frontend work that looks intentionally designed, is accessible by default, performs under real load, and respects the existing UI library. Every aesthetic choice traces to a commitment; every technical choice traces to a measured or documented constraint.

## Core Principles

- Define purpose, audience, and constraints before coding.
- Choose a bold, coherent aesthetic direction and commit to it.
- Use distinctive typography; avoid generic system fonts unless the brief requires them.
- Keep color palettes tight and intentional; use CSS variables.
- Use purposeful motion; prefer `transform` and `opacity` for 60fps performance.
- Break grids with intent; use whitespace to guide hierarchy.
- Add texture or depth when appropriate (gradients, noise, overlays).
- Accessibility is native, not bolted on.
- Treat performance metrics as goals only when measured.

## Decision Framework

### Design Focus Areas

Before writing code, commit to decisions in each area:

- **Typography.** Pair a distinctive display font with a readable body font. Justify both against the aesthetic commitment.
- **Color.** Pick a dominant base and a sharp accent. Evenly-distributed palettes look defaulted.
- **Motion.** Use one high-impact sequence (hero load, orchestrated reveal, surprising hover) over many micro-effects.
- **Layout.** Vary density. Avoid template-like symmetry. Break the grid with intent.
- **Backgrounds.** Avoid flat fills when the context allows. Gradient meshes, noise, geometric patterns, and layered transparencies create atmosphere.

### UI Library Discipline

If a UI library exists in the project, use its primitives for modals, dropdowns, buttons, forms, popovers, tooltips, and every other primitive it provides.

- Wrap or style library components to match the aesthetic — do not rebuild them.
- Rationale: stability, accessibility, and avoiding CSS pollution.
- Check for: Shadcn UI, Radix, MUI, Headless UI, Chakra, Mantine, Ant, and internal design systems.

### Coding Standards

- Prefer modern frameworks and idiomatic patterns.
- Use design tokens and a consistent spacing scale.
- Keep components small and composable.
- Reduce state; derive values whenever possible.
- Proper TypeScript types when applicable.
- Component composition over props drilling.

### Accessibility

- Semantic HTML and correct ARIA roles.
- Keyboard navigation works everywhere pointer navigation works.
- Visible focus states — not just `outline: none` replaced with nothing.
- Contrast ratios: 4.5:1 minimum for text, 3:1 for UI elements. WCAG AAA (7:1) for critical text surfaces.
- Respect `prefers-reduced-motion`.
- Screen reader announcements via ARIA live regions where state changes matter.
- Focus management on modals and route transitions — trap focus, restore on close.

### Performance

- Split bundles; lazy-load below the fold.
- Avoid unnecessary re-renders (proper memoization, stable references, derived state).
- Prefer `transform` and `opacity` for animated properties.
- Treat Core Web Vitals as targets only after measurement.
- State bundle impact explicitly when adding dependencies.

## Anti-Patterns

- **NEVER** use Arial, Roboto, Inter, or system-ui as the primary face unless the brief mandates it — these signal "AI default".
- **NEVER** ship purple gradients on white backgrounds — the defining cliche.
- **NEVER** build a custom modal, dropdown, or form primitive when the project's UI library provides one.
- **NEVER** use generic layout templates without a purposeful reason.
- **NEVER** bolt on accessibility after the fact.
- **NEVER** remove a focus outline without replacing it with a visible alternative.
- **NEVER** scatter micro-interactions across every element — pick one hero moment.
- **NEVER** claim performance wins without measurement.
- **NEVER** use `localStorage` or `sessionStorage` in claude.ai-rendered artifacts (unsupported).
- **NEVER** converge on the same visual choices (Space Grotesk, tasteful-Tailwind defaults) across generations.

## Standard Workflow

1. **Interrogate the brief.** Purpose, audience, tone, constraints, differentiator.

2. **Commit to an aesthetic direction** in one sentence before writing code. Brutalist, editorial, refined-minimal, maximalist — pick and execute.

3. **Decide typography pair.** Display + body. Specific families with rationale.

4. **Define the palette as CSS variables.** Dominant, accent, surface, text, one atmospheric layer.

5. **Design the hero motion moment.** One orchestrated sequence, not scattered animation.

6. **Detect and use the existing UI library.** Style or wrap its primitives.

7. **Build semantic HTML first, then style.** ARIA roles where semantics are insufficient. Keyboard flow and focus management designed in.

8. **Apply design tokens and a spacing scale.** Keep components small and composable.

9. **Measure performance.** Bundle size, LCP, CLS, interaction responsiveness. State what was measured and what was not.

10. **Validate accessibility.** Keyboard traversal, screen reader announcements, contrast ratios, reduced-motion fallback.

## Deliverables Contract

Frontend delivery includes:

- **Aesthetic commitment statement** — one or two sentences naming the direction and differentiator.
- **Typography decisions** — specific families and rationale.
- **Color palette** — CSS variables for dominant, accent, surface, text.
- **Hero motion description** — the orchestrated moment, how it is implemented, reduced-motion fallback.
- **UI library usage** — which library's primitives were used and where any were wrapped.
- **Component structure** — small, composable, with clear props contracts.
- **Accessibility notes** — contrast ratios, keyboard flow, ARIA usage, focus management.
- **Performance notes** — what is lazy, what is code-split, measured numbers if any, and what was not measured.
- **Production-grade code** — no TODOs, no placeholders.

## Quality Checklist

Before delivery, verify:

- Existing UI library primitives used where available.
- Every element justified — no ornamental noise without atmospheric purpose.
- Keyboard navigation traverses all interactive elements.
- Visible focus states on all focusable elements.
- Contrast ratios meet 4.5:1 text / 3:1 UI minimum (AAA 7:1 for critical surfaces).
- One hero motion moment, not scattered micro-animations.
- `prefers-reduced-motion` respected.
- Code is complete — no TODOs, no placeholders.
- Bundle impact of new dependencies stated.
- Aesthetic varies from prior generations — no convergence on Inter/Space Grotesk/purple-on-white.
