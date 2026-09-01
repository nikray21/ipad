# 02 — The Weekly Workflow, Command by Command

Two episodes a week. Sunday is the ticker; Wednesday is the lesson.

---

# SUNDAY — the stock episode

## Step 0 · Preflight (2 min)

```bash
cd "$(git rev-parse --show-toplevel)"
export DECK_OUT=output
python3 marketdata.py quote NVDA        # upstreams reachable?
ls decks/ episodes/                     # what's already been covered
```

Nothing to start. A failing route means connectivity or an upstream shape change,
never a service being down.

## Step 1 · Pick the ticker — `/find-stock`

```
/find-stock
```

What happens under the hood:

**Phase 1 — three parallel research agents**, each told today's date and the
5-day window:
1. *Market data* — Yahoo trending + gainers, Google Finance most-followed,
   stockanalysis.com weekly gainers, this week's earnings reactions, M&A/FDA/
   product catalysts. Output: 10–15 tickers with catalyst | move | sources.
2. *Social buzz* — ApeWisdom, AltIndex WSB + Stocktwits, Tradestie, Stocktwits
   trending, Benzinga "buzzing". Prioritises **rising mention velocity** over
   perennials. NVDA/TSLA only qualify with a specific this-week catalyst.
3. *YouTube demand* — what got uploaded this week and what pulled outsized views,
   plus YouTube autocomplete via
   `http://suggestqueries.google.com/complete/search?client=firefox&ds=yt&q=…`
   for "stock analysis", "should i buy", "is it too late to buy". Identifies
   saturated vs underserved tickers and collects the literal phrases people type.

**Phase 2 — Google Trends, YouTube Search property.** This is the deciding
dataset. Bundled script, stdlib-only, no browser:

```bash
python3 .claude/skills/find-stock/trends_http.py "NBIS stock" "nebius stock" "PLTR stock"
python3 .claude/skills/find-stock/trends_http.py --related "NBIS stock"
```

Rules: max 5 keywords per comparison · `property: youtube` · `now 7-d` · geo US ·
repeat one **anchor keyword** across batches so scales are comparable · test
**both query forms** per candidate (ticker form "NBIS stock" *and* company-name
form "nebius stock" — a rising *ticker* form means retail just found it, the
strongest early signal) · also test the big **thematic** queries in play that week
("ai bubble", "silver price"), because themes often out-search every ticker and
reveal the umbrella your video rides · pull **related queries** (top + rising/
Breakout) on the finalists — those become your title and description keywords.

**Phase 3 — the verdict**, applying the four tests in `00-START-HERE.md`.

**You get:** one ticker with its momentum numbers, 2–3 runner-ups with why each
lost, the skip list, and the search phrases for the title.

## Step 2 · Build the episode — `/stock-analysis-presentation`

```
/stock-analysis-presentation NBIS
```

### Phase 1 — find the story (this is most of the work)

Never start from the headline. In this order:

1. **The tape.** Last ~35 sessions, day by day with volume. Find the *actual*
   reaction day and its size — it is usually not the day you assume. Then the
   in-order peak-to-trough (a high minus a low is not a drawdown if the high came
   second).
2. **Every 8-K with Item 2.02 for eight quarters.** Fetch each EX-99.1 and extract
   per quarter: EPS, guidance low/high, segment operating income, debt, leverage,
   buybacks, per-unit metrics. **The guidance table across eight releases is
   frequently the whole story** — line each revision up against the next session's
   move.
3. **The latest 10-Q** — MD&A, revenue-recognition note, segment note, subsequent
   events. This is where the footnote lives.
4. **The latest 10-K** — Item 1 for unit economics and customer concentration,
   Item 1A for the risk that is actually live.
5. **Form 4s** if insiders have been active.
6. **Ask of every beat:** did operating profit come from the core business, or from
   a small/lumpy segment, a cost swing, or a one-off? Bridge it. Then check whether
   management's own guidance confirms or contradicts the beat.

Foreign private issuers (e.g. NBIS) file **6-K/20-F**, not 8-K/10-Q — and
shareholder letters filed as **EX-99.2** are SEC-traceable guidance sources.

### Phase 2 — write the two files

```
episodes/<SYM>.json     every figure, each naming the filing it came from
decks/<SYM>.py          derive(...) + slides(...) — the bespoke narrative
```

**Never edit `build_deck.py`.** It stays generic: it fetches, builds the tape, the
peak-to-trough, the earnings-reaction history, the indexed price-vs-earnings
series, forward multiples, the street block and provenance, resolves episode prose
tokens, then dispatches to your module.

