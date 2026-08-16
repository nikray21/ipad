# The deck engine contract

`assets/deck-engine.html` is the verified SWING-9TO5 build (2026-08-15). It is
one self-contained HTML file, no dependencies, ~19 slides. This documents what
you may change and what you must not break.

## What you edit for a new lesson

1. **`const DEFS = [...]`** — one entry per slide:
   ```js
   {id:'ShortName', kicker:'The odds', head:'≤9 words',
    punch:'≤14 words with <b>accent words</b>.',
    notes:'Long-form for the presenter-notes drawer. Sources named here.',
    headSize:52,            // optional — only when a head wraps badly
    mount:vYourVisual}
   ```
2. **The `v*(vis)` mount functions** — one per slide. Contract:
   - Receives the visual container; builds DOM/SVG once; returns an array of
     updater functions `t => {...}` (slide-local seconds since flip).
   - ALL animation is a pure function of `t` — set styles/attrs from eased
     progress every frame. No CSS transitions/animations, no internal state.
     This is what makes flips replayable and reduced-motion (t=99) work.
3. **`<title>`** and the `console.log` boot line. The progress rail, grid
   overview, and HUD target all derive from `DEFS.length` (patched
   2026-08-15: `buildRailTicks()` runs at boot, `TOTAL_TARGET` is a function)
   — any slide count works with no other edits.

## What you must NOT break

- **Keyboard map** (identical to episode decks): `→`/`Space`/`PageDown` next ·
  `←`/`PageUp` back · `Home`/`End` · `T` theme · `N` notes · `H` HUD+timer ·
  `R` restart timer · `G` grid overview · `F` fullscreen · `c` camera reflow ·
  `⇧C` OBS numbers · `[` `]` column resize · `Esc` close grid.
- **Themes**: dark default, cream via `T`. Tokens live twice — CSS vars on
  `:root[data-theme=…]` AND the JS `TOK` object — keep them in sync. All
  slide paint reads the live `C` pointer; theme toggle remounts the slide.
- **Camera layout**: `colLeft()` = 96 + 36.25% reserved = 792 (his recording
  geometry). Wide SVGs use `width:100%;max-width:<viewBox width>px` so they
  scale when the column narrows — do the same on any new chart wider than
  ~640.
- **Signature chrome** (from deck_template.html, do not restyle): `.kick`
  (accent number + muted small-caps label), `.punch` (5px accent left border,
  40px, `b` = 800/accent), footer mark NIKRAYANI + disclaimer, progress rail,
  ghost numeral, boundary sweep, grain/vignette/glow furniture.
- **Masked headline reveal**: `buildFrame` splits the head into
  overflow-hidden word spans (70ms stagger, easeOutExpo). Heads are plain
  text only — no HTML in `head`.
- **`prefers-reduced-motion`**: engine renders `t=99`/`G=0` — every new
  visual must look correct as a static final frame (check: does anything
  only make sense mid-motion?).

## Motion vocabulary (use these, don't invent new easings)

```
stEnter(el,t,start,dy,dur)   fade + rise            (default entrance)
stRise                       alias of stEnter        (lists: stagger 0.13–0.25s)
stPop(el,t,start)            overshoot scale-in      (tags, stamps, chips)
draw(t,start,dur)            eased 0→1               (SVG stroke draw, bars, fills)
prog(t,start,dur)            raw 0→1
svPop(g,t,start,cx,cy)       SVG group pop about a point
easeOutExpo                  word reveals, dashes
breathe/floatY               ambient only
drawablePath(d,stroke,w)     path with pathLength=1; reveal via setDraw(p, v)
```
Choreography pacing that works: kicker .15 → head words .32+ → visual builds
.6–5s in beats → punch 1.2. A slide should still be unfolding ~2–3s after the
flip, and be fully settled by ~8s.

## Chart recipes already in the engine (steal these)

- **Donut** (slide 5): segment circles with `pathLength=1`,
  `stroke-dasharray "frac 1-frac"`, `stroke-dashoffset -start`, rotate −90;
  0.012 dash gap between segments; sequential sweep; center total.
- **Survival staircase** (slide 14): computed `vals` array → staircase path
  string (`H`/`V` steps) + area fill close; dots appear as the line passes;
  labels on first/last point only; caption under.
- **Level lines + band** (slide 9): dashed lines drawing width, right-anchored
  labels INSIDE the viewBox (x=LX2+52, anchor end — they clip otherwise).
- **Zone chart** (slide 8): volume bars grow from baseline, band grows height,
  dashed SMA (real dash `.018 .012` + dashoffset reveal — a plain drawable
  dasharray makes it render solid), jolt = translateX sine burst on the group.
- **Count-up stat** (slide 2): `v = round(from + (to-from)*easeOutCubic(p))`,
  108px, tabular-nums.

## Layout geometry (1920×1080 stage)

- Content column: `left: colLeft()` (792 cam / 96 full), `right: 96`,
  `top: 116`, `bottom: 132` (the punch needs that air above the rail).
- Ghost numeral `top:300, right:72`; rail `bottom:82`; footer `bottom:44`.
- Visual block is flex-centered with a 5px ambient bob.

## Verification checklist (all must pass before handing over)

- [ ] Every slide stepped in dark AND cream AND camera-on AND full-bleed.
- [ ] No SVG text clipped at any edge; no label collisions at narrow column.
- [ ] Punches ≤14 words, heads ≤9 (count rendered textContent, dashes count).
- [ ] Derived figures computed, not typed; sourced figures named in notes.
- [ ] Notes drawer (`N`) reads as a real script for every slide.
- [ ] Rail tick count / `TOTAL_TARGET` match the slide count.
- [ ] Console clean except the boot line (favicon 404 is fine).
