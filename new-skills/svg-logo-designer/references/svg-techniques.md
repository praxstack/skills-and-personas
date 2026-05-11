# Advanced SVG Techniques

## When to load this file

Load when the logo needs capabilities beyond basic paths and fills: filters, blend modes, masks, gradients, path construction for complex shapes, animation, or optimization for production delivery.

## Path construction

- **Prefer absolute commands** (`M`, `L`, `C`) for anchor-point stability across tools.
- **Use cubic Béziers (`C`) for smooth curves**; quadratic (`Q`) for simple arcs; arcs (`A`) only when the ellipse geometry is intentional.
- **Round anchor coordinates to 0.1 precision** after layout is finalized — keeps file small and human-readable.
- **Close paths (`Z`)** even when the last point visually matches the first; prevents 1-pixel seams on stroke alignment.
- **Group paths semantically** (`<g id="mark">`, `<g id="wordmark">`) so downstream tooling can style or animate them.

## Filters (use sparingly)

- `feGaussianBlur` for soft glows (shadow, halo) — add `stdDeviation` proportional to viewBox size, not hard pixels.
- `feColorMatrix` for hue shifts, grayscale, or duotone effects.
- `feTurbulence` + `feDisplacementMap` for organic texture — expensive to render; keep off tiny app icons.
- `feComposite` for overlap math (intersect, exclude) when boolean ops aren't baked into paths.

Filters compound cost. Budget: one filter primitive per usage context, ideally baked into the static path before export.

## Blend modes (SVG 2 / CSS `mix-blend-mode`)

- `multiply` for duotone effects over photos.
- `screen` for overlapping color glows.
- `overlay` for contrast boosts.
- `difference` for inverted punch-out effects.
- `soft-light` for subtle texture blends.

Blend modes depend on the background. Test on both dark and light surfaces before shipping.

## Masks and clip-paths

- **`<clipPath>` for hard-edged cuts** (geometric shapes, type inside type).
- **`<mask>` for soft-edged or alpha-gradient cuts** (fade-outs, vignettes).
- Use `id` references sparingly and name them `clip-<purpose>` / `mask-<purpose>` for legibility.

## Gradients

- **`linearGradient`** — directional transitions; always include `gradientUnits="userSpaceOnUse"` for predictable positioning.
- **`radialGradient`** — center-focused glows, sphere-illusion depth.
- **Stops at 0%, stop-color, stop-opacity** — always include all three.
- **Prefer 2-3 stops max** unless photorealism is the goal. Too many stops read as muddy at small sizes.

## Animation (SMIL / CSS)

- **SMIL (`<animate>`, `<animateMotion>`, `<animateTransform>`)** — scoped to the SVG, no JS needed, best for "always-on" brand idle animation.
- **CSS animations inside `<style>`** — preferred for hover/trigger interactivity.
- **GSAP or Framer Motion via React** — when precision timing, scroll-driven, or interaction-reactive animation is needed.
- **Keep logo animation under 2 seconds and non-looping by default** — endless motion fatigues users fast.

## Optimization

1. **SVGO with a custom config** — strip editor metadata, round decimals, but preserve `id`s for animation targets.
2. **Manually inspect after SVGO** — it occasionally merges paths that break stroke rendering.
3. **Inline for hero / icon sizes** (< 5KB), link as `<img src>` for larger assets.
4. **`viewBox`, not `width`/`height`** — makes the logo responsively scalable.
5. **`preserveAspectRatio="xMidYMid meet"`** is the default you want 95% of the time.

## Accessibility

- **`<title>` immediately after `<svg>`** — announces to screen readers.
- **`<desc>` for longer context** if the logo carries meaning beyond its name.
- **`role="img"`** on the SVG element; **`aria-labelledby`** pointing at the title.
- **Do not rely on color alone** for meaning (e.g., dual-color states must differ in shape or label too).

## Theming with CSS custom properties

```svg
<style>
  svg { --mark-primary: #1a1a2e; --mark-accent: #eab308; }
  .mark-fill { fill: var(--mark-primary); }
  .mark-accent { fill: var(--mark-accent); }
</style>
```

External CSS can override `--mark-primary` for dark mode, product skins, or user themes without touching path geometry.

## Deliverable package checklist

- `logo.svg` — master, inline-ready, custom-properties-themed
- `logo-mono.svg` — single-color fallback for embroidery, signage, faxes
- `logo-dark.svg` — dark-surface optimized if the master is light-surface first
- `logo-favicon.svg` — minimal simplified mark that reads at 16px
- `logo.png` at 2x, 4x, 8x for raster fallback
- `tokens.css` + `tokens.json` — canonical color / spacing / typography values
- `usage.md` — one page: min size, clearspace, do / don't, placement on photos
