#!/usr/bin/env python3
"""Screen both sides of the 50 SMA setup. Stdlib only.

Two data sources, same math:

  Alpaca (preferred — authoritative for price):
      export APCA_API_KEY_ID=...  APCA_API_SECRET_KEY=...
      python3 screener.py --alpaca

  Saved Webull 4h bar JSON (fallback, and what the backtest used):
      python3 screener.py <bar-files...>

LONG is the measured A-setup: 64% reach +4%, 48% reach +8%, +0.44R.
SHORT is the mirror and has NO measured edge (expectancy ~0, worse as the
downtrend steepens). It is printed because it was asked for, capped at C size.
"""
import json, os, sys, urllib.request, urllib.parse, datetime as dt
try:
    from zoneinfo import ZoneInfo
    ET = ZoneInfo("America/New_York")           # handles the EST/EDT switch
except Exception:
    ET = dt.timezone(dt.timedelta(hours=-4))    # EDT fallback

SLOPE_MIN = 1.0          # % move in the 50 SMA over 10 bars
VOL_BAND  = (1.5, 3.0)   # median 4h bar range as % of price
EXT_MAX   = 2.5          # max % the close may sit away from the SMA

UNIVERSE = """NVDA AMD AVGO MU INTC QCOM TSM ARM MRVL LRCX AMAT KLAC ASML ADI TXN
NXPI ON MCHP SMCI DELL AAPL MSFT GOOGL AMZN META NFLX TSLA ORCL CRM ADBE NOW PANW
CRWD ZS NET DDOG SNOW MDB TEAM WDAY PLTR APP SHOP UBER ABNB DASH RBLX U SOFI AFRM
HOOD COIN PYPL TTD SNAP PINS LYFT SPOT TOST DKNG RKLB LUNR ACHR JOBY OKLO SMR CEG
GEV VRT ANET VST TLN NBIS IREN RIOT MARA CLSK MSTR WULF CORZ LLY UNH HIMS TEM ISRG
CAT DE BA GE HON JPM GS BAC XOM CVX WMT COST NKE LULU DIS""".split()


# ---------------------------------------------------------------- data sources

def from_alpaca(symbols):
    """4h RTH bars from Alpaca.

    Alpaca has no 4H timeframe and no regular-hours filter on /bars, so bars are
    built from 30-minute bars. 30Min is the coarsest timeframe whose boundaries
    land on 09:30 and 13:30 -- an hourly bar stamped 09:00 straddles the open,
    mixing pre-market prints into the session high/low."""
    kid = os.environ.get("APCA_API_KEY_ID") or os.environ.get("ALPACA_API_KEY_ID")
    sec = os.environ.get("APCA_API_SECRET_KEY") or os.environ.get("ALPACA_API_SECRET_KEY")
    if not (kid and sec):
        sys.exit("APCA_API_KEY_ID / APCA_API_SECRET_KEY not set in the environment.")
    start = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=140)).strftime("%Y-%m-%d")
    feed = os.environ.get("ALPACA_FEED", "sip")   # sip = full tape; iex sees ~3% of it
    out, page = {}, None
    while True:
        q = {"symbols": ",".join(symbols), "timeframe": "30Min", "start": start,
             "limit": 10000, "adjustment": "split", "feed": feed}
        if page:
            q["page_token"] = page
        req = urllib.request.Request(
            "https://data.alpaca.markets/v2/stocks/bars?" + urllib.parse.urlencode(q),
            headers={"APCA-API-KEY-ID": kid, "APCA-API-SECRET-KEY": sec})
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                d = json.load(r)
        except urllib.error.HTTPError as e:
            if e.code in (401, 403) and feed == "sip":
                print("  ! no SIP entitlement — falling back to the IEX feed, which "
                      "sees ~3% of volume and prints different highs/lows",
                      file=sys.stderr)
                feed = "iex"; continue
            raise
        for sym, bars in (d.get("bars") or {}).items():
            out.setdefault(sym, []).extend(bars)
        page = d.get("next_page_token")
        if not page:
            break
    return {s: _to_4h(b) for s, b in out.items()}


