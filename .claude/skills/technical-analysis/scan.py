#!/usr/bin/env python3
"""Screen for the A-setup from saved Webull 4h bar JSON. Stdlib only.

Workflow (cloud session):
  1. Call mcp__Webull__get_stock_bars with timespan="M240", trading_sessions="RTH",
     count>=80, up to 20 symbols per call. Large results are auto-saved to a file.
  2. python3 scan.py <those files...>

Prints: eligible names, live setups, and near-misses with the price to wait for.
"""
import json, sys

SLOPE_MIN   = 1.0      # % rise in the 50 SMA over 10 bars
VOL_BAND    = (1.5, 3.0)   # median 4h bar range as % of price
EXT_MAX     = 2.5      # max % the close may sit above the SMA


def load(paths):
    bars = {}
    for p in paths:
        try:
            blocks = json.load(open(p))["result"]
        except Exception as e:
            print(f"  ! skipped {p}: {e}", file=sys.stderr); continue
        for blk in blocks:
            rows = [{"t": b["time"], "c": float(b["close"]), "h": float(b["high"]),
                     "l": float(b["low"])} for b in blk["result"]]
            rows.sort(key=lambda r: r["t"])
            if len(rows) > len(bars.get(blk["symbol"], [])):
                bars[blk["symbol"]] = rows
    return bars


def metrics(rows):
    """SMA50, 10-bar slope %, extension %, median 20-bar range % — at the last closed bar."""
    if len(rows) < 61:
        return None
    c = [r["c"] for r in rows]
    sma = lambda i: sum(c[i - 49:i + 1]) / 50
    i = len(rows) - 1
    s_now, s_prev = sma(i), sma(i - 10)
    rng = sorted((r["h"] - r["l"]) / r["c"] * 100 for r in rows[i - 20:i])
    return {
        "px": c[i], "sma": s_now,
        "slope": (s_now - s_prev) / s_prev * 100,
        "ext": (c[i] - s_now) / s_now * 100,
        "range": rng[len(rng) // 2],
        "low": rows[i]["l"], "t": rows[i]["t"][:16],
    }


def main(paths):
    bars = load(paths)
    if not bars:
        print("no bar data found"); return
    rows = {s: metrics(r) for s, r in bars.items()}
    rows = {s: m for s, m in rows.items() if m}
    print(f"scanned {len(rows)} names — last bar {next(iter(rows.values()))['t']}\n")

    takes, waits = [], []
    for s, m in sorted(rows.items()):
        eligible = VOL_BAND[0] <= m["range"] <= VOL_BAND[1]
        steep    = m["slope"] >= SLOPE_MIN
        touched  = m["low"] <= m["sma"]
        above    = m["px"] > m["sma"]
        near     = m["ext"] <= EXT_MAX
        if eligible and steep and touched and above and near:
            takes.append((s, m))
        elif eligible and steep and above and not touched:
            waits.append((s, m))

    print("SETUPS  (bounced off a steep rising 50 SMA this bar)")
    if not takes:
        print("  none\n")
    for s, m in takes:
        print(f"  {s:<6} ${m['px']:.2f}  slope +{m['slope']:.1f}%  ext +{m['ext']:.1f}%  "
              f"range {m['range']:.1f}%/bar   stop ${m['px']*.96:.2f}  target ${m['px']*1.08:.2f}")

    print("\nARMED  (eligible + steep uptrend, waiting for a pullback to the SMA)")
    if not waits:
        print("  none")
    for s, m in sorted(waits, key=lambda x: x[1]["ext"])[:12]:
        print(f"  {s:<6} ${m['px']:.2f}  +{m['ext']:.1f}% over SMA — needs a dip to "
              f"${m['sma']:.2f} and a close back above  (slope +{m['slope']:.1f}%)")

    elig = [s for s, m in rows.items() if VOL_BAND[0] <= m["range"] <= VOL_BAND[1]]
    print(f"\nELIGIBLE NAMES ({len(elig)}/{len(rows)}, bar range {VOL_BAND[0]}–{VOL_BAND[1]}%):")
    print("  " + ", ".join(sorted(elig)))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(1)
    main(sys.argv[1:])
