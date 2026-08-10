#!/usr/bin/env python3
"""
validate_facts.py — check every numeric fact in an episode file actually
appears in the SEC document it claims to come from.

    python3 scripts/validate_facts.py DVA
    python3 scripts/validate_facts.py DVA --prove

audit_deck.py proves the deck's arithmetic is internally consistent. That is a
different question from whether the inputs are real. This script closes that
gap: it downloads each cited filing, strips it to text, and searches for every
number the episode file attributes to it.

A fact that cannot be found is not automatically wrong — a filing may render
$1,308 as "1,308" inside a table the extractor mangles — but it must be looked
at by a human, so it is reported as UNVERIFIED rather than passed.
"""

import json
import html
import os
import re
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, ".cache_filings")
UA = {"User-Agent": "nikil.rayani@puriscorp.com research"}

FOUND, MISSING, SKIPPED = [], [], []
PROVE_TARGET = []


def doc_text(url):
    """Fetch (and cache) a filing, flattened to searchable text."""
    os.makedirs(CACHE, exist_ok=True)
    key = re.sub(r"[^A-Za-z0-9]+", "_", url)[-120:] + ".txt"
    path = os.path.join(CACHE, key)
    if os.path.exists(path):
        return open(path, encoding="utf-8").read()

    raw = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=90).read()
    t = raw.decode("utf-8", "ignore")
    # A directory URL is a filing index — pull in every exhibit it lists so
    # figures cited to "the 8-K" are searched across its EX-99.1 too.
    if url.endswith("/"):
        parts = [t]
        for href in dict.fromkeys(re.findall(r'href="([^"]+\.htm)"', t, re.I)):
            if "/Archives/" not in href:
                continue
            full = "https://www.sec.gov" + href if href.startswith("/") else url + href
            try:
                parts.append(urllib.request.urlopen(
                    urllib.request.Request(full, headers=UA), timeout=90).read().decode("utf-8", "ignore"))
                time.sleep(0.25)
            except Exception:                                        # noqa: BLE001
                pass
        t = "\n".join(parts)

    t = re.sub(r"(?is)<(script|style).*?</\1>", " ", t)
    t = re.sub(r"(?s)<[^>]+>", " ", t)
    t = html.unescape(t)
    t = re.sub(r"[ \t\xa0  ]+", " ", t)
    open(path, "w", encoding="utf-8").write(t)
    time.sleep(0.25)
    return t


def forms(v, unit=None):
    """
    Every plausible way a filing might print this number.

    Two cases bit us and are handled explicitly:
      * a percentage like 11 is too short to search as a bare integer, but
        "11%" is specific enough — so percent-united facts get a % form;
      * we store dollars in millions while the statements report thousands,
        so -765.096 has to be searched for as "765,096" as well.
    """
    out = set()
    strong = set()                       # forms specific enough to skip the length filter

    if unit == "%":
        strong |= {f"{v:g}%", f"{v:g} %"}
    if isinstance(v, int) or (isinstance(v, float) and v == int(v)):
        n = abs(int(v))
        out |= {f"{n:,}", str(n)}
        strong |= {f"${n:,} million", f"${n:,}  million", f"$ {n:,} million"}
        if n >= 1000 and n % 1000 == 0:
            k = n // 1000
            out |= {f"{k:,}", str(k)}
            # "2,000" thousands is written "2.0 million" in the prose
            strong |= {f"{k:,}.0 million", f"{k:,} million", f"${k:,} million"}
        # millions -> the thousands a financial statement is printed in
        strong.add(f"{n * 1000:,}")
    if isinstance(v, float):
        a = abs(v)
        for d in (1, 2, 3):
            out.add(f"{a:,.{d}f}")
            out.add(f"{a:.{d}f}")
        if a >= 1000:
            out.add(f"{a / 1000:,.3f}")
            out.add(f"{a / 1000:,.2f}")
        # millions -> the thousands the financial statements are printed in
        th = a * 1000
        if abs(th - round(th)) < 0.5:
            strong.add(f"{round(th):,}")

    return strong | {s for s in out if len(s) >= 3 or (isinstance(v, float) and "." in s)}


def present(needle, haystack):
    """
    True only if `needle` appears as a whole figure — not inside a larger one.
    Plain `in` let a fabricated 611 pass by matching inside "2,611,500", so
    --prove reported a false clean bill of health.
    """
    return re.search(r"(?<![\d,.])" + re.escape(needle) + r"(?![\d,]*\d)", haystack) is not None


