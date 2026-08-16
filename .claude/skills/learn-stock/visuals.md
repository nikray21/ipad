# The visual library — every proven pattern, and how to make new ones

Two sources of working, verified code:

1. **`assets/deck-engine.html`** — the SWING-9TO5 build (19 slides).
2. **`assets/visual-library.html`** — 12 additional patterns built 2026-08-15,
   verified slide-by-slide in the browser. The live menu copy Nikil browses is
   `~/Desktop/educational/VISUAL-LIBRARY.html` — keep both in sync if either
   gets improved.

Steal the mount function, keep its animation formulas, swap the data.

## Patterns in the engine (SWING-9TO5, by slide)

| # | Pattern | Teaches / use for |
|---|---------|-------------------|
| 1 | Price wave + riding dot + BUY/SELL tag pops + dashed arc | any "one move" story |
| 1 | Horizon boxes (option row, one active) | picking between 3 approaches |
| 2 | Count-up stat cards (108px) + stamp + strike-through | big sourced numbers, rule changes |
| 3 | Day timeline + sweeping playhead + pulsing window | time-of-day arguments |
| 4 | Big-label tiles ("1 chart / 1 broker / 15 min") | "all you need" lists |
| 5 | Numbered step rows + donut (segments sweep in) | routines, time budgets |
| 6 | 2-col checklist + walking spotlight + ✓ pops | systems with N checks |
| 7 | Verdict panels (two mini-charts + TRADE/NO stamps) | this-not-that decisions |
| 8 | Zone chart: volume bars, band, dashed SMA, wick jolt, entry candle, breakout | full setup anatomy |
| 9 | Level lines + ATR band + live noise dot + rookie callout | stop placement |
| 10 | Risk/reward bars on level lines (1R vs 2R) | asymmetry |
| 11 | Order pill splits into stop/target boxes (OCO) | order mechanics |
| 12 | Account-at-risk bar (2% vs 98%) + formula cards | sizing math |
| 13 | Mini trend chart + relay of ✓ pills | recapping a system |
| 14 | Stat tiles + survival staircase (computed 0.98^n) + NEVER shudder | guardrails |
| 15 | ✕ mistake cards, 2-col | anti-patterns |
| 16 | Month heat grid (upgraded from week strip 2026-08-15) | patience, sparsity |
| 17 | Journal table (colored results) | logging habits |
| 18 | Probability tree w/ computed EV (upgraded from bars 2026-08-15) | why edges work |
| 19 | Chip relay + word-by-word line + cursor clicks Subscribe | recap + CTA |

## Patterns in the visual library (12 more)

| # | Pattern | Teaches / use for |
|---|---------|-------------------|
| 1 | **Callout anatomy** — one oversized object, labels land in reading order | what a thing IS (candle, ticket, pattern) |
| 2 | **Gauge** — zones draw, needle overshoots and settles, readout under hub | keep-this-number-in-a-range rules |
| 3 | **Probability tree** — branch curves draw, nodes pop, computed EV chip | expected value, outcome math |
| 4 | **Compounding curve** — two paths same money, computed end labels | compounding, fee drag, recovery math |
| 5 | **Order book** — asks above, bids below, spread band highlighted | microstructure, spread, liquidity |
| 6 | **Underwater chart** — equity line + mirrored drawdown, computed worst | drawdowns, risk honesty |
| 7 | **Slope chart** — before/after dots per metric, values beside dots | with-system vs without |
| 8 | **Connected trajectory** — dots pop along a drawing path, arrowhead, endpoint labels only | two measures over time |
| 9 | **Lollipop ranking** — stems grow, dots ride the tip, value at dot | ranked contributions |
| 10 | **Waterfall bridge** — start bar, decrement steps, computed NET | gross→net walks |
| 11 | **Month heat strip** — 20-day grid, computed tally line | cadence, discipline |
| 12 | **Radar score** — rings, spokes, polygon draws, computed total | multi-axis self-assessment |

## Rules when adapting or inventing

- Keep the engine's motion vocabulary (`draw`/`stPop`/`stRise`/`svPop`,
  `drawablePath` + `setDraw`) — never CSS animations.
- **Computed, not typed**: any figure derivable from the pattern's data array
  is computed in the mount (EV chip, NET bar, worst drawdown, tallies) so a
  data change updates every label. Numbers that are pure pattern placeholders
  are marked `// illustrative` — a real lesson replaces them.
- Selective labels: endpoints and the one point that matters, never all.
- Color meaning: good=green, loss=red, caution=amber, neutral series=`s2`,
  accent=emphasis/chrome. Ranked same-measure series = one hue.
- Wide SVGs: `width:100%;max-width:<viewBox w>px` so camera-column resize works.
- Every visual must read correctly as a static final frame (reduced-motion
  renders t=99).

## Spinning up NEW designs

The **design-craft skill** is installed at `~/.claude/skills/design-craft/`
(from Nikil's Claude Design package) — its `references/animation.md`,
`dataviz.md`, `svg.md`, and `gradients-color-effects.md` are the taste source
when a lesson needs a visual none of the 31 patterns covers. Process:
sketch the mechanism the slide must show → pick the nearest pattern → adapt;
only invent from scratch when nothing fits, and verify it in the browser the
same way (both themes, camera on/off, screenshots you actually look at).
New proven patterns get added to `assets/visual-library.html` AND the Desktop
copy AND this table.
