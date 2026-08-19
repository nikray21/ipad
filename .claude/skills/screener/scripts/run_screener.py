#!/usr/bin/env python3
"""/screener staged run. Five independent scans over the same single data pull:
  1-3. TREND hits  (long / short / fade)  -- the graded buckets
  4.   BREAK scan  (breakout=long bias, breakdown=short bias) -- flag only
  5.   SQUEEZE scan (range contraction into a flat level)     -- flag only

Buckets 4-5 run across the WHOLE universe, not only trend hits: a name can be
forming a break or a squeeze without being in the 2-5% entry band. Trend
context is recorded on every flag so it's never read as a graded pass.
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from full_check import analyze

syms = json.load(open(sys.argv[1]))
outfile = sys.argv[2]
print(f"Universe: {len(syms)}", file=sys.stderr)

trend_hits, breaks, squeezes, dropped = [], [], [], []

for idx, s in enumerate(syms):
    try:
        r = analyze(s)
    except Exception as e:
        dropped.append({"symbol": s, "error": str(e)}); continue
    if r.get("error"):
        dropped.append(r); continue
    if not r.get("verified"):
        dropped.append({**r, "error": "failed price verification"}); continue

    trend_ctx = ("uptrend" if r["longTemplate"] else
                 "downtrend" if r["shortTemplate"] else "no trend")

    # 1-3: graded trend buckets
    if r.get("signal"):
        trend_hits.append(r)

    # 4: break scan -- whole universe, flag only
    if r.get("breakSetup"):
        breaks.append({"symbol": s, "price": r["realPrice"], "trend": trend_ctx,
                       "atr14": r["atr14"], "levels": r["levels"], **r["breakSetup"]})

    # 5: squeeze scan -- whole universe, flag only
    if r.get("squeeze"):
        squeezes.append({"symbol": s, "price": r["realPrice"], "trend": trend_ctx,
                         "atr14": r["atr14"], **r["squeeze"]})

    flags = []
    if r.get("breakSetup"): flags.append(r["breakSetup"]["dir"])
    if r.get("squeeze"): flags.append("squeeze")
    print(f"  {idx+1}/{len(syms)} {s} {r.get('signal') or '-'}"
          f"{' [' + ','.join(flags) + ']' if flags else ''}", file=sys.stderr)

json.dump({"trendHits": trend_hits, "breaks": breaks, "squeezes": squeezes,
           "dropped": dropped}, open(outfile, "w"), indent=2)
print(f"DONE trend={len(trend_hits)} breaks={len(breaks)} squeezes={len(squeezes)} "
      f"dropped={len(dropped)}", file=sys.stderr)
