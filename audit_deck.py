#!/usr/bin/env python3
"""
audit_deck.py — prove every number in a generated deck is real.

    python3 scripts/audit_deck.py DVA
    python3 scripts/audit_deck.py DVA --prove   # perturb a value, confirm it fires

The deck goes on camera under Nikil's name, so "it rendered" is not the bar.
Each check below re-derives a figure from an independent path and fails on
disagreement. A check that cannot fail is worthless — `--prove` corrupts the
snapshot and asserts the suite goes red.
"""

import json
import os
import re
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import deckpath  # noqa: E402
import marketdata  # noqa: E402

# The audit re-derives every structural figure from a fresh fetch. Same local
# data layer the build used; TERMINAL_API switches back to HTTP for comparison.
API = os.environ.get("TERMINAL_API", "").rstrip("/") or None

FAILS, WARNS, PASSES, SKIPS = [], [], [], []

# What counts as a typed figure: a percentage, a money amount, or a MULTIPLE.
# The multiple arm is not optional — the bug this whole check exists for was
# "49x this year's guided revenue", which carries neither a % nor a $.
FIGURE_RE = (r"(?<![\d.])\d[\d,]*(?:\.\d+)?\s?%"
             r"|\$\s?\d[\d,]*(?:\.\d+)?"
             r"|(?<![\d.])\d[\d,]*(?:\.\d+)?\s?[x\u00d7](?![a-z])")

def _flatten(v):
    """Episode prose fields are sometimes a string, sometimes a list of them."""
    if v is None:
        return []
    return [v] if isinstance(v, str) else [x for x in v if isinstance(x, str)]


def ok(name):
    PASSES.append(name)


def bad(name, detail):
    FAILS.append(f"{name}: {detail}")


def warn(name, detail):
    WARNS.append(f"{name}: {detail}")


def close(a, b, tol=0.01):
    return a is not None and b is not None and abs(a - b) <= tol * max(1.0, abs(b))


def api(route, sym):
    """
    Live re-fetch, used to re-derive every structural figure. This is the one hard
    dependency the audit has on a running data source — say so plainly rather than
    dumping a urllib traceback.
    """
    where = f"{API}/{route}/{sym}" if API else f"marketdata.{route}({sym})"
    try:
        if API:
            with urllib.request.urlopen(f"{API}/{route}/{sym}", timeout=90) as r:
                return json.loads(r.read().decode())
        return marketdata.get(route, sym)
    except Exception as e:                                        # noqa: BLE001
        sys.exit(f"AUDIT CANNOT RUN: {where} failed: {e}\n"
                 f"  The audit re-derives every figure from a fresh fetch, so it needs\n"
                 f"  the same upstreams the build used: SEC XBRL, Yahoo, Nasdaq.")


# --------------------------------------------------------------------------

def audit_episode_sourcing(ep):
    """Every filing fact must name the document it was read from."""
    missing = []

    def walk(node, path):
        if isinstance(node, dict):
            if "v" in node and not isinstance(node.get("v"), (dict, list)):
                if "src" not in node:
                    missing.append(".".join(path))
                elif node["src"] not in ep["sources"]:
                    missing.append(".".join(path) + f" (unknown src {node['src']})")
                return
            for k, v in node.items():
                if not k.startswith("_"):
                    walk(v, path + [k])
        elif isinstance(node, list):
            for i, v in enumerate(node):
                walk(v, path + [str(i)])

    walk(ep["filings"], [])
    if missing:
        bad("episode-sourcing", f"{len(missing)} facts without a valid src: {missing[:5]}")
    else:
        ok("episode-sourcing")

    for k, v in ep["sources"].items():
        if not v.get("url", "").startswith("https://www.sec.gov/"):
            bad("source-urls", f"{k} does not point at sec.gov")
            return
    ok("source-urls")


def audit_no_hardcoded_figures(ep):
    """
    The template must contain no financial literals — every figure has to come
    through the payload. A number typed into the shell is a number that cannot
    drift-check and cannot be audited.
    """
    tpl = open(os.path.join(HERE, "deck_template.html")).read()
    tpl = re.sub(r"/\*.*?\*/", "", tpl, flags=re.S)          # block comments
    tpl = re.sub(r"(?m)^\s*//.*$", "", tpl)                  # JS line comments — never rendered
    body = tpl.split("<script>", 1)[1] if "<script>" in tpl else tpl
    hits = re.findall(r"\$\s?\d[\d,]*\.?\d*", body)
    hits = [h for h in hits if h not in ("$0",)]
    if hits:
        bad("no-hardcoded-figures", f"template carries literal money values: {hits[:6]}")
        return

    # The deck modules are the other half. A typed "44% drawdown" shipped on three
    # slides while every other check stayed green, because nothing looked at the
    # string literals in decks/<SYM>.py. Percentages and money in *prose* must be
    # interpolated from the snapshot, never written out.
    import ast as _ast
    import glob as _glob
    lit = []
    for f in sorted(_glob.glob(os.path.join(HERE, "decks", "*.py"))):
        tree = _ast.parse(open(f).read())
        # Docstrings explain the module to me; they never reach a slide.
        docs = {id(_ast.get_docstring(n, clean=False) and n.body[0].value)
                for n in _ast.walk(tree)
                if isinstance(n, (_ast.Module, _ast.FunctionDef, _ast.ClassDef)) and n.body
                and isinstance(n.body[0], _ast.Expr) and isinstance(n.body[0].value, _ast.Constant)
                and isinstance(n.body[0].value.value, str)}
        # Definitional label text ("Deals closed over $1M") is not a data claim.
        # It must be declared, so every exception is a decision someone made.
        allowed = set()
        for n in tree.body:
            if isinstance(n, _ast.Assign) and any(
                    getattr(tg, "id", None) == "LITERALS_OK" for tg in n.targets):
                allowed = {e.value for e in n.value.elts}
        for node in _ast.walk(tree):
            if not isinstance(node, _ast.Constant) or not isinstance(node.value, str):
                continue
            if id(node) in docs:
                continue
            # Allowed phrases are stripped before scanning, so a declared
            # "$100" basis does not whitelist the rest of the sentence.
            text = node.value
            for phrase in allowed:
                text = text.replace(phrase, "")
            for h in re.findall(FIGURE_RE,
                                text):
                lit.append(f"{os.path.basename(f)}:{node.lineno} {h!r}")
    if lit:
        bad("no-hardcoded-figures",
            f"deck modules carry typed figures ({len(lit)}): {lit[:8]} — interpolate from snap "
            f"or declare in LITERALS_OK")
        return

    # The third hiding place. The verdict reasons on the last slide said
    # "At $169 ... 49 times the revenue" while the live snapshot said $172.01 and
    # 53x — typed once, never updated, and no check was looking here.
    # Structural figures — read off a filing and fixed for the quarter — may be
    # written out, but the episode has to DECLARE them, so each one is a decision.
    # Anything that moves with the price must be a token.
    declared = tuple(ep.get("proseLiteralsOK", ()))
    ep_lit = []
    for key in ("why", "callLine", "watch", "working"):
        for i, line in enumerate(_flatten(ep.get("verdict", {}).get(key))):
            for phrase in declared:
                line = line.replace(phrase, "")
            for h in re.findall(FIGURE_RE, line):
                ep_lit.append(f"verdict.{key}[{i}] {h!r}")
    if ep_lit:
        bad("no-hardcoded-figures",
            f"episode verdict prose carries typed figures ({len(ep_lit)}): {ep_lit[:8]} — "
            f"write them as {{path|fmt}} tokens so they resolve from the live snapshot")
        return
    ok("no-hardcoded-figures (template and all deck modules)")


