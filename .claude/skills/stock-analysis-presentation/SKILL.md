---
name: stock-analysis-presentation
description: Build the flip-through FA presentation deck Nikil records his YouTube videos from — pull the SEC filings, find the story nobody else found, generate a 1920×1080 slide deck in the Terminal's design language with presenter notes, then prove every number traces to a filing. Use when he names a ticker and wants a deck, a presentation, an episode, or "run the deck for X" / "do NVDA next" / "make me the slides for TSLA".
argument-hint: [TICKER]
---

# Stock Analysis Presentation

Nikil's YouTube format: **the deck carries the fundamental analysis, then he cuts
to Webull for the technicals.** He presents *to* the audience — mostly beginner and
intermediate investors — so every slide carries one idea, one visual, and a plain-
English reason it matters.

The angle that makes the channel different is **the thing nobody else found.** Not
a recap of the press release — the footnote, the segment bridge, the guidance
midpoint, the tax line. That work is Phase 1 and it is most of the value.

- **Code:** the repo root (locally `~/Projects/episode-deck/`; in a cloud session,
  the clone root — run everything from there) — `build_deck.py` (generic
  engine), `marketdata.py` (the data layer, no server), `decks/<SYM>.py` (per-company
  derivation + narrative), `decks/fmt.py` (number formatting), `episodes/<SYM>.json`
  (filing-read facts), `deck_template.html`, `audit_deck.py`, `validate_facts.py`, `crosscheck.py` (independent vendor check),
  `deckpath.py` (finds a built episode wherever it was filed)
- **Output:** `$DECK_OUT/<TICKER> <YYYY-MM-DD>/` — deck HTML, `SCRIPT.md`,
  `SOURCES.md`, `data/<SYM>-<DATE>.json`, and `Notes/` (talking-point bullets
  per slide, via `export_notes.py`). Locally `DECK_OUT` is unset and this
  defaults to `~/Desktop/…`; in a cloud session `export DECK_OUT=output` and
  **commit the output folder** — the repo is the only persistence between sessions.
  `deckpath.py` *finds* a built episode afterwards even if it has been
  filed into a subfolder, so tidying the Desktop never breaks its audit trail.
- **Sibling skills:** `design` (**load before touching any chart**) · `fa` · `bull`.
  The `terminal` skill is no longer a dependency — the data traps that mattered are
  carried in `marketdata.py`'s comments — but it is still worth reading if you touch
  the data layer, and **`bull` is required reading before anything near 8787.**

## This skill is standalone — no server, no Terminal

`marketdata.py` owns the data layer. Nothing in the pipeline talks to
`127.0.0.1` at all. Upstreams are public and key-free:

| Route | Upstream |
|---|---|
| `fundamentals`, `filings` | SEC XBRL `companyfacts` + `submissions` |
| `history`, `quote` | Yahoo chart API (Nasdaq for the live quote) |
| `profile`, `street`, `estimates` | Nasdaq api |

**Its builders are lifted verbatim from the Terminal's `server.py`,** deliberately:
each one encodes a data trap found the hard way — deriving a quarter from cumulative
XBRL figures, the order to try revenue tags in, split normalisation, the freshness
ceilings. Reimplementing them would have meant rediscovering all of it.

Proven two ways, and re-prove both after touching `marketdata.py`:

1. **Same numbers** — `fundamentals`, `estimates`, `filings`, `profile` and `street`
   matched the old HTTP route byte for byte on PLTR, SPCX and DVA, every close agreeing.
2. **Genuinely independent** — the whole loop, both `--prove` suites included, runs with
   every localhost connection forcibly refused:

```python
# /tmp/no_localhost.py — raises if anything reaches 127.0.0.1
_real = urllib.request.urlopen
def guard(req, *a, **kw):
    url = req if isinstance(req, str) else req.full_url
    if "127.0.0.1" in url or "localhost" in url:
        raise AssertionError(f"BLOCKED: pipeline tried to reach {url}")
    return _real(req, *a, **kw)
urllib.request.urlopen = guard
```

`TERMINAL_API` still switches back to HTTP, which is only useful for comparing the
two implementations.

**Caches** live beside the code: `.cache_market/` (payloads, same TTL contract as the
old server), `.cache_filings/` (SEC documents), `.cache_form4/` (insider XML the audit
recomputes from). All gitignored.

## References — read the one you need

| File | When |
|---|---|
| `references/new-ticker-runbook.md` | **Start here for a new ticker.** The whole job, in order. |
| `references/episode-contract.md` | Before writing `episodes/<SYM>.json` |
| `references/plain-english.md` | Before writing any "why it matters" band |
| `references/recording-setup.md` | When he asks how to film it |

