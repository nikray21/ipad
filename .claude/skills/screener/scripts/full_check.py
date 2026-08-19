#!/usr/bin/env python3
"""Full ruleset check: trend template + entry zone + fade + sweep proxy + ATR,
on Alpaca 4H bars. Used for positions and for /screener finalists."""
import json, sys, time, datetime, urllib.request, urllib.parse

import os

# Credentials come from the environment -- NEVER hardcode them here, and never
# commit them. Set these in the Claude Code environment's env-var settings so
# they persist across cloud sessions (the repo is the only other persistence,
# and secrets must not live in it).
KEY = os.environ.get('APCA_API_KEY_ID')
SECRET = os.environ.get('APCA_API_SECRET_KEY')
if not KEY or not SECRET:
    raise SystemExit(
        "Missing Alpaca credentials.\n"
        "Set APCA_API_KEY_ID and APCA_API_SECRET_KEY as environment variables.\n"
        "In a cloud session, add them in the environment settings so they persist."
    )
HEADERS = {'APCA-API-KEY-ID': KEY, 'APCA-API-SECRET-KEY': SECRET}

def fetch_bars(sym, days=420):
    start = (datetime.datetime.utcnow() - datetime.timedelta(days=days)).strftime('%Y-%m-%dT00:00:00Z')
    all_bars, page_token = [], None
    base = f'https://data.alpaca.markets/v2/stocks/{sym}/bars'
    for _ in range(60):
        p = {'timeframe': '4Hour', 'start': start, 'limit': '10000'}
        if page_token: p['page_token'] = page_token
        url = base + '?' + urllib.parse.urlencode(p)
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=20) as r:
            d = json.load(r)
        all_bars.extend(d.get('bars', []))
        page_token = d.get('next_page_token')
        time.sleep(0.3)
        if not page_token: break
    return all_bars

def latest_price(sym):
    """Most recent COMPLETED daily close, for the verification pass.

    Must pass an explicit `start`. Without one, Alpaca returns bars:null
    pre-market (no daily bar exists for today yet) -- which on 2026-08-19
    made all 101 tickers 'fail verification' at 8am ET. Not a data problem;
    a missing parameter. Ask for a week and take the last bar."""
    start = (datetime.datetime.utcnow() - datetime.timedelta(days=7)).strftime('%Y-%m-%dT00:00:00Z')
    url = (f"https://data.alpaca.markets/v2/stocks/{sym}/bars"
           f"?timeframe=1Day&start={start}&limit=10")
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=15) as r:
        d = json.load(r)
    bars = d.get('bars') or []
    return bars[-1]['c'] if bars else None

def sma(c, k, i): return sum(c[i+1-k:i+1])/k if i+1 >= k else None

def atr14(bars, i):
    trs = [max(bars[k]['h']-bars[k]['l'], abs(bars[k]['h']-bars[k-1]['c']), abs(bars[k]['l']-bars[k-1]['c']))
           for k in range(i-13, i+1)]
    return sum(trs)/14

def find_pivots(bars, k=5):
    ph, pl = {}, {}
    for i in range(k, len(bars)-k):
        wh = [bars[j]['h'] for j in range(i-k, i+k+1)]
        wl = [bars[j]['l'] for j in range(i-k, i+k+1)]
        if bars[i]['h'] == max(wh): ph[i+k] = bars[i]['h']
        if bars[i]['l'] == min(wl): pl[i+k] = bars[i]['l']
    return ph, pl

def nearest(pivots, by, price, below):
    bi, bp = None, None
    for idx, lvl in pivots.items():
        if idx > by: continue
        if below and lvl >= price: continue
        if not below and lvl <= price: continue
        if bi is None or idx > bi: bi, bp = idx, lvl
    return bp


