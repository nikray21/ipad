"""alpaca_data.py — stdlib-only client for Alpaca's Market Data API.

The TA tools (`liquidity_swings.py`, `trade_setup.py`) get their bars from
here and nowhere else. That is a hard rule Nikil set: no Yahoo, no Nasdaq, no
Webull chart data feeding a swing-trade decision, full stop. The rest of the
pipeline (`marketdata.py` — fundamentals, quotes, the deck charts) is
untouched; this module exists so the TA tools never have to import it.

Auth: `APCA_API_KEY_ID` / `APCA_API_SECRET_KEY` from the environment. Get a
free key at https://alpaca.markets (a Paper or Live account both work for
market data) and export both — in your shell profile on the Mac, or before
running these tools in a cloud session. Never commit real values: keep them
out of CLAUDE.md, git, everywhere tracked. `.env.example` documents the two
variable names with no values filled in.

Free accounts get `feed="iex"` (the Investors Exchange's consolidated tape,
recent bars delayed ~15 minutes). `feed="sip"` is the full consolidated tape
and needs a paid subscription. Defaults to iex since that works on every
plan; pass `feed="sip"` once there's a subscription.

    from alpaca_data import bars
    bars("NBIS", "1Hour", days=400)
"""

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

_BASE = "https://data.alpaca.markets/v2/stocks"


def _headers():
    key = os.environ.get("APCA_API_KEY_ID")
    secret = os.environ.get("APCA_API_SECRET_KEY")
    if not key or not secret:
        raise RuntimeError(
            "APCA_API_KEY_ID / APCA_API_SECRET_KEY not set. Export both "
            "(see .env.example) — free key at https://alpaca.markets"
        )
    return {"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": secret}


def _parse_ts(s):
    """Alpaca's bar timestamps are RFC3339 UTC, fractional seconds or not."""
    s = s.rstrip("Z")
    if "." in s:
        s = s.split(".")[0]
    dt = datetime.strptime(s, "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


def bars(symbol, timeframe="1Hour", days=400, feed="iex", adjustment="split"):
    """OHLCV bars for one symbol, oldest first: {t: epoch_ms, o, h, l, c, v}.

    `timeframe` is Alpaca's own vocabulary ('1Hour', '1Day', '15Min', ...).
    `adjustment='split'` matches what a chart shows across a stock split —
    the alternative 'all' (splits + dividends) would shift historical closes
    in a way a swing trader's own chart doesn't; 'raw' applies neither.
    Regular trading hours only — Alpaca omits extended-hours bars unless
    asked for them, which nothing here does.
    """
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)
    params = {
        "timeframe": timeframe,
        "start": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "end": end.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "limit": "10000",
        "feed": feed,
        "adjustment": adjustment,
    }
    out = []
    headers = _headers()
    url = f"{_BASE}/{symbol}/bars?{urllib.parse.urlencode(params)}"
    while url:
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.load(resp)
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")
            raise RuntimeError(f"Alpaca {e.code} for {symbol}: {body}") from None
        for b in data.get("bars") or []:
            out.append({
                "t": _parse_ts(b["t"]),
                "o": b["o"], "h": b["h"], "l": b["l"], "c": b["c"], "v": b["v"],
            })
        token = data.get("next_page_token")
        url = (f"{_BASE}/{symbol}/bars?{urllib.parse.urlencode({**params, 'page_token': token})}"
               if token else None)
    if not out:
        raise RuntimeError(f"no Alpaca bars for {symbol} ({timeframe}, feed={feed})")
    return out


if __name__ == "__main__":
    import sys
    sym = sys.argv[1] if len(sys.argv) > 1 else "AAPL"
    b = bars(sym, "1Hour", days=5)
    print(f"{sym}: {len(b)} bars, last close {b[-1]['c']}")
