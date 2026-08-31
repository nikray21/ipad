"""
marketdata.py — the deck pipeline's own market-data layer.

The build used to fetch from the Terminal on 127.0.0.1:4747. That made a video
deck depend on a long-running server that also hosts the live trading system, so
the data layer now lives here and the pipeline stands alone.

**These builders are lifted verbatim from the Terminal's server.py.** That is
deliberate. Every one of them encodes a data trap that was found the hard way —
how a quarter is derived from cumulative XBRL figures, which revenue tags to try
in which order, how splits are normalised, why the freshness ceilings are what
they are. Reimplementing them would have meant rediscovering all of it, and the
whole point of this pipeline is that its numbers are trustworthy.

Upstreams, all public and key-free, exactly the ones the Terminal used:
  * SEC XBRL companyfacts + submissions  — fundamentals and the filing index
  * Yahoo chart API                      — daily bars and the live quote
  * Nasdaq api                           — profile, analyst ratings, estimates

Same on-disk cache contract as the Terminal: serve fast, refresh in the
background, stamp every payload with `_fetchedAt` / `_ageS`, and never hand back
a stale price — `max_stale=0` means block and refetch past TTL.

    from marketdata import get
    snap = get("quote", "PLTR")
"""

import gzip
import hashlib
import io
import json
import os
import re
import threading
import time
import urllib.parse
import urllib.request
from zoneinfo import ZoneInfo
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime as _dt, timedelta

BROWSER_UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
              "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36")
SEC_UA = "NikRayaniTerminal/1.0 (nikilrayani18@gmail.com)"
YAHOO_UA = "Mozilla/5.0"
_cache = {}
_cache_lock = threading.Lock()
_pool = ThreadPoolExecutor(max_workers=12)
_fanout = ThreadPoolExecutor(max_workers=6)    # small parallel fetches (street)
_inflight = set()
_inflight_lock = threading.Lock()
SCHEMA = "v17"          # bump when a payload shape changes; invalidates old cache
CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".cache_market")
_ET = ZoneInfo("America/New_York")
QFRAME = re.compile(r"^CY(\d{4})Q(\d)$")
AFRAME = re.compile(r"^CY(\d{4})$")
_SPLIT_RATIOS = (2, 3, 4, 5, 6, 7, 8, 10, 15, 20, 25, 30, 40, 50, 100)

def _disk_path(key):
    return os.path.join(CACHE_DIR, hashlib.sha1((SCHEMA + key).encode()).hexdigest() + ".json")

def _disk_read(key):
    try:
        with open(_disk_path(key)) as f:
            return json.load(f)
    except Exception:
        return None

def _disk_write(key, entry):
    try:
        tmp = _disk_path(key) + ".tmp"
        with open(tmp, "w") as f:
            json.dump(entry, f)
        os.replace(tmp, _disk_path(key))
    except Exception:
        pass

def market_state(now=None):
    """"open" during regular US cash hours, "ext" pre/post, "closed" otherwise.

    Deliberately ignores market holidays: on a holiday this reports "open" and
    every price TTL runs at its tightest setting. That direction of error costs
    a few redundant fetches; the other direction would serve day-old prices as
    live, which is the failure this whole module exists to prevent.
    """
    n = (now or _dt.now(tz=_ET)).astimezone(_ET)
    if n.weekday() >= 5:
        return "closed"
    mins = n.hour * 60 + n.minute
    if 570 <= mins < 960:            # 09:30–16:00 ET
        return "open"
    if 240 <= mins < 570 or 960 <= mins < 1200:   # 04:00–09:30, 16:00–20:00 ET
        return "ext"
    return "closed"

def ttl_for(open_s, ext_s, closed_s):
    """Market-state-aware TTL. Price-bearing data must not be cached on the
    same clock at 3am as at 10am — a flat TTL is either wasteful when the
    market is shut or stale while it is moving."""
    return {"open": open_s, "ext": ext_s, "closed": closed_s}[market_state()]

def cached(key, ttl, producer, disk_ttl=None, max_stale=None):
    """Serve fast, refresh in the background.

    A fresh value is returned immediately. A value past `ttl` but within
    `max_stale` is ALSO returned immediately and refreshed on a worker thread,
    so switching tickers never blocks on the network twice for the same data.
    Past `max_stale` the caller blocks on a real fetch. Values persist to disk,
    so a restart (or a ticker looked at yesterday) is still instant.

    `max_stale=0` disables the stale-serve entirely: never hand out a value
    past its TTL, block and refetch instead. That is the correct setting for
    anything price-bearing while the market is open — the old blanket `ttl * 4`
    meant a 900s history key would serve a value up to a FULL HOUR old with no
    indication whatsoever, which is exactly how a candle chart ends up showing
    the wrong open. Slower is an inconvenience; silently wrong is a defect.

    Every returned payload is stamped with `_fetchedAt` (epoch seconds of the
    upstream fetch) and `_ageS`, so the front end can display the real age
    instead of assuming whatever it got was current.
    """
    key = SCHEMA + ":" + key
    now = time.time()
    with _cache_lock:
        hit = _cache.get(key)
    if hit is None:
        hit = _disk_read(key)
        if hit:
            with _cache_lock:
                _cache[key] = hit

    age = (now - hit["at"]) if hit else None
    if hit and age < ttl:
        return _stamp(hit["val"], hit["at"], now)

    ceiling = (ttl * 4 if disk_ttl is None else disk_ttl) if max_stale is None else max_stale
    if hit and ceiling > 0 and age < ceiling:
        _refresh_async(key, producer)          # stale but usable — hand it over now
        return _stamp(hit["val"], hit["at"], now)

    val = producer()
    fetched = time.time()
    entry = {"val": val, "at": fetched}
    with _cache_lock:
        _cache[key] = entry
    _disk_write(key, entry)
    return _stamp(val, fetched, fetched)

def _stamp(val, fetched_at, now):
    """Attach provenance to a dict payload. Non-dicts (the market table is a
    list) pass through untouched rather than being wrapped into a new shape
    every existing consumer would have to learn."""
    if not isinstance(val, dict):
        return val
    out = dict(val)
    out["_fetchedAt"] = round(fetched_at, 3)
    out["_ageS"] = round(max(0.0, now - fetched_at), 1)
    return out

def _refresh_async(key, producer):
    with _inflight_lock:
        if key in _inflight:
            return
        _inflight.add(key)

    def run():
        try:
            val = producer()
            entry = {"val": val, "at": time.time()}
            with _cache_lock:
                _cache[key] = entry
            _disk_write(key, entry)
        except Exception:
            pass
        finally:
            with _inflight_lock:
                _inflight.discard(key)
    _pool.submit(run)

def fetch(url, ua=BROWSER_UA, cookie=None, timeout=15):
    headers = {"User-Agent": ua, "Accept": "application/json,text/*,*/*",
               "Accept-Encoding": "gzip"}
    if cookie:
        headers["Cookie"] = cookie
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read()
    if r.headers.get("Content-Encoding") == "gzip":
        raw = gzip.GzipFile(fileobj=io.BytesIO(raw)).read()
    return raw

def fetch_json(url, **kw):
    return json.loads(fetch(url, **kw))

def yf(symbol):
    """Symbol in Yahoo's dialect.

    Share classes are written with a dot nearly everywhere (BRK.B, BF.B — that
    is how the indices, the exchanges and every human writes them) but Yahoo
    keys them with a hyphen. Sending the dot form returns an empty result with
    no error, so Berkshire Hathaway B — a top-ten S&P 500 constituent — simply
    drew no chart, silently. Only the last dot-segment is a class suffix; a
    plain dot-free symbol passes through untouched.
    """
    if "." in symbol:
        head, _, tail = symbol.rpartition(".")
        if head and len(tail) <= 2 and tail.isalpha():
            return f"{head}-{tail}"
    return symbol

def cik_for(symbol):
    def load():
        data = fetch_json("https://www.sec.gov/files/company_tickers.json", ua=SEC_UA)
        return {v["ticker"].upper(): str(v["cik_str"]).zfill(10) for v in data.values()}
    return cached("cik_map", 86400, load).get(symbol)