def audit_snapshot_vs_api(snap, sym):
    """Re-fetch and re-derive. Prices move; structural figures must not."""
    fund = api("fundamentals", sym)
    qs = fund["quarters"]

    # A company that listed this quarter has no trailing-twelve-month anything.
    # The engine sets these to None on purpose; the audit checks they stayed None
    # rather than quietly becoming a number.
    if snap.get("newlyListed"):
        if snap["ttmRev"] is not None or snap["ttmRevGrowth"] is not None:
            bad("ttm-revenue", "newly-listed build produced a trailing-twelve-month figure "
                               "from fewer than eight quarters")
            return
        if len(qs) >= 8:
            bad("ttm-revenue", f"marked newly listed but the API now serves {len(qs)} quarters — "
                               "rebuild without the flag")
            return
        SKIPS.append(f"ttm-revenue: newly listed, {len(qs)} quarters available")
        SKIPS.append("ttm-growth: newly listed, no year-ago trailing base")
    else:
        ttm = sum(q["revenue"] for q in qs[4:8]) * 1000
        if not close(snap["ttmRev"], ttm, 0.001):
            bad("ttm-revenue", f"snapshot {snap['ttmRev']:.0f} vs recomputed {ttm:.0f}")
        else:
            ok("ttm-revenue")

        prior = sum(q["revenue"] for q in qs[0:4]) * 1000
        growth = (ttm / prior - 1) * 100
        if not close(snap["ttmRevGrowth"], growth, 0.001):
            bad("ttm-growth", f"snapshot {snap['ttmRevGrowth']:.3f}% vs recomputed {growth:.3f}%")
        else:
            ok("ttm-growth")

    est = api("estimates", sym)
    ey = {e["period"]: e["eps"] for e in est.get("yearly", []) if e.get("eps")}
    for f in snap["fwd"]:
        if f["period"] not in ey:
            bad("forward-eps", f"{f['period']} no longer in consensus")
            return
        if not close(f["eps"], ey[f["period"]], 0.001):
            bad("forward-eps", f"{f['period']} snapshot {f['eps']} vs live {ey[f['period']]}")
            return
        if f["eps"] <= 0:
            if f["pe"] is not None:
                bad("forward-pe", f"{f['period']} has a P/E on a loss-making estimate")
                return
        elif not close(f["pe"], snap["price"] / f["eps"], 0.001):
            bad("forward-pe", f"{f['period']} P/E does not equal price / EPS")
            return
    ok("forward-eps")
    ok("forward-pe")


def audit_no_trailing_multiple(snap, ep, html):
    """
    Two separate rules, previously conflated.

    1. A trailing P/E is never shown. The SEC XBRL pull has Q4'25 net income
       null, so the Terminal cannot compute one, and every multiple in the deck
       is forward.
    2. A trailing EARNINGS SERIES is allowed — the deck's indexed chart uses one
       — but only if every quarter in it carries a reported EPS attributed to a
       filing. That is a different question from whether the XBRL has it, and
       the original check wrongly banned both together.
    """
    for pat in (r"trailing\s+P/?E", r"trailing\s+multiple", r"\bP/?E\s+of\s+\d"):
        if re.search(pat, html, re.I):
            bad("no-trailing-pe", f"deck shows a trailing multiple (/{pat}/) — forward only")
            return
    ok("no-trailing-pe")

    if not snap.get("indexed"):
        SKIPS.append("trailing-eps-sourced: no trailing earnings series — the company has "
                     "either not been public four quarters or has never reported a profit")
        SKIPS.append("indexed-series: no trailing series to index against")
        return

    rows = ep["filings"]["quarterly"]["rows"]
    for step in snap["indexed"]["earn"]:
        k = next(i for i, r in enumerate(rows) if r["q"] == step["_q"])
        window = rows[k - 3:k + 1]
        if len(window) != 4:
            bad("trailing-eps-sourced", f"{step['_q']} trailing window is not four quarters")
            return
        for w in window:
            if w.get("eps") is None or not w.get("src"):
                bad("trailing-eps-sourced",
                    f"{step['q']} window includes {w['q']} with no reported, sourced EPS")
                return
        want = round(sum(w["eps"] for w in window), 2)
        if not close(step["_eps"], want, 0.0001):
            bad("trailing-eps-sourced",
                f"{step['q']} trailing EPS {step['_eps']} != sum of four reported quarters {want}")
            return
    ok(f"trailing-eps-sourced ({len(snap['indexed']['earn'])} steps, all from reported quarters)")

    ix = snap["indexed"]
    if not close(ix["earnGain"], (ix["endEps"] / ix["baseEps"] - 1) * 100, 0.001):
        bad("indexed-series", "earnings gain is not derived from the base and end trailing EPS")
    elif not close(ix["priceGain"], (ix["endPrice"] / ix["basePrice"] - 1) * 100, 0.001):
        bad("indexed-series", "price gain is not derived from the base and end closes")
    elif abs(ix["price"][0]["v"] - 100) > 0.01 or abs(ix["earn"][0]["v"] - 100) > 0.01:
        bad("indexed-series", "both series must start at exactly 100 — that is what makes one axis legal")
    else:
        ok("indexed-series")


def audit_fcf_is_quoted(snap, ep, html):
    """
    Company-defined FCF must be the one on screen. CFO minus capex off the XBRL
    gives a different number — putting that on camera would be wrong.
    Only applies where the episode quotes a trailing FCF figure.
    """
    if "fcfTTM" not in ep["filings"].get("results", {}):
        SKIPS.append("fcf-quoted: this episode quotes no trailing FCF figure")
        return
    quoted = ep["filings"]["results"]["fcfTTM"]["v"]
    fund = api("fundamentals", ep["symbol"])
    qs = fund["quarters"]
    naive = sum((q["cfo"] or 0) - (q["capex"] or 0) for q in qs[4:8]) * 1000
    if close(quoted, naive, 0.02):
        warn("fcf-quoted", "the naive CFO−capex now agrees with the filing; check the definition")
    # Match however decks/fmt.py would have rendered it, not one hardcoded shape.
    sys.path.insert(0, HERE)
    from decks import fmt as _F
    if _F.usd(naive) in html:
        bad("fcf-quoted", f"the naive CFO−capex figure ({_F.usd(naive)}) is on a slide")
        return
    if _F.usd(quoted) not in html:
        bad("fcf-quoted",
            f"the filing's FCF ({_F.usd(quoted)}) does not appear in the deck")
        return
    ok(f"fcf-quoted ({_F.usd(quoted)} from the filing, not {_F.usd(naive)} from CFO−capex)")


