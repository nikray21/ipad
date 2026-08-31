#!/usr/bin/env python3
"""Screen for the A-setup from Alpaca 4h RTH bars. Stdlib only.

Workflow:
  1. python3 alpaca.py bars ADBE AFRM AMD ...      (prints the JSON path it wrote)
  2. python3 scan.py <that path>            longs  — bounce off a rising 50 SMA
     python3 scan.py --short <that path>    shorts — rejection at a falling 50 SMA

The short side is the long side mirrored, with one exception that is NOT a mirror:
the long rule is "steeper is better", the short rule is a BAND. Past −1.5% the
measured expectancy goes negative, so a very steep downtrend is a SKIP, not an A.

Alpaca is the only price source — see alpaca.py for why the bars are rebuilt into
09:30/13:30 ET session buckets rather than used as Alpaca ships them. Only CLOSED
bars are scored; the forming bar is reported as the ARMED trigger time.

Prints: eligible names, live setups, and near-misses with the price to wait for.
"""
import json, sys

SLOPE_MIN   = 1.0      # % rise in the 50 SMA over 10 bars (longs: a floor)
SHORT_SLOPE = (-1.5, -1.0)  # shorts: a BAND. steeper than -1.5% measured negative.
VOL_BAND    = (1.5, 3.0)   # median 4h bar range as % of price
EXT_MAX     = 2.5      # max % the close may sit the wrong side of the SMA


def load(paths):
    """Read alpaca.py bar files. Later files win when a symbol appears twice."""
    bars, meta = {}, {}
    for p in paths:
        try:
            d = json.load(open(p))
        except Exception as e:
            print(f"  ! skipped {p}: {e}", file=sys.stderr); continue
        if d.get("source") != "alpaca":
            print(f"  ! skipped {p}: not an alpaca.py bar file", file=sys.stderr); continue
        meta = {"feed": d.get("feed"), "fetched_at": d.get("fetched_at")}
        for sym, blk in (d.get("symbols") or {}).items():
            rows = blk.get("bars") or []
            if len(rows) >= len(bars.get(sym, ([], None))[0]):
                bars[sym] = (rows, blk.get("next_close"))
    return bars, meta


