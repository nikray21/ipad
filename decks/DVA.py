"""
decks/DVA.py — DaVita's derived metrics and slide narrative.

The generator is generic; the *story* is not. Everything here is specific to
this company: the payor split, the segment bridge, the guidance arithmetic and
the twenty-four slides that argue the case. A new ticker gets a new module like
this one plus an episodes/<SYM>.json — it never edits build_deck.py.
"""

import re

from . import fmt


def derive(snap, ep, fund, qrows, die, fact):
    """Return the extra snapshot keys this company's slides need."""
    F = ep["filings"]
    qs = fund["quarters"]
    net_debt = fact(F, "balanceSheet", "netDebtQ2")
    ev = snap["marketCap"] + net_debt
    g = F["guidance"]["current"]
    # Capital structure: reported total debt beside XBRL shareholders' equity.
    eq_by_end = {q["endDate"]: q["equity"] for q in fund["quarters"]}
    funded = []
    for r in qrows:
        e = eq_by_end.get(r["end"])
        if e is None:
            die(f"no equity figure for {r['q']} ({r['end']}) — cannot draw the funding chart")
        funded.append({"q": r["q"], "debt": r["debt"], "equity": e * 1000, "lev": r["lev"]})

    # Payor mix
    pm = F["payorMixQ2"]
    a, b = pm["y2026"], pm["y2025"]
    gov26 = a["medicare"] + a["medicaid"] + a["otherGov"]
    gov25 = b["medicare"] + b["medicaid"] + b["otherGov"]
    tot26, tot25 = gov26 + a["commercial"], gov25 + b["commercial"]
    payor = {
        "gov26": gov26 / 1000, "gov25": gov25 / 1000,
        "com26": a["commercial"] / 1000, "com25": b["commercial"] / 1000,
        "govGrowth": (gov26 / gov25 - 1) * 100,
        "comGrowth": (a["commercial"] / b["commercial"] - 1) * 100,
        "comShare26": a["commercial"] / tot26 * 100,
        "comShare25": b["commercial"] / tot25 * 100,
        "govDollars": (gov26 - gov25) / 1000,
        "comDollars": (a["commercial"] - b["commercial"]) / 1000,
    }
    payor["shareShiftBps"] = (payor["comShare26"] - payor["comShare25"]) * 100

    # Derived per-payor rates. DaVita discloses the ratio (11% of patients ->
    # 26% of revenue) but never the two rates. Solved from the blended rate.
    # Labelled as derived wherever it appears.
    cpp = fact(F, "payorStructure", "commercialPctOfPatients") / 100
    cpr = fact(F, "payorStructure", "commercialPctOfRevenue") / 100
    blended = fact(F, "unitEconomics", "revPerTreatmentQ2")
    cost = fact(F, "unitEconomics", "costPerTreatmentQ2")
    ratio = (cpr / cpp) / ((1 - cpr) / (1 - cpp))       # commercial rate / government rate
    gov_rate = blended / (cpp * ratio + (1 - cpp))
    com_rate = gov_rate * ratio
    rates = {"ratio": ratio, "gov": gov_rate, "com": com_rate,
             "govMargin": gov_rate - cost, "comMargin": com_rate - cost, "cost": cost}

    # Cross-check the derivation against reported segment operating income.
    # If the implied model misses badly the split is wrong and must not ship.
    tx = fact(F, "operations", "treatmentsQ2")
    implied = (tx * cpp * rates["comMargin"] + tx * (1 - cpp) * rates["govMargin"]) / 1e6
    ga_dna = 331 + 146                                   # 10-Q, U.S. dialysis G&A + D&A, $M
    rates["impliedSegmentOpInc"] = implied - ga_dna
    rates["reportedSegmentOpInc"] = F["segments"]["q2_26"]["usDialysis"]
    rates["crossCheckErrPct"] = abs(rates["impliedSegmentOpInc"] / rates["reportedSegmentOpInc"] - 1) * 100
    if rates["crossCheckErrPct"] > 12:
        die(f"per-payor rate derivation misses reported segment operating income by "
            f"{rates['crossCheckErrPct']:.1f}% — do not put it on screen")

    # Segment bridge
    s2, s1 = F["segments"]["q2_26"], F["segments"]["q1_26"]
    bridge = {
        "start": s1["total"], "end": s2["total"],
        "dialysis": s2["usDialysis"] - s1["usDialysis"],
        "ancillary": s2["ancillary"] - s1["ancillary"],
        "corporate": s2["corporate"] - s1["corporate"],
    }
    bridge["total"] = s2["total"] - s1["total"]
    bridge["ancillaryShare"] = bridge["ancillary"] / bridge["total"] * 100

    # Guidance arithmetic — the H2 implied by an unchanged full-year guide
    gp = F["guidance"]["prior"]
    h1_eps = fact(F, "results", "epsH1_26")
    q2_eps = fact(F, "results", "epsQ2")
    guide = {
        "epsLow": g["adjEpsLow"], "epsHigh": g["adjEpsHigh"],
        "unchanged": (g["adjEpsLow"] == gp["adjEpsLow"] and g["adjEpsHigh"] == gp["adjEpsHigh"]
                      and g["adjOpIncomeLow"] == gp["adjOpIncomeLow"]),
        "h1Eps": h1_eps,
        "h2Low": g["adjEpsLow"] - h1_eps, "h2High": g["adjEpsHigh"] - h1_eps,
        "q2Annualised": q2_eps * 2,
        "opH1": F["segments"]["h1_26"]["total"],
        "opH2Low": g["adjOpIncomeLow"] - F["segments"]["h1_26"]["total"],
        "opH2High": g["adjOpIncomeHigh"] - F["segments"]["h1_26"]["total"],
        "fcfLow": g["fcfLow"], "fcfHigh": g["fcfHigh"],
        "fcfH1": fact(F, "results", "fcfQ1") + fact(F, "results", "fcfQ2"),
    }
    guide["h2Mid"] = (guide["h2Low"] + guide["h2High"]) / 2
    guide["vsQ2Run"] = (guide["h2Mid"] / guide["q2Annualised"] - 1) * 100
    guide["fcfH2Low"] = guide["fcfLow"] - guide["fcfH1"]
    guide["fcfH2High"] = guide["fcfHigh"] - guide["fcfH1"]
    guide["fcfMultiple"] = ((guide["fcfH2Low"] + guide["fcfH2High"]) / 2) / guide["fcfH1"]

    return {"funded": funded, "payor": payor, "rates": rates, "bridge": bridge,
            "guide": guide, "netDebt": net_debt, "ev": ev,
            "evEbitOnGuide": ev / ((g["adjOpIncomeLow"] + g["adjOpIncomeHigh"]) / 2),
            "fcfYield": fact(F, "results", "fcfTTM") / snap["marketCap"] * 100,
            "naiveFcfGap": (sum((qs[i]["cfo"] or 0) - (qs[i]["capex"] or 0) for i in range(4, 8)) * 1000
                            - fact(F, "results", "fcfTTM")),
            "levMin": min(r["lev"] for r in qrows), "levMax": max(r["lev"] for r in qrows)}


