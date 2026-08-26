<!-- capsule-v2 -->
# Playback-Driven vs Append-Driven Capture — ytdl and ttdl latch coverage differently

## Source
Repo: browser-harness-js @ main`6b18940` (unchanged vs base_sha).

## Question
Why does ytdl force 16x playback while ttdl never touches playbackRate, and what does each coverage latch actually wait for?

## Path / Symbol
- ytdl: play nudge :262-273, coverage loop :395-410, autonav kill :249-259, resume-position reset :266-268.
- ttdl: no-rate rationale :330-338, quiescence latch :356-395, edit-list trim :477-486.

## Signature
```js
// ytdl (playback-driven): the player fetches-as-it-plays (SABR)
v.currentTime = 0;                    // signed-in accounts RESUME from last position — capture would miss the start
v.muted = true; v.playbackRate = 16; v.play();
// every tick RE-ASSERTS muted+16x: "the player can clobber them on a quality
// switch, ad, or player re-init, which would un-mute the 16x chipmunk audio mid-capture"
if (s.end >= dur - 0.5 || s.ended) { done = true; break }   // break FIRST time, never re-check

// ttdl (append-driven): "the player fetches+appends the whole fMP4 up front, so
// buffered.end reaches the full duration before currentTime moves at all"
// → playbackRate is cosmetic AND TikTok resets it to 1x on foreground anyway. Don't set it.
if (s.end >= dur - 0.5 && stableTicks >= 2) { done = true }  // buffered + byte-quiescence BOTH
```

## Data Shape
Coverage tick returns `{t, end (buffered.end of last range), ended}` (ytdl) plus `{bytes: __capBytes(), title, og}` (ttdl); poll interval 250ms.

## Decisive source
- ytdl autonav invariant (:250-255): disable YouTube autoplay BEFORE play via `.ytp-autonav-toggle`, state read from aria-label/data-tooltip-title ("Autoplay is on/off"); missing toggle = no-op. "This is the real fix for the background-tab case — even if the tab is throttled and the coverage poll never latches, there is no next-video autoplay to run away to." Plus the first-break rule (:383-385): "we break the FIRST time buffered.end >= dur-0.5 and never re-check — so autoplay advancing to the next video (and resetting currentTime) doesn't matter."
- ytdl resume trap (:266-268): "a signed-in account resumes from the last watch position ('resume from where you left off') even on a bare watch?v=ID URL with no t= — without this the capture only covers from the resume point on."
- ttdl quiescence guard (:356-361): "the player's buffered range caps at the edit-listed duration even as the (longer) raw media keeps appending, so end>=dur alone could fire while bytes are still flowing" → require total captured bytes unchanged for 2 consecutive ticks (500ms) in addition to buffered coverage.
- ttdl trim step (:477-482): ffmpeg `-t $dur -c copy` because "the player plays an edit-listed <duration> (e.g. 27.8s) but the raw MSE media is longer... Trimming makes the output match what the user actually watched."
- Deadline formulas differ by drive model: ytdl `max(60s, dur/12 + 60s)` (16x ⇒ ~1/12 realtime), ttdl flat `max(120s, dur + 60s)` (append-driven, not playback-bound).

## Flow / Invariant
Identify which model the target site uses before porting: SABR/DASH streaming players (YouTube) are playback-driven — speed helps and re-assertion is required; progressive/full-append players (TikTok) are append-driven — speed is useless and byte-quiescence must join the latch.

## Probe (direct tests)
No upstream unit tests for the scripts; smoke harnesses exist but need a logged-in browser. Deterministic probes at pin: `grep -c "playbackRate" skills/ytdl/scripts/ytdl` → 2 lines (:299 quality-apply expr sets `v.playbackRate = 16`, :373 coverage-tick expr re-asserts it) vs `grep -c "playbackRate" skills/ttdl/scripts/ttdl` → **0 code lines** (:307/:309 comments only — the asymmetry IS the capsule; a bare `grep -c` returns 2 there from comment lines alone) — ERRATUM pass-5 execution audit: shipped as "ytdl → 4"; live count at unchanged pin `main@6b189406` is 2 (invented count, re-derived against source). `grep -c "stableTicks" skills/ttdl/scripts/ttdl` → 3 lines (:326 decl, :337 bump/reset, :339 done-check).

## Retrieve
grep-first (`autonav-toggle`, `stableTicks`, `__capBytes`).

## Verdict
ADOPT both latches as a matched pair; the resume-position reset and the buffered-caps-at-edit-list quirk are the two silent-corruption traps.
