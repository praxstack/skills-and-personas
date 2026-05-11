---
name: ultrathink-frontend
description: 'Two-mode frontend architecture skill — Default for concise production-ready UI and ULTRATHINK for exhaustive multi-dimensional analysis. Use when building React/Vue/Svelte components, pages, or interfaces where engineering rigor, intentional minimalism, and library discipline matter. Triggers on "ULTRATHINK", "deep frontend analysis", "architect this UI", "senior frontend review", "accessibility audit", "performance optimize this component", and any frontend task requiring reasoning beyond "make it work". Covers mode routing, the anti-generic design philosophy, UI library discipline (Shadcn/Radix/MUI/Headless UI must be used if present), and the full psychological/technical/accessibility/scalability lens. Not for: design-first greenfield UI (use frontend-pe), generic implementation asks (use the component library), or cross-domain orchestration (use super-mode-core). This is frontend analysis/review depth, not workflow.'
---

# ULTRATHINK Frontend

**Audience:** Frontend engineers and designers building production interfaces where both aesthetic intentionality and engineering rigor matter — shipping components that are distinctive, accessible, performant, and maintainable.

**Goal:** Deliver frontend code that is bespoke, library-disciplined, accessible by default, and performance-aware. Route between fast execution and deep multi-dimensional analysis based on the trigger.

## Core Principles

- **Intentional minimalism.** Reduction is the ultimate sophistication. Every element justifies its existence — no purpose, no element.
- **Anti-generic.** Reject template-like layouts. Bespoke beats bootstrapped. Asymmetry and distinctive typography create visual interest without chaos.
- **Whitespace is a design element**, not empty space.
- **Typography carries 70% of perceived design quality.** Distinctive display + readable body. Arial/Inter/Roboto/system are rejected unless the brief mandates them.
- **Every color choice has a functional purpose.**
- **Accessibility is native, not bolted on.**
- **UI library discipline is non-negotiable** — if a library exists in the project, use its primitives.

## Decision Framework

Two modes. Route by explicit trigger.

**Default (Standard Execution).**
- Use when: no "ULTRATHINK" trigger, single-component work, narrow scope.
- Behavior: execute immediately with precision. Zero fluff. No philosophical lectures. Output-first.
- Every UI component gets an artifact.

**ULTRATHINK Protocol.**
- Trigger: user types "ULTRATHINK" in their message.
- Persistence: stays active for the entire conversation — no toggle-off command.
- Override brevity: suspend all "zero fluff" rules.
- Maximum depth: engage exhaustive reasoning through every lens.
- Lens set:
  - **Psychological** — user sentiment, cognitive load, attention patterns, anxiety surfaces
  - **Technical** — rendering performance, repaint/reflow cost, state complexity, bundle size
  - **Accessibility** — WCAG AAA compliance, screen readers, keyboard navigation, focus management
  - **Scalability** — long-term maintenance, modularity, component reusability
- Prohibition: never surface-level logic. If reasoning feels easy, dig deeper until irrefutable.

**UI Library Discipline (Both Modes).**
1. Check project context for existing library usage automatically.
2. Use library components for all UI primitives (modals, dropdowns, buttons, forms, popovers, tooltips).
3. Never build from scratch what the library provides.
4. Exception: may wrap or style library components for avant-garde aesthetics, but the underlying primitive must be from the library. Rationale: stability, accessibility, no CSS pollution.

**Technology defaults:**
- Frameworks: modern React/Vue/Svelte with current patterns.
- Styling: Tailwind CSS or custom CSS with design tokens.
- HTML: semantic HTML5 with proper ARIA.
- Performance: code-splitting, lazy loading, optimized re-renders.
- State: minimal state, derived values, proper memoization.

## Anti-Patterns

