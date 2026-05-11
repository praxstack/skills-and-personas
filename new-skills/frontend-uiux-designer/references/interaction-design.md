# Interaction Design & Motion

**When to load this file:** Designing interactive elements, states, transitions, micro-interactions, or applying usability heuristics.

## State Matrix (Mandatory)

Every interactive element needs visual treatment for:

| State | Visual | Notes |
|-------|--------|-------|
| Default (rest) | Base style | |
| Hover | Subtle (~5% lightness shift, shadow bump) | Desktop only; do not design touch UX around hover |
| Active/pressed | More dramatic; scale 0.98; darker | Felt, not just seen |
| Focus-visible | Distinct outline, 3:1 contrast | NOT same as hover |
| Disabled | 40-50% opacity; cursor not-allowed; `aria-disabled` or `disabled` | `pointer-events: none` for decorative-only |
| Loading | Spinner or skeleton; prevent double-submit | `aria-busy="true"`, keep layout stable |
| Error | Red accent + icon + message (not color alone) | Announce via `aria-live` |
| Success | Green/neutral confirmation | Brief, auto-dismiss or persist based on importance |
| Empty | Explanation + CTA | Never silent blank regions |

Designs that only show default + hover are half-done.

## Usability Laws Applied

**Fitts's Law** (target acquisition time is f(distance, size)):
- Primary CTAs: larger than secondary. Not just visually — hit area too.
- Screen edges/corners have infinite size — use for persistent controls (close buttons in top-right, menu bars).
- Minimum touch target: 44x44 (iOS HIG), 48x48 (Material), 24x24 CSS px (WCAG 2.2 AA minimum). Prefer 44+.
- Expand hit area beyond visual bounds with padding or absolutely-positioned pseudo-elements, especially for small icons.

**Hick's Law** (decision time grows log with choices):
- Keep primary nav to ~7 items; split into secondary nav if more.
- Progressive disclosure: advanced options hidden until needed.
- Provide sensible defaults so users can pick "accept" instead of configuring.

**Miller's Law** (working memory ~7±2):
- Chunk long numbers (phone: (555) 123-4567).
- Multi-step forms when fields exceed ~7 logical groups.
- Don't show 20 nav items — categorize.

**Jakob's Law** (users transfer mental models from other sites):
- Logo top-left → home. Cart top-right. Search top. Hamburger on mobile.
- Don't reinvent icons: trash = delete, pencil = edit, gear = settings.
- Deviate only when you can afford the learning cost (distinctive products can; utility products can't).

## Gestalt (visual perception applied)

- **Proximity:** Whitespace groups. Related form fields closer; separators between groups.
- **Similarity:** Same style = same category. All primary buttons match; all links match.
- **Continuity:** Eye follows lines/curves — align to grids for scannability.
- **Closure:** Partial shapes work (hamburger icon) — the mind fills them in.
- **Figure/ground:** Modal overlay at ~50-70% black. Sufficient contrast between surface and content.
- **Common fate:** Elements animating together read as related — good for list reveals, card groups.

## Motion Principles (Disney → UI)

Speed carries meaning:
- 100-200ms: instant/responsive (hover, button press feedback)
- 200-400ms: intentional (modal open, drawer slide, tab switch)
- 400-600ms: dramatic (page reveal, first-load orchestration)
- >1000ms: only when actually loading; show progress

**Easing:**
- `ease-out` for entrances (objects decelerate as they arrive)
- `ease-in` for exits (accelerate as they leave)
- `ease-in-out` for continuous, self-contained motion
- Linear only for indeterminate progress (spinners) or looping anims

**Material-standard curves:**
```css
--ease-standard: cubic-bezier(0.4, 0, 0.2, 1);   /* default */
--ease-decelerate: cubic-bezier(0, 0, 0.2, 1);   /* entrance */
--ease-accelerate: cubic-bezier(0.4, 0, 1, 1);   /* exit */
--ease-sharp: cubic-bezier(0.4, 0, 0.6, 1);      /* interruption */
```

**Bounce/overshoot** (elastic): use sparingly. Great for success confirmations, wrong for page transitions.

## Performance Rules for Motion

- **Animate `transform` and `opacity` only.** Everything else triggers layout/paint.
- **`will-change` sparingly.** It tells the browser to promote to a layer; overusing creates memory bloat. Add it, animate, remove it.
- **Avoid animating `filter: blur()` on large elements** — GPU-accelerated but expensive.
- **Measure on throttled CPU.** DevTools Performance → CPU throttle 4-6x. If it drops below 60fps, simplify.
- **Respect `prefers-reduced-motion`:**
  ```css
  @media (prefers-reduced-motion: reduce) {
    *, *::before, *::after {
      animation-duration: 0.01ms !important;
      transition-duration: 0.01ms !important;
    }
  }
  ```
  Don't just remove animation — the element still needs to transition state instantly, not remain in a transient state.

## Micro-interactions (Dan Saffer structure)

Trigger → Rules → Feedback → Loops/Modes.

**Like button example:**
- Trigger: click
- Rules: toggle state, update count optimistically
- Feedback: icon fills with color, brief scale bounce, count increments
- Loops: stays liked until un-clicked

**Optimistic UI:** Update UI immediately on user action; rollback on API error. Better perceived performance; requires careful error messaging when rollback happens.

**Feedback timing:**
- <100ms: feels instant, no indicator needed
- 100-1000ms: brief indicator (button shows spinner, disabled while processing)
- >1s: progress indicator required (determinate if possible; skeleton for content)
- >10s: consider background processing + notification on completion

## Form Patterns

- **Labels above inputs**, not floating or inside (accessibility + usability beats density).
- **Required fields marked**, not optional ones (required is the constraint).
- **Inline validation on blur**, not on keypress. Submit-time validation is backup.
- **Error message below field**, red + icon + text. Linked via `aria-describedby`.
- **Submit button disabled** only when form is invalid AND user has interacted. Disabled on load hides why.
- **Password visibility toggle** (eye icon) — reduces errors significantly.
- **Autocomplete attributes** (`autocomplete="email"`, `"new-password"`, `"one-time-code"`) — huge UX win for free.

## Responsive Interaction Patterns

- **Column drop:** Multi-column desktop → stacked mobile. Most common.
- **Off-canvas:** Nav slides in from edge on mobile (hamburger-triggered).
- **Priority+:** Visible nav items based on space; overflow into "More" menu.
- **Tabs on desktop → accordion on mobile:** When tabs don't fit.

**Touch considerations:**
- No hover. Active/pressed feedback is your main tool.
- 44x44 minimum targets; spacing between targets 8px+.
- Swipe gestures (carousel, drawer) with visible handle or indicator — gestures are hidden otherwise.
- Pull-to-refresh where natural (feed, inbox).
- Long-press for context menu alternative only if there's a visible alternative too.

## Loading State Hierarchy

1. **Skeleton screens** for content pages where layout is known (FB, LinkedIn). Reduces perceived wait.
2. **Spinners** when duration is unknown and content structure is unclear.
3. **Progress bars** when you have a definite percentage (file upload, multi-step).
4. **Optimistic UI** for user-initiated mutations where failure is rare.
5. **Streaming** (for AI outputs, long reports) — show content as it arrives.

Never leave the screen blank. Never show a spinner for <100ms (flicker).
