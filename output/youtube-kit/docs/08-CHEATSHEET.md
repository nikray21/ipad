# 08 — Cheat Sheet

One page. Everything you actually type.

---

## Session preflight

```bash
cd "$(git rev-parse --show-toplevel)"
export DECK_OUT=output
python3 marketdata.py quote NVDA      # network check
ls decks/ episodes/ output/
git log --oneline -5
```

## Find the ticker

```
/find-stock
```
```bash
python3 .claude/skills/find-stock/trends_http.py "NBIS stock" "nebius stock" "PLTR stock"
python3 .claude/skills/find-stock/trends_http.py --related "NBIS stock"
```
Max 5 keywords per comparison · always include an anchor keyword · YouTube
property, `now 7-d`, geo US · both ticker form and company-name form.

## Build the Sunday deck

```
/stock-analysis-presentation <SYM>
```
```bash
python3 build_deck.py <SYM>
python3 audit_deck.py <SYM>            # ALL DECK INVARIANTS PASS
python3 validate_facts.py <SYM>        # ALL EPISODE FACTS TRACE
python3 audit_deck.py <SYM> --prove    # must go RED
python3 validate_facts.py <SYM> --prove
python3 export_notes.py <SYM>
```

## Build the Wednesday deck

```
/learn-stock "how shorting works"
```
```bash
cp .claude/skills/learn-stock/assets/deck-engine.html "output/educational/<TOPIC> $(date +%F)/<TOPIC>-deck.html"
```
Replace only `DEFS` and the `v*()` mount functions.

## View a deck (cloud)

Publish the HTML as an artifact, then open with:

| Query string | For |
|---|---|
| `?theme=cream&audit=1` | building — read the audit line |
| `?theme=dark&audit=1` | the other theme; must also be CLEAN |
| `?cam=left&camw=26` | recording layout check |
| `?theme=cream` | recording |

## Deck keys

`→`/`←` slides · `T` theme · `N` notes · `c` camera · `⇥` calculator step

## Post the video

```bash
which ffmpeg || apt-get install -y ffmpeg
ffmpeg -y -v error -i "$AUDIO" -ac 1 -acodec libmp3lame -q:a 4 "$SP/final.mp3"
npx hyperframes transcribe "$SP/final.mp3" -d "$SP" --json --model small.en
```
```
/post-video   (attach the M4A, name the ticker)
```

## Data routes

```bash
python3 marketdata.py {quote|history|fundamentals|profile|street|estimates|filings} <SYM>
```

## Other skills

```
/fa <TICKER>                    python3 .claude/skills/fa/analyze.py TICKER [--json]
/technical-analysis             (attach the chart screenshot)
/design                         load before any chart change
/design-craft                   new visual patterns
```

## End of session — always

```bash
git add -A
git status --short
git commit -m "<SYM> episode: deck, notes, sources"
git push -u origin <branch>
```

---

## Copy budgets

| Field | Max |
|---|---|
| `head` | 9 words |
| `punch` | 14 words |
| `sub` | 12 words |
| all on-screen | 30 words |

Everything longer goes in `why` (Sunday) or `notes` (Wednesday) — never rendered,
lands in the script.

## Chapter rules

First at `0:00` · ≥3 chapters · each ≥10s · chronological · `M:SS`.

## The five things that fail a build

1. Fewer than three original findings (Rule Zero)
2. A typed figure anywhere
3. A chart form carrying >⅓ of the deck
4. An HTML entity in a chart spec
5. On-screen copy over the word budget
