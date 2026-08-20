"""trade_setup.py — the measurable half of the 6-step swing playbook.

`technical-analysis` used to grade a trade off a TradingView screenshot: zone
edges, volume labels, ATR and the 50 SMA all read by eye. Every one of those is
a number the pipeline can derive, and misreading any of them silently moves the
stop. This computes them.

What it does NOT compute is the SWING CALL line. That is a paid LuxAlgo toolkit
signal — it is not in the public Library (`library_search` finds no such slug),
so there is no source to port and no honest proxy for it. It stays a one-word
input: pass `--swing green|red|flat`. The 50 SMA half of step 1 is computed, so
a missing SWING CALL only leaves that one condition ungraded rather than the
whole gate.

Everything else in the checklist becomes arithmetic:

  step 1  price vs 50 SMA, and the SMA's own slope
  step 2  is price inside a live zone, and how that zone's volume ranks
          against the other live zones — "heavy" is relative, as the skill says
  step 3  sweep vs stall, as the two numbers side by side: the extreme price
          actually printed at the zone against the edge it had to exceed
  step 4  whether a closed bar has closed back through the zone
  step 5  Level +/- 1.5 x ATR, off the LEVEL — and whether a stop he already
          has sits inside the wiggle zone
  step 6  target in front of the next opposing zone, and the R:R that implies

Pivot lookback defaults to 7, not the indicator's 14: 7 is what reproduced his
actual NBIS chart (see liquidity_swings.py). Override with --length if he
changes the setting.

    python3 trade_setup.py NBIS --side short --swing red --budget 100
"""

import argparse
import json
import sys

import liquidity_swings as ls


def atr(bars, period=14):
    """Wilder's RMA of true range, which is what TradingView's ta.atr is.

    A plain mean of the last 14 true ranges runs several percent off and would
    move every stop by that much.
    """
    trs = [max(b["h"] - b["l"], abs(b["h"] - p["c"]), abs(b["l"] - p["c"]))
           for p, b in zip(bars, bars[1:])]
    if len(trs) < period:
        return None
    a = sum(trs[:period]) / period
    for tr in trs[period:]:
        a = (a * (period - 1) + tr) / period
    return a


def sma(bars, period=50, back=0):
    """Simple MA of closes, `back` bars ago."""
    i = len(bars) - 1 - back
    if i + 1 < period:
        return None
    return sum(b["c"] for b in bars[i - period + 1:i + 1]) / period


def last_visit(bars, zone):
    """The most recent unbroken run of bars touching the zone.

    Restricted to the latest run on purpose: a sweep that happened two months
    ago says nothing about the setup in front of him now.
    """
    hits = [i for i in range(zone["pivot_i"] + 1, len(bars))
            if bars[i]["l"] < zone["top"] and bars[i]["h"] > zone["btm"]]
    if not hits:
        return []
    run = [hits[-1]]
    for i in reversed(hits[:-1]):
        if i != run[0] - 1:
            break
        run.insert(0, i)
    return run


