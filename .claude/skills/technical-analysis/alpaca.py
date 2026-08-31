#!/usr/bin/env python3
"""Alpaca market data for the trade grader. Stdlib only, no pip installs.

    python3 alpaca.py bars NVDA AMD PLTR ...     -> writes 4h RTH bar JSON, prints the path
    python3 alpaca.py quote NVDA                 -> live-verified last trade
    python3 alpaca.py earnings NVDA [--days 14]  -> earnings inside the hold window

WHY THIS FILE EXISTS. The grader used to read Webull MCP bars. Alpaca is now the
single price source, because a grade is only as good as the number under it — SBUX
(#15 in the journal) was stopped out off a bad price a model handed over from a
second feed. One feed, stamped with which feed it was, or ask.

THE BAR SHAPE IS NOT ALPACA'S. The backtest that produced every threshold in
SKILL.md was measured on **regular-hours 4h bars**: two per session, 09:30-13:30
and 13:30-16:00 ET. Alpaca's own 4Hour bars are aligned to UTC and include
pre/post market, so they are a different bar and would silently move the SMA, the
slope and the bar-range band. So this fetches 30Min bars, drops everything outside
09:30-16:00 ET, and rebuilds the exact session buckets the backtest used.

ONLY CLOSED BARS ARE EMITTED. The setup requires a bar that *closed* back above
the SMA; a forming bar that is above it right now is a WAIT, not a trigger. The
forming bucket is reported separately, with the time it closes, so the WAIT answer
can name that time.

CREDENTIALS (env, never hardcoded):
    APCA_API_KEY_ID / APCA_API_SECRET_KEY      (ALPACA_API_KEY_ID / ALPACA_API_SECRET_KEY also read)
    APCA_FEED=sip|iex   optional; default tries sip and falls back to iex.
"""
import json, os, sys, urllib.request, urllib.error
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

DATA = "https://data.alpaca.markets"
ET = ZoneInfo("America/New_York")
OPEN_M, MID_M, CLOSE_M = 9 * 60 + 30, 13 * 60 + 30, 16 * 60   # ET minutes: session bucket edges
CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".cache_bars")
BROWSER_UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")


def keys():
    k = os.environ.get("APCA_API_KEY_ID") or os.environ.get("ALPACA_API_KEY_ID")
    s = os.environ.get("APCA_API_SECRET_KEY") or os.environ.get("ALPACA_API_SECRET_KEY")
    if not k or not s:
        sys.exit("Alpaca keys missing. Set APCA_API_KEY_ID and APCA_API_SECRET_KEY "
                 "(Claude Code web: environment settings -> environment variables).")
    return {"APCA-API-KEY-ID": k, "APCA-API-SECRET-KEY": s, "Accept": "application/json"}


def _get(url, headers, timeout=45):
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def _ts(s):
    """Alpaca RFC3339 -> aware UTC datetime. Nanosecond precision is truncated."""
    s = s.replace("Z", "+00:00")
    if "." in s:
        head, rest = s.split(".", 1)
        frac, tz = rest[:-6], rest[-6:]
        s = f"{head}.{frac[:6]}{tz}"
    return datetime.fromisoformat(s).astimezone(timezone.utc)


# ------------------------------------------------------------------ 30Min -> 4h RTH
def fetch_30min(symbols, days, feed, hdr):
    """Raw 30Min bars for every symbol. Paginates; Alpaca caps a page at 10k bars."""
    start = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    out, token = {s: [] for s in symbols}, None
    while True:
        q = (f"?symbols={','.join(symbols)}&timeframe=30Min&start={start}"
             f"&limit=10000&adjustment=all&sort=asc&feed={feed}")
        page = _get(DATA + "/v2/stocks/bars" + q + (f"&page_token={token}" if token else ""), hdr)
        for sym, rows in (page.get("bars") or {}).items():
            out.setdefault(sym, []).extend(rows)
        token = page.get("next_page_token")
        if not token:
            return out


def bucket(rows, now_et):
    """Fold 30Min bars into the backtest's session buckets. Returns (closed, forming)."""
    buckets = {}
    for b in rows:
        t = _ts(b["t"]).astimezone(ET)
        m = t.hour * 60 + t.minute
        if m < OPEN_M or m >= CLOSE_M:          # pre/post market is not in the backtest
            continue
        key = (t.date(), 0 if m < MID_M else 1)
        agg = buckets.get(key)
        if agg is None:
            buckets[key] = {"t": t.isoformat(), "o": b["o"], "h": b["h"],
                            "l": b["l"], "c": b["c"], "v": b["v"]}
        else:
            agg["h"] = max(agg["h"], b["h"])
            agg["l"] = min(agg["l"], b["l"])
            agg["c"] = b["c"]
            agg["v"] += b["v"]

    closed, forming = [], None
    for (day, half), agg in sorted(buckets.items()):
        end_m = MID_M if half == 0 else CLOSE_M
        end = datetime.combine(day, datetime.min.time(), ET) + timedelta(minutes=end_m)
        agg["closes"] = end.isoformat()
        if now_et >= end:
            closed.append(agg)
        else:
            forming = agg                        # only the last bucket can still be open
    return closed, forming


