---
name: ttdl
description: >-
  Download TikTok videos browser-natively — no `yt-dlp`, no signature solver, no
  watermark. The browser plays the video (URL signing, CDN tokens, quality
  selection all done by the page itself); ttdl records the demuxed media the
  player feeds to MediaSource via a `SourceBuffer.appendBuffer` hook and muxes
  to MP4 with ffmpeg. If the user can watch the video, it's downloadable —
  region-locked and age-gated content work as long as a logged-in tab can play
  them. The capture is the clean, unwatermarked playback stream (TikTok's own
  Download button serves a separately-rendered watermarked file). Use when the
  user wants to download, save, or fetch a TikTok video (with or without audio)
  to disk.
setup: bash <skill-dir>/scripts/setup
compatibility: Requires `browser-harness-js` on PATH + a Chromium browser with remote debugging (see the `cdp` skill) and a logged-in TikTok tab for gated/region-locked content. `ffmpeg` on PATH (always — mux + trim + faststart).
---

# ttdl — browser-native TikTok downloader

A thin `browser-harness-js` heredoc, exactly like `gsearch`/`xsearch`/`ytdl`.
There is **no Bun program, no vendored signer, no HTTP client impersonation**.
Every hard thing TikTok does to play a video — the signed CDN URL, the adaptive
quality ramp, the edit list — the page already does for playback. ttdl just
records the result. The capture is the **clean, unwatermarked** playback stream:
TikTok's in-app/Download button serves a *separately rendered* watermarked file,
while recording MediaSource gets exactly what the player shows the viewer.

```bash
ttdl "https://www.tiktok.com/@user/video/7642721752497310989"   # best → ~/Downloads
ttdl "https://www.tiktok.com/@user/video/7642721752497310989" -q audio   # audio only (.m4a)
ttdl "https://www.tiktok.com/@user/video/7642721752497310989" --info      # title / author / duration / resolution
ttdl "https://vm.tiktok.com/ZMxxxxx/"                            # short link (browser resolves the redirect)
ttdl 7642721752497310989                                         # bare numeric ID
ttdl "https://www.tiktok.com/@user/video/..." -o Name -d ~/Videos
```

## Quality targets

| `-q`    | what happens | needs ffmpeg? |
|---------|--------------|---------------|
| `best`  | let the player pick (it auto-ramps to the highest quality it offers), capture, mux, trim, faststart | yes |
| `audio` | keep only the audio buffer → `.m4a` | yes |

There is no `-q 720p`/`1080p` on purpose. Unlike YouTube, TikTok's web player
doesn't expose a clean quality API — it auto-selects based on connection and
*ramps up* (creating a new, higher-quality MediaSource mid-playback; see How it
works). ttdl captures the largest of each kind, so you always get the top quality
the player reached. Forcing a specific resolution isn't reliably possible.

`ffmpeg` is a **muxer + trimmer** here, never a re-encoder (`-c copy`):
- **Mux:** TikTok serves audio and video as **separate** SourceBuffers (e.g.
  HEVC `hvc1.*` video + AAC `mp4a.*` audio), so they need combining into one file.
- **Trim:** the raw MSE media is *longer* than what the player plays (see
  "Why trim to the duration").
- **Faststart:** the captured streams are fragmented MP4; `-movflags +faststart`
  reorders `moov` to the front so the file is seekable/streamable everywhere.

The output stays pure (lossless) at TikTok's own codecs — HEVC video + AAC
audio. That pair is QuickTime/iOS-friendly (iOS natively decodes HEVC+AAC), so
unlike ytdl's AV1/Opus output, no re-encode is needed for Apple devices.

## How it works

All inside one `browser-harness-js <<EOF` heredoc, ytdl-style:

