---
name: screener
description: Scan a universe of tickers (watchlist, NASDAQ-100, S&P 500, or a custom list) for names that meet Nikil's long or short trend rules — SMA stack on 4H bars, 2-5% entry zone, 20%+ fade, plus a liquidity-sweep check — using live Alpaca data. Use when he says "run the screener", "screen the market", "what meets our requirements", "find me longs/shorts", or wants a shortlist of candidates rather than a grade on one specific ticker/chart.
argument-hint: [universe: watchlist | nasdaq100 | sp500 | tickers,comma,separated]
---

# Screener — Universe Scan

Finds candidates across many tickers. Produces a **shortlist, never a trade** — every hit still
goes to `/technical-analysis` for the live 6-step grade (SWING CALL + LuxAlgo zone) before he
sizes anything. Never present a screener hit as a TAKE IT.

## THE RULES (identical to /technical-analysis — keep them in sync)

All on **Alpaca 4H bars**.

**LONG trend confirmed when ALL THREE are true:**
1. Price above the 50, 150, AND 200 SMA
2. Stacked: 50 > 150 > 200
3. 200 SMA rising (vs its value 20 bars ago)

**SHORT trend confirmed when ALL THREE are true:**
1. Price below the 50, 150, AND 200 SMA
2. Stacked down: 50 < 150 < 200
3. 200 SMA falling (vs its value 20 bars ago)

**Entry zone decides the trade:**
- **2–5% from the 50 SMA** → trend trade, same direction as the trend
- **20%+ from the 50 SMA** → fade trade, OPPOSITE direction to the trend
- **Anything else** → no trade

There are **no 52-week high/low conditions** — removed 2026-08-18 at his direction, on both sides.
Don't reintroduce them.

**Fade trades are counter-trend — always label them as such.** A fade is deliberately trading
against the SMA stack. Never present one next to trend entries without the distinction being
obvious; a fade mislabeled as a trend trade is exactly what mis-scored the NBIS short.

## LIQUIDITY SWEEP — run on every hit, never optional

Identical definition to `/technical-analysis`. **No chart is available in a screen, so the level is
a 5-bar swing pivot** — a bar whose high is the highest (or low the lowest) of the five bars on
each side. A pivot is only "known" 5 bars after it forms; never use one the market couldn't have
seen yet.

**A valid sweep needs ALL THREE, in order:**
1. **Wick prints THROUGH the level** (below the pivot low on a long, above the pivot high on a
   short). A touch is not a sweep; stalling inside is not a sweep.
2. **Candle CLOSES back through the level.**
3. **The reclaim HOLDS 3+ more bars** without closing back past it. One candle is noise — a
   2026-08-18 backtest put same-day reclaims at the worst hit rate tested (20%, -8.3R) and the
   3-bar-hold version at the best (38.5%).

Report it on every hit: direction (bullish/bearish), the level, and how many bars it has held.
Say "no sweep" explicitly when there isn't one — silence reads as "not checked."

**When sweep and trend disagree:**
- Sweep **beats a fade call** (PSX/VLO, 2026-08-18: extension said fade-short, but both had swept
  a low and held a week — the dip got bought, trend continuing).
- Sweep does **NOT flip a confirmed trend** (PLTR, 2026-08-18: bullish trend + bearish sweep held
  10 bars is still not a short — one rejection in an uptrend is a pause, not a reversal).
- Flag the conflict explicitly in the output either way.

**The sweep signal is rare — expect mostly "no sweep."** Base rate is roughly one signal per
ticker every 9 months (~0.5%/ticker/day). Across ~100 tickers expect ~0-1 hits on a given day;
zero is a normal result, not a broken run. Never treat "no sweep" as a reason to withhold an
otherwise-valid trend hit — report the trend hit and note the sweep is absent.

## ALWAYS report the nearest level BOTH sides, with distances

**Added 2026-08-18.** Every hit reports the nearest level above and below price with % distance —
computed from confirmed 5-bar pivots, never estimated. "No zone nearby" carries no information;
this does:

```
$286.36  ← nearest resistance    +6.2%
$269.59  ← price now
$267.52  ← nearest support       -0.8%
```

This is what showed VRT was a bad short: not "mid-air," but **0.8% above support and 6.2% below
resistance** — about to short straight into the level most likely to bounce it. A hit sitting
right on top of the level it would trade into is worth calling out explicitly, in both directions.

## BREAKOUT / BREAKDOWN — check and flag on every run (added 2026-08-18)

