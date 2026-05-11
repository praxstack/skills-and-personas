# Design System Package — Color, Typography, Tokens

## When to load this file

Load after final concept approval when generating the deliverable package. Covers color psychology, typography guidance, style patterns, design token formats, and Figma spec templates.

## Color

### Primary palette (build 3-5 values)

- **Brand primary** — the signature color users will associate with the brand.
- **Brand secondary** — supports primary, used for accents and hover states.
- **Neutral scale** — 5-9 grays from near-black to near-white, perceptually even steps (use OKLCH for even perceptual distribution, then convert to hex).
- **Semantic colors** — success / warning / danger / info. Accessible against both light and dark backgrounds.

### Psychology quick reference

| Hue family | Typical associations | Watch out for |
|---|---|---|
| Blue | Trust, stability, tech | Overused in fintech/tech (differentiate with saturation or hue shift) |
| Green | Growth, wellness, finance | Pale green reads clinical; olive reads outdoorsy |
| Red | Energy, urgency, passion | Easy to read as warning; pair with calmer neutrals |
| Yellow / Gold | Optimism, value, warmth | Accessibility challenge on white backgrounds |
| Purple | Creativity, premium, imagination | Generic AI-gradient territory — be specific |
| Orange | Playful, accessible, appetite | Hard to scale to luxury |
| Black | Luxury, authority, minimalism | Can read as heavy; soften with off-black |
| White space | Sophistication, clarity | Empty if not balanced with intentional elements |

### Accessibility

- **WCAG AA**: 4.5:1 contrast for body text, 3:1 for large text and UI elements.
- **WCAG AAA**: 7:1 body, 4.5:1 large — harder but reachable with a deliberate palette.
- Test every pairing at both extremes of the palette. A brand's primary must work on both its neutral-lightest and neutral-darkest.
- Color blindness: verify with a simulator. Red/green distinctions often fail for 8% of men.

## Typography

### Picking a typeface

- **Match the brand mood words**. Geometric sans for modern/tech, humanist sans for warm/accessible, serif for trust/editorial, slab serif for confident/sturdy, display for distinctive.
- **Test at the smallest real-world size** (e.g., 12px app menu) before approving.
- **Open-source first** unless the brand budget justifies Foundry licensing. Inter, IBM Plex, Source Sans, Recursive are reliable defaults — but watch for overuse (Inter especially).
- **Logomark wordmarks should use paths, not font references** — fonts go missing; paths don't.

### Type system

- **Display** — hero headlines, usually 48-96px, tightened letter-spacing
- **Heading scale** — 4-6 sizes with clear hierarchy (e.g., 1.25x or 1.333x modular scale)
- **Body** — 14-16px base, 1.5-1.7 line-height, left-aligned with natural ragged right
- **Mono** — for code and data; prefer a typeface designed for this (JetBrains Mono, Fira Code)

### Pairing rules

- **Two families max** (one for display/headings, one for body) unless the brand is typography-led.
- **Contrast via weight and size**, not family-count.
- **Same x-height family** for display+body creates a more cohesive feel than wildly different typefaces.

## Logo variants to deliver

- Primary horizontal
- Primary vertical (stacked)
- Monochrome (black and white versions)
- Reversed (for dark surfaces)
- Icon-only / mark
- Wordmark-only (if combination mark)
- Favicon / app icon (16px, 32px, 180px, 512px raster + SVG)

## Clearspace and sizing

- **Clearspace** — use a unit derived from the logo itself (often the x-height or the height of the smallest element) and enforce that as the minimum padding around the mark.
- **Minimum size** — test the logo at 16px, 32px, 48px digital and 0.5" / 1" print. Below the minimum readable size, provide a simplified favicon variant.

## Design tokens — file format

### CSS custom properties (`tokens.css`)

```css
:root {
  --brand-primary: #1a1a2e;
  --brand-primary-hover: #26264a;
  --brand-accent: #eab308;
  --neutral-900: #0a0a0f;
  --neutral-100: #fafaff;
  /* ... */
  --type-display: 'Brand Display', system-ui, sans-serif;
  --type-body: 'Brand Body', system-ui, sans-serif;
  --space-1: 0.25rem;
  --space-8: 2rem;
  --radius-sm: 0.25rem;
  --radius-lg: 1rem;
}
```

### JSON (`tokens.json`) — tool-agnostic, suitable for Style Dictionary or Figma Tokens

```json
{
  "color": {
    "brand": {
      "primary": { "value": "#1a1a2e" },
      "accent": { "value": "#eab308" }
    },
    "neutral": {
      "900": { "value": "#0a0a0f" },
      "100": { "value": "#fafaff" }
    }
  },
  "type": {
    "display": { "value": "Brand Display" },
    "body": { "value": "Brand Body" }
  },
  "space": {
    "1": { "value": "0.25rem" },
    "8": { "value": "2rem" }
  }
}
```

## Figma spec template

Create a Figma file with these pages:

1. **Cover** — logo variants at display size, brand personality in a single paragraph
2. **Logo** — all variants, clearspace rules, size minimums, do/don't examples
3. **Color** — primary palette with hex/rgb/hsl, neutral scale, semantic colors, accessibility notes
4. **Typography** — type scale, weights, letter-spacing rules, real-text examples
5. **Spacing** — spacing scale visualized, grid system, component padding conventions
6. **Iconography** — icon grid, stroke weight, corner radius, optical sizing
7. **Motion** — animation timing curves, durations, idle-animation specs
8. **Tokens** — link out to `tokens.css` and `tokens.json` source of truth

Publish the Figma file as a shared library so product teams can link components back to canonical tokens.
