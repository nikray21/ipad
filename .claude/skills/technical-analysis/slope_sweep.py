#!/usr/bin/env python3
"""Sweep the SMA slope threshold under every exit rule, including the breakeven one.

The slope table in reference/backtest.md was measured on the 1:2 all-out exit.
That exit is now the worst of the three, so the threshold it picked was chosen
against a rule Nikil no longer trades. This re-sweeps it under all three.

Reads the cached bars written by backtest.py.
"""
import sys, os, json, statistics as st

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import backtest as B

CACHE = os.path.join(HERE, ".cache_bars.json")
if not os.path.exists(CACHE):
    sys.exit("no cached bars — run backtest.py first")
bars = {k: v for k, v in json.load(open(CACHE)).items() if len(v) >= 120}


def slope_at(rows, i):
    c = [r["c"] for r in rows[:i + 1]]
    sma, prev = sum(c[-50:]) / 50, sum(c[-60:-10]) / 50
    return (sma - prev) / prev * 100


# find every signal once at the loosest threshold, tag it with its slope, then
# filter -- so the sweep can look below the skill's default of 1.0%
episodes = []
for sym, rows in bars.items():
    for i in B.signals(rows, slope_min=-99):
        episodes.append((sym, rows, i, slope_at(rows, i)))

MONTHS = 14.0

print(f"{len(episodes)} episodes, {len(bars)} names, "
      f"{min(v[0]['t'][:10] for v in bars.values())} -> "
      f"{max(v[-1]['t'][:10] for v in bars.values())}\n")
print("%-8s %6s %7s %7s %10s %10s %12s %10s %8s %9s" % (
    "slope>=", "n", "+4%", "+8%", "E(1:1)", "E(1:2)", "E(BE rule)",
    "$/trade", "per mo", "$/month"))
print("-" * 97)

rows_out = []
for thr in (-1.0, 0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0):
    sel = [e for e in episodes if e[3] >= thr]
    if len(sel) < 20:
        print("%-8.1f %6d   (too few episodes to read)" % (thr, len(sel)))
        continue
    r4 = [B.barrier(rw, i, 0.04)[0] for _, rw, i, _ in sel]
    r8 = [B.barrier(rw, i, 0.08)[0] for _, rw, i, _ in sel]
    be = [B.barrier_be(rw, i)[0] for _, rw, i, _ in sel]
    h4, h8 = sum(r4) / len(r4) * 100, sum(r8) / len(r8) * 100
    e1 = sum(x - (1 - x) for x in r4) / len(r4)
    e2 = sum(x * 2 - (1 - x) for x in r8) / len(r8)
    eb = sum(be) / len(be)
    per_mo = len(sel) / MONTHS
    rows_out.append((thr, len(sel), eb, eb * 50 * per_mo))
    print("%-8.1f %6d %6.1f%% %6.1f%% %+9.2fR %+9.2fR %+11.2fR %+9.0f %8.1f %+8.0f" % (
        thr, len(sel), h4, h8, e1, e2, eb, eb * 50, per_mo, eb * 50 * per_mo))

best_t = max(rows_out, key=lambda r: r[2])
best_d = max(rows_out, key=lambda r: r[3])
print(f"\nbest PER TRADE : slope >= {best_t[0]:.1f}%  "
      f"({best_t[1]} episodes, {best_t[2]:+.2f}R = ${best_t[2]*50:+.0f}/trade)")
print(f"best PER MONTH : slope >= {best_d[0]:.1f}%  "
      f"({best_d[1]} episodes, ${best_d[3]:+.0f}/month)")
print("\nThese usually disagree: a steeper threshold pays more per trade and fires")
print("less often. The monthly column is the one that pays his bills, but it is also")
print("the one that assumes he takes every signal. Prefer a plateau over a peak.")