**BOTH DIRECTIONS, equal weight.** Breakdown through support = SHORT setup. Breakout through
resistance = LONG setup. His explicit instruction — do not treat this as short-only.

**What counts as a real break — 1 bar, NOT 3.** Breaks and sweeps use different hold counts; each
was earned on its own backtest. Do not harmonise them.
1. A **full 4H candle CLOSES through the level** — below support (short) or above resistance
   (long). A wick through is not a break.
2. The break **HOLDS 1+ more bar** without closing back through.

Tested 2026-08-18 (30 names, Alpaca 4H, 2026 YTD, 754–1,284 trades per setting — the largest
sample of any test run for him): hold 0 = **−11.88R, the only losing setting**; hold 1 = **+25.79R
(best total)**; hold 2 = +7.61R; hold 3 = +22.66R; hold 4 = +19.09R. Settings 1–4 are
statistically tied on per-trade edge, so take the earliest that works — 1 bar enters 8 hours
sooner on a 4H chart with the stop still tight to the level, across 24% more trades. **The sweep
rule keeps its 3 bars** — that number was earned on reclaims, which behave differently.

**Thin-edge caveat, state it whenever a break is flagged:** avg R ≈ +0.025. Positive but small;
most trades exit on the time stop, not at target.

**Two paths, report which one applies:**
- **Path A — the break itself.** Flag it, never grade it a pass. It sits outside the 6 steps, same
  status as the squeeze flag. Give the numbers and let him decide.
- **Path B — the retest.** Once price returns to the broken level from the other side and gets
  rejected (short) or holds (long), that is a **standard 6-step setup** on the flipped level and
  grades normally.

**When a hit's level is far from price, show what waiting would do to the stop.** VRT on
2026-08-18: shorting at $269.59 stopped off the $300.30 pivot — $37.02/share, 13.6% stop, 5
shares. Waiting for the break of $267.52 stopped off *that* level — ~$10.78/share, ~4% stop, 18
shares, on the same idea. Always surface that comparison rather than only pricing the far level.

**Caveat to state:** breakouts and breakdowns fail often. The only backtest run so far
(squeeze-breakout longs, 2026-08-18) returned 30.6% hit rate / -7.4R over 49 trades — no
demonstrated standalone edge. That's why Path A is a flag, not a pass.

## SQUEEZE / VCP — flag only, never a pass

A range visibly contracting into a flat multi-touch resistance with rising lows. **Not a graded
condition — it cannot make a name a hit, and its absence cannot disqualify one.** Mention it when
a hit also shows one, or when he asks about a specific name that has one but no zone nearby. A
2026-08-18 backtest of squeeze breakouts alone returned 30.6% hit rate / -7.4R over 49 trades —
no demonstrated standalone edge, which is exactly why it stays a flag.

## Run it in stages — cheap filters first

Don't compute everything for every ticker. Each stage runs only on what survived the last:

1. **Stage 1 — pull bars once per ticker** (the expensive part: ~30+ pages each). Do the split
   check and staleness check here and drop anything that fails.
2. **Stage 2 — SMA stack + 200 slope.** Pure arithmetic on bars already in memory, no new calls.
   Most of the universe dies here.
3. **Stage 3 — entry zone** (2–5% or 20%+). Also free. Usually leaves a handful of names.
4. **Stage 4 — liquidity-sweep check on survivors only.** ALWAYS run this, don't skip it and don't
   treat it as optional — he asked for it to be automatic on 2026-08-18 after a run omitted it.
   Pivot detection is O(n) per ticker so it's cheap, but only worth doing on names that already
   passed stages 2–3.
5. **Stage 5 — verification.** One fresh 1-day bar per finalist; drop anything whose price differs
   from the computed price by more than ~3%.

Stages 2–5 add negligible time. The wall-clock cost is stage 1, so the only real lever is
universe size — say so up front if he asks for something large.

## Data source — Alpaca only, hard rule

**Never yfinance/Yahoo, never Webull.** Alpaca's 4H bars matched his real TradingView SMA(200) to
the penny ($510.66 vs $510.67) where both other sources drifted badly.

```
Data endpoint:   https://data.alpaca.markets/v2/stocks/{symbol}/bars
Auth headers:    APCA-API-KEY-ID: <key>
                 APCA-API-SECRET-KEY: <secret>
Params:          timeframe=4Hour, start=<ISO8601, ~420 days back>, limit=10000
Pagination:      loop on next_page_token until null
```