## What a new ticker needs

Two files, and **never an edit to `build_deck.py`**:

1. **`episodes/<SYM>.json`** — every figure, each naming the filing it came from.
2. **`decks/<SYM>.py`** — `derive(snap, ep, fund, qrows, die, fact)` returning the
   company-specific metrics, and `slides(snap, ep, fact, fund_quarters=None)`
   returning the slide list. `die()` on anything that does not reconcile.

`build_deck.py` stays generic: it fetches, builds the tape, the peak-to-trough, the
earnings-reaction history, the indexed price-vs-earnings series, forward multiples,
the street block and provenance, resolves episode prose tokens, then dispatches.

An earlier version of this skill claimed a new ticker needed no new code at all —
that was wrong. The *facts* are data; the **narrative is bespoke**, and pretending
otherwise produces a template, which is the opposite of the point.

Company-shaped audit checks (a payor split, an EPS-guidance range, an insider
block) `SKIP` with an `n/a` line when a company has no such figure — never silently
pass.

## The loop

```bash
cd "$(git rev-parse --show-toplevel)"   # repo root
python3 build_deck.py <SYM>          # refuses on stale data
python3 audit_deck.py <SYM>          # must print ALL DECK INVARIANTS PASS
python3 validate_facts.py <SYM>      # must print ALL EPISODE FACTS TRACE
python3 audit_deck.py <SYM> --prove  # must go red
python3 validate_facts.py <SYM> --prove
python3 export_notes.py <SYM>       # talking-point bullets -> Notes/
```

**A check that cannot fail is worthless.** Run `--prove` after adding any check.
This is not ceremony: the episode-prose check was written to catch `"49x guided
revenue"` and its first version matched only `%` and `$`, so it would have missed
the exact bug it existed for. `--prove` is what exposed that.

Then look at it. Locally, the Chrome extension blocks `file://`, so serve it:

```bash
cd "$(python3 -c 'import deckpath,sys; print(deckpath.read_dir(sys.argv[1], sys.argv[2]))' <SYM> <DATE>)" \
  && python3 -m http.server 4849 --bind 127.0.0.1 &
# open with ?audit=1 — the layout audit lives IN the deck and runs on load
# http://127.0.0.1:4849/<SYM>-<DATE>.html?theme=cream&audit=1&cb=$(date +%s)
```

In a cloud session there is no localhost to open — **publish the deck HTML as an
artifact** and open the private URL (this is also how Nikil views/records it on
the iPad). Append `?theme=cream&audit=1` there too.

**The layout audit is part of the deck, not a console paste.** Open with
`?audit=1` and read one line:

```
[deck] AUDIT CLEAN — 22 slides, no layout, animation or text faults
[deck] AUDIT — 3 issue(s):
  10 bridge: chart draws 2510px below its box
  10 bridge: chart overlaps the why band by 2198px
  18 range: DEAD CHART
```

It checks, per slide, in both themes: dead charts · SVG **content** measured
against **all four edges** of its own viewBox · overlap with the why band · text
running into text · **text struck through by a prominent rule** · **any rendered
"undefined"/"NaN"** · unknown or badly-filled animations · sub-15px on-camera text
· a stage translated off-centre without `?cam=`. `window.deckAudit()` returns the
same array on demand.

Three of those arms were added after the audit passed a deck that was visibly
broken, and each is worth remembering:

* **Four edges, not two.** It checked bottom and right only, so a bracket label at
  `x = -37` and a rail bleeding 730px off the left both read CLEAN.
* **Text over a line.** Text-vs-text cannot see a strikethrough. Restrict it to
  prominent rules (`stroke-width >= 2`, no `grid`/`zero` class) — a recessive 1px
  gridline is *designed* to pass behind a label and grazing a `$` descender is not
  a fault.
* **Rendered "undefined".** Cheap, and it caught a broken key on slide 1.

This exists because every layout bug this deck has shipped was found by
hand-pasting a sweep into devtools — which means it ships the moment anyone
forgets. **It must read CLEAN in cream and dark before a deck is recorded.** Then
step the slides and still look at them: the audit proves geometry, not that the
chart argues its headline.

## Phase 1 — find the story (this is the job)

Never start from the headline. In this order:

1. **The tape.** `/api/history/<SYM>`, last ~35 sessions day by day with volume.
   Find the actual reaction day and its size. It is usually not the day you assume.
2. **Every 8-K with Item 2.02** for eight quarters, from
   `https://data.sec.gov/submissions/CIK##########.json`. Fetch each EX-99.1 and
   extract per quarter: EPS, guidance, segment operating income, debt, leverage,
   buybacks, per-unit metrics. **The guidance table across eight releases is
   frequently the whole story** — build the path and compare each revision to the
   next session's move.
