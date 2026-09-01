#!/usr/bin/env python3
"""
build_deck.py — generate an episode slide deck from the Terminal's live API
plus hand-verified facts read out of the company's SEC filings.

    python3 scripts/build_deck.py DVA

Writes ~/Desktop/<TICKER> <YYYY-MM-DD>/ containing the deck, the spoken
script, a source index, and the frozen snapshot every number is rendered from.

Design rules, in order of importance:

  1. No figure is ever typed into a slide. Slides read from `snap`, which is
     built here from (a) live API payloads and (b) episodes/<SYM>.json, whose
     every entry carries the filing it was read from. audit_deck.py re-derives
     the whole thing and fails on any mismatch.
  2. Anything a company defines itself — free cash flow, adjusted EPS, its
     leverage ratio — is QUOTED from the filing, never recomputed. DaVita's
     reported FCF is $1,308M; CFO minus capex off the XBRL gives $1,611M. The
     company's definition wins.
  3. A metric with a missing input is omitted, not estimated. DVA's Q4'25 net
     income is absent from the XBRL pull, so trailing P/E is not computable and
     does not appear anywhere in the deck.
  4. Derived estimates (the per-payor rate split) are labelled as derived, on
     screen, with their inputs shown.
"""

import json
import re
import math
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from importlib import import_module

import deckpath
import marketdata

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.dirname(HERE)
# Market data comes from scripts/marketdata.py — the deck pipeline owns its own
# data layer and needs no server running. Setting TERMINAL_API switches back to
# HTTP against something serving the same routes, which is only useful for
# comparing the two.
API = os.environ.get("TERMINAL_API", "").rstrip("/") or None

# Per-route freshness ceilings, mirroring server.py's ttl_for() worst case
# (market-closed TTL). max_stale=0 means the server blocks and refetches past
# TTL, so anything above these ceilings is a server bug, not a slow day.
AGE_CEILING = {"quote": 120, "history": 1800, "fundamentals": None,
               "street": None, "estimates": None, "profile": None, "filings": None}


def deck_module(sym):
    """The per-ticker narrative module: scripts/decks/<SYM>.py."""
    try:
        return import_module(f"decks.{sym}")
    except ModuleNotFoundError:
        die(f"no scripts/decks/{sym}.py. The generator is generic; the story is not — "
            f"each ticker needs its own slide module alongside episodes/{sym}.json.")


def die(msg):
    print("BUILD FAILED: " + msg, file=sys.stderr)
    sys.exit(1)


def get(route, sym):
    where = f"{API}/{route}/{sym}" if API else f"marketdata.{route}({sym})"
    try:
        if API:
            with urllib.request.urlopen(f"{API}/{route}/{sym}", timeout=90) as r:
                payload = json.loads(r.read().decode())
        else:
            payload = marketdata.get(route, sym)
    except Exception as e:                                    # noqa: BLE001
        die(f"{where} failed: {e}\n"
            f"  Every price, share count and estimate in the deck comes from here.\n"
            f"  The upstreams are SEC XBRL, the Yahoo chart API and Nasdaq — check "
            f"connectivity.")
    ceiling = AGE_CEILING.get(route)
    age = payload.get("_ageS")
    if ceiling is not None:
        if age is None:
            die(f"{route}/{sym} carries no _ageS — refusing to bake undated data into a deck")
        if age > ceiling:
            die(f"{route}/{sym} is {age:.0f}s old against a {ceiling}s ceiling — refusing to bake stale data")
    return payload


def fact(node, *path):
    """Read a value out of episodes/<SYM>.json, insisting it names its source."""
    cur = node
    for p in path:
        if p not in cur:
            die(f"episode file is missing {'.'.join(path)}")
        cur = cur[p]
    if isinstance(cur, dict) and "v" in cur:
        if "src" not in cur:
            die(f"episode fact {'.'.join(path)} has no `src` — every fact must name its filing")
        return cur["v"]
    return cur


