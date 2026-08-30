<!-- capsule-v2 -->
# Realtime barge-in — how is model audio stopped and truncated when the user interrupts?

**Source:** Vercel AI SDK Apache-2.0 `main@9d9a73f1551f...`; Codebase Memory `ai`. **Question:** How does the session compute the truncation offset and notify the server on speech barge-in?

## Measured-offset stop-and-truncate
**Path/Symbol:** `packages/ai/src/realtime/realtime-session.ts` — `handleReducerEffect` 'speech-started' arm (:349–364), 'play-audio' arm tracking `currentResponseItemId` (:344–348); `packages/ai/src/realtime/browser-realtime-audio.ts` — `stopPlayback` (:95–111), `getPlaybackOffsetMs` (:113–117).
**Signature:** `getPlaybackOffsetMs(): number` = `(ctx.currentTime - playbackStartTime) * 1000`; effect `{type:'speech-started'}` carries no payload.
**Data Shape:** truncate event `{type:'conversation-item-truncate', itemId, contentIndex: 0, audioEndMs: number}`.

### Decisive source
```ts
case 'speech-started': {
  if (this.state.isPlaying) {
    const playedMs = this.audio.getPlaybackOffsetMs();
    this.audio.stopPlayback();                    // queue drop + source.stop() all
    if (this.currentResponseItemId != null) {
      this.sendEvent({
        type: 'conversation-item-truncate',
        itemId: this.currentResponseItemId,
        contentIndex: 0,
        audioEndMs: Math.round(playedMs),
      });
    }
  }
  break;
}
```

**Flow:** every `audio-delta` effect records which itemId is playing before scheduling audio → a new `speech-started` (user began talking) while audio plays measures how far playback got (`playbackStartTime` was stamped at first play of the burst) → local stop drops queued buffers and stops every active `AudioBufferSourceNode` (try/catch per source: the browser may have already stopped them) → server gets `conversation-item-truncate` with the ROUNDED millisecond offset so its transcript context matches what the user actually heard.
**Invariant:** Truncation is sent ONLY when something was actually playing and only for a KNOWN item id; `contentIndex` is pinned to 0 because one item = one audio content part in this protocol. The offset must be captured BEFORE stopping playback — after `stopPlayback`, `currentTime` bookkeeping resets to "now" and the measurement is lost. Reducer also clears `currentAssistantMessageId` on speech-started so post-interrupt text lands in a FRESH message.
**Probe:** deterministic: `grep -n conversation-item-truncate packages/ai/src/realtime/realtime-session.ts` → `356:`; `grep -n "audioEndMs: Math.round(playedMs)" packages/ai/src/realtime/realtime-session.ts` → `359:`; `grep -n "playbackTime = this.playbackContext.currentTime" packages/ai/src/realtime/browser-realtime-audio.ts` → `108:`. Direct tests: reducer suites cover state side; timing side is browser-only (no unit test — recorded caveat).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "handleReducerEffect speech-started stopPlayback truncate", limit: 10, fields: ["signature","name","file"] });
// verified live @9d9a73f: rank#1 AbstractRealtimeSession.handleReducerEffect :342-381
```

## Verdict
Adopt measure-before-stop ordering and the guard trifecta (isPlaying + known itemId); adapt the truncate event shape to your provider; omit nothing — sending full-length or zero offsets desyncs the server's idea of heard audio.
