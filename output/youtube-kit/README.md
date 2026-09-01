# @NikRayani YouTube Kit

Everything the channel runs on, in one folder: the skills, the runnable deck
pipeline, and a written playbook for operating all of it **from a cloud session
on an iPad** (no Mac, no localhost, no pip).

Built from the `nikray21/ipad` repo. Stdlib-Python only — nothing here needs
installing.

---

## What's in the box

| Folder | What it is |
|---|---|
| `docs/` | **The playbook.** Written for this kit — read `docs/00-START-HERE.md` first. |
| `skills/` | Verbatim copies of all 12 channel skills (`SKILL.md` + their references, scripts and assets). |
| `pipeline/` | The runnable deck engine: `build_deck.py`, `marketdata.py`, `audit_deck.py`, `validate_facts.py`, `deck_template.html`, plus the 5 shipped episodes as worked examples. |
| `templates/` | Fill-in-the-blank starting points: episode JSON, deck module, YouTube description. |

## Read in this order

1. **`docs/00-START-HERE.md`** — the whole channel in one page: the two formats, the weekly cadence, what each skill hands you.
2. **`docs/01-CLOUD-SETUP.md`** — iPad/cloud session setup. Network settings, `DECK_OUT`, artifacts instead of localhost, committing your work. **Read this before your first cloud build or things will silently fail.**
3. **`docs/02-WEEKLY-WORKFLOW.md`** — Sunday and Wednesday, command by command, start to upload.
4. **`docs/03-SKILLS-REFERENCE.md`** — every skill: trigger phrases, inputs, exact outputs, cloud-ready or not.
5. **`docs/04-DECK-PIPELINE.md`** — how the deck engine works, the file contracts, the build→audit→validate loop, the hard rules and why each exists.
6. **`docs/05-DATA-SOURCES.md`** — every upstream, every route, the caches, and the data traps that have already burned an episode.
7. **`docs/06-POSTING-CHECKLIST.md`** — transcribe → chapters → titles → description → upload, with the templates.
8. **`docs/07-TROUBLESHOOTING.md`** — every known failure mode and its fix.
9. **`docs/08-CHEATSHEET.md`** — one page, print it. Every command you actually type.

## The 30-second version

```
Sunday   /find-stock  →  /stock-analysis-presentation TICKER  →  record  →  /post-video
Wednesday                /learn-stock "topic"                 →  record  →  /post-video
```

The deck is never done until this passes:

```bash
export DECK_OUT=output
python3 build_deck.py <SYM> && python3 audit_deck.py <SYM> && python3 validate_facts.py <SYM>
python3 audit_deck.py <SYM> --prove && python3 validate_facts.py <SYM> --prove
python3 export_notes.py <SYM>
git add -A && git commit -m "..." && git push
```

## Two rules that override everything else

1. **Never type a figure into a deck.** Every number is computed from pulled data or read out of a filing and recorded in `episodes/<SYM>.json`. The audit scans three hiding places for typed figures and fails the build.
2. **In a cloud session, uncommitted work is deleted.** The container is thrown away. `git push` at the end of every session or the episode is gone.