def _split_normalize(eps, shares):
    """Put the EPS and share-count series on ONE basis: the current one.

    A stock split makes every prior per-share figure incomparable, and the
    filings do not fix this for you. A company restates a prior quarter only
    when a later filing happens to show it as a comparative, so after NFLX's
    10-for-1 split its Q1'25 EPS was restated to 0.66 while Q3'25 sat
    untouched at the pre-split 5.87 — the next filing to carry Q3 as a
    comparative is not due until Q3'26. Charting those together produced a
    sawtooth that looked like Netflix's earnings collapsing and recovering by
    10x every other quarter, and the derived-Q4 arithmetic (FY minus three
    quarters, across two bases) turned Q4'24 into an EPS of −13.58.

    Net income is split-invariant, and each period's EPS and share count come
    from the same filing, so `eps x shares` is a true dollar amount and the
    ratio of a period's share count to the newest one exposes that period's
    basis directly. Dividing out that factor is therefore not a guess — it is
    the same arithmetic the filer will publish when it eventually restates.

    The share counts are normalised too, and that matters as much as the EPS:
    every hole-filling path here derives EPS as net income over the nearest
    share count, so a share count left on a stale basis reintroduces the same
    10x error through the back door.

    Returns (normalised_eps, normalised_shares, adjusted_period_count).
    """
    if not shares:
        return eps, shares, 0
    ref_end = max(shares)
    ref = shares.get(ref_end)
    if not ref:
        return eps, shares, 0
    eps_out, sh_out, adjusted = dict(eps), dict(shares), 0
    for end, sh in shares.items():
        if not sh:
            continue
        ratio = ref / sh
        if 0.67 <= ratio <= 1.5:
            continue                       # same basis (organic drift only)
        factor = next((f for f in _SPLIT_RATIOS if abs(ratio / f - 1) < 0.12), None)
        if factor is None:
            factor = next((1.0 / f for f in _SPLIT_RATIOS if abs(ratio * f - 1) < 0.12), None)
        if factor is None:
            continue                       # unrecognised — leave the values as filed
        sh_out[end] = sh * factor          # up to the current basis
        if end in eps_out and eps_out[end] is not None:
            eps_out[end] = round(eps_out[end] / factor, 4)
        adjusted += 1
    return eps_out, sh_out, adjusted

def _latest_filed(facts):
    """One fact per reporting period — the most recently FILED one.

    A restatement supersedes the original, and for per-share figures that is
    not a nicety, it is the difference between a real series and a corrupt one.
    NFLX split 10-for-1: Q1'25 EPS was first filed as 6.61, then restated to
    0.66 on the post-split basis. SEC's `frame` field marks only one fact per
    frame and is NOT applied consistently across periods — it pointed at the
    restated 0.66 for CY2025Q1 but at the *pre-split* 5.87 for CY2025Q3, which
    never got re-framed. Trusting `frame` alone therefore interleaved two
    different share bases in one EPS series, and the derived-Q4 arithmetic on
    top of that produced a −13.58 EPS for a quarter Netflix was profitable in.

    Keying on the period and keeping the newest filing puts the whole series on
    one basis — the current one — for every filer, split or not.
    """
    best = {}
    for u in facts:
        if u.get("val") is None or not u.get("end"):
            continue
        period = (u.get("start"), u["end"])
        prev = best.get(period)
        # `filed` is ISO, so a string compare is a date compare. `fy`/`fp` break
        # ties within one filing date deterministically rather than by dict order.
        if prev is None or (u.get("filed", ""), str(u.get("fy", "")), str(u.get("fp", ""))) > \
                          (prev.get("filed", ""), str(prev.get("fy", "")), str(prev.get("fp", ""))):
            best[period] = u
    # Preserve ascending period order so downstream `setdefault` logic still
    # sees oldest-first, exactly as it did when reading the raw array.
    return sorted(best.values(), key=lambda u: (u["end"], u.get("start") or ""))

