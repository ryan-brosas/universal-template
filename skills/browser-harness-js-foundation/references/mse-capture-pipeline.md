<!-- capsule-v2 -->
# MSE appendBuffer capture — how do you download streaming video with no yt-dlp, no signer, and no client impersonation?

**Source:** browser-harness-js MIT `main@6b189406`; Codebase Memory `browser-harness-js`. **Question:** What is the hook/latch/drain architecture that records exactly the bytes the player feeds MediaSource?

## Pre-navigate prototype hook + instance shadowing; one-shot coverage latch; 3-aligned slice drain
**Path/Symbol:** `skills/cdp/interaction-skills/media-capture.md` (:1-152); consumers `skills/ytdl/scripts/ytdl`, `skills/ttdl/scripts/ttdl` (both "100% browser-harness-js native" per their headers).
**Signature:** inject via `Page.addScriptToEvaluateOnNewDocument({source: HOOK})` BEFORE navigate; hook wraps `MediaSource.prototype.addSourceBuffer` then defines an OWN `appendBuffer` on each SourceBuffer instance.
**Data Shape:** per-buffer entry `{mime, kind, chunks: Uint8Array[], bytes, count}`; capture frozen by `window.__capDone = true` (hook passes appends through once set).

### Decisive source
```js
const origAdd = MediaSource.prototype.addSourceBuffer;
Object.defineProperty(MediaSource.prototype, 'addSourceBuffer', {
  configurable: true, writable: true,
  value(mime) {
    const sb = origAdd.call(this, mime);
    ...
    Object.defineProperty(sb, 'appendBuffer', {   // OWN property: the prototype's is a non-writable native — assignment silently fails
      configurable: true, writable: true,
      value(data) { if (window.__capDone) return origApp(data); ...entry.chunks.push(u8.slice()); return origApp(data); },
    });
```
Latch + drain rules:
- latch ONCE when `buffered.end >= duration - 0.5` (never re-check → autoplay/loop can't pollute), re-asserting `muted`/`playbackRate=16` each tick because players clobber them on quality switches;
- freeze (`__capDone`) and `pause()` ATOMICALLY;
- pull slices ≤262143 bytes, divisible by 3, in ≤49998-char btoa sub-chunks (payload-limits-replay capsule);
- keep only the LARGEST buffer of each kind (re-inits leave abandoned low-quality pairs);
- derive kind from the CODEC fourcc (`mp4a|opus`=audio, `avc1|av01`=video) — TikTok puts audio in a `video/mp4` SourceBuffer.

**Flow:** foreground tab → inject hook pre-navigate (after = missed init segment) → play muted at high rate while draining incrementally DURING playback (post-pause full drain keeps the tab open ~30s) → latch → freeze+pause → slice-drain to disk → mux with ffmpeg (`-t <shown-duration> -c copy`; MSE media can exceed the player-displayed duration).
**Invariant:** (1) The page does the hard parts (auth, poToken, n-solving, SABR demux); you persist what it already produced — that is why this needs no signer. (2) Hook timing is absolute: pre-navigate or miss the init segment. (3) Instance-shadowing vs prototype-assignment is not a style nit — native accessors silently ignore plain assignment.
**Probe:** live-site behavior (no test). Deterministic probes: ytdl/ttdl headers state the mechanism; doc constants `grep -n "262143\|addScriptToEvaluateOnNewDocument" skills/cdp/interaction-skills/media-capture.md`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-harness-js", query: "addScriptToEvaluateOnNewDocument", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt hook→latch→drain for any "capture what the page feeds a native API" task (generalizes to XHR.send/fetch/WebSocket bodies); adapt codec table and rates; omit nothing from the latch/freeze pair or looping autoplay corrupts captures.
