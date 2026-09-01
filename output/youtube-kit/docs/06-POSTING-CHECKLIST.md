# 06 — Posting Checklist

From finished export to uploaded video. `/post-video` does steps 2–6; this is what
it does and what you check.

---

## 1 · Get the audio in

**Cloud / iPad (the normal path):**
1. Export the finished cut from CapCut. **The finished export — not the raw take.**
   Chapters must land on the edited timeline.
2. Run the **"Extract Audio"** iOS Shortcut (Encode Media → Audio Only, M4A).
3. Attach the M4A directly in the chat. It lands under
   `/root/.claude/uploads/<session>/…` — the path comes from the message, never a
   guess.
4. Cloud filenames are opaque (`IMG_2687.m4a`), so **say which ticker or topic it
   is.** Mac filenames like `NBIS 8.16.mov` are self-describing.

**Mac:** just give the video path; usually `~/Desktop`.

---

## 2 · Transcribe

```bash
SP="<scratchpad dir>"
which ffmpeg || apt-get install -y ffmpeg       # cloud sandbox runs as root

# Mac — strip the audio track off the video:
ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1 "$VIDEO"
ffmpeg -y -v error -i "$VIDEO" -vn -ac 1 -acodec libmp3lame -q:a 4 "$SP/final.mp3"

# Cloud — the input is already audio-only, just transcode:
ffmpeg -y -v error -i "$AUDIO" -ac 1 -acodec libmp3lame -q:a 4 "$SP/final.mp3"

npx hyperframes transcribe "$SP/final.mp3" -d "$SP" --json --model small.en
```

First run in a fresh cloud session downloads the whisper model — allow a minute or
two. `transcript.json` is a flat word array `[{text, start, end}, …]`; group words
into sentences at terminal punctuation and print with `M:SS` stamps. **That
timestamped sentence list drives everything else.**

**Fact source of truth:**
- Sunday episodes → `episodes/<SYM>.json` (`verdict`, `findings`, `fairValue`,
  `sources`).
- Wednesday `/learn-stock` episodes → no episode JSON; build from the transcript
  alone, skip the deck cross-checks.

---

## 3 · Chapters

Find the topic shifts in the timestamped transcript (new finding, numbers → chart,
recap, trade plan, outro).

**YouTube's rules for linked chapters — all three or none of them link:**
- First chapter at exactly `0:00`
- At least 3 chapters
- **Every chapter ≥ 10 seconds** (merge anything shorter)
- Chronological, `M:SS` format

**Label with a short curiosity-preserving phrase from the content** — "The
customers who vanished", "My fair value: $173" — never "Part 2".

---

## 4 · Titles (2–3 options, best first)

- **WebSearch first** — the ticker's news this week AND the competing YouTube
  titles. Never rely on recall for what's working right now.
- Every option must match what the video **actually argues**. A hook the video
  never mentions kills retention. Verify against the transcript before proposing.
- Patterns that work in this niche:
  - real tension — "Grew 454% — but the profit isn't real"
  - a specific number from the video
  - question + price target
  - the forensic angle — "I read the filings"

---

## 5 · Description

Order matters. See `templates/description-template.txt`.

1. **Two-line hook** — this is all that shows in search. **No links here.**
2. `In this video:` bullets — pulled from the findings/transcript. **Tease, don't
   spoil.**
3. **Source links** — the SEC filing URLs from the episode JSON. Credibility is
   the brand.
4. `⏱ CHAPTERS` block from step 3.
5. Not-financial-advice disclaimer.
6. 4–6 hashtags (`#TICKER #StockAnalysis #Investing …`).

Delivered in **one copy-paste code block**.

---

## 6 · Quality checks (always reported)

- **Fact flubs.** Every spoken number is cross-checked against the episode JSON.
  Mismatches are flagged with the timestamp — e.g. *"$97.6 million" spoken vs
  97.6% verified* — so you can listen back before uploading. **Whisper mishears
  are possible: flag, don't accuse.**
- **Comment teases.** If the video says "comment ___", pin a comment with that
  word right after posting.
- **ASR noise.** Ticker and company spellings come out mangled ("Nebus",
  "Corvive"). Ignore them in the transcript — but never copy those spellings into
  a title or description.

---

## 7 · Upload, by hand

`/post-video` never uploads, publishes or posts anything. You do that.

Before you hit publish:

- [ ] Title matches what the video argues
- [ ] Description hook is 2 lines, no links above the fold
- [ ] SEC source links present and clickable
- [ ] First chapter is `0:00`, ≥3 chapters, none under 10s
- [ ] Hashtags 4–6
- [ ] Thumbnail set (`/youtube-thumbnail-maker` on the Mac)
- [ ] Any "comment ___" tease pinned as a comment
- [ ] Fact flubs reviewed
- [ ] The session's work committed and pushed
