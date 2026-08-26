<!-- capsule-v2 -->
# Realtime audio codec kernel — how do Float32 samples become wire PCM16 and scheduled playback?

**Source:** Vercel AI SDK Apache-2.0 `main@9d9a73f1551f...`; Codebase Memory `ai`. **Question:** What are the exact encode/decode/resample contracts, and how is gapless browser playback scheduled?

## PCM16 little-endian codec + clock-chained buffer sources
**Path/Symbol:** `packages/ai/src/realtime/audio-utils.ts` — `encodeRealtimeAudio` (:8–25), `decodeRealtimeAudio` (:34–47), `resampleAudio` (:58–82); `packages/ai/src/realtime/browser-realtime-audio.ts` — `schedulePlayback` (:136–167), `startCapture` (:50–74).
**Signature:** `encodeRealtimeAudio(Float32Array): string (btoa)`; `decodeRealtimeAudio(base64): Float32Array`; `resampleAudio(input, inputRate, outputRate): Float32Array`.
**Data Shape:** wire = 16-bit signed little-endian PCM, base64; capture path: ScriptProcessor(4096,1,1) → resample to capture rate → encode → `onAudio`.

### Decisive source
```ts
const s = Math.max(-1, Math.min(1, float32Array[i]));
view.setInt16(i * 2, s < 0 ? s * 0x8000 : s * 0x7fff, true); // ASYMMETRIC clamp
...
const chunkSize = 0x8000;
binary += String.fromCharCode(...chunk);   // chunked: spread has an arg-count limit
```
```ts
const startTime = Math.max(this.playbackTime, ctx.currentTime);
source.start(startTime);
this.playbackTime = startTime + buffer.duration;   // chain next chunk after this one
...
source.onended = () => {
  this.activeSources.delete(source);
  if (this.playbackQueue.length === 0 && this.activeSources.size === 0)
    this.setPlaying(false);                        // idle only when ALL drained
};
```

**Flow:** CAPTURE: mic stream → ScriptProcessor → linear-interpolated resample (`inputRate === outputRate ⇒ identity return`) → clamp to [-1,1] → asymmetric scale (negative ×0x8000, positive ×0x7FFF — symmetric scaling overflows −32768) → base64 in 32KiB chunks. PLAYBACK: decode base64 → Float32 → push to queue → each buffer scheduled at `max(playbackClock, now)` with the clock advanced by the buffer's duration so chunks chain gaplessly → `stopPlayback` drops the queue, stops live sources, and RESETS the clock to current time so the next burst starts clean.
**Invariant:** The negative/positive scale split and the chunked base64 build are correctness constraints, not style (spread on >~64–128KiB throws). `isPlaying` clears only when BOTH queue and active-source set are empty — clearing on queue-empty alone would flicker between every delta. Resampling is deliberately "suitable for voice" quality (linear), not audiophile-grade.
**Probe:** deterministic: `grep -n "s \* 0x7fff" packages/ai/src/realtime/audio-utils.ts` → `14:`; `grep -n "chunkSize = 0x8000" packages/ai/src/realtime/audio-utils.ts` → `18:`; `grep -n "Math.max(this.playbackTime, ctx.currentTime)" packages/ai/src/realtime/browser-realtime-audio.ts` → `153:`; `grep -n "activeSources.size === 0" packages/ai/src/realtime/browser-realtime-audio.ts` → `162:`. Direct tests: none for these functions (browser-API-bound; recorded caveat) — reducer/session suites cover their callers.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "encodeRealtimeAudio PCM16 base64", limit: 10, fields: ["signature","name","file"] });
// verified live @9d9a73f: rank#1 audio-utils.encodeRealtimeAudio :8-25
```

## Verdict
Adopt the asymmetric PCM16 clamp, chunked base64, and clock-chained scheduling verbatim; adapt sample rates via session config; omit ScriptProcessor for production (deprecated API — swap in AudioWorklet keeping the same encode contract).