def resolve_prose(node, snap):
    """
    Substitute `{path|fmt}` tokens in episode prose from the live snapshot.

    Verdict lines like "49x this year's guided revenue" were typed once and went
    stale the moment the price moved — the same slide pack was quoting 49x while
    the chart three slides earlier computed 53x. Anything price-dependent is
    written as a token and resolved at build time.

        {val.evRevOnGuide|x0}   -> "53x"      {price|$}       -> "$172.01"
        {val.fcfYieldOnGuide|%} -> "1.0%"     {marketCap|usd} -> "$442B"
    """
    from decks import fmt as F

    def one(m):
        path, _, kind = m.group(1).partition("|")
        cur = snap
        for part in path.split("."):
            if isinstance(cur, list) and part.isdigit() and int(part) < len(cur):
                cur = cur[int(part)]
                continue
            if not isinstance(cur, dict) or part not in cur:
                die(f"episode prose references {{{m.group(1)}}} but the snapshot has no `{path}`")
            cur = cur[part]
        if kind in ("x0", "x1"):
            return f"{cur:.{int(kind[1])}f}\u00d7"      # the glyph, safe in text or HTML
        if kind == "%":
            return F.pct(cur, 1, signed=False)
        if kind == "%0":
            return F.pct(cur, 0, signed=False)
        if kind == "%abs":                       # magnitude only — "fell 48%", not "fell −48%"
            return f"{abs(cur):.0f}%"
        if kind == "%+":
            return F.pct(cur, 0)
        if kind == "usd":
            return F.usd(cur)
        if kind == "usdB":                       # value already carried in billions
            return F.usd(cur * 1000)
        if kind == "$":
            return F.dollars(cur)
        if kind == "":                           # bare {path} — a plain number
            if isinstance(cur, float):
                return f"{cur:,.1f}".rstrip("0").rstrip(".")
            return f"{cur:,}" if isinstance(cur, int) else str(cur)
        die(f"episode prose uses an unknown format `{kind}` in {{{m.group(1)}}}")

    if isinstance(node, str):
        return re.sub(r"\{([^{}]+)\}", one, node)
    if isinstance(node, list):
        return [resolve_prose(x, snap) for x in node]
    if isinstance(node, dict):
        return {k: resolve_prose(v, snap) for k, v in node.items()}
    return node


# --------------------------------------------------------------------------
# Snapshot
# --------------------------------------------------------------------------

