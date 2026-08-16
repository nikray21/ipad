# Interactive prototypes & apps

A prototype's job is to feel real enough to evaluate a flow, not to be
production code. Prioritize: believable states, real interaction feedback, and
the happy path working end-to-end.

## Principles

- **Make the core loop actually work.** If it's a todo app, adding/completing/
  deleting must work with real state. Fake the periphery (auth, settings), nail
  the spine.
- **Real data shape, plausible content.** Seed with realistic, specific data —
  never "Lorem ipsum" or "Item 1/2/3". Specificity sells the prototype.
- **Every interaction gives feedback** within 100ms: press states, optimistic
  UI, transitions between views, empty/loading/error states designed (not
  afterthoughts).
- **State persists** where the user would expect (localStorage) so a refresh
  doesn't wipe their work. Restore scroll/position on load. Never clobber
  storage you didn't write.
- **Follow the platform.** iOS feels different from Android feels different from
  desktop web. Match the target's conventions (nav, gestures, type, hit
  targets ≥44px on touch).

## Architecture (plain JS, no framework needed for most prototypes)

Single source of truth + render-from-state:

```js
const state = { todos: [], filter: 'all' };
const listeners = new Set();
function setState(patch) {
  Object.assign(state, patch);
  save();
  listeners.forEach(fn => fn(state));
}
function subscribe(fn) { listeners.add(fn); fn(state); }
function save() { localStorage.setItem('app', JSON.stringify(state)); }
function load() { try { Object.assign(state, JSON.parse(localStorage.getItem('app')||'{}')); } catch {} }

load();
subscribe(render);          // render() rebuilds the view from state
```

Render either by rebuilding innerHTML (fine for small prototypes) or by
targeted DOM updates for lists you animate. For view transitions between
screens, wrap navigation in `document.startViewTransition()`.

## States you must design (not just the happy one)

- **Empty** — first-run, no data. This is your onboarding moment; make it
  inviting and instructive, not a blank void.
- **Loading** — skeletons that match the eventual layout, not spinners.
- **Error** — human message + a way forward, never a raw stack trace.
- **Success/feedback** — confirmation of consequential actions.
- **Edge** — long strings, many items, zero items, offline.

## Interaction detail that sells realism

- Buttons depress on `:active`; disabled states look disabled and are
  non-interactive.
- Inputs: focus ring, validation on blur, inline error messages, correct
  keyboard type on mobile.
- Lists: animate insert/remove/reorder (FLIP or View Transitions — see
  animation.md). Swipe actions on touch.
- Navigation: animated transitions that imply hierarchy (push = slide from
  right, modal = rise from bottom, tab switch = crossfade/slide indicator).
- Gestures on mobile mocks: swipe, pull-to-refresh, sheet drag.
- Scroll: momentum feel, sticky headers that condense, reveal-on-scroll.

## Device framing

When it should look like a real phone/desktop, wrap it in a believable device
frame with the correct status bar, safe areas, and keyboard — don't hand-draw a
rough bezel. Match hit-target and type conventions inside it.

## Calling a real model from a prototype

If the prototype needs genuine intelligence (chat, generation, classification),
you can call an LLM from the client via the provided completion bridge
(`window.claude.complete` in supported environments) — use it for the smart bit
and keep the rest deterministic. Design the loading/streaming and error states
for it like any other async action.

## What NOT to do

- Don't build a backend or real auth for a prototype.
- Don't leave dead buttons — either wire them or visibly mark them out of scope.
- Don't ship the happy path only; the empty/error states are where prototypes
  usually fail to convince.
