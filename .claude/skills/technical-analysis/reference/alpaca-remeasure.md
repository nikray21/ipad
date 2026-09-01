# Re-measurement on Alpaca, 2026-09-01

**Why this exists.** The original backtest ran on Webull bars with scratch scripts that
were not kept. This is an independent rebuild on Alpaca SIP data, with a random-entry
control run on the same bars, the same period and the same bar construction — so the
comparison is apples to apples rather than against a number quoted from another run.

**Data:** 100 names, 4h RTH bars folded from 30-minute SIP bars (session splits at noon
ET), 2025-06-30 → 2026-09-01. **Method:** signal at a 4h close, entry at that close,
barrier test to the target or −4%, 20-bar time stop, consecutive signals in one name
collapsed on a 6-bar gap, a bar trading through both barriers counted as half.
**Reproduce:** `python3 backtest.py` (bars cache to `.cache_bars.json`).

## The exit comparison — this is the finding that matters

| Exit rule | reaches target | expectancy | median bars | per trade @ $50 risk |
|---|---|---|---|---|
| +4% all-out (1:1) | 53.2% | +0.06R | **4 bars (2.0 days)** | +$3 |
| +8% all-out (1:2) | 31.9% | −0.04R | 7 bars (3.5 days) | −$2 |
| **+4% → breakeven, then run** | 26.4% to +8% | **+0.14R** | 7 bars | **+$7** |

**The breakeven stop is the best of the three, and it is not close.** Moving the stop to
breakeven at +4% costs 5.5 points of win rate (31.9% → 26.4% reach +8%) and buys 27
points of loss rate (68.1% → 41% take a full stop; 25% scratch instead). That trade is
strongly positive, and it is the opposite of what the old skill assumed when it treated
the breakeven stop as a psychological concession that "costs nothing".

Two supporting numbers:

- **+4% arrives in a median of 4 bars — 2.0 trading days.** Reaching the point where the
  trade goes free is a two-day wait, not a ten-day one.
- **Losers hit the stop in a median of 4 bars too.** The trade tells you it is wrong as
  fast as it tells you it is right.

## Does the setup beat random? Yes, but by less than claimed

| Cut | n | +4% | +8% | E(1:1) | E(1:2) |
|---|---|---|---|---|---|
| **RANDOM entry (control)** | 1296 | 49.5% | 27.0% | −0.01R | −0.19R |
| A-setup, slope ≥ 1.0% | 216 | 53.2% | 31.9% | +0.06R | −0.04R |
| A-setup, slope ≥ 1.5% | 146 | 57.5% | 34.9% | +0.15R | +0.05R |
| A-setup, his original ~50 names | 119 | 54.6% | 38.7% | +0.09R | +0.16R |

The setup clears the control on every cut, and **the slope filter is monotonic** — ≥1.5%
beats ≥1.0% on all four measures. Both findings survive the rebuild.

## Where this disagrees with `backtest.md`, and what to do about it

`backtest.md` reports **64% / 48% / +0.44R** on 93 episodes. This run measures **53% /
32% / +0.06R** on 216. Both cannot be right, and the gap is roughly a factor of two.

Checks already done: his original ~50-name universe was measured separately and does
**not** close the gap (54.6% / 38.7%); the period matches within two weeks; the Alpaca
bars were validated against the earlier source to within pennies on closes and SMAs. So
universe, period and data source do not explain it.

The likeliest remaining cause is **in-sample optimism in the original**: 397 raw signals
were cut to 93 by filters chosen after looking at the same data, across three or four
swept parameters. `backtest.md` says as much in its own "What this does not prove"
section. A second possibility is a defect in either implementation; this one is in the
repo and can be read, which the original scripts cannot.

**Until that is resolved, plan on the numbers in this file, not the older ones.** They
are the conservative pair, they come with a control, and they are reproducible. Concretely:

- Expect roughly **+$7/trade**, not +$22. The edge is real; it is about a third of what
  the skill has been claiming.
- Prefer the **slope ≥ 1.5%** cut. It is where the edge actually concentrates, and the
  1.0% threshold was chosen to keep n usable rather than because it pays.
- The 15-trade validation block should compare against **53% reaching +4%**, not 64%.
  Against the old baseline he would conclude the system is broken when it is behaving
  exactly as measured.