1. **Connect** to the browser's shared CDP session (or `session.connect()`).
2. **`Page.addScriptToEvaluateOnNewDocument`** — inject the MSE hook *before*
   any page JS runs:
   - Wrap `MediaSource.prototype.addSourceBuffer` (via `Object.defineProperty`)
     so each `SourceBuffer` is tagged with its **codec** and a derived **kind**.
   - On each SourceBuffer, define an OWN `appendBuffer` property that records
     the bytes (the demuxed ISO-BMFF fragment) before calling the original. An
     own property is required — `SourceBuffer.prototype.appendBuffer` is a
     non-writable native method, so reassigning the prototype silently no-ops.
   - **Kind is derived from the `codecs=` fourcc, not the container mime** (see
     Traps — this is the single biggest TikTok-specific difference from ytdl).
3. **`Target.createTarget` foreground** → `Page.navigate` to the watch URL →
   wait `networkIdle`, then poll for `<video>` and bail on a verify/captcha
   interstitial. Foreground is required: background tabs have flaky autoplay,
   and if the player never starts, MediaSource is never fed.
4. **Read the author + video id** from the final (post-redirect) `location.href`
   — short links (`vm.tiktok.com/…`, `tiktok.com/t/…`) have redirected by now.
5. **Play muted** from `currentTime = 0`. Unlike ytdl (16×, because YouTube's
   SABR fetches-as-it-plays and playback rate bounds capture), TikTok capture is
   **append-driven**: the player fetches+appends the whole fMP4 up front, so
   `buffered.end` reaches the full duration before `currentTime` moves at all.
   Playback rate is therefore **cosmetic** for capture — and TikTok's player
   resets `playbackRate` to 1× while the tab is foregrounded, so fighting it is
   pointless. ttdl doesn't set `playbackRate`. It does re-assert `muted` each
   coverage tick: the player can un-mute on a quality switch / re-init and blast
   audio mid-capture.
6. **Wait until the watched portion is buffered AND append activity quiesces**
   (`buffered.end >= duration-0.5` *and* total captured bytes unchanged for 2
   ticks), then **freeze capture + pause atomically**. A `__capDone` flag makes
   the hook pass appends through (stop recording) the instant coverage
   completes, so TikTok's auto-loop (which re-feeds MSE) doesn't pollute the
   captured buffers.
7. **Pick the largest video + largest audio buffer.** The player commonly
   creates **two** MediaSource instances — an initial lower-quality one, then a
   higher-quality one when it ramps up — yielding 4 buffers (2 video, 2 audio).
   The largest of each kind is the real capture; the small ones are the
   abandoned lower-quality pair.
8. **Pull each to disk** in 256 KB (byte-count divisible by 3, so each base64
   slice is independently decodable) chunks: page-side `__pullBuffer(i,offset,len)`
   returns base64; the REPL decodes with `Buffer.from(b64,'base64')` and
   `fs.appendFileSync`s it. 256 KB, not 4 MB — see the Traps below: a single
   `returnByValue` frame carrying base64 of a 4 MB slice closes Dia's debug
   WebSocket on the first call.
9. **ffmpeg** `-i video -i audio -t <duration> -c copy -movflags +faststart out.mp4`
   (bash, after the heredoc returns the temp-file paths).
10. **`closeTab`** in `try/finally`, fire-and-forget — exact ytdl teardown.

## Why capture at MediaSource, not the CDN URL

TikTok serves each video from a **signed** CDN URL
(`v16-webapp-prime.tiktok.com/video/tos/…?a=…&bti=…&ft=…&x-expires=…&x-signature=…`)
that's minted by the page and tied to the session. The signature is in the URL,
so a naive `fetch(url)` *can* work while the page is live — but the URL is
short-lived, the response can be range-limited, and you'd be reverse-engineering
TikTok's player to find it. Capturing at `SourceBuffer.appendBuffer` sidesteps
all of that: whatever the player fetched, however it signed it, the demuxed bytes
flow through MSE in the clear. This is auth-agnostic, signing-agnostic, and
quality-agnostic — the page did all of it; we record the output. It's literally
"watch it → record it," the same model as ytdl.

## Why trim to the duration

TikTok serves an fMP4 that is **longer** than what the player plays. The
`<video>.duration` (and `seekable`/`buffered` ranges) reflect an **edit-listed**
playback length — e.g. 27.8 s — while the raw MSE media is ~30.4 s. The player
plays 0 → 27.8 s then **loops back to 0**; the trailing ~2.6 s is real footage
the player deliberately excludes from the feed. If you capture all the MSE bytes
verbatim (the ytdl model), you get a video ~10% longer than what the user
watched, with a tail they never saw.