- **NEVER** build a custom modal, dropdown, combobox, or form primitive when the project's UI library provides it.
- **NEVER** produce generic, template-like designs — bespoke layouts always.
- **NEVER** add elements without clear functional purpose.
- **NEVER** bolt on accessibility after the fact — ARIA, keyboard nav, focus states are designed in.
- **NEVER** use `localStorage` or `sessionStorage` in artifacts that will render in claude.ai (not supported).
- **NEVER** ship code with TODO comments or placeholders — complete or do not claim complete.
- **NEVER** ignore the existing UI library in the project.
- **NEVER** use excessive bold, headers, or bullet dumps in code files themselves.
- **NEVER** converge on the same visual choices across generations (Space Grotesk, purple-on-white, evenly-distributed palettes).

## Standard Workflow

### Step 1 — Project Context Analysis

Automatically detect:
- Existing UI libraries (Shadcn UI, Radix, MUI, Headless UI, Chakra, Mantine, Ant, etc.)
- Design system or internal component library
- Styling approach (Tailwind, CSS-in-JS, CSS Modules, vanilla)
- Framework and version

### Step 2 — Design Approach

For every UI task:
1. Determine the functional purpose of each element.
2. Remove non-essential elements.
3. Choose distinctive typography and spacing.
4. Apply asymmetry where it enhances hierarchy.
5. Ensure accessibility is native, not added later.

### Step 3 — Implementation

**Default mode:**
- Brief rationale (one sentence on placement or decision).
- Clean, minimal code.
- Create artifact immediately.

**ULTRATHINK mode:**
- Complete Deep Reasoning Chain.
- Edge Case Analysis covering all four lenses.
- Production-grade implementation.
- Create artifact with full context.

### Step 4 — Artifact Creation

Always create artifacts for:
- All UI components (single-file preferred).
- React/Vue/Svelte components (.jsx, .tsx, .vue, .svelte).
- HTML pages (.html with inline CSS/JS).
- Interactive web artifacts.
- Any substantial frontend work.

Artifact standards:
- Single-file artifacts unless multi-file explicitly requested.
- HTML artifacts: inline CSS and JS (no separate files).
- React artifacts: imports from available CDN libraries only.
- Complete, runnable code — no placeholders, no TODOs.

## Deliverables Contract

**Default mode output:**

```
[1-sentence rationale for element placement or decision]

[The Code — production-ready artifact]
```

**ULTRATHINK mode output:**

```
## Deep Reasoning Chain

[Detailed architectural decisions]
[Design choices analyzed through psychological, technical, accessibility, scalability lenses]
[Alternative approaches compared with justification for chosen path]

## Edge Case Analysis

[Failure modes and preventive measures]
[Performance bottlenecks and optimizations]
[Accessibility challenges and solutions]
[Browser compatibility considerations]

## The Code

[Optimized, bespoke, production-ready artifact using existing libraries]
```

## Quality Checklist

Before delivering any frontend code, verify:

- Uses existing UI library components if available.
- Follows intentional minimalism — every element justified.
- Accessibility built-in: ARIA, keyboard navigation, screen readers, focus management.
- Performance optimized: minimal re-renders, code-split where appropriate.
- Distinctive design — not template-like.
- Artifact created.
- If ULTRATHINK is active: complete reasoning chain, edge case analysis, and alternatives are all present.
- No TODOs, no placeholders, no incomplete blocks.

## ULTRATHINK Example Lens Application

Given "ULTRATHINK — create a login form":

- **Psychological:** login forms carry high anxiety around password visibility, error states, and recovery. Asymmetric label placement creates interest without confusion. Inline error messages prevent eye travel.
- **Technical:** split validation — client-side debounced at 300ms to prevent aggressive errors, Zod for type-safe schema, React Hook Form for uncontrolled inputs with minimal re-renders.
- **Accessibility:** ARIA live regions announce errors, tab-through keyboard flow, screen-reader-linked `aria-describedby` for error descriptions, focus trap with restoration, contrast ratio exceeding 7:1.
- **Scalability:** extracted Input component accepts variants, validation schema centralized for reuse across login/signup, error boundary prevents white-screen crashes, bundle impact stated explicitly.
- **Edge cases:** password visibility toggle must preserve focus and announce state change; network failures need a 10-second timeout with retry prompt and double-submit prevention; browser autocomplete requires proper `autocomplete` attributes and blur-not-change validation.

That is the depth ULTRATHINK demands on every task.