def metrics(rows, back=0):
    """SMA50, 10-bar slope %, extension %, median 20-bar range % — at a closed bar."""
    if len(rows) < 61 + back:
        return None
    c = [r["c"] for r in rows]
    sma = lambda i: sum(c[i - 49:i + 1]) / 50
    i = len(rows) - 1 - back
    s_now, s_prev = sma(i), sma(i - 10)
    rng = sorted((r["h"] - r["l"]) / r["c"] * 100 for r in rows[i - 20:i])
    return {
        "px": c[i], "sma": s_now,
        "slope": (s_now - s_prev) / s_prev * 100,
        "ext": (c[i] - s_now) / s_now * 100,
        "range": rng[len(rng) // 2],
        "low": rows[i]["l"], "high": rows[i]["h"], "t": rows[i]["t"][:16],
    }


def room(rows):
    """% to the first live overhead pivot zone. Proxy for the LuxAlgo target level —
    confirm on his chart before acting."""
    n, L = len(rows), 3
    px = rows[-1]["c"]
    best = None
    for k in range(L, n - L):
        w = rows[k - L:k + L + 1]
        if rows[k]["h"] != max(x["h"] for x in w):
            continue
        if any(rows[j]["c"] > rows[k]["h"] for j in range(k + 1, n)):
            continue                      # zone already broken
        if rows[k]["l"] > px and (best is None or rows[k]["l"] < best):
            best = rows[k]["l"]
    return None if best is None else (best - px) / px * 100


def room_down(rows):
    """% down to the first live support pivot. Mirror of room() — same proxy, same
    caveat: confirm the level on his chart before acting."""
    n, L = len(rows), 3
    px = rows[-1]["c"]
    best = None
    for k in range(L, n - L):
        w = rows[k - L:k + L + 1]
        if rows[k]["l"] != min(x["l"] for x in w):
            continue
        if any(rows[j]["c"] < rows[k]["l"] for j in range(k + 1, n)):
            continue                      # zone already broken
        if rows[k]["h"] < px and (best is None or rows[k]["h"] > best):
            best = rows[k]["h"]
    return None if best is None else (px - best) / px * 100


def bounced(rows, back):
    """Did the bar `back` bars ago dip to the SMA and close above it?"""
    m = metrics(rows, back)
    return bool(m and m["low"] <= m["sma"] and m["px"] > m["sma"])


def rejected(rows, back):
    """Mirror: did the bar `back` bars ago poke ABOVE the SMA and close back under it?"""
    m = metrics(rows, back)
    return bool(m and m["high"] >= m["sma"] and m["px"] < m["sma"])


def scan_long(bars, rows, nextclose):
    takes, waits = [], []
    for sym, m in sorted(rows.items()):
        eligible = VOL_BAND[0] <= m["range"] <= VOL_BAND[1]
        steep    = m["slope"] >= SLOPE_MIN
        above    = m["px"] > m["sma"]
        near     = 0 <= m["ext"] <= EXT_MAX
        # the trigger may have fired on this bar or the previous one, as long as
        # price is still within the 2.5% chase limit
        fired = bounced(bars[sym], 0) or bounced(bars[sym], 1)
        if eligible and steep and fired and above and near:
            m["age"] = 0 if bounced(bars[sym], 0) else 1
            takes.append((sym, m))
        elif eligible and steep and above and not fired:
            waits.append((sym, m))

    print("SETUPS  (bounced off a steep rising 50 SMA this bar)")
    if not takes:
        print("  none\n")
    for sym, m in takes:
        age = "this bar" if m["age"] == 0 else "prev bar"
        rm = room(bars[sym])
        if rm is None:      plan = "RUNNER 1:2 (clear air)"
        elif rm >= 8:       plan = f"RUNNER 1:2 (room +{rm:.1f}%)"
        elif rm >= 4:       plan = f"SCALP 1:1 (room +{rm:.1f}%)"
        else:               plan = f"*** SKIP — only +{rm:.1f}% room, hard stop 6 ***"
        print(f"  {sym:<6} ${m['px']:.2f}  bounce {age}  slope +{m['slope']:.1f}%  ext +{m['ext']:.1f}%  "
              f"range {m['range']:.1f}%/bar")
        print(f"         stop ${m['px']*.96:.2f}  target ${m['px']*1.08:.2f}   {plan}")

    print("\nARMED  (eligible + steep uptrend, waiting for a pullback to the SMA)")
    if not waits:
        print("  none")
    for sym, m in sorted(waits, key=lambda x: x[1]["ext"])[:12]:
        nc = nextclose.get(sym)
        print(f"  {sym:<6} ${m['px']:.2f}  +{m['ext']:.1f}% over SMA — needs a dip to "
              f"${m['sma']:.2f} and a close back above  (slope +{m['slope']:.1f}%)"
              + (f"  [bar closes {nc[11:16]} ET]" if nc else ""))


def scan_short(bars, rows, nextclose):
    """The mirror. Note the slope test is a BAND, not a floor — that is the one
    condition that does not flip, and steeper than -1.5% is a SKIP not an upgrade."""
    lo, hi = SHORT_SLOPE
    takes, waits, toosteep = [], [], []
    for sym, m in sorted(rows.items()):
        eligible = VOL_BAND[0] <= m["range"] <= VOL_BAND[1]
        inband   = lo <= m["slope"] <= hi
        below    = m["px"] < m["sma"]
        near     = -EXT_MAX <= m["ext"] <= 0
        fired = rejected(bars[sym], 0) or rejected(bars[sym], 1)
        if eligible and m["slope"] < lo and below:
            toosteep.append((sym, m)); continue
        if eligible and inband and fired and below and near:
            m["age"] = 0 if rejected(bars[sym], 0) else 1
            takes.append((sym, m))
        elif eligible and inband and below and not fired:
            waits.append((sym, m))

    print("SHORT SETUPS  (rejected at a falling 50 SMA this bar)")
    if not takes:
        print("  none\n")
    for sym, m in takes:
        age = "this bar" if m["age"] == 0 else "prev bar"
        rm = room_down(bars[sym])
        if rm is None:      plan = "RUNNER 1:2 (clear air)"
        elif rm >= 8:       plan = f"RUNNER 1:2 (room -{rm:.1f}%)"
        elif rm >= 4:       plan = f"SCALP 1:1 (room -{rm:.1f}%)"
        else:               plan = f"*** SKIP — only -{rm:.1f}% room, hard stop 6 ***"
        print(f"  {sym:<6} ${m['px']:.2f}  rejection {age}  slope {m['slope']:.1f}%  ext {m['ext']:.1f}%  "
              f"range {m['range']:.1f}%/bar")
        print(f"         stop ${m['px']*1.04:.2f}  target ${m['px']*0.92:.2f}   {plan}")
    if takes:
        print("  >>> shorts are capped at C size ($400) — no measured edge. See SKILL.md.")

    print("\nARMED  (eligible + slope in band, waiting for a rally back to the SMA)")
    if not waits:
        print("  none")
    for sym, m in sorted(waits, key=lambda x: -x[1]["ext"])[:12]:
        nc = nextclose.get(sym)
        print(f"  {sym:<6} ${m['px']:.2f}  {m['ext']:.1f}% under SMA — needs a rally to "
              f"${m['sma']:.2f} and a close back below  (slope {m['slope']:.1f}%)"
              + (f"  [bar closes {nc[11:16]} ET]" if nc else ""))

    if toosteep:
        print(f"\nTOO STEEP TO SHORT (slope < {lo}%, where the measured expectancy turns "
              f"negative — these are SKIPs, not A-setups):")
        print("  " + ", ".join(f"{s} ({m['slope']:.1f}%)" for s, m in toosteep))


def main(argv):
    short = "--short" in argv
    paths = [a for a in argv if not a.startswith("--")]
    loaded, meta = load(paths)
    if not loaded:
        print("no bar data found"); return
    bars = {s: r for s, (r, _) in loaded.items()}
    nextclose = {s: n for s, (_, n) in loaded.items()}
    rows = {s: metrics(r) for s, r in bars.items()}
    rows = {s: m for s, m in rows.items() if m}
    if not rows:
        print("no name has the 61 closed bars a score needs"); return
    print(f"scanned {len(rows)} names — last closed bar {next(iter(rows.values()))['t']} "
          f"· alpaca feed={meta.get('feed')} · {'SHORT' if short else 'LONG'} side\n")

    (scan_short if short else scan_long)(bars, rows, nextclose)

    elig = [s for s, m in rows.items() if VOL_BAND[0] <= m["range"] <= VOL_BAND[1]]
    print(f"\nELIGIBLE NAMES ({len(elig)}/{len(rows)}, bar range {VOL_BAND[0]}–{VOL_BAND[1]}%):")
    print("  " + ", ".join(sorted(elig)))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(1)
    main(sys.argv[1:])