def levels_both_sides(bars, ph, pl, i, price, atr=None):
    """Nearest confirmed pivots above and below price. Returns the 3 nearest
    each side -- a single nearest is misleading when a noise-level pivot sits
    right next to price and hides the real level (VRT 2026-08-18: nearest
    resistance computed $270.91 / +0.5%, while the level that mattered was
    $286.36 / +6.2%). Also marks the nearest SIGNIFICANT level, defined as
    at least 1x ATR away, so noise pivots never masquerade as structure."""
    ups = sorted([v for k,v in ph.items() if k<=i and v>price])[:3]
    dns = sorted([v for k,v in pl.items() if k<=i and v<price], reverse=True)[:3]
    def pct(v): return round((v-price)/price*100,2)
    sig_up = next((v for v in ups if atr is None or (v-price) >= atr), None)
    sig_dn = next((v for v in dns if atr is None or (price-v) >= atr), None)
    return {
        "resistances": [{"level": round(v,2), "pct": pct(v)} for v in ups],
        "supports":    [{"level": round(v,2), "pct": pct(v)} for v in dns],
        "sigResistance": {"level": round(sig_up,2), "pct": pct(sig_up)} if sig_up else None,
        "sigSupport":    {"level": round(sig_dn,2), "pct": pct(sig_dn)} if sig_dn else None,
    }

def detect_break(bars, closes, i, atr, hold=1, window=5, k=10, decisive=1.0):
    """Breakout/breakdown: a decisive close THROUGH a MAJOR pivot that then HELD.
    Distinct from a sweep (wick through + close BACK through = rejection).

    hold=1, NOT 3. Tested 2026-08-18 (30 names, 4H, 2026 YTD, 754-1284
    trades/setting): hold 0 = -11.88R (only losing setting), hold 1 =
    +25.79R (best total), 2 = +7.61R, 3 = +22.66R, 4 = +19.09R. Settings
    1-4 tie on per-trade edge, so take the earliest that works. The SWEEP
    proxy keeps its 3-bar hold -- different pattern, own backtest.

    TWO NOISE FILTERS, added 2026-08-19 after a NASDAQ-100 run flagged 88 of
    97 tickers (91%) -- a 'signal' that fires on nearly everything carries no
    information:
      k=10 (not 5): the level must be a MAJOR pivot -- the extreme of 21 bars,
        not 11. 5-bar fractals litter the chart with minor pivots, so almost
        any close crosses one.
      decisive=1.0: the close must clear the level by >= 1x ATR. A hairline
        close through a level is not a break.
      window=5 (not 12): only RECENT breaks are actionable. A break 12 bars
        old that is still holding is just 'price is trending' -- it is not an
        alert. 5 bars is ~1 trading day on 4H.
    """
    ph, pl = find_pivots(bars, k=k)
    out = None
    for s in range(max(k+1, i-window), i-hold+1):
        L = max([v for kk,v in pl.items() if kk<=s-1 and v<closes[s-1]], default=None)
        if (L and closes[s-1] > L and closes[s] < L - decisive*atr
                and all(closes[d] < L for d in range(s, i+1))):
            out = {"dir":"breakdown","bias":"short","level":round(L,2),
                   "date":bars[s]['t'][:10],"barsHeld":i-s}
        H = min([v for kk,v in ph.items() if kk<=s-1 and v>closes[s-1]], default=None)
        if (H and closes[s-1] < H and closes[s] > H + decisive*atr
                and all(closes[d] > H for d in range(s, i+1))):
            out = {"dir":"breakout","bias":"long","level":round(H,2),
                   "date":bars[s]['t'][:10],"barsHeld":i-s}
    return out

def detect_squeeze(bars, i, n=10, shrink=0.7, flat_tol=0.02):
    """Range contracting into a flat multi-touch level."""
    if i < 2*n: return None
    recent = bars[i-n+1:i+1]; prior = bars[i-2*n+1:i-n+1]
    ar = sum(b['h']-b['l'] for b in recent)/n
    ap = sum(b['h']-b['l'] for b in prior)/n
    if ap <= 0 or ar >= ap*shrink: return None
    hi = max(b['h'] for b in recent)
    touches = sum(1 for b in recent if b['h'] >= hi*(1-flat_tol))
    if touches < 3: return None
    return {"flatLevel": round(hi,2), "touches": touches,
            "rangeShrinkPct": round((1-ar/ap)*100,1)}

