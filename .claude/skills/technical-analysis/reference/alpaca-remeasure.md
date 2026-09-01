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


## Slope sweep, re-run under the breakeven rule (2026-09-01)

`backtest.md`'s slope table was measured on the 1:2 all-out exit — the worst of the three
— so the 1.0% threshold it picked was chosen against a rule no longer traded. Re-swept
under the breakeven rule, over 744 raw episodes before the slope filter:

| slope ≥ | n | +4% | +8% | E(1:1) | E(1:2) | **E(BE)** | $/trade | per mo | $/month |
|---|---|---|---|---|---|---|---|---|---|
| −1.0% | 504 | 49.2% | 25.4% | −0.02R | −0.24R | **+0.02R** | +$1 | 36.0 | +$29 |
| 0.0% | 364 | 50.5% | 25.8% | +0.01R | −0.23R | **+0.04R** | +$2 | 26.0 | +$53 |
| 0.5% | 283 | 49.5% | 27.6% | −0.01R | −0.17R | **+0.04R** | +$2 | 20.2 | +$44 |
| 1.0% | 209 | 53.6% | 32.1% | +0.07R | −0.04R | **+0.16R** | +$8 | 14.9 | +$116 |
| **1.5%** | 146 | 57.5% | 34.9% | +0.15R | +0.05R | **+0.27R** | +$13 | 10.4 | **+$140** |
| 2.0% | 105 | 56.2% | 33.3% | +0.12R | +0.00R | **+0.30R** | +$15 | 7.5 | +$111 |
| 2.5% | 69 | 62.3% | 34.8% | +0.25R | +0.04R | **+0.37R** | +$18 | 4.9 | +$91 |
| **3.0%** | 40 | 65.0% | 37.5% | +0.30R | +0.12R | **+0.48R** | **+$24** | 2.9 | +$69 |

Three things to take from it.

**There is a cliff at 1.0%, not a gradient.** Below it the setup is worth nothing
(+0.02 to +0.04R, against a random baseline of −0.01R). This is the one finding from the
original backtest that survives the rebuild at full strength — the slope filter really is
where the edge lives.

**Above the cliff it is monotonic, which is what makes it trustworthy.** +0.16 → +0.27 →
+0.30 → +0.37 → +0.48. A parameter that improves steadily across its whole range is a
plateau, not a fitted peak. **The gate moves to 1.5%**, and steeper is strictly better
above that, so slope should also rank competing setups.

**Per-trade and per-month disagree, and the monthly column lies.** It reads best at 1.5%
($140/month) only by assuming all 10.4 signals a month get taken. With ~10-day holds and
the 50%-deployed cap he can carry perhaps two positions at once — call it 4–6 trades a
month. Once capacity binds, taking the *steepest available* beats taking the *first
qualifying*, which is again an argument for ranking on slope rather than merely gating.