So ttdl **trims the muxed output to `<video>.duration`** (`ffmpeg -t <dur> -c
copy`). The output matches what the user actually watched. The quiescence guard
in the coverage latch (step 6) is what makes this safe to do from a capture that
may or may not have grabbed the whole tail: `buffered.end >= dur-0.5` guarantees
the watched portion is fully appended regardless of how much tail came through,
and trimming discards whatever tail did.

## Files

All paths relative to `<skill-dir>`.

- `scripts/ttdl` — the bash CLI (a `browser-harness-js` heredoc, no `#!bun`)
- `scripts/setup` — symlink `ttdl` + `browser-harness-js` onto PATH
- (no `lib/` — no solver/client scaffolding)

## Traps

- **Classify SourceBuffers by the codec in `codecs=`, never by the container mime.** TikTok puts the **audio** in a SourceBuffer whose container is `video/mp4` — only the `codecs="mp4a.40.29"` param reveals it's audio. A naive `mime.startsWith("video") ? "video" : "audio"` (the ytdl pattern) tags *both* TikTok buffers as `video`, you pick the largest (the real video) and drop the audio buffer as "smaller video", and the capture comes back **silent**. ttdl parses the fourcc prefix (`mp4a`→audio, `hvc1`/`avc1`/`av01`→video) and only falls back to the container mime if there's no `codecs=`. Keep this — it's the one line that makes TikTok capture work.
- **The MSE hook must inject via `Page.addScriptToEvaluateOnNewDocument`, not a post-load `Runtime.evaluate`.** The player grabs `MediaSource`/`addSourceBuffer` references while it boots; injecting before any page JS runs is the only way to patch them in time. The hook runs in the main world (no `worldName`), where the player lives.
- **Patch `appendBuffer` as an OWN property on each `SourceBuffer` instance, never on the prototype.** `SourceBuffer.prototype.appendBuffer` is a non-writable native method — `sb.appendBuffer = fn` on the prototype silently no-ops; `Object.defineProperty(SourceBuffer.prototype, 'appendBuffer', …)` fails to take effect. Defining an own property on the instance shadows the prototype method correctly. (`addSourceBuffer` *can* be patched on the prototype via `defineProperty` — it's writable.)
- **Use a foreground tab.** Background-tab autoplay is unreliable on TikTok; if the player doesn't start, MediaSource is never fed and capture is empty. `createTarget({ url: 'about:blank' })` (no `background: true`).
- **Trim the output to `<video>.duration`.** TikTok's raw MSE media is longer than the played (edit-listed) duration; without `-t <dur>` the muxed file has a trailing section the user never saw (see "Why trim to the duration"). The quiescence latch guarantees the watched portion is fully captured before the trim, so this is always safe.
- **Coverage is append-driven, but latch on quiescence, not just `buffered.end`.** TikTok appends the whole fMP4 up front, so capture completes in seconds — but `buffered.end` *caps at the edit-listed duration* even as the (longer) raw media keeps appending. Latching on `end >= dur-0.5` alone can fire while bytes are still flowing. ttdl additionally requires total captured bytes to be unchanged for 2 consecutive ticks (500 ms) before breaking. The `__capDone` freeze-on-latch keeps the auto-loop's re-appends out of the buffers.
- **Pick the largest buffer of each kind — the player re-inits MediaSource on a quality bump.** TikTok ramps quality mid-playback (e.g. HEVC `hvc1.1.6.L186` → `hvc1.1.6.L150`), creating a *second* MediaSource with its own audio+video SourceBuffers. You'll see 4 buffers (2 video, 2 audio); the largest of each kind is the real full capture, the small pair is the abandoned lower-quality one. Don't assume one buffer per kind.
- **TikTok auto-loops; never rely on `ended`.** The `<video>` loops back to 0 instead of firing `ended`, so an `ended`-based latch would spin forever. The `__capDone` flag is what stops the loop's re-appends from doubling the capture. (An `ended` check is kept as a safety for non-looping edge cases, but the real exit is the quiescence+coverage latch.)
- **Re-assert `muted` every poll tick (but NOT `playbackRate`).** TikTok's player can un-mute on a quality switch / re-init; a one-shot `muted = true` at play-start gets clobbered and you'll hear audio mid-capture. The coverage poll re-asserts `muted` each 250 ms. Don't re-assert `playbackRate`: capture is append-driven (the whole file is buffered before playback advances), so the rate is cosmetic, and TikTok's player resets `playbackRate` to 1× on a foregrounded tab anyway — fighting it is pointless. ytdl re-asserts 16× because YouTube coverage *is* playback-bound (SABR fetches-as-it-plays); ttdl isn't, so the divergence is deliberate.
- **Read the title AFTER coverage, with a `data-e2e=video-desc` fallback.** `document.title` is the generic `"TikTok - Make Your Day"` until SRM/hydration finishes (a few seconds in). Reading it right after `networkIdle` gives the generic title. ttdl reads it after the coverage loop completes, and falls back to the `[data-e2e=video-desc]` element's text if the title is still generic.
- **Detect the "verify you are human" / captcha interstitial and back off.** TikTok is aggressive about bot detection. ttdl scans `document.body.innerText` for `verify|robot|human|captcha|unusual|slide to|puzzle` during the player-ready poll and throws a clear error if it hits one. Open the URL once manually in the browser to clear it, then retry — don't hammer it.
- **Borrow a logged-in tab for gated content.** Region-locked, age-gated, and followers-only videos may require an active TikTok login. ttdl opens its own tab but reuses the browser's cookie jar; if you can watch it in the browser, ttdl can record it.
- **`ffmpeg` is always required.** Unlike ytdl (where ffmpeg is only needed for HD muxing), ttdl needs it for every download: TikTok serves separate audio+video buffers (mux), the edit-list tail (trim), and fragmented-MP4 capture (faststart). The CLI refuses to run if `ffmpeg` isn't on PATH. Don't drop `-y` (overwrite) — without it ffmpeg's interactive `Overwrite? [y/N]` prompt fails non-interactively and leaves a stale file.
- **Bytes cross the CDP boundary as base64** in 256 KB (3-aligned) slices via `Runtime.evaluate` `returnByValue`, decoded with `Buffer.from(b64,'base64')` and appended. The slice size is divisible by 3 so each slice's base64 is independently decodable (no interior `=` padding). Don't slice at a non-multiple-of-3 offset or the concatenation decodes to garbage. **256 KB, NOT 4 MB:** a single `returnByValue` frame carrying base64 of a 4 MB slice is ~5.6 MB of JSON on one CDP frame, which **closes Dia's debug WebSocket on the first call** (reproduced in ytdl — a 256 KB slice from the same buffer survives, the 4 MB slice drops `rs→3` instantly). This was latent in ttdl because TikTok buffers are usually <4 MB, but any longer/higher-quality HEVC TikTok exceeds it and the first pull slice kills the socket. Keep slices small; throughput is a non-issue at these sizes.
- **Output is HEVC + AAC, which is QuickTime/iOS-friendly as-is.** TikTok typically serves HEVC (`hvc1`) video + AAC (`mp4a`) audio; `-c copy` preserves those and iOS/macOS play them natively (no re-encode needed, unlike ytdl's AV1/Opus). If a video comes back as AV1/VP9+Opus and you need QuickTime/iOS, re-encode in one step: `ffmpeg -y -i "out.mp4" -c:v libx264 -crf 18 -preset veryfast -pix_fmt yuv420p -c:a aac -b:a 192k "out-qt.mp4"`.
- **No backticks anywhere in the heredoc body.** In an unquoted `<<EOF`, a lone backtick opens bash command substitution and trips an EOF parse error. Use string concatenation (`'...' + var + '...'`) and double-quoted JS strings, never template literals. Likewise avoid `$` in JS (only intentional `${bash_var}` interpolations belong) and avoid backslash-regex for URL parsing (use `indexOf`/`slice`) so the unquoted heredoc passes it through untouched.
