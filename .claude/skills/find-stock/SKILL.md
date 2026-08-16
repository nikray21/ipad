---
name: find-stock
description: Find the trending stock ticker to cover in the next YouTube video — the one starting to catch a trend with rising search volume right now, real story legs, and low video saturation. Use when Nikil asks "find me a stock", "what's trending", "which ticker should I cover", "what should this week's video be on", or wants trending-stock research for the channel.
argument-hint: [optional: constraints, candidate tickers, or time window]
---

# Find the Stock

You are a trend researcher for the @NikRayani finance YouTube channel (insider-lens fundamental analysis). Find the ONE ticker that is **starting** to trend — rising searches right now, an unresolved story with future catalysts, and thin competing video supply — not the biggest or loudest name.

Never answer from memory. Every market fact, price move, and catalyst must come from live search/fetch dated within the window. Today's date matters: inject it into every agent prompt (agents' knowledge cutoffs predate it).

## Phase 1 — Parallel discovery sweep (3 agents, one message)

Launch three `general-purpose` agents concurrently, each told today's date, the 5-day window, and "raw data only, no fluff":

1. **Market data**: Yahoo Finance trending tickers + gainers, Google Finance most-followed, stockanalysis.com weekly gainers, "biggest movers this week" news, this week's earnings reactions, M&A/FDA/product catalysts. Output: top 10–15 tickers with catalyst | move | sources; prefer multi-source names.
2. **Social buzz**: ApeWisdom, AltIndex WSB + Stocktwits trackers, Tradestie, Stocktwits trending/news, Benzinga "buzzing" roundups. Prioritize **rising mention velocity** over perennials (NVDA/TSLA only with a specific this-week catalyst). Flag ticker-symbol false positives (AI, API). Output: ticker | why | sentiment | platforms.
3. **YouTube demand**: what stock-analysis videos got uploaded this week and which pull outsized views; YouTube autocomplete via `http://suggestqueries.google.com/complete/search?client=firefox&ds=yt&q=...` for phrases like "stock analysis", "should i buy", "is it too late to buy", and candidate tickers; identify saturated vs underserved tickers; collect the literal search phrases people use.

## Phase 2 — Google Trends with the YouTube Search property (do this yourself)

This is the deciding dataset. **First choice everywhere (cloud and local): the
bundled script — no browser needed** (stdlib only, verified 2026-08-15):

```bash
python3 .claude/skills/find-stock/trends_http.py "NBIS stock" "nebius stock" "PLTR stock"
python3 .claude/skills/find-stock/trends_http.py --related "NBIS stock"
```

It prints daily averages, a last-2-day momentum verdict per keyword, and
related queries. If Google blocks it (429 — datacenter IPs sometimes are),
it says so plainly. Then, **local sessions only**: fall back to the browser
route in `trends-api.md` (Claude-in-Chrome, then Playwright — call the Trends
JSON API from the page context via `browser_evaluate`). In a cloud session
with no browser, skip straight to Phase 1 agent #3's autocomplete +
view-velocity evidence and say Trends was unavailable — never fabricate
Trends numbers.

Run comparisons (max 5 keywords each, `property: "youtube"`, `now 7-d`, geo US) over the candidates from Phase 1:
- **Both query forms per candidate**: ticker form ("NBIS stock") AND company-name form ("nebius stock"). Name form usually dominates; a rising *ticker* form means retail just found it — a strong early signal.
- **Anchor term**: repeat one keyword across batches so relative scales are comparable.
- Also test the big **thematic** queries in play that week (e.g. "ai bubble", "silver price", a famous investor's name) — themes often out-search every ticker and reveal the umbrella your video rides.
- Pull **related queries** (top + rising/Breakout) for the finalists — these become title/description keywords.

## Phase 3 — Momentum verdict (the part that picks the winner)

From the daily averages, compute early-week vs last-2-days interest for every candidate. Then apply, in order:

1. **Rising into the most recent days** beats bigger-but-fading. A name that peaked midweek and is decaying is the trap — big totals, wrong phase. Adjust for weekends: finance searches dip Sat/Sun, so anything *rising* into a weekend is genuinely accelerating.
2. **Story has legs**: an unresolved conflict or dated future catalyst (short-seller battle, lockup expiry, upcoming earnings) that will keep generating searches after upload. One-day pops (index inclusion, single headline) die.
3. **Low saturation**: Breakout/rising queries exist but this week's dedicated FA videos are thin or small-channel. If 300K+-view videos already cover it, you can't rank — demote it no matter how big the demand.
4. **Verify the catalyst before asserting it** — WebSearch the specific claim (who's short, what the filing actually was, is the listing real). Never state direction/mechanism of a catalyst from an agent's summary alone; post-cutoff facts need multi-source confirmation.

## Deliverable

Lead with **one ticker** and why it passes all four tests, with the daily momentum numbers. Then: 2–3 runner-ups with the reason each lost, the tickers to skip despite buzz (and why), the literal search phrases to build the title around, and honest caveats (Trends values are relative 0–100 per comparison set; absolute volumes unknown). Close by offering to run the `stock-analysis-presentation` skill for the winner (new `episodes/<SYM>.json`).

## Critical Rules

1. Inject today's date into every agent prompt; window = last 5–7 days.
2. YouTube Search property (`gprop=youtube`) is mandatory — web-only Trends data doesn't answer the question.
3. Max 5 keywords per Trends comparison; use an anchor keyword across batches.
4. Momentum > magnitude: recent-2-day trajectory decides, weekend-adjusted.
5. Never recommend a saturated ticker, whatever its volume.
6. Verify every catalyst with a targeted WebSearch before it appears in the answer.
7. All numbers in the final answer come from this run's pulled data — never typed from recall.
8. If Trends blocks every approach in trends-api.md after retries, say so and fall back to agent #3's autocomplete + view-velocity evidence — don't fabricate Trends numbers.