3. **The latest 10-Q** — MD&A, revenue-recognition note, segment note, subsequent
   events. This is where the footnote lives.
4. **The latest 10-K** — Item 1 for unit economics and customer concentration,
   Item 1A for the risk that is actually live.
5. **Form 4s** if insiders have been active — see the runbook for the parser and
   which transaction codes count.
6. **Ask of every beat:** did operating profit come from the core business, or from
   a small/lumpy segment, a cost swing, or a one-off? Bridge it. Then check whether
   management's own guidance confirms or contradicts the beat.

Only then decide the narrative. Write kickers as **connective tissue** — each reads
as the answer to the slide before it, so the deck argues instead of lists.

## Phase 2 — the deck

**8–10 slides. Not 20.** A 23-slide SPCX cut was condensed to 10 and got better:
the argument survives, the pace does not sag, and every slide has to earn its
place. What that means concretely:

* **No title slide and no price-tape slide.** He delivers the intro to camera
  full-frame and the technical read comes *after* the deck, so both only delay the
  reason to keep watching. **Open on the findings slide** — the hook is the promise.
* **Combine ruthlessly.** Pairs that became one slide: three revenue tiles + the
  segment-profit bars (the bars' own sub-labels already carried the revenue); the
  subscriber hero + the revenue-per-customer pair (the catch only means something
  against the good news); the capex hero + the cash bridge; the Note 17 quote + the
  13G. Each pair was two slides saying one thing.
* **Every slide is fundamentals or fine print** — what the filings say that the
  press release does not. Cut the peer multiple, the analyst range, the fair-value
  band and the scored call if the time is not there; keep what a viewer could not
  have found themselves.
* **Close by handing off to the chart**, not with a price target.

~20–25 slides. Every slide: one idea, one visual, a "why it matters" band in plain
English, presenter notes, a target duration. Mark droppable slides `"optional":
True` so the FA half can be cut for time without losing the argument.

Structure that has worked twice: hook → the tape → **what nobody else found** →
what the business does → the one thing you must understand → the unit economics →
what management said → multi-quarter proof → where the profit actually came from →
cash → how it is financed → the forward risk → valuation → peers → the Street →
insiders → scored verdict → working/watch → fair value → the call.

## The presentation toolkit (added 2026-08-15, NBIS)

Template-level capabilities every deck now has. Use them; do not re-invent them.

* **Ticker identity on every slide** — `NBIS · Nebius Group N.V.` renders
  automatically top-right from the payload. Nothing to pass.
* **Stat-anchored findings** — give each finding a `stat` ("$781M", "97.6%") and
  the card leads with it at 44px accent under a `FINDING 01` label; the claim
  becomes one explaining line. Cards without `stat` keep the classic layout.
  Pair with a `sub` carrying the reaction move ("After a {react.move|%+} one-day
  pop, here is the paperwork.") and cards deal in ~180ms apart.
* **Breadcrumb kickers** — the finding-delivery slides carry "Finding 2 of 5 —
  …" kickers, AND the findings list must be ORDERED to delivery order or the
  numbers lie. A finding delivered on a non-finding slide (NBIS's ClickHouse
  markup lands on the scoreboard slide) gets "· finding 1 of 5" appended to
  that slide's kicker.
* **Hero tile** — `"hero": True` on ONE tile per tiles slide renders its value
  at 82px: the slide's entry point. Scale contrast is the engine; six equal
  tiles read as no hierarchy.
* **`extra` on chart slides** — a compact HTML block under the visual (tile
  row, or a `whylist` of ✓/✕ one-liners). This is how the fvband close carries
  its readable bullets.
* **The ruler close** — the pattern that replaced the verdict+calculator slide:
  an `fvband` with `rangeLo/Hi` = bear/bull, `fairValue` = the entry line
  (computed, e.g. midpoint of base and bull — `fair["mid"]` in derive), zones
  labelled "below my base case / my base-to-bull range / above even the bull
  case", a computed verdict line, ✓/✕ bullet recap in `extra`, and the punch
  carrying the call + entry price. **Trade-off:** no `verdict`-type slide means
  the live ⇥-stepping calculator is gone; re-add it as an optional 14th slide
  if the episode wants the on-camera bit.
* **Motion, all automatic:** headlines wipe up (`maskrise`), subs follow, the
  punch lands LAST (~1.15s) so the conclusion is a beat; `.tile .tv`,
  `.mega .v` and `.find .fstat` numerals COUNT UP on slide entry (the final
  frame always writes the exact built string — the animation can never leave a
  drifted figure); chart bodies are vertically centred; every slide must still
  land its build inside 1.4–3.0s.
* **Chart polish, available in chart code:** `areaFill(s, color, top)` gradient
  fades under lines (line/forecast/steparea already use it), `halo(s, x, y, r,
  color, delay)` radial emphasis glow on THE hero mark only (scatter/forecast/
  steparea endpoints already do), `scatter` is negative-safe (spans [min,max],
  zero line), and a `bridge` total prints at 44px accent automatically — the
  landing number is the slide.
* **Talking points** — after any (re)build:
  `python3 export_notes.py <SYM>` writes `Notes/` into the episode folder: one
  txt per slide of one-sentence bullets (the N-key notes, sentence-split) plus
  a combined `00 TALKING-POINTS.txt`. Rerun after every rebuild; figures come
  from the frozen payload so they always match the screen.

Two engine truths found on NBIS, now generalizable:

* **Foreign private issuers** file 6-K/20-F, not 8-K/10-Q — and shareholder
  letters filed as EX-99.2 are SEC-traceable sources for guidance. Restated
  comparatives in year-later releases are the ONE consistent basis for a
  quarterly series when a deconsolidation reclassified history.
* **Pre-market reporters** break the engine's next-session reaction assumption;
  derive the same-day move from the daily bars in the deck module and never
  render the engine's `releases` moves. The quote route's `asOf` now
  self-corrects against the last daily bar (Nasdaq's label can lag its own
  price by a session).

# HARD RULES

Every one of these is a bug that already shipped. The audits enforce them.

## Rule zero — the deck must earn its existence

**Every episode declares at least three ORIGINAL FINDINGS or the build fails.** A
deck that restates the press release has no reason to exist.

Put them in `episodes/<SYM>.json` as `findings: [{claim, where, src}]`, render them
on a `findings` slide early — it is the promise that keeps people watching — and
deliver each in full later.

`where` must name **the note, page, table or statement**, not just the document.
The audit rejects "the 10-Q" and accepts "10-Q Note 3, three pages past the
highlights", because the vague version is what you write when you did not read it.

| Episode | Finding | Where it was buried |
|---|---|---|
| DVA | Commercial revenue — 11% of patients, nearly all the profit — fell 0.7% while government grew 5.4% | 10-Q Note 2, page 7, a payor table with no commentary |
| DVA | 53% of the profit jump came from a segment booking $98M for work done in *previous years* | segment note × revenue-recognition note |
| DVA | Eight guidance tables show the stock rises on one thing only: a higher midpoint | eight 8-Ks, lined up against the tape |
| PLTR | A **1.4% tax rate** — $15M on $1,081M of pretax profit | 10-Q statement of operations, the tax line |
| PLTR | "$6.2B of deal value" vs $4.9B of committed backlog, terminable for convenience | 10-Q Note 3 |
| PLTR | Their own raised guide implies growth rolls over 93% → 83% → 72% | arithmetic on the guide they published as a raise |
| PLTR | **$1.01B of insider selling, zero open-market buying**, across 60 Form 4s | SEC Form 4 XML, aggregated |

The shape that keeps working: **a number management leads with, set against a
number they file three pages later.** Payor tables, revenue-recognition notes,
segment splits, the tax line and backlog definitions are where it lives.

## Data integrity

1. **No figure is ever typed — anywhere.** A typed figure has **three** hiding
   places and the audit scans all of them: `deck_template.html`, string literals in
   `decks/*.py`, and **episode verdict prose**. A hand-typed "44% drawdown" shipped
   on three slides when the real figure was 48%; "15% of the company" recomputes to
   16%; the verdict slide read "$169 … 49x … 145x" while the snapshot said $172.01,
   53× and 147×. **The pattern must include bare multiples** (`49x`), not just `%`
   and `$`.
   - Price-dependent prose → `{path|fmt}` tokens, resolved by
     `build_deck.resolve_prose()` from the live snapshot.
   - Definitional label text ("Deals closed over $1M") → module-level `LITERALS_OK`.
   - Structural filing figures fixed for the quarter → `proseLiteralsOK` in the
     episode file.
   Each exception is then a decision someone made, not an oversight.
2. **One number, one value, across the whole deck.** If two slides state the same
   metric they render from the same expression. Slides 17 and 21 once disagreed by
   4 points on the same multiple.
3. **Anything the company defines itself is QUOTED, never recomputed** — free cash
   flow, adjusted EPS, its own leverage ratio. DVA reports TTM FCF of $1.3B;
   CFO−capex off the XBRL gives $1.6B. The filing wins.
4. **A metric with a missing input is omitted, not estimated.** If a quarter is
   null, say so on screen or leave the metric out.
5. **Derived estimates must cross-check against a reported figure** and be labelled
   "my derivation" on screen. The per-payor rate split only shipped because it
   reproduces reported segment operating income to within 3%.
6. **Never trust the Terminal's `epsYears` / `ttmSeries`.** They overstate DVA's
   annual EPS ~37%, apparently dividing *total* net income rather than income
   attributable to the parent. Build trailing EPS from the reported 8-K quarters.
7. **Refuse to build on stale data.** `_ageS` over its `ttl_for()` ceiling is a hard
   stop, not a warning.
8. **Verify every "best/highest in N" claim.** "Best margin in two years" was false.
9. **Never mix measurement bases in one sentence.** Diluted weighted-average shares
   and shares outstanding gave 25% and 23% for the same fact.
10. **Only assert a beat against consensus if you hold the consensus**, and check
    the consensus is not stale — PLTR's published FY estimate sat *below* the
    half-year already banked. Build multiples off company guidance and say so on
    screen.
11. **A high minus a low is not a drawdown.** PLTR's 52-week high *precedes* its
    low. `snap.peakToTrough` walks the tape in order and carries both endpoints.
12. **Aggregates across many filings need recomputation, not text-matching.** No
    single Form 4 states "$1.01B across 435 transactions". Mark the block
    `_derived`, cache source XML under `.cache_form4/<SYM>/`, and add an
    audit that re-parses and recomputes.
13. **A number must match on a number boundary.** `validate_facts.py` once passed a
    fabricated 611 because it sits inside "2,611,500". The same tightening then
    caught a real mis-attribution. When it flags something, confirm the filing text
    first; add `_pct` or `searchAs` rather than loosening the match.
14. **When two figures for the "same" thing disagree, name every reason.**
    Palantir's $6.2B "remaining deal value" vs $4.9B of RPO differs on *three* axes
    at once. Presenting it as one clean gap overstated it. And never write a
    self-contradicting sentence: RPO is what remains *after* cancelable value is
    removed, so "non-cancelable backlog, and customers can terminate" is nonsense —
    the termination right is the *cause* of the small number.
15. **Test the hypothesis before it becomes a slide.** For PLTR I guessed the
    reaction tracked the prior run-up, measured it, it did not hold, so it did not
    ship. What shipped was the weaker, true claim.

## Story

16. **The chart must argue the caption's point.** A revenue chart under a margin
    claim showed a 2.8× gap while the words said 10×. Stack the shared cost out.
17. **Plot the change, not the level, when the change is the point.** Two bars
    differing by 0.7% on a shared axis differ by two pixels.
18. **No copy that points FORWARD at a neighbouring slide.** Slides get cut, so
    "the next number is the one the headline hides" breaks silently in the short
    cut. The check covers loose nouns ("the next number/one") only in the forward
    direction — "that last one", pointing at the third figure inside the same
    band, is ordinary prose and flagging it was a false positive.
19. **A caption must not contradict its chart, or restate the wrong quantity.**
    "Does not leave much between here and fair" sat above a 65% gap. And 65% is
    *price over fair value*; *fair value below price* is 39%. Different sentences.
20. **A single point estimate reads as false precision.** Put the bear/bull bracket
    on the fair-value ruler. When the bull case sits near today's price the honest
    line is not "this is overvalued", it is "you are already being paid as if the
    bull case happens".
21. **EXECUTIVE STYLE: one visual, a short headline, one punch line.** The screen
    used to carry a 90-word "why it matters" paragraph per slide — 945 words across
    ten slides, which a viewer reads *instead of* listening, and which was saying
    what the presenter says out loud anyway. The long form is still written and
    still verified: it goes in `why`, which is **never rendered** and lands in
    `SCRIPT.txt` as the second half of what he says. On screen: head ≤ 9 words,
    `punch` ≤ 14, `sub` ≤ 12, **30 words all in** — enforced by `word-budget`.
    The punch line renders at 40px, so it reads from the sofa. Wrap the two or
    three words that carry it in `<b>`. 185 words now do what 945 did.
22. **The punch line is for a beginner.** No "multiple", "underwriting", "pretax",
    "add-back", "exit multiple", "print". See `references/plain-english.md` — it
    carries the banned list and the script that measures reading grade.

## Design

23. **Mark specs, from the `dataviz` skill — load it before touching a chart.**
    Three specs were being violated, and each reads as "default chart": **thin
    marks** (bars were up to 160px wide; now 58–84px), **rounded on the data end
    only** — `rx` on a rect rounds all four corners including the one on the
    baseline, so bars, hbars and stacked segments now draw through `barPath()`,
    which is square where the mark is anchored — and **a 2px surface gap between
    abutting fills**, without which stacked segments read as one mark. Also:
    markers ≥ 8px, a 2px–3px surface ring where marks overlap, and **selective
    direct labels — never a number on every point** (the step area labels 2 of its
    7 points). Text wears ink tokens; a coloured mark beside it carries identity.
    **`validate_palette.js` HAS now been run** (NBIS build, 2026-08-15 — the
    bundled dataviz skill ships the script again): both pairs pass all six
    checks. Cream `#c2603f`+`#2a78d6` on `#fcfcfb`: CVD ΔE 22.8, normal 28.3.
    Dark `#d67350`+`#4d90da` on `#1a1a19`: CVD ΔE 20.0, normal 25.5. Re-run it
    only if a palette value changes.
24. **Never eyeball a palette when the validator is available.** Chart
    marks use `--s1`/`--s2` (light `#c2603f`+`#2a78d6`, dark `#d67350`+`#4d90da`).
    `--accent` is chrome and text only.
25. **Colour carries meaning.** Green = good for the shareholder, red/orange = bad,
    anything else = neither. Assets green, liabilities orange, insider selling red,
    revenue-vs-earnings a neutral series pair. `--s1` and `--accent` may never
    stand in for "good": a `dumbbell` painted every good delta terracotta. And a
    band that is **mechanical rather than a verdict** must not be green/red at all
    — the merger-collar chart painted "below the floor" green when below the floor
    is the *worst* outcome for a holder (maximum dilution). `fvband` takes
    `zoneTone: "neutral"` plus `zoneLabs` for that case, and the labels carry the
    meaning instead of the colour.
26. **One magnitude rule, whole deck** — `decks/fmt.py`. **$1.8B · $730M · $208K.**
    Never `$0.45B`, never `$1,800M`. Nothing formats money by hand.
27. **Never a dual y-axis.** Index both to 100, or `smallmult`.
28. **No single visual form carries more than a third of the deck** (`slide-variety`).
    **26 chart kinds**: `bars bridge distribution donut dumbbell forecast funded
    fvband gauge grouped hbars indexed insider line lollipop peers radar range
    sankey scatter slope smallmult stackedh steparea track treemap`.
    **Count the FAMILY, not the kind.** A deck of bars, lollipops, hbars, stacked
    bars and bridges is still a deck of rectangles against an axis — and a
    `smallmult` is two more panels of bars. Told twice that the visuals were "the
    same old bar charts" while `slide-variety` passed, because that check counts
    kinds. What fixed it was choosing forms by job:
    * composition of a total → **`treemap`** (area), not `hbars` (length)
    * two measures moving against each other over time → **`scatter`**, a
      connected trajectory with an arrowhead. One shape says "twice the customers,
      each worth a fifth less"; two bar panels make the viewer hold one chart in
      their head while reading the other
    * how much of what came in survived → **`dumbbell`** from sales to profit
    * a running total over dates → **`steparea`**
    * ranked change across a few categories → **`lollipop`**
    Keep a `bridge` where a walk is genuinely the subject. SPCX went from six of
    eight chart slides being rectangles to two.
    **`lollipop`** is the right form for ranked change across a handful of
    categories — a 3px stem leading to an 11px dot, where the dot's position
    carries the value. Four of those read in a glance where four fat bars read as
    a wall. **`steparea`** is for a running total over dated steps: a staircase
    with a filled area, because accumulation over time is a line's job, not a
    bar's. Both were added after three of twelve slides were vertical bars and the
    deck looked generic; it is now one bars slide out of twelve. **10 slide types**: `chart findings mega
    quote reasons snapshot tiles title twocol verdict`. The `design` skill maps
    each to its job.
29. **Never pass a callable across the Python→JSON boundary.** A `"fmt": None`
    became `null`, threw in the render map, and blanked *every* slide. Formatters
    are named strings (`fmtKind`).
30. **No HTML entity in a chart spec.** Chart labels are `textContent`, so
    `&times;` renders as seven literal characters and its width shoved a label into
    the next column. Prose takes entities; chart labels take the glyph.
31. **Nothing on camera below 15px** (`min-font-size`). `#notes`, `#grid`, the HUD
    and the footer slug are exempt.
32. **A chart's spec must match what that chart actually reads** (`chart-shape`).
    `chart-specs` only asks whether the KIND exists. Five SPCX charts shipped with
    the wrong keys and all passed: `hbars` was handed a `right` column it does not
    render, `range` a `rows` table it does not read (blank slide), `grouped` a
    `series`/`v` shape instead of `cats`/`vals`. The audit now derives each kind's
    required keys from the template source, so it cannot drift, and also flags a
    key the chart never reads — silently discarded data.
    **It checks ROW-level keys too**, and that arm exists because top-level-only
    checking let a blanket rename of every `"v":` to `"when":` through a deck
    module pass all 30 invariants with four charts holding no plottable value. A
    row key the chart never reads, or a collection supplying none of the keys the
    chart reads, both fail. Provenance carried deliberately beside the drawn
    values takes a `_` prefix (`_eps`, `_q`) — the same convention as `_derived`.
33. **Every `fmtKind` must exist** (`fmt-kinds`). An unknown name falls back to
    money-in-millions without complaint: it printed "$14M" for 14 million Starlink
    subscribers and "$102M" for a $102 monthly bill. Valid names: `auto usdB usdM
    pct plain plain0 plain1 usd0 usd2 pct0`.
34. **A chart scale must hold what it is given.** `bridge` was zero-based, so a
    running total that crossed into negative mapped off the bottom of the slide and
    straight through the why-band — SpaceX's cash bridge drew to 2587 in a 500-high
    box. `dumbbell` hardcoded `min = 0`, so a negative endpoint landed on top of the
    row name. Both now span [min, max] and draw a zero line when the range crosses it.
    `track` spanned the analyst target range alone, so DVA's price — *below* the
    lowest target — drew the rail 730px off the left of the canvas and dropped the
    "now" marker, the single most important mark, entirely. Every chart's scale
    spans every mark it draws, not just the series it was designed around.
35. **Never mix units on one axis.** Launch counts (9–46) and tonnes to orbit
    (485–652) on a shared dumbbell squashed three rows into an unreadable cluster.
    Four different units belong on a percentage-change axis, not a shared absolute one.
36. **A negative value needs a chart that can draw it** (`negative-values`). Only
    `bars` (with `zeroLine`), `bridge`, `dumbbell`, `line`, `indexed`, `smallmult`,
    `slope`, `forecast` and `distribution` span [min, max]. Everything else measures
    magnitude from zero, so a negative is invisible or inverted. This bites the
    moment a loss-making company meets a magnitude chart.
37. **Every slide animates for 1.5–3s after the flip, and horizontal bars use `growX`.**
    A slide that finishes animating before the first sentence is out reads as a
    static image. Durations were roughly doubled and every per-element stagger runs
    through **one** function, `AD()`, scaled by `AD_SCALE` — 55 inline delay
    expressions, so pacing is one number, not 55 edits. Measure it rather than
    eyeballing: `max(animationDelay + animationDuration)` per slide should land
    between 1.4s and 3.0s. `grow` is `scaleY`;
    using it on an hbar squashes it vertically instead of extending it sideways —
    that shipped on four charts. Eight keyframes — `grow growX draw fade pop bloom
    pipin rowin` — plus a `sweep` class that reuses `draw` for arcs. All `fill:
    both`, all finishing inside ~1.6s.

38. **A chart must contain the numbers in its own headline.** Slide 8 read "Costs
    grew +34% while revenue grew +62%" over a chart showing only +25% and +50% —
    neither headline figure was on screen, and the two that were looked like a
    contradiction. If the headline compares two things, both belong on the chart.
39. **The magnitude rule must not round a label into a lie.** A $122.569M actual
    against a $123M guidance top printed "$123M", so the row read "guided 117–123
    … $123M … inside the range" — the label contradicting its own verdict. Keep a
    decimal in exactly that case. Accuracy outranks the formatting convention.
40. **A peer set can contain a non-comparable.** RKLB's peers include Iridium — the
    company it is *buying*, not a rival. Averaging all five gave 23.8× and the
    headline called it "what the defence companies cost"; the primes-only figure is
    **35.2×**. Declare `target` and `defence` in the episode's peers block, average
    only the declared subset, and make the chart's reference line mean the same
    thing the headline does. `die()` if the subset is not declared.
41. **Never blanket-rename inside a deck module.** A regex meant for three chip keys
    renamed 21 chart value keys across two files; every audit still printed ALL
    PASS. Change the specific lines, re-read the diff, and remember `git` only
    covers files that are actually tracked — `decks/RKLB.py` was untracked and had
    no revert path.
42. **Nothing rendered may read "undefined", "NaN" or "[object Object]"**
    (in-deck audit). Two title slides shipped **"READ THE SOURCE — undefined
    undefined"** because RKLB and SPCX built chips as `{k, v}` while the template
    reads `{form, when}`. It was the first thing on camera and no check looked at
    rendered strings.

43. **Audit BOTH layouts — the camera one is the default, so it is what ships.** `?cam=left&camw=26`
    narrows every chart from 1660 to 1161, and four charts that passed at full
    width broke there — `bars` sub-labels into each other, `track`'s two value
    labels touching, `donut`'s legend into its stats panel, and `radar` drawing
    labels to x = −133, outside its own box, which no check had ever looked at
    because it renders outside `[data-chart]`. Nothing may cross into the
    reserved column; the footer did, at `left:96px`, while the audit said CLEAN.

44. **No British currency, spelling or slang** (`us-idiom`). A fair-value band
    shipped "ends up keeping 20p in the pound" — in a deck quoting SEC filings in
    dollars. It reads naturally when you write fast and is unmissable on camera.
45. **State dates; never say "yesterday"** (`relative-dates`). "The 13G filed
    yesterday" is true the day the deck is built and wrong the day it is recorded.
    Put the filing date in the episode as a fact and interpolate it. A deck
    deliberately recorded the same evening opts out per slide with `sameDay: True`.
46. **A threshold must never round toward the wrong side.** The lockup's price
    trigger is `$135.00 × 1.30 = $175.50`; printing it as "$176" states a harder
    bar than the prospectus sets. Round thresholds to the cent.
47. **A bar of zero cannot show that nothing happened.** The lockup chart carried a
    0% bar captioned "price bonus — MISSED", which draws as nothing at all. A
    non-event belongs in the words. That chart is now a **running total**, which
    also answers the better question: how much of the locked group can sell by the
    time someone is watching.

48. **Cross-check against an independent vendor** — `python3 crosscheck.py <SYM>`,
    opt-in and outside the core loop, because it needs the network and yfinance and a
    vendor outage must never fail a build. On SPCX ten of eleven figures matched the
    filings to the dollar; the one gap was capex (vendor 29,352 against the filed
    28,476) because the vendor folds capitalised interest into capital expenditure
    while the cash flow statement lists it separately. **The filing always wins** —
    the job is to explain the gap in the fact's `_vendorNote`, not to change the deck.
49. **A count stated in words is still a figure.** The findings slide said "Four
    things" after a fifth finding was added; spelled-out numbers slip past every
    figure check. `findings-count` compares the stated count to the rendered one.

## Themes and keys

One file, both palettes. `T` toggles cream ⇄ dark; `?theme=cream|dark` on open;
cream is default. Zero dependencies — hand-rolled inline SVG, works offline. ⌘P
exports a clean PDF.

**THE CAMERA LAYOUT IS THE DEFAULT.** Every deck opens with a reserved column on
the left and a frame the camera sits inside, because that is how every episode is
recorded — it is not a mode to remember to switch on. `C` turns it off, `⇧C` shows
the OBS pixel box, `[`/`]` resize the column, and the choice persists. The stored
value is **tri-state** (`left`/`right`/`off`): with a default of `left`, an absent
key had to mean "never chosen", or turning it off could not stick. `?cam=` still
overrides from a URL. `@media print` strips the column, so a ⌘P handout is
full-bleed. It reserves
the column by *padding the slide*, so the stage stays `scale(1.0)` against a 1080p
frame and no type shrinks; charts rebuild at `chartW()`. `C` toggles the pixel
measurements for aligning OBS (never during a take). **Run the layout audit in
camera mode as well as normal** — narrowing the charts is what finds label
collisions, and it found four. See `references/recording-setup.md`.

`→`/`Space` next · `←` back · `T` theme · `N` notes · `H` presenter HUD + timer ·
`G` grid · `F` fullscreen · `R` restart timer. On the call slide, `⇥` and `↑↓` step
the fair-value assumptions live on camera.

## Timing

The build prints a full cut and a core cut. PLTR landed 10m6s / 8m8s; DVA 9m2s /
7m9s — both over the 5:00 FA budget it warns about. **Report both honestly and let
him choose what to cut.** Do not quietly trim the argument to hit a number, and do
not pad target durations to make the total look better.

## Working with Nikil

Lead with the answer, bullets, no walls of text. Verify before asserting — pull
live data for anything date-sensitive rather than recalling it. Never fabricate or
assume: everything is in the 8-K, 10-Q, Yahoo, Webull or a web search, so go get
it. Do not soften bad news about data quality; he would rather hear a number is
unverifiable than see it presented as fact. When you find a Terminal bug mid-build,
flag it with the diagnosis and keep the deck's numbers independent of it.

**Validate before you write to disk.** `ast.parse(t)` *then* `open(p,"w")`. Writing
first has broken `decks/PLTR.py` twice mid-edit.
