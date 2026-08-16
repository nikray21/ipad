---
name: design
description: The visual vocabulary for Nikil's episode decks and the Terminal — the seventeen chart forms available, which metric each one is for, the validated palette, and the layout system. Use before adding or changing any chart, slide layout or colour in a deck or on the dashboard, and when a deck is leaning on one chart type too heavily.
argument-hint: [what you're visualising]
---

# Deck & Dashboard Design

Every chart is read by a beginner on a phone-sized YouTube frame, once, at
speaking pace. That single constraint drives everything here: **one idea per
visual, the shape carries the argument, and no chart form appears so often that
the audience stops looking at it.**

Implementations live in `deck_template.html` at the repo root (locally
`~/Projects/episode-deck/deck_template.html`)
(one function per form, registered in `CHARTS`). The `stock-analysis-presentation`
skill governs the decks themselves; this file governs how they look. Its
`references/new-ticker-runbook.md` carries the browser audit that checks every
chart actually rendered, animated and fits.

**Four enforced rules** (`audit_deck.py`):
- No single form may carry more than a third of a deck (`slide-variety`).
- No chart spec may contain a `null` where a function is expected; formatters are
  named strings (`fmtKind`), never callables across the payload boundary.
- **No HTML entity in any chart spec** (`chart-entities`). Chart labels are written
  with `textContent`, so `&times;` renders as the literal seven characters — and the
  extra width pushed a value label into the next column. Entities are for prose
  fields (`head`, `sub`, `why`) only; chart labels take the glyph.
- **No typed figure in any deck module** (`no-hardcoded-figures`, now scanning
  `decks/*.py` string literals as well as the template). A hand-written "44%
  drawdown" shipped on three slides and was wrong; so was a "15% of the company"
  that recomputes to 16%. Docstrings are exempt; definitional label text must be
  declared in a module-level `LITERALS_OK` tuple, so each exception is a decision.

Before writing any chart, load the bundled **`dataviz`** skill and run
`scripts/validate_palette.js` on any new colour pair. Never eyeball it.

## Pick the form from the job, not from habit

| The job | Form | Used for |
|---|---|---|
| Reported history continuing into forecast/guided periods | `forecast` | revenue still climbing while the growth rate rolls over |
| One number that needs a threshold to mean anything | `gauge` | Rule of 40 at 155 against the bar of 40 |
| A flow from one total to another, with leaks | `sankey` | revenue → costs → operating income → tax → net income |
| Contribution to a change, step by step | `bridge` | which segment produced the quarter's profit jump |
| Then vs now for a few series | `dumbbell` | US revenue vs rest-of-world, a year apart |
| The same forecast re-issued over time | `slope` | a full-year guide raised in Feb, May, August |
| Where one company sits in a population | `distribution` | 49× revenue when software trades at 10–15× |
| Two measures of different scale | `smallmult` | $10B of debt beside ±$0.8B of equity |
| Two measures, same direction, different units | `indexed` | share price vs trailing EPS, both from 100 |
| Position on a range with reference points | `track` | price against the low / mean / high analyst target |
| A range with an implied value inside it | `range` | guided full-year EPS vs the implied second half |
| A whole company as one shape | `radar` + pips | the six-dimension verdict |
| Composition of a single unit | `stackedh` | one dialysis treatment: cost block + margin block |
| Discrete values across a short ordered series | `bars` | eight quarters of revenue growth |
| A signed change where the sign is the point | `bars` + `zeroLine` | one payor grew, the other shrank |
| Level plus annotated events over time | `line` + markers | the tape, with the low, high and reaction day |
| Ranked magnitudes | `hbars` | per-treatment economics by payor |
| A multiple that only means something beside its growth | `peers` | 71.8x P/S at +79% against a peer average of 13.7x at +24% |
| How little of a price is earnings | `donut` | $6.16B revenue and $3.02B profit drawn inside a $441B market cap |
| A whole balance sheet at a glance | `treemap` | every block green because there is no debt block |
| Where the price sits on an under/fair/over ruler | `fvband` | $172.01 against a $104.30 fair value |
| Buying against selling, by recency | `insider` | $1.01B sold, zero bought, four quarterly buckets |
| Two grouped series per category | `grouped` | rarely — prefer `dumbbell` or a change chart |

Slide types that are not charts: `title` `mega` `tiles` `quote` `findings`
`snapshot` `twocol` `verdict` `reasons`.

## The traps each form was built to avoid

- **A shared axis hides the point.** Two bars differing 0.7% differ by two pixels.
  If the *change* is the story, plot the change (`bars` + `zeroLine`), not the level.
- **The chart must argue the caption's claim.** A revenue chart under a margin
  claim showed a 2.8× gap while the words said 10×. Stack the shared cost out
  (`stackedh`) so the gap you assert is the gap they see.
- **Never a dual y-axis.** Index both to 100 (`indexed`) or split into panels
  (`smallmult`).
- **A negative bar needs its own gutter** — its value label hangs below and will
  land on the category label otherwise.
- **A segment too thin to hold a label still needs the label.** Float it outside;
  the small number is often the whole point (a 1.4% tax ribbon).

## Colour means something — it is not decoration

| The thing | Colour | Example |
|---|---|---|
| Good for the shareholder | `--good` green | assets, equity, a score of 4–5 |
| Bad for the shareholder | `--crit` red / `--warn` orange | liabilities, insider selling, a score of 1 |
| Neither — just a fact | `--s1` / `--s2` / `--muted` | revenue vs earnings, US vs rest of world |

A number that is merely *large* is not "bad". Reserve red and orange for things a
viewer should actually worry about, and everything else takes a series colour.

## Number magnitudes — one rule, whole deck

`decks/fmt.py` picks the unit; nothing formats money by hand. **$1.8B · $730M ·
$208K** — never `$0.45B`, never `$1,800M`. One decimal, dropped once the mantissa
already carries three significant figures ($442B, not $441.8B). `fmt.usd()` takes
millions, `fmt.num()` takes a bare count, `fmt.dollars()` is a share price.

## Animation

Three jobs, nine keyframes, and every slide gets one — text slides that appeared
fully formed beside charts that built themselves read as a bug.

| Keyframe | For |
|---|---|
| `grow` | vertical bars, growing off a baseline |
| `growX` | **horizontal** bars. `grow` is `scaleY`; using it on an hbar squashes it vertically instead of extending it sideways — this shipped on four charts |
| `draw` / `sweep` | a line or an arc drawing itself along its own length |
| `fade` | labels and annotations, staggered behind the mark they belong to |
| `pop` / `bloom` | a hero number, and the radar blooming out of its centre |
| `pipin` / `rowin` | score pips tallying up, list rows arriving |
| `maskrise` | slide chrome: the headline wipes up out of a mask; the punch reuses it and lands LAST (~1.15s) so the conclusion is a beat, not furniture |

Beyond keyframes (added 2026-08-15, all automatic or one helper call):
- **Count-up numerals** — `.tile .tv`, `.mega .v` and `.find .fstat` tally from
  zero on slide entry; the final frame always writes the exact built string, so
  the resting deck is byte-identical to what was audited.
- **`areaFill(s, color, top)`** — gradient fade under a line instead of a flat
  translucent block (line / forecast / steparea already use it).
- **`halo(s, cx, cy, r, color, delay)`** — radial emphasis glow behind THE hero
  mark only (scatter / forecast / steparea endpoints already do). A glow on
  every mark is noise; stacked rings read as a fat dot — it must be a gradient.
- **Hero scale**: `"hero": True` on one tile (82px) and the `bridge` total at
  44px accent — the biggest number on a slide must be the one that matters.
- **Findings cards** take a per-finding `stat` — the card leads with the number.
- `scatter` now spans [min, max] with a zero line — safe for loss-era margins.

**Audit them in the browser, not by eye.** Add `.on` to each slide in turn and read
`getComputedStyle().animationName` — every animated element must resolve to one of
the nine known keyframes, with `fill: both` and a non-zero duration. Text slides that
appeared fully formed beside charts that built themselves is what this catches.

Everything is `both` fill and finishes inside ~1.6s — well under any slide's target
duration. Audit them in the browser by adding `.on` to each slide in turn and
reading `getComputedStyle().animationName`; the `.slide.on` gate means an inactive
slide reports no animation at all.

## Filming the deck

Measured across a finished 24-slide deck, **82% of the 1920×1080 canvas carries
content on some slide**, and the only always-free region is a 1080×80 strip at the
bottom. A webcam bubble laid over a full-bleed deck *will* cover a chart. Use
`?cam=left|right|bottom` (with optional `&camw=34`), which shrinks and re-anchors
the stage to reserve a real zone instead.

## Palette

Chart marks use `--s1` / `--s2`, which are **not** the UI accent. Both pairs pass
every check in `dataviz/scripts/validate_palette.js`:

| | series 1 | series 2 | surface |
|---|---|---|---|
| cream | `#c2603f` | `#2a78d6` | `#ffffff` |
| dark | `#d67350` | `#4d90da` | `#1b1a19` |

`--accent` (`#c2603f` / `#d97757`) is for chrome and text only. The Terminal's old
`--cool` steel blue failed the chroma floor in both modes — it read grey next to
the terracotta. Status colours (`--good` `--warn` `--crit`) are reserved and never
used as "series 3".

Sankey ribbons: trunk `--s1` at 78%, costs `--muted`, income joining `--s2`, tax
`--crit`. Grey for what leaves, blue for what joins, red for what the taxman takes.

## Layout

Fixed **1920×1080** stage scaled to the window, so it frames identically in OBS at
any window size. Every slide: kicker + source chip, one head, optional sub, the
visual, and a **"why it matters"** band in plain English. Presenter notes hidden
behind `N`. Cream and dark from one file, `T` toggles.

Type scale: head 64px (52 when long), sub 25px, why-band 22px, chart value labels
20–31px, axis 16–17px. Nothing on a slide is below 15px — it has to survive
compression on a phone.

**The full catalogue of forms worth stealing — 23 screens, with the data each
needs and whether we have it — is in `references/visual-catalogue.md`.** Read it
before deciding a deck needs a new chart; the answer is often already there.

## What we learned from Simply Wall St

Studied 2026-08-07 across **all seven pages** of their PLTR report — overview,
valuation, future, past, health, dividend, ownership. These are standard
visualisation forms, not their assets or styling; we implemented our own.

**Honesty about coverage.** Their site fought the browser automation badly: the
capture viewport clipped to a ~470px slice, charts lazy-load only when scrolled
into view, and a bulk-scroll loop froze the renderer once. So the table below
marks what I **saw rendered** against what I **inferred** from section headings,
DOM structure and page text. Anything marked *inferred* should be looked at
properly before it is copied.

| Their pattern | Seen? | Status |
|---|---|---|
| **Past → Forecast continuation** — two series over 2024–28 with a vertical divider labelled "Past \| Analysts Forecasts", the reported region shaded, dots at the boundary, series-toggle chips below | **rendered** | **Adopted** as `forecast`. The best thing on their site. Levels reassure while the gradient indicts, and both are visible at once. |
| **Snowflake** — 5-axis radar with *curved organic lobes* rather than straight polygon edges | **rendered** | **Adopted.** Our `radar` closes the shape with midpoint beziers. |
| **Peer comparison bars with an average reference line** | rendered (partial) | Partly — `hbars` covers it; add a reference line when needed. |
| **Metric vs industry distribution** — histogram of industry P/E buckets with a "you are here" marker | inferred (read the bucket labels in text) | **Built** as `distribution`, **not yet used** — using it would mean inventing the industry buckets, and fabricating data to fill a nice chart is exactly what rule 1 forbids. Waiting on sourced peer data. |
| **Share price vs fair value** — paired bar with the % over/under called out | inferred | Covered by `track` and the verdict calculator. |
| **Insider trading volume** — buy/sell bars over time | inferred (ownership page) | Candidate. Would need Form 4 data we do not currently pull. |
| **Ownership breakdown** — composition by holder type | inferred (ownership page) | Candidate. A donut or `stackedh` would do it. |
| **Financial position** — short/long-term assets vs liabilities | inferred (health page) | `smallmult` or `stackedh` covers it. |
| **Debt to equity history** | inferred (health page) | `smallmult` already does this better for a company whose equity goes negative. |
| **Earnings & revenue history** — revenue/earnings/G&A/R&D over time | inferred (past page) | Superseded by `sankey` for a single period. |
| **Volatility scale** — company vs industry vs market vs the 10% most/least volatile bands | rendered (text) | Not adopted. A market-structure point, not a fundamentals one. |
| **Criteria checks "6/6"** chips per section | rendered (text) | Our `snapshot` pips do the same job with the fact attached. |

Nothing new on their **dividend** page (PLTR pays none — 0/6 checks) or
**management** page (insider-sale news, no charts).

Their income statement is presented as a **list** — revenue → cost of revenue →
gross profit → other expenses → earnings. That structure *is* a flow, and a flow
wants a Sankey. That gap is where our version is genuinely better than theirs.

| Their pattern | Status |
|---|---|
| **Snowflake** — 5-axis radar with *curved organic lobes* rather than straight polygon edges | **Adopted.** Our `radar` now closes the shape with midpoint beziers. A lopsided score reads instantly as a blob with a dent. |
| **Metric vs industry distribution** — histogram of the whole industry's P/E buckets with a "you are here" marker | **Adopted** as `distribution`. The honest way to say "expensive" is to show where everyone else trades, and point. |
| **Peer comparison bars with an average reference line** | Partly — `hbars` covers it; add a reference line when needed. |
| **Share price vs fair value** — paired bar with the % over/under called out | Covered by `track` and the verdict calculator. |
| **Community fair-value distribution** across price buckets with the last price marked | `distribution` can do this if the crowd view is ever wanted. |
| **Volatility scale** — company vs industry vs market vs the 10% most/least volatile bands | Not adopted. Interesting, but it is a market-structure point, not a fundamentals one. |
| **Criteria checks "6/6"** chips per section | Our `snapshot` pips do the same job with the fact attached. |
| **Layered revenue / expense / earnings history** | Superseded by `sankey`, which decomposes one period far more clearly. |

Their income statement is presented as a **list** — revenue → cost of revenue →
gross profit → other expenses → earnings. That structure *is* a flow, and a flow
wants a Sankey. That gap is where our version is genuinely better than theirs.

## Cross-validation is a design feature

Their report independently confirmed our figures: TTM revenue $6.16B, TTM earnings
$3.02B, gross margin 84.8%, short-term assets $11.1B against $1.5B of liabilities,
52-week range $106.37–$207.52, debt/equity 0%, and a DCF fair value of $171.78
against our base case of roughly break-even at $170.

Two disagreements, both basis differences rather than errors — worth remembering:

- **EPS.** They print $1.26 TTM (net income ÷ current shares outstanding); we print
  $1.17 (the sum of four *reported diluted* quarters). Ours is the more
  conservative basis. State the basis on the slide.
- **Reaction size.** Their AI-written earnings summary says the stock "rose
  approximately 14%" after the Aug 3 release. The tape says **+29.45%**, and their
  own 7-day figure of +27.5% corroborates ours, not their summary. Compute
  reactions from daily bars; never take a narrative summary's number.
