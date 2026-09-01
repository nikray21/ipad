#!/usr/bin/env python3
"""
export_notes.py — write simple TALKING POINTS into a Notes/ folder inside the
episode's output directory: short bullets per slide that can be read at a
glance and spoken from, not paragraphs.

    python3 export_notes.py NBIS

Reads the built deck's frozen data (data/<SYM>-<DATE>.json), so every figure in
the bullets is exactly what the deck displays — rerun after any rebuild.
Writes one .txt per slide plus a combined 00 TALKING-POINTS.txt.
"""

import json
import os
import re
import sys

import deckpath

STRIP = [("&mdash;", "—"), ("&minus;", "−"), ("&times;", "×"), ("&ndash;", "–"),
         ("&rarr;", "→"), ("&lsquo;", "'"), ("&rsquo;", "'"), ("&ldquo;", "“"),
         ("&rdquo;", "”"), ("&amp;", "&"), ("&nbsp;", " "), ("&ensp;", " ")]


def clean(v):
    s = re.sub(r"<[^>]+>", "", str(v or ""))
    for a, b in STRIP:
        s = s.replace(a, b)
    return re.sub(r"\s+", " ", s).strip()


def bullets(text):
    """Split spoken prose into one-sentence bullets. Decimal points are safe:
    a sentence boundary is a period/!/? followed by a space and a capital,
    quote or dollar sign."""
    text = re.sub(r"\s*TARGET\s+\d+s\.?\s*$", "", text).strip()
    parts = re.split(r"(?<=[.!?…])\s+(?=[A-Z“\"'$])", text)
    return [p.strip() for p in parts if p.strip()]


def main():
    sym = (sys.argv[1] if len(sys.argv) > 1 else "NBIS").upper()
    ep = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                     "episodes", f"{sym}.json")))
    outdir = deckpath.read_dir(sym, ep["episodeDate"],
                               die=lambda m: sys.exit("export_notes: " + m))
    blob = json.load(open(os.path.join(outdir, "data", f"{sym}-{ep['episodeDate']}.json")))
    slides = blob["payload"]["slides"]

    notes_dir = os.path.join(outdir, "Notes")
    os.makedirs(notes_dir, exist_ok=True)
    for f in os.listdir(notes_dir):
        if f.endswith(".txt"):
            os.remove(os.path.join(notes_dir, f))

    combined = [f"{blob['payload']['company']} ({sym}) — TALKING POINTS",
                f"{len(slides)} slides · short bullets per slide · read, glance, talk",
                "=" * 72, ""]

    for i, sl in enumerate(slides, 1):
        head = clean(sl.get("head") or sl.get("company") or "")
        block = [f"SLIDE {i:02d} — {head}   ({sl.get('target', '?')}s)"
                 + ("   [CAN CUT]" if sl.get("optional") else "")]
        if sl.get("punch"):
            block.append(f"ON SCREEN: {clean(sl['punch'])}")
        block.append("")
        for b in bullets(clean(sl.get("notes", ""))):
            block.append(f"• {b}")
        block.append("")

        safe = re.sub(r"[^A-Za-z0-9 .,%$×'+-]", "", head)[:56].strip() or f"slide {i}"
        open(os.path.join(notes_dir, f"{i:02d} {safe}.txt"), "w").write(
            "\n".join(block) + "\n")
        combined += block + ["-" * 72, ""]

    open(os.path.join(notes_dir, "00 TALKING-POINTS.txt"), "w").write(
        "\n".join(combined) + "\n")
    print(f"{len(slides)} slide files + 00 TALKING-POINTS.txt → {notes_dir}")


if __name__ == "__main__":
    main()
