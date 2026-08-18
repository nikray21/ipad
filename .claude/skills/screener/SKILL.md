---
name: screener
description: Scan a universe of tickers (watchlist, S&P 500, NASDAQ-100, or a custom list) for names that meet Nikil's long or short trend/fade rules — Minervini Trend Template on 4H bars, 2-5% entry zone, 20%+ fade — using live Alpaca data. Use when he says "run the screener", "screen the market", "what meets our requirements", "find me longs/shorts", or wants a shortlist of candidates rather than a grade on one specific ticker/chart.
argument-hint: [universe: watchlist | sp500 | nasdaq100 | tickers,comma,separated]
---

# Screener — Universe Scan

Finds candidates across many tickers. This is the "who's worth a closer look" pass — it does NOT
grade a trade. Once a name passes here, hand it to `/technical-analysis` for the real grade (the
live SWING CALL + LuxAlgo 6-step check) before he sizes anything. Never present a screener hit as
a TAKE IT — it's a shortlist, always say so.

## Data source — same hard rule as /technical-analysis

**Alpaca only. Never yfinance/Yahoo, never Webull, never any other reconstruction.** Decided
2026-08-18: Alpaca's 4-hour bars matched his real TradingView chart's SMA(200) to the penny
($510.66 vs $510.67) where Yahoo-hourly-aggregation and Webull's RTH-only bars both drifted by a
wide margin. This is the only source that's been verified to match what he actually trades off.

```
Data endpoint:   https://data.alpaca.markets/v2/stocks/{symbol}/bars
Multi-symbol:    https://data.alpaca.markets/v2/stocks/bars?symbols=A,B,C
Auth headers:    APCA-API-KEY-ID: <key>
                 APCA-API-SECRET-KEY: <secret>
Params:          timeframe=4Hour, start=<ISO8601, ~420 days back>, limit=10000
Pagination:      loop on next_page_token until null -- one call is never the
                 whole dataset, pages have run ~60-300 bars each in practice
```

## CRITICAL — pagination page-limit bug, fixed 2026-08-18, keep the guardrail anyway

A full-universe run on 2026-08-18 returned "prices" wildly off reality for 85% of hits (AMD showed
$256.60 against a real $484.39). Root cause found: the pagination loop capped at **8 pages**, but
420 days of 4H bars needs **~30+ pages** (each page returns ~40-50 bars). At 8 pages the fetch
silently stopped around **2025-11-05** and the code treated that stale last bar as "today's price"
— every downstream number (SMAs, 52-week range) was built on that same truncated window too. Not a
network/proxy issue, not bad Alpaca data — just too low a page cap. **Fix: the pagination loop must
run enough iterations to actually reach the present (50 is generous headroom), and the last bar's
timestamp should be sanity-checked as recent (within a few days) before trusting the pull at all.**

**Keep the verification pass as a permanent safeguard regardless.** Even with the page-limit fixed,
after computing candidates and before presenting ANY of them: re-fetch a fresh 1-day bar for every
symbol that made the long/short/fade lists and confirm the price is within ~3% of what the screener
computed. Drop anything that doesn't match. This is what caught the pagination bug in the first
place — cheap insurance (one extra call per finalist, not per scan) against whatever the next
version of this mistake turns out to be.

**The verification pass only checks price, not the SMA it's compared against — a split can still
sneak past it.** After the pagination fix, the rerun surfaced MNST as a 20%+ fade candidate. Its
CURRENT price passed verification (it matched reality), but the 50-SMA it was measured against was
still built from bars spanning MNST's 2-for-1 split on 2026-08-10/11 — the split-sanity-check only
scanned the last 15 bars (~4 days), and the split was ~24-32 bars back, outside that window.
Verification confirms the price is real; it does NOT confirm the SMA it's being compared to is
clean. **Fix: scan the FULL pulled bar history for a halving/doubling pattern, not just a recent
tail window** — a split anywhere in the lookback corrupts every SMA computed across it, however
long ago it happened within that window.

**Credentials live in an environment variable, never in this file, never committed to the repo.**
If they're not available in a session, ask him to set them in the Claude Code environment's env
vars (outside git) rather than pasting them in chat again.