def audit_payor_derivation(snap, ep):
    if not snap.get("rates"):
        SKIPS.append(f"payor-derivation: no derived per-payor split in this episode")
        return
    """
    The per-payor rate split is derived, not disclosed. It only ships because
    it reproduces reported segment operating income. Re-verify that here.
    """
    r = snap["rates"]
    F = ep["filings"]
    cpp = F["payorStructure"]["commercialPctOfPatients"]["v"] / 100
    blended = F["unitEconomics"]["revPerTreatmentQ2"]["v"]

    recon = cpp * r["com"] + (1 - cpp) * r["gov"]
    if not close(recon, blended, 0.001):
        bad("payor-split-blends", f"weighted rates give {recon:.2f}, filing says {blended:.2f}")
    else:
        ok("payor-split-blends")

    if r["crossCheckErrPct"] > 12:
        bad("payor-split-crosscheck",
            f"implied segment op income is {r['crossCheckErrPct']:.1f}% off reported")
    else:
        ok(f"payor-split-crosscheck ({r['crossCheckErrPct']:.1f}% off reported)")


def audit_guidance_math(snap, ep):
    g, F = snap.get("guide") or {}, ep["filings"]
    if "adjEpsLow" not in F.get("guidance", {}).get("current", {}):
        SKIPS.append("guidance-math: this company does not guide to an EPS range")
        return
    cur, prior = F["guidance"]["current"], F["guidance"]["prior"]

    unchanged = (cur["adjEpsLow"] == prior["adjEpsLow"] and cur["adjEpsHigh"] == prior["adjEpsHigh"])
    if g["unchanged"] != unchanged:
        bad("guidance-unchanged", "the snapshot's unchanged flag disagrees with the two 8-Ks")
    else:
        ok("guidance-unchanged")

    h1 = F["results"]["epsH1_26"]["v"]
    if not (close(g["h2Low"], cur["adjEpsLow"] - h1, 0.001)
            and close(g["h2High"], cur["adjEpsHigh"] - h1, 0.001)):
        bad("implied-h2", "implied H2 EPS is not full-year guidance minus reported H1")
    else:
        ok("implied-h2")

    if not close(g["q2Annualised"], F["results"]["epsQ2"]["v"] * 2, 0.001):
        bad("q2-annualised", "Q2 annualised is not 2x reported Q2 EPS")
    else:
        ok("q2-annualised")

    if not close(g["fcfH1"], F["results"]["fcfQ1"]["v"] + F["results"]["fcfQ2"]["v"], 0.001):
        bad("h1-fcf", "H1 FCF is not Q1 + Q2 as reported")
    else:
        ok("h1-fcf")


def audit_bridge(snap, ep):
    if not snap.get("bridge"):
        SKIPS.append(f"bridge: no segment bridge in this episode")
        return
    b, s = snap["bridge"], ep["filings"]["segments"]
    parts = b["dialysis"] + b["ancillary"] + b["corporate"]
    if not close(parts, b["total"], 0.001):
        bad("bridge-sums", f"segment deltas sum to {parts}, total delta is {b['total']}")
    elif not close(s["q1_26"]["total"] + b["total"], s["q2_26"]["total"], 0.001):
        bad("bridge-endpoints", "the bridge does not land on reported Q2 operating income")
    else:
        ok("bridge-sums")

    for label, seg in (("q1_26", s["q1_26"]), ("q2_26", s["q2_26"])):
        got = seg["usDialysis"] + seg["ancillary"] + seg["corporate"]
        if not close(got, seg["total"], 0.001):
            bad("segments-sum", f"{label} segments sum to {got}, filing total is {seg['total']}")
            return
    ok("segments-sum")


def audit_enterprise_value(snap, ep):
    mcap = snap["price"] * snap["sharesNow"]
    if snap.get("netDebt") is None:
        SKIPS.append("enterprise-value: episode carries no net debt figure")
        return
    if not close(snap["marketCap"], mcap, 0.001):
        bad("market-cap", "market cap is not price x shares outstanding")
    elif not close(snap["ev"], snap["marketCap"] + snap["netDebt"], 0.001):
        bad("enterprise-value", "EV is not market cap + net debt")
    elif "netDebtQ2" in ep["filings"]["balanceSheet"] and not close(
            snap["netDebt"], ep["filings"]["balanceSheet"]["netDebtQ2"]["v"], 0.001):
        bad("net-debt", "net debt does not match the filing")
    else:
        ok("market-cap")
        ok("enterprise-value")


def audit_earnings_history(snap, ep, sym, html):
    """
    Re-derive every earnings-day reaction from live daily bars, and re-derive
    each guidance action from the two 8-K figures either side of it.
    """
    hist = api("history", sym)
    import datetime as _dt
    days = [_dt.datetime.fromtimestamp(p["t"] / 1000, _dt.timezone.utc).strftime("%Y-%m-%d")
            for p in hist["points"]]
    for r in snap["releases"]:
        if r.get("kind") == "pending":
            # Built the same evening the release landed. There is no session to
            # verify yet; assert the engine left the move empty rather than
            # inventing one from the after-hours print.
            if r.get("move") is not None or r.get("reactDate") is not None:
                bad("earnings-reaction", f"{r['q']} is marked pending but carries a move")
                return
            continue
        nxt = [i for i, d in enumerate(days) if d > r["date"]]
        i = nxt[0]
        if days[i] != r["reactDate"]:
            bad("earnings-reaction-date", f"{r['q']} reaction session {r['reactDate']} vs {days[i]}")
            return
        mv = (hist["points"][i]["c"] / hist["points"][i - 1]["c"] - 1) * 100
        if not close(r["move"], mv, 0.001):
            bad("earnings-reaction", f"{r['q']} move {r['move']:.2f}% vs recomputed {mv:.2f}%")
            return
    ok("earnings-reaction")

    rels = ep["filings"]["earningsHistory"]["releases"]
    if all(f.get("guideLow") is None for f in rels):
        # A company that publishes no guidance has no midpoint path to check. The
        # reaction days above are still verified against the tape.
        SKIPS.append("guidance-midpoint: this company publishes no guidance")
        SKIPS.append("guidance-action: this company publishes no guidance")
        SKIPS.append("earnings-stats: no guidance revisions to count")
        SKIPS.append("earnings-claim: no guidance revisions to claim anything about")
        return
    for k, r in enumerate(snap["releases"]):
        f = rels[k]
        if not close(r["mid"], (f["guideLow"] + f["guideHigh"]) / 2, 0.0001):
            bad("guidance-midpoint", f"{r['q']} midpoint disagrees with the filing table")
            return
        if r.get("kind") == "pending":
            continue                      # no session yet; nothing to classify
        if k and rels[k - 1]["fy"] == f["fy"]:
            pm = (rels[k - 1]["guideLow"] + rels[k - 1]["guideHigh"]) / 2
            want = "up" if r["mid"] > pm + 1e-9 else "down" if r["mid"] < pm - 1e-9 else "flat"
            if r["kind"] != want:
                bad("guidance-action", f"{r['q']} classified '{r['kind']}', midpoints say '{want}'")
                return
        elif r["kind"] != "new":
            bad("guidance-action", f"{r['q']} starts a new fiscal year but is not marked 'new'")
            return
    ok("guidance-action")

    es = snap["earningsStats"]
    # A release whose session has not happened yet has move=None and is excluded
    # from every count — it cannot be up, down, or a verified revision.
    settled = [r for r in snap["releases"] if r.get("move") is not None]
    ups = [r for r in settled if r["move"] > 0]
    downs = [r for r in settled if r["move"] < 0]
    rev = [r for r in settled if r["kind"] not in ("new", "pending")]
    raised = [r for r in rev if r["kind"] == "up"]

    # Re-derive the counts rather than trust the snapshot's own arithmetic.
    if es["revisions"] != len(rev) or es["raised"] != len(raised):
        bad("earnings-stats", "earningsStats counts disagree with the release data")
        return
    if es["raisedAllPositive"] != all(r["move"] > 0 for r in raised):
        bad("earnings-stats", "the raisedAllPositive flag disagrees with the moves")
        return
    ok(f"earnings-stats ({len(ups)} up, {len(downs)} down, {len(raised)} of "
       f"{len(rev)} revisions were raises)")

    # Whatever count the deck states on screen must be the real one. Different
    # companies make opposite claims here — DVA rose only when the midpoint went
    # up; PLTR raised almost every time and still fell three times — so the
    # check verifies the stated number, never a fixed hypothesis.
    WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
             "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10}
    for verb, actual in (("fell", len(downs)), ("rose", len(ups))):
        for mm in re.finditer(rf"{verb}\s+(?:on\s+)?(\w+)\s+of\s+(?:these|them|eight|the)", html, re.I):
            tok = mm.group(1).lower()
            n = WORDS.get(tok, int(tok) if tok.isdigit() else None)
            if n is not None and n != actual:
                bad("earnings-claim",
                    f"deck says the stock {verb} on {tok} of them; the data says {actual}")
                return
    ok(f"earnings-claim (stated counts match: {len(ups)} up / {len(downs)} down)")


