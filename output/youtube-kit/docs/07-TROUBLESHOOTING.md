# 07 — Troubleshooting

Known failure modes and their fixes. Ordered by how often they bite.

---

## Network / data

**`python3 marketdata.py quote NVDA` → connection error or timeout**
The environment's network policy is on the default **Trusted** allowlist, which
blocks every upstream here. Set it to **Full**, or allowlist `sec.gov`,
`data.sec.gov`, `api.nasdaq.com`, `query1.finance.yahoo.com`, `api.stocktwits.com`,
`trends.google.com`, `suggestqueries.google.com`.
*Not* a service being down — nothing in the pipeline talks to `127.0.0.1`.

**SEC returns 403 / empty**
Missing User-Agent. Every SEC request needs
`{"User-Agent": "nikil.rayani@puriscorp.com research"}`.

**`build_deck.py` refuses: stale data**
`_ageS` exceeded its `ttl_for()` ceiling. That's a hard stop by design, not a
warning. Clear the relevant cache and refetch:
```bash
rm -rf .cache_market/ && python3 build_deck.py <SYM>
```

**`trends_http.py` returns 429**
Google blocks datacenter IPs sometimes. The script says so plainly. In cloud
there's no browser fallback — use the YouTube-autocomplete + view-velocity
evidence from the research agent instead, **and say Trends was unavailable.**
Never fabricate Trends numbers.

**A route raises `KeyError`**
Unknown route name. Valid ones: `quote`, `history`, `fundamentals`, `profile`,
`street`, `estimates`, `filings`.

**Numbers look wrong but nothing errored**
Check the authority order. SEC XBRL is authoritative; vendor data is a cross-check
only. Specifically: never trust vendor `epsYears`/`ttmSeries` (they overstated
DVA's annual EPS ~37%, apparently dividing total net income rather than income
attributable to the parent). Build trailing EPS from the reported 8-K quarters.

---

## Build / audit failures

**`audit_deck.py` fails `no-hardcoded-figures`**
A number is typed somewhere. Three hiding places: `deck_template.html`, string
literals in `decks/*.py`, and episode verdict prose. Fix by choosing one of the
three legitimate escapes:
- price-dependent prose → `{path|fmt}` tokens (resolved by `resolve_prose()`)
- definitional label text → module-level `LITERALS_OK` tuple
- structural filing figures fixed for the quarter → `proseLiteralsOK` in the
  episode JSON

The scanner catches bare multiples (`49x`) too, not just `%` and `$`.

**`audit_deck.py` fails `slide-variety`**
One chart form carries more than a third of the deck. Load `/design` and pick a
different form for the job — the table there maps job → form.

**`audit_deck.py` fails `chart-entities`**
An HTML entity is in a chart spec. Chart labels are written with `textContent`, so
`&times;` renders as seven literal characters and the extra width shoves a value
label into the next column. Use the glyph (`×`). Entities are only for prose
fields (`head`, `sub`, `why`).

**`audit_deck.py` fails `word-budget`**
On-screen copy over budget: head ≤ 9 words, `punch` ≤ 14, `sub` ≤ 12, 30 words all
in. Move the long form into `why` — it's never rendered, and lands in the script.

**A check passes but `--prove` doesn't go red**
The check can't actually fail, which makes it worthless. That's the exact bug
`--prove` exists to expose (the episode-prose check originally matched only `%`
and `$` and would have missed the `49x` it was written for). Tighten the check and
re-run `--prove`.

**`validate_facts.py` flags a number that's really in the filing**
Number-boundary matching. It once passed a fabricated `611` because it sits inside
`2,611,500`; tightening that then caught a real mis-attribution. **Confirm the
filing text first, then add `_pct` or `searchAs`** — never loosen the match.

**Build fails: fewer than three findings**
Rule Zero. The episode needs at least three original findings, each with a `where`
naming the note/page/table — "the 10-Q" is rejected, "10-Q Note 3, three pages past
the highlights" is accepted.

**A company-shaped check neither passes nor fails**
That's correct behaviour: checks like a payor split or an insider block `SKIP` with
an `n/a` line when the company has no such figure. They never silently pass.

---

## Deck rendering