**Rate limit: 200 requests/minute on his account (measured 2026-08-18).** Every response carries
`X-Ratelimit-Limit` / `X-Ratelimit-Remaining` / `X-Ratelimit-Reset`. For a full-universe run
(hundreds of tickers × several pages each = many hundreds of requests):
- Pace requests — don't fire everything at once. A small sleep between calls (~0.3-0.5s) keeps a
  sustained run comfortably under 200/min without needing to poll the header on every call.
- Check `X-Ratelimit-Remaining` periodically during a long run; back off if it's dropping faster
  than expected rather than waiting to hit a 429.
- A full 500+-ticker screen takes real wall-clock time at this pace (expect several minutes) —
  that's the tradeoff for data that's actually correct. Run it in the background.

## The rules being screened for

Identical logic to `/technical-analysis`'s screening section — this skill exists to *run* it at
scale, not to redefine it. Full detail (why 2-5%, why 20%, the fade rule, the sweep-proxy 4th
layer) lives there; summary below.

**Long — Minervini Trend Template, on 4H bars:**
- Price above the 50-period, 150-period, AND 200-period 4H SMA
- Stacked in order: 50 > 150 > 200
- The 200-period 4H SMA itself trending up (compare to its value 20 bars ago)
- Price within 25% of its 52-week high (measured off 4H bar highs over the last 365 days)
- Price at least 25-30% above its 52-week low
- **Entry zone:** price 2-5% above the 50-period SMA

**Short — the exact mirror, no hedging:** price below all three, stacked downward (50 < 150 <
200), the 200-period SMA declining, within 25% of the 52-week low, 25%+ below the 52-week high,
entry zone 2-5% below the falling 50 SMA.

**Fade — 20%+ from the 50 SMA, opposite direction of the underlying trend:** 20%+ above a rising
SMA gets flagged as a SHORT fade candidate; 20%+ below a falling SMA gets flagged LONG. This is
deliberately counter-trend — label it as such, always, never present it next to trend-following
hits without the distinction being obvious.

**Split sanity check — mandatory before trusting any result.** Flag and exclude any ticker where a
single-bar move is a near-exact halving or doubling (ratio 0.47-0.53 or 1.9-2.1 between adjacent
closes) — that's an unadjusted stock split, not a real move. MNST produced a fake 47% "breakdown"
this way on 2026-08-18 before this check existed.

## Universe sources

- **`watchlist`** — his current tracked names (ask him if not already known this session, or use
  whatever he's most recently referenced as his watchlist).
- **`sp500`** — S&P 500 constituents. No single clean live source; pull from a maintained list
  (e.g. the `datasets/s-and-p-500-companies` GitHub CSV) and cross-check against a broker table if
  anything looks stale.
- **`nasdaq100`** — `https://api.nasdaq.com/api/quote/list-type/nasdaq100` (Nasdaq's own public
  screener API, no auth needed) returns the current constituent list directly.
- **custom list** — whatever tickers he names.

Ticker LISTS (which symbols exist) can come from any reasonable source — that's just metadata.
**Price/bar DATA for the actual screening math must always be Alpaca**, per the hard rule above.

## Output format

Keep it short, same standing preference as `/technical-analysis`. Three buckets:

1. **Longs** — ranked by strongest trend (closest to 52-week high, or steepest 200-SMA slope)
2. **Shorts** — same, mirrored
3. **Fades** — clearly labeled counter-trend, never mixed into the trend lists

For each hit: symbol, price, distance from 50 SMA, and one line of why it qualified. Always close
with: this is a shortlist, not a trade — run `/technical-analysis` on the real chart before sizing
anything, and sanity-check any 30%+ SMA-distance outlier against a stock split before trusting it.

## Critical rules

1. Never place, modify, or cancel orders.
2. A printed value from his actual TradingView chart always beats a screener/API number — if he's
   cross-checking a specific hit against his live chart and they disagree, his chart wins.
3. Every number in the output must trace to a real Alpaca pull — never estimate or recall a prior
   run's numbers as if they were current when asked to "run it" again.
4. Don't editorialize a fade as a trend call or vice versa — the labeling distinction is load-
   bearing, not cosmetic (this is the exact mistake that mis-scored the NBIS short).
