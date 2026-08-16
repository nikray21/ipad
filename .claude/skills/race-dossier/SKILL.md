---
name: race-dossier
description: Build/refresh the F1 race-weekend betting dossier (~/Projects/f1-dossier). Use when he says "race dossier", "quali analysis", "final check", "F1 picks", or before any Grand Prix.
---

# F1 Race Dossier — BULL

Produce the full pre-race betting dossier and write it to
`~/Projects/f1-dossier/f1_dossier.json`.

**BULL was retired on 2026-08-10, so the dossier has no host.** It used to render
under BULL's F1 tab. The files were rescued into `~/Projects/f1-dossier/` (its own
git repo) — to view one, serve that folder and open `f1app.html`:

    cd ~/Projects/f1-dossier && python3 -m http.server 4852 --bind 127.0.0.1
    open http://127.0.0.1:4852/f1app.html

## Data collection (all free, no keys)
1. **OpenF1** (`api.openf1.org/v1/`): sessions for `meeting_key=latest` → per contender pull:
   - Quali: best lap + best S1/S2/S3, speed traps (`st_speed`, `i1_speed`, `i2_speed`)
   - Corner-by-corner: fastest-lap `car_data` (speed) resampled ~280 pts; local minima <260 km/h = corner zones; compare min speeds across drivers
   - FP2 long runs: laps 80–90s per driver (≥5 laps) → avg pace + stdev (consistency). Note who HID race pace.
   - Tyre sets burned per driver (stints across all sessions)
   - Weather baseline (air/track/wind/humidity)
   - Space calls ~2s; retry on 429; never cache empty results.
2. **WebSearch**: race weather forecast, grid penalties/stewards decisions (CHECK BOTH before finalizing — penalties flip everything), tech upgrades, driver form/mood narratives.
3. **Webull events MCP** (`get_event_snapshot`, series `KXF1RACE-*`, `KXF1RACEPODIUM-*`): live winner + podium prices for all contenders. Re-pull AFTER any penalty news — market moves fast.

## Analysis rules (learned the hard way)
- **Weight grid position heavily** at low-overtaking tracks; a pace-based pick starting P4+ to WIN is a chaos lottery — prefer the podium market for pace theses.
- Passing at Hungaroring-type tracks happens via UNDERCUT (pit lane), not on track.
- Straight-line speed deficit = can't pass, regardless of corner speed (wing tradeoff).
- Long-run sims carry unknown fuel loads — cap their weight.
- Rain flips everything to the proven wet drivers (HAM/VER class); state the kill-switch.
- Human factor (form, incidents, pressure) = 1–2% nudge max, never a thesis.
- Output per bet: price, $1 payout, my odds vs market, VALUE/FAIR/RICH tag. Fun money $10–30 total, separate from trading.

## Dossier format (f1_dossier.json)
`{_updated, title, race, sections:[{h, html}]}` — sections: ⚖️ Verdict hero (main/small/conditional/skips + reasoning), 📊 odds board (my% bar vs market tick), 🧠 form & headspace, ⏱ race pace bars, 🛣 straights cards, 🌀 corner table (green = fastest), 📐 sector deltas, 🌡 weather cards + rain kill-switch, 🔧 pit strategy, 🏁 grid/penalty/final odds. Use the dashboard's light-theme CSS vars and existing classes (`analysis`, `tablewrap`, table). Update `f1_analysis.json` (headline/verdict) and `events.json` odds to match.

## Cadence
FP2 done → first read. Post-quali → recalibrate. **Post-stewards/penalties → final board** (this is when value appears/dies). Morning of race → weather + closing prices check before any bet.