def audit_margin_ranking(snap, html, sym):
    """
    'Highest since Q4'24' is a checkable claim. Q2'26 at 16.3% is NOT a
    two-year high — Q3'24 was 16.4% and Q4'24 17.1%. Guard the corrected form.
    """
    fund = api("fundamentals", sym)
    qs = [q for q in fund["quarters"] if q.get("opInc") and q.get("revenue")]
    margins = [(q["label"], q["opInc"] / q["revenue"] * 100) for q in qs]
    latest_lab, latest = margins[-1]
    higher = [lab for lab, mg in margins[:-1] if mg > latest]

    if re.search(r"best in two years|highest in two years|two-year high", html, re.I):
        bad("margin-ranking", f"deck claims a two-year high, but {higher} were higher")
        return
    mref = re.search(r"highest since (Q\d'\d\d)", html)
    if mref:
        claimed = mref.group(1)
        after = [lab for lab, mg in margins if mg > latest and lab > claimed]
        if after:
            bad("margin-ranking", f"deck says 'highest since {claimed}' but {after} were higher since")
            return
        if claimed not in [lab for lab, _ in margins]:
            bad("margin-ranking", f"deck references {claimed}, which is not in the quarter series")
            return
        ok(f"margin-ranking (highest since {claimed}; {latest:.1f}%)")
    else:
        ok("margin-ranking (no ranking claim made)")


def audit_no_slide_crossrefs(payload):
    """
    Slides get cut for time, so any copy that points at a neighbour ("the next
    slide", "both of the next two") breaks silently in the shortened cut. Two
    such references had already drifted onto the wrong slides.
    """
    # "the next number", "the slide before" and "coming up" are the same bug as
    # "the next slide" — a pointer at a neighbour that survives being cut.
    # The loose nouns ("number", "one") only count FORWARD. "that last one"
    # points at the third figure inside the same band — ordinary prose, and
    # flagging it was a false positive. A forward pointer is the actual bug,
    # because the thing pointed at is what gets cut.
    pat = re.compile(
        r"\b(next|previous|last|following)\s+(slide|two slides|chart|page|section)\b"
        r"|\b(next|following)\s+(number|one|figure|chart)\b"
        r"|\bslide\s+\d+\b|\bon the next\b|\bcoming up\b"
        r"|\b(slide|chart)\s+(before|after)\s+(this|that|it)\b", re.I)
    hits = []
    for i, sl in enumerate(payload["slides"], 1):
        for field in ("head", "sub", "why", "callLine"):
            if sl.get(field) and pat.search(str(sl[field])):
                hits.append(f"slide {i} .{field}")
        for r in sl.get("reasons", []):
            if pat.search(str(r)):
                hits.append(f"slide {i} .reasons")
    if hits:
        bad("no-slide-crossrefs", f"order-dependent copy in {hits}")
    else:
        ok("no-slide-crossrefs")


def audit_share_basis(snap, payload, ep):
    """
    Diluted weighted-average shares (the chart's basis) and shares outstanding
    at the balance-sheet date are different numbers. Quoting a reduction against
    a mixed pair gave 25% on one slide and 23% on another for the same claim.
    """
    wa_then, wa_now = snap["sharesThen"], snap["sharesNowWA"]
    if not close(snap["shareReductionWA"], (wa_now / wa_then - 1) * 100, 0.001):
        bad("share-basis", "shareReductionWA is not derived from the weighted-average pair")
        return
    wa_pct = round(abs(snap["shareReductionWA"]))
    out_pct = round(abs(snap["shareReduction"]))
    if wa_pct == out_pct:
        ok(f"share-basis (both bases round to {wa_pct}%)")
        return
    # Only the like-for-like figure may be presented as "% of the company".
    body = json.dumps(payload["slides"]) + json.dumps(ep["verdict"])
    if re.search(rf"{out_pct}% of the company", body):
        bad("share-basis", f"{out_pct}% mixes weighted-average with outstanding; "
                           f"the like-for-like figure is {wa_pct}%")
        return
    if not re.search(r"\d+% of the company", body):
        # This check exists to stop a buyback claim being quoted on a mixed basis.
        # A company that has just issued shares makes no such claim, and inventing
        # one to satisfy the audit would be the opposite of the point.
        SKIPS.append("share-basis: the deck makes no share-count claim to check")
        return
    if not re.search(rf"{wa_pct}% of the company", body):
        bad("share-basis", f"expected the like-for-like {wa_pct}% to be the figure presented")
        return
    ok(f"share-basis (presents {wa_pct}% weighted-average, {out_pct}% outstanding kept distinct)")


