<!-- capsule-v2 -->
# In-session MediaRecorder fallback swap — how do you swap engines mid-recording without losing the user's take?

**Source:** screenity GPL-3.0 `master@e10e375fafa1680de99ca6db36536dd4a1f4f7d4`; Codebase Memory `screenity`. **Question:** When the WebCodecs encoder dies before any output, what exact conditions justify silently restarting on MediaRecorder, and what must be torn down first?

## Conditional engine swap in onError
**Path/Symbol:** `src/pages/Recorder/Recorder.jsx:2204-2326` (`onError` callback of the WebCodecsRecorder wiring).
**Signature:** `onError(err: {code?: string, detail?, finalized?})` — closure over recorder/liveStream/chunkWriter refs.
**Data Shape:** decision inputs: `sentLast` (video-ready shipped), `savedCount/hasChunks` (any output), `liveStream` track readyState, `webcodecsFallbackTriggered` (once-per-session latch).

### Decisive source
```ts
            // Late teardown error after video-ready shipped: the file is
            // finalized and the sandbox is mid OPFS read, so surfacing it races
            // that read and pops a spurious modal. Breadcrumb and drop.
            if (sentLast.current && !err?.finalized) { /* diag breadcrumb */ return; }
            ...
            // Same-session fallback: if WebCodecs blew up before any chunk
            // landed and the capture track is still live, swap to
            // MediaRecorder via a recursive startRecording() so the user
            // doesn't have to re-pick the screen / re-grant prompts.
            // NOT gated on `transient`: a live track with zero chunks is the
            // canonical recoverable case ...
            const liveVideoTrack = liveStream.current?.getVideoTracks?.()[0] || null;
            const trackLive = liveVideoTrack?.readyState === "live";
            const noChunksYet = savedCount.current === 0 && !hasChunks.current;
            if (!webcodecsFallbackTriggered && noChunksYet && trackLive) {
              webcodecsFallbackTriggered = true;
              ...
                // Abort the OPFS writer so the re-entered startRecording opens
                // a fresh IDB one. Without this, MR bytes would stream into
                // OPFS and the editor.html sandbox couldn't read them.
                if (chunkWriter.current) {
                  try { await chunkWriter.current.abort(); } catch {}
                  chunkWriter.current = null;
                  chunkBackendRef.current = null;
                }
                isStarting.current = false;
                try { await startRecording({ forceMediaRecorder: true }); } catch (e) { /* toast + error */ }
```

**Flow:** structured failure code preferred over generic → post-finalize errors dropped with breadcrumb → transient classification shared with `markFastRecorderFailure` → persist failure keys (never flips the durable user setting — sticky TTL handles it) → if once-latch free AND zero chunks AND track live: null the recorder, flip `fastRecorderInUse=false`, cleanup old engine, ABORT OPFS writer, clear `isStarting`, recurse into `startRecording({forceMediaRecorder:true})`; else toast + surface error for non-transient failures.
**Invariant:** at most one swap per session; a swap must abort/reset the chunk-writer backend BEFORE re-entry (backend mismatch makes the artifact unreadable by the editor); the durable `useWebCodecsRecorder` user setting is never written from an error path.
**Probe:** deterministic anchors: grep Recorder.jsx for `NOT gated on \`transient\`` (:2260-2261), `MR bytes would stream into\n                  // OPFS and the editor.html sandbox couldn't read them` (:2291-2293), `webcodecsFallbackTriggered = true` (:2275). Byte-exact at HEAD.

## Get live surrounding code
**Retrieve:**
```
search_graph(project="screenity", file_pattern="*Recorder/Recorder.jsx", query="onError fallback webcodecs")
→ observed onError :2204-2326 (complexity 13) adjacent to onFinalized :1996-2187 and onStop :2327-2330;
  trace_path("shouldUseFastRecorder", inbound) shows startRecording/startStream as gate consumers.
```

## Verdict
Adopt the three-condition swap gate (once-latch ∧ zero-output ∧ live track) and the writer-abort-before-reentry ordering. Adapt engine names/backends to your host. Omit OPFS-vs-IDB specifics unless your port shares the dual-backend chunk store.
