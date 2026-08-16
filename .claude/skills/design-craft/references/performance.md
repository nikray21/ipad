# Performance — make it feel instant

Perceived performance is part of the design. Jank, layout shift, and slow paints
read as "cheap" even when the visuals are great.

## Rendering & animation

- Animate **only `transform` and `opacity`** in anything that runs per-frame.
  Layout properties (`width`, `height`, `top`, `margin`, `box-shadow`,
  `background-position`) trigger layout/paint and jank.
- Promote animating elements with `will-change:transform` *just before* they
  animate; remove it after. Don't leave it on everything (costs memory).
- Batch DOM reads then writes — never read `offsetWidth` in a loop that also
  writes styles (layout thrashing). Use `requestAnimationFrame` to schedule
  writes.
- Prefer `IntersectionObserver` and `animation-timeline` over scroll listeners.
  If you must listen to scroll/resize, throttle with rAF.
- Beyond a few dozen animating DOM nodes → `<canvas>`/WebGL.
- `content-visibility:auto` + `contain-intrinsic-size` to skip rendering
  offscreen sections of long pages.

## Loading & layout stability (CLS)

- Reserve space for media: always set `width`/`height` or `aspect-ratio` on
  images/embeds so content doesn't jump when they load.
- `loading="lazy"` and `decoding="async"` on below-the-fold images.
- Use skeletons that match final layout so the shell doesn't shift when data
  arrives.
- Preload the hero image and critical fonts; `<link rel="preconnect">` to font/
  asset origins.

## Fonts

- `font-display:swap` (or `optional` for body) to avoid invisible text.
- Subset fonts to the characters/weights you actually use. Self-host or
  `preload` the critical weight. Don't load 8 weights you don't use.
- Variable font = one file for many weights (often a net win).

## Images

- Right format: AVIF/WebP for photos, SVG for vector, PNG only for
  transparency-on-flat. Serve responsive sizes (`srcset`/`sizes`).
- Compress. A 3MB hero is a design failure. Target < 200KB for most heroes.
- `object-fit:cover` + a defined box beats loading oversized images.

## JS discipline

- Ship less. For a prototype, a few KB of vanilla JS beats a framework bundle.
- Defer non-critical scripts (`defer`/`type=module`); lazy-`import()` heavy libs
  (three.js, chart libs) only when the section is reached.
- Avoid re-rendering the whole DOM on every state change for large lists — do
  targeted updates or keyed diffing.

## Budget & check

- Rough budgets: hero image < 200KB, total JS < 150KB for a marketing page,
  first paint < 1s on a fast connection.
- Test at 6× CPU throttle and "Slow 4G" in devtools. Watch the Performance
  panel for long tasks and layout-shift markers.
- Lighthouse for a number, but trust the filmstrip and your eyes for "feel."
