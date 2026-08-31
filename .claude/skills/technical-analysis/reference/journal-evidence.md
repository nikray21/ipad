# What Nikil's own trade log proves

Source: **TRADING_JOURNAL_updated (2).xlsx** in his Drive
(`1SrzWq9UKi6r2aHUfgGe6W7DDtLCUP0zF`). 25 closed trades, all of August 2026,
$5,000 account. Re-read it before a grading session if it has been updated —
these numbers are a snapshot, not a constant.

**Unit note:** these trades were sized with variable stops (avg planned risk $65.09), so
"R" below means *his* planned risk on that trade. Under the current fixed system **1R =
4%** of position value on every trade, which makes the same finding easier to act on: the
avg winner of 0.40R is a trade closed around **+1.6%** against a 4% stop.

**Sample-size warning: 25 trades in one month is suggestive, not proven.** Per-setup
buckets are 1–6 trades each. Treat every "best setup / worst setup" line below as a
prior to lean on, never as a law to quote at him.

## Headline: the entries are fine, the exits are the leak

| | |
|---|---|
| Win rate | **76%** (19W / 6L) |
| Net P&L | +$290.11 (+5.8%) |
| Profit factor | 2.40 |
| Avg planned R:R | **1.81x** |
| Avg *realized* R | **0.22R** |
| Avg win | $26.15 = **0.40R** of the $65.09 he risks |
| Avg loss | $34.45 = **0.53R** |
| Avg days held | **1.0** |

He wins three trades out of four and his average winner is *smaller than his average
loser*. That is not an entry problem. Reconstructing expectancy from those inputs:

```
E = 0.76 × 0.40R − 0.24 × 0.53R = 0.178R
25 trades × 0.178R × $65.09 = $290      ← journal says $290.11 ✓
```

The model ties out to the penny, so the lever is unambiguous:

| If the average winner were… | Expectancy | Same 25 trades |
|---|---|---|
| 0.40R (today) | 0.18R | $290 |
| 0.75R | 0.44R | $721 |
| **1.00R** | **0.63R (3.5×)** | **$1,030** |
| 1.50R | 1.01R | $1,648 |

**At the same 76% win rate, just holding winners to 1R is a 3.5× on the account.**
No new setup, no better entry, no more risk. This is why the rewritten skill spends
as much space on managing an open trade as on grading a new one.

His own words, unprompted:
- HOOD #16 — *"I feel nervous holding for so long… I usually just get scared and take
  the profit right away. need to figure out a better exit strategy."*
- SPCX #18 — *"should've held longer and let it run."*
- INTC #13 — *"just got out to lock in, no real plan on the getting out."*

## The single loss that matters

Six losses: −$4.26, −$14.60, −$25.40, **−$150.00**, −$8.96, −$3.45.

