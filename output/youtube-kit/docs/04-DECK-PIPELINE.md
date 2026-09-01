# 04 — The Deck Pipeline

How the Sunday engine works, what a new ticker needs, and every hard rule — each
of which exists because it already shipped as a bug.

---

## The files

| File | Role |
|---|---|
| `build_deck.py` | **Generic engine. Never edit it for a ticker.** Fetches, builds the tape, peak-to-trough, earnings-reaction history, indexed price-vs-earnings, forward multiples, the street block and provenance, resolves episode prose tokens, then dispatches to your module. |
| `marketdata.py` | The whole data layer. No server, no localhost. |
| `decks/<SYM>.py` | **Bespoke per company.** `derive(...)` + `slides(...)`. |
| `decks/fmt.py` | Number formatting helpers. |
| `episodes/<SYM>.json` | Every filing-read figure, each naming its source. |
| `deck_template.html` | The renderer — one function per chart form, registered in `CHARTS`. |
| `audit_deck.py` | Deck invariants. Must print `ALL DECK INVARIANTS PASS`. |
| `validate_facts.py` | Every episode fact traces to filing text. Must print `ALL EPISODE FACTS TRACE`. |
| `crosscheck.py` | Independent vendor cross-check. |
| `export_notes.py` | Writes `Notes/` — per-slide talking points. |
| `deckpath.py` | Finds a built episode wherever it was filed. |

## What a new ticker needs

**Two files, and never an edit to `build_deck.py`:**

1. **`episodes/<SYM>.json`** — every figure, each naming the filing it came from.
2. **`decks/<SYM>.py`** — exporting:
   - `derive(snap, ep, fund, qrows, die, fact)` → the company-specific metrics.
     Call `die()` on anything that does not reconcile.
   - `slides(snap, ep, fact, fund_quarters=None)` → the slide list.

An earlier version of this skill claimed a new ticker needed no new code at all.
That was wrong. **The facts are data; the narrative is bespoke** — pretending
otherwise produces a template, which is the opposite of the point.

Company-shaped audit checks (a payor split, an EPS-guidance range, an insider
block) `SKIP` with an `n/a` line when a company has no such figure — never
silently pass.

---

## The loop

```bash
cd "$(git rev-parse --show-toplevel)"
export DECK_OUT=output

python3 build_deck.py <SYM>          # refuses on stale data
python3 audit_deck.py <SYM>          # ALL DECK INVARIANTS PASS
python3 validate_facts.py <SYM>      # ALL EPISODE FACTS TRACE
python3 audit_deck.py <SYM> --prove  # must go RED
python3 validate_facts.py <SYM> --prove
python3 export_notes.py <SYM>        # writes Notes/
```

**`--prove` is not ceremony.** A check that cannot fail is worthless. The
episode-prose check was written to catch `"49x guided revenue"` — and its first
version matched only `%` and `$`, so it would have missed the exact bug it existed
for. `--prove` is what exposed that. Run it after adding any check.

Rerun `export_notes.py` after **every** rebuild — figures come from the frozen
payload so the notes always match the screen.

---

## The in-deck layout audit

**It lives in the deck, not in a console paste.** Open the HTML with `?audit=1`
and read one line:

```
[deck] AUDIT CLEAN — 22 slides, no layout, animation or text faults
```
```
[deck] AUDIT — 3 issue(s):
  10 bridge: chart draws 2510px below its box
  10 bridge: chart overlaps the why band by 2198px
  18 range: DEAD CHART
```

`window.deckAudit()` returns the same array on demand.

Per slide, in both themes, it checks:
- dead charts
- SVG **content** measured against **all four edges** of its own viewBox
- overlap with the why band
- text running into text
- **text struck through by a prominent rule**
- any rendered `undefined` / `NaN`
- unknown or badly-filled animations
- sub-15px on-camera text
- a stage translated off-centre without `?cam=`

Three of those arms were added *after* the audit passed a visibly broken deck:

- **Four edges, not two.** It checked bottom and right only, so a bracket label at
  `x = -37` and a rail bleeding 730px off the left both read CLEAN.
- **Text over a line.** Text-vs-text cannot see a strikethrough. Restricted to
  prominent rules (`stroke-width >= 2`, no `grid`/`zero` class) — a recessive 1px
  gridline is *designed* to pass behind a label, and grazing a `$` descender is
  not a fault.