# Kinds whose geometry spans [min, max] and can therefore draw a negative value.
# Everything else measures magnitude from zero, so a negative is either invisible
# or drawn upside down. `bars` needs zeroLine to get the deeper bottom gutter.
NEGATIVE_SAFE = {"bars", "bridge", "dumbbell", "line", "indexed", "smallmult",
                 "slope", "forecast", "distribution"}


def audit_negative_values(payload):
    """
    A chart handed a negative it cannot express is the bug behind two broken
    SpaceX slides. `bridge` was zero-based and drew 2587px into a 500px box;
    `dumbbell` pinned min to 0 and put a negative endpoint on top of the row
    label. Both are fixed, but the class recurs whenever a loss-making company
    meets a magnitude chart.
    """
    def numbers(node):
        if isinstance(node, bool):
            return
        if isinstance(node, (int, float)):
            yield node
        elif isinstance(node, dict):
            for k, v in node.items():
                if k in ("v", "from", "to", "lo", "hi", "mid", "value", "sold", "bought",
                         "price", "fairValue", "rangeLo", "rangeHi", "total", "avg",
                         "min", "max", "threshold", "compare", "now", "mean"):
                    yield from numbers(v)
                elif isinstance(v, (dict, list)):
                    yield from numbers(v)
        elif isinstance(node, list):
            for v in node:
                yield from numbers(v)

    problems = []
    for i, sl in enumerate(payload["slides"], 1):
        c = sl.get("chart")
        if not c:
            continue
        kind = c.get("kind")
        neg = [n for n in numbers(c) if n < 0]
        if not neg:
            continue
        if kind not in NEGATIVE_SAFE:
            problems.append(f"slide {i}: {kind} was handed {len(neg)} negative value(s) "
                            f"(min {min(neg):,.0f}) and measures from zero")
        elif kind == "bars" and not c.get("zeroLine"):
            problems.append(f"slide {i}: bars has negative values but no zeroLine, so the "
                            f"value labels hang into the category labels")
    if problems:
        bad("negative-values", f"{len(problems)}: {problems[:5]}")
        return
    ok("negative-values (every negative sits on a chart that can draw it)")


def audit_chart_shape(payload):
    """
    Every chart kind dereferences certain spec keys without a guard — `spec.rows`,
    `spec.steps`, `spec.series`. Hand a chart the wrong shape and it either throws
    (caught by the render guard, blank slide) or silently drops the data.

    Five SPCX charts shipped with the wrong keys and `chart-specs` passed all of
    them, because that check only asks whether the KIND exists. This one asks
    whether the SPEC fits it, and it reads the requirement straight out of the
    template so it cannot drift.
    """
    tpl = open(os.path.join(HERE, "deck_template.html")).read()
    fns = re.split(r"\nfunction (chart\w+)\(", tpl)
    required, known_keys, item_keys = {}, {}, {}
    for i in range(1, len(fns), 2):
        body = fns[i + 1].split("\nfunction ")[0]
        kind = fns[i].replace("chart", "").lower()
        keys = set(re.findall(r"spec\.(\w+)", body))
        known_keys[kind] = keys
        required[kind] = {k for k in keys
                          if re.search(rf"spec\.{k}\.(map|forEach|length|flatMap)", body)}
        # And what the chart reads off each ITEM of those collections. Checking
        # only top-level keys is how a rename of every `"v":` to `"when":` in a
        # deck module passed clean: the charts had no value to plot and nothing
        # looked inside the rows.
        for k in required[kind]:
            m = re.search(rf"spec\.{k}\.(?:map|forEach|flatMap)\(\s*\(?(\w+)", body)
            if m:
                pv = m.group(1)
                item_keys[(kind, k)] = set(re.findall(rf"\b{pv}\.(\w+)\b", body))
    problems = []
    for i, sl in enumerate(payload["slides"], 1):
        c = sl.get("chart")
        if not c:
            continue
        kind = c.get("kind")
        if kind not in required:
            continue                      # chart-specs already reports unknown kinds
        for k in sorted(required[kind] - set(c)):
            problems.append(f"slide {i} ({kind}) is missing required `{k}`")
        # A key the chart never reads is data thrown away silently.
        # `fmtKind` is read by the renderer, which resolves it into `fmt2` before
        # the chart sees it — universal, not per-kind.
        ignored = sorted(set(c) - known_keys[kind] - {"kind", "height", "fmt2", "fmtKind"})
        for k in ignored:
            problems.append(f"slide {i} ({kind}) passes `{k}`, which {kind} never reads")
        # Row level, both directions, in the only two forms that cannot be a
        # matter of taste: a key no row supplies that the chart needs to plot
        # anything, and a key every row supplies that the chart never reads.
        for coll in sorted(required[kind] & set(c)):
            reads = item_keys.get((kind, coll))
            items = [r for r in (c.get(coll) or []) if isinstance(r, dict)]
            if not reads or not items:
                continue
            supplied = set().union(*(set(r) for r in items))
            if not (reads & supplied):
                problems.append(f"slide {i} ({kind}) `{coll}` rows supply none of "
                                f"{sorted(reads)[:6]} — the chart has nothing to plot")
            for k in sorted(supplied - reads):
                # A leading underscore declares "carried on purpose, not for
                # render" — the same convention `_derived` already uses. Without
                # it there is no way to keep provenance beside the drawn values.
                if k.startswith("_"):
                    continue
                if all(k in r for r in items):
                    problems.append(f"slide {i} ({kind}) every `{coll}` row carries "
                                    f"`{k}`, which {kind} never reads")
    if problems:
        bad("chart-shape", f"{len(problems)} spec mismatch(es): {problems[:6]}")
        return
    ok(f"chart-shape (every spec matches what its chart reads)")


def audit_fmt_kinds(payload):
    """
    An unknown `fmtKind` falls back to money-in-millions without a word of
    complaint. That printed "$14M" for 14 million Starlink subscribers and
    "$102M" for a $102 monthly bill. Every name must exist in the template's FMT.
    """
    tpl = open(os.path.join(HERE, "deck_template.html")).read()
    block = re.search(r"const FMT = \{(.*?)\n\};", tpl, re.S)
    if not block:
        bad("fmt-kinds", "cannot find the FMT registry in the template")
        return
    known = set(re.findall(r"(\w+)\s*:", block.group(1)))
    used = set()
    for i, sl in enumerate(payload["slides"], 1):
        for m in re.finditer(r'"fmtKind":\s*"([^"]+)"', json.dumps(sl.get("chart") or {})):
            used.add((i, m.group(1)))
    unknown = sorted({f"slide {i}: {k}" for i, k in used if k not in known})
    if unknown:
        bad("fmt-kinds", f"{len(unknown)} unknown formatter(s): {unknown[:6]} — "
                         f"known: {sorted(known)}")
        return
    ok(f"fmt-kinds ({len({k for _, k in used})} distinct, all implemented)")


