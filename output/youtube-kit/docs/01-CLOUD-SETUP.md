# 01 — Cloud / iPad Session Setup

Read this before your first cloud build. Three things behave differently from the
Mac, and each one fails *silently* if you skip it.

---

## 1. Set the output directory

On the Mac, `deckpath.py` defaults output to `~/Desktop/…`. A cloud container has
no Desktop, and anything written outside the repo is destroyed when the container
is reclaimed.

```bash
export DECK_OUT=output
```

Do this **before** `build_deck.py`, every session. Everything then lands in
`output/<TICKER> <DATE>/` inside the repo, where git can keep it.

Verify:
```bash
echo "$DECK_OUT"                 # must print: output
python3 -c "import deckpath; print(deckpath.root())" 2>/dev/null || true
```

---

## 2. Network access must be **Full**

The default "Trusted" allowlist blocks every upstream the pipeline needs. Set the
environment's network policy to **Full**, or a custom allowlist containing:

```
sec.gov
data.sec.gov
www.sec.gov
api.nasdaq.com
query1.finance.yahoo.com
api.stocktwits.com
trends.google.com
suggestqueries.google.com
```

Smoke test before you commit to a build:

```bash
python3 marketdata.py quote NVDA
```

- JSON with a price → you're good.
- Connection error / timeout → it's the network policy, not the code. Nothing in
  this pipeline talks to `127.0.0.1`, so "connection refused" never means a
  service is down.

---

## 3. There is no localhost — publish an artifact instead

On the Mac you serve the deck with `python3 -m http.server 4849`. **In a cloud
session that URL is unreachable from the iPad.** Instead, publish the deck HTML
as an artifact and open the private URL.

Append the query string you need:

| Query | What it does |
|---|---|
| `?theme=cream` | The light theme (the one that films best) |
| `?audit=1` | Runs the built-in layout audit on load |
| `?cam=left&camw=26` | Reserves 26% of the width on the left for the camera |
| `?theme=cream&audit=1` | **The usual combination while building** |

The artifact URL is also how you open the deck full-screen on the iPad to record.

**The layout audit lives inside the deck, not in a console paste.** Open with
`?audit=1` and read the one line it prints:

```
[deck] AUDIT CLEAN — 22 slides, no layout, animation or text faults
```

or

```
[deck] AUDIT — 3 issue(s):
  10 bridge: chart draws 2510px below its box
  10 bridge: chart overlaps the why band by 2198px
  18 range: DEAD CHART
```

It must read **CLEAN in cream and in dark** before a deck is recorded. Then still
step every slide and look at it — the audit proves geometry, not that the chart
argues its headline.

---

## 4. Commit and push — the repo is the only persistence

The container is thrown away after the session. Anything not pushed is gone.

At the end of **every** cloud session:

```bash
git add -A
git status --short          # look at it — confirm output/ and episodes/ are staged
git commit -m "NBIS episode: deck, notes, sources"
git push -u origin <your-branch>
```

Specifically commit:
- `output/` — the whole built episode folder
- `episodes/<SYM>.json` — the filing-read facts
- `decks/<SYM>.py` — the narrative module

**Not** committed (gitignored, and disposable): `.cache_filings/`, `.cache_form4/`,
`.cache_market/`.

---

## 5. `/post-video` in a cloud session

There's no filesystem access to the iPad, so the input is **audio only**:

1. Finish the edit in CapCut and export.
2. Run the **"Extract Audio"** iOS Shortcut (Encode Media → Audio Only, M4A) on
   the *finished export* — not the raw take. Chapters must land on the edited
   timeline.
3. Attach the M4A directly in the chat. It lands under
   `/root/.claude/uploads/<session>/…` — take the path from the message, never
   guess it.
4. Cloud filenames are opaque (`IMG_2687.m4a`) and carry no topic, so say which
   ticker or topic it is.

`ffmpeg` may not be preinstalled:

```bash
which ffmpeg || apt-get install -y ffmpeg     # sandbox runs as root; one-time
```

---

## 6. What does NOT work in a cloud session

| Skill | Why | What to do |
|---|---|---|
| `/youtube-thumbnail-maker` | Higgsfield MCP not connected | Run on the Mac |
| `/youtube-popup-graphic` | Higgsfield MCP | Run on the Mac |
| `/youtube-broll-maker` | Higgsfield MCP | Run on the Mac |
| `/youtube-clipper` | Higgsfield MCP | Run on the Mac |
| `/race-dossier` | Needs `~/Projects/f1-dossier` locally | Run on the Mac |
| Browser fallback in `/find-stock` | No Chrome in the sandbox | Use the bundled `trends_http.py`; if it 429s, fall back to YouTube autocomplete + view-velocity evidence and **say Trends was unavailable** — never fabricate Trends numbers |

Everything else — find-stock's HTTP path, the whole deck pipeline, learn-stock,
post-video, design, fa, technical-analysis — runs fine in the cloud.

---

## Session preflight, copy-paste

```bash
cd "$(git rev-parse --show-toplevel)"
export DECK_OUT=output
python3 marketdata.py quote NVDA | head -20    # network check
ls decks/ episodes/ output/                    # what already exists
git log --oneline -5                           # where you left off
```