- **Rendered "undefined".** Cheap, and it caught a broken key on slide 1.

**It must read CLEAN in cream and dark before a deck is recorded.** Then step the
slides and still look at them: the audit proves geometry, not that the chart
argues its headline.

---

## Slide count and structure

**8–10 slides. Not 20.** A 23-slide SPCX cut was condensed to 10 and got better.
Concretely:

- **No title slide and no price-tape slide.** The intro is delivered to camera
  full-frame and the technical read comes *after* the deck, so both only delay the
  reason to keep watching. **Open on the findings slide** — the hook is the promise.
- **Combine ruthlessly.** Pairs that became one slide: three revenue tiles + the
  segment-profit bars (the bars' sub-labels already carried the revenue); the
  subscriber hero + revenue-per-customer (the catch only means something against
  the good news); the capex hero + the cash bridge; the Note 17 quote + the 13G.
- **Every slide is fundamentals or fine print** — what the filings say that the
  press release does not. Cut the peer multiple, the analyst range, the fair-value
  band and the scored call if the time isn't there; keep what a viewer could not
  have found themselves.
- **Close by handing off to the chart**, not with a price target.

The long form (~20–25 slides) that has worked twice:
hook → the tape → **what nobody else found** → what the business does → the one
thing you must understand → the unit economics → what management said →
multi-quarter proof → where the profit actually came from → cash → how it is
financed → the forward risk → valuation → peers → the Street → insiders → scored
verdict → working/watch → fair value → the call.

Mark droppable slides `"optional": True` so the FA half can be cut for time
without losing the argument.

Write kickers as **connective tissue** — each reads as the answer to the slide
before it, so the deck argues instead of lists.

---

## The presentation toolkit (use it, don't re-invent it)

- **Ticker identity on every slide** — `NBIS · Nebius Group N.V.` renders
  automatically top-right from the payload. Nothing to pass.
- **Stat-anchored findings** — give a finding a `stat` ("$781M", "97.6%") and the
  card leads with it at 44px accent under a `FINDING 01` label; the claim becomes
  one explaining line. Cards without `stat` keep the classic layout. Pair with a
  `sub` carrying the reaction move; cards deal ~180ms apart.
- **Breadcrumb kickers** — finding-delivery slides carry "Finding 2 of 5 — …",
  **and the findings list must be ordered to delivery order or the numbers lie.**
  A finding delivered on a non-finding slide gets "· finding 1 of 5" appended to
  that slide's kicker.
- **Hero tile** — `"hero": True` on ONE tile per tiles slide renders its value at
  82px: the slide's entry point. Scale contrast is the engine; six equal tiles
  read as no hierarchy.
- **`extra` on chart slides** — a compact HTML block under the visual (a tile row,
  or a `whylist` of ✓/✕ one-liners).
- **The ruler close** — the pattern that replaced verdict+calculator: an `fvband`
  with `rangeLo/Hi` = bear/bull, `fairValue` = the entry line (computed, e.g.
  `fair["mid"]`), zones labelled "below my base case / my base-to-bull range /
  above even the bull case", a computed verdict line, ✓/✕ recap in `extra`, and
  the punch carrying the call + entry price.
  *Trade-off:* no `verdict`-type slide means the live ⇥-stepping calculator is
  gone; re-add it as an optional 14th slide if the episode wants the on-camera bit.
- **Motion, all automatic** — headlines wipe up (`maskrise`), subs follow, the
  punch lands LAST (~1.15s) so the conclusion is a beat; `.tile .tv`, `.mega .v`
  and `.find .fstat` numerals COUNT UP on entry (the final frame always writes the
  exact built string, so the animation can never leave a drifted figure); chart
  bodies are vertically centred; every slide must land its build inside 1.4–3.0s.
- **Chart polish** — `areaFill(s, color, top)` gradient fades under lines;
  `halo(s, x, y, r, color, delay)` radial emphasis on THE hero mark only; `scatter`
  is negative-safe (spans [min,max], zero line); a `bridge` total prints at 44px
  accent automatically — the landing number is the slide.

---

## Recording layout — the `?cam=` system

Measured across a finished 24-slide deck: **82% of the 1920×1080 canvas carries
content on some slide**, and the only region free on *every* slide is a 1080×80
strip at the bottom — too short for a camera.

**So a webcam bubble over a full-bleed deck will cover a chart. Not might.** The
deck has to make room instead:

```
?cam=left&camw=26     the recording layout — 26% of the width free on the left
?cam=right&camw=26    mirrored
?cam=bottom           reserve height underneath
```

**The column is reserved by PADDING the slide, not by shrinking the stage.** The
first version scaled the whole 16:9 stage into 70% of the frame — `scale(0.70)` on
every font, so a 15px axis label landed at 10px, below the readability floor,
plus 324px of dead vertical space. Now the stage still fills 1920×1080 at scale
1.0 and `.slide` gains `padding-left: 96 + 1920·camw`. Type stays exactly the size
it was designed at.

Verify:
```js
getComputedStyle(document.getElementById('stage')).transform    // matrix(1,0,0,1,0,0)
getComputedStyle(document.querySelector('.slide')).paddingLeft  // 595px at camw=26
```

`chartW()` returns `1660 - camPx()` and all chart functions read it — without that
a 1660 viewBox inside a narrower box gets scaled down by `preserveAspectRatio`,
and every label with it.

**Narrowing is what finds latent chart bugs.** All of these passed at 1660 and
broke at 1161:

| Chart | Broke when narrowed | Fix |
|---|---|---|
| `bars` | two-word sub-labels ran into each other | `wrapLabel()` to the slot, 2 lines |
| `track` | price and mean-target labels touched | stack the second 62px higher |
| `donut` | legend ran into the stats panel | columns from measured widths; stats stack when tight |
| `radar` | labels drew to x = −133, outside the box | box widened by `LP`, labels wrap inside |

**Re-run the layout audit in camera mode after touching any chart.**

---

# THE HARD RULES

Every one of these is a bug that already shipped. The audits enforce them.

## Rule zero — the deck must earn its existence

**Every episode declares at least three ORIGINAL FINDINGS or the build fails.**

Put them in `episodes/<SYM>.json` as `findings: [{claim, where, src}]`, render them
on a `findings` slide early — it is the promise that keeps people watching — and
deliver each in full later.

**`where` must name the note, page, table or statement**, not just the document.
The audit rejects "the 10-Q" and accepts "10-Q Note 3, three pages past the
highlights", because the vague version is what you write when you did not read it.

Worked examples of what a finding looks like:

| Episode | Finding | Where it was buried |
|---|---|---|
| DVA | Commercial revenue — 11% of patients, nearly all the profit — fell 0.7% while government grew 5.4% | 10-Q Note 2, page 7, a payor table with no commentary |
| DVA | 53% of the profit jump came from a segment booking $98M for work done in *previous years* | segment note × revenue-recognition note |
| DVA | Eight guidance tables show the stock rises on one thing only: a higher midpoint | eight 8-Ks, lined up against the tape |
| PLTR | A **1.4% tax rate** — $15M on $1,081M of pretax profit | 10-Q statement of operations, the tax line |
| PLTR | "$6.2B of deal value" vs $4.9B of committed backlog, terminable for convenience | 10-Q Note 3 |
| PLTR | Their own raised guide implies growth rolls over 93% → 83% → 72% | arithmetic on the guide they published as a raise |
| PLTR | **$1.01B of insider selling, zero open-market buying**, across 60 Form 4s | SEC Form 4 XML, aggregated |

**The shape that keeps working: a number management leads with, set against a
number they file three pages later.** Payor tables, revenue-recognition notes,
segment splits, the tax line and backlog definitions are where it lives.

## Data integrity

1. **No figure is ever typed — anywhere.** A typed figure has **three** hiding
   places and the audit scans all of them: `deck_template.html`, string literals in
   `decks/*.py`, and **episode verdict prose**. A hand-typed "44% drawdown" shipped
   on three slides when the real figure was 48%; "15% of the company" recomputes to
   16%; a verdict slide read "$169 … 49x … 145x" while the snapshot said $172.01,
   53× and 147×. **The pattern must include bare multiples (`49x`)**, not just `%`
   and `$`. Three legitimate escapes:
   - price-dependent prose → `{path|fmt}` tokens, resolved by
     `build_deck.resolve_prose()` from the live snapshot;
   - definitional label text ("Deals closed over $1M") → module-level `LITERALS_OK`;
   - structural filing figures fixed for the quarter → `proseLiteralsOK` in the
     episode file.

   Each exception is then a decision someone made, not an oversight.
2. **One number, one value, across the whole deck.** If two slides state the same
   metric they render from the same expression. Slides 17 and 21 once disagreed by
   4 points on the same multiple.
3. **Anything the company defines itself is QUOTED, never recomputed** — free cash
   flow, adjusted EPS, its own leverage ratio. DVA reports TTM FCF of $1.3B;
   CFO−capex off the XBRL gives $1.6B. **The filing wins.**
4. **A metric with a missing input is omitted, not estimated.** If a quarter is
   null, say so on screen or leave the metric out.
5. **Derived estimates must cross-check against a reported figure** and be labelled
   "my derivation" on screen. The per-payor rate split only shipped because it
   reproduces reported segment operating income to within 3%.
6. **Never trust vendor `epsYears` / `ttmSeries`.** They overstate DVA's annual EPS
   ~37%, apparently dividing *total* net income rather than income attributable to
   the parent. Build trailing EPS from the reported 8-K quarters.
7. **Refuse to build on stale data.** `_ageS` over its `ttl_for()` ceiling is a hard
   stop, not a warning.
8. **Verify every "best/highest in N" claim.** "Best margin in two years" was false.
9. **Never mix measurement bases in one sentence.** Diluted weighted-average shares
   and shares outstanding gave 25% and 23% for the same fact.
10. **Only assert a beat against consensus if you hold the consensus**, and check it
    isn't stale — PLTR's published FY estimate sat *below* the half-year already
    banked. Build multiples off company guidance and say so on screen.
11. **A high minus a low is not a drawdown.** PLTR's 52-week high *precedes* its low.
    `snap.peakToTrough` walks the tape in order and carries both endpoints.
12. **Aggregates across many filings need recomputation, not text-matching.** No
    single Form 4 states "$1.01B across 435 transactions". Mark the block
    `_derived`, cache source XML under `.cache_form4/<SYM>/`, and add an audit that
    re-parses and recomputes.
13. **A number must match on a number boundary.** `validate_facts.py` once passed a
    fabricated 611 because it sits inside "2,611,500". The same tightening then
    caught a real mis-attribution. When it flags something, confirm the filing text
    first; add `_pct` or `searchAs` rather than loosening the match.
14. **When two figures for the "same" thing disagree, name every reason.** PLTR's
    $6.2B "remaining deal value" vs $4.9B of RPO differs on *three* axes at once;
    presenting it as one clean gap overstated it. And never write a
    self-contradicting sentence: RPO is what remains *after* cancelable value is
    removed, so "non-cancelable backlog, and customers can terminate" is nonsense —
    the termination right is the *cause* of the small number.
15. **Test the hypothesis before it becomes a slide.** For PLTR the guess was that
    the reaction tracked the prior run-up; it was measured, it did not hold, so it
    did not ship. What shipped was the weaker, true claim.

## Story

16. **The chart must argue the caption's point.** A revenue chart under a margin
    claim showed a 2.8× gap while the words said 10×. Stack the shared cost out.
17. **Plot the change, not the level, when the change is the point.** Two bars
    differing by 0.7% on a shared axis differ by two pixels.
18. **No copy that points FORWARD at a neighbouring slide.** Slides get cut, so
    "the next number is the one the headline hides" breaks silently in the short
    cut. The check covers loose nouns ("the next number/one") in the forward
    direction only — "that last one", pointing back inside the same band, is
    ordinary prose.
19. **A caption must not contradict its chart, or restate the wrong quantity.**
    "Does not leave much between here and fair" sat above a 65% gap. And 65% is
    *price over fair value*; *fair value below price* is 39%. Different sentences.
20. **A single point estimate reads as false precision.** Put the bear/bull bracket
    on the fair-value ruler. When the bull case sits near today's price, the honest
    line is not "this is overvalued" — it is "you are already being paid as if the
    bull case happens".
21. **EXECUTIVE STYLE: one visual, a short headline, one punch line.** The screen
    used to carry a 90-word "why it matters" paragraph per slide — 945 words across
    ten slides, which a viewer reads *instead of* listening, and which says what
    the presenter says out loud anyway. The long form is still written and still
    verified: it goes in `why`, which is **never rendered** and lands in `SCRIPT`
    as the second half of what he says.
    **On screen: head ≤ 9 words, `punch` ≤ 14, `sub` ≤ 12, 30 words all in** —
    enforced by `word-budget`.
