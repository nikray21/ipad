# Filming the deck

Sample layouts live in `~/Desktop/Recording layouts/` — six annotated frames plus
the editable HTML that generated them.

---

## The measurement that decides the layout

Across a finished 24-slide deck, **82% of the 1920×1080 canvas carries content on
some slide**, and the only region free on *every* slide is a 1080×80 strip at the
bottom — too short for a camera.

**So a webcam bubble laid over a full-bleed deck will cover a chart.** Not might.
The deck has to make room instead.

To re-measure for a new deck, activate each slide in turn, mark a 40px grid where
any element paints, and find the largest all-empty rectangle. The full script is in
the session history; the conclusion has held for both episodes.

---

## `?cam=` — the deck reserves the zone itself

```
?cam=left&camw=26    the recording layout: 26% of the width free on the left
?cam=right&camw=26   mirrored
?cam=bottom          reserve height underneath instead
```

**The column is reserved by PADDING the slide, not by shrinking the stage.** The
first version scaled the whole 16:9 stage into 70% of the frame, which meant
`scale(0.70)` on every font — a 15px axis label landing at 10px, below the
readability floor — plus 324px of dead vertical space. Now the stage still fills
1920×1080 at **scale 1.0** and `.slide` simply gains `padding-left: 96 + 1920·camw`.
Type stays exactly the size it was designed at. Verify:

```js
getComputedStyle(document.getElementById('stage')).transform   // matrix(1,0,0,1,0,0) at 1080p
getComputedStyle(document.querySelector('.slide')).paddingLeft // 595px at camw=26
```

Every mode uses the same pure centred scale, so there is no translate left to
double-offset — the bug that once shifted the deck sideways and cropped it.

### Charts rebuild at the width they actually have

`chartW()` returns `1660 - camPx()`, and all 22 chart functions read it. Without
that a 1660 viewBox inside a narrower box is scaled down by `preserveAspectRatio`
and every label with it.

**Narrowing is what finds latent chart bugs.** Everything below passed at 1660 and
broke at 1161, so re-run the layout audit in camera mode after touching any chart:

| Chart | What broke when narrowed | Fix |
|---|---|---|
| `bars` | two-word sub-labels ran into each other | `wrapLabel()` to the slot, 2 lines |
| `track` | price and mean-target value labels touched | stack the second one 62px higher |
| `donut` | legend text ran into the stats panel | columns from measured widths; stats stack when tight |
| `radar` | labels drew to x = −133, outside the box | box widened by `LP`, labels wrap inside it |

### It is the DEFAULT, and a key

A deck opens in the camera layout. Nothing to remember, nothing to add to the URL.

`?cam=` alone was a design mistake: opening the deck the normal way — a
double-click, or a bare `#s2` link — gave the full-bleed layout with no hint the
camera layout existed, and it read as broken. So:

| Key | Does |
|---|---|
| **`C`** | camera layout off / on. On by default; the choice is remembered. |
| **`⇧C`** | show/hide the pixel measurements. Never leave these up for a take. |
| **`[` `]`** | narrow / widen the reserved column by 2% at a time |

The query string still wins when present (`?cam=left&camw=26`), so a link can pin a
layout. The stored value is **tri-state** — `left` / `right` / `off` — because with
a default of `left` an absent key has to mean "never chosen"; removing it on
toggle-off meant the next open quietly went back to camera mode. `@media print`
neutralises the column and hides the frame, so ⌘P still gives a full-bleed PDF. Toggling at runtime **re-mounts every chart** through `mountCharts()` —
charts take their width at build time from `chartW()`, so without that the column
is reserved while the charts are still 1660 wide and overflow straight into it.

On a `file://` URL `localStorage` can throw, so every access is wrapped: the key
still works for the session, it just may not persist. Serve the folder if that
matters.

### The frame, and the numbers

The **frame** is part of the slide and stays up in the recording: a soft filled
rounded slot the camera sits inside, no text. It is removed when camera mode goes
off — `fit()` returned early on that path and left the slot painted on the slide.
**`⇧C`** toggles the *measurements* — the dashed column plus `put the camera here 411 × 548 at 44, 266` — which
must never be up during a take. At `camw=26` on a 1920×1080 canvas that is:

```
reserved column   499 px wide, full height
camera bubble     411 × 548 at x=44, y=266     (3:4 portrait, vertically centred)
```

Those are stage pixels, and the stage is 1:1 with a 1080p recording, so they are the
numbers to type straight into OBS.

### The invariant that makes any of it trustworthy

`deckAudit()` fails any ink that crosses into the reserved column. It had to be
added: `.footer` is absolutely positioned at `left:96px`, so the slug printed
straight across the column while the audit still said CLEAN. It now reads
`var(--cam-l)` like everything else. The same pass also checks **every `<svg>` on
the slide**, not just the one inside `[data-chart]` — the snapshot slide's radar
lived outside that host and so had never been geometry-checked at all.

---

## The four scenes

| When | Layout | Why |
|---|---|---|
| 0:00 hook | full-frame camera, no deck | the first 15 seconds decide retention; lead with the hardest number |
| the FA half | **`?cam=left`, camera in the reserved column** | he stays visible for the whole deck, nothing covered |
| the handoff | 50/50 deck + chart, circular camera on the seam | makes the cut feel like one video, not two |
| the TA half | Webull full-bleed, camera bottom-left | charts put the action top-right; the lower-left is watchlist gutter |
| sign-off | back to full frame | the call should come from him, not a slide |

Full-bleed deck with a corner bubble is the tempting option and it is the one that
covers content. If he wants it, restrict it to the title, findings and verdict
slides, which have room.

---

## Two constraints that bite

**Capture the window, not the display.** The deck is a fixed 1920×1080 stage scaled
to its window, so a window capture is always pixel-sharp at any size.

**The notes drawer is on the same page.** `N` toggles it. If he captures the whole
display it is on camera. Capture the window, or put notes on a second screen.

---

## Before he presses record

- Rebuild that morning — the build refuses on stale data and stamps the price into
  every slide footer.
- Serve over `http://127.0.0.1`, never `file://` (the extension blocks it, and it
  keeps the URL bar clean).
- Console must read `[deck] self-check ok — N slides, every chart rendered`.
- Draw the Webull levels first. Live drawing is the most-skipped part of TA videos.
- Pick the theme once — `?theme=cream` or `dark` — and keep it for the episode.

---

## Software

**Do not tell him to download or install anything.** Ask what he already has.

- Already has OBS / Ecamm / ScreenFlow → that is the answer; build the scenes above.
- Built-in only → QuickTime records screen and camera as two separate files, which
  he composites in editing. macOS Presenter Overlay puts him over shared content,
  but only during a video call, so it does not fit a solo recording.
