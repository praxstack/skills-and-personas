# Design Systems & Component Libraries

**When to load this file:** Building or extending a design system, defining design tokens, deciding component API shape, or evaluating component-library tradeoffs.

## Design Token Structure

Single source of truth exported to CSS, iOS, Android. Use Style Dictionary (Amazon) or Theo (Salesforce) for multi-platform, or just CSS custom properties + a JSON source for web-only.

Minimal token categories:
- **color:** primary scale (50-950), neutral scale, semantic (success/warning/error/info), plus role aliases (`--bg-surface`, `--text-primary`, `--border-subtle`) so theming swaps are clean.
- **spacing:** 4px or 8px base. Scale: 0, 4, 8, 12, 16, 20, 24, 32, 40, 48, 64, 80, 96. Name by use (`--space-page-gutter`) or T-shirt (`--space-md`) — pick one, stay consistent.
- **typography:** font-family (sans/serif/mono), font-size scale, line-height, letter-spacing, font-weight.
- **radius:** scale (0, 2, 4, 8, 12, 16, 24, full).
- **shadow:** elevation scale (sm, md, lg, xl, 2xl) — not individual values per component.
- **motion:** easing curves + durations as tokens, not inline.

Anti-token: component-specific tokens like `--button-hover-bg`. That's a style decision, not a token. Tokens are primitives; components compose them.

## Atomic Design (Brad Frost) — When It Helps

Atoms → Molecules → Organisms → Templates → Pages. Useful for ORGANIZATION, not for implementation hierarchy. Do not force every component into the taxonomy; many sit between levels.

What atomic design gets right: separating "Button" (atom, many contexts) from "LoginForm" (molecule, specific flow).

What it gets wrong in practice: over-decomposition. A "Card" molecule that just wraps an atom adds cost without value.

## Component API Design

**Composition over configuration.** Boolean-prop explosion is the signal you should have used composition.

Bad:
```tsx
<Card title="..." description="..." footer={<Button/>} imageUrl="..." />
```

Good:
```tsx
<Card>
  <Card.Image src="..." />
  <Card.Header>
    <Card.Title>...</Card.Title>
    <Card.Description>...</Card.Description>
  </Card.Header>
  <Card.Footer><Button/></Card.Footer>
</Card>
```

**Variant + size + state, then stop.** If a component has more than these three axes, it's probably two components. Use CVA (class-variance-authority) or Tailwind variants, not boolean-prop chains.

**Forward refs.** Every custom component that wraps a native element should `forwardRef` so consumers can compose focus management, tooltips, etc.

**`asChild` pattern (Radix).** Instead of `as` prop, accept `asChild` + use Slot to merge props with the child. Preserves type safety and avoids prop collision.

**Invariants to enforce via types:**
- If `loading` is true, `disabled` is implicitly true
- If `icon` only (no children), require `aria-label`
- If `variant="destructive"`, require confirmation for onClick (at docs level)

## Component Library Tradeoffs

| Library | Style | When to use |
|---------|-------|-------------|
| shadcn/ui | Copy-paste, Radix underneath | Default for most React apps — you own the code |
| Radix UI primitives | Headless + ARIA | When you want full visual control + don't want to rebuild accessibility |
| Headless UI | Headless, Tailwind-team | Tailwind-heavy codebases, simpler than Radix |
| MUI | Opinionated Material | Internal tools, B2B dashboards where design time is low priority |
| Chakra UI | Themed, accessible | Good DX, but look starts to feel generic without heavy theming |
| Ant Design | Enterprise, opinionated | Admin panels, heavy data UIs, Chinese-market apps |

**shadcn is not a library.** It's a pattern: copy components into your repo, own them, evolve them. Zero runtime cost, maximum flexibility, at the cost of manual updates.

## Theming Strategy

**CSS variables in :root + data-theme attribute:**
```css
:root { --bg: #fff; --text: #000; }
[data-theme="dark"] { --bg: #000; --text: #fff; }
```

Avoid JS-based theme switching where possible — CSS-only is faster and flash-free.

For `prefers-color-scheme`, include `<meta name="color-scheme" content="light dark">` to tell the browser to pick default form control colors.

## Storybook / Ladle

Every public component ships with stories for:
- Default
- All variants
- All sizes
- Loading / disabled / error states
- Long content (overflow behavior)
- Interactive playground

Stories double as documentation and visual regression fixtures.

## Versioning

Design system repo is versioned independently from consumers. Breaking changes (prop rename, removed variant) require a major bump. Provide codemods for rename migrations.

Deprecation protocol: warn in console with migration link for one minor version, then remove in next major.
