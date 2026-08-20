"""liquidity_swings.py — Liquidity Swings [LuxAlgo], computed instead of screenshotted.

The `technical-analysis` skill grades a trade on where price sits relative to
LuxAlgo's swing zones, and until now those zones were read off a TradingView
screenshot by eye. This is the same algorithm in Python, run against bars
from `alpaca_data.py`, so a zone's edges are numbers the pipeline derived
rather than numbers someone squinted at.

Bars come from Alpaca and nowhere else — a hard rule, not a preference. A
first pass ran on `marketdata.py`'s Yahoo-backed history, and it looked
right without being right: zone sequence and rough price levels matched a
real TradingView chart (checked against NBIS, then again against AMD), but
Yahoo's own OHLCV disagrees with the feed Nikil trades against by enough to
occasionally pick a different bar as the pivot extreme, which moves a zone
edge exactly where a stop gets placed. Alpaca is the vendor whose bars are
close enough to his chart's feed to trust the edges. Volume is a separate
problem — the label each zone carries is deliberately not authoritative
right now (see "What this doesn't do" below) — so this module answers
*where the zones are*, not how much traded inside them.

Ported from the published Pine v6 source (fetched via the LuxAlgo MCP server,
`library_get_source_code` for slug `liquidity-swings`). The original is
© LuxAlgo, licensed CC BY-NC-SA 4.0 — this port inherits that licence:
attribution above, share-alike, non-commercial.
https://creativecommons.org/licenses/by-nc-sa/4.0/

What the indicator actually does, since the Pine is terse about it:

  * A pivot high at bar p (highest high of the 2*length+1 bars centred on p)
    opens a zone from high[p] down to max(close[p], open[p]) — the candle body
    top, so the zone covers the wick where stops rest. 'full' area mode uses
    low[p] instead and covers the whole candle. Pivot lows mirror this.
  * The zone's label is not a touch count on the level, it is the volume of
    every later bar whose range overlaps the zone box. That is the number the
    playbook reads as "millions = real, K-volume = weak".
  * Accumulation stops when the next same-side pivot confirms, not when the
    zone is broken — each zone's label is frozen from that point on.
  * Pine confirms a pivot `length` bars late, so the newest zone's volume is
    always short by that many bars. Reproduced here rather than corrected:
    the point is to match the chart Nikil is looking at.

What this doesn't do: the volume label. `count`/`volume` on each zone still
exist as fields — the accumulation logic is unchanged — but they're computed
off whatever feed `alpaca_data.py` returns, which was never checked against
his chart's own volume figures and probably won't match them; a different
indicator is the plan for that number. Trust `top`/`btm`/`level`, not
`volume`, until that's sorted.

**Settings confirmed from the indicator's own panel** (screenshot, 20 Aug
2026): Pivot Lookback **14** — the Pine default, not the 7 an earlier pass
here guessed from trying to reproduce one Yahoo-sourced chart; that guess
was wrong and is superseded. Swing Area **Wick Extremity**, Intrabar
Precision **off**, Filter Areas By **Count, 0** (unfiltered — every zone
shows). All four are this module's defaults now, not guesses. If a computed
zone still disagrees with the screenshot, re-check the panel before doubting
the port — but don't start from "maybe the lookback is different" again.

`broken` vs `taken` is the one place this reports more than the chart does.
Pine only tracks a break while the zone is the most recent one on its side —
the dashed line you see is frozen at the moment the next pivot formed, so a
level price blew through months later still draws solid. `broken` is that
chart-faithful flag; `taken` says whether price has closed through the level
at any point since. Grade the setup on `taken`; match the screenshot on
`broken`.

    python3 liquidity_swings.py NBIS --tf 4h --min-vol 1e6
"""

import argparse
import json
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

import alpaca_data

_ET = ZoneInfo("America/New_York")


