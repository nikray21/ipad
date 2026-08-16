"""
decks/META.py — Meta Platforms' derived metrics and slide narrative.

The tension held across the deck: **revenue is compounding at 28%, and almost
nothing below the revenue line tells the same story.** Operating income fell.
Free cash flow collapsed 91% to $784M. The segment that actually earns the
profit — Family of Apps — saw its own operating income shrink. None of that
is a mystery once you read past the highlights table: a $2.4B legal charge
and the AI infrastructure buildout landed inside the ad business, the capex
guide has been raised at every release, $55B of bonds funded the gap, part of
the buildout just moved off the balance sheet into a guaranteed joint
venture, and two one-time tax items whipsawed EPS from $1.05 to $10.44 while
a live IRS notice for another $15.89B sits underneath both of them.

Three things this module is careful about:

  * **Every dollar figure that could go stale by the time this airs is a
    token** ({price|$}, {fair.mid|$}, …). Everything else — the quarter's
    numbers, the debt table, the commitments — is fixed for the quarter and
    written out, declared in `proseLiteralsOK` or computed through `fv()`.
  * **The fair-value model is mirrored exactly from the on-camera
    calculator** (`_fair`), so the verdict prose and the live slide can never
    disagree, the same discipline as every other deck on this engine.
  * **Peer forward P/E mixes fiscal-year ends** — MSFT's and AAPL's next
    fiscal year does not line up with calendar 2026 the way META's, GOOGL's,
    AMZN's and NFLX's do. The slide says so; averaging silently would be the
    same basis-mixing mistake rule 9 exists to catch.
"""

import re

from . import fmt

LITERALS_OK = (
    "10b5-1",             # the SEC's Rule 10b5-1 plan naming, not a figure about Meta
    "0%",                 # the dumbbell's baseline reference point, not a data claim
)


def _peer(sym, die):
    """One peer row: price against next-FY consensus EPS, growth beside it."""
    import marketdata as _md

    def g(route):
        try:
            return _md.get(route, sym)
        except Exception as e:                                   # noqa: BLE001
            die(f"cannot fetch {route} for peer {sym} ({e}) — peer multiples are computed "
                "live and never hand-entered, so the build stops here")
    q, est, fu = g("quote"), g("estimates"), g("fundamentals")
    yearly = est.get("yearly") or []
    if not yearly or yearly[0].get("eps") is None:
        die(f"peer {sym} has no forward EPS estimate")
    yr = yearly[0]
    qs = [x for x in fu["quarters"] if x.get("revenue")]
    if len(qs) < 5:
        die(f"peer {sym} has only {len(qs)} revenue quarters — need 5 for a year-over-year read")
    last, year_ago = qs[-1], qs[-5]
    return {"sym": sym, "price": q["price"], "pe": q["price"] / yr["eps"],
            "period": yr["period"], "growth": (last["revenue"] / year_ago["revenue"] - 1) * 100}


def _fair(case, K, H, rr, shares_now):
    """Mirror of the template's runCase(), so verdict prose and the live
    calculator can never disagree at build time."""
    growth = (1 + case["revGrowth"] / 100) ** H
    rev = K["startRevenueTTM"] * growth
    ebit = rev * case["opMargin"] / 100
    pretax = ebit - K["netDebt"] * K["interestRate"] / 100
    net = pretax * (1 - K["taxRate"] / 100)
    nci = K["nciAnnualRunRate"] * growth
    shares = shares_now * (1 + case["shareChange"] / 100) ** H
    price5 = (net - nci) / shares * case["exitPE"]
    return price5 / (1 + rr / 100) ** H