def analyze(sym):
    bars = fetch_bars(sym)
    if len(bars) < 250: return {"symbol": sym, "error": f"only {len(bars)} bars"}
    closes = [b['c'] for b in bars]
    n = len(closes); i = n-1

    # Split check across FULL history.
    # Band is deliberately WIDE (any ratio <0.55 or >1.8), not a 2:1-only test.
    # The old 0.47-0.53 / 1.9-2.1 window only caught 2-for-1 splits and let
    # BKNG's ~20:1 (ratio 0.042, 2026-04-06) and NFLX's ~10:1 (ratio 0.099,
    # 2025-11-17) through -- both surfaced as screener hits on 2026-08-19 with
    # SMAs computed across pre- and post-split prices. BKNG's gave itself away
    # with a 'resistance' 1,805% above price; NFLX's did not, which is why the
    # band matters more than spotting absurd output.
    # A genuine >45% single-bar move is possible but rare; dropping one real
    # mover is far cheaper than trading off a corrupted SMA.
    for a, b in zip(closes[:-1], closes[1:]):
        if a and b and (b/a < 0.55 or b/a > 1.8):
            return {"symbol": sym, "error": "split artifact in history"}

    # recency check
    last_t = datetime.datetime.fromisoformat(bars[-1]['t'].replace('Z','+00:00'))
    age_days = (datetime.datetime.now(datetime.timezone.utc) - last_t).days
    if age_days > 5: return {"symbol": sym, "error": f"stale data ({age_days}d old)"}

    price = closes[i]
    s50, s150, s200 = sma(closes,50,i), sma(closes,150,i), sma(closes,200,i)
    s200_20 = sma(closes,200,i-20)
    atr = atr14(bars, i)
    yr = [b for b in bars if datetime.datetime.fromisoformat(b['t'].replace('Z','+00:00')) >= last_t - datetime.timedelta(days=365)]
    hi52, lo52 = max(b['h'] for b in yr), min(b['l'] for b in yr)
    off_high = (price-hi52)/hi52*100
    above_low = (price-lo52)/lo52*100
    dist50 = (price-s50)/s50*100

    # Trend = 3 SMA conditions only. 52-week high/low rules removed 2026-08-18.
    long_t = price > s50 > s150 > s200 and s200 > s200_20
    short_t = price < s50 < s150 < s200 and s200 < s200_20

    signal = None
    if long_t and 2 <= dist50 <= 5: signal = "LONG (trend entry)"
    elif short_t and -5 <= dist50 <= -2: signal = "SHORT (trend entry)"
    elif long_t and dist50 >= 20: signal = "SHORT (fade - extended up)"
    elif short_t and dist50 <= -20: signal = "LONG (fade - extended down)"

    # sweep proxy
    ph, pl = find_pivots(bars)
    sweep = None
    for s in range(max(6, i-15), i-2):
        L = nearest(pl, s-1, closes[s], True)
        if L and bars[s]['l'] < L and bars[s]['c'] > L and all(closes[d] > L for d in range(s+1, i+1)):
            sweep = {"dir": "bullish", "level": round(L,2), "date": bars[s]['t'][:10], "barsHeld": i-s}
    for s in range(max(6, i-15), i-2):
        L = nearest(ph, s-1, closes[s], False)
        if L and bars[s]['h'] > L and bars[s]['c'] < L and all(closes[d] < L for d in range(s+1, i+1)):
            sweep = {"dir": "bearish", "level": round(L,2), "date": bars[s]['t'][:10], "barsHeld": i-s}

    lv = levels_both_sides(bars, ph, pl, i, price, atr)
    brk = detect_break(bars, closes, i, atr)
    sqz = detect_squeeze(bars, i)

    real = latest_price(sym)
    verified = real is not None and abs(real-price)/price < 0.03

    return {"symbol": sym, "price": round(price,2), "realPrice": real, "verified": verified,
            "sma50": round(s50,2), "sma150": round(s150,2), "sma200": round(s200,2),
            "sma200Rising": s200 > s200_20, "dist50Pct": round(dist50,2),
            "offHighPct": round(off_high,2), "aboveLowPct": round(above_low,2),
            "atr14": round(atr,2), "longTemplate": long_t, "shortTemplate": short_t,
            "signal": signal, "sweep": sweep,
            "levels": lv, "breakSetup": brk, "squeeze": sqz}

if __name__ == "__main__":
    syms = sys.argv[1].split(",")
    out = []
    for s in syms:
        r = analyze(s)
        out.append(r)
        print(json.dumps(r, indent=2))
    json.dump(out, open("/tmp/claude-0/-home-user-ipad/b190a594-2c3a-5b59-b4b1-611265df878e/scratchpad/full_check_out.json","w"), indent=2)
