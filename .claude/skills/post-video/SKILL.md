---
name: post-video
description: Prep a finished YouTube video for posting — transcribe the final export locally, then produce the title options, full description, and linked chapters. Use when Nikil says /post-video, "get this ready to post", "make the chapters", "title and description for my video", or drops a final exported .mov/.mp4 and wants the YouTube metadata.
argument-hint: [path to final exported video] [ticker or topic, if not obvious]
---

# Post Video

You prep Nikil's finished @NikRayani videos for YouTube upload. Input: the final exported video file (usually on `~/Desktop`, named like `NBIS 8.16.mov`). Output: chapters, 2–3 title options, and a paste-ready description — all grounded in what the video *actually says*, never guessed.

## Process

### 1. Locate inputs
- Video path comes from the arguments. If missing, look for the newest video file on `~/Desktop` and confirm with Nikil before proceeding.
- Identify the ticker/topic from the filename or arguments.
- **Sunday stock episodes**: load the verified episode data at `episodes/<SYM>.json` — it has `verdict`, `findings` (the video's claims), `fairValue`, and `sources` (SEC URLs). This is the fact source of truth.
- **Wednesday /learn-stock episodes**: no episode JSON — skip deck cross-checks and build from the transcript alone.

### 2. Transcribe (local, free)
```bash
SP="<scratchpad dir>"
ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1 "$VIDEO"
ffmpeg -y -v error -i "$VIDEO" -vn -ac 1 -acodec libmp3lame -q:a 4 "$SP/final.mp3"
npx hyperframes transcribe "$SP/final.mp3" -d "$SP" --json --model small.en
```
`transcript.json` is a flat word array `[{text, start, end}, …]`. Group words into sentences at terminal punctuation and print them with `M:SS` timestamps — that timestamped sentence list drives everything below.

### 3. Chapters
Find the topic shifts in the timestamped transcript (new finding, numbers → chart, recap, trade plan, outro). YouTube rules for linked chapters:
- First chapter at exactly `0:00`
- At least 3 chapters, **every chapter ≥ 10 seconds** (merge anything shorter)
- Chronological, `M:SS` format
Label each chapter with a short curiosity-preserving phrase from the content ("The customers who vanished", "My fair value: $173") — not generic labels like "Part 2".

### 4. Titles (2–3 options, best first)
- Run WebSearch for the ticker's news this week AND competing YouTube titles — never rely on recall for what's "working right now".
- Every option must match what the video actually argues (a hook the video never mentions kills retention). Verify against the transcript before proposing.
- Best patterns for this niche: real tension ("Grew 454% — but the profit isn't real"), a specific number from the video, question + price target, "I read the filings" forensic angle.

### 5. Description (paste-ready, in one code block)
Order matters:
1. **Two-line hook** (this is all that shows in search — no links here)
2. "In this video:" bullets — pulled from the findings/transcript, tease don't spoil
3. Source links (SEC filing URLs from the episode JSON — credibility is the brand)
4. `⏱ CHAPTERS` block from step 3
5. Not-financial-advice disclaimer
6. 4–6 hashtags (#TICKER #StockAnalysis #Investing …)

### 6. Quality checks (always report these)
- **Fact flubs**: cross-check every spoken number against the episode JSON. Flag mismatches with the timestamp (e.g. "$97.6 million" spoken vs 97.6% verified) so Nikil can listen back before upload. Whisper mishears are possible — flag, don't accuse.
- **Comment teases**: if the video says "comment ___", remind him to pin a comment with that word right after posting.
- Transcript spellings of tickers/names will be mangled ("Nebus", "Corvive") — that's ASR noise, ignore it, but never copy those spellings into titles/descriptions.

## Critical Rules
1. Never invent a chapter, title claim, or description bullet the transcript doesn't support.
2. Never state date-sensitive market facts from memory — WebSearch first.
3. Numbers in the description come from the episode JSON (the verified source), not from the transcript's ASR guesses.
4. Deliver title options + description + chapters in one final message; description in a single copy-paste code block.
5. Don't upload, publish, or post anything — Nikil posts it himself.
