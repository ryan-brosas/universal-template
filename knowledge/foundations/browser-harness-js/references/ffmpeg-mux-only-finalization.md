<!-- capsule-v2 -->
# ffmpeg Mux-Only Finalization — container copy, never re-encode

## Source
Repo: browser-harness-js @ main`6b18940` (unchanged vs base_sha).

## Question
What exactly does ffmpeg do in ytdl/ttdl, and which flags carry correctness?

## Path / Symbol
ytdl :477-505; ttdl :464-489. Header claims: ytdl :17-19 "ffmpeg is a muxer only (HD video+audio)"; ttdl :14-15 "ffmpeg is a muxer+trimmer only (-c copy)".

## Signature
```bash
# WebM pair: plain stream-copy mux
ffmpeg -hide_banner -y -loglevel error -i video.webm -i audio.webm -c copy out.webm
# fMP4 pair: +faststart so moov atom leads (streamable immediately)
ffmpeg ... -i v -i a -c copy -movflags +faststart out.mp4
# TikTok: trim to the EDIT-LISTED duration the player actually showed:
ffmpeg ... ${dur:+-t "$dur"} -c copy -movflags +faststart out.mp4
```

## Data Shape
Input files are raw `.fmp4`/`.webm` captures named by buffer kind (`video0.fmp4`, `audio1.webm` — kind+index+ext from the mime). Output ext follows the VIDEO buffer's container: webm→`.webm`, else `.mp4`; audio-only → `.m4a`/`.webm` by audio container.

## Decisive source
ytdl :493-500 branch structure: both buffers present → mux; video only → plain copy ("YouTube sometimes serves a single muxed buffer"); audio only → m4a/webm copy. ttdl :489-491: "TikTok serves audio and video as SEPARATE SourceBuffers, so ffmpeg is always needed (mux + trim + faststart)." The trim rationale (:477-482): "the player plays an edit-listed <duration> (e.g. 27.8s) but the raw MSE media is longer (the source file has a trailing section the player excludes). Trimming to <duration> makes the output match what the user actually watched." `-loglevel error` keeps output clean for CLI composition; `-hide_banner -y` for non-interactive use.

## Flow / Invariant
1. NEVER re-encode: `-c copy` preserves the exact bits the site served.
2. `-movflags +faststart` on every mp4 output — without it the file is not streamable and players stall before moov loads.
3. Trim only when the platform edit-lists duration shorter than raw media (TikTok yes, YouTube no).
4. Handle the missing-partner cases explicitly (muxed-single-buffer, audio-only keep).

## Probe (direct tests)
Smoke harnesses require ffmpeg transitively (ttdl hard-fails with install guidance if absent :75-79 — "Required to mux audio+video, trim to playback duration, and faststart"). Deterministic probes at pin: `grep -c "\-c copy" skills/ttdl/scripts/ttdl skills/ytdl/scripts/ytdl` → 6 total occurrences (ttdl=4 + ytdl=2; grep -c prints per-file lines when given multiple paths); `grep -c "faststart" skills/ttdl/scripts/ttdl` → 6. [ERRATUM 8/24 frontier-agents audit lane: original capsule claimed "4 total" / "3" — those were single-file reads; counts re-derived against source at pin `6b189406`.]

## Retrieve
grep-first (`faststart`, `-c copy`, `-t "$dur"`); no graph plane (bash scripts outside TS index).

## Verdict
ADOPT flag-for-flag; each flag maps to a documented failure mode when omitted (unstreamable file, watermark-length mismatch, re-encode quality loss).