**IREN (#19) is 62% of every dollar he has ever lost**, and it is the only −1.00R in
the book. It was an earnings play on an "SMA bounce": *"I got in too early, i did wait
for a bounce of the 50 sma but should've gotten out when it didn't go my direction with
a small loss but i held the bag… Will need to make it a hard rule to never trade
earnings at all."*

RKLB (#2) was also *"1 day after earnings"* and he tagged it *"bad trade"* despite it
closing green.

→ **Earnings ban is side-agnostic and non-negotiable.** The old skill only gated
earnings on shorts. His worst trade ever was a long.

## By setup

| Setup (his label) | N | Win% | Net | Avg R |
|---|---|---|---|---|
| Bounce off Support Line | 3 | 100% | **+$153.50** | **0.79R** |
| Pullback | 4 | 100% | +$54.70 | 0.30R |
| Upward Momentum | 1 | 100% | +$51.06 | 0.42R |
| Uptrend Parallel Channel | 2 | 100% | +$42.08 | 0.19R |
| Other | 6 | 67% | +$40.23 | 0.11R |
| Breakout | 4 | 50% | +$30.78 | 0.15R |
| **SMA bounce** | **5** | **60%** | **−$82.24** | **−0.02R** |

Two findings, both load-bearing:

1. **This ranking did NOT survive measurement — see `backtest.md`.** Across 50 names and
   14 months the SMA bounce is the *only* pattern with an edge, and requiring a LuxAlgo
   zone added nothing to it. The three "Bounce off Support Line" winners were all SPCX:
   one ticker, three trades, against 93 measured setups. The SMA-bounce losses below came
   from execution — an earnings trade, a flat SMA, no close confirmation — not from the
   pattern. **Trust `backtest.md` over this table.**
2. The five SMA-bounce trades break down as: RKLB +$9 (*"bad trade"*), AMD +$30
   (*"got faked out"*), RIOT +$32, BAC −$3, **IREN −$150**. Four scratches and a
   disaster. The winners were small enough to be noise; the loser paid for everything.

## Structural reads he already uses that the old skill never encoded

- **The 2–5% band.** AAPL loss (#9): *"didnt follow my rule of above 50 sma by 2-5%."*
  CVX win (#10): *"above 3.6% from the 50 sma"* — his only trade tagged
  *"Perfect trade — followed my rules."* He has a distance-from-SMA rule and the skill
  was blind to it.
- **The break candle.** AMD short (#12): *"it's had a long red stick break below of 50
  sma.. also 50 sma is downtrending"* → +0.57R. His cleanest short trigger.
- **Over-extension as a short setup.** NBIS (#11) and AMD (#12) shorts were both
  *"over extended"* off the SMA. The far side of the distance band is where his shorts
  live.
- **Channel rails.** TSLA, COIN, HOOD all reference the upper/lower rail of a parallel
  channel as the actual decision level, not the zone.

## "Got in too early" — four separate confessions

CVX short (#14): *"i should have waited for reversal with a red stick to short it. got
in too early… good lesson to wait for reversal from liquidity before shorting."*
AMD (#8): *"should have waited for the candle to close above the resistance line."*
COIN (#6): *"should've waited for sma break."*
SBUX (#15): *"i should've waited for it to go back up before getting in."*

The close-confirmation rule is **correct and he keeps breaking it**. But note what he
does when the skill says SKIP: he takes the trade anyway, early. A verdict of SKIP reads
to him as *"the idea is dead"*, so he front-runs it rather than lose it.

→ This is the strongest argument for a **WAIT** verdict with an armed trigger price and
the bar-close time. Give him something to *do* at 2:00pm instead of a no.

## Book discipline is where the old rules were being ignored outright

- Old rule: max 2 open positions. Actual: **7 trades opened on 8/28**, 6 on 8/18.
- Old rule: nothing on concentration. Actual: avg position **20.9% of the account**,
  COIN (#17) hit **37.5%** — *"i realized i was almost 40% of my portfolio into this
  stock and it was moving quick so quickly got out."* The size, not the setup, forced
  the exit.
- Risk-per-trade discipline is genuinely good: avg 1.3% of account, **stop honored
  100% of the time**, zero trades over planned risk. He is not a reckless sizer; he is
  a reckless *concentrator* and an over-trader on bad days.

→ Cap risk, cap concentration, cap trades-per-day, add a daily circuit breaker. Drop
the 2-position rule he has never once followed.

## Horizon mismatch

Avg hold is **1.0 day** against a 4h *swing* playbook targeting 2R. He closes for
reasons unrelated to the chart: *"it's friday not trying to hold"*, *"didn't want to
hold over weekend"*, *"had to sell on market close because on flight."*

Don't fight this. Set the target at the **first** opposing zone he can realistically
reach inside his horizon, and if that target is under 1.5R, the answer is WAIT for a
better entry — not a 2R target he will abandon at +0.5%.

## He grades himself

The log has a **Self Assess score (1–10)**, averaging 5.5. The rewritten scorecard uses
the same 1–10 scale so his grade and the skill's grade sit in the same column and
diverge visibly when he is kidding himself.

## One caution on trusting the machine

SBUX (#15): *"claude recommended trade… big problem found - claude had wrong number
from yfinance and webull so had to reconfigure everything to alpaca… claude made a
mistake and i got stopped out for a loss."*

Every number in a grade traces to his chart or a live-verified quote. When a value is
unreadable, **ask** — never infer a price from memory or a stale feed.