def cmd_bars(symbols, days=120):
    hdr = keys()
    feed = os.environ.get("APCA_FEED")
    feeds = [feed] if feed else ["sip", "iex"]
    raw = err = None
    for f in feeds:
        try:
            raw, feed = fetch_30min(symbols, days, f, hdr), f
            break
        except urllib.error.HTTPError as e:
            # 403 = the account's plan does not carry that feed; iex is on every plan.
            if e.code not in (403, 422) or f is feeds[-1]:
                sys.exit(f"Alpaca {e.code} on feed={f}: {e.read()[:300].decode('utf8','replace')}")
            err = e
    now_et = datetime.now(ET)
    data = {}
    for s in symbols:
        closed, forming = bucket(raw.get(s, []), now_et)
        data[s] = {"bars": closed, "forming": forming,
                   "next_close": (forming or {}).get("closes")}
    payload = {"source": "alpaca", "feed": feed,
               "bar": "4h RTH (09:30-13:30 / 13:30-16:00 ET) built from 30Min bars",
               "fetched_at": now_et.isoformat(), "symbols": data}
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, f"bars-{now_et.strftime('%Y%m%dT%H%M')}.json")
    with open(path, "w") as fh:
        json.dump(payload, fh)
    thin = [s for s in symbols if len(data[s]["bars"]) < 61]
    print(f"{len(symbols)} symbols · feed={feed} · "
          f"{min(len(d['bars']) for d in data.values())}-{max(len(d['bars']) for d in data.values())} closed 4h bars")
    if err:
        print("  note: sip unavailable on this plan, used iex")
    if thin:
        print(f"  too few bars to score (need 61): {', '.join(thin)}")
    print(path)


# ------------------------------------------------------------------ quote
def cmd_quote(symbol):
    hdr = keys()
    feed = os.environ.get("APCA_FEED", "iex")
    try:
        snap = _get(f"{DATA}/v2/stocks/{symbol}/snapshot?feed=sip", hdr); feed = "sip"
    except urllib.error.HTTPError:
        snap = _get(f"{DATA}/v2/stocks/{symbol}/snapshot?feed={feed}", hdr)
    t, d, p = snap.get("latestTrade") or {}, snap.get("dailyBar") or {}, snap.get("prevDailyBar") or {}
    chg = (d.get("c", 0) - p["c"]) / p["c"] * 100 if p.get("c") else None
    print(f"{symbol}  ${t.get('p', float('nan')):.2f}   day {d.get('o')}/{d.get('h')}/{d.get('l')}/{d.get('c')}"
          + (f"   {chg:+.2f}% vs prev close" if chg is not None else ""))
    print(f"  last trade {t.get('t','?')}  feed={feed}"
          + ("   (iex: consolidated tape not on this plan — confirm against his chart)" if feed == "iex" else ""))


# ------------------------------------------------------------------ earnings
def cmd_earnings(symbol, days=14):
    """Alpaca has no earnings calendar, so this is Nasdaq's — the one non-Alpaca call
    here, and it exists because 'earnings inside the hold' is a hard SKIP."""
    today = datetime.now(ET).date()
    hits = []
    for i in range(days + 1):
        d = today + timedelta(days=i)
        if d.weekday() > 4:
            continue
        try:
            j = _get(f"https://api.nasdaq.com/api/calendar/earnings?date={d}",
                     {"User-Agent": BROWSER_UA, "Accept": "application/json"}, timeout=20)
        except Exception:
            continue
        for r in ((j.get("data") or {}).get("rows") or []):
            if r.get("symbol", "").upper() == symbol.upper():
                hits.append((d, r.get("time", "")))
    if hits:
        for d, when in hits:
            print(f"*** {symbol} REPORTS {d} ({when}) — inside a {days}-day hold. HARD SKIP.")
    else:
        print(f"{symbol}: no earnings found in the next {days} days (Nasdaq calendar). "
              "Confirm on his chart before sizing.")


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a:
        print(__doc__); sys.exit(1)
    cmd, rest = a[0], a[1:]
    n = int(rest[rest.index("--days") + 1]) if "--days" in rest else None
    rest = [x for x in rest if not x.startswith("--") and not x.isdigit()] if n else rest
    if cmd == "bars":
        cmd_bars([s.upper() for s in rest], n or 120)
    elif cmd == "quote":
        cmd_quote(rest[0].upper())
    elif cmd == "earnings":
        cmd_earnings(rest[0].upper(), n or 14)
    else:
        print(__doc__); sys.exit(1)
