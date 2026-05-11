# Accessibility & WCAG

**When to load this file:** Any interactive UI, forms, modals, navigation, custom widgets, or when auditing for WCAG compliance. MANDATORY reading for interactive work.

## WCAG Levels — What to Actually Target

- **A:** Bare minimum, legal floor in many jurisdictions. Not enough for product quality.
- **AA:** Industry standard. Target this by default for all user-facing products.
- **AAA:** Reserved for critical reading paths (news, healthcare content, legal), not whole apps. AAA is often infeasible for interactive UIs (7:1 contrast, no flashing, etc.).

## POUR Applied

**Perceivable**
- Alt text for meaningful images; empty `alt=""` for decorative so screen readers skip them.
- Captions for video, transcripts for audio — always.
- Contrast: 4.5:1 normal text, 3:1 large text (>=18px or >=14px bold), 3:1 UI components and graphical objects.
- Resize to 200% without content loss or horizontal scroll. Use rem/em for text, not px.
- Content reflows at 320px viewport width.

**Operable**
- Every interactive element reachable by Tab, activatable by Enter/Space.
- Visible focus indicator at 3:1 contrast minimum. Don't reuse hover styles — focus is a distinct state.
- Skip-to-main-content link as first focusable element.
- No keyboard traps (can always Tab out, or provide Escape).
- No flashing > 3 times/second in a large area.
- Target size 24x24 CSS pixels minimum (WCAG 2.2); 44x44 preferred for touch.

**Understandable**
- `<html lang="en">` (or correct language) — screen readers use this to pick pronunciation.
- Consistent navigation — same nav items in same order on every page.
- Form errors: identify the field, explain the error, suggest the fix. Not "Invalid input" alone.
- No auto-submit on focus change; no surprise popups on focus.

**Robust**
- Valid HTML (no duplicate IDs — breaks `aria-describedby`).
- Every interactive widget has accessible name, role, value.
- Status messages use `role="status"` or `aria-live="polite"`; errors use `role="alert"` or `aria-live="assertive"`.

## Semantic HTML Checklist

Before reaching for ARIA, ask: is there a native element?

- Button (clicks things) → `<button>`. Not `<div onClick>`.
- Link (navigates) → `<a href>`. Not `<button onClick={navigate}>`.
- Heading (structural) → `<h1>`-`<h6>` in order, never skipped.
- List → `<ul>`/`<ol>` with `<li>`. Screen readers announce "list, 5 items".
- Form → `<form>` with `<label>` bound to inputs via `for`/`id` or wrapping.
- Checkbox/radio → native `<input type>`. Custom ones are pain.
- Disclosure (show/hide) → `<details>`/`<summary>` if basic; otherwise button + aria-expanded.
- Dialog → `<dialog>` with `showModal()` for modals (handles focus trap, Escape, inert backdrop — wrap with Radix if you need more control).

## ARIA Patterns That Matter

**`aria-label` vs `aria-labelledby` vs visible label:** Prefer visible label. Use `aria-labelledby` to point to an existing visible element. Use `aria-label` only when no visible text exists (icon-only button).

**`aria-describedby`:** For supplementary info like hints or error messages. Announced after the label.

**`aria-expanded`:** On the trigger, not the panel. Toggles true/false.

**`aria-controls`:** On the trigger, points to the ID of the controlled element. Some screen readers use it for navigation.

**`aria-current`:** For current page in nav (`page`), current step in wizard (`step`).

**`aria-live`:**
- `polite` for non-urgent updates (search results count, toast notifications)
- `assertive` for urgent (error banners, form submission errors) — interrupts current announcement
- `off` (default) to disable updates

Live regions must be in DOM when the page loads — dynamically inserted live regions often miss the first update. Use an empty live region container and inject content into it.

**`aria-hidden="true"`:** Hide decorative elements from screen readers. NEVER on focusable elements (creates ghost-focus bug where keyboard users can focus invisible elements).

## Focus Management

**Focus on route change (SPA):** Move focus to `<h1>` or main content on navigation. Otherwise screen-reader users don't realize the page changed.

**Focus trap in modals:** Tab cycles through modal; Escape closes; focus returns to trigger on close. Use Radix Dialog or react-focus-lock.

**`:focus-visible` not `:focus`:** Avoids showing focus ring on mouse clicks while preserving it for keyboard. Fallback to `:focus` for older browsers.

```css
button:focus-visible {
  outline: 2px solid var(--focus);
  outline-offset: 2px;
}
```

**Skip links:** First focusable element. Visible on focus (not `display: none`, which removes from tab order; use visually-hidden + reveal on focus).

## Keyboard Shortcuts Within Widgets

- **Tabs:** Arrow keys move between tabs; Tab moves to tabpanel content.
- **Combobox/autocomplete:** Down arrow opens/moves, Enter selects, Escape closes, typing filters.
- **Menu:** Arrow keys navigate items, Enter activates, Escape closes, Home/End jump.
- **Listbox/select:** Same as menu.
- **Tree:** Arrow keys navigate, Enter/Space activates, Left collapses, Right expands.

Radix, Headless UI, and React Aria implement these correctly — don't reinvent.

## Screen Reader Copy

Write for assistive tech:
- Icon-only button: `aria-label="Close dialog"` not `"X"`.
- Image link: combine image alt and surrounding text into one coherent announcement; avoid duplicating.
- Form errors: announce field + error in one string: `aria-describedby` pointing to "Email is required".
- Loading: `aria-live="polite"` region saying "Loading search results" then "Showing 12 results for ..."

## Testing Approach

1. **Tab through every page.** Can you reach everything? Is focus visible? Any traps?
2. **Screen reader pass:** VoiceOver (macOS: Cmd+F5), NVDA (Windows, free), TalkBack (Android). Do announcements make sense?
3. **Automated scan:** axe DevTools or Lighthouse a11y audit. Catches ~30% of issues; rest needs humans.
4. **Zoom to 200%.** Does layout hold? Content visible? No horizontal scroll.
5. **prefers-reduced-motion:** Toggle in OS settings; animations should collapse.
6. **Color contrast tool:** Stark, Contrast Checker, or DevTools contrast ratio.

## Common Mistakes

- Using placeholder as label — disappears on focus, fails when autofilled, low contrast.
- Custom dropdown that isn't keyboard navigable.
- Focus ring removed with `outline: none` and no replacement.
- `role="button"` on a span with onClick but no Space/Enter handler.
- Form validation only on submit, no per-field feedback.
- Motion that cannot be paused/stopped (auto-playing carousels).
- Color as sole indicator (red border only for error — add icon and text).
- `tabindex="0"` on non-interactive content, making screen reader users stop on decorations.
- Loading spinners without `aria-live` or status text — users wait in silence.
