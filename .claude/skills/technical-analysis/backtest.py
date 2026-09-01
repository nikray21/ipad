#!/usr/bin/env python3
"""Re-measure the A-setup on Alpaca bars, comparing the 1:1 and 1:2 exits.

The question this answers is not just which target pays more -- the existing
backtest already says 1:2 does -- but how LONG each one takes. A target that
pays more but needs a hold he won't sit through is worth less than its number.

    export APCA_API_KEY_ID=...  APCA_API_SECRET_KEY=...
    python3 backtest.py [months]
"""
import sys, os, json, statistics as st
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import screener as S

SLOPE_MIN, VOL_BAND, EXT_MAX, STOP = 1.0, (1.5, 3.0), 2.5, 0.04
GAP, HORIZON = 6, 20          # episode separation, and the time stop in bars


def signals(rows):
    """Indices of bars that fire the A-setup, collapsed into episodes."""
    out, last = [], -99
    for i in range(60, len(rows)):
        c = [r["c"] for r in rows[:i + 1]]
        sma = sum(c[-50:]) / 50
        prev = sum(c[-60:-10]) / 50
        slope = (sma - prev) / prev * 100
        ext = (c[-1] - sma) / sma * 100
        rng = sorted((r["h"] - r["l"]) / r["c"] * 100 for r in rows[i - 20:i])
        band = rng[len(rng) // 2]
        if (VOL_BAND[0] <= band <= VOL_BAND[1] and slope >= SLOPE_MIN
                and rows[i]["l"] <= sma and c[-1] > sma and 0 <= ext <= EXT_MAX):
            if i - last >= GAP:
                out.append(i)
            last = i
    return out


def barrier_be(rows, i):
    """His rule: +4% moves the stop to breakeven, then the trade runs.

    This is the FLOOR of "exit any time at or after +4%" -- it holds all the
    way to +8% and takes a scratch if price comes back to entry. Exiting the
    moment +4% prints is the other end of that range, and that is just the
    1:1 row. Anything he actually does lands between the two.

    Returns R multiples: -1 stopped, 0 scratched at breakeven, +2 at target,
    or the mark-to-market return if the 20-bar time stop lands first."""
    entry = rows[i]["c"]
    tp4, tp8, sl = entry * 1.04, entry * 1.08, entry * (1 - STOP)
    armed = False
    for k in range(i + 1, min(i + 1 + HORIZON, len(rows))):
        h, l = rows[k]["h"], rows[k]["l"]
        if not armed:
            if h >= tp4 and l <= sl:
                return 0.5, k - i                 # ambiguous bar, split it
            if h >= tp4:
                armed = True
                if h >= tp8:
                    return 2.0, k - i
                continue
            if l <= sl:
                return -1.0, k - i
        else:
            if h >= tp8:
                return 2.0, k - i
            if l <= entry:
                return 0.0, k - i                 # scratched at breakeven
    last = rows[min(i + HORIZON, len(rows) - 1)]["c"]
    return (last - entry) / entry / STOP, None    # timed out, closed at market


def barrier(rows, i, target):
    """Walk forward from the signal close. Returns (won, bars_taken).
    A bar that trades through both barriers is ambiguous -- counted as half."""
    entry = rows[i]["c"]
    tp, sl = entry * (1 + target), entry * (1 - STOP)
    for k in range(i + 1, min(i + 1 + HORIZON, len(rows))):
        hit_tp, hit_sl = rows[k]["h"] >= tp, rows[k]["l"] <= sl
        if hit_tp and hit_sl:
            return 0.5, k - i
        if hit_tp:
            return 1.0, k - i
        if hit_sl:
            return 0.0, k - i
    return 0.0, None                      # timed out: closed flat, not a loss


def main(months=14):
    syms = S.UNIVERSE
    cache = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".cache_bars.json")
    if os.path.exists(cache):
        bars = json.load(open(cache))
        print(f"  using cached bars ({len(bars)} names) -- delete .cache_bars.json to refetch",
              file=sys.stderr)
    else:
        part = cache + ".part"
        bars = json.load(open(part)) if os.path.exists(part) else {}
        for i in range(0, len(syms), 25):
            chunk = [x for x in syms[i:i + 25] if x not in bars]
            if not chunk:
                continue
            bars.update(S.from_alpaca(chunk))
            json.dump(bars, open(part, "w"))      # checkpoint every chunk
            print(f"  fetched {min(i+25,len(syms))}/{len(syms)} names", file=sys.stderr)
        os.replace(part, cache)

    res = {0.04: [], 0.08: []}
    be, names = [], set()
    for sym, rows in bars.items():
        if len(rows) < 120:
            continue
        for i in signals(rows):
            names.add(sym)
            for t in res:
                res[t].append(barrier(rows, i, t))
            be.append(barrier_be(rows, i))

    n = len(res[0.04])
    span = min(r["t"][:10] for r in next(iter(bars.values())))
    print(f"\nA-setup on ALPACA SIP 4h bars — {n} episodes across {len(names)} names")
    print(f"universe {len(bars)} names, history from {span}, time stop {HORIZON} bars\n")
    print("%-12s %8s %10s %14s %16s"%("target","hit","expectancy","median bars","80th pct bars"))
    for t in (0.04, 0.08):
        w = [x for x, _ in res[t]]
        hits = sum(w) / len(w) * 100
        rr = t / STOP
        e = sum(x * rr - (1 - x) * 1 for x in w) / len(w)
        took = sorted(b for x, b in res[t] if x > 0 and b)
        med = st.median(took) if took else float("nan")
        p80 = took[int(len(took) * .8)] if took else float("nan")
        print("%-12s %7.1f%% %+9.2fR %10.0f bars %12.0f bars"%(
            f"+{t*100:.0f}% ({rr:.0f}:1)", hits, e, med, p80))
        print(f"{'':13}{'':8} = ${e*50:+.0f}/trade   ~{med/2:.1f} trading days to target")
    r = [x for x, _ in be]
    won = sum(1 for x in r if x >= 2) / len(r) * 100
    scr = sum(1 for x in r if -0.01 < x < 0.5) / len(r) * 100
    lost = sum(1 for x in r if x <= -0.9) / len(r) * 100
    took = sorted(b for x, b in be if x >= 2 and b)
    med = st.median(took) if took else float("nan")
    print("\nYOUR RULE — +4% moves the stop to breakeven, then let it run")
    print("%-22s %8s %11s %9s %9s"%("", "reach +8%", "expectancy", "scratch", "stopped"))
    print("%-22s %7.1f%% %+10.2fR %8.0f%% %8.0f%%"%("+4% -> BE, hold", won,
          sum(r) / len(r), scr, lost))
    print("%-22s = $%+.0f/trade at $50 risk   median %.0f bars to +8%%"%(
          "", sum(r) / len(r) * 50, med))

    losers = sorted(b for x, b in res[0.08] if x == 0 and b)
    if losers:
        print(f"\nlosers hit the stop in a median of {st.median(losers):.0f} bars "
              f"({st.median(losers)/2:.1f} days) — the trade tells you it is wrong fast")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 14)
