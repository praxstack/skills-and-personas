# Frontend Design Rules — Canonical Shared Reference

**When to load this file:** MANDATORY whenever a frontend skill (frontend-pe, frontend-design-excellence, frontend-excellence-standards, frontend-uiux-designer, ultrathink-frontend) is active and aesthetic or library discipline decisions are being made. This is the single source of truth for rules that apply across all frontend skills — load this once rather than re-learning the same rules inside multiple skill bodies.

## Banned Defaults (reject generic AI aesthetics)

These are the signature of AI-generated UI and should never ship unless an explicit brief mandates them:

- **Primary typeface: Inter, Roboto, Arial, system-ui, or any platform-default font.** These signal "AI default output." Pair a distinctive display face with a readable body face instead (e.g., Instrument Serif + Geist, Fraunces + Inter-substitute, PP Neue Montreal, Söhne, IBM Plex Serif + Mono).
- **Purple gradient on white background.** The single most common tell of generated UI. If a gradient is warranted, pick an unexpected color relationship (e.g., muted earth tones, electric accent on deep neutral, duotone with measured saturation).
- **Evenly-distributed color palettes.** Balanced triads and symmetric palettes read as templated. Use dominant + accent (60-70% + 20-30%) with surface/text neutrals.
- **Solid flat backgrounds when the aesthetic allows depth.** Gradient meshes, grain overlays, noise, subtle geometric patterns, layered transparencies, or dramatic shadows create atmosphere. Flat is a last resort, not a default.
- **Template-like symmetry.** Centered everything, three equal columns, even gutters everywhere. Break the grid with intent — asymmetry, overlap, diagonal flow, controlled density.
- **Tailwind-default spacing / Shadcn-default theme without modification.** These are starting points, not finished designs. Override spacing scale, type scale, and at least one primitive.
- **Micro-interactions scattered across every element.** Ten small animations = zero signal. Pick one hero motion moment (orchestrated page-load, scroll sequence, or surprising hover) and let the rest stay quiet.
- **Repeating the same aesthetic across unrelated generations.** Convergence on Space Grotesk, Geist + purple, or the current "tasteful Tailwind" look. Variation across projects is a hard requirement.

## UI Library Discipline (non-negotiable)

When a UI library is present in the project, style its primitives — **do not rebuild modals, dropdowns, forms, comboboxes, or tabs from scratch.**

- **Shadcn/ui / Radix UI / Headless UI / React Aria:** use their primitives, theme them through the provided tokens or CSS variables.
- **MUI / Chakra / Ant Design:** theme via their provided theming APIs; extend with sx/styled patterns, not parallel components.
- **If the project has no UI library and is greenfield:** pick one deliberately and justify the choice (brand fit, accessibility baseline, design-system alignment) — do not roll your own accessible dialog.

Exceptions: when the library primitive genuinely doesn't fit (rare) or when the brand demands a bespoke primitive (specific animation, unusual interaction). Document the exception and its reason.

## Typography Discipline

- **Display face carries character**, body face carries readability. Pair them with intent.
- **Type scale uses a modular ratio** (1.25x / 1.333x / 1.5x / golden). Random sizes collapse hierarchy.
- **Body text: 16-18px baseline**, 1.5-1.7 line-height, left-aligned with natural ragged right.
- **Letter-spacing: tight on display (-0.02em to -0.04em)**, normal on body, slightly loose on small caps.
- **Test at the smallest real-world size** (12-14px app menu) before approving — many display faces break at small sizes.

## Color Discipline

- **Dominant + accent.** One color owns 60-70% of the surface; one accent cuts through.
- **Neutral scale with 5-9 perceptually-even steps** (use OKLCH for perceptual evenness, convert to hex for output).
- **Contrast: WCAG AA (4.5:1 body, 3:1 large/UI) minimum.** AAA (7:1 / 4.5:1) when the brand budget allows.
- **Semantic colors (success/warning/danger/info)** tested against both extremes of the neutral scale.

## Motion Discipline

- **One hero moment per page/view.** An orchestrated page-load, a staggered list reveal, a surprising scroll reaction.
- **Use `transform` and `opacity`** for 60fps animations. Avoid animating layout properties (width/height/margin/top/left).
- **Spring physics over ease-in-out** when a library is available (Framer Motion's spring, GSAP physics). Match the aesthetic: springy for playful, critically-damped for refined.
- **Respect `prefers-reduced-motion`.** Reduce or disable non-essential animations when the user opts out.

## Layout Discipline

- **Whitespace and asymmetry are tools, not leftovers.** Break the grid deliberately. Overlap elements. Use diagonal flow.
- **Controlled density is valid.** Editorial design can be dense; minimalist design needs restraint. Pick a density and commit.
- **Semantic HTML first.** `<main>`, `<nav>`, `<article>`, `<section>`, `<header>`, `<footer>` — give the structure meaning before styling it.

## Accessibility Native (not bolted on)

- Keyboard navigation for every interactive element.
- Visible focus states (not just browser default — style them to match the aesthetic).
- `prefers-reduced-motion` fallbacks for every non-essential animation.
- ARIA roles where semantic HTML is insufficient (not as a substitute for semantic HTML).
- Form labels, error states, and required fields announced to assistive tech.
- Heading hierarchy (h1 → h2 → h3) without skipping levels.

## Performance Discipline

- **Core Web Vitals as concrete targets**, not as vibes: LCP < 2.5s, INP < 200ms, CLS < 0.1.
- **Lazy-load below-the-fold** images, embeds, carousels.
- **Code-split routes** by default in React Router / Next.js App Router / TanStack Router.
- **Preload / prefetch** the hero image, critical fonts, above-the-fold data.
- **Measure, don't guess.** Claims like "fast" require numbers. Lighthouse, WebPageTest, real-user monitoring.

## Aesthetic Commitment Statement Template

Every frontend delivery should open with a 1-2 sentence aesthetic commitment statement:

> **Aesthetic direction:** [Brutalist editorial / Luxury refined / Maximalist chaos / Retro-futuristic / ...]
>
> **Differentiator:** [The one thing a visitor will remember.]

Then the typography pair, the palette with CSS variables, and the hero motion moment follow from that commitment.

## Why this reference exists

Prior reviews (skill-judge + skill-auditor, 2026-05-12) found that `frontend-pe`, `frontend-design-excellence`, `frontend-excellence-standards`, `frontend-uiux-designer`, and `ultrathink-frontend` were repeating these rules across their bodies. Consolidating the shared rules here removes the duplication without collapsing the distinct skills. Each skill's body can now focus on its unique axis (workflow / constellation role / taste / standards / depth) and delegate the shared discipline to this reference.