**Credentials live in an environment variable — never in this file, never committed.** If missing
in a session, ask him to set the env var rather than paste them in chat.

**Rate limit: 200 requests/minute.** Sleep ~0.3-0.4s between calls. A 100-ticker run is ~3000
requests across pagination — pace it and run it in the background.

## Four bugs that have already burned us — guard against all four

0. **Verification silently fails pre-market.** The verification pass must request daily bars with
   an explicit `start` date. With no `start`, Alpaca returns `bars:null` before today's daily bar
   exists — so at 8am ET on 2026-08-19 all 101 NASDAQ-100 tickers came back "failed price
   verification" and the run reported zero hits. **Nothing was wrong with the data or the market;
   a missing parameter made a healthy run look empty.** Ask for ~7 days and take the last bar.
   More generally: when a run returns almost nothing, suspect the pipeline before concluding the
   market is quiet — a 99/101 failure rate is a bug signature, not a market signature.

   **Also state the session when running outside regular hours.** Alpaca's 4H grid includes
   extended hours (that's exactly why it matches his TradingView chart to the penny), so a
   pre-market run computes off a thin pre-market bar — AAPL's 4am–8am ET bar on 2026-08-19 traded
   306k shares against millions in a normal session. Don't strip those bars (that would break the
   chart match), but tell him the numbers will move at the open.

1. **Pagination cap too low.** 420 days of 4H bars needs ~30+ pages (~40-50 bars each). An 8-page
   cap silently stopped in Nov 2025 and treated a stale bar as "today," corrupting 85% of a run's
   results (AMD showed $256.60 against a real $484.39). **Loop until `next_page_token` is null,
   and sanity-check the last bar's timestamp is within a few days of now.**
2. **Split contamination.** A stock split anywhere in the pulled window corrupts every SMA computed
   across it. MNST showed a fake 47% "breakdown" from its 2-for-1. **Scan the FULL bar history for
   an adjacent-close ratio of 0.47-0.53 or 1.9-2.1, not just a recent tail window** — the split
   that slipped through was ~24-32 bars back, outside a 15-bar check.
3. **Price verification only checks price, not the SMA.** A name can pass verification (its live
   price is real) while the SMA it's compared against is still split-corrupted. Both checks are
   needed; neither substitutes for the other.

## Universe sources

- **`watchlist`** — his tracked names; ask if not already known this session.
- **`nasdaq100`** — `https://api.nasdaq.com/api/quote/list-type/nasdaq100` (public, no auth).
- **`sp500`** — a maintained constituents list (e.g. the `datasets/s-and-p-500-companies` CSV).
- **custom** — whatever tickers he names.

Ticker LISTS can come from any source — that's just metadata. **Price/bar DATA must always be
Alpaca.**

## Output format

Short. Three buckets, in this order:

**Five independent scans off ONE data pull** — the break and squeeze scans run across the WHOLE
universe, not just trend hits, because a name can be forming a break or a squeeze without sitting
in the 2–5% entry band. Every flag records its trend context so it's never misread as a pass.

1. **Longs** — symbol, price, % from 50 SMA, sweep status, nearest support/resistance + distances
2. **Shorts** — same
3. **Fades** — clearly marked counter-trend, never mixed into the above
4. **Breaks** (own scan) — breakout (long bias) / breakdown (short bias), the level, bars held,
   and the trend context. Flag only, never a graded pass.
5. **Squeezes** (own scan) — flat level, touch count, how much the range contracted, trend
   context. Flag only, never a graded pass.

A hit whose entry sits within ~1% of the level it would trade *into* (a short resting on support,
a long resting under resistance) gets called out explicitly — that's the VRT mistake and it is
invisible unless stated.

Close with: this is a shortlist, run `/technical-analysis` on the real chart before sizing.

## Critical rules

0. **Never assume, never leave a step out, always ask.** Every run does all five stages —
   including the liquidity-sweep check on survivors and the price verification — and reports the
   sweep status on every hit even when it's "none." If something is ambiguous (which universe,
   which rule applies to an edge case, two rules appearing to conflict), **ask him in plain simple
   words** before proceeding. He asked for this explicitly on 2026-08-18 after a run silently
   omitted the sweep layer. A partial run presented as complete is the worst outcome.
1. Never place, modify, or cancel orders.
2. A printed value from his live TradingView chart beats any screener number.
3. Every number must trace to a real Alpaca pull this run — never recall a prior run's numbers as
   current.
4. If a large share of finalists fail verification, say the whole run is unreliable rather than
   presenting a partial list.