**`[deck] AUDIT — N issue(s)` with "chart draws Xpx below its box"**
The chart's SVG content exceeds its viewBox. Usually a label at a negative
coordinate or a rail bleeding off an edge — the audit checks **all four edges**,
which it didn't originally (a bracket label at `x = -37` and a 730px left bleed
both read CLEAN under the two-edge version).

**"DEAD CHART"**
The chart function returned nothing renderable. Check the spec keys against the
form's signature in `deck_template.html`'s `CHARTS` registry, and check for a
`null` where a function is expected — formatters must be named strings
(`fmtKind`), never callables across the payload boundary.

**Rendered `undefined` or `NaN` on a slide**
A broken key in the payload. Cheap check, and it caught one on slide 1 of a
shipped deck.

**Charts look fine full-width, break in camera mode**
Expected — narrowing is what finds latent chart bugs. `chartW()` returns
`1660 - camPx()`; several charts passed at 1660 and broke at 1161 (`bars`
sub-labels colliding, `track` value labels touching, `donut` legend into the stats
panel, `radar` labels at x = −133). **Re-run the audit with
`?cam=left&camw=26` after touching any chart.**

**The whole deck is shifted sideways / cropped**
An old bug from when camera mode scaled the stage. It must not: the stage stays at
`scale 1.0` filling 1920×1080, and `.slide` gains
`padding-left: 96 + 1920·camw`. Verify:
```js
getComputedStyle(document.getElementById('stage')).transform    // matrix(1,0,0,1,0,0)
getComputedStyle(document.querySelector('.slide')).paddingLeft  // 595px at camw=26
```

**Numbers on screen drift from the built string**
They shouldn't — count-up animations always write the exact built string on the
final frame. If one drifted, the payload has two expressions for one metric.
Rule 2: **one number, one value, across the whole deck** — render both slides from
the same expression.

**Notes don't match the deck**
Rerun `python3 export_notes.py <SYM>` after every rebuild. Figures come from the
frozen payload.

---

## Cloud-session specifics

**Deck built but I can't open it**
There is no localhost. Publish the HTML as an artifact and open the private URL
with `?theme=cream&audit=1`.

**Everything I did last session is gone**
The container was reclaimed. Only what was committed and pushed survives. At the
end of every session: `git add -A && git commit -m "…" && git push -u origin <branch>`.

**Output landed somewhere odd / nothing in `output/`**
`DECK_OUT` wasn't exported. `export DECK_OUT=output` **before** `build_deck.py`.
`deckpath.py` will still *find* an episode filed one level deeper, so a tidied
folder never breaks the audit trail.

**"No space left on device" with low disk used**
The writable allowance is spent, not the machine broken. Delete what you don't
need — the caches first (`rm -rf .cache_market .cache_filings .cache_form4`).
Deletes still succeed while writes fail.

**A Higgsfield skill says its tools don't exist**
The Higgsfield MCP isn't connected in cloud. Run those four on the Mac.

**`ffmpeg: not found`**
```bash
apt-get install -y ffmpeg
```
One-time per container; the sandbox runs as root.

**`npx hyperframes transcribe` hangs on first run**
It's downloading the whisper model. Give it a minute or two.

---

## Content mistakes that have shipped

| Symptom | Rule | Fix |
|---|---|---|
| "44% drawdown" wrong on three slides | 1 | Never type a figure |
| Slides 17 and 21 disagree on one multiple | 2 | One expression, both slides |
| Computed FCF ≠ reported FCF | 3 | Quote what the company defines |
| "Best margin in two years" — false | 8 | Verify every best/highest claim |
| 25% and 23% for the same fact | 9 | Don't mix diluted-weighted-average with outstanding |
| A "drawdown" that was high-minus-low | 11 | `snap.peakToTrough` walks the tape in order |
| Margin claim under a revenue chart | 16 | The chart must argue the caption |
| Two bars two pixels apart | 17 | Plot the change, not the level |
| "The next number…" on a slide that got cut | 18 | No forward-pointing copy |
| "Not much between here and fair" above a 65% gap | 19 | Caption must not contradict the chart |
| A single fair-value point estimate | 20 | Ship the bear/bull bracket |