def _is_pivot(bars, i, length, side):
    """Pine's ta.pivothigh/pivotlow: strictly the extreme of its window.

    Pine leaves tie behaviour undocumented; strict on both sides is the
    reading that never reports two adjacent pivots for one flat top.
    """
    key = "h" if side == "high" else "l"
    x = bars[i][key]
    for j in range(i - length, i + length + 1):
        if j == i:
            continue
        y = bars[j][key]
        if (y >= x) if side == "high" else (y <= x):
            return False
    return True


def _zone_edges(b, side, area):
    if side == "high":
        return b["h"], (max(b["c"], b["o"]) if area == "wick" else b["l"])
    return (min(b["c"], b["o"]) if area == "wick" else b["h"]), b["l"]


def swing_zones(bars, length=14, area="wick", filter_by="count", filter_value=0.0):
    """Every swing zone in `bars`, oldest first.

    `bars` are marketdata OHLCV dicts (t/o/h/l/c/v). `area` is 'wick' or
    'full'; `filter_by` is 'count' or 'volume', matching the indicator's own
    "Filter Areas By" setting — zones under the threshold are still returned,
    flagged `shown=False`, because a zone the chart hides is still a zone the
    grader may want to know about.
    """
    n = len(bars)
    last_tested = n - 1 - length          # Pine samples bar n-length, never later
    zones = []

    for side in ("high", "low"):
        piv = [i for i in range(length, n - length) if _is_pivot(bars, i, length, side)]
        for k, p in enumerate(piv):
            nxt = piv[k + 1] if k + 1 < len(piv) else None
            top, btm = _zone_edges(bars[p], side, area)

            # Volume/count: bars strictly between this pivot and the next one
            # on the same side, whose range overlaps the box.
            end = min(nxt - 1 if nxt is not None else last_tested, last_tested)
            count, vol = 0, 0.0
            for m in range(p + 1, end + 1):
                b = bars[m]
                if b["l"] < top and b["h"] > btm:
                    count += 1
                    vol += b["v"]

            # A close through the level takes the liquidity. Pine starts
            # looking the bar after this pivot confirms.
            level = top if side == "high" else btm
            taken_i = None
            for m in range(p + length + 1, n):
                c = bars[m]["c"]
                if (c > level) if side == "high" else (c < level):
                    taken_i = m
                    break
            frozen = (nxt + length - 1) if nxt is not None else n - 1

            metric = count if filter_by == "count" else vol
            zones.append({
                "side": side,
                "top": top,
                "btm": btm,
                "level": level,
                "pivot_i": p,
                "t": bars[p]["t"],
                "count": count,
                "volume": vol,
                "taken": taken_i is not None,
                "taken_i": taken_i,
                "broken": taken_i is not None and taken_i <= frozen,
                "shown": metric > filter_value,
            })

    zones.sort(key=lambda z: z["pivot_i"])
    return zones


def to_session_bars(points, per=4):
    """Aggregate hourly bars into `per`-hour bars anchored to the session open.

    TradingView anchors intraday aggregates to the session, not to the wall
    clock, so a US equity 4h chart is two bars a day: 09:30-13:30 and the
    short 13:30-16:00 stub. Bucketing by UTC hour instead would shift every
    zone edge by an hour and quietly stop matching the chart.
    """
    out, bucket, day = [], [], None
    for b in points:
        d = datetime.fromtimestamp(b["t"] / 1000, _ET).date()
        if d != day:
            if bucket:
                out.append(_merge(bucket))
            bucket, day = [], d
        bucket.append(b)
        if len(bucket) == per:
            out.append(_merge(bucket))
            bucket = []
    if bucket:
        out.append(_merge(bucket))
    return out


def _merge(bs):
    return {"t": bs[0]["t"], "o": bs[0]["o"], "c": bs[-1]["c"],
            "h": max(b["h"] for b in bs), "l": min(b["l"] for b in bs),
            "v": sum(b["v"] for b in bs)}