OPEN, MID, CLOSE = 9 * 60 + 30, 13 * 60 + 30, 16 * 60

def _to_4h(half_hourly):
    """Fold 30-minute bars into RTH 4h buckets: 09:30-13:30 and 13:30-16:00 ET.

    Drops the bucket still in progress. The A-setup is defined on a CLOSED 4h
    bar -- a live bar's low and close both still move, so grading one is the
    same error as reading the chart with the crosshair on it."""
    buckets = {}
    for b in half_hourly:
        t = dt.datetime.fromisoformat(b["t"].replace("Z", "+00:00"))
        et = t.astimezone(ET)
        mins = et.hour * 60 + et.minute
        if not OPEN <= mins < CLOSE:                 # regular hours only
            continue
        half = 0 if mins < MID else 1
        g = buckets.setdefault((et.date(), half),
                               {"h": -1e9, "l": 1e9, "c": None, "t": et})
        g["h"] = max(g["h"], b["h"]); g["l"] = min(g["l"], b["l"]); g["c"] = b["c"]

    now = dt.datetime.now(ET)
    rows = []
    for (day, half), v in sorted(buckets.items()):
        ends = dt.datetime.combine(day, dt.time(0), ET) + dt.timedelta(
            minutes=MID if half == 0 else CLOSE)
        if now < ends:                               # bucket still forming
            continue
        rows.append({"t": v["t"].isoformat(), "c": float(v["c"]),
                     "h": float(v["h"]), "l": float(v["l"])})
    return rows


def from_files(paths):
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


# ------------------------------------------------------------------ indicators

