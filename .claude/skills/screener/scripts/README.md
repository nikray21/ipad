# Screener scripts

The working engine behind `/screener` and the SMA/level math in
`/technical-analysis`. `SKILL.md` is the spec; this is the implementation.

## Setup

Alpaca credentials come from the environment — never hardcoded, never committed:

```bash
export APCA_API_KEY_ID=...
export APCA_API_SECRET_KEY=...
```

In a cloud session set these in the environment's env-var settings so they
persist between sessions. The scripts exit with a clear message if they're missing.

## Files

| File | What it does |
|---|---|
| `full_check.py` | The engine. `analyze(symbol)` returns trend template, entry zone/fade signal, liquidity sweep, breakout/breakdown, squeeze, levels both sides, ATR, and the price-verification result. |
| `run_screener.py` | Runs the five scans over a ticker list, one data pull each. |

## Usage

```bash
# one or more tickers, full detail
python3 full_check.py VRT,SBUX,PLTR

# universe scan -> JSON with trendHits / breaks / squeezes / dropped
python3 run_screener.py tickers.json out.json
```

`tickers.json` is a plain JSON array: `["AAPL", "MSFT", ...]`.

## Tuned parameters and why

Every number here was set by a backtest or a failure, not by taste. Don't
change them without re-testing.

| Parameter | Value | Why |
|---|---|---|
| Break `hold` | 1 bar | 30 names, 4H, 2026 YTD, 754–1,284 trades/setting: hold 0 = −11.88R (only loser), 1 = +25.79R (best total), 2 = +7.61R, 3 = +22.66R, 4 = +19.09R. 1–4 tie per-trade, so take the earliest. |
| Break `k` | 10 | 5-bar fractals litter the chart with minor pivots. At k=5 the scan flagged 88 of 97 NASDAQ-100 tickers (91%) — noise, not signal. |
| Break `decisive` | 1.0 × ATR | A hairline close through a level isn't a break. |
| Break `window` | 5 bars | Only recent breaks are actionable; a 12-bar-old break still holding is just "price is trending." With k=10 + 1×ATR + window=5 the hit rate fell to ~10%. |
| Sweep hold | 3 bars | Its own backtest: same-day reclaim 20% / −8.3R, 3-bar hold 38.5%. **Different from the break hold on purpose — do not harmonise.** |
| Pagination | loop to null | An 8-page cap silently stopped in Nov 2025 and treated a stale bar as "today," corrupting 85% of a run. |
| Split check | full history | A split anywhere in the window corrupts every SMA across it (MNST's 2-for-1 produced a fake 47% breakdown). |
| `latest_price` start | 7 days | Without an explicit `start`, Alpaca returns `bars:null` pre-market — which made all 101 tickers "fail verification" at 8am ET on 2026-08-19. |

## Known limitation

Runs outside regular hours compute off thin extended-hours bars (AAPL's 4–8am ET
bar: 306k shares vs millions intraday). Those bars stay in — stripping them would
break the match with his TradingView chart, which is the reason Alpaca was chosen —
but say so in the output, since the numbers move at the open.