def audit_chart_specs(payload):
    """
    A `"fmt": None` — a Python callable slot that JSON-ified to null — threw
    inside the render map and blanked EVERY slide, not just its own. The deck
    now guards each chart, but the spec should never carry a null in the first
    place, and every chart kind must be one the template implements.
    """
    tpl = open(os.path.join(HERE, "deck_template.html")).read()
    known = set(re.findall(r"(\w+):chart\w+", tpl))
    problems = []
    for i, sl in enumerate(payload["slides"], 1):
        c = sl.get("chart")
        if not c:
            continue
        if c.get("kind") not in known:
            problems.append(f"slide {i} uses unknown chart kind '{c.get('kind')}' "
                            f"(template implements {sorted(known)})")

        def walk(node, path):
            if isinstance(node, dict):
                for k, v in node.items():
                    if v is None:
                        problems.append(f"slide {i} chart{path}.{k} is null")
                    else:
                        walk(v, f"{path}.{k}")
            elif isinstance(node, list):
                for j, v in enumerate(node):
                    walk(v, f"{path}[{j}]")

        walk(c, "")
    if problems:
        bad("chart-specs", "; ".join(problems[:4]))
    else:
        ok(f"chart-specs ({len(known)} kinds implemented, no nulls)")


def audit_slide_variety(payload):
    """
    The whole point of the visual pass: no single chart form should dominate.
    Flag it if one form carries more than a third of the slides.
    """
    from collections import Counter
    forms = Counter((sl.get("chart") or {}).get("kind") or sl["type"] for sl in payload["slides"])
    top, n = forms.most_common(1)[0]
    share = n / len(payload["slides"])
    if share > 0.34:
        bad("slide-variety", f"'{top}' is {n}/{len(payload['slides'])} slides ({share:.0%}) — too repetitive")
    else:
        ok(f"slide-variety ({len(forms)} distinct forms, most common '{top}' at {n})")


def audit_original_findings(ep, payload):
    """
    The channel's whole differentiator is showing something a headline recap
    cannot. A deck that only restates the press release has no reason to exist,
    so this is a build requirement, not an aspiration.

    Every episode declares at least three findings. Each must name the document
    it came from AND where inside it — "10-Q Note 3" beats "the 10-Q", because
    the second one is what you write when you did not actually read it. And the
    deck has to put them on screen.
    """
    f = ep.get("findings") or []
    if len(f) < 3:
        bad("original-findings",
            f"only {len(f)} declared findings — a deck needs at least 3 things the "
            "press release does not say, or it is a recap")
        return
    for i, x in enumerate(f, 1):
        for key in ("claim", "where", "src"):
            if not x.get(key):
                bad("original-findings", f"finding {i} has no `{key}`")
                return
        if x["src"] not in ep["sources"]:
            bad("original-findings", f"finding {i} cites unknown source {x['src']}")
            return
        # "the 10-Q" is not a location. Demand a note, page, table or statement.
        if not re.search(r"note|page|table|statement|line|footnote|arithmetic|derived|matched|"
                         r"cross-referenc|section|item", x["where"], re.I):
            bad("original-findings",
                f"finding {i} says only \"{x['where']}\" — name the note, page or table")
            return

    slide = next((s for s in payload["slides"] if s.get("type") == "findings"), None)
    if not slide:
        bad("original-findings", "the findings are declared but never put on a slide")
        return
    if len(slide.get("items") or []) != len(f):
        bad("original-findings", "the findings slide does not carry every declared finding")
        return
    ok(f"original-findings ({len(f)} declared, sourced to a named location, and on screen)")


def audit_entity_count(ep):
    """
    A count of named entities in a filing is an aggregate no filing states, so it
    is recomputed here rather than text-matched (the same rule the Form 4 totals
    follow). The 13G's Valor list is the live case, and it is a trap: four of the
    thirty names carry an internal comma ("Valor IV Space Holdings, LLC"), so a
    naive comma split returns 34.
    """
    node = None
    for blk in (ep.get("filings") or {}).values():
        if isinstance(blk, dict) and "valorEntityCount" in blk:
            node = blk["valorEntityCount"]; break
    if not node:
        SKIPS.append("entity-count: this episode declares no counted entity list")
        return
    url = ep["sources"][node["src"]]["url"]
    try:
        # validate_facts owns the filing cache; no second fetcher.
        import validate_facts
        txt = validate_facts.doc_text(url)
    except Exception as exc:                                          # noqa: BLE001
        bad("entity-count", f"cannot fetch {url}: {exc}")
        return
    m = re.search(r'held of record by the following entities[^:]*:(.*?)\. By virtue', txt, re.S)
    if not m:
        bad("entity-count", "cannot find the entity list in the filing")
        return
    parts = [x.strip() for x in m.group(1).split(",")]
    names, i = [], 0
    while i < len(parts):
        n = re.sub(r"^and\s+", "", parts[i])
        while i + 1 < len(parts) and re.fullmatch(
                r"(and\s+)?(LLC|L\.P\.|L\.L\.C\.|Inc\.?)", parts[i + 1].strip()):
            i += 1
            n += ", " + re.sub(r"^and\s+", "", parts[i].strip())
        names.append(n); i += 1
    if len(set(names)) != len(names):
        bad("entity-count", f"the filing lists {len(names)} names but only "
                            f"{len(set(names))} are distinct")
        return
    if len(names) != node["v"]:
        bad("entity-count", f"episode says {node['v']} entities, the filing lists {len(names)}")
        return

    # And the stake percentage, recomputed from the two inputs that ARE
    # text-verifiable, against the figure the filer put on the cover page.
    blk = next(b for b in ep["filings"].values()
               if isinstance(b, dict) and "valorEntityCount" in b)
    sh, base, stated = (blk.get("valorClassAShares"), blk.get("valorPctBase"),
                        blk.get("valorClassAPct"))
    if sh and base and stated:
        calc = sh["v"] / base["v"] * 100
        if abs(round(calc, 1) - stated["v"]) > 0.05:
            bad("entity-count", f"{sh['v']:,} / {base['v']:,} = {calc:.2f}%, which does not "
                                f"round to the filed {stated['v']}%")
            return
        ok(f"entity-count ({len(names)} entities recounted; {calc:.2f}% recomputed "
           f"against the filed {stated['v']}%)")
        return
    ok(f"entity-count ({len(names)} entities recounted from the filing itself)")


def audit_bridge_closes(payload):
    """
    A bridge asserts arithmetic on screen: start, plus each step, equals the total.
    If it does not close, a viewer who adds the labels catches the deck out.

    SPCX's AI bridge drew -1,257 + 1,885 + 516 under a total of 1,146 — the steps
    summed to 1,144, because the filing's reconciliation has a FOURTH line
    (restructuring, $2M) that the slide left out. Small enough to be invisible in
    the bars and still wrong. Tolerance is half a unit, for genuine rounding.
    """
    problems = []
    for i, sl in enumerate(payload["slides"], 1):
        c = sl.get("chart") or {}
        if c.get("kind") != "bridge":
            continue
        run = None
        for st in c.get("steps") or []:
            v, ty = st.get("v"), st.get("type")
            if v is None:
                continue
            if ty == "start":
                run = v
            elif ty == "step":
                run = v if run is None else run + v
            elif ty == "total":
                if run is not None and abs(run - v) > 0.5:
                    problems.append(f"slide {i}: steps sum to {run:,.1f} but the total "
                                    f"drawn is {v:,.1f} (off by {v - run:,.1f})")
                run = v
    if problems:
        bad("bridge-closes", f"{len(problems)} bridge(s) do not reconcile: {problems[:4]}")
        return
    n = sum(1 for sl in payload["slides"] if (sl.get("chart") or {}).get("kind") == "bridge")
    if not n:
        SKIPS.append("bridge-closes: this deck draws no bridge")
        return
    ok(f"bridge-closes ({n} bridge{'s' if n > 1 else ''} "
       f"{'sum' if n > 1 else 'sums'} to the total drawn)")