def metrics(rows, back=0):
    if len(rows) < 61 + back:
        return None
    c = [r["c"] for r in rows]
    sma = lambda i: sum(c[i - 49:i + 1]) / 50
    i = len(rows) - 1 - back
    s_now, s_prev = sma(i), sma(i - 10)
    rng = sorted((r["h"] - r["l"]) / r["c"] * 100 for r in rows[i - 20:i])
    return {"px": c[i], "sma": s_now,
            "slope": (s_now - s_prev) / s_prev * 100,
            "ext": (c[i] - s_now) / s_now * 100,
            "range": rng[len(rng) // 2],
            "low": rows[i]["l"], "high": rows[i]["h"], "t": str(rows[i]["t"])[:16]}


def room(rows, side):
    """% to the first unbroken opposing pivot zone. Proxy for the LuxAlgo level —
    confirm on the chart before acting."""
    n, L, px = len(rows), 3, rows[-1]["c"]
    best = None
    for k in range(L, n - L):
        w = rows[k - L:k + L + 1]
        if side == "long":
            if rows[k]["h"] != max(x["h"] for x in w):
                continue
            if any(rows[j]["c"] > rows[k]["h"] for j in range(k + 1, n)):
                continue
            if rows[k]["l"] > px and (best is None or rows[k]["l"] < best):
                best = rows[k]["l"]
        else:
            if rows[k]["l"] != min(x["l"] for x in w):
                continue
            if any(rows[j]["c"] < rows[k]["l"] for j in range(k + 1, n)):
                continue
            if rows[k]["h"] < px and (best is None or rows[k]["h"] > best):
                best = rows[k]["h"]
    if best is None:
        return None
    return (best - px) / px * 100 * (1 if side == "long" else -1)


def touched(rows, back, side):
    m = metrics(rows, back)
    if not m:
        return False
    if side == "long":
        return m["low"] <= m["sma"] and m["px"] > m["sma"]
    return m["high"] >= m["sma"] and m["px"] < m["sma"]


def score(m, rm, age, side):
    s, why = 0, []
    ok = VOL_BAND[0] <= m["range"] <= VOL_BAND[1]
    s += 2 if ok else 0
    why.append(("Eligible name", 2 if ok else 0, f"{m['range']:.1f}%/bar"))
    sl = abs(m["slope"])
    p = 2 if sl >= 1.5 else 1 if sl >= 1.0 else 0
    s += p; why.append(("SMA slope", p, f"{m['slope']:+.1f}% / 10 bars"))
    p = 2 if age == 0 else 1 if age == 1 else 0
    s += p; why.append(("The bounce", p, "this bar" if age == 0 else "prev bar"))
    p = 1 if abs(m["ext"]) <= EXT_MAX else 0
    s += p; why.append(("Not extended", p, f"{m['ext']:+.1f}% vs SMA"))
    p = 2 if (rm is None or rm >= 8) else 1 if rm >= 4 else 0
    s += p; why.append(("Room", p, "clear air" if rm is None else f"{rm:+.1f}% to zone"))
    why.append(("Book & calendar", "?", "verify earnings + book"))
    return s, why


# ----------------------------------------------------------------------- main

def main(argv):
    if "--alpaca" in argv:
        syms = [a for a in argv if a.isupper() and a.isalpha()] or UNIVERSE
        bars, src = {}, "ALPACA"
        for i in range(0, len(syms), 50):
            bars.update(from_alpaca(syms[i:i + 50]))
    else:
        bars, src = from_files([a for a in argv if not a.startswith("-")]), "WEBULL bars"
    rows = {s: m for s, m in ((s, metrics(r)) for s, r in bars.items()) if m}
    if not rows:
        print("no bar data"); return
    print(f"source: {src} — scanned {len(rows)} names, last closed bar "
          f"{next(iter(rows.values()))['t']}\n")

    for side in ("long", "short"):
        takes, armed = [], []
        for s, m in sorted(rows.items()):
            if not VOL_BAND[0] <= m["range"] <= VOL_BAND[1]:
                continue
            steep = (m["slope"] >= SLOPE_MIN) if side == "long" else (m["slope"] <= -SLOPE_MIN)
            right = (m["px"] > m["sma"]) if side == "long" else (m["px"] < m["sma"])
            if not (steep and right):
                continue
            age = 0 if touched(bars[s], 0, side) else 1 if touched(bars[s], 1, side) else None
            if age is not None and abs(m["ext"]) <= EXT_MAX:
                takes.append((s, m, age))
            elif age is None:
                armed.append((s, m))

        tag = "LONG — the measured A-setup" if side == "long" else \
              "SHORT — mirror setup, NO measured edge (E~0), C size max"
        print(f"=== {tag} ===")
        print("SETUPS")
        if not takes:
            print("  none")
        for s, m, age in takes:
            rm = room(bars[s], side)
            sc, why = score(m, rm, age, side)
            grade = "A" if sc >= 9 else "B" if sc >= 7 else "C" if sc >= 5 else "D"
            d = 1 if side == "long" else -1
            stop = m["px"] * (1 - .04 * d)
            if rm is None or rm >= 8:                    # clear to +8%
                plan, tgt = "RUNNER 1:2", m["px"] * (1 + .08 * d)
            elif rm >= 4:                                # a zone caps it at +4%
                plan, tgt = "SCALP 1:1", m["px"] * (1 + .04 * d)
            else:                                        # nothing worth taking
                plan, tgt = "SKIP — no room", None
            print(f"  {s:<6} ${m['px']:.2f}  {sc}/10 {grade}  {plan}")
            print(f"         slope {m['slope']:+.1f}%  ext {m['ext']:+.1f}%  "
                  f"range {m['range']:.1f}%/bar  touch {'this' if age==0 else 'prev'} bar"
                  f"  room {'clear' if rm is None else f'{rm:+.1f}%'}")
            t = "—" if tgt is None else f"${tgt:.2f}"
            print(f"         stop ${stop:.2f}   target {t}")
        print("\nARMED (steep trend, waiting for the pullback to the SMA)")
        if not armed:
            print("  none")
        for s, m in sorted(armed, key=lambda x: abs(x[1]["ext"]))[:10]:
            verb = "dip to" if side == "long" else "pop to"
            print(f"  {s:<6} ${m['px']:.2f}  {m['ext']:+.1f}% vs SMA — needs a {verb} "
                  f"${m['sma']:.2f} and a close back {'above' if side=='long' else 'below'}"
                  f"  (slope {m['slope']:+.1f}%)")
        print()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(1)
    main(sys.argv[1:])
