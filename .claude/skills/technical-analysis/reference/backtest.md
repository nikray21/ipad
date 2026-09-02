# What was actually measured

**Universe:** 50 liquid US names (his journal tickers + common swing names).
**Data:** 600 × 4h RTH bars each, 2025-06-18 → 2026-08-31 (~14 months), Webull.
**Method:** signal at a 4h bar close; entry at that close; barrier test to +target / −4%.
Consecutive signal bars in the same name collapsed into **one independent episode**
(6-bar gap), because raw signal bars badly overstate n. Bars where the high and low
both crossed a barrier are counted as ambiguous and split 50/50.
**Run:** 2026-08-31. Scripts were scratch; re-derive rather than trusting these numbers
if the market regime has clearly changed.

## Headline

The **rising-50-SMA bounce** is the only pattern tested that shows a durable edge.

> Eligible name (4h bar range 1.5–3.0%) · SMA slope ≥ +1% over 10 bars ·
> bar low touches the SMA and closes back above it · close within 2.5% of the SMA

| | |
|---|---|
| Setups | **93** over 14 months, across **32** different names |
| Reaches +4% | **64%** |
| Reaches +8% | **48%** |
| Expectancy at 1:2 | **+0.44R ≈ +$22/trade** at $50 risk |
| Frequency | ~6.6/month on a 50-name list |
| Concentration | busiest name 9 of 93 = 10% |

Split by period: first 8 months +0.35R, last 6 months +0.55R. Both positive.

## Every trigger tested (long, uptrend)

| Trigger | n | +4% | +8% | E at 1:2 |
|---|---|---|---|---|
| **SMA bounce** | 397 | 56% | 38% | **+0.14** |
| SMA reclaim | 310 | 56% | 35% | +0.05 |
| Buy strength (no pullback) | 334 | 52% | 34% | +0.03 |
| Zone reclaim (LuxAlgo) | 527 | 51% | 33% | 0.00 |
| Sweep reclaim | 206 | 49% | 32% | −0.05 |
| *random entry baseline* | 1200 | 52% | 31% | −0.07 |

Only the SMA bounce clears the baseline meaningfully. Adding the volatility band takes it
to 43% / +0.29, and the slope filter to 48–54% / +0.44–0.61.

## The findings that changed the skill

**1. The 6-bar time stop was destroying the edge.** Winners take a median of **9 bars
(4.5 trading days)** to reach +8%; the 80th percentile is 18 bars. Losers hit the stop in
a median of 4 bars — so the trade tells you it's wrong fast, but takes its time being
right.

| Time stop | +8% hit | Expectancy |
|---|---|---|
| 6 bars | 37% | +$6 |
| 10 bars | 45% | +$17 |
| 16 bars | 46% | +$20 |
| **20 bars** | **48%** | **+$22** |
| 30 bars | 50% | +$25 |

His logged average hold is **1.0 day**. That single habit is the difference between a
working system and a pointless one.

**2. LuxAlgo zones are not an entry filter.** Requiring a live zone within 2% of the SMA
cut 91 setups to 68 at identical expectancy (+0.46 → +0.48). Within noise. Zones were
demoted to target-finding and context. This contradicts his journal, where "Bounce off
Support Line" looked like his best setup — but that was 3 trades in one ticker (SPCX).

**3. His journal's "worst" setup is actually his best.** SMA bounce showed −$82 over 5
logged trades. Across 50 names it is the only pattern with an edge. The logged losses
came from execution — an earnings trade, no close confirmation, a flat SMA — not from the
pattern.

**4. The slope filter is where most of the edge lives.** A merely-rising SMA is not
enough:

| Slope over 10 bars | n | +8% | E |
|---|---|---|---|
| > 0.0% | 152 | 41% | +0.24 |
| > 0.5% | 127 | 42% | +0.27 |
| **> 1.0%** | 91 | 49% | **+0.46** |
| > 1.5% | 57 | 54% | +0.61 |
| > 2.0% | 37 | 53% | +0.58 |

A plateau, not a spike — the effect survives moving the threshold, which is what makes it
credible. 1.0% was chosen over 1.5% to keep n usable; 1.5% is the A-grade cut.

**5. The volatility band is real.** Best at 1.5–3.0%/bar, degrading either side:

| Band | n | +8% | E |
|---|---|---|---|
| 1.0–2.0% | 43 | 37% | +0.11 |
| 1.2–2.5% | 50 | 44% | +0.33 |
| **1.5–3.0%** | 57 | 54% | **+0.61** |
| 1.5–3.5% | 75 | 49% | +0.46 |
| 2.0–4.0% | 71 | 44% | +0.33 |

Mechanism: below the band the name can't cover 8% in the horizon (BAC, CVX, MCD, SBUX,
MSFT managed it in **zero** of 70 six-bar windows); above it, a 4% stop is roughly one
candle of noise (IREN 3.7%/bar, RIOT 4.0%, NBIS 3.6%, COIN 3.3%, HOOD 3.1%).

**6. Don't chase the entry.** Close within 2.5% of the SMA: 52% / +0.56. No cap: 49% /
+0.46. Within 1.5%: worse (+0.32) — too tight, it filters out good bounces.

**7. The 1:2 runner beats the 1:1 scalp decisively.** +0.44R vs +0.20R on identical
entries. Scaling a third at +4% costs nothing measurable (+0.45 vs +0.46) and buys the
psychological ease that makes holding possible.

**8. Shorts show no edge.** The mirror setup, same universe:

| Slope | n | +4% | +8% | E at 1:2 |
|---|---|---|---|---|
| < −0.5% | 113 | 52% | 34% | +0.01 |
| < −1.0% | 84 | 52% | 35% | +0.05 |
| < −1.5% | 54 | 47% | 27% | −0.19 |
| < −2.0% | 35 | 41% | 24% | −0.27 |

It gets *worse* as the downtrend steepens — the opposite of the long side. Capped at
starter size in the skill.

## What this does not prove

- **One regime.** 14 months, broadly a bull tape. A sustained bear market was not tested
  and the long-only edge would likely suffer.
- **n is small where it's most flattering.** The +0.61R variant rests on 57 episodes.
  The skill uses the wider, lower-expectancy cut on purpose.
- **Parameters were swept, then chosen.** Overfitting risk is real. It is mitigated by
  preferring plateaus over peaks, checking both time halves, and capping name
  concentration — not eliminated.
- **No fees, no slippage, no gaps.** Entry assumed at the exact 4h close.
- **The zone proxy is a proxy.** Pivot highs/lows with a 3-bar lookback, box = pivot bar
  range, live until a close breaks it. Close to Liquidity Swings in spirit, not identical.
  The "zones add nothing" conclusion is only as good as the proxy.
- **SWING CALL was never tested** — no data for it. It is not part of any measured claim.

## Expected performance, stated honestly

~6.6 setups/month × +$22 = **~$146/month ≈ 2.9%/month on the account size in his journal**, before fees
and slippage, if he takes most signals and holds them ~10 days. That is a good outcome
and roughly double his logged +$11.60/trade. It is a backtest estimate, not a promise —
and it collapses to about +$6/trade if he keeps closing on day one.