def audit_insider_aggregates(ep, sym):
    """
    The insider figures are aggregates across dozens of Form 4 filings, so no
    single document states them and `validate_facts` cannot text-match them.
    They get the verification they actually need: re-parse every cached Form 4
    and recompute the totals from scratch.
    """
    import glob
    import datetime as _dt
    import xml.etree.ElementTree as ET

    ins = ep["filings"].get("insider")
    if not ins:
        SKIPS.append("insider-aggregates: this episode has no insider block")
        return
    files = glob.glob(os.path.join(HERE, ".cache_form4", sym, "*.xml"))
    if not files:
        bad("insider-aggregates", f"no cached Form 4 XML in .cache_form4/{sym} — cannot verify")
        return

    def val(n, path):
        e = n.find(path)
        if e is None:
            return None
        v = e.find("value")
        s = (v.text if v is not None else e.text)
        return s.strip() if s and s.strip() else None

    sold_sh = bought_sh = 0.0
    sold_val = 0.0
    sellers, with_plan, with_tx = set(), 0, 0
    for f in files:
        root = ET.parse(f).getroot()
        txs = root.findall(".//nonDerivativeTransaction")
        if not txs:
            continue
        with_tx += 1
        blob = " ".join((e.text or "") for e in root.iter())
        if (root.findtext(".//aff10b5One") or "").strip() in ("1", "true") or "10b5-1" in blob:
            with_plan += 1
        owner = root.find(".//reportingOwner")
        name = val(owner, "reportingOwnerId/rptOwnerName") if owner is not None else None
        for t in txs:
            code = val(t, "transactionCoding/transactionCode")
            try:
                sh = float(val(t, "transactionAmounts/transactionShares") or 0)
                px = float(val(t, "transactionAmounts/transactionPricePerShare") or 0)
            except ValueError:
                continue
            if code == "S":                       # open-market sale
                sold_sh += sh
                sold_val += sh * px
                if name:
                    sellers.add(name)
            elif code == "P":                     # open-market purchase
                bought_sh += sh

    checks = [
        ("totalSoldShares", ins["totalSoldShares"], sold_sh, 1),
        ("totalSoldValue", ins["totalSoldValue"], sold_val / 1e6, 0.1),
        ("totalBought", ins["totalBought"], bought_sh, 0.5),
        ("distinctSellers", ins["distinctSellers"], len(sellers), 0.5),
        ("plan10b5Filings", ins["plan10b5Filings"], with_plan, 0.5),
        ("totalFilings", ins["totalFilings"], with_tx, 0.5),
    ]
    for name, stated, actual, tol in checks:
        if abs(stated - actual) > tol:
            bad("insider-aggregates",
                f"{name}: episode says {stated:,.1f}, recomputed from {len(files)} Form 4s "
                f"gives {actual:,.1f}")
            return

    bucket_sold = sum(b["sold"] for b in ins["buckets"])
    if abs(bucket_sold - sold_sh) > 1:
        bad("insider-aggregates",
            f"the recency buckets sum to {bucket_sold:,.0f} shares but the filings give {sold_sh:,.0f}")
        return
    ok(f"insider-aggregates (recomputed from {len(files)} Form 4 filings: "
       f"{sold_sh:,.0f} sold, {bought_sh:,.0f} bought)")


def audit_derived_arithmetic(snap, ep):
    """
    Sums we compute from printed components must reconcile to a printed total.
    Storing my own arithmetic as a 'fact' is how a typo becomes a source.
    """
    cb = snap.get("cb")
    if cb:
        parts = cb["netIncome"] + cb["dna"] + cb["sbc"] + cb["workingCapitalAndOther"]
        if abs(parts - cb["cfo"]) > 1:
            bad("derived-arithmetic", "cash bridge does not reconcile to reported operating cash flow")
            return
        if abs((cb["cfo"] - cb["capex"]) - cb["endpoint"]) > 1:
            bad("derived-arithmetic", "the bridge endpoint is not operating cash flow minus capex")
            return
    bb = snap.get("bb")
    if bb:
        a = sum(bb[k] for k in ("marketableSecurities", "cash", "receivables",
                                "otherCurrentAssets", "rouAssets", "otherAssets", "ppe"))
        le = sum(bb[k] for k in ("equityParent", "nci", "deferredRevenue", "customerDeposits",
                                 "payablesAccrued", "leaseLiabilities", "otherNoncurrent"))
        if abs(a - le) > 1:
            bad("derived-arithmetic", f"balance sheet does not balance: {a:,.0f} vs {le:,.0f}")
            return
    pb = snap.get("peers")
    if pb:
        for r in pb["rows"]:
            if r["ps"] <= 0 or r["growth"] is None:
                bad("derived-arithmetic", f"peer {r['sym']} has an unusable multiple or growth rate")
                return
        if not close(pb["psPremium"], pb["selfPs"] / pb["avgPs"], 0.001):
            bad("derived-arithmetic", "the peer premium is not self P/S over peer average")
            return
    ok("derived-arithmetic (cash bridge, balance sheet and peer multiples all reconcile)")


def audit_min_font_size(payload):
    """
    Nothing the camera sees may drop below 15px. A YouTube frame gets watched on
    a phone and compressed twice on the way there. The presenter-only surfaces
    (#notes, #grid, the HUD) and the deliberate footer chrome are exempt —
    everything else is content.
    """
    tpl = open(os.path.join(HERE, "deck_template.html")).read()
    tpl = re.sub(r"/\*.*?\*/", "", tpl, flags=re.S)
    css = tpl.split("</style>", 1)[0]
    exempt = ("#notes", "#grid", "#hud", ".stamp", ".pg", "@media print", ".gc", ".tot",
              ".footer")            # build slug and page number — deliberate chrome
    small = []
    for rule in css.split("}"):
        if "font-size:" not in rule:
            continue
        sel = rule.split("{")[0].strip()
        if any(e in sel for e in exempt):
            continue
        for m in re.finditer(r"font-size:\s*(\d+(?:\.\d+)?)px", rule):
            if float(m.group(1)) < 15:
                small.append(f"{sel.splitlines()[-1].strip()[:44]} @ {m.group(1)}px")
    # Inline sizes set on chart marks, which the CSS scan cannot see.
    for i, sl in enumerate(payload["slides"], 1):
        for m in re.finditer(r"font-size:(\d+(?:\.\d+)?)px", json.dumps(sl.get("chart") or {})):
            if float(m.group(1)) < 15:
                small.append(f"slide {i} chart mark @ {m.group(1)}px")
    if small:
        bad("min-font-size", f"{len(small)} on-camera rule(s) below the 15px floor: {small[:6]}")
        return
    ok("min-font-size (nothing on camera below 15px)")


