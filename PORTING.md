# Porting this repo off Claude Code

What is already self-contained, what lives outside the repo, and every line that
names a Claude-only capability. Written 2026-09-02 against commit `14b821e`.

## 1. Already in the repo — nothing to do

All 13 skills are committed under `.claude/skills/`, along with everything the
deck pipeline needs to run:

| Asset | Path |
|---|---|
| Skills | `.claude/skills/` (13 folders) |
| Deck chart library | `deck_template.html` |
| Learn-deck engine | `.claude/skills/learn-stock/assets/deck-engine.html` |
| Visual pattern library | `.claude/skills/learn-stock/assets/visual-library.html` |
| Pipeline | `build_deck.py`, `audit_deck.py`, `validate_facts.py`, `crosscheck.py`, `marketdata.py`, `export_notes.py`, `deckpath.py` |
| Episode data | `episodes/*.json`, `decks/*.py` (DVA, NBIS, PLTR, RKLB, SPCX) |
| TA tooling | `.claude/skills/technical-analysis/` — `backtest.py`, `screener.py`, `control.py`, `slope_sweep.py`, all three `reference/*.md` |

The Python is stdlib-only, so it runs under any agent, or by hand with no agent
at all.

## 2. Referenced but NOT in the repo

These are named by absolute path in skill files and live on the Mac or in Drive.
A cloud session cannot reach them, and neither can Antigravity on a fresh clone.

| What | Referenced at | Where it actually lives |
|---|---|---|
| Thumbnail style reference JPG | `youtube-thumbnail-maker/SKILL.md:15` | `/Users/fknr/Downloads/DhxDncjsItw-HD (1).jpg` — note the `fknr` home dir, likely stale |
| F1 dossier repo | `race-dossier/SKILL.md:3,9,12,15` | `~/Projects/f1-dossier/` (its own git repo) |
| Browsable visual menu | `learn-stock/SKILL.md:52`, `visuals.md:8` | `~/Desktop/educational/VISUAL-LIBRARY.html` — but `assets/visual-library.html` in this repo is the same content |
| Reference learn build | `learn-stock/SKILL.md:21` | `~/Desktop/educational/SWING-9TO5 2026-08-12/` — superseded by `assets/deck-engine.html` |
| Local deck template copy | `design/SKILL.md:15`, `stock-analysis-presentation/SKILL.md:18` | `~/Projects/episode-deck/` — superseded by `deck_template.html` here |
| Trading journal | not referenced in-repo any more | personal, kept out of this public repo — see `.gitignore` |

**Do not commit the trading journal.** This repo is public.

The `dataviz` skill both deck skills cite is bundled inside Claude Code itself,
not a file anywhere in this repo, and it is not on disk in a cloud session
either. The validated palette is recorded in `design/SKILL.md`, which is the
part that matters — treat that as the replacement.

## 3. Claude-only capabilities named in skill bodies

Each of these needs a host-specific equivalent or a rewrite.

### Artifact publishing — the blocking one
`CLAUDE.md:23` · `stock-analysis-presentation/SKILL.md:134` ·
`learn-stock/SKILL.md:65` · `new-ticker-runbook.md:199`

Every deck ends by publishing the HTML as an artifact and opening the private
URL. That is both the layout audit path (`?theme=cream&audit=1`) and how the
deck gets onto the iPad full-screen to record. There is no equivalent outside
Claude. Any port needs a different answer here — static host, or accept that
decks are built and viewed on the Mac only.

### `ToolSearch` — deferred tool loading
`youtube-thumbnail-maker:14` · `youtube-broll-maker:15` ·
`youtube-clipper:18` · `youtube-popup-graphic:51`

All four are MCP loaders for Higgsfield. Other hosts expose MCP tools directly;
delete the load step and call the tools.

### `AskUserQuestion` — structured prompts
`youtube-thumbnail-maker:19,24` · `youtube-broll-maker:19,27`

Replace with a plain question in prose.

### Parallel subagents
`find-stock/SKILL.md:15` — launches three `general-purpose` agents in one
message for the discovery sweep. Hosts with a subagent concept can map this;
otherwise run the three sweeps sequentially and accept it is slower.

## 4. MCP servers — account config, not repo content

Higgsfield (thumbnail, b-roll, popup, clipper) and Webull (race-dossier odds,
market data) are connected at the account level. Nothing about them is stored
here, and nothing should be — they carry credentials. Reconnect them on the new
host.

## 5. Order of work, cheapest first

1. `/post-video` — transcription is already local Whisper (`npx hyperframes`),
   no Claude-only step at all. Should work as-is.
2. `/find-stock` — only the subagent fan-out needs changing; `trends_http.py`
   is stdlib and portable.
3. `/technical-analysis`, `/fa` — no Claude-only references. Portable.
4. The four Higgsfield skills — mechanical: drop `ToolSearch`, replace
   `AskUserQuestion`.
5. `/stock-analysis-presentation`, `/learn-stock` — everything works up to
   delivery, then hits the artifact gap. Solve that before porting these.