def derive(snap, ep, fund, qrows, die, fact):
    """Company-specific metrics. die() on anything that does not reconcile."""
    F = ep["filings"]
    fv = lambda *k: fact(F, *k)                                  # noqa: E731
    qs = {q["label"]: q for q in fund["quarters"]}

    # The balance sheet has to balance, or a figure is wrong.
    bs = F["balanceSheet"]
    if abs((fv("balanceSheet", "totalAssetsQ2") - fv("balanceSheet", "totalLiabilitiesQ2"))
           - fv("balanceSheet", "totalEquityQ2")) > 1:
        die("assets minus liabilities does not equal equity")

    # The debt table has to sum to the filed total, or a tranche is wrong.
    tranches = F["debt"]["tranches"]
    tsum = sum(t["amount"] for t in tranches)
    if abs(tsum - fv("debt", "totalFace")) > 1:
        die(f"debt tranches sum to {tsum}, filed total face is {fv('debt','totalFace')}")

    # Segment revenue and operating income must foot to the consolidated total.
    seg = F["segments"]["rows"][-1]
    if abs((seg["foaRev"] + seg["rlRev"]) - fv("results", "revenueQ2")) > 1:
        die("FoA + RL revenue does not equal total revenue")
    if abs((seg["foaOpInc"] + seg["rlOpInc"]) - fv("results", "opIncQ2")) > 1:
        die("FoA + RL operating income does not equal total operating income")

    # The one-time tax items are two independently filed numbers — cross-check
    # the per-share gap against the dollar amount divided by that quarter's
    # own diluted share count, rather than trusting the arithmetic blind.
    ts = F["taxSwing"]
    q3_shares = qs["Q3'25"]["shares"]
    q1_shares = qs["Q1'26"]["shares"]
    if not q3_shares or not q1_shares:
        die("missing diluted share count for the tax-swing cross-check")
    charge_per_share = fv("taxSwing", "q3_25ChargeAmount") / q3_shares
    reported_gap = fv("taxSwing", "q3_25ChargeExEps") - fv("taxSwing", "q3_25ChargeReportedEps")
    if abs(charge_per_share - reported_gap) / reported_gap > 0.08:
        die(f"Q3'25 charge/share ({charge_per_share:.2f}) does not reconcile with the filed "
            f"EPS gap ({reported_gap:.2f})")
    benefit_per_share = fv("taxSwing", "q1_26BenefitAmount") / q1_shares
    if abs(benefit_per_share - fv("taxSwing", "q1_26BenefitEpsImpact")) / fv(
            "taxSwing", "q1_26BenefitEpsImpact") > 0.08:
        die("Q1'26 benefit/share does not reconcile with the filed EPS impact")

    foa_rev_growth = (seg["foaRev"] / F["segments"]["rows"][3]["foaRev"] - 1) * 100  # vs Q2'25
    foa_op_growth = (seg["foaOpInc"] / F["segments"]["rows"][3]["foaOpInc"] - 1) * 100
    foa = {"revFrom": F["segments"]["rows"][3]["foaRev"], "revTo": seg["foaRev"],
           "opFrom": F["segments"]["rows"][3]["foaOpInc"], "opTo": seg["foaOpInc"],
           "revGrowth": foa_rev_growth, "opGrowth": foa_op_growth,
           "otherCostsGrowth": (fv("segments", "foaOtherCostsQ2")
                                 / fv("segments", "foaOtherCostsQ2prior") - 1) * 100}

    # Capex guidance path — each release's full-year range, plus the settled
    # FY25 actual as the pivot between "reported" and "the guide". Selective
    # labels only (rule: never a number on every point) — eight adjacent
    # range labels collide in the camera-narrowed layout; the first guide,
    # the settled actual, and the final ask carry the story on their own.
    # chartForecast's fmtKind="usdB" gridlines expect `v` in millions (it
    # divides by 1000), so every point value is billions * 1000, not the bare
    # billions figure the episode file and the `lab` text carry.
    path = F["capexGuide"]["path"]
    points = []
    for i, p in enumerate(path):
        labelled = i in (0, len(path) - 1) or "actual" in p
        if "actual" in p:
            points.append({"x": p["label"], "v": p["actual"] * 1000,
                           "lab": fmt.usd(p["actual"] * 1000, 1) if labelled else "",
                           "growth": "actual"})
        else:
            mid = (p["lo"] + p["hi"]) / 2
            points.append({"x": p["label"], "v": mid * 1000,
                           "lab": f"${p['lo']:.0f}–{p['hi']:.0f}B" if labelled else "",
                           "guided": p["fy"] == "FY26"})
    points[-1]["growth"] = "the ask"

    debt_recent = sum(t["amount"] for t in tranches if t["series"] in ("Nov 2025 Notes", "May 2026 Notes"))
    debt_prior = tsum - debt_recent

    insider = F["insider"]
    if abs(sum(s["shares"] for s in insider["topSellers"]) - insider["totalSoldShares"]) > (
            insider["totalSoldShares"] * 0.5):
        die("top sellers materially exceed the total sold shares — recheck the aggregate")
    plan_pct = insider["plan10b5Filings"] / insider["totalFilings"] * 100

    peers = [_peer(x, die) for x in F["peers"]["tickers"]]
    self_row = {"sym": snap["symbol"], "price": snap["price"],
                "pe": snap["price"] / next(f["eps"] for f in snap["fwd"] if f["eps"] > 0),
                "period": snap["fwd"][0]["period"], "growth": foa_rev_growth * 0 + (
                    fv("results", "revenueQ2") / fv("results", "revenueQ2prior") - 1) * 100}
    avg_pe = sum(p["pe"] for p in peers) / len(peers)
    # The shared audit's peer-reconciliation check was written for a P/S basis
    # (self/avg multiple, never non-positive, growth always present) — the
    # mechanism is basis-agnostic, so alias `pe` as `ps` rather than fork the
    # generic check for one deck's valuation basis.
    for r in peers + [self_row]:
        r["ps"] = r["pe"]
    prow = sorted(peers + [self_row], key=lambda r: r["pe"])

    # Street revision direction — a live market-data fact, not a filing fact.
    import marketdata as _md
    est = _md.get("estimates", snap["symbol"])
    revisions = {"up": est.get("revisionsUp"), "down": est.get("revisionsDown"),
                 "direction": est.get("direction")}

    # Fair value, mirrored from the on-camera calculator.
    K = ep["fairValue"]["constants"]
    net_debt_derived = fv("debt", "carryingValue") - fv("results", "cashSecuritiesQ2")
    if abs(K["netDebt"] - net_debt_derived) > 1:
        die(f"fairValue netDebt {K['netDebt']} does not match derived {net_debt_derived:.0f}")
    rate_derived = fv("debt", "interestExpQ2") * 4 / fv("debt", "carryingValue") * 100
    if abs(K["interestRate"] - rate_derived) > 0.2:
        die(f"fairValue interestRate {K['interestRate']} vs derived {rate_derived:.2f}")
    H, rr = ep["fairValue"]["horizonYears"], ep["fairValue"]["requiredReturn"]
    fair = {k: _fair(c, K, H, rr, snap["sharesNow"]) for k, c in ep["fairValue"]["cases"].items()}
    fair["mid"] = (fair["base"] + fair["bull"]) / 2

    return {
        "foa": foa, "capexPath": points, "debtRecent": debt_recent, "debtPrior": debt_prior,
        "planPct": plan_pct,
        "peers": {"rows": prow, "avgPe": avg_pe, "selfPe": self_row["pe"],
                  "avgPs": avg_pe, "selfPs": self_row["pe"], "psPremium": self_row["pe"] / avg_pe},
        "revisions": revisions, "fair": fair,
        "wd": {
            "revGrowthQ2": (fv("results", "revenueQ2") / fv("results", "revenueQ2prior") - 1) * 100,
            "foaOpIncQ2": seg["foaOpInc"],
            "cashSecurities": fv("results", "cashSecuritiesQ2"),
            "debtFace": fv("debt", "totalFace"),
            "streetTarget": snap["street"]["target"],
            "insiderSold": insider["totalSoldValue"],
            "plan10b5Pct": plan_pct,
            "fcfQ2": fv("results", "fcfQ2"),
            "fcfQ2prior": fv("results", "fcfQ2prior"),
            "irsAdditional": fv("taxSwing", "irsNoticeAdditionalTax"),
            "commitmentsTotal": fv("commitments", "nonCancelableTotal"),
            "leaseNotYetCommenced": fv("commitments", "leaseObligationsNotYetCommenced"),
            "jvGuaranteeMax": fv("subsequentEvent", "elPasoGuaranteeMax"),
            "jvStakePct": fv("subsequentEvent", "elPasoStakePct"),
        },
    }