def grade(bars, side, entry=None, budget=100.0, length=7, area="wick",
          min_vol=1e6, stop=None, swing=None):
    """Every step-by-step number the grader needs, as a dict. No verdicts.

    Returning facts rather than pass/fail keeps the judgement in the skill,
    where the qualitative half of the checklist lives.
    """
    zones = ls.swing_zones(bars, length, area, "volume", min_vol)
    price = bars[-1]["c"]
    entry = price if entry is None else entry
    below, above = ls.nearest_zones(zones, price)
    long_ = side == "long"
    zone, opp = (below, above) if long_ else (above, below)

    a = atr(bars, 14)
    ma = sma(bars, 50)
    prior = sma(bars, 50, back=6)
    live = [z for z in zones if z["shown"] and not z["taken"]]

    out = {
        "side": side, "price": price, "entry": entry, "bars": len(bars),
        "length": length, "atr14": a, "sma50": ma,
        "swing_call": swing,
        "above_sma50": (price > ma) if ma else None,
        "sma50_slope": None if not (ma and prior) else (
            "rising" if ma - prior > price * 0.0005 else
            "falling" if prior - ma > price * 0.0005 else "flat"),
        "zone": zone, "opposing_zone": opp, "live_zones": len(live),
    }

    if zone is None:
        out["error"] = f"no live {'demand' if long_ else 'supply'} zone " \
                       f"{'below' if long_ else 'above'} {price:.2f} over {min_vol:,.0f} volume"
        return out

    # step 2 — "heavy" is relative to the other zones on the chart, not absolute
    ranked = sorted(live, key=lambda z: -z["volume"])
    out["vol_rank"] = ranked.index(zone) + 1
    out["in_zone"] = zone["btm"] <= price <= zone["top"]

    # step 3 — sweep prints THROUGH the edge; stall halts inside it
    run = last_visit(bars, zone)
    if run:
        edge = zone["btm"] if long_ else zone["top"]
        extreme = min(bars[i]["l"] for i in run) if long_ else max(bars[i]["h"] for i in run)
        out["visit"] = {
            "bars": len(run),
            "ended_bars_ago": len(bars) - 1 - run[-1],
            "extreme": extreme,
            "edge_to_beat": edge,
            "swept": (extreme < edge) if long_ else (extreme > edge),
            "missed_by": abs(edge - extreme),
        }
    else:
        out["visit"] = None

    # step 4 — a close is real, a wick is not. Only meaningful while price is
    # still at the zone: NBIS closed "back below" a 280 zone from 223, which is
    # a crash that already happened, not a trigger to short.
    trigger_edge = zone["top"] if long_ else zone["btm"]
    last, lb = bars[-1]["c"], bars[-1]
    out["trigger"] = {
        "edge": trigger_edge, "last_close": last,
        "closed_back": (last > trigger_edge) if long_ else (last < trigger_edge),
        "at_zone": lb["l"] < zone["top"] and lb["h"] > zone["btm"],
        "distance": 0.0 if zone["btm"] <= last <= zone["top"] else
                    min(abs(last - zone["btm"]), abs(last - zone["top"])),
    }

    # step 5 — off the LEVEL, never off entry
    level = zone["btm"] if long_ else zone["top"]
    st = (level - 1.5 * a) if long_ else (level + 1.5 * a)
    risk = (entry - st) if long_ else (st - entry)
    out["level"], out["stop"], out["risk_per_share"] = level, st, risk
    out["shares"] = int(budget // risk) if risk > 0 else 0
    out["budget"] = budget
    if risk <= 0:
        out["error"] = "entry is already through the stop — no trade to size"
    if stop is not None:
        # the classic Entry -/+ 1.5 x ATR mistake parks the stop on the level
        out["his_stop"] = stop
        out["stop_is_noise_bait"] = (stop > level - 1.5 * a) if long_ else (stop < level + 1.5 * a)

    # step 6 — target goes in FRONT of the next opposing zone
    if opp is not None and risk > 0:
        target = opp["btm"] if long_ else opp["top"]
        reward = (target - entry) if long_ else (entry - target)
        out["target"], out["reward_per_share"] = target, reward
        out["rr"] = reward / risk
    return out


def _line(z):
    return f"{z['btm']:.2f}-{z['top']:.2f} ({ls.fmt_vol(z['volume'])})" if z else "none"


def report(g):
    y = lambda b: "yes" if b else "no"
    p = print
    p(f"{g['symbol']}  {g['tf']}  {g['side'].upper()}  {g['bars']} bars"
      f"   lookback {g['length']}   last close {g['price']:.2f}")
    p(f"  ATR14 {g['atr14']:.2f}   50 SMA {g['sma50']:.2f} ({g['sma50_slope']})")
    p()
    p(f"1 trend      price {'above' if g['above_sma50'] else 'BELOW'} 50 SMA, SMA {g['sma50_slope']}"
      f"   |  SWING CALL: {g['swing_call'] or 'NOT SUPPLIED — ungraded'}")
    if g.get("error"):
        p(f"\n  {g['error']}")
        return
    p(f"2 location   zone {_line(g['zone'])}   price inside: {y(g['in_zone'])}"
      f"   volume rank {g['vol_rank']} of {g['live_zones']} live")
    v = g["visit"]
    if v:
        p(f"3 trap       printed {v['extreme']:.2f} against {v['edge_to_beat']:.2f}"
          f"   {'SWEPT' if v['swept'] else 'STALL — never left the box'}"
          f" (by {v['missed_by']:.2f}), {v['bars']} bars, ended {v['ended_bars_ago']} bars ago"
          + ("" if v["ended_bars_ago"] <= 1 else " — stale, not this setup"))
    else:
        p("3 trap       price has not visited this zone since it formed")
    t = g["trigger"]
    p(f"4 trigger    last close {t['last_close']:.2f} vs zone edge {t['edge']:.2f}"
      f"   closed back through: {y(t['closed_back'])}")
    if not t["at_zone"]:
        p(f"             not a live trigger — price is {t['distance']:.2f} away from the zone")
    p(f"5 stop       Level {g['level']:.2f}  -/+ 1.5 x ATR ({1.5 * g['atr14']:.2f})"
      f"  =  STOP {g['stop']:.2f}")
    p(f"             risk/share {g['risk_per_share']:.2f}"
      f"   shares {g['shares']} on ${g['budget']:.0f}")
    if "his_stop" in g:
        p(f"             his stop {g['his_stop']:.2f} vs the {g['stop']:.2f} the level demands — "
          + ("NOISE BAIT, it is not clear of the level" if g["stop_is_noise_bait"]
             else "clear of the level"))
    if "rr" in g:
        p(f"6 exit       target {g['target']:.2f} in front of {_line(g['opposing_zone'])}"
          f"   reward/share {g['reward_per_share']:.2f}   R:R {g['rr']:.2f}"
          f"  {'PASS' if g['rr'] >= 2 else 'FAILS the 2R bar'}")
    else:
        p(f"6 exit       no opposing zone to target — {_line(g['opposing_zone'])}")


def main():
    ap = argparse.ArgumentParser(description="Compute the 6-step playbook numbers for a trade")
    ap.add_argument("symbol")
    ap.add_argument("--side", default="long", choices=("long", "short"))
    ap.add_argument("--tf", default="4h", choices=("4h", "1h", "1d"))
    ap.add_argument("--entry", type=float, help="his entry; defaults to last close")
    ap.add_argument("--budget", type=float, default=100.0, help="dollar risk budget (default 100)")
    ap.add_argument("--stop", type=float, help="a stop he already has, to check against the level")
    ap.add_argument("--swing", choices=("green", "red", "flat"),
                    help="SWING CALL line colour, read off his chart — the one input left")
    ap.add_argument("--length", type=int, default=7, help="pivot lookback (his chart runs 7)")
    ap.add_argument("--area", default="wick", choices=("wick", "full"))
    ap.add_argument("--min-vol", type=float, default=1e6,
                    help="zone volume floor, the chart's Volume filter (default 1M)")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    sym = a.symbol.upper()
    bars = ls.load_bars(sym, a.tf)
    g = grade(bars, a.side, a.entry, a.budget, a.length, a.area, a.min_vol, a.stop, a.swing)
    g["symbol"], g["tf"] = sym, a.tf
    print(json.dumps(g, indent=1)) if a.json else report(g)


if __name__ == "__main__":
    sys.exit(main())
