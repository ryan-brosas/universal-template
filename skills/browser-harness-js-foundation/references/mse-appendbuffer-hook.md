<!-- capsule-v2 -->
# MSE appendBuffer Capture Doctrine — record what the player feeds MediaSource

## Source
Repo: browser-harness-js @ main`6b18940` (unchanged vs base_sha). BEHAVIORALLY VERIFIED LIVE this pass: real Chrome/151, real fMP4 appended through the hooked prototype, drained byte-exact (see Probe).

## Question
How do ytdl/ttdl download YouTube/TikTok media with zero third-party code — no yt-dlp, no signature solver, no client impersonation?

## Path / Symbol
- `skills/ytdl/scripts/ytdl` hook injection :125-247 (`addScriptToEvaluateOnNewDocument`), drain helpers :322-368, freeze :411-414.
- `skills/ttdl/scripts/ttdl` codec-classification hook :168-262, quiescence latch :356-395, pull :407-433.

## Signature
```js
// Inject BEFORE navigate. appendBuffer is a NON-WRITABLE native property on the
// PROTOTYPE, so define an OWN property on each instance to shadow it:
const origAddSB = MediaSource.prototype.addSourceBuffer;
Object.defineProperty(MediaSource.prototype, 'addSourceBuffer', {
  configurable: true, writable: true,
  value: function(mime) {
    const sb = origAddSB.call(this, mime);
    const entry = { mime, codec, kind, chunks: [], bytes: 0, count: 0 };  // registry
    const origApp = sb.appendBuffer.bind(sb);
    Object.defineProperty(sb, 'appendBuffer', { configurable:true, writable:true,
      value: function(data) {
        if (window.__capDone) return origApp(data);            // frozen: pass through
        const u8 = data instanceof ArrayBuffer ? new Uint8Array(data)
          : new Uint8Array(data.buffer, data.byteOffset, data.byteLength);
        entry.chunks.push(u8.slice()); entry.bytes += u8.length;  // .slice() = own copy
        return origApp(data);                                   // playback unaffected
      }});
    return sb;
  }
});
window.__capDone = true;   // + pause() = atomic freeze; autoplay appends never enter buffers after this
```

## Data Shape
Per-buffer entry `{mime, codec, kind, chunks[], bytes, count}`; page-side accessors `__capInfo()` / `__capBytes()` / `__drainNew(i,maxBytes)` / `__pullBuffer(i,off,len)` all return base64 slices capped at **262143 bytes (256KB−1, divisible by 3 → each base64 slice independently decodable, no interior padding)**.

## Decisive source
- The 4MB socket-death invariant, stated from a reproduced incident (ttdl :415-420): "a single returnByValue frame carrying base64 of a 4MB slice is ~5.6MB of JSON on ONE CDP frame, which closes Dia's debug WebSocket on the first call... a 256KB slice from the same buffer survives." Same note in ytdl :249-253 ("proven on Dia") and in the page-side helper comment :225-231.
- `__drainNew` slices an oversized single chunk ACROSS calls via a per-buffer `(_chunkIdx,_chunkOff)` cursor and "NEVER emits more than maxBytes even if a single appended fmp4 segment exceeds it — a 1440p segment is often 1-4MB, so the old force-one-whole-chunk-through path that dropped the socket is gone" (:232-236).
- Append-before-done ordering (ytdl :340-344): "`__drainNew` returns done:true WITH a non-empty b64 for the final slice... Append BEFORE testing done, or that last slice is silently dropped and the muxed file ends up truncated/corrupt."
- Streaming drain during playback (ytdl :318-322, drain tick every 4th 250ms poll): "By latch-time nearly all of the capture is on disk, so the post-pause pull is just the tail and the tab closes immediately — bytes live in page memory and the tab can't close until they're off, which is why pulling everything after pause kept the tab open ~30s."
- Multi-MediaSource selection (ytdl :421-427, ttdl mirrors): "The player can create more than one MediaSource (quality-switch re-init, mini-player), so there may be several video/audio files. Pick the LARGEST of each kind — that is the real full capture"; the rest are unlinked.

## Flow / Invariant
1. Hook BEFORE navigate (`addScriptToEvaluateOnNewDocument`), guard with `window.__ytdlHooked` idempotency flag.
2. Shadow-on-instance because prototype properties are non-writable; bind original first.
3. Copy every buffer (`u8.slice()`) — detached ArrayBuffers would otherwise corrupt entries.
4. Freeze atomically (`__capDone` + pause in ONE evaluate) before final tail drain.
5. Drain incrementally DURING playback; keep every CDP response ≤256KB base64.

## Probe (direct tests)
LIVE EXECUTION this pass (headless Chromium/151, standalone probe script driving raw CDP over the browser WS): armed the exact hook source, constructed a MediaSource in-page, called `addSourceBuffer('video/mp4; codecs="avc1.64001e"')` (hook fired: entry `{kind:"video",codec:"avc1.64001e",bytes:991017,count:1}`), appended a real 10s Big-Buck-Bunny fMP4, then drained with `__drainNew(0, 262143)` until done → reassembled Buffer.equals(original) = **TRUE**, `ftyp isom` box verified at offset 4. The same probe showed a `background:true` tab NEVER reaches `sourceopen` in headless Chrome while a foreground tab does within ~100ms — empirical confirmation of ytdl/ttdl's foreground-tab requirement ("background tabs have flaky autoplay and MediaSource would never be fed", ttdl :160-162). SDK unit suites at same pin: session.test 1✔, axview.test 11✔, video.test 5✔.

## Retrieve
grep-first (`__drainNew`, `appendBuffer`); graph plane covers session.ts closeTab used by both scripts' finally blocks.

## Verdict
ADOPT as THE reusable browser-native media-capture contract; the 256KB slice cap and append-before-done are correctness-critical, not tuning knobs.
