# Accessibility — craft that everyone can use

Accessible is not a constraint on good design; it *is* good design. Most of it
is free if you build correctly from the start.

## Semantics first

- Use real elements: `<button>` for actions, `<a href>` for navigation,
  `<nav>/<main>/<header>/<footer>/<section>` for landmarks, `<h1>`–`<h6>` in
  order (one `<h1>`, no skipping levels), `<ul>/<ol>` for lists, `<label>` tied
  to every input. A `<div onclick>` is a bug.
- Buttons vs links: if it goes somewhere, it's a link; if it does something,
  it's a button.
- Use `<dialog>` for modals (native focus trap, `Esc`, backdrop).

## Keyboard

- Everything interactive must be reachable and operable by keyboard, in a
  logical tab order. Never `tabindex` > 0.
- **Visible focus** — never `outline:none` without a replacement. Design a nice
  focus ring: `:focus-visible{outline:2px solid var(--accent);outline-offset:2px}`.
- Manage focus on route/modal changes (move focus into the new view/dialog,
  restore it on close). Add a skip-to-content link.

## Screen readers & ARIA

- Prefer native semantics over ARIA. First rule of ARIA: don't use ARIA if HTML
  can do it.
- When needed: `aria-label`/`aria-labelledby` for icon-only controls,
  `aria-expanded`/`aria-controls` for disclosures, `aria-current` for the active
  nav item, `aria-live="polite"` for async status/toasts, `role="status"`.
- Decorative images: `alt=""`. Meaningful images: descriptive `alt`. Icons that
  duplicate visible text: `aria-hidden="true"`.

## Color & contrast

- Body text ≥ 4.5:1, large text (≥24px or 19px bold) and UI/graphics ≥ 3:1
  against their background. Check it — don't eyeball light-gray-on-white.
- **Never rely on color alone** to convey meaning — add icon, text, or pattern
  (e.g. error state = red + icon + message, not just red border).
- Support `prefers-color-scheme` and don't break at high zoom (up to 200%) or
  400% reflow.

## Motion & media

- Honor `prefers-reduced-motion`: replace transforms/parallax/autoplay with
  instant or minimal change. Never auto-play looping motion that can't be paused.
- Captions/transcripts for audio/video. No content that flashes > 3×/second
  (seizure risk).

## Forms

- Label every field; group with `<fieldset>/<legend>`. Associate errors with
  `aria-describedby` and announce them. Don't disable submit silently — explain
  what's needed. Correct `inputmode`/`type`/`autocomplete`.

## Touch & target size

- Interactive targets ≥ 44×44px (24px absolute minimum with spacing). Adequate
  spacing between tappable items.

## Quick audit before shipping

- Tab through the whole thing — can you do everything, is focus always visible?
- Zoom to 200% — does it still work?
- Run an automated pass (axe/Lighthouse) — fix what it finds, then hand-check
  the things it can't (focus order, meaningful alt, live regions).
