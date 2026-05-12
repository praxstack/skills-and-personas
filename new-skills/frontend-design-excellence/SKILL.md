---
name: frontend-design-excellence
description: 'Create distinctive, production-grade frontend interfaces that reject generic AI aesthetics. Use when building a component, page, landing, marketing site, portfolio, or any UI where visual distinctiveness matters. Triggers on "design a UI", "build a landing page", "make this look better", "avoid AI slop", "distinctive design", "bespoke aesthetic", "visual identity". Covers aesthetic commitment, typography discipline, bold color palettes, purposeful motion, asymmetric layout, and atmospheric backgrounds. Not for: pure layout fixes, component library wrapper work, tasks that explicitly require template-matching, engineering workflow (use frontend-pe), cross-functional role work (use frontend-uiux-designer), or super-mode orchestration (use frontend-excellence-standards). This is aesthetic commitment discipline, not process.'
---

# Frontend Design Excellence

**Audience:** Engineers and designers building customer-facing UI where visual distinctiveness materially affects outcomes (marketing sites, product launches, portfolios, brand-forward SaaS surfaces).

**Goal:** Ship interfaces that look intentionally designed — not defaulted. Every design choice traces to an aesthetic commitment, not a framework preset.

## Shared discipline (load first)

**MANDATORY:** Before doing anything else, read `../frontend-pe/references/design-rules.md`. It is the canonical source for typography bans (Inter/Roboto/Arial), color discipline (dominant+accent, no purple-on-white), motion rules (one hero moment), UI-library discipline, accessibility baseline, and performance targets. This skill inherits those rules and focuses only on what's unique to aesthetic commitment.

## Unique to this skill — aesthetic commitment

The difference between a defaulted UI and a committed one is whether every choice traces back to a single stated direction. The shared rules tell you what NOT to do. This skill tells you how to pick and commit.

## Decision Framework

**Pick the aesthetic tone before writing code.** Choose one and commit:

- Brutally minimal — extreme whitespace, one typeface, monochrome with one accent
- Maximalist chaos — layered typography, overlapping elements, saturated color
- Retro-futuristic — CRT effects, chromatic aberration, 80s palettes
- Editorial/magazine — strong grids, large display type, generous leading
- Brutalist/raw — exposed structure, monospace, hard edges, limited color
- Art deco/geometric — symmetry, metallics, strict geometry
- Organic/natural — soft curves, muted earth tones, tactile textures
- Luxury/refined — serif display, tight tracking, deep neutrals, restrained motion
- Playful/toy-like — rounded everything, bouncy motion, primary colors
- Industrial/utilitarian — system fonts are OK here, grid-heavy, data-dense

**Vary across generations.** Do not converge on Space Grotesk, purple gradients, or the current "tasteful" Tailwind look. Each new design should pick a different flavor unless context demands continuity.

**Match complexity to the vision.** Maximalist designs need elaborate code with extensive animations. Minimalist designs need restraint, precision, and meticulous spacing. Elegance comes from executing the chosen vision well, not from doing less.

## Anti-Patterns (aesthetic commitment only — shared rules in design-rules.md)

- **NEVER** ship without first committing to a single aesthetic direction in one sentence. The uncommitted middle is where AI-generated UI lives.
- **NEVER** converge on the same choices across successive generations. Each new brief should pick a different flavor unless continuity is the explicit goal.
- **NEVER** add elements without either a functional role or an atmospheric purpose. Decorative-by-default collapses into noise.
- **NEVER** use template-like symmetry as a default — break the grid with intent when the commitment calls for it.
- **NEVER** let the aesthetic commitment and the technical execution disagree. Maximalist visions need elaborate code; minimalist visions need meticulous spacing.

For typography bans (Inter/Roboto/Arial), color rules (dominant+accent, no purple-on-white), motion discipline, UI library discipline, accessibility baseline, and performance targets — see `../frontend-pe/references/design-rules.md`.

## Standard Workflow

1. **Interrogate the brief.**
   - Purpose: what problem does this interface solve? Who uses it?
   - Tone: which aesthetic direction will the work commit to?
   - Constraints: framework, performance budget, accessibility level, browser targets.
   - Differentiation: what is the one thing a visitor will remember?

2. **Commit to the aesthetic direction in one sentence** before writing code. Example: "Brutalist editorial — oversized serif display, monospace body, two-tone black/safety-orange, hard grid with one overlap moment."

3. **Pick the typography pair.** Display face + body face. Justify both choices against the aesthetic commitment.

4. **Define the palette as CSS variables.** Dominant, accent, surface, text. Include one atmospheric layer (gradient, noise, or texture).

5. **Design the hero motion moment.** Where will the orchestrated reveal happen? Staggered load? Scroll sequence? Hover that surprises? Pick one.

6. **Implement with framework idioms.** Semantic HTML. ARIA where needed. Tailwind or design tokens with consistent spacing scale. Components small and composable.

7. **Respect the library.** If Shadcn/Radix/MUI/Headless UI is in the project, style its primitives — do not rebuild modals, dropdowns, or forms from scratch.

8. **Accessibility is native, not bolted on.** Keyboard navigation, visible focus states, 4.5:1 text contrast, 3:1 UI contrast, reduced-motion fallbacks.

9. **Performance discipline.** Lazy-load below-the-fold. Code-split routes. Treat performance metrics as goals only when they are actually measured.

## Deliverables Contract

Every delivery includes:

- **Aesthetic commitment statement** (1–2 sentences) — the chosen direction and the differentiator.
- **Typography choices** with the specific font families and the rationale for each.
- **Color palette** expressed as CSS variables with dominant/accent/surface/text roles.
- **Hero motion description** — the one orchestrated moment and how it is implemented.
- **Production-grade code** — no TODOs, no placeholders, no incomplete artifacts.
- **Accessibility notes** — contrast ratios hit, keyboard flow, ARIA roles used.
- **Performance notes** — what is lazy, what is split, what was not measured.

Remember: restraint and excess both demand precision. The failure mode is defaulted, not defaulted-up or defaulted-down.