### Phase 3 — the loop (must all pass)

```bash
python3 build_deck.py <SYM>          # refuses on stale data
python3 audit_deck.py <SYM>          # must print ALL DECK INVARIANTS PASS
python3 validate_facts.py <SYM>      # must print ALL EPISODE FACTS TRACE
python3 audit_deck.py <SYM> --prove  # must go RED
python3 validate_facts.py <SYM> --prove
python3 export_notes.py <SYM>        # writes Notes/
```

`--prove` deliberately breaks the inputs to confirm the checks can actually fail.
A check that cannot fail is worthless — the episode-prose check was written to
catch `"49x guided revenue"` and its first version matched only `%` and `$`, so it
would have missed the exact bug it existed for. `--prove` is what exposed that.

### Phase 4 — look at it

Publish the deck HTML as an artifact, open with `?theme=cream&audit=1`, read the
audit line, then **step every slide in both themes and in camera mode**
(`?cam=left&camw=26`). Narrowing is what finds latent chart bugs — several charts
passed at 1660px and broke at 1161px.

## Step 3 · Record

- Deck full-screen on the iPad from the artifact URL.
- Intro delivered to camera, full-frame — **no title slide, no price-tape slide**.
  Open on the findings slide; the hook is the promise.
- Camera beside the deck, not over it: `?cam=left&camw=26` reserves the column by
  *padding* the slide, so type stays at its designed size.
- Close by handing off to the Webull chart, not with a price target.

## Step 4 · Post — `/post-video`

```bash
# iPad: run the "Extract Audio" Shortcut on the finished CapCut export → attach M4A
```
```
/post-video   (attach the M4A, say which ticker)
```

Produces chapters, 2–3 titles, the paste-ready description, and a fact-flub report
cross-checking every spoken number against `episodes/<SYM>.json`.

## Step 5 · Commit

```bash
git add -A && git commit -m "NBIS episode" && git push -u origin <branch>
```

---

# WEDNESDAY — the educational episode

```
/learn-stock "how shorting works"
```

1. **Outline the lesson** — 8–19 slides, one idea each. The arc:
   hook → why it matters → the core mechanism → the system/steps → worked example
   → mistakes/guardrails → discipline → recap + next-video hook. Cut any slide
   that doesn't advance the arc.
2. **Write the copy first** as the new `DEFS` array:
   `{id, kicker, head, punch, notes, mount}`.
3. **Design one visual per slide.** Word-slides are the failure mode. 31 proven
   patterns are catalogued in `skills/learn-stock/visuals.md` — 19 in the engine
   plus 12 in `assets/visual-library.html` (gauge, probability tree, compounding
   curve, order book, underwater chart, slope, trajectory, lollipop, waterfall
   bridge, month grid, radar, callout anatomy). Pick from the catalogue first;
   invent new ones with `design-craft` only when nothing fits.
4. **Copy the engine — never rebuild it:**
   ```bash
   cp skills/learn-stock/assets/deck-engine.html "<workdir>/<TOPIC>-deck.html"
   ```
   Then replace exactly two things: the `DEFS` array and the per-slide `v*()`
   mount functions. Tokens, motion, chrome, shortcuts, themes, camera reflow and
   reduced-motion are already correct and verified. Read
   `skills/learn-stock/format.md` first — it is the engine contract.
5. **Build each `v*()` mount** as a pure function of slide-local `t` — the
   engine's model. No CSS animations, no rAF state.
6. **Verify** by publishing as an artifact; step every slide in dark AND cream
   (`T`), camera on AND off (`c`). Label collisions, clipped SVG text and bars
   that outgrow a narrowed column are the recurring bugs.
7. **Deliver** to `output/educational/<TOPIC> <YYYY-MM-DD>/` — deck HTML plus
   `TALKING-POINTS.md`. Commit it.

Copy budgets (same as Sunday): **head ≤ 9 words, punch ≤ 14 words, ~21 words on
screen**. Wrap the 2–3 carrying words of the punch in `<b>`. Everything cut goes
into `notes` (the `N` drawer) — notes are half the deck, write them properly.

---

## Deck keyboard shortcuts (both formats)

| Key | Does |
|---|---|
| `→` / `←` | Next / previous slide |
| `T` | Toggle cream ⇄ dark theme |
| `N` | Presenter notes drawer |
| `c` | Toggle camera mode |
| `⇥` | Step the live calculator (verdict-type slides only) |