def audit_chart_entities(payload):
    """
    Chart labels are written with `textContent`, so an HTML entity in one renders
    literally: "71.8&times;" appeared on screen, and the extra glyphs pushed the
    label into the next column. Entities belong in prose fields only.
    """
    hits = []
    for i, sl in enumerate(payload["slides"], 1):
        c = sl.get("chart")
        if not c:
            continue
        for e in sorted(set(re.findall(r"&[a-zA-Z]+;|&#\d+;", json.dumps(c)))):
            hits.append(f"slide {i} chart carries {e}")
    if hits:
        bad("chart-entities", "; ".join(hits) + " — chart labels are textContent, use the glyph")
        return
    ok("chart-entities (no HTML entities in any chart spec)")


def audit_provenance(snap):
    for route, p in snap["provenance"].items():
        if p["fetchedAt"] is None:
            bad("provenance", f"{route} has no fetch timestamp")
            return
    q = snap["provenance"]["quote"]
    if q["ageS"] is None or q["ageS"] > 120:
        bad("provenance", f"quote was {q['ageS']}s old at build — over the 120s contract ceiling")
        return
    ok("provenance")


def audit_slide_integrity(payload, snap):
    slides = payload["slides"]
    for i, sl in enumerate(slides, 1):
        if not sl.get("notes"):
            bad("slide-notes", f"slide {i} has no presenter notes")
            return
        if not sl.get("target"):
            bad("slide-notes", f"slide {i} has no target duration")
            return
    ok("slide-notes")

    total = sum(s["target"] for s in slides)
    if total != payload["totalTarget"]:
        bad("slide-timing", "payload totalTarget disagrees with the sum of slide targets")
    else:
        ok("slide-timing")

    if payload["price"] != snap["price"]:
        bad("payload-price", "payload price disagrees with the snapshot")
    else:
        ok("payload-price")


# --------------------------------------------------------------------------

def main():
    sym = (sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("-") else "DVA").upper()
    prove = "--prove" in sys.argv

    ep = json.load(open(os.path.join(HERE, "episodes", f"{sym}.json")))
    outdir = deckpath.read_dir(sym, ep["episodeDate"], die=lambda m: sys.exit("AUDIT: " + m))
    blob = json.load(open(os.path.join(outdir, "data", f"{sym}-{ep['episodeDate']}.json")))
    snap, payload = blob["snapshot"], blob["payload"]
    html = open(os.path.join(outdir, f"{sym}-{ep['episodeDate']}.html")).read()

    if prove:
        # Corrupt one derived value. Every downstream check should notice.
        if snap.get("ttmRev") is not None:
            snap["ttmRev"] = snap["ttmRev"] * 1.05
        else:                                   # newly listed — corrupt what exists instead
            snap["ttmRev"] = 1.0
        snap["ev"] = snap["ev"] + 500
        if snap.get("bridge"):
            snap["bridge"]["ancillary"] += 5
        if "h2Low" in (snap.get("guide") or {}):
            snap["guide"]["h2Low"] += 0.5
        snap["releases"][0]["move"] += 3
        if len(snap["releases"]) > 1:
            snap["releases"][-1]["kind"] = "up"
        snap["shareReductionWA"] = -31.0
        if snap.get("indexed"):
            snap["indexed"]["earnGain"] += 9
        payload["slides"][1]["why"] = "See the next slide for the rest."
        payload["slides"][1]["chart"]["fmt"] = None
        payload["slides"][1]["chart"]["_lab"] = "9.9&times;"
        payload["slides"][1]["chart"]["_style"] = "font-size:11px"
        payload["slides"][1]["chart"]["fmtKind"] = "notAFormatter"
        # hand a magnitude chart a negative, and a chart a key it never reads
        for _s in payload["slides"]:
            _c = _s.get("chart") or {}
            if _c.get("kind") and _c["kind"] not in NEGATIVE_SAFE:
                _c["_negProbe"] = {"v": -1}
                break
        for _s in payload["slides"]:
            if _s.get("chart"):
                _s["chart"]["notAKeyAnyChartReads"] = 1
                break
        ep["findings"] = (ep.get("findings") or [])[:2]
        ep.setdefault("verdict", {}).setdefault("why", [])
        ep["verdict"]["why"] = list(ep["verdict"]["why"]) + ["A stale typed 49x sneaks in here."]
        if snap.get("cb"):
            snap["cb"]["sbc"] += 1000
        if ep["filings"].get("insider"):
            ep["filings"]["insider"]["totalSoldValue"] += 40
        print("--prove: snapshot deliberately corrupted\n")

    audit_episode_sourcing(ep)
    audit_no_hardcoded_figures(ep)
    audit_snapshot_vs_api(snap, sym)
    audit_no_trailing_multiple(snap, ep, html)
    audit_fcf_is_quoted(snap, ep, html)
    audit_payor_derivation(snap, ep)
    audit_guidance_math(snap, ep)
    audit_bridge(snap, ep)
    audit_earnings_history(snap, ep, sym, html)
    audit_margin_ranking(snap, html, sym)
    audit_no_slide_crossrefs(payload)
    audit_share_basis(snap, payload, ep)
    audit_negative_values(payload)
    audit_chart_shape(payload)
    audit_fmt_kinds(payload)
    audit_chart_specs(payload)
    audit_slide_variety(payload)
    audit_original_findings(ep, payload)
    audit_enterprise_value(snap, ep)
    audit_min_font_size(payload)
    audit_chart_entities(payload)
    audit_insider_aggregates(ep, sym)
    audit_entity_count(ep)
    audit_bridge_closes(payload)
    audit_derived_arithmetic(snap, ep)
    audit_provenance(snap)
    audit_slide_integrity(payload, snap)

    for p in PASSES:
        print(f"  pass  {p}")
    for sk in SKIPS:
        print(f"  n/a   {sk}")
    for w in WARNS:
        print(f"  WARN  {w}")
    for f in FAILS:
        print(f"  FAIL  {f}")

    print()
    if prove:
        if FAILS:
            print(f"✓ --prove worked: {len(FAILS)} check(s) fired on corrupted input")
            sys.exit(0)
        print("✗ --prove FAILED: corrupted input passed every check. The suite is worthless.")
        sys.exit(1)

    if FAILS:
        print(f"✗ {len(FAILS)} FAILED, {len(PASSES)} passed")
        sys.exit(1)
    print(f"ALL DECK INVARIANTS PASS ({len(PASSES)} checks"
          + (f", {len(SKIPS)} n/a" if SKIPS else "")
          + (f", {len(WARNS)} warnings)" if WARNS else ")"))


if __name__ == "__main__":
    main()