def slides(snap, ep, fact, fund_quarters=None):
    F = ep["filings"]
    # The episode file's notes end with a hand-written "TARGET 30s." Slide
    # targets are set below and are the single source of truth, so strip the
    # duplicate rather than let two numbers disagree on the presenter's screen.
    N = {k: re.sub(r"\s*TARGET\s+\d+s\.?\s*$", "", v) for k, v in ep["notes"].items()}
    s, p, r, b, g = snap, snap["payor"], snap["rates"], snap["bridge"], snap["guide"]
    ops, ue, res, bs = F["operations"], F["unitEconomics"], F["results"], F["balanceSheet"]
    fv = lambda *k: fact(F, *k)                                          # noqa: E731

    MINUS = "−"                                   # true minus, not a hyphen

    # One magnitude rule for the whole deck: $1.8B, $730M, $208K — see decks/fmt.py.
    m = b_ = fmt.usd                        # inputs in millions, unit chosen for you
    d2 = dm = fmt.dollars
    pc = fmt.pct

    # Everything the prose used to state as a literal, derived once here.
    react = s["releases"][-1]                       # the earnings reaction session
    seg = F["segments"]
    _segRev = seg["revQ2_26"]["usDialysis"] + seg["revQ2_26"]["ancillary"]
    ancRevShare = seg["revQ2_26"]["ancillary"] / _segRev * 100
    dialysisRevShare = seg["revQ2_26"]["usDialysis"] / _segRev * 100
    epsJump = (fv("results", "epsQ2") / fv("results", "epsQ1") - 1) * 100
    _qs = {q["label"]: q["revenue"] for q in s["quarters"] if q.get("revenue") is not None}
    _cur, _yr = s["quarters"][-1], None
    for q in s["quarters"]:
        if q["label"][:2] == _cur["label"][:2] and q["label"] != _cur["label"]:
            _yr = q
    revGrowthQ2 = (_cur["revenue"] / _yr["revenue"] - 1) * 100 if _yr else None

    S = []

    # 01 ---------------------------------------------------------------
    S.append({
        "type": "title", "kicker": "Fundamental analysis · episode deck",
        "company": s["company"], "ticker": s["symbol"],
        "exchange": s["exchange"], "sector": s["sector"],
        "price": s["price"], "changePct": s["changePct"],
        "hook": (f"Up <em>{s['runUp']:.0f}%</em> since January. "
                 f"Then down <em>{abs(s['drawdown']):.0f}%</em> in three days &mdash; "
                 f"on its <em>strongest quarter in six</em>."),
        "chips": [{"form": lab.split(" ")[0], "when": lab.split("filed ")[-1]}
                  for lab in [v["label"] for v in ep["sources"].values()]][:7],
        "notes": N["title"], "target": 15,
    })

    # 02 ---------------------------------------------------------------
    S.append({
        "type": "chart", "kicker": "Where we are", "src": "Daily closes · Yahoo via Terminal",
        "head": "What actually happened",
        "sub": (f"{d2(s['low']['v'])} on {s['low']['when']} to {d2(s['high']['v'])} on "
                f"{s['high']['when']}. Two sessions later, {pc(s['worst']['pct'])} in a day."),
        "chart": {"kind": "line", "points": s["tape"], "height": 560, "markers": [
            {"i": s["low"]["i"], "lab": d2(s["low"]["v"]), "sub": s["low"]["when"], "side": "below"},
            {"i": s["high"]["i"], "lab": d2(s["high"]["v"]), "sub": s["high"]["when"]},
            {"i": s["worst"]["i"], "lab": f"{pc(s['worst']['pct'])} in one day",
             "sub": f"{s['worst']['when']} — day after Q2", "crit": True, "side": "below"},
        ]},
        "why": (f"{s['worst']['volume']/1e6:.1f} million shares traded that day, "
                f"{s['worst']['volX']:.0f}&times; the normal run rate. This was not a misread "
                "&mdash; something in the release genuinely changed the story."),
        "notes": N["tape"], "target": 18,
    })

    S.append({
        "type": "findings", "kicker": "Four things the headlines missed",
        "src": "All four from the filings, not the press release",
        "head": "What nobody else is going to show you",
        "items": ep["findings"],
        "why": ("Every one of these came out of a document DaVita filed with the SEC, not out of the "
                f"press release. Three of them are the reason this stock fell {abs(react['move']):.0f}% "
                "on a quarter that "
                "looked good. We will walk each one."),
        "notes": N["findings"], "target": 26,
    })

    # 03 ---------------------------------------------------------------
    S.append({
        "type": "tiles", "kicker": "First, what they actually do", "src": "8-K EX-99.1 · Aug 4 2026",
        "head": "Dialysis clinics. That's it.",
        "sub": ("Kidneys fail, you go three times a week, for life or until a transplant. "
                "The most non-discretionary revenue in healthcare."),
        "cols": 4,
        "tiles": [
            {"v": f"{fv('operations','centersTotal'):,}", "l": "Clinics worldwide",
             "n": f"{fv('operations','centersUS'):,} in the U.S., {fv('operations','centersIntl')} international"},
            {"v": f"{fv('operations','patients'):,}", "l": "Patients on treatment", "n": "at June 30, 2026"},
            {"v": f"{fv('operations','treatmentsPerDay'):,}", "l": "Treatments every day",
             "n": f"{fv('operations','treatmentsQ2'):,} in the quarter", "tone": "accent"},
            {"v": "#2", "l": "By size in U.S. dialysis",
             "n": f"{fv('other','largestCompetitor')} is the larger, per the 10-K"},
        ],
        "why": ("Recurring, government-backed, recession-proof demand is exactly what lets a "
                "company carry a lot of debt. Hold that thought &mdash; it comes back."),
        "notes": N["business"], "target": 16,
    })

    # 04 ---------------------------------------------------------------
    S.append({
        "type": "quote", "kicker": "Now the one thing you have to understand", "src": "10-K FY2025 · Item 1",
        "head": f"{fv('payorStructure','commercialPctOfPatients')}% of the patients are the whole company",
        "quote": fv("payorStructure", "quote"),
        "attr": "DaVita Inc., 2025 Form 10-K",
        "extra": (
            '<div class="tiles" style="grid-template-columns:repeat(3,1fr);margin-top:20px">'
            f'<div class="tile accent"><div class="tv num">{fv("payorStructure","commercialPctOfPatients")}%</div>'
            '<div class="tl">of U.S. dialysis patients</div><div class="tn">have commercial insurance</div></div>'
            f'<div class="tile accent"><div class="tv num">{fv("payorStructure","commercialPctOfRevenue")}%</div>'
            '<div class="tl">of dialysis revenue</div><div class="tn">comes from those patients</div></div>'
            '<div class="tile accent"><div class="tv num">~all</div>'
            '<div class="tl">of the profit</div><div class="tn">comes from those patients</div></div></div>'),
        "why": (f"You are not really analysing {fv('operations','patients'):,} patients. You are "
                "analysing the roughly one in nine with private insurance. Everything else "
                "close to washes."),
        "notes": N["payor"], "target": 26,
    })

    # 05 ---------------------------------------------------------------
    S.append({
        "type": "chart", "kicker": "Why one patient is worth ten",
        "src": "Derived from 10-K + 10-Q disclosure",
        "head": "Same treatment. Same cost. Ten times the profit.",
        "sub": (f"One dialysis session, split into what it costs to deliver and what is left over. "
                f"The cost block is identical. Only the payor changes."),
        "chart": {"kind": "stackedh", "height": 470, "labelRoom": 330, "rows": [
            {"name": "Commercial patient",
             "sub": f"~{fv('payorStructure','commercialPctOfPatients')}% of patients",
             "totalLab": f"{d2(r['com'])} collected",
             "segs": [{"v": r["cost"], "cls": "mut", "lab": d2(r["cost"]), "ink": "var(--ink)"},
                      {"v": r["comMargin"], "cls": "", "lab": f"{d2(r['comMargin'])} profit"}]},
            {"name": "Government patient",
             "sub": f"~{fv('payorStructure','govPctOfPatients')}% of patients",
             "totalLab": f"{d2(r['gov'])} collected",
             "segs": [{"v": r["cost"], "cls": "mut", "lab": d2(r["cost"]), "ink": "var(--ink)"},
                      {"v": r["govMargin"], "cls": "", "lab": f"{d2(r['govMargin'])} profit"}]},
        ]},
        "legend": [{"c": "var(--muted)", "t": f"cost to deliver — {d2(r['cost'])}, the same either way"},
                   {"c": "var(--accent)", "t": "what's left over"}],
        "why": (f"{d2(r['govMargin'])} left over from a government patient. {d2(r['comMargin'])} from a "
                f"commercial one &mdash; about {r['comMargin']/r['govMargin']:.0f}&times; as much. That is why "
                "a small shift in who is paying moves profit more than almost anything else. "
                "<b>Derived from their two disclosures, not a number DaVita prints.</b>"),
        "notes": N["twoprices"], "target": 26,
    })

    # 06 ---------------------------------------------------------------
    S.append({
        "type": "chart", "kicker": "And that group just shrank", "src": "10-Q · Note 2, page 7",
        "head": f"The {fv('payorStructure','commercialPctOfPatients')}% went backwards",
        # Plotted as the CHANGE, not the level. Side by side at full scale the
        # two commercial bars differ by 0.7% — about two pixels — so the one
        # thing this slide exists to show was invisible.
        "sub": ("Year-over-year change in U.S. dialysis revenue. The low-margin half grew. "
                "The half that carries the profit did not."),
        "chart": {"kind": "bars", "height": 545, "zeroLine": True, "series": [
            {"x": "Government", "x2": f"{b_(p['gov25'])} → {b_(p['gov26'])}",
             "v": p["govGrowth"], "lab": f"{pc(p['govGrowth'])}   +{m(p['govDollars'])}", "cls": "mut"},
            {"x": "Commercial", "x2": f"{b_(p['com25'])} → {b_(p['com26'])}",
             "v": p["comGrowth"], "lab": f"{pc(p['comGrowth'])}   {m(p['comDollars'])}", "cls": "bad"},
        ]},
        "why": (f"Commercial's share of the mix fell from {p['comShare25']:.1f}% to {p['comShare26']:.1f}% "
                f"&mdash; {abs(p['shareShiftBps']):.0f} basis points off the only line that carries profit. "
                "This is the most important number in the release and it sits in a footnote."),
        "notes": N["commercial"], "target": 26,
    })

    # 07 ---------------------------------------------------------------
    S.append({
        "type": "mega", "kicker": "So the price per treatment fell", "src": "8-K EX-99.1 · Aug 4 2026",
        "head": "Revenue per treatment fell",
        "value": f"&minus;{d2(ue['revPerTreatmentQ1']['v'] - ue['revPerTreatmentQ2']['v'])[1:]}",
        "tone": "bad",
        "caption": (f"{d2(ue['revPerTreatmentQ1']['v'])} in Q1 to {d2(ue['revPerTreatmentQ2']['v'])} in Q2. "
                    "The company's own explanation: the decline was "
                    "&ldquo;driven by changes in payor mix.&rdquo;"),
        "why": (f"For a company whose treatment volume grows "
                f"{fv('operations','normNonAcqGrowthQ2')}%, price per treatment "
                "<b>is</b> the growth. It just went the wrong way."),
        "notes": N["rpt"], "target": 12, "optional": True,
    })

    # 08 ---------------------------------------------------------------
    S.append({
        "type": "mega", "kicker": "And there is no volume to offset it", "src": "8-K EX-99.1 · Aug 4 2026",
        "head": "Normalized non-acquired treatment growth",
        "value": f"{fv('operations','normNonAcqGrowthQ2')}%", "tone": "bad",
        "caption": ("Their own metric &mdash; strips out acquisitions and calendar effects. "
                    "Not three percent. Zero point three. "
                    f"Q1 was {fv('operations','normNonAcqGrowthQ1')}%."),
        "why": ("This company does not grow by treating more people. It grows three ways: price, "
                "buying clinics, and buying its own stock. Remember that for the verdict."),
        "notes": N["volume"], "target": 12, "optional": True,
    })

    # 09 ---------------------------------------------------------------
    S.append({
        "type": "tiles", "kicker": "And yet the headline looked strong", "src": "8-K EX-99.1 · Aug 4 2026",
        "head": f"Revenue up. Margin up. Earnings up {epsJump:.0f}% in a quarter.",
        "cols": 4,
        "tiles": [
            {"v": b_(fv("results", "revenueQ2")), "l": "Q2 revenue",
             "n": f"{pc(revGrowthQ2)} year over year"},
            {"v": m(fv("results", "opIncomeQ2")), "l": "Operating income",
             "n": f"{fv('results','opMarginQ2')}% margin, highest since Q4'24", "tone": "good"},
            {"v": d2(fv("results", "epsQ2")), "l": "Diluted EPS",
             "n": f"vs {d2(fv('results','epsQ1'))} last quarter", "tone": "good"},
            {"v": m(fv("results", "cfoQ2")), "l": "Operating cash flow",
             "n": f"vs {m(fv('results','cfoQ2prior'))} a year ago", "tone": "good"},
        ],
        "why": (f"Read the headline and you would expect this stock <b>up</b>. It fell "
                f"{abs(react['move']):.0f}%. Here is what the headline hides."),
        "optional": True,
        "notes": N["headline"], "target": 13,
    })

    # 10 ---------------------------------------------------------------
    S.append({
        "type": "chart", "kicker": "Because the jump came from here", "src": "10-Q · Note 12, segments",
        "head": f"{b['ancillaryShare']:.0f}% of it came from {ancRevShare:.0f}% of the company",
        "sub": f"Operating income bridge, Q1 2026 to Q2 2026 ($ millions).",
        "chart": {"kind": "bridge", "height": 545, "steps": [
            {"type": "start", "v": b["start"], "lab": m(b["start"]), "x": "Q1 2026", "x2": "operating income"},
            {"type": "step", "v": b["dialysis"], "lab": f"+{b['dialysis']:.0f}", "x": "U.S. dialysis",
             "x2": f"{dialysisRevShare:.0f}% of revenue", "cls": "mut"},
            {"type": "step", "v": b["ancillary"], "lab": f"+{b['ancillary']:.0f}", "x": "Ancillary",
             "x2": f"{b['ancillaryShare']:.0f}% of the jump", "cls": ""},
            {"type": "step", "v": b["corporate"], "lab": f"+{b['corporate']:.0f}", "x": "Corporate",
             "x2": "cost swing", "cls": "cool"},
            {"type": "total", "v": b["end"], "lab": m(b["end"]), "x": "Q2 2026", "x2": "operating income"},
        ]},
        "why": (f"The ancillary segment went from {m(F['segments']['q1_26']['ancillary'])} to "
                f"{m(F['segments']['q2_26']['ancillary'])} in one quarter. The core dialysis business "
                f"&mdash; the thing everyone thinks they are buying &mdash; contributed {m(b['dialysis'])} of the {m(b['total'])}."),
        "notes": N["bridge"], "target": 26,
    })

    # 11 ---------------------------------------------------------------
    eq = F["earningsQuality"]
    S.append({
        "type": "tiles", "kicker": "And that is the softest profit there is",
        "src": "10-Q · Note 2, revenue recognition",
        "head": "Integrated kidney care gets paid late, and lumpy",
        "sub": ("Value-based contracts: DaVita books the revenue when the health plan finally settles, "
                "sometimes years after the work."),
        "cols": 3,
        "tiles": [
            {"v": m(eq["ikcPriorYearRevH1_26"]["v"] / 1000), "l": "H1 2026 revenue booked for<br>work done in <b>previous years</b>",
             "n": "their disclosure, not my inference", "tone": "warn"},
            {"v": (f'{m(eq["contractAssetsDec25"]["v"]/1000)} <span style="color:var(--muted)">&rarr;</span> '
                   f'{m(eq["contractAssetsJun26"]["v"]/1000)}'),
             "l": "Contract assets &mdash; revenue earned,<br>not yet billed", "small": True,
             "n": f"+{m((eq['contractAssetsJun26']['v']-eq['contractAssetsDec25']['v'])/1000)} in six months", "tone": "warn"},
            {"v": m(F["segments"]["q2_26"]["ancillary"]), "l": "The segment's Q2 operating income",
             "n": f"on {m(F['segments']['revQ2_26']['ancillary'])} of revenue", "tone": "warn"},
        ],
        "why": ("A segment that is recognising old work and building unbilled receivables carried "
                "the quarter. That is an accounting timing win, not an operating one &mdash; which is "
                "why the cash never shows up the way the profit does."),
        "notes": N["quality"], "target": 24, "optional": True,
    })

    # 12 ---------------------------------------------------------------
    S.append({
        "type": "chart", "kicker": "Management said the quiet part", "src": "Aug 4 vs May 5 8-K",
        "head": "Guidance did not move one character",
        "sub": (f"Full-year adjusted EPS guidance: {d2(g['epsLow'])}&ndash;{d2(g['epsHigh'])}. "
                f"Identical to the guide issued on May 5."),
        "chart": {"kind": "range", "height": 400,
                  "scaleLo": 6.5, "scaleHi": 9.0,
                  "bandLo": g["h2Low"], "bandHi": g["h2High"],
                  "bandLoLab": d2(g["h2Low"]), "bandHiLab": d2(g["h2High"]),
                  "bandName": "implied second half EPS",
                  "marks": [{"v": g["q2Annualised"], "lab": d2(g["q2Annualised"]),
                             "sub": "Q2 annualised", "crit": True}]},
        "why": (f"First half was {d2(g['h1Eps'])}, so the guide leaves {d2(g['h2Low'])}&ndash;{d2(g['h2High'])} "
                f"for the second half. Q2 alone annualises to {d2(g['q2Annualised'])} &mdash; at the top of "
                f"that range. And that is <b>with</b> the share count still shrinking. The midpoint implies "
                f"earnings power {abs(g['vsQ2Run']):.0f}% <b>below</b> the Q2 run rate."),
        "notes": N["guidance"], "target": 30,
    })

    # 13 ---------------------------------------------------------------
    es, rel = s["earningsStats"], s["releases"]
    S.append({
        "type": "chart", "kicker": "Eight quarters say the same thing", "src": "8-K guidance tables + daily closes",
        "head": "This stock trades on one number, and it isn't earnings",
        "sub": ("Next-session move after each earnings release, labelled with what management did "
                "to full-year EPS guidance that day."),
        "chart": {"kind": "bars", "height": 520, "zeroLine": True, "series": [
            {"x": r["q"], "x2": r["action"], "v": r["move"], "lab": pc(r["move"]),
             "cls": "good" if r["kind"] == "up" else "mut" if r["kind"] == "new" else "bad"}
            for r in rel
        ]},
        "legend": [{"c": "var(--good)", "t": "guidance midpoint raised"},
                   {"c": "var(--crit)", "t": "unchanged or narrowed"},
                   {"c": "var(--muted)", "t": "first guide for a new year — not comparable"}],
        "why": (f"Of the {es['revisions']} times management revised guidance <b>within</b> a year, the stock "
                f"rose exactly once &mdash; the one time the midpoint went up "
                f"({pc(es['bestRaise'])}). The other {es['held']} it fell every single time. "
                "On August 4 the midpoint did not move."),
        "notes": N["history"], "target": 30,
    })

    # 14 ---------------------------------------------------------------
    S.append({
        "type": "tiles", "kicker": "Cash agrees", "src": "Q1 + Q2 2026 8-K EX-99.1",
        "head": "Trailing free cash flow looks great. First-half free cash flow does not.",
        "cols": 4,
        "tiles": [
            {"v": m(fv("results", "fcfTTM")), "l": "Trailing 12-month FCF",
             "n": f"up from {m(fv('results','fcfTTMprior'))}", "tone": "good"},
            {"v": m(g["fcfH1"]), "l": "But H1 2026 FCF was only",
             "n": f"{m(fv('results','fcfQ1'))} in Q1 + {m(fv('results','fcfQ2'))} in Q2", "tone": "bad"},
            {"v": f"{m(g['fcfLow'])}&ndash;{m(g['fcfHigh'])}", "l": "Full-year FCF guidance",
             "small": True, "n": "unchanged since May"},
            {"v": f"{g['fcfMultiple']:.1f}&times;", "l": "What H2 must do vs H1",
             "n": f"needs {m(g['fcfH2Low'])}&ndash;{m(g['fcfH2High'])}", "tone": "warn"},
        ],
        "why": (f"Company-defined free cash flow, quoted from the release &mdash; not operating cash "
                f"flow minus capex, which flatters DaVita by about {m(s['naiveFcfGap'])}. Every dollar of "
                "that second half is already committed to buybacks and interest."),
        "notes": N["cash"], "target": 18, "optional": True,
    })

    # 15 ---------------------------------------------------------------
    S.append({
        "type": "chart", "kicker": "So where did the earnings growth come from?", "src": "SEC filings · quarterly share counts",
        "head": (f"Revenue grew {s['ttmRevGrowth']:.0f}%. Earnings per share grew "
                 f"{s['indexed']['earnGain']:.0f}%. Here is the difference."),
        "sub": (f"Diluted weighted-average shares, {s['sharesLabelThen']} to {s['sharesLabelNow']} "
                f"(millions). Q4s are absent — share counts are not filed for them."),
        "chart": {"kind": "bars", "height": 545, "series": [
            {"x": q["label"], "v": q["shares"], "lab": f"{q['shares']:.1f}",
             "cls": "" if i == len(s["quarters"]) - 1 else "mut"}
            for i, q in enumerate(s["quarters"]) if q["shares"]
        ]},
        "why": (f"{s['sharesThen']:.1f}M to {s['sharesNowWA']:.1f}M &mdash; they have retired "
                f"<b>{abs(s['shareReductionWA']):.0f}% of the company</b> in two years, "
                f"{m(fv('buybacks','h1_2026Amount'))} of it in the first half alone "
                f"({s['sharesNow']:.1f}M actually outstanding at June 30). "
                "Fewer slices, so each slice is bigger. That is the whole EPS story."),
        "notes": N["engine"], "target": 22,
    })

    # 16 ---------------------------------------------------------------
    S.append({
        "type": "chart", "kicker": "It was paid for with debt",
        "src": "Reported total debt + SEC equity, 8 quarters",
        "head": "Debt went up. Shareholders' equity went below zero.",
        "sub": ("Eight quarters, each panel on its own scale. Buying back stock faster than you "
                "earn it does exactly this."),
        "chart": {"kind": "smallmult", "height": 540, "panels": [
            {"label": "Borrowed money — total debt",
             "fmtKind": "usdB", "series": [
                {"x": f["q"], "v": f["debt"], "cls": "s1",
                 "lab": b_(f["debt"]) if i in (0, len(s["funded"]) - 1) else "",
                 "x2": f"{f['lev']:.2f}×", "x2crit": f["lev"] >= 3.34}
                for i, f in enumerate(s["funded"])]},
            {"label": "Shareholders' money — equity",
             "fmtKind": "usdM", "series": [
                {"x": f["q"], "v": f["equity"], "cls": "s2" if f["equity"] >= 0 else "bad",
                 "lab": m(f["equity"]) if i in (0, len(s["funded"]) - 1) else ""}
                for i, f in enumerate(s["funded"])]},
        ]},
        "legend": [{"c": "var(--s1)", "t": "debt"},
                   {"c": "var(--s2)", "t": "equity, positive"},
                   {"c": "var(--crit)", "t": "equity deficit"}],
        "why": (f"Debt {b_(s['funded'][0]['debt'])} to {b_(s['funded'][-1]['debt'])}. Equity "
                f"{m(s['funded'][0]['equity'])} to {m(s['funded'][-1]['equity'])} &mdash; it crossed below "
                f"zero in {next(f['q'] for f in s['funded'] if f['equity'] < 0)} and has not been back. "
                f"Leverage has sat between {s['levMin']:.2f}× and {s['levMax']:.2f}× throughout; the figure "
                "under each quarter is that quarter's ratio."),
        "notes": N["engine"], "target": 24,
    })

    # 17 ---------------------------------------------------------------
    hist_bb = F["buybacks"]["history"]
    S.append({
        "type": "chart", "kicker": "And look at what they paid",
        "src": "10-K FY2025 + quarterly 8-Ks",
        "head": "They bought their own stock all the way up",
        "sub": ("Average price paid per share repurchased. The dashed line is where the stock "
                "trades now."),
        "chart": {"kind": "line", "height": 470,
                  "points": [{"t": i, "v": h["avgPrice"]} for i, h in enumerate(hist_bb)],
                  "ref": {"v": s["price"], "lab": f"now {d2(s['price'])}"},
                  "ticks": [{"i": i, "lab": h["period"].replace(" 26", " '26")}
                            for i, h in enumerate(hist_bb)],
                  "markers": [{"i": len(hist_bb) - 1, "lab": d2(hist_bb[-1]["avgPrice"]),
                               "sub": "settling Berkshire, Jul 31", "crit": True}]},
        "why": (f"{d2(hist_bb[0]['avgPrice'])} in 2024, {d2(hist_bb[3]['avgPrice'])} in Q1, then "
                f"{d2(hist_bb[-1]['avgPrice'])} between July 1 and August 4 &mdash; that last one was "
                f"settling the Berkshire Hathaway obligation on July 31. Three trading days later the "
                f"stock was {d2(s['price'])}. A buyback only creates value below intrinsic value."),
        "notes": N["buyprice"], "target": 18, "optional": True,
    })

    # 18 ---------------------------------------------------------------
    reg = F["regulatory"]
    S.append({
        "type": "chart", "kicker": "Now the 2027 problem", "src": "10-Q · CMS proposed rule, June 2026",
        "head": "Medicare's raise is getting cut in half",
        "sub": (f"Medicare and Medicare Advantage are {fv('payorStructure','medicarePctOfRevenue')}% of "
                "U.S. dialysis revenue. CMS sets that rate."),
        "chart": {"kind": "bars", "height": 545, "series": [
            {"x": "CY2026", "x2": "final rule", "v": reg["cms2026Final"]["v"],
             "lab": f"+{reg['cms2026Final']['v']}%", "cls": "mut"},
            {"x": "CY2027", "x2": "proposed rule", "v": reg["cms2027Proposed"]["v"],
             "lab": f"+{reg['cms2027Proposed']['v']}%", "cls": "bad"},
            {"x": "Their cost per treatment", "x2": "H1'26 vs H1'25, actual",
             "v": reg["costInflationH1"]["v"], "lab": f"+{reg['costInflationH1']['v']}%", "cls": ""},
        ]},
        "why": (f"Prices on {fv('payorStructure','medicarePctOfRevenue')}% of the business rise "
                f"{reg['cms2027Proposed']['v']}% while costs rise {reg['costInflationH1']['v']}%. "
                "That is negative jaws from January, and it is why &lsquo;12&times; earnings is cheap&rsquo; "
                "needs an asterisk."),
        "notes": N["medicare"], "target": 20,
    })

    # 19 ---------------------------------------------------------------
    ix = s["indexed"]
    S.append({
        "type": "chart", "kicker": "Did the earnings justify the run?",
        "src": "Reported quarterly EPS + daily closes",
        "head": "The price ran further than the earnings did",
        "sub": (f"Both start at 100 on {ix['baseDate']}. Trailing earnings step on the day each quarter "
                "was reported — so you see what the market knew when it knew it."),
        "chart": {"kind": "indexed", "height": 470,
                  "price": ix["price"], "earn": ix["earn"],
                  "priceLabel": f"price {pc(ix['priceGain'], 0)}",
                  "earnLabel": f"earnings {pc(ix['earnGain'], 0)}",
                  "ticks": [{"t": e["t"], "lab": e["q"]} for e in ix["earn"]]},
        "legend": [{"c": "var(--s1)", "t": "share price, indexed to 100"},
                   {"c": "var(--s2)", "t": "trailing 12-month EPS — steps on the report date"}],
        "why": (f"Trailing earnings went from {d2(ix['baseEps'])} to {d2(ix['endEps'])}, "
                f"{pc(ix['earnGain'], 0)}. The share price went {pc(ix['priceGain'], 0)} &mdash; and that "
                "is <b>after</b> the crash. The difference is the market agreeing to pay a higher "
                "multiple, which is the part that hands itself back when guidance disappoints."),
        "notes": N["indexed"], "target": 26,
    })

    # 20 ---------------------------------------------------------------
    st = s["street"]
    fwd_tiles = [{"v": f"{f['pe']:.1f}&times;", "l": f"{f['period'].split()[-1]} expected earnings",
                  "n": (f"{d2(f['eps'])} consensus EPS"
                        + (f" &mdash; only {f['analysts']} analyst{'s' if f['analysts'] != 1 else ''}"
                           if f.get("analysts") and f["analysts"] <= 2 else "")),
                  "tone": "accent" if i == 0 else ""}
                 for i, f in enumerate(s["fwd"][:3])]
    S.append({
        "type": "tiles", "kicker": "So what is it worth?", "src": "Consensus estimates + filings",
        "head": "Cheap on the equity. Only cheap-ish on the whole thing.",
        "cols": 5,
        "tiles": fwd_tiles + [
            {"v": f"{s['fcfYield']:.1f}%", "l": "Trailing FCF yield", "n": "on market cap", "tone": "good"},
            {"v": b_(s["ev"]), "l": "Enterprise value", "small": True,
             "n": f"{b_(s['marketCap'])} equity + {b_(s['netDebt'])} net debt", "tone": "warn"},
        ],
        "why": (f"Beginners see an {b_(s['marketCap'])} market cap and call it cheap. You are actually buying a "
                f"{b_(s['ev'])} enterprise, which is about {s['evEbitOnGuide']:.1f}&times; the operating profit "
                f"they guided to. The Street has a {d2(st['target'])} target "
                f"({pc(st['upside'], 0)}) and still rates it <b>{st['rec']}</b> &mdash; they agree it screens "
                "cheap and they do not trust it either."),
        "notes": N["valuation"], "target": 22,
    })

    # 21 ---------------------------------------------------------------
    S.append({
        "type": "chart", "kicker": "And the Street half-agrees", "src": "Nasdaq analyst consensus",
        "head": f"{pc(st['upside'], 0)} to the mean target — and still rated {st['rec']}",
        "sub": (f"{st['analysts']} analysts: {st['strongBuy']} strong buy, {st['buy']} buy, "
                f"{st['hold']} hold, {st['sell']} sell."),
        "chart": {"kind": "track", "height": 250,
                  "lo": st["targetLow"], "hi": st["targetHigh"],
                  "loLab": f"low {dm(st['targetLow'])}", "hiLab": f"high {dm(st['targetHigh'])}",
                  "now": s["price"], "nowLab": d2(s["price"]),
                  "mean": st["target"], "meanLab": dm(st["target"])},
        "why": (f"A {pc(st['upside'], 0)} gap to the average target, from a panel that rates it "
                f"<b>{st['rec']}</b>. That is the whole DaVita argument in one line: everybody agrees "
                "the number is low, and nobody wants to be the one holding the leverage."),
        "notes": N["street"], "target": 16, "optional": True,
    })

    # 22 ---------------------------------------------------------------
    _sc = [v["score"] for v in ep["verdict"]["scored"]]
    _strong = sum(1 for x in _sc if x >= 4)
    _mid = sum(1 for x in _sc if 2 <= x <= 3)
    _weak = sum(1 for x in _sc if x <= 1)
    S.append({
        "type": "snapshot", "kicker": "The verdict", "src": "My call · not financial advice",
        "head": "Six dimensions, scored from the filings",
        "rows": [{"name": v["dim"], "score": v["score"], "fact": v["fact"], "tone": v["tone"]}
                 for v in ep["verdict"]["scored"]],
        "why": (f"{_strong} of six score four or better. {_mid} are middling and {_weak} is a red flag "
                "&mdash; and it is the one that decides whether the others matter."),
        "notes": N["verdict"], "target": 24,
    })

    # 23 ---------------------------------------------------------------
    S.append({
        "type": "twocol", "kicker": "The two lists", "src": "Every line traces to a filing",
        "head": "What's working, and what to watch",
        "leftHead": "What's working", "rightHead": "What to watch",
        "left": ep["verdict"]["working"], "right": ep["verdict"]["watch"],
        "notes": N["twolists"], "target": 22,
    })

    # 24 ---------------------------------------------------------------
    S.append({
        "type": "verdict", "kicker": "So what am I doing?", "src": "My call · not financial advice",
        "head": f"My call: {ep['verdict']['call']}",
        "call": ep["verdict"]["call"], "callLine": ep["verdict"]["callLine"],
        "reasons": ep["verdict"]["why"],
        "why": ("Fundamentals tell you <b>what</b> to own. They never tell you <b>when</b>. "
                "Let's go to the chart."),
        "notes": N["handoff"], "target": 30,
    })

    return S