def series(gaap, tags, unit="USD", derive=True):
    """Quarterly series [(end_date, value)] oldest first.

    Companies migrate between XBRL tags over the years, so every candidate tag is
    read and the one with the most recent coverage wins; older tags only backfill
    quarters the newer tag doesn't cover. A missing Q4 is derived as FY minus the
    year's three reported quarters.
    """
    per_tag = []
    for tag in tags:
        node = gaap.get(tag)
        if not node:
            continue
        quarters, annuals = {}, {}
        facts = _latest_filed(node["units"].get(unit, []))
        for u in facts:
            fr = u.get("frame")
            if not fr:
                continue
            if (m := QFRAME.match(fr)):
                quarters.setdefault((int(m.group(1)), int(m.group(2))), (u["end"], u["val"]))
            elif AFRAME.match(fr):
                annuals.setdefault(u["end"], (u.get("start"), u["val"]))
        if not quarters:
            # Some tags carry no SEC frames — detect quarters by period length instead
            for u in facts:
                s, e = u.get("start"), u.get("end")
                if not s or u.get("form") not in ("10-Q", "10-K"):
                    continue
                try:
                    days = (date.fromisoformat(e) - date.fromisoformat(s)).days
                except ValueError:
                    continue
                if 80 <= days <= 100:
                    ed = date.fromisoformat(e)
                    quarters.setdefault((ed.year, (ed.month - 1) // 3 + 1), (e, u["val"]))
        if quarters:
            newest = max(end for end, _ in quarters.values())
            per_tag.append((newest, quarters, annuals))

    if not per_tag:
        return []
    per_tag.sort(key=lambda t: t[0], reverse=True)   # most recently used tag first
    quarters, annuals = {}, {}
    for _, qs, ans in per_tag:
        for k, v in qs.items():
            quarters.setdefault(k, v)
        for k, v in ans.items():
            annuals.setdefault(k, v)

    if not derive:
        seen0, out0 = set(), []
        for _, (e, v) in sorted(quarters.items(), key=lambda kv: kv[1][0]):
            if e not in seen0:
                seen0.add(e)
                out0.append((e, v))
        return out0

    # Derive the unreported quarter on the FILER'S fiscal calendar: take each annual
    # period and subtract the quarters that fall inside its own window. Grouping by
    # calendar year breaks for Sept/June/Jan year-ends (Apple, Microsoft, Nvidia).
    by_end = {end: key for key, (end, _) in quarters.items()}
    for a_end, (a_start, total) in annuals.items():
        if not a_start or a_end in by_end:
            continue
        inside = [(e, v) for (e, v) in quarters.values() if a_start < e <= a_end]
        if len(inside) != 3:
            continue
        derived = total - sum(v for _, v in inside)
        sibling = sorted(abs(v) for _, v in inside)[1]
        if sibling and abs(derived) > 3 * sibling:
            continue                       # fiscal-boundary artifact, not a quarter
        d = date.fromisoformat(a_end)
        quarters[(d.year, (d.month - 1) // 3 + 1, a_end)] = (a_end, derived)

    seen, out = set(), []
    for _, (e, v) in sorted(quarters.items(), key=lambda kv: kv[1][0]):
        if e not in seen:
            seen.add(e)
            out.append((e, v))
    return out

def flow_series(gaap, tags, unit="USD"):
    """Quarterly values for CUMULATIVE (year-to-date) line items.

    Cash-flow statements in 10-Qs are reported year-to-date, so SEC only frames
    Q1 as a discrete quarter. Recover the rest by differencing consecutive YTD
    periods that share a fiscal-year start: Q2 = H1 - Q1, Q3 = 9M - H1, Q4 = FY - 9M.
    Directly-reported quarters beat derived ones, and — as elsewhere — the tag with
    the most recent coverage wins, since filers migrate tags over the years.
    """
    per_tag = []
    for tag in tags:
        node = gaap.get(tag)
        if not node:
            continue
        direct, buckets = {}, {}
        for u in node["units"].get(unit, []):
            s, e, v = u.get("start"), u.get("end"), u.get("val")
            if not s or not e or v is None:
                continue
            try:
                days = (date.fromisoformat(e) - date.fromisoformat(s)).days
            except ValueError:
                continue
            framed_quarter = bool(QFRAME.match(u.get("frame") or ""))
            if not framed_quarter and u.get("form") not in ("10-Q", "10-K"):
                continue
            if framed_quarter or days <= 100:
                direct.setdefault(e, v)
            # A reported Q1 is ALSO the first link of the year-to-date chain, so it
            # belongs in the bucket as well — otherwise Q2 has nothing to subtract from.
            if days <= 400:
                buckets.setdefault(s, {}).setdefault(e, v)

        derived = {}
        for bstart, ends in buckets.items():
            prev_end, prev_val = bstart, 0.0
            for e, v in sorted(ends.items()):
                try:
                    span = (date.fromisoformat(e) - date.fromisoformat(prev_end)).days
                except ValueError:
                    break
                if 80 <= span <= 100:
                    derived.setdefault(e, v - prev_val)
                prev_end, prev_val = e, v

        merged = dict(derived)
        merged.update(direct)
        if merged:
            per_tag.append((max(merged), merged))

    if not per_tag:
        return []
    per_tag.sort(key=lambda t: t[0], reverse=True)
    out = {}
    for _, vals in per_tag:
        for k, v in vals.items():
            out.setdefault(k, v)
    return sorted(out.items())

def instants(gaap, tags, unit="USD"):
    """Point-in-time series [(end_date, value)], newest-covering tag preferred."""
    per_tag = []
    for tag in tags:
        node = gaap.get(tag)
        if not node:
            continue
        vals = {}
        for u in node["units"].get(unit, []):
            fr = u.get("frame", "")
            if fr.startswith("CY") and fr.endswith("I"):
                vals.setdefault(u["end"], u["val"])
        if vals:
            per_tag.append((max(vals), vals))
    if not per_tag:
        return []
    per_tag.sort(key=lambda t: t[0], reverse=True)
    merged = {}
    for _, vals in per_tag:
        for k, v in vals.items():
            merged.setdefault(k, v)
    return sorted(merged.items())

def at_or_before(pairs, end, max_age_days=None):
    """Latest value in `pairs` dated at or before `end`.

    With max_age_days set, a value older than that is treated as absent. Ford
    stopped reporting consolidated debt under the standard tags years ago, and
    without the window this quietly served the last old figure — the screen
    showed debt/equity 0.01x for a company carrying Ford Credit. A stale
    balance-sheet figure is worse than a missing one.
    """
    best = None
    for d, v in pairs:
        if d <= end:
            if max_age_days is not None and \
               (date.fromisoformat(end) - date.fromisoformat(d)).days > max_age_days:
                continue
            best = v
    return best

def fq_label(end_iso):
    d = date.fromisoformat(end_iso)
    q = (d.month - 1) // 3 + 1
    return f"Q{q}'{str(d.year)[2:]}", d.strftime("%b '%y")

def build_fundamentals(symbol):
    """SEC XBRL first — authoritative, same-day on filing. Filers it cannot
    serve (foreign issuers, sparse taggers) fall through to Yahoo's quarterly
    statements rather than to an apology: the deck must WORK for any ticker
    searched on camera, and say which source it is standing on."""
    cik = cik_for(symbol)
    if not cik:
        return build_fundamentals_yahoo(symbol)
    facts = fetch_json(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json",
                       ua=SEC_UA, timeout=45)
    gaap = facts.get("facts", {}).get("us-gaap", {})
    if not gaap:
        return build_fundamentals_yahoo(symbol)

    REV_TAGS = ["RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues",
                "RevenueFromContractWithCustomerIncludingAssessedTax",
                "RevenuesNetOfInterestExpense", "SalesRevenueNet"]
    rev = series(gaap, REV_TAGS)
    net_probe = dict(series(gaap, ["NetIncomeLoss", "ProfitLoss"]))
    # Sanity: some filers tag only a revenue COMPONENT (a fee line) under the
    # modern tag. Revenue below net income is the tell — try the other tags and
    # keep whichever reports the largest top line for the same period.
    if rev and net_probe:
        end, val = rev[-1]
        ni = net_probe.get(end)
        if ni is not None and val < abs(ni):
            for alt_tag in REV_TAGS:
                alt = series(gaap, [alt_tag])
                if alt and alt[-1][0] == end and alt[-1][1] > val:
                    rev, val = alt, alt[-1][1]
    gross = dict(series(gaap, ["GrossProfit"]))
    cogs = dict(series(gaap, ["CostOfRevenue", "CostOfGoodsAndServicesSold"]))
    opinc = dict(series(gaap, ["OperatingIncomeLoss"]))
    net = dict(series(gaap, ["NetIncomeLoss", "ProfitLoss"]))
    opex = dict(series(gaap, ["OperatingExpenses", "CostsAndExpenses"]))
    rd = dict(series(gaap, ["ResearchAndDevelopmentExpense",
                            "ResearchAndDevelopmentExpenseExcludingAcquiredInProcessCost",
                            "TechnologyAndInfrastructureExpense",
                            "TechnologyAndContentExpense"]))
    # derive=False on EPS: a missing Q4 must NOT be back-solved as
    # FY minus three quarters here. Across a split those four numbers sit on
    # two different share bases, and the subtraction turns into nonsense
    # (Netflix's Q4'24 came out as an EPS of −13.58). Q4 is filled further
    # down from net income over a normalised share count instead, which is
    # basis-safe because net income is dollars.
    eps = dict(series(gaap, ["EarningsPerShareDiluted"], unit="USD/shares", derive=False))
    shares = dict(series(gaap, ["WeightedAverageNumberOfDilutedSharesOutstanding",
                                "WeightedAverageNumberOfSharesOutstandingBasic"],
                         unit="shares", derive=False))
    eps, shares, splitAdj = _split_normalize(eps, shares)
    cfo = dict(flow_series(gaap, ["NetCashProvidedByUsedInOperatingActivities",
                                  "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations"]))
    capex = dict(flow_series(gaap, ["PaymentsToAcquirePropertyPlantAndEquipment",
                                    "PaymentsToAcquireProductiveAssets",
                                    "PaymentsToAcquirePropertyPlantAndEquipmentAndIntangibleAssets"]))
    sbc = dict(flow_series(gaap, ["ShareBasedCompensation",
                                  "AllocatedShareBasedCompensationExpense"]))
    fcfDiv = dict(flow_series(gaap, ["PaymentsOfDividends", "PaymentsOfDividendsCommonStock"]))
    buyback = dict(flow_series(gaap, ["PaymentsForRepurchaseOfCommonStock"]))
    inv = instants(gaap, ["InventoryNet"])
    ar = instants(gaap, ["AccountsReceivableNetCurrent", "ReceivablesNetCurrent"])
    equity = instants(gaap, ["StockholdersEquity"])
    assets = instants(gaap, ["Assets"])
    debt = instants(gaap, ["LongTermDebtNoncurrent", "LongTermDebt"])
    cash = instants(gaap, ["CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
                           "CashAndCashEquivalentsAtCarryingValue"])

    B = 1e9
    quarters = []
    # 12 quarters, not 9: the TTM series needs four to warm up, so nine gave
    # the price-vs-earnings chart only 15 months of steps instead of two years.
    for end, r in rev[-12:]:
        if not r:
            continue
        g = gross.get(end)
        c = cogs.get(end)
        if g is None and c is not None:
            g = r - c
        oi = opinc.get(end)
        ni = net.get(end)
        # Gross profit is optional: plenty of filers (marketplaces, banks, some
        # service businesses) never report it. Keep the quarter and let the client
        # hide the gross-margin views rather than dropping the company entirely.
        if oi is None and ni is None:
            continue
        label, short = fq_label(end)
        ox = opex.get(end)
        if ox is None and g is not None and oi is not None:
            ox = g - oi
        quarters.append({
            "label": label, "end": short, "endDate": end,
            "revenue": round(r / B, 3),
            "gross": round(g / B, 3) if g is not None else None,
            "opInc": round(oi / B, 3) if oi is not None else None,
            "netInc": round(ni / B, 3) if ni is not None else None,
            "opex": round(ox / B, 3) if ox is not None else None,
            "rd": round(rd[end] / B, 3) if end in rd else None,
            "eps": round(eps[end], 2) if end in eps else None,
            "shares": round(shares[end] / 1e6, 1) if end in shares else None,
            "cfo": round(cfo[end] / B, 3) if end in cfo else None,
            "capex": round(abs(capex[end]) / B, 3) if end in capex else None,
            "sbc": round(sbc[end] / B, 3) if end in sbc else None,
            "dividends": round(abs(fcfDiv[end]) / B, 3) if end in fcfDiv else None,
            "buyback": round(abs(buyback[end]) / B, 3) if end in buyback else None,
            "inventory": (lambda v: round(v / B, 3) if v else None)(at_or_before(inv, end)),
            "receivables": (lambda v: round(v / B, 3) if v else None)(at_or_before(ar, end)),
            "equity": (lambda v: round(v / B, 3) if v else None)(at_or_before(equity, end)),
            "assets": (lambda v: round(v / B, 3) if v else None)(at_or_before(assets, end)),
            "debt": (lambda v: round(v / B, 3) if v else None)(
                at_or_before(debt, end, max_age_days=400)),
            "cash": (lambda v: round(v / B, 3) if v else None)(at_or_before(cash, end)),
        })
    # ---- Graham's long-window measures -------------------------------------
    # The charts want 8 quarters; these two want a decade. Kept separate so the
    # slice above stays untouched.
    #
    # Normalised earnings: EPS averaged over five years, so one peak-cycle year
    # cannot flatter the multiple. Graham's whole objection to a trailing P/E.
    # Built from net income over diluted shares, not from the per-share tag.
    # The tag is the fragile one: SEC assigned HAL no annual EPS frame after
    # 2019, so reading it left a decade-stale series and a 2012-2016 valuation
    # average. Net income and share counts are continuous, and their ratio is
    # the same number. Q4 carries no share count of its own by design, so the
    # nearest quarter's stands in — diluted counts drift by ~1% a quarter.
    _share_ends = sorted(shares)

    def _shares_near(end):
        if shares.get(end):
            return shares[end]
        if not _share_ends:
            return None
        target = date.fromisoformat(end)
        return shares[min(_share_ends,
                          key=lambda e: abs((date.fromisoformat(e) - target).days))]

    # Net income over shares is NOT the reported figure for every filer:
    # diluted EPS is income attributable to COMMON holders, after preferred
    # dividends and minority interests. For RITM the raw ratio ran 2x the
    # reported number. So the derivation is calibrated: the median ratio of
    # reported to derived, over quarters where both exist, captures that
    # company's attributable-to-common haircut and scales every derived value.
    #
    # Calibrate ONLY where the share count is from the very same period. The
    # nearest-quarter fallback is right for filling a hole but ruinous here:
    # GOOGL's pre-2022-split quarters still carry ~$27 EPS while its share
    # counts only go back to 2023 (post 20-for-1), so the fallback paired a
    # pre-split EPS against a post-split share count and produced a ratio of
    # ~18. That became the median, and every derived Q4 was multiplied by it —
    # Alphabet's Q4'25 EPS rendered as 51.20 against a true 2.82.
    # The [0.2, 5] guard is the backstop: an attributable-to-common haircut is
    # a haircut, never an 18x multiplier, so anything outside that band is a
    # basis mismatch rather than a real adjustment and must not be averaged in.
    _pairs = []
    for end, ni in net.items():
        sh = shares.get(end)
        rep = eps.get(end)
        if ni is None or not sh or rep is None:
            continue
        drv = ni / sh
        if abs(rep) >= 0.05 and abs(drv) >= 0.05 and (rep > 0) == (drv > 0):
            ratio = rep / drv
            if 0.2 <= ratio <= 5:
                _pairs.append(ratio)
    _pairs.sort()
    eps_factor = _pairs[len(_pairs) // 2] if _pairs else 1.0

    by_year = {}
    for end, ni in net.items():
        sh = _shares_near(end)
        if ni is None or not sh:
            continue
        rep = eps.get(end)
        # Reported wins wherever it exists; the calibrated ratio only fills holes.
        by_year.setdefault(end[:4], []).append(
            rep if rep is not None else ni / sh * eps_factor)
    # Only whole years — a part-reported year would drag the average down.
    eps_years = {y: round(sum(v), 3) for y, v in sorted(by_year.items()) if len(v) == 4}
    # Dividend record: consecutive years, most recent backwards. Graham's single
    # best durability test — a long streak has already survived recessions.
    div_years = {}
    for end, v in fcfDiv.items():
        if v:
            div_years.setdefault(end[:4], 0)
            div_years[end[:4]] += 1
    # Anchored to the latest filing: a streak that lapsed is zero, not "N as of
    # whenever it stopped". Without the anchor a company that quit paying in
    # 2019 still advertised its old run, and a stale claim about dividends is
    # exactly the kind of thing that gets said out loud on camera.
    latest_yr = int(quarters[-1]["endDate"][:4]) if quarters else None
    streak, yrs = 0, sorted(div_years, reverse=True)
    if yrs and latest_yr and int(yrs[0]) >= latest_yr - 1:
        for i, y in enumerate(yrs):
            if i and int(yrs[i - 1]) - int(y) != 1:
                break
            streak += 1

    # TTM EPS at each quarter, computed from the FULL history BEFORE the
    # 8-quarter display slice — the price-vs-earnings chart needs a rolling
    # four-quarter window over two years, which the sliced payload cannot
    # provide (the chart silently shrank to 13 months trying).
    #
    # knownAt is when the market could actually see the number: the filing
    # date. SEC frames do not retain per-quarter filing dates here, so history
    # uses the typical 10-Q lag; the LATEST quarter uses the real lastFiled —
    # plotting today's blowout at quarter-end backdated it five weeks and made
    # "price follows earnings" look broken on the one day it mattered most.
    ttm_series = []
    _full = quarters[:]
    for i in range(3, len(_full)):
        w = _full[i - 3:i + 1]
        vals = []
        for q_ in w:
            v = q_.get("eps")
            # Q4 has no reported share count of its own (share counts are never
            # derived — that subtraction once produced negative billions of
            # shares), so requiring q_["shares"] here dropped every window
            # containing a Q4. Since EPS stopped being derived inside series()
            # — necessary, because deriving it across a stock split produced
            # nonsense — that meant EVERY window failed and ttmSeries came back
            # empty for every ticker, which is why the price-vs-earnings chart
            # was blank everywhere. Fall back to the nearest quarter's share
            # count, exactly as the per-quarter rebuild below already does.
            if v is None and q_.get("netInc") is not None:
                sh_ = q_.get("shares") or (_shares_near(q_["endDate"]) or 0) / 1e6
                if sh_:
                    v = q_["netInc"] * 1000 / sh_ * eps_factor
            if v is None:
                vals = None
                break
            vals.append(v)
        if vals is not None:
            ttm_series.append({"end": _full[i]["endDate"], "v": round(sum(vals), 3)})
    ttm_series = ttm_series[-10:]

    quarters = quarters[-8:]

    # Rebuild any quarter whose EPS went missing. Two things collide in Q4: SEC
    # never assigned some filers an annual EPS frame (HAL's stops at CY2019), so
    # the derived Q4 has nothing to subtract from; and Q4 share counts are
    # deliberately not derived, because that subtraction once produced negative
    # billions of shares. Net income survives both, and EPS is just net income
    # over shares — so the quarter is recoverable instead of lost. Diluted share
    # counts drift slowly, so the nearest quarter's count is a sound stand-in.
    # Losing one quarter silently voided the whole TTM figure, which is what left
    # HAL with no P/E at all while it was 17% of a real portfolio.
    for i, q in enumerate(quarters):
        if q.get("eps") is not None or q.get("netInc") is None:
            continue
        sh = q.get("shares")
        if not sh:
            for step in range(1, len(quarters)):
                for k in (i - step, i + step):
                    if 0 <= k < len(quarters) and quarters[k].get("shares"):
                        sh = quarters[k]["shares"]
                        break
                if sh:
                    break
        if sh:
            # netInc is in billions, shares in millions. Scaled by the same
            # attributable-to-common calibration the annual series uses.
            q["eps"] = round(q["netInc"] * 1000 / sh * eps_factor, 2)
            q["epsDerived"] = True

    if len(quarters) < 2:
        return build_fundamentals_yahoo(symbol)
    # Refuse to serve figures that are no longer current. Filers with unusual
    # income statements (banks, trusts, some ADRs) can resolve to a tag that
    # stopped being used years ago — showing that on camera would be a disaster.
    age = (date.today() - date.fromisoformat(quarters[-1]["endDate"])).days
    if age > 400:
        return {"error": f"SEC financials for {symbol} look stale "
                         f"(most recent quarter ends {quarters[-1]['endDate']}). "
                         f"This filer's statements don't map to the standard tags."}

    # Most recent filing date across the income-statement tags we used
    filed = ""
    for tag in ("Revenues", "GrossProfit", "OperatingIncomeLoss", "NetIncomeLoss"):
        node = gaap.get(tag)
        if not node:
            continue
        for u in node["units"].get("USD", []):
            f = u.get("filed", "")
            if f > filed:
                filed = f
    return {
        "symbol": symbol,
        "entityName": facts.get("entityName", symbol),
        "cik": cik,
        "lastFiled": filed,
        "latestPeriodEnd": quarters[-1]["endDate"],
        "quarters": quarters,
        # Full-year EPS by calendar year, and the run of consecutive years with a
        # dividend paid. Both feed Graham's checks and need a longer window than
        # the eight quarters the charts draw.
        "epsYears": eps_years,
        "ttmSeries": ttm_series,
        "dividendStreak": streak,
        "source": "SEC EDGAR XBRL companyfacts",
    }

def build_fundamentals_yahoo(symbol):
    """Quarterly fundamentals from Yahoo for filers SEC XBRL cannot serve.

    NIO files as a foreign private issuer — 20-F/6-K, no us-gaap quarters — so
    the deck showed an apology where the analysis should be. Yahoo's
    fundamentals timeseries carries the quarterly statements for ADRs. Same
    payload shape as the SEC path so every render works unchanged; fields
    Yahoo lacks stay null and the charts degrade exactly as they do for a bank.
    """
    import time as _t
    now = int(_t.time())
    types = ("quarterlyTotalRevenue,quarterlyGrossProfit,quarterlyOperatingIncome,"
             "quarterlyNetIncome,quarterlyDilutedEPS,quarterlyOperatingCashFlow,"
             "quarterlyCapitalExpenditure,quarterlyStockholdersEquity,"
             "quarterlyTotalDebt,quarterlyCashAndCashEquivalents,"
             "quarterlyDilutedAverageShares,quarterlyInventory")
    d = fetch_json("https://query1.finance.yahoo.com/ws/fundamentals-timeseries/v1/"
                   f"finance/timeseries/{yf(symbol)}?type={types}"
                   f"&period1={now - 3 * 365 * 86400}&period2={now}", ua=YAHOO_UA)
    series_by, currency = {}, "USD"
    for res in d.get("timeseries", {}).get("result", []):
        key = next((k for k in res if k.startswith("quarterly")), None)
        if not key:
            continue
        for row in res.get(key) or []:
            if row and row.get("reportedValue") is not None:
                series_by.setdefault(row["asOfDate"], {})[key] = row["reportedValue"]["raw"]
                if row.get("currencyCode"):
                    currency = row["currencyCode"]

    B = 1e9
    quarters = []
    for end in sorted(series_by):
        r = series_by[end]
        rev = r.get("quarterlyTotalRevenue")
        if rev is None:
            continue
        sh = r.get("quarterlyDilutedAverageShares")
        capex = r.get("quarterlyCapitalExpenditure")
        quarters.append({
            "label": fq_label(end), "end": end, "endDate": end,
            "revenue": round(rev / B, 3),
            "gross": (lambda v: round(v / B, 3) if v is not None else None)(r.get("quarterlyGrossProfit")),
            "opInc": (lambda v: round(v / B, 3) if v is not None else None)(r.get("quarterlyOperatingIncome")),
            "netInc": (lambda v: round(v / B, 3) if v is not None else None)(r.get("quarterlyNetIncome")),
            "opex": None, "rd": None,
            "eps": r.get("quarterlyDilutedEPS"),
            "shares": round(sh / 1e6, 1) if sh else None,
            "cfo": (lambda v: round(v / B, 3) if v is not None else None)(r.get("quarterlyOperatingCashFlow")),
            "capex": round(abs(capex) / B, 3) if capex is not None else None,
            "sbc": None, "dividends": None, "buyback": None,
            "inventory": (lambda v: round(v / B, 3) if v is not None else None)(r.get("quarterlyInventory")),
            "receivables": None,
            "equity": (lambda v: round(v / B, 3) if v is not None else None)(r.get("quarterlyStockholdersEquity")),
            "assets": None,
            "debt": (lambda v: round(v / B, 3) if v is not None else None)(r.get("quarterlyTotalDebt")),
            "cash": (lambda v: round(v / B, 3) if v is not None else None)(r.get("quarterlyCashAndCashEquivalents")),
        })
    if len(quarters) < 5:
        return {"error": f"Not enough quarterly data for {symbol} from any source"}
    age = (date.today() - date.fromisoformat(quarters[-1]["endDate"])).days
    if age > 400:
        return {"error": f"Financials for {symbol} look stale (latest {quarters[-1]['endDate']})"}

    ttm_series = []
    for i in range(3, len(quarters)):
        w = quarters[i - 3:i + 1]
        if all(q.get("eps") is not None for q in w):
            ttm_series.append({"end": quarters[i]["endDate"], "v": round(sum(q["eps"] for q in w), 3)})

    return {
        "symbol": symbol, "entityName": symbol, "cik": None,
        "lastFiled": quarters[-1]["endDate"],
        "latestPeriodEnd": quarters[-1]["endDate"],
        "quarters": quarters[-8:],
        "epsYears": {}, "ttmSeries": ttm_series[-10:], "dividendStreak": None,
        "fallback": True,
        # A CNY income statement beside a USD share price: every cross-currency
        # ratio (P/E, P/S, earnings yield) must be suppressed client-side, and
        # every money figure labelled. "$25.5B" for a ¥25.5B quarter is a lie.
        "currency": currency,
        "source": f"Yahoo Finance quarterly statements (foreign filer — no SEC XBRL"
                  + (f", reported in {currency}" if currency != "USD" else "") + ")",
    }

# ---------------------------------------------------------------- Alpaca
# Alpaca is the price source for this repo: charts, quotes, and the trade grader
# in .claude/skills/technical-analysis all read the same tape. The Yahoo and
# Nasdaq paths below are kept as a fallback for when no key is configured — a
# missing key should degrade the deck, not blank it — and every payload says
# which one answered, because the one price bug that cost real money (journal
# #15, SBUX) was two feeds disagreeing with nothing to show which was which.
ALPACA = "https://data.alpaca.markets"


def alpaca_headers():
    k = os.environ.get("APCA_API_KEY_ID") or os.environ.get("ALPACA_API_KEY_ID")
    sec = os.environ.get("APCA_API_SECRET_KEY") or os.environ.get("ALPACA_API_SECRET_KEY")
    if not k or not sec:
        return None
    return {"APCA-API-KEY-ID": k, "APCA-API-SECRET-KEY": sec, "Accept": "application/json"}


def alpaca_json(path, hdr, timeout=30):
    req = urllib.request.Request(ALPACA + path, headers=hdr)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def _epoch_ms(iso):
    """Alpaca RFC3339 (nanosecond precision) -> epoch ms, the `t` every chart reads."""
    iso = iso.replace("Z", "+00:00")
    if "." in iso:
        head, rest = iso.split(".", 1)
        iso = f"{head}.{rest[:-6][:6]}{rest[-6:]}"
    return int(_dt.fromisoformat(iso).timestamp() * 1000)


def alpaca_bars(symbol, timeframe, days):
    """OHLCV in the existing chart point shape. Returns [] when unavailable so the
    caller falls through to Yahoo rather than raising into a half-built deck.

    `adjustment=all` — splits AND dividends. A chart that is not adjusted end to
    end draws a gap that looks like a selloff and isn't one.
    """
    hdr = alpaca_headers()
    if not hdr:
        return [], None
    start = (_dt.now(tz=_ET) - timedelta(days=days)).strftime("%Y-%m-%d")
    for feed in ("sip", "iex"):
        pts, token = [], None
        try:
            while True:
                q = (f"/v2/stocks/bars?symbols={symbol}&timeframe={timeframe}"
                     f"&start={start}&limit=10000&adjustment=all&sort=asc&feed={feed}")
                page = alpaca_json(q + (f"&page_token={token}" if token else ""), hdr)
                for b in ((page.get("bars") or {}).get(symbol) or []):
                    pts.append({"t": _epoch_ms(b["t"]), "c": b["c"], "o": b["o"],
                                "h": b["h"], "l": b["l"], "v": int(b["v"])})
                token = page.get("next_page_token")
                if not token:
                    break
            if pts:
                return pts, feed
        except Exception:
            continue          # try the next feed, then fall through to Yahoo
    return [], None


def alpaca_hourly_rth(symbol, days):
    """Regular-hours hourly bars ANCHORED AT 09:30, built from 30Min bars.

    Alpaca's own 1Hour bars are aligned to the clock hour, so the 09:00 bar
    straddles the open: keep it and premarket leaks into the session, drop it and
    the first thirty minutes of trading — the most informative half hour on the
    chart — disappears. Neither is acceptable, so the session is rebuilt from
    30Min bars into 09:30/10:30/…/15:30 buckets, which is also the grid the
    client-side 4h aggregation and the trade grader both assume.
    """
    raw, feed = alpaca_bars(symbol, "30Min", days)
    if not raw:
        return [], None
    OPEN_M, CLOSE_M = 9 * 60 + 30, 16 * 60
    buckets = {}
    for b in raw:
        t = _dt.fromtimestamp(b["t"] / 1000, tz=_ET)
        m = t.hour * 60 + t.minute
        if m < OPEN_M or m >= CLOSE_M:
            continue
        key = (t.date(), (m - OPEN_M) // 60)
        agg = buckets.get(key)
        if agg is None:
            buckets[key] = dict(b)
        else:
            agg["h"] = max(agg["h"], b["h"])
            agg["l"] = min(agg["l"], b["l"])
            agg["c"] = b["c"]
            agg["v"] += b["v"]
    return [buckets[k] for k in sorted(buckets)], feed


def build_history(symbol, interval="1d"):
    """OHLCV powering volatility bands, projections, and the candlestick
    chart. `c` is the field every existing caller reads; o/h/l/v are
    additive so nothing that came before this needs to change.

    interval="60m" backs the chart's 4h view (aggregated client-side from
    these hourly bars — Yahoo has no native 4h granularity). It has no
    Nasdaq fallback: Nasdaq's chart endpoint is daily-only, and silently
    substituting daily bars under an hourly request would mislabel the
    data rather than degrade it honestly, so a failure here is a real error.
    """
    if interval == "60m":
        pts, feed = alpaca_hourly_rth(symbol, 400)
        if len(pts) > 20:
            return {"symbol": symbol, "points": pts, "source": f"Alpaca hourly OHLCV ({feed})"}
        j = fetch_json(f"https://query1.finance.yahoo.com/v8/finance/chart/{yf(symbol)}"
                       "?range=1y&interval=60m", ua=YAHOO_UA)
        res = ((j.get("chart") or {}).get("result") or [{}])[0]
        ts = res.get("timestamp") or []
        q = ((res.get("indicators") or {}).get("quote") or [{}])[0]
        o, h, l, c, v = (q.get(k) or [] for k in ("open", "high", "low", "close", "volume"))
        pts = []
        for i, t in enumerate(ts):
            cv = c[i] if i < len(c) else None
            if cv is None:
                continue
            pts.append({
                "t": t * 1000, "c": cv,
                "o": o[i] if i < len(o) and o[i] is not None else cv,
                "h": h[i] if i < len(h) and h[i] is not None else cv,
                "l": l[i] if i < len(l) and l[i] is not None else cv,
                "v": v[i] if i < len(v) and v[i] is not None else 0,
            })
        if len(pts) > 20:
            return {"symbol": symbol, "points": pts, "source": "Yahoo hourly OHLCV"}
        return {"error": f"no hourly history for {symbol}"}

    pts, feed = alpaca_bars(symbol, "1Day", 760)
    if len(pts) > 20:
        return {"symbol": symbol, "points": pts, "source": f"Alpaca daily OHLCV ({feed})"}

    try:
        j = fetch_json(f"https://query1.finance.yahoo.com/v8/finance/chart/{yf(symbol)}"
                       "?range=2y&interval=1d", ua=YAHOO_UA)
        res = ((j.get("chart") or {}).get("result") or [{}])[0]
        ts = res.get("timestamp") or []
        q = ((res.get("indicators") or {}).get("quote") or [{}])[0]
        o, h, l, c, v = (q.get(k) or [] for k in ("open", "high", "low", "close", "volume"))
        pts = []
        for i, t in enumerate(ts):
            cv = c[i] if i < len(c) else None
            if cv is None:
                continue
            pts.append({
                "t": t * 1000, "c": cv,
                "o": o[i] if i < len(o) and o[i] is not None else cv,
                "h": h[i] if i < len(h) and h[i] is not None else cv,
                "l": l[i] if i < len(l) and l[i] is not None else cv,
                "v": v[i] if i < len(v) and v[i] is not None else 0,
            })
        if len(pts) > 20:
            return {"symbol": symbol, "points": pts, "source": "Yahoo daily OHLCV"}
        raise RuntimeError("thin history")
    except Exception:
        d = nasdaq(f"https://api.nasdaq.com/api/quote/{symbol}/chart?assetclass=stocks"
                   "&fromdate=2024-07-01&todate=2026-12-31").get("data") or {}
        rows = d.get("chart") or []
        pts = []
        for r in rows:
            z = r.get("z") or {}
            v = z.get("value") or z.get("close")
            if v and r.get("x"):
                try:
                    cv = float(str(v).replace(",", ""))

                    def num(k, fallback):
                        raw = z.get(k)
                        return float(str(raw).replace(",", "")) if raw not in (None, "") else fallback
                    # "x" here is already epoch milliseconds — unlike Yahoo's
                    # seconds, do not rescale it.
                    pts.append({"t": int(r["x"]), "c": cv, "o": num("open", cv), "h": num("high", cv),
                               "l": num("low", cv), "v": int(num("volume", 0))})
                except ValueError:
                    pass
        return {"symbol": symbol, "points": pts, "source": "Nasdaq daily OHLCV"}

def build_filings(symbol):
    """Links straight to the company's most recent filings on EDGAR."""
    cik = cik_for(symbol)
    if not cik:
        return {"error": f"No SEC filer found for {symbol}"}
    j = fetch_json(f"https://data.sec.gov/submissions/CIK{cik}.json", ua=SEC_UA, timeout=30)
    r = (j.get("filings") or {}).get("recent") or {}
    bare = str(int(cik))
    out = []
    for i, form in enumerate(r.get("form", [])):
        if form not in ("10-Q", "10-K", "8-K"):
            continue
        acc = r["accessionNumber"][i].replace("-", "")
        doc = r["primaryDocument"][i]
        out.append({
            "form": form,
            "filed": r["filingDate"][i],
            "period": r.get("reportDate", [None] * (i + 1))[i],
            "url": f"https://www.sec.gov/Archives/edgar/data/{bare}/{acc}/{doc}",
        })
        if len(out) >= 6:
            break
    return {"symbol": symbol, "entityName": j.get("name", symbol), "filings": out,
            "profileUrl": f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type=10-&dateb=&owner=include&count=40"}

def nasdaq(url):
    return json.loads(fetch(url, timeout=15))

def build_street(symbol):
    """Analyst ratings, consensus targets and consensus history — Nasdaq public API."""
    # Both Nasdaq calls at once — sequential requests were the slowest path in the deck
    f_tp = _fanout.submit(nasdaq, f"https://api.nasdaq.com/api/analyst/{symbol}/targetprice")
    f_rt = _fanout.submit(nasdaq, f"https://api.nasdaq.com/api/analyst/{symbol}/ratings")
    tp = (f_tp.result().get("data") or {})
    co = tp.get("consensusOverview") or {}
    buy, hold, sell = co.get("buy") or 0, co.get("hold") or 0, co.get("sell") or 0
    try:
        rt = f_rt.result().get("data") or {}
    except Exception:
        rt = {}
    actions = []
    for ud in (rt.get("upgradesDowngrades") or [])[:8]:
        actions.append({
            "date": ud.get("date"), "firm": ud.get("company") or ud.get("firm"),
            "action": ud.get("action"), "from": ud.get("fromRating") or ud.get("from"),
            "to": ud.get("toRating") or ud.get("to"),
            "target": ud.get("toPT") or ud.get("priceTarget")
        })
    history = []
    for pt in (tp.get("historicalConsensus") or []):
        z = pt.get("z") or {}
        if z.get("date") and pt.get("y"):
            history.append({"date": z["date"], "price": pt.get("y"),
                            "buy": z.get("buy", 0), "hold": z.get("hold", 0),
                            "sell": z.get("sell", 0), "consensus": z.get("consensus")})
    return {
        "symbol": symbol,
        "strongBuy": buy, "buy": 0, "hold": hold, "sell": sell,
        "analysts": buy + hold + sell,
        "targetMean": co.get("priceTarget"), "targetMedian": co.get("priceTarget"),
        "targetLow": co.get("lowPriceTarget"), "targetHigh": co.get("highPriceTarget"),
        "recKey": rt.get("meanRatingType"),
        "ratingsSummary": rt.get("ratingsSummary"),
        "brokerCount": len(rt.get("brokerNames") or []),
        "brokers": (rt.get("brokerNames") or [])[:24],
        "actions": actions,
        "history": history[-24:],
        "source": "Nasdaq analyst consensus",
    }

def alpaca_quote(symbol):
    """Alpaca snapshot -> the quote payload shape. None when unavailable.

    Feed ladder, in descending order of truth: `sip` (real-time consolidated
    tape, paid plans), `delayed_sip` (the same full tape, 15 minutes late),
    `iex` (real-time but ~3% of the tape, so the print can sit cents off). A
    late full-tape price beats a live sliver, so delayed_sip outranks iex, and
    `source` always names which one answered plus its delay.

    `prevDailyBar.c` is the prior REGULAR session close, which is the baseline
    the headline change has to use — the bug this replaces compared an
    after-hours print against today's close and showed MSFT green on a day it
    fell 8%.
    """
    hdr = alpaca_headers()
    if not hdr:
        return None
    for feed in ("sip", "delayed_sip", "iex"):
        try:
            snap = alpaca_json(f"/v2/stocks/{symbol}/snapshot?feed={feed}", hdr)
        except Exception:
            continue
        t = snap.get("latestTrade") or {}
        day = snap.get("dailyBar") or {}
        prev = (snap.get("prevDailyBar") or {}).get("c")
        price = t.get("p")
        if price is None or not prev:
            continue
        state = market_state()
        in_session = state == "open"
        reg = day.get("c")
        stamp = _dt.fromtimestamp(_epoch_ms(t["t"]) / 1000, tz=_ET) if t.get("t") else None
        label = {"sip": "Alpaca real-time (SIP)",
                 "delayed_sip": "Alpaca 15-min delayed (SIP)",
                 "iex": "Alpaca real-time (IEX only, ~3% of tape)"}[feed]
        return {
            "symbol": symbol, "price": price,
            "change": round(price - prev, 3),
            "prevClose": prev,
            "changePct": round((price / prev - 1) * 100, 2),
            # The extended-session-only move, for the session chip.
            "sessionChange": round(price - reg, 3) if (reg and not in_session) else None,
            "sessionChangePct": round((price / reg - 1) * 100, 2) if (reg and not in_session) else None,
            "asOf": stamp.strftime("%b %-d, %Y %-I:%M %p ET") if stamp else None,
            "session": "live" if in_session else ("extended" if state == "ext" else "closed"),
            "regular": {"price": reg, "asOf": None},
            "name": None,
            "source": label,
        }
    return None


def build_quote(symbol):
    """Real-time quote. Alpaca first — it is this repo's price source, and its
    prevDailyBar gives the honest prior-regular-close baseline for free. Nasdaq
    and then Yahoo remain as fallbacks so a missing key or a provider hiccup
    degrades the deck instead of blanking it."""
    q = alpaca_quote(symbol)
    if q:
        return q

    def money(s):
        if not s:
            return None
        try:
            return float(re.sub(r"[^\d.\-]", "", str(s)))
        except ValueError:
            return None
    def yday_close():
        # The prior REGULAR session's close — the only honest baseline for "the
        # day's move". Nasdaq's live block compares an after-hours print to
        # TODAY's close, which showed MSFT +1.06% green on a day it fell 8%.
        # Changes once a day; cached accordingly.
        j = fetch_json(f"https://query1.finance.yahoo.com/v8/finance/chart/{yf(symbol)}"
                       "?range=1d&interval=1d", ua=YAHOO_UA)
        m = (((j.get("chart") or {}).get("result") or [{}])[0].get("meta") or {})
        return m.get("chartPreviousClose") or m.get("previousClose")

    try:
        d = nasdaq(f"https://api.nasdaq.com/api/quote/{symbol}/info?assetclass=stocks").get("data") or {}
        pri = d.get("primaryData") or {}
        sec = d.get("secondaryData") or {}
        # During extended hours Nasdaq puts the regular session in one block and
        # the live after/pre-market print in the other; prefer whichever is live.
        live, base = (pri, sec) if pri.get("isRealTime") else (sec or pri, pri)
        price = money(live.get("lastSalePrice")) or money(pri.get("lastSalePrice"))
        chg = money(live.get("netChange"))
        if price is None:
            raise RuntimeError("no nasdaq price")
        try:
            prev = cached(f"yc:{symbol}", 600, yday_close)
        except Exception:
            prev = None
        if not prev:
            prev = (price - chg) if chg is not None else None
        in_session = live is pri and pri.get("isRealTime")
        q = {
            "symbol": symbol, "price": price,
            # The headline change is ALWAYS against yesterday's close — the
            # number a viewer means when they say "MSFT is down 8 today".
            "change": round(price - prev, 3) if prev else chg,
            "prevClose": prev,
            "changePct": round((price / prev - 1) * 100, 2) if prev else money(live.get("percentageChange")),
            # The extended-session-only move, for the session chip.
            "sessionChange": chg if not in_session else None,
            "sessionChangePct": money(live.get("percentageChange")) if not in_session else None,
            "asOf": live.get("lastTradeTimestamp") or pri.get("lastTradeTimestamp"),
            "session": "live" if in_session else "extended",
            "regular": {"price": money(base.get("lastSalePrice")), "asOf": base.get("lastTradeTimestamp")},
            "name": d.get("companyName"),
            "source": "Nasdaq real-time",
        }
        # Nasdaq's lastTradeTimestamp can lag its own lastSalePrice by a session:
        # observed 2026-08-15 on NBIS and SPCX, where the price was Friday's close
        # and the label still said Thursday. That label ends up in the deck's
        # footer stamp, so when the last daily bar matches the price but not the
        # label, the bar's date is the truthful one.
        try:
            import datetime as _dt
            bar = get("history", symbol)["points"][-1]
            lab = _dt.datetime.fromtimestamp(bar["t"] / 1000, _dt.timezone.utc).strftime("%b %-d, %Y")
            if q["asOf"] and abs((bar.get("c") or 0) - price) < 0.01 and lab not in str(q["asOf"]):
                q["asOf"] = lab
        except Exception:
            pass
        return q
    except Exception:
        j = fetch_json(f"https://query1.finance.yahoo.com/v8/finance/chart/{yf(symbol)}?range=1d&interval=1d", ua=YAHOO_UA)
        m = (((j.get("chart") or {}).get("result") or [{}])[0].get("meta") or {})
        price = m.get("regularMarketPrice")
        prev = m.get("chartPreviousClose") or m.get("previousClose")
        if price is None:
            raise
        return {
            "symbol": symbol, "price": price,
            "change": (price - prev) if prev else None,
            "prevClose": prev,
            "changePct": ((price - prev) / prev * 100) if prev else None,
            "high52": m.get("fiftyTwoWeekHigh"), "low52": m.get("fiftyTwoWeekLow"),
            "asOf": None, "session": "regular",
            "source": "Yahoo Finance",
        }

def build_estimates(symbol):
    """Consensus EPS by fiscal period, with how many analysts moved their number
    in the last four weeks. Rising estimates are what precedes a re-rating."""
    d = nasdaq(f"https://api.nasdaq.com/api/analyst/{symbol}/earnings-forecast").get("data") or {}

    def rows(block):
        out = []
        for r in ((d.get(block) or {}).get("rows") or []):
            try:
                out.append({
                    "period": r.get("fiscalEnd"),
                    "eps": float(r["consensusEPSForecast"]),
                    "high": float(r["highEPSForecast"]) if r.get("highEPSForecast") else None,
                    "low": float(r["lowEPSForecast"]) if r.get("lowEPSForecast") else None,
                    "analysts": int(r.get("noOfEstimates") or 0),
                    "up": int(r.get("up") or 0),
                    "down": int(r.get("down") or 0),
                })
            except (TypeError, ValueError):
                continue
        return out

    yearly, quarterly = rows("yearlyForecast"), rows("quarterlyForecast")
    pool = yearly or quarterly
    up = sum(r["up"] for r in pool)
    down = sum(r["down"] for r in pool)
    return {
        "symbol": symbol, "yearly": yearly, "quarterly": quarterly,
        "revisionsUp": up, "revisionsDown": down,
        "direction": "up" if up > down else "down" if down > up else "flat",
        "source": "Nasdaq analyst estimates",
    }

def market_row(symbol):
    try:
        return cached("market", 300, build_market).get(symbol)
    except Exception:
        return None

def build_profile(symbol):
    """Company identity + key statistics — Nasdaq quote summary."""
    sd = (nasdaq(f"https://api.nasdaq.com/api/quote/{symbol}/summary?assetclass=stocks")
          .get("data") or {}).get("summaryData") or {}

    def val(key):
        node = sd.get(key) or {}
        v = node.get("value")
        return None if v in (None, "", "N/A") else v

    def num(key):
        v = val(key)
        if not v:
            return None
        try:
            return float(re.sub(r"[^\d.\-]", "", v))
        except ValueError:
            return None

    hi = lo = None
    if (rng := val("FiftTwoWeekHighLow")):
        nums = re.findall(r"[\d.]+", rng.replace(",", ""))
        if len(nums) == 2:
            hi, lo = float(nums[0]), float(nums[1])
    prof = {
        "symbol": symbol,
        "exchange": val("Exchange"), "sector": val("Sector"), "industry": val("Industry"),
        "marketCapRaw": num("MarketCap"),
        "divYield": val("Yield"),
        "oneYearTarget": num("OneYrTarget"),
        "high52": hi, "low52": lo,
        "prevClose": num("PreviousClose"),
        "avgVolume": num("AverageVolume"),
        "annualDividend": val("AnnualizedDividend"),
        "source": "Nasdaq quote summary",
    }
    # Whole-market backstop: the per-symbol summary endpoint has gaps for
    # plenty of listings, and a blank sector or missing cap reads as a broken
    # dashboard. The screener table covers essentially everything trading.
    m = market_row(symbol)
    if m:
        prof["sector"] = prof.get("sector") or m["sector"]
        prof["industry"] = prof.get("industry") or m["industry"]
        prof["name"] = prof.get("name") or m["name"]
        if not prof.get("marketCapRaw") and m["cap"]:
            prof["marketCapRaw"] = m["cap"]
    # PRICE comes from Alpaca, never from the screener table. The screener row is
    # here for sector/industry/name/cap — fields Alpaca does not carry — and its
    # `last` used to leak in as a prevClose backstop, which is exactly the
    # two-feeds-disagreeing failure the rest of this module is built to avoid.
    if not prof.get("prevClose"):
        try:
            prof["prevClose"] = (get("quote", symbol) or {}).get("prevClose")
        except Exception:
            pass
    return prof

def build_market():
    """The entire US market in one call — Nasdaq's screener table.

    ~7,100 listings with price, day change, volume, market cap, sector and
    industry. Serves two jobs: a market-wide data backstop so no ticker ever
    renders blanks when the per-symbol summary endpoint has gaps, and a
    foundation for anything market-wide (movers, sector context) later.
    """
    d = nasdaq("https://api.nasdaq.com/api/screener/stocks?tableonly=true&limit=25000&download=true")
    rows = (d.get("data") or {}).get("rows") or []
    out = {}
    money = lambda v: (lambda m: float(m) if m else None)(re.sub(r"[^\d.\-]", "", str(v or "")) or None)
    for r in rows:
        sym = (r.get("symbol") or "").strip()
        if not sym:
            continue
        out[sym] = {
            "name": (r.get("name") or "").replace(" Common Stock", "").strip(),
            "last": money(r.get("lastsale")),
            "chg": money(r.get("netchange")),
            "pct": money(r.get("pctchange")),
            "volume": money(r.get("volume")),
            "cap": money(r.get("marketCap")),
            "sector": r.get("sector") or None,
            "industry": r.get("industry") or None,
        }
    if len(out) < 4000:
        raise RuntimeError(f"market table implausibly small ({len(out)})")
    return out

# --------------------------------------------------------------------------
# The routes the deck consumes. Same names, same shapes, same freshness rules
# as the HTTP API they replace — so build_deck and audit_deck did not have to
# learn anything new.
# --------------------------------------------------------------------------

ROUTES = {
    "quote":        lambda s: cached(f"quote:{s}", ttl_for(8, 20, 120),
                                     lambda: build_quote(s), max_stale=0),
    "history":      lambda s: cached(f"hist:{s}:1d", ttl_for(60, 300, 1800),
                                     lambda: build_history(s), max_stale=0),
    "fundamentals": lambda s: cached(f"fund:{s}", 6 * 3600, lambda: build_fundamentals(s),
                                     disk_ttl=7 * 86400),
    "profile":      lambda s: cached(f"prof:{s}", 6 * 3600, lambda: build_profile(s),
                                     disk_ttl=7 * 86400),
    "street":       lambda s: cached(f"street:{s}", 3 * 3600, lambda: build_street(s),
                                     disk_ttl=3 * 86400),
    "estimates":    lambda s: cached(f"est:{s}", 6 * 3600, lambda: build_estimates(s),
                                     disk_ttl=7 * 86400),
    "filings":      lambda s: cached(f"filings:{s}", 12 * 3600, lambda: build_filings(s),
                                     disk_ttl=14 * 86400),
}


def get(route, symbol):
    """Fetch one route for one symbol. Raises on an unknown route."""
    if route not in ROUTES:
        raise KeyError(f"no such route {route!r} — have {sorted(ROUTES)}")
    return ROUTES[route](symbol.upper())


if __name__ == "__main__":
    import sys
    r = sys.argv[1] if len(sys.argv) > 1 else "quote"
    s = sys.argv[2] if len(sys.argv) > 2 else "PLTR"
    print(json.dumps(get(r, s), indent=1)[:3000])