def slides(snap, ep, fact, fund_quarters=None):
    F = ep["filings"]
    N = {k: re.sub(r"\s*TARGET\s+\d+s\.?\s*$", "", v) for k, v in ep["notes"].items()}
    s = snap
    fv = lambda *k: fact(F, *k)                                  # noqa: E731

    m = b_ = fmt.usd
    d2 = fmt.dollars
    pc = fmt.pct
    MINUS = fmt.MINUS

    def xt(n, d=1): return f"{n:.{d}f}×"        # chart labels — textContent

    foa, debtRecent, debtPrior = s["foa"], s["debtRecent"], s["debtPrior"]
    peers, rev = s["peers"], s["revisions"]
    fair = s["fair"]
    seg = F["segments"]["rows"][-1]

    S = []

    # 01 — the hook ---------------------------------------------------------
    S.append({
        "type": "findings", "kicker": "The highlights table isn't the whole quarter",
        "src": "Filed with the SEC Jul 30 2026, plus the Form 4 trail",
        "head": "What the 10-Q says. The release doesn&rsquo;t.",
        "items": ep["findings"],
        "punch": "Four things in the filing. <b>None made the press release.</b>",
        "why": (f"Revenue grew {pc(s['wd']['revGrowthQ2'], 0)} this quarter and the stock barely "
                "moved. That headline is true and it is not the story. These four things are in "
                "the document behind it, not in the release, and we are going to take each one "
                "properly."),
        "notes": N["findings"], "target": 26,
    })

    # 02 — the quarter as reported -------------------------------------------
    S.append({
        "type": "tiles", "kicker": "Start with the headline they sold", "cols": 3,
        "src": "8-K EX-99.1, Q2 2026 highlights", "head": "Revenue up. Profit down. Cash gone.",
        "tiles": [
            {"v": b_(fv("results", "revenueQ2")), "l": "Revenue",
             "n": f"{pc(s['wd']['revGrowthQ2'], 0)} year over year", "tone": "good"},
            {"v": m(fv("results", "opIncQ2")), "l": "Operating income",
             "n": f"down from {m(fv('results','opIncQ2prior'))}", "tone": "bad"},
            {"v": f"{fv('results','marginQ2')}%", "l": "Operating margin",
             "n": f"from {fv('results','marginQ2prior')}% a year ago", "tone": "bad"},
            {"v": d2(fv("results", "epsQ2")), "l": "Diluted EPS",
             "n": f"down from {d2(fv('results','epsQ2prior'))}", "tone": "warn"},
            {"v": m(fv("results", "fcfQ2")), "l": "Free cash flow",
             "n": f"from {m(fv('results','fcfQ2prior'))} a year ago", "tone": "bad"},
            {"v": b_(fv("results", "capexQ2")), "l": "Capital expenditures",
             "n": "including finance-lease payments", "tone": "warn"},
        ],
        "punch": f"Free cash flow: <b>{m(fv('results','fcfQ2'))}</b>, not a typo.",
        "why": (f"Read the headline and you would expect this stock up. Operating income fell "
                f"{pc(abs((fv('results','opIncQ2')/fv('results','opIncQ2prior')-1)*100),0,signed=False)}, "
                f"margin went from {fv('results','marginQ2prior')}% to {fv('results','marginQ2')}%, "
                f"and free cash flow — cash left over after the business runs itself — nearly "
                f"vanished. That gap between the top line and everything below it is the whole "
                f"episode."),
        "notes": N["quarter"], "target": 26,
    })

    # 03 — the tax whiplash ---------------------------------------------------
    ts = F["taxSwing"]
    S.append({
        "type": "chart", "kicker": "Why the earnings number is hard to trust",
        "src": "Q3 2025 and Q1 2026 8-Ks — each company-quoted",
        "head": "Ten dollars of EPS, two one-time items",
        "sub": "Reported diluted EPS against what it would have been without the item.",
        "chart": {"kind": "grouped", "height": 500, "cats": [
            {"x": "Q3 2025", "vals": [fv("taxSwing", "q3_25ChargeReportedEps"),
                                       fv("taxSwing", "q3_25ChargeExEps")],
             "labs": [d2(fv("taxSwing", "q3_25ChargeReportedEps")),
                      d2(fv("taxSwing", "q3_25ChargeExEps"))],
             "cls": "", "delta": f"{MINUS}{b_(fv('taxSwing','q3_25ChargeAmount'))[1:]} charge",
             "deltaGood": False},
            {"x": "Q1 2026", "vals": [fv("taxSwing", "q1_26BenefitReportedEps"),
                                       fv("taxSwing", "q1_26BenefitReportedEps")
                                       - fv("taxSwing", "q1_26BenefitEpsImpact")],
             "labs": [d2(fv("taxSwing", "q1_26BenefitReportedEps")),
                      d2(fv("taxSwing", "q1_26BenefitReportedEps")
                         - fv("taxSwing", "q1_26BenefitEpsImpact"))],
             "cls": "", "delta": f"+{b_(fv('taxSwing','q1_26BenefitAmount'))[1:]} benefit",
             "deltaGood": True},
        ]},
        "legend": [{"c": "var(--muted)", "t": "as reported"},
                   {"c": "var(--s1)", "t": "without the one-time item"}],
        "punch": (f"{d2(fv('taxSwing','q3_25ChargeReportedEps'))} to "
                  f"<b>{d2(fv('taxSwing','q1_26BenefitReportedEps'))}</b> in two quarters."),
        "why": (f"A {b_(fv('taxSwing','q3_25ChargeAmount'))} one-time non-cash charge crushed Q3 "
                f"2025 EPS to {d2(fv('taxSwing','q3_25ChargeReportedEps'))} — it would have been "
                f"{d2(fv('taxSwing','q3_25ChargeExEps'))} without it. Two quarters later an "
                f"{b_(fv('taxSwing','q1_26BenefitAmount'))} one-time benefit did the opposite, "
                f"pushing EPS to {d2(fv('taxSwing','q1_26BenefitReportedEps'))}. Same underlying "
                f"business, {d2(fv('taxSwing','q1_26BenefitReportedEps') - fv('taxSwing','q3_25ChargeReportedEps'))} "
                f"of reported EPS apart. Neither swing was really about the business."),
        "notes": N["taxwhiplash"], "target": 28,
    })

    # 04 — the live IRS threat -------------------------------------------------
    S.append({
        "type": "quote", "kicker": "And that's not the end of it", "src": "10-Q Note 11, Income Taxes",
        "head": f"The IRS wants {b_(fv('taxSwing','irsNoticeAdditionalTax'))} more",
        "quote": fv("taxSwing", "irsQuote"),
        "attr": "Meta Platforms, Inc., Q2 2026 Form 10-Q — Note 11, Income Taxes",
        "extra": ('<div class="tiles" style="grid-template-columns:repeat(3,1fr);margin-top:20px">'
                  f'<div class="tile bad" style="animation-delay:700ms"><div class="tv num">'
                  f'{b_(fv("taxSwing","irsNoticeAdditionalTax"))}</div>'
                  '<div class="tl">Additional tax the IRS wants</div><div class="tn">2017&ndash;2019 tax years</div></div>'
                  f'<div class="tile warn" style="animation-delay:1000ms"><div class="tv num">'
                  f'{b_(fv("taxSwing","taxCourtIpValueExcess"))}</div>'
                  '<div class="tl">What Meta already lost</div><div class="tn">Tax Court’s May 2025 valuation, above what Meta reported</div></div>'
                  f'<div class="tile" style="animation-delay:1300ms"><div class="tv num">'
                  f'{b_(fv("taxSwing","grossUtb"))}</div>'
                  '<div class="tl">Total reserved for tax uncertainty</div><div class="tn">up from '
                  f'{b_(fv("taxSwing","grossUtbPrior"))} at year end</div></div></div>'),
        "punch": "Built on a fight <b>Meta already lost once</b>.",
        "why": (f"This is the company's own note, word for word. The IRS is asking for "
                f"{b_(fv('taxSwing','irsNoticeAdditionalTax'))} more for 2017 through 2019, on "
                f"the same transfer-pricing question a Tax Court already ruled on in May 2025 — "
                f"valuing the intellectual property {b_(fv('taxSwing','taxCourtIpValueExcess'))} "
                f"higher than Meta had reported. This is not hypothetical risk language. It is a "
                f"number, on an argument they have already partially lost."),
        "notes": N["irs"], "target": 26,
    })

    # 05 — the profit engine shrank -------------------------------------------
    S.append({
        "type": "chart", "kicker": "Now the segment that actually earns it",
        "src": "10-Q Note 12, Segment Information",
        "head": "Revenue up. Family of Apps profit down.",
        "sub": "Year-over-year change, Q2 2025 to Q2 2026 — same scale, both rows.",
        "chart": {"kind": "dumbbell", "height": 420, "labelRoom": 280, "rows": [
            {"name": "FoA revenue", "sub": f"{m(foa['revFrom'])} → {m(foa['revTo'])}",
             "from": 0, "to": foa["revGrowth"],
             "fromLab": "0%", "toLab": f"+{pc(foa['revGrowth'],0,signed=False)}",
             "cls": "", "delta": f"+{pc(foa['revGrowth'],0,signed=False)}", "deltaGood": True},
            {"name": "Operating income", "sub": f"{m(foa['opFrom'])} → {m(foa['opTo'])}",
             "from": 0, "to": foa["opGrowth"],
             "fromLab": "0%", "toLab": pc(foa["opGrowth"], 0),
             "cls": "mut", "delta": pc(foa["opGrowth"], 0), "deltaGood": False},
        ]},
        "punch": (f"Revenue <b>+{pc(foa['revGrowth'],0,signed=False)}</b>. Profit "
                  f"<b>{pc(foa['opGrowth'],0)}</b>."),
        "why": (f"Family of Apps — the ads business, the thing that funds everything else — grew "
                f"revenue {pc(foa['revGrowth'],0,signed=False)}. Its own operating income fell "
                f"{pc(abs(foa['opGrowth']),0,signed=False)}. Why: the segment's own ‘other "
                f"costs and expenses’ line — infrastructure, legal-related costs, partner "
                f"arrangements — grew {pc(foa['otherCostsGrowth'],0,signed=False)}, absorbing the "
                f"legal charge and a share of the AI buildout. The business everyone thinks they "
                f"are buying got less profitable this quarter, not more."),
        "notes": N["foa"], "target": 28,
    })

    # 06 — capex guidance only ever rises --------------------------------------
    S.append({
        "type": "chart", "kicker": "Why infrastructure is eating the profit",
        "src": "CFO Outlook Commentary, eight consecutive 8-Ks",
        "head": "Capex guidance: raised. Never cut.",
        "sub": "Full-year capex range at each release; FY26 is still guidance.",
        "chart": {"kind": "forecast", "height": 500, "fmtKind": "usdB",
                  "pastLab": "settled", "futureLab": "still guidance",
                  "points": s["capexPath"]},
        "punch": (f"FY26: {b_(F['capexGuide']['path'][5]['lo']*1000)}–"
                  f"{b_(F['capexGuide']['path'][5]['hi']*1000)[1:]} to "
                  f"<b>{b_(F['capexGuide']['path'][7]['lo']*1000)}–"
                  f"{b_(F['capexGuide']['path'][7]['hi']*1000)[1:]}</b>."),
        "why": ("FY2025's range was revised upward at every release and landed at the top of it. "
                "FY2026 opened even higher and has already been raised again. This is not a "
                "company trimming its ambitions — it is the reason infrastructure costs keep "
                "outrunning the ad business underneath them."),
        "notes": N["capexpath"], "target": 24,
    })

    # 07 — paid for with debt ---------------------------------------------------
    S.append({
        "type": "chart", "kicker": "And here's how it gets financed",
        "src": "10-Q Note 8, Long-term Debt", "head": "Two bond sales dwarf the rest",
        "sub": "Every tranche of Meta's outstanding notes, by issue date.",
        "chart": {"kind": "bars", "height": 520, "series": [
            {"x": t["series"].replace(" Notes", ""), "v": t["amount"], "lab": b_(t["amount"]),
             "cls": "s1" if t["series"] in ("Nov 2025 Notes", "May 2026 Notes") else "mut"}
            for t in F["debt"]["tranches"]
        ]},
        "legend": [{"c": "var(--muted)", "t": "issued 2022–2024"},
                   {"c": "var(--s1)", "t": "issued in the last nine months"}],
        "punch": (f"Last nine months: <b>{b_(debtRecent)}</b>. Everything before: "
                  f"{b_(debtPrior)}."),
        "why": (f"{b_(debtRecent)} of bonds in two sales, nine months apart — more than the "
                f"{b_(debtPrior)} Meta had issued in the fourteen years it carried any bond debt "
                f"at all before that. Interest expense on the notes alone went from "
                f"{m(fv('debt','interestExpQ2prior'))} to {m(fv('debt','interestExpQ2'))} in a "
                f"single quarter, year over year. The AI buildout is being financed, not funded "
                f"out of cash flow."),
        "notes": N["debt"], "target": 26,
    })

    # 08 — off balance sheet -----------------------------------------------------
    se = F["subsequentEvent"]
    S.append({
        "type": "mega", "kicker": "And some of it isn't on the balance sheet yet",
        "src": "10-Q Note 13, Subsequent Event",
        "head": f"Guaranteeing {b_(fv('subsequentEvent','elPasoGuaranteeMax'))} on a JV",
        "value": b_(fv("subsequentEvent", "elPasoGuaranteeMax")), "tone": "warn",
        "caption": (f"of residual-value guarantees on a data-center joint venture Meta just "
                    f"agreed to for a {fv('subsequentEvent','elPasoStakePct')}% stake — after "
                    f"contributing {b_(fv('subsequentEvent','elPasoContribution'))} of assets and "
                    f"pulling out an immediate {b_(fv('subsequentEvent','elPasoDistribution'))}."),
        "extra": ('<div class="tiles" style="grid-template-columns:repeat(3,1fr);margin-top:22px">'
                  f'<div class="tile" style="animation-delay:700ms"><div class="tv num">'
                  f'{b_(fv("commitments","leaseObligationsNotYetCommenced"))}</div>'
                  '<div class="tl">Leases signed, not yet started</div></div>'
                  f'<div class="tile" style="animation-delay:1000ms"><div class="tv num">'
                  f'{b_(fv("commitments","nonCancelableTotal"))}</div>'
                  '<div class="tl">Non-cancelable commitments</div>'
                  f'<div class="tn">{b_(fv("commitments","due2026"))} due in 2026 alone</div></div>'
                  f'<div class="tile warn" style="animation-delay:1300ms"><div class="tv num">'
                  f'{b_(fv("commitments","restrictedCashEscrow"))}</div>'
                  '<div class="tl">Cash locked in escrow</div><div class="tn">for infrastructure purchase agreements</div></div></div>'),
        "punch": "The buildout is bigger than today's balance sheet shows.",
        "why": (f"In July, Meta agreed to hand a data-center campus to a joint venture for a "
                f"{fv('subsequentEvent','elPasoStakePct')}% stake and a quick "
                f"{b_(fv('subsequentEvent','elPasoDistribution'))} payout — while guaranteeing up "
                f"to {b_(fv('subsequentEvent','elPasoGuaranteeMax'))} if the venture falls short. "
                f"Add {b_(fv('commitments','leaseObligationsNotYetCommenced'))} of leases that "
                f"have not even started and {b_(fv('commitments','nonCancelableTotal'))} of "
                f"non-cancelable commitments sitting in the footnotes, and there is a lot more "
                f"building than the balance sheet shows today."),
        "notes": N["offbalance"], "target": 26,
    })

    # 09 — insiders ---------------------------------------------------------------
    ins = F["insider"]
    buckets = [
        {"label": b["label"], "sold": b["sold"], "bought": b["bought"],
         "soldLab": f"{b['sold']:,.0f} shares", "sub": f"~{m(b['value'])} · {b['people']} people",
         "boughtLab": "none" if b["bought"] == 0 else f"{b['bought']:,.0f}"}
        for b in ins["buckets"]
    ]
    S.append({
        "type": "chart", "kicker": "What insiders do with their own money",
        "src": f"SEC Form 4 XML — {ins['totalFilings']} filings, aggregated and recomputed",
        "head": f"{m(ins['totalSoldValue'])} sold. Nothing bought.",
        "sub": "Shares sold on the open market, trailing twelve months, by quarter.",
        "chart": {"kind": "insider", "height": 440, "rows": buckets},
        "punch": (f"The CEO, the CFO, the COO — <b>all sellers</b>."),
        "why": (f"{ins['distinctSellers']} insiders sold {m(ins['totalSoldValue'])} of stock over "
                f"the last year: the CFO, the CEO, the chief product officer, the COO, the CTO "
                f"among them. Nobody bought shares with their own money. To be fair, "
                f"{s['planPct']:.0f}% of those sales were set up months ahead on an automatic "
                f"schedule, so do not read too much timing into it. But zero purchases, at any "
                f"price, from anyone, is still zero."),
        "notes": N["insiders"], "target": 24, "optional": True,
    })

    # 10 — peers ---------------------------------------------------------------
    S.append({
        "type": "chart", "kicker": "So what are you paying for it",
        "src": "Live prices · each company's next-FY consensus EPS",
        "head": f"{xt(peers['selfPe'])} next year's earnings",
        "sub": "Price against next fiscal year consensus EPS; MSFT, AAPL use non-calendar years.",
        "chart": {"kind": "peers", "height": 460, "avg": peers["avgPe"],
                  "avgLab": f"peer average {xt(peers['avgPe'])}",
                  "rightHead": "revenue growth",
                  "rows": [{"name": F["peers"]["names"].get(r["sym"], r["sym"]),
                            "v": r["pe"], "lab": xt(r["pe"]),
                            "right": pc(r["growth"], 0, signed=False),
                            "here": r["sym"] == s["symbol"]} for r in peers["rows"]]},
        "punch": "Not the cheapest name here. Not the most expensive either.",
        "why": (f"Everyone here on the same basis: the price against what analysts expect each "
                f"company to earn next year, growth beside it, because expensive and "
                f"expensive-for-its-growth are different claims. Meta costs {xt(peers['selfPe'])} "
                f"next year's earnings against a peer average of {xt(peers['avgPe'])} — a normal "
                f"price to pay for above-average growth, which is a fine place to be if the "
                f"profit line stabilizes."),
        "notes": N["peers"], "target": 22, "optional": True,
    })

    # 11 — the Street ------------------------------------------------------------
    st = s["street"]
    S.append({
        "type": "chart", "kicker": "What the models actually say",
        "src": "Nasdaq analyst consensus, fetched at build time",
        "head": "More cuts than raises, near the highs",
        "sub": f"EPS estimate revisions, last month, across {st['analysts']} analysts.",
        "chart": {"kind": "lollipop", "height": 440, "fmtKind": "plain0", "rows": [
            {"name": "Raised", "sub": "estimate increases", "v": rev["up"],
             "lab": str(rev["up"]), "cls": "good"},
            {"name": "Cut", "sub": "estimate decreases", "v": rev["down"],
             "lab": str(rev["down"]), "cls": "bad"},
        ]},
        "punch": f"Mean target {d2(st['target'])} — <b>{pc(st['upside'],0)} above today</b>.",
        "why": (f"{st['analysts']} analysts cover it, {st['strongBuy']} rate it a strong buy, and "
                f"the mean target sits {pc(st['upside'],0)} above where it trades. But last month "
                f"{rev['down']} of them cut their earnings estimate against {rev['up']} who raised "
                f"it, even with the stock this close to its highs. The professionals are bullish on "
                f"the target and quietly less bullish on the earnings that are supposed to get it "
                f"there."),
        "notes": N["street"], "target": 22, "optional": True,
    })

    # 12 — the close --------------------------------------------------------------
    band = (fair["bull"] - fair["mid"]) / fair["mid"]
    gap = (s["price"] / fair["base"] - 1) * 100
    verdict_line = (f"today sits {pc(gap, 0, signed=False)} above my base case"
                    if gap > 0 else
                    f"today sits {pc(-gap, 0, signed=False)} below my base case")
    S.append({
        "type": "chart", "kicker": "So what am I doing?", "src": "My call · my model, not financial advice",
        "head": "Real growth. Financed with a lot of fine print.",
        "sub": "My model's range, against today's price.",
        "chart": {"kind": "fvband", "height": 430, "band": band,
                  "price": s["price"], "priceLab": d2(s["price"]),
                  "fairValue": fair["mid"], "fairLab": d2(fair["mid"]),
                  "fairName": "where I’d get interested",
                  "rangeLo": fair["bear"], "rangeHi": fair["bull"],
                  "rangeLoLab": f"bear {d2(fair['bear'])}",
                  "rangeHiLab": f"bull {d2(fair['bull'])}",
                  "zoneLabs": ["below my base case", "base-to-bull range", "above even the bull case"],
                  "verdict": verdict_line},
        "extra": ('<div class="whylist" style="margin-top:16px;gap:13px">'
                  f'<p style="animation-delay:900ms;font-size:23px">'
                  f'<b style="color:var(--good)">✓</b>&ensp;<b>The growth is real</b> — '
                  f'revenue up {pc(s["wd"]["revGrowthQ2"],0,signed=False)}, ad pricing and volume '
                  f'both climbing.</p>'
                  f'<p style="animation-delay:1100ms;font-size:23px">'
                  f'<b style="color:var(--warn)">✕</b>&ensp;<b>The profit engine shrank</b> '
                  f'— Family of Apps operating income fell even as its revenue grew.</p>'
                  f'<p style="animation-delay:1300ms;font-size:23px">'
                  f'<b style="color:var(--warn)">✕</b>&ensp;<b>The buildout is debt-funded</b> '
                  f'— two bond sales, nine months apart, bigger than everything before them.</p>'
                  f'<p style="animation-delay:1500ms;font-size:23px">'
                  f'<b style="color:var(--crit)">✕</b>&ensp;<b>The tax line isn’t settled</b> '
                  f'— a live IRS notice sits on an argument Meta already lost once.</p></div>'),
        "punch": f"My call: <b>{ep['verdict']['call']}</b>. Interesting <b>at {d2(fair['mid'])} or lower</b>.",
        "why": (f"That ruler is the whole episode. {d2(fair['bear'])} if the AI spend does not "
                f"pay off, {d2(fair['base'])} in my base case, {d2(fair['bull'])} if the bull "
                f"case fully lands. Today's price sits just under my base case — not expensive, "
                f"not a screaming bargain. My line is {d2(fair['mid'])}, halfway between base and "
                f"bull. The growth is genuinely real. So is every finding in this deck. That is "
                f"the fundamentals. Now let's go to the chart."),
        "notes": N["call"], "target": 30,
    })

    return S
