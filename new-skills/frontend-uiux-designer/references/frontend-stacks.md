# Frontend Stacks & Tooling

**When to load this file:** Choosing framework, state management, styling approach, or build tooling for a new project or refactor.

## Framework Selection Matrix

| Framework | Pick when | Avoid when |
|-----------|-----------|------------|
| React + Next.js (App Router) | Default for most product UIs, marketing sites, SaaS | Tiny static sites (overkill), RSC complexity is a tax for small apps |
| React + Remix/React Router | Data-heavy apps, nested routes, progressive enhancement matters | Static-first content sites |
| Vue + Nuxt | Team prefers SFCs; Vue ecosystem fits (Pinia, VueUse) | Tight React-only talent pool |
| Svelte/SvelteKit | Bundle size critical; compile-time wins; simpler mental model | Need React-specific libs; team familiarity low |
| Solid | Want fine-grained reactivity + React-like syntax | Ecosystem immaturity will bite you |
| Astro | Content-first sites (marketing, docs, blog) with islands of interactivity | App-style heavy interactivity |
| Qwik | Sub-second TTI critical on slow devices | Team not up for resumability mental model |

**Meta-consideration:** the team's existing expertise usually beats the marginally better framework. Pick the one they'll ship well with.

## React: Server Components vs Client Components

**RSC when:**
- Data fetching + rendering stays on server (DB queries, CMS reads)
- No interactivity needed
- Want to keep client bundle small

**Client ('use client') when:**
- Uses hooks (useState, useEffect), event handlers, browser APIs
- Uses Context from a provider
- Needs third-party client-only libraries

**Boundary pattern:** Server component passes serialized props → Client component. Keep interactive islands small; let the rest stay on the server.

**Common RSC pitfall:** marking a whole route "use client" because one leaf is interactive. Instead, keep the route server and isolate the client island.

## State Management Decision Tree

1. **Is it component-local?** → `useState` / `useReducer`.
2. **Shared between parent and a few children?** → Lift state. Props drilling is fine up to ~3 levels.
3. **Cross-tree app config (theme, auth, i18n)?** → React Context (once, at the right level). Not for rapidly-changing values — every consumer re-renders.
4. **Server data (fetched, cached, refetched)?** → TanStack Query or SWR. These handle loading/error/stale/background-refresh/dedup/invalidation. Don't reinvent in Redux or Zustand.
5. **Global client state that's actually shared (cart, complex wizard, collab cursors)?** → Zustand (simple), Jotai (atomic, fine-grained), or Redux Toolkit (when you need middleware/devtools/time-travel).
6. **Form state?** → React Hook Form + Zod (validation). Formik is legacy.
7. **URL as state (filters, tabs, dialogs)?** → Put it in search params. Makes state shareable and survives reload. Next.js and TanStack Router have helpers.

**Red flag:** Redux/Zustand storing data that came from a server and never changes locally. That's a cache — use TanStack Query.

## Styling Approach

| Approach | Pros | Cons |
|----------|------|------|
| Tailwind | Fast iteration, no naming, consistent via design tokens, tiny runtime | Learning curve, verbose class strings, JIT-only customization |
| CSS Modules | Scoped styles, standard CSS | Build config, no runtime dynamism |
| Vanilla Extract | Type-safe CSS, zero-runtime | Build complexity |
| Styled Components/Emotion | Dynamic props, good DX | Runtime cost, SSR hydration cost, slower |
| Panda CSS | Type-safe + zero-runtime + recipe system | Newer ecosystem |
| Plain CSS + custom properties | Zero cost, modern CSS is great | Naming/scope is on you |

**Default recommendation:** Tailwind + CVA (class-variance-authority) for variants, CSS custom properties for theming. Use CSS Modules or plain CSS when Tailwind is a poor fit (print styles, complex selectors, heavy component styling that would bloat classNames).

Avoid: Styled Components for new projects. Runtime cost and hydration issues outweigh benefits now that Tailwind and zero-runtime CSS-in-JS exist.

## Animation

| Library | Pick when |
|---------|-----------|
| CSS animations/transitions | Simple state changes, hover, reveals. Always first choice. |
| Motion (motion.dev, née Framer Motion) | React declarative animations, layout animations, gesture interactions |
| GSAP | Complex timelines, scroll-triggered sequences, SVG animation, framework-agnostic |
| React Spring | Physics-based, natural motion |
| Anime.js | Small, direct DOM animation (non-React) |
| View Transitions API | Same-document + cross-document navigation transitions (progressive) |

**Performance rule:** Test animations on a throttled CPU (Chrome DevTools Performance tab → CPU throttle 4-6x). If it drops below 60fps, simplify.

## Build Tooling

- **Vite** for SPAs, libraries, dev-server speed. Default choice.
- **Next.js built-in** if you're on Next.
- **Turbopack** (Next.js 15+) — still maturing; stable for dev, production varies.
- **esbuild** standalone for libraries where bundle-size is critical.

## Performance Budget Defaults

- JS bundle (initial): <200KB gzipped for SPA; <80KB for content sites.
- CSS: <30KB gzipped.
- Images: AVIF > WebP > JPEG. Lazy-load below the fold.
- Fonts: 2 max, subset, WOFF2, `font-display: swap` (or `optional` if you prefer no swap flash).
- Third-party scripts: measure impact; defer non-critical; consider Partytown for analytics.

## Code Splitting Strategy

- Route-level: automatic in Next.js and most meta-frameworks.
- Component-level: `React.lazy` + Suspense for heavy components (rich editors, charts, modals).
- Library-level: dynamic `import()` for occasional-use heavy libs (PDF generator, date picker with large locale data).

Avoid over-splitting — each chunk has overhead. 10 chunks of 50KB can be slower than 1 chunk of 400KB if parallelism is limited.

## File Structure (React)

```
src/
  app/              # routing (Next.js App Router) or pages/
  components/
    ui/             # design system primitives
    features/       # feature-scoped components
    layouts/
  lib/              # utilities, API client, helpers
  hooks/            # custom hooks
  styles/           # globals, tokens
  types/            # shared TS types
```

Feature folders > type folders at scale. Group by feature/domain, not by kind (hooks/, components/, utils/). Easier to move, delete, and reason about.

## Testing Stack

- **Unit:** Vitest (or Jest if legacy). Keep in watch mode during dev.
- **Component:** Testing Library (React Testing Library) — test behavior, not implementation.
- **E2E:** Playwright (preferred) or Cypress. Run a small set of critical flows on PRs.
- **Visual regression:** Chromatic, Percy, or Playwright snapshot — catches CSS regressions CI-ready tests miss.
- **Accessibility:** axe-core integrated in tests (`@axe-core/playwright`).