def build_snapshot(sym, ep):
    q = get("quote", sym)
    prof = get("profile", sym)
    fund = get("fundamentals", sym)
    street = get("street", sym)
    est = get("estimates", sym)
    hist = get("history", sym)

    F = ep["filings"]
    price = q["price"]

    # A company that listed weeks ago has neither eight quarters nor a year of
    # tape. Rather than refuse — or worse, pad the history — the engine marks the
    # snapshot `newlyListed` and omits every metric whose inputs do not exist.
    # Rule 4 applies: a metric with a missing input is omitted, not estimated.
    qs = fund["quarters"]
    newly_listed = len(qs) < 8
    if newly_listed:
        print(f"  ! only {len(qs)} quarters of fundamentals — building in newly-listed mode; "
              f"trailing-twelve-month metrics will be omitted, not estimated")

    def rev(i):
        v = qs[i]["revenue"]
        if v is None:
            die(f"revenue missing for {qs[i]['label']}")
        return v

    if newly_listed:
        ttm_rev = ttm_rev_prior = None
    else:
        ttm_rev = sum(rev(i) for i in range(4, 8)) * 1000      # $B -> $M
        ttm_rev_prior = sum(rev(i) for i in range(0, 4)) * 1000

    shares_now = fact(F, "balanceSheet", "sharesOutstanding") / 1000.0   # thousands -> millions
    shares_then = qs[0]["shares"]                                        # already millions
    if shares_then is None and not newly_listed:
        die("earliest quarter has no share count — the buyback slide has no baseline")

    mcap = price * shares_now                                   # $M

    # Forward multiples off consensus. Trailing is deliberately absent:
    # Q4'25 net income is null in the XBRL pull, so TTM EPS is not computable.
    yearly = {e["period"]: e for e in est.get("yearly", [])}
    fwd = []
    for period in sorted(yearly, key=lambda p: p.split()[-1]):
        e = yearly[period]
        eps = e.get("eps")
        if eps is None:
            continue
        # A loss has no P/E. Carry the estimate so the slide can say "still a loss",
        # but never divide a price by a negative number and print it as a multiple.
        fwd.append({"period": period, "eps": eps,
                    "pe": (price / eps) if eps > 0 else None,
                    "low": e.get("low"), "high": e.get("high"),
                    "analysts": e.get("analysts")})
    if not fwd and not newly_listed:
        die("no forward EPS estimates — the valuation slide has nothing to stand on")

    ttm_net_income_computable = (not newly_listed
                                 and all(qs[i]["netInc"] is not None for i in range(4, 8)))

    # Price tape: last ~12 months, downsampled for a clean line. A recent listing
    # gets its whole life instead, and the slide has to say so.
    pts = hist["points"][-252:]
    if len(pts) < 200 and not newly_listed:
        die(f"only {len(pts)} daily bars — need a year of tape for the move slide")
    if len(pts) < 20:
        die(f"only {len(pts)} daily bars — too little tape to draw anything honest")
    step = max(1, len(pts) // 150)
    tape = [{"t": p["t"], "v": round(p["c"], 2)} for p in pts[::step]]
    if tape[-1]["t"] != pts[-1]["t"]:
        tape.append({"t": pts[-1]["t"], "v": round(pts[-1]["c"], 2)})

    lo_bar = min(pts, key=lambda p: p["l"])
    hi_bar = max(pts, key=lambda p: p["h"])

    def dstr(ms, fmt="%b %-d"):
        return datetime.fromtimestamp(ms / 1000, timezone.utc).strftime(fmt)

    def nearest(ms):
        return min(range(len(tape)), key=lambda i: abs(tape[i]["t"] - ms))

    # The earnings reaction day: the worst single-session close in the tape.
    worst_i, worst_pct = 0, 0.0
    for i in range(1, len(pts)):
        ch = (pts[i]["c"] / pts[i - 1]["c"] - 1) * 100
        if ch < worst_pct:
            worst_pct, worst_i = ch, i

    # The deepest peak-to-trough fall, walked IN ORDER. High-minus-low is not a
    # drawdown when the low came first — PLTR's 52-week high precedes its low, so
    # the naive pair says one thing and the sequence says another.
    _peak, _peak_t, peak_to_trough = pts[0]["c"], pts[0]["t"], {"pct": 0.0}
    for p in pts:
        if p["c"] > _peak:
            _peak, _peak_t = p["c"], p["t"]
        dd = (p["c"] / _peak - 1) * 100
        if dd < peak_to_trough["pct"]:
            peak_to_trough = {"pct": dd, "peak": _peak, "peakWhen": dstr(_peak_t),
                              "trough": p["c"], "troughWhen": dstr(p["t"])}

    # Earnings history: what the guidance midpoint did, and what the stock did
    # the next session. DaVita reports after the close, so the market's verdict
    # is the FIRST session strictly after the release date. Moves are derived
    # here from live daily bars — nothing about them is hand-entered.
    all_bars = hist["points"]
    bar_days = [datetime.fromtimestamp(p["t"] / 1000, timezone.utc).strftime("%Y-%m-%d")
                for p in all_bars]
    releases, prev = [], None
    for rel in F["earningsHistory"]["releases"]:
        nxt = [i for i, d in enumerate(bar_days) if d > rel["date"]]
        if not nxt or nxt[0] == 0:
            # A deck built the same evening a release lands has no reaction yet. That
            # is a normal thing to do on this channel, so record the release with the
            # move left as None and let the slide say the verdict is pending. It must
            # never be filled in with the after-hours print dressed up as a session.
            if rel["date"] >= bar_days[-1]:
                releases.append({
                    "date": rel["date"], "q": rel["q"], "fy": rel["fy"],
                    "guideLow": rel.get("guideLow"), "guideHigh": rel.get("guideHigh"),
                    "mid": ((rel["guideLow"] + rel["guideHigh"]) / 2
                            if rel.get("guideLow") is not None else None),
                    "action": "reaction pending", "kind": "pending",
                    "reactDate": None, "move": None, "volX": None,
                })
                continue
            die(f"no trading session after the {rel['date']} release in the history window")
        i = nxt[0]
        # Not every company guides. SpaceX gives none at all, so there is no
        # midpoint to track — the reaction is still real and still measured.
        if rel.get("guideLow") is None or rel.get("guideHigh") is None:
            vol = all_bars[i]["v"]
            base = [b["v"] for b in all_bars[max(0, i - 31):i - 1]]
            releases.append({
                "date": rel["date"], "q": rel["q"], "fy": rel["fy"],
                "guideLow": None, "guideHigh": None, "mid": None,
                "action": "no guidance given", "kind": "none",
                "reactDate": bar_days[i],
                "move": (all_bars[i]["c"] / all_bars[i - 1]["c"] - 1) * 100,
                "volX": vol / (sum(base) / len(base)) if base else None,
            })
            continue
        mid = (rel["guideLow"] + rel["guideHigh"]) / 2
        if prev is None or prev["fy"] != rel["fy"]:
            action, kind = f"first FY{rel['fy']} guide", "new"
        elif mid > prev["mid"] + 1e-9:
            action, kind = "RAISED", "up"
        elif mid < prev["mid"] - 1e-9:
            action, kind = "CUT", "down"
        elif (rel["guideLow"], rel["guideHigh"]) != (prev["low"], prev["high"]):
            action, kind = "narrowed, midpoint flat", "flat"
        else:
            action, kind = "UNCHANGED", "flat"
        vol = all_bars[i]["v"]
        base = [b["v"] for b in all_bars[max(0, i - 31):i - 1]]
        releases.append({
            "date": rel["date"], "q": rel["q"], "fy": rel["fy"],
            "guideLow": rel["guideLow"], "guideHigh": rel["guideHigh"], "mid": mid,
            "action": action, "kind": kind,
            "reactDate": bar_days[i],
            "move": (all_bars[i]["c"] / all_bars[i - 1]["c"] - 1) * 100,
            "volX": vol / (sum(base) / len(base)) if base else None,
        })
        prev = {"fy": rel["fy"], "mid": mid, "low": rel["guideLow"], "high": rel["guideHigh"]}

    # Only WITHIN-YEAR revisions are comparable. A January guide for a new
    # fiscal year is judged against a consensus we do not hold, so it is shown
    # but explicitly excluded from the claim.
    revisions = [r for r in releases if r["kind"] not in ("new", "none", "pending")]
    raised = [r for r in revisions if r["kind"] == "up"]
    held = [r for r in revisions if r["kind"] != "up"]
    earnings_stats = {
        "revisions": len(revisions), "raised": len(raised), "held": len(held),
        "raisedAllPositive": all(r["move"] > 0 for r in raised),
        "heldAllNegative": all(r["move"] < 0 for r in held),
        "bestRaise": max((r["move"] for r in raised), default=None),
        "worstHeld": min((r["move"] for r in held), default=None),
    }

    # Indexed price vs trailing earnings. TTM EPS steps on the day each quarter
    # was REPORTED, so the line shows what the market knew when it knew it. Built
    # from the reported quarterly EPS in the releases, NOT from the Terminal's
    # epsYears/ttmSeries — those overstate DVA's annual EPS by ~37% (they appear
    # to divide total net income rather than income attributable to DaVita).
    qrows = F["quarterly"]["rows"]
    reldate = {r["q"]: r["date"] for r in F["earningsHistory"]["releases"]}
    ttm = []
    for k in range(3, len(qrows)):
        window = qrows[k - 3:k + 1]
        if any(w["eps"] is None for w in window):
            continue
        d = reldate.get(qrows[k]["q"])
        if not d:
            die(f"no release date for {qrows[k]['q']} — cannot place the earnings step")
        ttm.append({"q": qrows[k]["q"], "date": d, "v": round(sum(w["eps"] for w in window), 2)})

    # Price indexed against trailing earnings needs four quarters of reported EPS
    # and a price history that covers them. A company that listed this quarter has
    # neither, so the chart is omitted rather than faked.
    indexed = None
    _eps_present = sum(1 for r in qrows if r.get("eps") is not None)
    if len(ttm) < 4 or newly_listed:
        if newly_listed:
            pass
        elif _eps_present <= 1:
            # A company that has never earned a profit has no earnings series to
            # index against. Omit it — rule 4, a metric with a missing input is
            # omitted, not estimated — and say so rather than dying.
            print(f"  ! only {_eps_present} reported EPS figure(s) — this company has no earnings "
                  f"series, so the price-vs-earnings chart is omitted, not estimated")
        else:
            die(f"only {len(ttm)} trailing-EPS points from {_eps_present} reported quarters — "
                f"not enough for the indexed chart, and this company does report EPS")
    else:
        base_ms = int(datetime.strptime(ttm[0]["date"], "%Y-%m-%d")
                      .replace(tzinfo=timezone.utc).timestamp() * 1000)
        px = [b for b in all_bars if b["t"] >= base_ms]
        if len(px) < 60:
            die("price history does not cover the indexed window")
        p0, e0 = px[0]["c"], ttm[0]["v"]
        stepv = max(1, len(px) // 150)
        indexed = {
            "price": [{"t": b["t"], "v": round(b["c"] / p0 * 100, 2)} for b in px[::stepv]],
            "earn": [{"t": int(datetime.strptime(x["date"], "%Y-%m-%d")
                              .replace(tzinfo=timezone.utc).timestamp() * 1000),
                      # `_`-prefixed: carried for the deck module and provenance,
                      # never drawn by the chart itself.
                      "v": round(x["v"] / e0 * 100, 2), "_q": x["q"], "_eps": x["v"]} for x in ttm],
            "baseDate": ttm[0]["date"], "basePrice": p0, "baseEps": e0,
            "endPrice": px[-1]["c"], "endEps": ttm[-1]["v"],
            "priceGain": (px[-1]["c"] / p0 - 1) * 100,
            "earnGain": (ttm[-1]["v"] / e0 - 1) * 100,
        }
        if indexed["price"][-1]["t"] != px[-1]["t"]:
            indexed["price"].append({"t": px[-1]["t"], "v": round(px[-1]["c"] / p0 * 100, 2)})

    target = street.get("targetMean")
    snap = {
        "symbol": sym,
        "company": ep["company"],
        "exchange": prof.get("exchange"), "sector": prof.get("sector"),
        "price": price, "changePct": q.get("changePct"),
        "asOf": q.get("asOf"), "quoteSource": q.get("source"),
        "marketCap": mcap,
        "sharesNow": shares_now, "sharesThen": shares_then,
        "sharesLabelThen": qs[0]["label"], "sharesLabelNow": qs[-1]["label"],
        # Two different things, never to be mixed in one sentence:
        #   sharesNowWA — diluted weighted-average, the basis the share chart plots
        #   sharesNow   — the basis the episode file nominates for market cap and EPS
        "sharesNowWA": qs[-1]["shares"],
        "shareReductionWA": ((qs[-1]["shares"] / shares_then - 1) * 100
                             if qs[-1]["shares"] else None),
        "shareReduction": (shares_now / shares_then - 1) * 100,
        "quartersMissingShares": [x["label"] for x in qs if x["shares"] is None],
        "ttmRev": ttm_rev, "ttmRevPrior": ttm_rev_prior,
        "ttmRevGrowth": ((ttm_rev / ttm_rev_prior - 1) * 100) if ttm_rev else None,
        "quarters": [{"label": x["label"], "revenue": x["revenue"], "netInc": x["netInc"],
                      "opInc": x["opInc"], "shares": x["shares"]} for x in qs],
        "fwd": fwd, "ttmNetIncomeComputable": ttm_net_income_computable,
        "tape": tape,
        "low": {"v": lo_bar["l"], "when": dstr(lo_bar["t"]), "i": nearest(lo_bar["t"])},
        "high": {"v": hi_bar["h"], "when": dstr(hi_bar["t"]), "i": nearest(hi_bar["t"])},
        "worst": {"pct": worst_pct, "when": dstr(pts[worst_i]["t"]),
                  "i": nearest(pts[worst_i]["t"]), "close": pts[worst_i]["c"],
                  "volume": pts[worst_i]["v"],
                  "volX": pts[worst_i]["v"] / (sum(p["v"] for p in pts[max(0, worst_i - 31):worst_i - 1])
                                               / 30)},
        "runUp": (hi_bar["h"] / lo_bar["l"] - 1) * 100,
        "drawdown": (price / hi_bar["h"] - 1) * 100,
        "peakToTrough": peak_to_trough,
        "releases": releases, "earningsStats": earnings_stats,
        "indexed": indexed,
        # Honest flags for a company that has not been public a full year.
        "newlyListed": newly_listed,
        "tapeDays": len(pts),
        "quartersAvailable": len(qs),
        "street": {"strongBuy": street.get("strongBuy"), "buy": street.get("buy"),
                   "hold": street.get("hold"), "sell": street.get("sell"),
                   "analysts": street.get("analysts"), "rec": street.get("recKey"),
                   "target": target, "targetLow": street.get("targetLow"),
                   "targetHigh": street.get("targetHigh"),
                   "upside": (target / price - 1) * 100 if target else None,
                   "nasdaqTarget": prof.get("oneYearTarget")},
        "provenance": {r: {"fetchedAt": p.get("_fetchedAt"), "ageS": p.get("_ageS"),
                           "source": p.get("source")}
                       for r, p in [("quote", q), ("profile", prof), ("fundamentals", fund),
                                    ("street", street), ("estimates", est), ("history", hist)]},
        "builtAt": datetime.now().astimezone().isoformat(timespec="seconds"),
    }
    # Company-specific derived metrics live in the per-ticker deck module.
    snap.update(deck_module(sym).derive(snap, ep, fund, qrows, die, fact))
    return snap


# --------------------------------------------------------------------------
# Slides
# --------------------------------------------------------------------------

# --------------------------------------------------------------------------
# Output
# --------------------------------------------------------------------------

STRIP = [("&mdash;", "—"), ("&minus;", "−"), ("&times;", "×"), ("&ndash;", "–"),
         ("&rarr;", "→"), ("&lsquo;", "‘"), ("&rsquo;", "’"), ("&ldquo;", "“"),
         ("&rdquo;", "”"), ("&amp;", "&"), ("&nbsp;", " ")]


def strip_html(v):
    s = re.sub(r"<[^>]+>", "", str(v))
    for a, b in STRIP:
        s = s.replace(a, b)
    return s


def write_script(path, snap, slides):
    total = sum(s.get("target", 0) for s in slides)
    opt = [s for s in slides if s.get("optional")]
    core = total - sum(s.get("target", 0) for s in opt)
    fmt = lambda x: f"{x//60}:{x%60:02d}"                                 # noqa: E731
    L = [f"# {snap['company']} ({snap['symbol']}) — spoken script", "",
         f"Built {snap['builtAt']} · price {snap['price']:.2f} as of {snap['asOf']}", "",
         f"- **Full cut:** {len(slides)} slides, {fmt(total)}",
         f"- **Core cut:** {fmt(core)} — drop the {len(opt)} slides marked `CUT FOR TIME`. "
         "They are support, not argument; the case still stands without them.", "",
         "Keys: → next · ← back · T theme · N notes · H presenter HUD + timer · G grid · "
         "F fullscreen",
         "",
         "**C = camera layout** — reserves a column on the left with a frame to sit your "
         "camera in, and remembers the choice. `[` and `]` resize the column; `⇧C` shows the "
         "exact pixel box to type into OBS, and hides it again before you record.",
         "", "---", ""]
    for i, sl in enumerate(slides, 1):
        head = strip_html(sl.get("head") or sl.get("company") or "")
        tag = "  `CUT FOR TIME`" if sl.get("optional") else ""
        L += [f"## {i:02d} — {head}   `{sl.get('target','?')}s`{tag}", ""]
        if sl.get("sub"):
            L += ["> " + strip_html(sl["sub"]), ""]
        if sl.get("punch"):
            L += ["**On screen:** " + strip_html(sl["punch"]), ""]
        L += [strip_html(sl.get("notes", "")), ""]
        if sl.get("why"):
            # `why` is no longer rendered — it is the second half of what he says.
            L += [strip_html(sl["why"]), ""]
        L += ["---", ""]
    open(path, "w").write("\n".join(L))


def write_script_txt(path, snap, slides):
    """
    A plain-text script, one block per slide, for reading off a phone or a second
    screen while presenting. No markdown syntax to trip over mid-sentence.
    """
    fmt = lambda x: f"{x//60}:{x%60:02d}"                                 # noqa: E731
    total = sum(sl.get("target", 0) for sl in slides)
    W = 78
    L = [f"{snap['company']} ({snap['symbol']}) — SPOKEN SCRIPT",
         f"{len(slides)} slides · {fmt(total)} · price {snap['price']:.2f} as of {snap['asOf']}",
         "=" * W, ""]
    for i, sl in enumerate(slides, 1):
        head = strip_html(sl.get("head") or sl.get("company") or "")
        L += ["-" * W,
              f"SLIDE {i:02d}  ({sl.get('target','?')}s)"
              + ("   [CUT FOR TIME]" if sl.get("optional") else ""),
              f"HEADLINE: {head}"]
        if sl.get("punch"):
            L.append(f"ON SCREEN: {strip_html(sl['punch'])}")
        L += ["-" * W, ""]
        for para in (strip_html(sl.get("notes", "")), strip_html(sl.get("why", ""))):
            if not para:
                continue
            line, out = "", []
            for word in para.split():
                if len(line) + len(word) + 1 > W:
                    out.append(line); line = word
                else:
                    line = (line + " " + word).strip()
            if line:
                out.append(line)
            L += out + [""]
    L += ["=" * W, "END — cut to the chart."]
    open(path, "w").write("\n".join(L) + "\n")


def write_sources(path, snap, ep):
    L = [f"# {snap['company']} ({snap['symbol']}) — where every number came from", "",
         f"Deck built {snap['builtAt']}.", "",
         "Two checks stand behind this file:", "",
         "- `python3 scripts/audit_deck.py DVA` — the deck's arithmetic is self-consistent.",
         "- `python3 scripts/validate_facts.py DVA` — every figure below was found in the "
         "document it is attributed to.", "",
         "## SEC filings", ""]
    for k, v in ep["sources"].items():
        L.append(f"- **{k}** — {v['label']}  \n  {v['url']}")
    L += ["", "## Live Terminal API", "",
          "| Route | Source | Fetched | Age at build |", "|---|---|---|---|"]
    for r, pv in snap["provenance"].items():
        ts = datetime.fromtimestamp(pv["fetchedAt"]).strftime("%Y-%m-%d %H:%M:%S") if pv["fetchedAt"] else "—"
        age = f"{pv['ageS']:.0f}s" if pv["ageS"] is not None else "—"
        L.append(f"| `/api/{r}/{snap['symbol']}` | {pv['source'] or '—'} | {ts} | {age} |")

    L += ["", "## Deliberately not used", "",
          "- **The Terminal's `epsYears` / `ttmSeries`.** They overstate DVA's annual EPS by ~37% "
          "(FY2024 reads 14.71 against a reported 10.73; FY2023 10.38 against 7.42). The ratio tracks "
          "total net income over income *attributable to DaVita*, so the series appears to ignore "
          "noncontrolling interests — ~$311M/yr here. **This is a live Terminal bug** and it affects "
          "the dashboard's PRICE FOLLOWS EARNINGS chart for any company with large NCI. The deck builds "
          "its trailing-EPS series from the reported quarterly figures in the 8-Ks instead.",
          *([f"- **CFO minus capex as free cash flow.** The company's own definition differs from the "
             f"subtraction by about ${abs(snap['naiveFcfGap']):,.0f}M. The filing wins."]
            if snap.get("naiveFcfGap") is not None else []),
          "- **A trailing P/E.** The SEC XBRL pull has Q4'25 net income null, so it is not computable "
          "from our data. Every multiple in the deck is forward.", "",
          "## Flagged disagreements", "",
          f"- Nasdaq's one-year target (`/api/profile`) is ${snap['street']['nasdaqTarget']}, while the "
          f"analyst consensus mean (`/api/street`) is ${snap['street']['target']}. The deck shows the "
          "consensus mean and names its source.",
          "- `/api/fundamentals` reports $181M of Q2 repurchases; the 8-K reports $348M / 2.238M shares. "
          "The deck uses the filing figure. The XBRL gap is an open item.",
          f"- Coverage is thin: {snap['street']['analysts']} analysts rate the stock, and the 2028 "
          "consensus rests on 2 estimates. The deck says so on the valuation slide.", ""]
    open(path, "w").write("\n".join(L))


def main():
    sym = (sys.argv[1] if len(sys.argv) > 1 else "DVA").upper()
    ep_path = os.path.join(HERE, "episodes", f"{sym}.json")
    if not os.path.exists(ep_path):
        die(f"no episode file at {ep_path}. Filing-sourced facts are hand-verified per episode.")
    ep = json.load(open(ep_path))

    print(f"→ fetching live data for {sym} from {API} …")
    snap = build_snapshot(sym, ep)
    _steps = (f"{len(snap['indexed']['earn'])} trailing-EPS steps" if snap.get("indexed")
              else f"newly listed — {snap['quartersAvailable']} quarters, no trailing series")
    print(f"  price {snap['price']:.2f} · quote {snap['provenance']['quote']['ageS']:.0f}s old · "
          f"{len(snap['tape'])} tape points · {_steps}")
    if snap.get("rates"):          # DVA's derived per-payor split, if this deck has one
        print(f"  cross-check: derived per-payor split implies "
              f"${snap['rates']['impliedSegmentOpInc']:.0f}M segment operating income vs "
              f"${snap['rates']['reportedSegmentOpInc']}M reported "
              f"({snap['rates']['crossCheckErrPct']:.1f}% off)")

    # Price-dependent prose resolves against the snapshot before any slide sees it.
    ep["verdict"] = resolve_prose(ep["verdict"], snap)
    slides = deck_module(sym).slides(snap, ep, fact, snap["quarters"])
    total = sum(s.get("target", 0) for s in slides)
    optional = [s for s in slides if s.get("optional")]
    core = total - sum(s.get("target", 0) for s in optional)
    fmt = lambda x: f"{x//60}m {x%60}s"                                   # noqa: E731
    print(f"  {len(slides)} slides · full cut {fmt(total)} · "
          f"core cut {fmt(core)} dropping the {len(optional)} marked slides")
    if core > 300:
        print(f"  ! even the core cut is {fmt(core)} — over the 5:00 FA budget")

    payload = {
        "symbol": sym, "company": ep["company"],
        "price": snap["price"], "sharesOutstanding": snap["sharesNow"],
        "stamp": f"{snap['symbol']} · {snap['price']:.2f} as of {snap['asOf']} · "
                 f"built {snap['builtAt'][:16].replace('T', ' ')}",
        "totalTarget": total, "coreTarget": core, "optionalCount": len(optional),
        "fairValue": ep["fairValue"], "slides": slides,
    }

    outdir = deckpath.write_dir(sym, ep["episodeDate"])
    os.makedirs(os.path.join(outdir, "data"), exist_ok=True)

    tpl = open(os.path.join(HERE, "deck_template.html")).read()
    html = (tpl.replace("__TITLE__", f"{ep['company']} ({sym}) — {ep['episodeDate']}")
               .replace("__PAYLOAD__", json.dumps(payload, separators=(",", ":"))))
    deck_path = os.path.join(outdir, f"{sym}-{ep['episodeDate']}.html")
    open(deck_path, "w").write(html)

    json.dump({"snapshot": snap, "payload": payload, "episode": ep},
              open(os.path.join(outdir, "data", f"{sym}-{ep['episodeDate']}.json"), "w"), indent=1)
    write_script(os.path.join(outdir, "SCRIPT.md"), snap, slides)
    write_script_txt(os.path.join(outdir, "SCRIPT.txt"), snap, slides)
    write_sources(os.path.join(outdir, "SOURCES.md"), snap, ep)

    print(f"\n✓ {deck_path}")
    print(f"  {outdir}/SCRIPT.md · SCRIPT.txt · SOURCES.md · data/{sym}-{ep['episodeDate']}.json")
    print(f"\n  open '{deck_path}'")


if __name__ == "__main__":
    main()