def check(node, path, ep, cache, parent=None):
    if isinstance(node, dict):
        if node.get("_derived"):
            # Derived either way: an aggregate no document prints, or a total whose
            # components ARE printed and validated individually. Both are verified
            # by recomputation elsewhere, not by searching for the total.
            SKIPPED.append((".".join(path), "derived — recomputed from validated components"))
            return
        if "v" in node and not isinstance(node["v"], (dict, list)):
            v, src = node["v"], node.get("src")
            label = ".".join(path)
            if not src or src not in ep["sources"]:
                MISSING.append((label, v, "no valid src"))
                return
            if isinstance(v, str):
                SKIPPED.append((label, "prose quote — verified by eye"))
                return
            unit = node.get("unit")
            if node.get("searchAs"):
                url = ep["sources"][src]["url"]
                if url not in cache:
                    cache[url] = doc_text(url)
                hit = node["searchAs"] in cache[url]   # explicit phrase, boundaries implied
                (FOUND if hit else MISSING).append(
                    (label, v, f"searchAs matched in {src}" if hit
                     else f"searchAs {node['searchAs']!r} NOT FOUND in {src}"))
                return
            if isinstance(v, bool) or (isinstance(v, (int, float)) and abs(v) < 3 and unit != "%"):
                # 0.3, 1.1, 2.2 etc. are too short to search for meaningfully
                SKIPPED.append((label, f"{v} too small to search uniquely"))
                return
            url = ep["sources"][src]["url"]
            if url not in cache:
                cache[url] = doc_text(url)
            text = cache[url]
            hit = next((f for f in forms(v, unit) if present(f, text)), None)
            (FOUND if hit else MISSING).append(
                (label, v, f"'{hit}' in {src}" if hit else f"NOT FOUND in {src}"))
            return
        # Row-style facts: one `src` covering several numeric columns
        # (quarterly.rows[n] = {q, eps, debt, netDebt, lev, src}). Without this
        # branch a whole table of figures slipped past unvalidated.
        if node.get("_derived"):
            # Aggregates computed across many filings. No document prints them, so
            # they are verified by recomputation in audit_deck.py, not by search.
            SKIPPED.append((".".join(path), "derived aggregate — recomputed by audit_deck.py"))
            return
        if "src" in node and "v" not in node:
            src = node["src"]
            if src not in ep["sources"]:
                MISSING.append((".".join(path), src, "unknown src"))
                return
            url = ep["sources"][src]["url"]
            if url not in cache:
                cache[url] = doc_text(url)
            text = cache[url]
            # A row may declare explicit phrases per column, for figures a bare
            # number can never pin down ("0.2 million shares").
            sa = node.get("searchAs") or {}
            if isinstance(sa, str):
                sa = {}
            pct_cols = set(node.get("_pct") or [])
            if not pct_cols:                          # inherited from the row table
                for anc in (parent or {},):
                    pct_cols = set(anc.get("_pct") or [])
            for k, val in node.items():
                if (k.startswith("_") or k in ("src", "note", "unit", "searchAs")
                        or not isinstance(val, (int, float))):
                    continue
                if isinstance(val, bool):
                    continue
                lbl = ".".join(path + [k])
                if k in sa:
                    hit = sa[k] if sa[k] in text else None
                else:
                    hit = next((f for f in forms(val, "%" if k in pct_cols else None)
                                if present(f, text)), None)
                (FOUND if hit else MISSING).append(
                    (lbl, val, f"'{hit}' in {src}" if hit else f"NOT FOUND in {src}"))
            return
        for k, val in node.items():
            if not k.startswith("_") and k not in ("src", "note", "unit"):
                check(val, path + [k], ep, cache, node)
    elif isinstance(node, list):
        for i, val in enumerate(node):
            check(val, path + [str(i)], ep, cache, parent)


def main():
    sym = (sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("-") else "DVA").upper()
    prove = "--prove" in sys.argv
    ep = json.load(open(os.path.join(HERE, "episodes", f"{sym}.json")))

    if prove:
        # Corrupt the first searchable numeric fact under `results`, whatever this
        # episode happens to call it. The old hook named a DVA-only key and blew
        # up on any company that does not have one.
        target = None
        for k, v in ep["filings"]["results"].items():
            if isinstance(v, dict) and isinstance(v.get("v"), (int, float)) and not v.get("_derived"):
                target = k
                break
        if target is None:
            print("--prove: this episode has no numeric fact under `results` to corrupt")
            sys.exit(1)
        ep["filings"]["results"][target]["v"] = 611998877          # a figure nobody reported
        ep["filings"]["results"][target].pop("searchAs", None)
        PROVE_TARGET.append(f"results.{target}")
        print(f"--prove: results.{target} set to a fabricated 611998877\n")

    cache = {}
    check(ep["filings"], [], ep, cache)

    for label, why in SKIPPED:
        print(f"  skip   {label:<48} {why}")
    for label, v, why in FOUND:
        print(f"  found  {label:<48} {v!r:>14}  {why}")
    for label, v, why in MISSING:
        print(f"  CHECK  {label:<48} {v!r:>14}  {why}")

    print(f"\n{len(FOUND)} verified against the filing text · "
          f"{len(SKIPPED)} skipped · {len(MISSING)} need eyes")

    if prove:
        if any(l == PROVE_TARGET[0] for l, _, _ in MISSING):
            print("✓ --prove worked: the fabricated figure was caught")
            sys.exit(0)
        print("✗ --prove FAILED: a fabricated figure passed")
        sys.exit(1)

    if MISSING:
        print("\nEvery CHECK line must be resolved before this deck is recorded.")
        sys.exit(1)
    print("ALL EPISODE FACTS TRACE TO THEIR FILING")


if __name__ == "__main__":
    main()
