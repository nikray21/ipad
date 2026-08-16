---
name: learn-stock
description: >-
  Build Nikil's Wednesday educational episode deck — a "learn" format that
  teaches a trading/investing concept, sibling of stock-analysis-presentation
  (the Sunday stock episode). Use when he says "/learn-stock", "Wednesday
  video", "educational episode", "teach X", "lesson deck on X", "learn deck",
  or asks for a deck that explains a concept (options basics, shorting, risk
  sizing) rather than analyzes a ticker.
argument-hint: [topic — e.g. "how shorting works" or "options basics"]
---

# Learn-Stock — the Wednesday educational deck

You build the educational half of Nikil's channel: Sunday is
`/stock-analysis-presentation` (a ticker, filings, findings); **Wednesday is
this** — one concept taught to beginner/intermediate viewers, in the same
signature design language, recorded the same way (camera beside the deck).

The canonical, verified reference build is **SWING-9TO5**
(`~/Desktop/educational/SWING-9TO5 2026-08-12/SWING-9TO5-deck.html`). A
snapshot of that exact file ships with this skill as the starting template:

```
cp .claude/skills/learn-stock/assets/deck-engine.html "<workdir>/<TOPIC>-deck.html"   # path from repo root
```

**Never rebuild the engine from scratch.** Copy it, then replace two things:
the `DEFS` array (copy) and the per-slide `v*()` visual mount functions.
Everything else — tokens, motion system, chrome, shortcuts, themes, camera
reflow, reduced-motion — is already correct and verified. Read
`.claude/skills/learn-stock/format.md` (this skill's folder) before editing;
it is the engine contract.

## Workflow

1. **Outline the lesson.** 8–19 slides, one idea per slide, arc:
   hook → why it matters → the core mechanism → the system/steps → worked
   example → mistakes/guardrails → discipline → recap + next-video hook.
   Cut any slide that doesn't advance the arc.
2. **Write the copy first** (executive style, hard budgets below), as the new
   `DEFS` array: `{id, kicker, head, punch, notes, mount}`.
3. **Design one visual per slide.** Every slide gets a real visual — a chart,
   a diagram that moves, or a number set huge. Word-slides are the failure
   mode. **31 proven patterns are cataloged in
   `.claude/skills/learn-stock/visuals.md`** — 19 from the engine
   plus 12 in `assets/visual-library.html` (gauge, probability tree,
   compounding curve, order book, underwater chart, slope, trajectory,
   lollipop, waterfall bridge, month grid, radar, callout anatomy). Pick from
   the catalog first; invent new ones with the installed `design-craft` skill
   when nothing fits. Nikil's browsable menu of the 12 new patterns lives at
   `~/Desktop/educational/VISUAL-LIBRARY.html`.
4. **Build each `v*()` mount function** as a pure function of slide-local `t`
   (the engine's model — no CSS animations, no rAF state).
5. **Verify in the browser.** Chrome blocks `file://`:
   `cd "<workdir>" && python3 -m http.server 4851 --bind 127.0.0.1`
   then step EVERY slide, in dark AND cream (`T`), camera on AND off (`c`).
   Screenshot the complex slides and actually look at them — label
   collisions, clipped SVG text, and bars that outgrow a narrowed column are
   the recurring bugs.
6. **Deliver** to `~/Desktop/educational/<TOPIC> <YYYY-MM-DD>/` locally — the
   deck HTML plus a `TALKING-POINTS.md` (per-slide: head, punch, the notes
   long-form, target seconds). **In a cloud session deliver to
   `output/educational/<TOPIC> <YYYY-MM-DD>/`, commit it, and publish the deck
   HTML as an artifact** (no localhost in cloud — the artifact URL is also how
   Nikil opens it on the iPad; step 5's local http.server applies only on the
   Mac).

## Copy rules (the guardrails — same as the Sunday deck)

1. **Head ≤ 9 words. Punch ≤ 14 words. ~21 words on screen per slide.**
   The speaker carries the words; the slide carries the image.
2. **Punch format is fixed**: rendered by the engine's `.punch` (5px accent
   stripe, 40px, `<b>` words turn accent). Wrap the 2–3 carrying words in
   `<b>`. Written for a beginner — no "multiple", "underwriting", "pretax",
   "expectancy" without teaching it first.
3. **Everything cut goes into `notes`** — the long-form explanation lands in
   the presenter-notes drawer (`N`), never on screen. Notes are half the
   deck; write them properly.
4. **Never type a derived figure.** Anything computable is computed once as a
   const and interpolated everywhere it appears (chart, punch, notes) — e.g.
   SWING-9TO5's `SURV = 100 * 0.98**5` feeds slide 14's chart AND its punch,
   so the number cannot drift. Sourced stats (a study's 97%) are deliberate
   literals — name the source in `notes`.
5. **Verify every factual claim** (studies, rule changes, dates) with a live
   search before it ships — never recall. Date-sensitive claims state dates.
6. Every slide carries the footer "NIKRAYANI · Educational — not financial
   advice" (the engine does this — don't remove it).

## Visual rules

7. **No visual form carries more than ~a third of the deck.** The engine has
   working patterns for: line/wave + riding dot, tag pops (BUY/SELL), day
   timeline + playhead, tiles, numbered step rows + donut, spotlight
   checklist, verdict panels, zone/price chart with jolt, level lines + ATR
   band, risk/reward bars, pill flows, staircase step-area, week strip,
   table, formula cards, count-up stats, chip relay + cursor click. Reuse and
   recombine before inventing.
8. **Color carries meaning**: good = green, danger/loss = red, caution = amber,
   info/neutral series = blue (`s2`), accent = chrome and emphasis only.
9. **Numbers as graphics**: a key stat renders ≥100px and becomes the visual.
10. Selective labels on charts — first and last point, never every point.
11. Keep his loved SWING-9TO5 visuals as the taste reference; don't flatten
    the motion (draw-ins, pops, spotlights, the boundary sweep).

## Recording contract (why the layout is what it is)

- Camera mode is the DEFAULT: content column right of 792px, transparent-feel
  gutter left where his camera sits. `c` reflows full-bleed, `[`/`]` resize,
  `⇧C` prints OBS numbers. 15s target per slide; HUD (`H`) times the run.
- Shortcuts must keep working after your edits: → Space ← Home End T N H G F
  R C ⇧C [ ] Esc. If you touch the engine beyond DEFS+visuals, re-test all.

Use the argument text as the lesson topic. If no topic is given, ask for one
— don't guess the lesson. If the topic needs source data (a study, a rule, a
price history), gather and verify it before writing slide one.
