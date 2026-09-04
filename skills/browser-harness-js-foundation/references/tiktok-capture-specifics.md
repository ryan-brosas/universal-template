<!-- capsule-v2 -->
# TikTok Capture Specifics — foreground autoplay, separate buffers, edit-list trim, og:title fallback

## Source
Repo: browser-harness-js @ main`6b18940` (unchanged vs base_sha). Complements mse-appendbuffer-hook (shared hook core), codec-kind-classification (kind logic), playback-vs-append-capture (latch), title-latch-spa-reversion (naming) — this capsule holds the TikTok-only residue.

## Question
Which TikTok-specific behaviors must a porter handle beyond the generic MSE capture?

## Path / Symbol
`skills/ttdl/scripts/ttdl` :160-162 (foreground requirement), :75-79 (ffmpeg hard dependency), :66-73 + :440-461 (URL/ID normalization + author/id extraction), :489-491 (separate-buffers note), :477-486 (trim).

## Signature
```bash
# Bare numeric ID → https://www.tiktok.com/@_/video/<id>  ("TikTok redirects to the real author");
# vm.tiktok.com/<code> and tiktok.com/t/<code> short links pass through — the browser follows
# the redirect and "the canonical URL is read back from location.href after load".
# author = substring after '/@' up to '/'; id   = digits after '/video/' (pure string ops).
```

## Decisive source
- Foreground tab (:160-162): "TikTok autoplays muted on a foreground tab; **background tabs have flaky autoplay and MediaSource would never be fed**." (Independently reproduced for headless Chrome in this pass's MSE probe: background:true tab never fired sourceopen.)
- Separate SourceBuffers always (:489-491): ffmpeg required even when only video+audio — no muxed-buffer path.
- Watermark-free by construction (header :13-15): "The capture is the CLEAN, unwatermarked playback stream — TikTok's own 'Download' button serves a separately-rendered watermarked file; recording MediaSource gets what the player actually shows."
- Quality ramp in --info (:296-312): intrinsic resolution read by polling `videoWidth/videoHeight` with max-tracking and stable≥4 stop — "it ramps up as the player bumps quality, so track the max."

## Data Shape
--info result `{ok,info:true,title,author,id,duration,width,height}`; capture result adds `videoPath/videoCodec/audioPath/audioCodec` (codec strings from the classification entry) + `_stats`.

## Flow / Invariant
1. Foreground tab + muted autoplay; never fight playbackRate resets (append-driven model).
2. Read canonical identity from post-redirect location.href, not the input URL.
3. Expect exactly two buffers (video+audio); largest-of-kind selection still guards quality re-init.

## Probe (direct tests)
Deterministic probes at pin: `grep -c "@_/video" skills/ttdl/scripts/ttdl` → 1; `grep -c "'/@'" skills/ttdl/scripts/ttdl` → 1. The foreground-autoplay invariant has live corroboration from this pass's Chromium probe (background tab sourceopen timeout). Full TikTok E2E needs egress + likely login — coverage caveat recorded.

## Retrieve
grep-first (`@_/video`, `og:title`, `-t "$dur"`).

## Verdict
ADOPT these four specifics whenever porting MSE capture to TikTok or similar redirect-heavy, edit-listed, two-buffer platforms.
