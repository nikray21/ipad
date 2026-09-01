# The "why it matters" band

Every slide ends with one. It is the only part of the deck written *for* the
viewer rather than *about* the company, and it is the difference between a video
someone finishes and one they close.

**The standard: a smart person who has never read a 10-Q understands what the
number means and why they should care — first time, at speaking pace, on a phone.**

Ten of PLTR's 23 bands failed this on the first pass. Every one failed the same
way: a word that is invisible to someone who works with filings and opaque to
everyone else.

---

## Two jobs, in this order

1. **What it means** — in words a fourteen-year-old uses.
2. **Why it matters to someone deciding whether to buy** — the consequence.

A band that only does (1) is a caption, not a why-band. Slide 8 once listed
93% → 83% → 72% and stopped. Fixed:

> Sales still grow, just more slowly each quarter. **That matters because the price
> of this stock assumes growth keeps speeding up, and the company's own forecast
> says it is about to stop.**

---

## Banned words, and what to say instead

| Never | Say |
|---|---|
| the multiple / multiple compression | how much people are willing to pay for the same sales |
| underwriting the opportunity | if part of why you like this stock is… |
| pretax income | the profit, before tax |
| adjusted operating income | their profit forecast |
| free cash flow | the cash they expect to be left with |
| add-back | item added back |
| exit multiple | buyers still paying a rich price at the end of it |
| a great print | a great set of results |
| entry price | a good price to buy at |
| open-market purchase | bought shares with their own money |
| 10b5-1 plan | set up months ahead on an automatic schedule |
| termination for convenience | the customer can walk away whenever they like |
| bankable backlog | money locked, as opposed to money promised |
| remaining performance obligations | what is truly committed |
| per unit of growth | for each point of growth |
| analyst consensus | what analysts expect |
| basis points | just use the percentage |
| accretive / dilutive | makes your slice bigger / smaller |

The test is not "would a finance person accept this" — it is **"would my mum know
what I just said."**

---

## Devices that work

**Put it in dollars they can hold.** The strongest band in the PLTR deck:

> For every $100 of this stock you buy, the company brings in about $1.39 of sales
> a year and keeps about 68 cents of that as profit.

That is a 53× revenue multiple, said without the words "revenue multiple".

**Own vs owe, not assets vs liabilities.**

> They own about $11.7B and they owe about $1.8B. None of what they owe is borrowed
> money — most of it is customers who have already paid for work not yet delivered.

**Explain the rule of thumb before you use the number.**

> Add how fast a software company grows to how much of each sale it keeps as
> profit, and anything over 40 is considered healthy. Palantir grew 93% and kept 62
> cents in the dollar, which lands at 155.

**Give the caveat rather than the flattering number alone.** The same band
continues, because the 62 cents excludes stock compensation while the deck later
argues stock compensation is a real cost:

> One caveat worth knowing: that profit figure leaves out the shares handed to
> staff. Count those and it is 47 cents, still excellent.

Accuracy outranks simplicity. A simple sentence that overstates is worse than a
slightly longer one that does not.

**Name the consequence to the viewer, not to the company.**

> every share they hand out makes the slice you own a little smaller

**Short sentences.** The worst band was one 40-word sentence. Six short ones say
the same thing at half the reading grade.

---

## Measure it, do not eyeball it

```python
import json, os, re, sys
sys.path.insert(0, os.getcwd())   # repo root
from deckpath import read_dir
SYM, DATE = "PLTR", "2026-08-07"
b = json.load(open(os.path.join(read_dir(SYM, DATE), "data", f"{SYM}-{DATE}.json")))
JARGON = ['multiple','underwrit','compress','pretax','GAAP','consensus','RPO','per unit',
          'basis point','operating margin','add-back','EBITDA','adjusted','entry price',
          'open-market','10b5','bankable','termination-for','accretive','headwind','dilutive']
def syl(w):
    w = re.sub(r'[^a-z]', '', w.lower())
    if not w: return 1
    n = len(re.findall(r'[aeiouy]+', w))
    if w.endswith('e'): n -= 1
    return max(1, n)
rows = []
for i, s in enumerate(b['payload']['slides'], 1):
    w = s.get('why')
    if not w: continue
    t = re.sub('<[^>]+>', '', w).replace('&mdash;', '—')
    words = re.findall(r"[A-Za-z'’]+", t); sents = max(1, len(re.findall(r'[.!?]', t)))
    grade = 0.39*len(words)/sents + 11.8*sum(syl(x) for x in words)/len(words) - 15.59
    hits = [j for j in JARGON if j.lower() in t.lower()]
    rows.append((i, len(words), grade, hits))
    print(f"{i:>3} {len(words):>4}w {grade:>5.1f}  {', '.join(hits) or '—'}")
g = [r[2] for r in rows]
print(f"\navg grade {sum(g)/len(g):.1f} · max {max(g):.1f} · longest {max(r[1] for r in rows)}w"
      f" · jargon in {sum(1 for r in rows if r[3])}/{len(rows)}")
```

**Targets:** average grade **under 7**, no band over **90 words**, **zero** jargon
hits. PLTR shipped at avg 5.4, max 9.9, longest 88w, zero hits.

A band scoring high is almost always one long sentence — split it before rewording
anything.

---

## Two traps

**Do not let simplifying introduce an error.** Rewriting a margin as "kept 62 cents
of every dollar" quietly swapped the GAAP figure (47%) for the adjusted one (62%),
and the deck argues elsewhere that the difference is a real cost. Check that the
plain version still says the true thing.

**Do not restate the wrong quantity.** "65% over fair value" and "fair value 65%
below price" are different numbers (the second is 39%). Read the figure off the
chart and word the sentence to match it.