def load_bars(symbol, tf="4h"):
    """Bars for one ticker at 1d, 1h or 4h, from Alpaca — never Yahoo,
    Nasdaq, or Webull. Alpaca only returns completed bars for a real trade,
    so there's no forming-bar placeholder to strip here the way Yahoo's feed
    needed.
    """
    pts = alpaca_data.bars(symbol, "1Day" if tf == "1d" else "1Hour",
                            days=800 if tf == "1d" else 400)
    return to_session_bars(pts, 4) if tf == "4h" else pts


def nearest_zones(zones, price):
    """The live zone bracketing price on each side, or None.

    "Live" means it passed the volume filter and price has not closed through
    it — a taken level is not where the next stop goes. Ties go to the zone
    whose near edge is closest to price, which is the one the trade actually
    has to clear.
    """
    live = [z for z in zones if z["shown"] and not z["taken"]]
    below = [z for z in live if z["top"] < price]
    above = [z for z in live if z["btm"] > price]
    return (max(below, key=lambda z: z["top"]) if below else None,
            min(above, key=lambda z: z["btm"]) if above else None)


def fmt_vol(v):
    """Pine's format.volume, near enough for reading against the chart."""
    for cut, suf in ((1e9, "B"), (1e6, "M"), (1e3, "K")):
        if v >= cut:
            return f"{v / cut:.3f}{suf}"
    return f"{v:.0f}"


def main():
    ap = argparse.ArgumentParser(description="LuxAlgo Liquidity Swings zones for a ticker")
    ap.add_argument("symbol")
    ap.add_argument("--tf", default="4h", choices=("4h", "1h", "1d"))
    ap.add_argument("--length", type=int, default=14, help="pivot lookback (default 14)")
    ap.add_argument("--area", default="wick", choices=("wick", "full"))
    ap.add_argument("--min-vol", type=float, default=0.0,
                    help="hide zones under this volume, as the chart's Volume filter does")
    ap.add_argument("--all", action="store_true", help="include filtered-out and taken zones")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    bars = load_bars(a.symbol.upper(), a.tf)
    filt = ("volume", a.min_vol) if a.min_vol else ("count", 0.0)
    zones = swing_zones(bars, a.length, a.area, filt[0], filt[1])
    price = bars[-1]["c"]

    keep = [z for z in zones if a.all or (z["shown"] and not z["taken"])]

    if a.json:
        print(json.dumps({"symbol": a.symbol.upper(), "tf": a.tf, "price": price,
                          "bars": len(bars), "zones": keep}, indent=1))
        return

    print(f"{a.symbol.upper()}  {a.tf}  {len(bars)} bars  last close {price:.2f}"
          f"   (pivot lookback {a.length}, {a.area} area)")
    print(f"{'':2} {'zone':>18}  {'volume':>9} {'bars':>5}  {'when':<16} state")
    for z in keep:
        when = datetime.fromtimestamp(z["t"] / 1000, _ET).strftime("%Y-%m-%d %H:%M")
        state = "taken" if z["taken"] else ("broken" if z["broken"] else "live")
        if not z["shown"]:
            state += ", filtered"
        mark = "R" if z["side"] == "high" else "G"
        print(f"{mark:2} {z['btm']:8.2f}-{z['top']:8.2f}  {fmt_vol(z['volume']):>9} "
              f"{z['count']:5}  {when:<16} {state}")

    below, above = nearest_zones(zones, price)
    print()
    if below:
        print(f"nearest zone below  {below['btm']:.2f}-{below['top']:.2f}  {fmt_vol(below['volume'])}"
              f"   long stop keys off {below['btm']:.2f}")
    if above:
        print(f"nearest zone above  {above['btm']:.2f}-{above['top']:.2f}  {fmt_vol(above['volume'])}"
              f"   short stop keys off {above['top']:.2f}")


if __name__ == "__main__":
    sys.exit(main())
